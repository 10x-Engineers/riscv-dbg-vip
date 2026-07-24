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
