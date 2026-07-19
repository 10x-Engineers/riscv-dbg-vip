# DM Core Cluster — CVA6 Results (2026-07-17)

Slice: dmcontrol/dmstatus run control (`run_control`, `reset_control`,
`halt_on_reset`, `dm_activation`, `hart_selection` — 23 TC-IDs, see
`testplans/riscv_debug_testplan.md`). Recorded, not fixed — per policy, no RTL
was modified in response to anything below.

DUT: CVA6 (`integration_with_cva6/cva6_sim`), Questa Sim-64 2021.2_1, `make
soc_test`. Both new SV assertion tiers (`dmi_assertions.sv` protocol,
`dm_csrs_assertions.sv` register) and the coverage subscriber
(`covergroups.sv`) were live and bound for every run below — this is the first
time any of this session's SV deliverables ran against real RTL rather than a
controlled proof script.

## Summary

| Scenario | Python-mock (`make static`) | CVA6 sim | Notes |
|---|---|---|---|
| `run_control` | 7/7 pass | **2/9 steps, then BLOCKED** | DUT RTL bug, root-caused below — not a stimulus/kit defect |
| `dm_activation` | 2/2 pass | **3/3 pass, 0 errors** | Clean end-to-end proof the whole new pipeline works on real RTL |
| `reset_control` | 6/6 pass | Not run this session | `TC-RST-002` calls `dm.halt()` — expected to hit the same blocker; `TC-RST-001` alone likely would not (no `halt()` call) |
| `halt_on_reset` | 5/5 pass | Not run this session | Sequence never calls `dm.halt()`/`dm.resume()` — plausible candidate for a clean run, not yet verified |
| `hart_selection` | 3/3 pass | Not run this session | Sequence never calls `dm.halt()`/`dm.resume()` — plausible candidate for a clean run, not yet verified |
| Ibex baseline | — | Not run this session | Deferred; CVA6 gave a root-caused, non-generic failure, so the fallback's main purpose (a clean comparison point) was already partially served by the `dm_activation` pass |

Pytest-side numbers ("Python-mock") are `make static`'s per-scenario TC-ID
counts, all green (54/54 total suite). Full log excerpts referenced below,
originals at `sim_outputs/soc_test_*.log` in `cva6_sim/` and mirrored under the
session scratchpad.

## `run_control` on CVA6 — BLOCKED, root cause identified

**Command:** `make -C integration_with_cva6/cva6_sim soc_test CFG_FILE=configs/run_control_uvm.json`

**Result:** `Session complete - 2/9 passed (7 failed)`. Steps 01 (pre-activation
dmstatus read) and 02 (DM activation) passed. Step 03 (`TC-RC-001`, halt
request) is where the run actually died; steps 04-09 all fail with the socket
already closed, purely as a cascade.

**Root cause — a genuine zero-delay combinational loop in the DUT itself, not
in any of this project's code:**

```
#############  Autofindloop Analysis  ###############
#############  Loop found at time 7785 ns ###############
#   Active process: /tb_top_soc/dut/i_dm_top/i_dm_mem/#IMPLICIT-WIRE(cmdbusy_o)#49 @ sub-iteration 0
#     Source: CVA6-fork/corev_apu/riscv-dbg/src/dm_top.sv:191
#     Assigning reg to (val=0)
#   Active process: /tb_top_soc/dut/i_dm_top/i_dm_mem/#ASSIGN#114 @ sub-iteration 1
#     Source: CVA6-fork/corev_apu/riscv-dbg/src/dm_top.sv:191
#   Active process: /tb_top_soc/dut/i_dm_top/i_dm_mem/#IMPLICIT-WIRE(cmdbusy_o)#49 @ sub-iteration 2
#     Source: CVA6-fork/corev_apu/riscv-dbg/src/dm_top.sv:191
#     Assigning reg to (val=0)
################# END OF LOOP #################
# ** Error (suppressible): (vsim-3601) Iteration limit 200000000 reached at time 7785 ns.
```

`dm.halt()`'s poll loop (write `haltreq=1`, then repeatedly read `dmstatus`
until `allhalted`) is what triggers it — the DUT's `cmdbusy_o` signal in
`dm_top.sv:191` (PULP `riscv-dbg`, as vendored into `CVA6-fork`) oscillates
within a single time step under this condition, hits Questa's 200,000,000
iteration limit, and the simulator issues `quit -f`. That is what closes the
Python↔Questa DPI socket, producing every subsequent
`TransportError: UVMTransport: socket closed by remote` /
`BrokenPipeError` in the log — a cascade, not 7 independent failures. This
reproduces the previously-documented "known CVA6 convergence issue"
(`VERIFICATION_STRATEGY.md`/earlier session notes referenced it only as
"vsim-3601 iteration limit, socket closed mid-halt" with no root cause) — this
run pins it to an exact file, line, and signal for the first time.

**The register-tier SVA fired correctly, live, during the same window** —
independent confirmation of a real spec-conformance bug, not just the earlier
isolated proof script:

```
# ** Error: [DM-CSRS-SVA] FINDING: dmcontrol.haltreq (WARZ) reads back non-zero -- spec #3.14.2
#    Time: 7135 ns ... Scope: tb_top_soc.dut.i_dm_top.i_dm_csrs.u_dm_csrs_assertions.a_readzero_haltreq
```

Fired 65 times, once every 10ns from t=7135ns to t=7775ns — i.e. on every
`dmstatus` poll cycle while `haltreq` was held asserted, exactly matching the
finding the assertions agent originally proved in a controlled script. Seeing
it fire unprompted in a live Questa run, under real DUT timing, is stronger
evidence than the controlled proof alone.

**Per policy: no RTL was touched.** `dm_top.sv` was not modified, and no sim
parameters (iteration limit, `-novopt`, etc.) were changed beyond what already
shipped in the Makefile.

## `dm_activation` on CVA6 — clean pass, 0 errors

**Command:** `make -C integration_with_cva6/cva6_sim soc_test CFG_FILE=configs/dm_activation_uvm.json`

**Result:** `Session complete - 3/3 passed`. `UVM_ERROR: 0`, `UVM_FATAL: 0`,
clean `$finish`, 20s elapsed. `[SCB] Checked=18 Errors=0`.

This sequence never calls `dm.halt()`/`dm.resume()` (only `dmcontrol.dmactive`
writes and `dmstatus`/`dmcontrol` reads), so it does not exercise the
`dm_top.sv:191` path above. This is the clean end-to-end proof that
everything built this session — the Python golden model, the observer hook,
both coverage substrates, both assertion tiers, and the stimulus sequences —
actually functions correctly against live Questa RTL, not only against the
mock.

**Confirms a previously-*predicted*, now *observed*, VIP gap:** the coverage
subscriber printed real numbers from the live run —

```
[DBG_COV] run-control coverage: dmi_access=75.00% dmcontrol_write=44.30% dmstatus_read=0.00% hart_transition=0.00%
```

`dmstatus_read=0.00%` despite `dmstatus` being read four times in this
sequence (once by `activate()`, once each by `TC-DMA-001`/`TC-DMA-002`'s
status checks). This is the exact consequence the coverpoints agent predicted
from static analysis of `jtag_monitor.sv` (it never samples TDO, so
`dmi_rdata`/`dmi_status` are permanently zero on the SV side) — now confirmed
against a real simulation instead of only inferred from reading the monitor's
source. `hart_transition=0.00%` is expected here: this scenario never touches
`haltreq`/`resumereq`, so no hart-state-transition bin should be hit.

## What this run does and doesn't prove

- **Proves:** the whole new pipeline (model → coverage → assertions →
  stimulus → regression, in both Python and SystemVerilog) is not just
  internally consistent against a mock — it runs, compiles, binds, and
  produces correct live results against real CVA6 RTL over the DPI/UVM
  transport.
- **Proves:** the register-tier SVA finds a real spec-conformance bug live,
  matching the controlled proof.
- **Proves:** the `jtag_monitor.sv` TDO gap is a live defect with an observable
  consequence (0% dmstatus coverage on the SV side), not a theoretical one.
- **Does not prove:** anything about `reset_control`/`halt_on_reset`/
  `hart_selection` on CVA6 — those were not run this session. `halt_on_reset`
  and `hart_selection` are plausible candidates for a clean pass (neither
  calls `dm.halt()`/`dm.resume()`); `reset_control` will very likely reproduce
  the same `dm_top.sv:191` blocker at `TC-RST-002` specifically, since that's
  the only step in that sequence calling `dm.halt()`.
- **Does not prove:** anything about Ibex. The fallback baseline described in
  the roadmap was not run this session — `dm_activation`'s clean CVA6 pass
  already supplies a "does the pipeline work at all" data point, which was the
  fallback's main purpose; a true cross-platform comparison is still open.

## Next steps (not done this session)

1. Run `reset_ctrl`, `halt_on_reset`, `hart_selection` on CVA6 to confirm/refute
   the predictions above.
2. Run the same scenarios against Ibex for the cross-platform comparison the
   project's portability thesis depends on.
3. File the `dm_top.sv:191` zero-delay-loop bug and the `dmcontrol.haltreq`
   WARZ violation as tracked findings against the pinned PULP `riscv-dbg`
   version in `CVA6-fork` — both are now precisely located, not just observed.
4. Fix `jtag_monitor.sv`'s TDO-sampling gap (flagged, not yet actioned per
   earlier discussion of its blast radius on the passing Ibex regression).
