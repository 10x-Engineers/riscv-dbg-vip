# RTL findings — CVA6 + riscv-dbg

Design defects found while closing functional coverage. **Recorded, not fixed.**
Fixing RTL from the DV side hides the defect from whoever owns the design, and
a testbench that works around a bug stops measuring it.

DV-side bugs are fixed in place and are not listed here — they belong in the
commit that fixed them.

| Status | Meaning |
|---|---|
| `filed` | Raised upstream, issue linked |
| `unfiled` | Confirmed and evidenced here, not yet raised |
| `suspected` | Reproducible but root cause not yet isolated |

---

## RTL-001 — Single-step over `wfi` deadlocks the hart

**Status:** filed · `openhwgroup/cva6#3549` (duplicate of `#3497`, PR `#3525` open)
**Component:** CVA6 `core/csr_regfile.sv`, `wfi_ctrl`
**Severity:** high — the debugger loses the hart permanently

`wfi_ctrl` arms the stall without checking `dcsr.step`, so a `wfi` stepped over
stalls instead of retiring as a `nop`. Nothing can recover it: `dcsr.stepie=0`
masks the interrupts that would wake it, the debugger must not assert `haltreq`
while stepping, and `dcsr.step` is not itself a wake source.

Spec: `Sdext.html#stepbit` — *"If the instruction being stepped over would
normally stall the hart, then instead the instruction is treated as a nop."*

Measured, fix absent — three successive reads:

```
dmstatus=0x00830c83  allhalted=0  allrunning=1  anyunavail=0
```

`anyunavail=0` with `allrunning=1`: the DM still sees the hart alive. It left
Debug Mode via `dret` and never came back.

Measured, fix present: `dcsr.cause=4`, `dpc 0x80000008 -> 0x8000000c (+4)`.

Covered by `cg_step_external.cp_stepped_class.wfi` and carried as an illegal
transition bin, `cp_step_transition.stuck_running` (`DEBUG => RUNNING [* 2]`),
so a regression of this is a coverage failure rather than a timeout.

---

## RTL-002 — `sbcs.sbaccess` hardwired, and reset to 3 rather than 2

**Status:** unfiled
**Component:** `riscv-dbg` `src/dm_csrs.sv:618`
**Severity:** medium — blocks all System Bus Access verification

Two distinct defects in one line:

```systemverilog
sbcs_d.sbaccess = (BusWidth == 32'd64) ? 3'd3 : 3'd2;
```

**Reset value.** The spec gives `sbaccess` a reset of **constant 2**, not
`Preset`, with no exception for a DM that lacks 32-bit support. This DUT resets
it to 3.

**Writability.** `sbaccess` is declared **`R/W`**. Line 513 applies the DMI
write, then line 618 unconditionally overwrites it later in the same
`always_comb`, so last-assignment-wins means no debugger write can ever stick.
The spec grants tying permission explicitly where it means to — `hartsel` high
bits, `hartarraymask`, several `dcsr` bits — and grants nothing for `sbaccess`.

Hardwiring also makes a specified error path unreachable: *"If `sbaccess` has an
unsupported value when the DM starts a bus access, the access is not performed
and `sberror` is set to 4."* That clause presupposes the field can hold an
unsupported value.

**Not a PR #4 regression.** `git log -L 618,618:src/dm_csrs.sv` attributes the
line to `17e912c "Updated 1.0 debug module"`, which replaced the old v0.13
support-bit block. An earlier note in this project claimed PR #4 introduced it
and that pulp upstream lacks it; neither follows from the history.

Spec adjudication with quoted clauses: `debug_module.html#dm-sbcs`,
`introduction.html#1-1-3-3-register-definition-format` (Table 1, Register Access
Abbreviations).

Blocks `SBA-001` through `SBA-018` and `cg_sba` closure.

---

## RTL-003 — `allrunning`/`anyrunning` asserted for a nonexistent hart

**Status:** unfiled · tracked internally as issue #130
**Component:** DM `dmstatus` assembly
**Severity:** low — misleads a debugger enumerating harts

Selecting a `hartsel` index with no hart behind it reports
`allnonexistent=1`/`anynonexistent=1` **and** `allrunning=1`/`anyrunning=1`.
A hart that does not exist is not running, and a debugger enumerating harts by
walking `hartsel` will conclude it found one.

Reproduces on **both** project DUTs, which suggests a shared assembly pattern
rather than a CVA6-specific slip.

Carried as an illegal cross cell,
`cg_hart_selection.x_hartsel_x_state`, so it cannot silently return.

---

## RTL-004 — halt-on-reset not implemented

**Status:** not a defect — optional feature, recorded so it is not re-diagnosed
**Component:** DM

`dmstatus.hasresethaltreq=0`, so `setresethaltreq` does nothing and
`dcsr.cause=5` (resethaltreq) is unreachable. The spec makes halt-on-reset
optional, so this is a capability gap rather than a bug.

The portable substitute is `RST-053`: assert `ndmreset`, write `haltreq` while
reset is held, release. The hart enters Debug Mode on release and reports
`cause=3`. `cp_cause.resethaltreq` is an `ignore_bins` naming this reason.

---

## Observations that are NOT RTL defects

Recorded because each cost time to diagnose and would otherwise be re-diagnosed.

**`dscratch0`/`dscratch1` are clobbered by the DM.** `hartinfo.nscratch=2` means
the DM owns them as scratch for abstract-command execution. A debugger write
does not survive a program-buffer command. `TC-DCSR-003` asserted preservation
and was wrong; the testplan row was re-specified rather than an issue filed.

**Coverage reads 0.00% under `make soc_test`.** Covergroups only collect when
the snapshot is built with `-coverage all`. `soc_test` reports zeros by
construction; `soc_test_cov` is the target that measures. This looks exactly
like a broken testbench and is not one.

**`step_stall` once reported 9/9 against the wrong program.** `coverage_regress`
did not pass each config's `params.elf`, so every scenario ran the default
`halt_probe.elf`. The sequence resolved `wfi_insn` from the right ELF's symbol
table and stepped whatever sat at that address in the wrong one — a 2-byte
compressed instruction — and passed. Fixed in the Makefile; worth knowing
because it passed vacuously rather than failing.
