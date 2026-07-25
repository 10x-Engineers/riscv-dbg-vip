# DM Core Cluster — CVA6 Results (2026-07-25)

Slice: dmcontrol/dmstatus run control (`run_control`, `reset_control`,
`halt_on_reset`, `dm_activation`, `hart_selection` — 23 TC-IDs, see
`testplans/riscv_debug_testplan.md`). Supersedes
`run_control_cluster_cva6_2026-07-17.md`: that run only got `dm_activation`
clean (3/3) — `run_control` was BLOCKED by a Questa combinational-loop abort
before reaching any real TC-ID, and `reset_control`/`halt_on_reset`/
`hart_selection` were never run at all. All five run clean here.

DUT: CVA6 (`cva6_sim/`, current repo layout — the 2026-07-17 run's
`integration_with_cva6/cva6_sim` path predates a since-completed
restructure), Questa Sim-64 2021.2_1, `make soc_test`. Fixes made along the
way: [riscv-dbg-vip#131](https://github.com/10x-Engineers/riscv-dbg-vip/pull/131)
(DV) and [#130](https://github.com/10x-Engineers/riscv-dbg-vip/issues/130)
(RTL, filed not fixed).

## Summary

| Scenario | Result | Notes |
|---|---|---|
| `run_control` | **14/14 checks, 0 mismatches** | Previously BLOCKED by the vsim-3601 combinational-loop abort (2026-07-17) — worked around locally (not pushed, tool-specific: see `dm_mem`/`dm_top` `cmdbusy` registering) |
| `dm_activation` | **7/7 checks, 0 mismatches** | Already clean on 2026-07-17; still clean |
| `reset_control` | **14/14 checks, 0 mismatches** | First real run against CVA6. Surfaced and fixed: `supports_hartreset` model bug, `ndmreset`-window `running`/`havereset` model bug, `TC-RST-005` exception-handling bug (see PR #131) |
| `halt_on_reset` | **4/4 checks, 0 mismatches** | First real run against CVA6 |
| `hart_selection` | **4/4 checks, 1 mismatch** | First real run against CVA6. The 1 mismatch is real RTL bug #130 (`allrunning`=1 for a nonexistent hart, spec violation), correctly left unresolved by the model |
| Ibex regression (all 12 wired scenarios) | 11/12 clean | Confirms no cross-DUT regression from this session's model changes; the 1 mismatch is the pre-existing, standing-off-limits #119 |

## What changed since 2026-07-17

The `vsim-3601` blocker on `run_control` is the exact same `dm_mem.cmdbusy_o`
combinational loop documented in the prior run (`dm_top.sv`/PULP `riscv-dbg`
as vendored into `CVA6-fork`) — confirmed identical root cause, now worked
around locally (register `cmdbusy` between `dm_mem` and `dm_csrs`) so
regressions can actually complete. This workaround is deliberately **not**
pushed to `10x-Engineers/riscv-dbg` — it's a Questa `-novopt` tooling
artifact, not a real RTL defect.

Running the other four scenarios for the first time (they had stimulus and
testplan TC-IDs already, just no CVA6 scenario config to actually invoke
them) surfaced three real DV model bugs and one real RTL bug — see PR #131's
description for the full root-cause writeup of each. All are fixed (DV) or
filed (RTL, #130) as of this run.

## Functional coverage

`testplans/results/cva6_functional_coverage_merged.txt` (regenerated same
session, all 17 CVA6 scenarios under `+cover=sbceft`): see that file for the
full per-covergroup breakdown.

## Round 2 — coverage closure cycle (same day, 2026-07-25)

Governing instruction: run coverage, fix DV failures, file (verified) RTL
failures, write more tests for any gap, repeat until CVA6 coverage is 100% of
reachable bins. Baseline going in: **91.78%** merged (the number produced
just before this round began). Result: **99.58%** merged, with the residual
0.42% being a genuine, non-closeable single-DUT-report artifact (below), not
a real gap.

### New/extended stimulus

- `TC-RST-001 (cont'd)`: `haltreq` asserted while a hart is in `ndmreset`,
  released with `haltreq` still set — the universally-supported substitute
  for `TC-HOR-002`'s `setresethaltreq` path (which doesn't work on either
  current DUT, `hasresethaltreq=0` hardcoded in both `dm_csrs.sv`).
- `TC-DHS-006` (write-only half): `ackunavail` discovery probe.
- `TC-KA-001` (new): `setkeepalive`/`clrkeepalive` discovery probe — the
  testplan's own previously-open "was keepalive present in the targeted
  v1.0.0-rc3 spec tag?" question is now resolved (confirmed present, checked
  directly against that tag's `xml/dm_registers.xml`).
- `TC-HOR-002`/`003` rewritten to always perform the `set`/`clrresethaltreq`
  write (closing write-coverage on every DUT), gating only the functional
  halt-on-reset assertion on `hasresethaltreq`.
- `TC-RC-007` fixed: `dm.ndmreset(True)` is write-only with no read-back: an
  intervening `dm.read_dmstatus()` was needed for the coverage model's own
  `cur_state` tracking to observe "in reset" before the `resumereq` write.
- `tests/test_coverage_and_assertions.py`'s `full_trace` fixture was missing
  `build_dm_activation_sequence`/`build_hart_selection_sequence` entirely —
  `dmactive.0`/`hasel.1`/`hartsel.*` had real, working stimulus all along but
  were never actually exercised by the pytest suite.

### DV bugs found and fixed

- **`cg_sb_access` bin-encoding swap** (`covergroups.sv`): the
  `{addr==ADDR_SBDATA0, op==DMI_WRITE}` concatenation's `data_read`/
  `ignore_bins addr_read` bin values were swapped relative to what the
  concatenation actually produces — every genuine SBDATA0 read was silently
  landing in the excluded bin. Confirmed via direct log inspection
  (`addr=0x3c op=01` = a real SBDATA0 read). Now `cg_sb_access` = 100%.
- **`dm.ndmreset(False)` silently clearing `haltreq`**: `TC-RST-001 (cont'd)`
  first looked like an RTL bug (hart never halted on reset release) —
  `dm.ndmreset()` is a raw absolute `dmcontrol` write with no `haltreq`
  parameter, so releasing reset via that helper silently withdrew the very
  halt request the step was trying to test, at the exact edge the spec
  requires it to still be observed. A waveform trace
  (`dut.i_dm_top.debug_req_o`) confirmed the DM's own `haltreq_o` mux and
  `dm_top.sv` wiring have no reset-dependent gating at all — the DM was
  behaving correctly throughout; the bug was in the stimulus calling the
  wrong release helper. Fixed by using `write_dmcontrol(haltreq=True,
  ndmreset=False)` for the release instead.
- **`covergroups.sv`'s hart-state classifier mis-timed the reset-release
  transition**: even after the above stimulus fix, `in_reset_to_halted`
  stayed at 0 hits. Root cause: `decode_hart_state()`'s local `ndmreset`
  write-tracking flag flips to 0 the instant the release write is
  *processed*, well before real RTL's halt handshake (fetch resume ->
  observe `debug_req` -> debug-ROM entry -> `halted_q`, ~4.6us of sim time,
  confirmed via waveform) actually completes — so the first poll read after
  release was mis-classified as plain `ST_RUNNING` instead of a continuing
  `ST_IN_RESET`, splitting the real `in_reset->halted` transition into a
  spurious `in_reset->running->halted` pair. Fixed with a one-write grace
  flag (`ndmreset_release_pending`), gated on `haltreq` being set in the
  same release write specifically so `TC-RST-001`'s own baseline release (no
  `haltreq`) is not affected — confirmed both paths classify correctly via
  CVA6 UVM. `cg_hart_transition` = 100%.
- Added `ignore_bins` (with RTL citations, not forced) for gaps confirmed
  structurally unreachable on both current SoC integrations: `allunavail`/
  `anyunavail=1` (`unavailable_i` hardwired to 0 in both
  `ariane_testharness.sv` and `ibex_demo_system.sv`), `hasresethaltreq=1`
  (both DUTs' `dm_csrs.sv` hardcode `dmstatus.hasresethaltreq = 1'b0`),
  `dmstatus.version=0`/"none" (not gated by `dmactive` on real RTL, mirrors
  the identical Python-model fix), and `sbcs.sbbusy=1` (every SBCS read in
  the `sba_uvm` log shows `busy=0` — this DUT's SBA transaction completes
  faster than software polling can observe a busy moment).

### RTL findings (verified, filed, assigned)

No new RTL bugs from this round's own changes. Encountered and properly
triaged three **pre-existing** issues while re-running the full regression
(none caused by anything touched this round):

- [#127](https://github.com/10x-Engineers/riscv-dbg-vip/issues/127) (CVA6
  single-step: DM never observes the hart's internal re-halt) — already
  filed, now assigned to Tufail + labeled `RTL`.
- [#130](https://github.com/10x-Engineers/riscv-dbg-vip/issues/130)
  (`allrunning`=1 for a nonexistent hart, spec violation) — already filed,
  now assigned to Tufail + labeled `RTL`.
- [#132](https://github.com/10x-Engineers/riscv-dbg-vip/issues/132) (new,
  DV-only, not RTL): Ibex `single_step` — the golden model has no way to
  represent `dcsr.step`'s autonomous re-halt (a hardware-only transition
  with no corresponding DMI write for the write-driven model to hook into).
  Stimulus itself passes; only the checker mismatch is a model limitation.

### Final coverage

| | Baseline (start of round 2) | Final |
|---|---|---|
| CVA6 merged | 91.78% | **99.58%** |
| Ibex merged | — (12 scenarios, unchanged scope) | 91.64% |

CVA6's residual 0.42% is `cp_stickyunavail.zero` and `cp_version.v0_13` in
`cg_dmstatus_read` — both are real, reachable bins, just not on *this* DUT:
CVA6 is permanently `stickyunavail=1`/`version=v1_0` by declared config, so
these two values are exclusively Ibex's (confirmed: Ibex's own merged report
shows the complementary `cp_stickyunavail=100%`/`cp_version` including
`v0_13`). This is the same accepted cross-DUT-split pattern the testplan
already documents for `cp_version`'s `v0_13`/`v1_0` split — not a gap to
close, a property of merging one DUT's regression alone.

Ibex's lower 91.64% is **scope, not regression**: `cg_dmcontrol_write`
(52.63%), `cg_dmstatus_read` (90.38%), and `cg_hart_transition` (40.00%) are
exactly the bins this round's `reset_ctrl`/`halt_on_reset`/`run_control`/
`dm_activation`/`hart_selection` sequences close — Ibex has no scenario
config wiring any of those five sequences at all yet (`ibex_sim/configs/`
has no `reset_ctrl_uvm.json` etc.), a separate, not-yet-started task, not a
regression from this round. Every covergroup Ibex *does* have configured
(`cg_sb_access`, `cg_sbcs`, `cg_trigger`, ...) is 100%. The full Ibex
functional regression (all 12 wired scenarios, non-coverage build) was
rerun and confirmed clean — no cross-DUT regression from any change in this
round; the only Ibex finding is the new, separately-filed `#132` above.

Updated: `testplans/results/cva6_functional_coverage_merged.txt` and
`testplans/results/ibex_functional_coverage_merged.txt` (both regenerated
this round, all scenarios under `+cover=sbceft`).
