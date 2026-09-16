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

## RTL-006 — `sbcs` reserved bits [28:23] read back as written

**Status:** filed · [`#149`](https://github.com/10x-Engineers/riscv-dbg-vip/issues/149) — inherited from pulp upstream; no matching issue in `pulp-platform/riscv-dbg` as of 2026-09-16
**Component:** `riscv-dbg` `src/dm_csrs.sv:513` (`sbcs_d = sbcs;`) vs the fixed-field block at `:610-618`
**Severity:** low — a spec deviation a debugger is unlikely to trip over, but a conformance failure

```systemverilog
513:    sbcs_d = sbcs;                     // whole written word, reserved field included
...
610:    sbcs_d.sbversion = 3'd1;           // fixed fields are re-forced here --
                                           // zero0 [28:23] is not among them
```

A write to `sbcs` copies the whole word into `sbcs_d`, and the later block that
re-forces the fixed fields does not include `zero0`, so whatever the debugger
wrote to bits 28:23 is stored and read back. The spec defines that field as 0.

Measured, `TC-DMC-007` in `dm_corners_uvm`:

```
DMI  WRITE sbcs data=0xffffffff
DMI  READ  sbcs data=0x3f978808      bits [28:23] = 0x3f, expected 0
```

**Inherited from pulp upstream, not introduced by PR #4**: Ibex's vendored copy
(`ibex-demo-system/vendor/pulp_riscv_dbg/src/dm_csrs.sv:457`) has the same
assignment and also never clears `sbcs_d.zero0`, while it does clear
`dmcontrol_d.zero0` and `abstractauto_d.zero0`.

**Found by toggle coverage.** `sbcs_q.zero0` was the only reserved field in
`dm_csrs` whose register bits were listed as *toggleable but untoggled* rather
than constant, which is what prompted writing all-ones to it. The reference
model does not catch it: `predict_mask()` compares `sbcs` only over the fields
it predicts, so reserved bits were checked by nobody until this step.

**Same shape as RTL-002 and RTL-005** — the fixed-field block in the same
`always_comb` decides what a write can change, and this time it misses a field.

---

## RTL-007 — `haltsum1`–`haltsum3` read X on a single-hart DM

**Status:** filed · [`#150`](https://github.com/10x-Engineers/riscv-dbg-vip/issues/150) — introduced by 10x PR #4 (`17e912c`), whose repository has issues disabled
**Component:** `riscv-dbg` `src/dm_csrs.sv:110-126` (`gen_haltsum0_single`) vs `:129-170`
**Severity:** low — the registers are optional below 33 harts, but a read must not return X

```systemverilog
110:  if (NrHarts == 1) begin : gen_haltsum0_single
112:      haltsum0 = {31'b0, halted_i[0]};   // halted / halted_reshaped0 never assigned
...
137:      halted_flat1[k] = |halted_reshaped0[k];   // haltsum1..3 are built from it
```

The single-hart shortcut for `haltsum0` skips the block that fills `halted` and
`halted_reshaped0`, but the `haltsum1`, `haltsum2` and `haltsum3` reduction trees
still read `halted_reshaped0`. With `NrHarts == 1` it is never driven, so bit 0 of
all three registers is X in simulation and undefined in silicon. Upstream
assigns `halted_reshaped0` unconditionally (Ibex's vendored copy,
`dm_csrs.sv:110`); `git log -L` attributes the generate to `17e912c`, one of
PR #4's commits — the same commit as RTL-002.

Measured, `TC-DMC-008` in `dm_corners_uvm`:

```
DMI  READ  addr=0x13  data=0x0000000X
DMI  READ  addr=0x34  data=0x0000000X
DMI  READ  addr=0x35  data=0x0000000X
```

**It passed a check first.** A step that read these three registers and required
0 passed, because the DPI bridge carried read data in a 2-state `int` and X
arrived in Python as 0. The bridge now sends an X/Z mask beside the value and
the transport refuses such a read, so an undriven register fails the step that
reads it. Found through toggle coverage: `halted_flat1..3` were the only
`haltsum` signals with not one toggle, including bit 0.

---

## RTL-008 — `dmstatus` reads X for a nonexistent hart

**Status:** filed · [`#151`](https://github.com/10x-Engineers/riscv-dbg-vip/issues/151) — the indexing is in PR #4's "#520" change; related to, but not the same as, RTL-003 (#130)
**Component:** `riscv-dbg` `src/dm_csrs.sv:255` vs `:306-320`
**Severity:** low — a debugger enumerating harts gets an undefined answer

```systemverilog
191:  logic [NrHarts-1:0] unavailable_effective;              // one bit with one hart
306:    dmstatus.allunavail = unavailable_effective[selected_hart];
319:    dmstatus.allrunning = ~halted_aligned[selected_hart] & ~unavailable_effective[selected_hart];
```

`unavailable_effective` is `NrHarts` wide, but `dmstatus` indexes it with
`selected_hart`, which ranges over `2**HartSelLen` entries. Selecting a hart that
does not exist indexes past the end, so `allunavail`/`anyunavail` and
`allrunning`/`anyrunning` (bits 13:10) are X. The `_aligned` vectors next to it
are padded to `NrHartsAligned` for exactly this reason; this one is not. The
lines carry PR #4's "new version 1.0 #520" comments.

Measured, `TC-DMC-001` in `dm_corners_uvm`, `hartsel`=1:

```
DMI read of 0x11 returned X/Z in bits 0x00003c00: 0x0080XX83
```

RTL-003 describes the same bits reading 1 for a nonexistent hart, from the
zero-filled aligned slot upstream. On this build they are X instead. Until the
bridge carried an X mask, reads went through a 2-state `int`, so neither value
was visible exactly; the X is what the RTL actually produces here.

---

## RTL-009 — `dtmcs.dmihardreset` is not implemented

**Status:** filed · [`#152`](https://github.com/10x-Engineers/riscv-dbg-vip/issues/152) — this fork's DTM predates upstream's support; the newer pulp copy Ibex vendors implements it
**Component:** `riscv-dbg` `src/dmi_jtag_tap.sv:149-160`, `src/dmi_jtag.sv`
**Severity:** medium — the debugger's documented way to abandon a stuck DMI transaction does nothing

The spec defines `dmihardreset` as a hard reset of the DTM that forgets any
outstanding DMI transaction and returns its registers to their reset values.
In this DTM the bit is shifted into `dtmcs` and cleared again at the next
capture, and nothing reads it: `dmi_jtag` acts only on `dmireset`. The newer
upstream copy vendored by Ibex has it — `dmi_clear = jtag_dmi_clear ||
(dtmcs_select && update && dtmcs_q.dmihardreset)` (`dmi_jtag.sv:63`), feeding a
clearable CDC.

Measured, `TC-DTM-012` in `dmi_error_uvm`: busy provoked (scans 0/3/3),
`dmistat`=3, `dmihardreset` written, `dmistat` still 3.

**It passed a check first.** The previous `TC-DTM-012` wrote `dmihardreset`
with no error pending and required `dmistat`=0 afterwards, which a DTM that
ignores the bit satisfies. Found while auditing what the coverage closure had
actually proven.

---

## Observations that are NOT RTL defects

Recorded because each cost time to diagnose and would otherwise be re-diagnosed.

**An SBA transfer started under `ndmreset` may never complete.** The CVA6
testharness resets the AXI crossbar with `ndmreset_n`
(`ariane_testharness.sv:572`) but the DM's AXI master with power-on reset only
(`:350`). While `ndmreset` is held the transfer cannot finish, which is what
`dm_corners` uses to hold `sbbusy` deliberately. After release it depends on
where the request was when the crossbar went into reset: in three of four runs
it was lost and `sbbusy` stayed 1 until power-on reset; in one it completed. That
is an integration property of this testharness, not of the DM, and the spec
does not require a system bus access to survive `ndmreset`. `dm_corners` runs it
last and checks only what the DM owes either way: `sbcs` stays consistent with
`sbbusy`, and `dmactive=0` clears `sbbusyerror`.

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
