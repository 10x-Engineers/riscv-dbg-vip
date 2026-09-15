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

## RTL-002 — `sbcs.sbaccess` hardwired, and its reset value lost

**Status:** filed · [`10x-Engineers/riscv-dbg` PR #4 review comment](https://github.com/10x-Engineers/riscv-dbg/pull/4#issuecomment-5677436187)
(issues are disabled on that repository, and the code is that PR's)
**Component:** `riscv-dbg` `src/dm_csrs.sv:618`
**Severity:** medium — blocks all System Bus Access verification

Two distinct defects in one line:

```systemverilog
sbcs_d.sbaccess = (BusWidth == 32'd64) ? 3'd3 : 3'd2;
```

**Reset value.** The spec gives `sbaccess` a reset of **constant 2**, not
`Preset`, with no exception for a DM that lacks 32-bit support. Upstream honours
this with `sbcs_q <= '{default: '0, sbaccess: 3'd2}` at both reset points
(`dm_csrs.sv:612,640`). PR #4 changed those to a plain `'0` (`:694,728`), so the
register now resets to **0**; the 2-or-3 a debugger observes comes only from line
618 overwriting it combinationally every cycle.

**Writability.** `sbaccess` is declared **`R/W`**. Line 513 applies the DMI
write, then line 618 unconditionally overwrites it later in the same
`always_comb`, so last-assignment-wins means no debugger write can ever stick.
The spec grants tying permission explicitly where it means to — `hartsel` high
bits, `hartarraymask`, several `dcsr` bits — and grants nothing for `sbaccess`.

Hardwiring also makes a specified error path unreachable: *"If `sbaccess` has an
unsupported value when the DM starts a bus access, the access is not performed
and `sberror` is set to 4."* That clause presupposes the field can hold an
unsupported value.

**This IS a PR #4 regression** — an earlier revision of this file said it was
not, and that was wrong. `git log -L 618,618:src/dm_csrs.sv` attributes the line
to `17e912c "Updated 1.0 debug module"`, and `17e912c` is one of PR #4's five
commits (`gh api repos/10x-Engineers/riscv-dbg/compare/master...features/riscv-debug-update`).
It is not an ancestor of `pulp-platform/riscv-dbg` master. The mistake was
stopping at "which commit" without then asking which branch that commit belongs
to.

Upstream comparison, measured rather than assumed:

| | `pulp-platform/riscv-dbg` | PR #4 (`17e912c`) |
|---|---|---|
| Reset | `'{default:'0, sbaccess: 3'd2}` (`:612,640`) | `'0` (`:694,728`) |
| Comb. writes to bare `sbcs_d.sbaccess` | **none** — field is writable | `:618`, unconditional |
| `sbaccessN` support bits | `BusWidth >= N` (`:551-555`) | `sbaccess16/8` forced `1'b0` (`:616-617`) |

Upstream assigns only the `sbaccessN` **support** bits combinationally and leaves
the `sbaccess` **size-select** field alone. PR #4 added an assignment to the
size-select field itself, which is the behavioural change.

Spec adjudication with quoted clauses: `debug_module.html#dm-sbcs`,
`introduction.html#1-1-3-3-register-definition-format` (Table 1, Register Access
Abbreviations).

Blocks `SBA-001` through `SBA-018` and `cg_sba` closure.

---

## RTL-003 — `allrunning`/`anyrunning` asserted for a nonexistent hart

**Status:** filed upstream — **independently, by a third party** ·
[`pulp-platform/riscv-dbg#200`](https://github.com/pulp-platform/riscv-dbg/issues/200)
· tracked internally as issue #130

Do **not** file this again. It was reported upstream on 2026-08-12 as *"DMStatus
reports overlapping states for invalid and unselectable harts"*, with the same
root cause: the zero-filled aligned slot reads as running. We
[added our reproduction](https://github.com/pulp-platform/riscv-dbg/issues/200#issuecomment-5677439402)
to that issue rather than opening a second one.
**Component:** DM `dmstatus` assembly
**Severity:** low — misleads a debugger enumerating harts

Selecting a `hartsel` index with no hart behind it reports
`allnonexistent=1`/`anynonexistent=1` **and** `allrunning=1`/`anyrunning=1`.
A hart that does not exist is not running, and a debugger enumerating harts by
walking `hartsel` will conclude it found one.

Reproduces on **both** project DUTs, which suggests a shared assembly pattern
rather than a CVA6-specific slip — confirmed: the two lines are character-identical
in PR #4's DM (`dm_csrs.sv:319-320`) and in pulp upstream as vendored by Ibex
(`:250-251`), so unlike RTL-002 this one is **inherited, not introduced**.

Carried as an illegal cross cell,
`cg_hart_selection.x_hartsel_x_state`, so it cannot silently return.

---

## RTL-004 — halt-on-reset not implemented

**Status:** not a defect — optional feature, recorded so it is not re-diagnosed.
Also tracked upstream as [`pulp-platform/riscv-dbg#187`](https://github.com/pulp-platform/riscv-dbg/issues/187)
**Component:** DM

`dmstatus.hasresethaltreq=0`, so `setresethaltreq` does nothing and
`dcsr.cause=5` (resethaltreq) is unreachable. The spec makes halt-on-reset
optional, so this is a capability gap rather than a bug.

The portable substitute is `RST-053`: assert `ndmreset`, write `haltreq` while
reset is held, release. The hart enters Debug Mode on release and reports
`cause=3`. `cp_cause.resethaltreq` is an `ignore_bins` naming this reason.

---

## RTL-005 — `setkeepalive`/`clrkeepalive` cleared before they are tested

**Status:** filed · [`10x-Engineers/riscv-dbg-vip#148`](https://github.com/10x-Engineers/riscv-dbg-vip/issues/148)
**Component:** `riscv-dbg` `src/dm_csrs.sv:590-591` vs `:602-607`
**Severity:** low — `keepalive` is a hint, but its control bits are specified writable

```systemverilog
590:    dmcontrol_d.setkeepalive = '0;      // cleared here...
602:    if(dmcontrol_d.setkeepalive) begin  // ...then tested here, in the SAME always_comb
```

Last-assignment-wins inside one `always_comb`, so both conditions are constant
zero and `keepalive` can never be set or cleared.

**Found by code coverage, not by a failing check** — which is the part worth
keeping. `TC-AC-025` writes both bits and asserts the hart stays halted. It
**passes**, because ignoring keepalive does not disturb run control. The defect
appeared only as two blocks that stayed uncovered after the test was added, with
the DMI writes confirmed correct on the wire (`0x21`, `0x11`) and the bit
positions matching `dm_pkg.sv`'s own `dmcontrol_t` packing.

A test that passes while proving nothing is exactly what a coverage model is
supposed to catch.

**Same shape as RTL-002.** Second instance in this file of a later unconditional
assignment in one `always_comb` killing an earlier one. Worth sweeping
`dm_csrs.sv` for more rather than fixing the two in isolation.

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
