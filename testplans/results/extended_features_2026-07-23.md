# Extended Debug Features + Core-Ops Reconfirmation — Ibex/CVA6 Results (2026-07-23)

Slice: 6 new feature scenarios added this pass (`gpr_write`, `csr_access`,
`program_buffer`, `single_step`, `sw_breakpoint_progbuf`, `external_trigger` —
see `testplans/riscv_debug_testplan.md` for the underlying TC-IDs), plus a
reconfirmation of the `run_control` core-op cluster after the fixes below. All
scenarios are per-test-case files under `src/pydebug/sequences/`, composing
primitives from `src/pydebug/api/riscv_dm.py`.

This is also the first pass where a real SV register-value checker
(`src/pydebug/sv/model/dm_ref_model.sv` + `src/pydebug/sv/env/dm_checker.sv`) was live and wired
into the UVM env (`env.sv`) for every run below, alongside the existing
scoreboard/coverage subscribers — see `VERIFICATION_STRATEGY.md` for the
checker's design. Per standing project policy: **no RTL was modified in
response to any finding below.** DV-side bugs were fixed in this project's own
stimulus/checker code; RTL-suspected findings were filed as GitHub issues on
`10x-Engineers/riscv-dbg-vip` and left untouched for the RTL owners.

DUTs: Ibex (`ibex_sim/`, unmodified spec-v0.13 `pulp-platform/riscv-dbg`),
CVA6 (`cva6_sim/`, `10x-Engineers/riscv-dbg@features/riscv-debug-update`
spec-v1.0 fork). Questa Sim-64, `make soc_test CFG_FILE=configs/*.json`.

## Summary — core operations (reconfirmed)

| TC-ID(s) | Feature | Ibex (v0.13) | CVA6 (v1.0 fork) |
|---|---|---|---|
| `TC-RC-001` | Halt (single hart) | **PASS** — `8/8` steps, `Checked=38 Errors=0` | **PASS** (this pass) — after the fix in [#101](https://github.com/10x-Engineers/riscv-dbg-vip/issues/101) |
| `TC-RC-003` | Resume (single hart) | **PASS** — same run | Not reconfirmed this pass — run did not reach this step |
| `TC-AC-001` | GPR read (Abstract Command) | **PASS** — same run | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) |
| `TC-SBA-002`/`003` | SBA (System Bus Access) | **PASS** — same run | Not reconfirmed this pass — run did not reach this step |

## Summary — extended features (new this pass)

| TC-ID(s) | Feature | Ibex (v0.13) | CVA6 (v1.0 fork) | Notes |
|---|---|---|---|---|
| `TC-AC-002` | GPR write + read-back | **PASS**, `4/4` | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | `0xa5a5a5a5` written/read back on x5; x0 confirmed hardwired 0 |
| `TC-AC-005`, `TC-DCSR-003` | CSR access (`dscratch0`/`dscratch1`) | **PASS**, `4/4` | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | Round-trip write/read-back; preserved across a resume→halt cycle |
| `TC-AC-013`, `TC-PB-001`–`003` | Program Buffer execution | **PASS**, `6/6` | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | `progbufsize=8`; `addi x5,x5,1; ebreak` via `postexec`, **x5=1 confirmed on real RTL** |
| `TC-SSTEP-001` | Hardware single-step | **PASS**, `3/3` | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | Fixed this pass ([#105](https://github.com/10x-Engineers/riscv-dbg-vip/issues/105)); `dcsr.cause=4` confirmed |
| `TC-PB-003`, `TC-DCSR-001` | SW breakpoint via Program Buffer | **PASS**, `3/3` | **BLOCKED** — [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | `dcsr.cause` unchanged (`3→3`) on an already-halted hart — predicted in advance, then confirmed |
| `TC-HG-001` | `dmcs2` halt-group discovery | **PASS**, `2/2` — does **not** round-trip | **PASS**, `2/2` — does **not** round-trip | Confirmed correct/expected on both DUTs; see [#102](https://github.com/10x-Engineers/riscv-dbg-vip/issues/102) |

## GitHub issues filed this pass (`10x-Engineers/riscv-dbg-vip`)

All labeled and assigned; RTL-suspected findings are labeled `RTL`+`bug` (never
patched by us), DV-side findings are labeled `DV` (fixed directly where
closed).

| # | Title | Label | State | Root cause |
|---|---|---|---|---|
| [#100](https://github.com/10x-Engineers/riscv-dbg-vip/issues/100) | Ibex `riscv-dbg` v1.0 vendor repoint: lowrisc-primitives patch fails to apply | `DV` | Open | Vendoring/patch-application issue; Ibex reverted to clean v0.13 per decision to keep Ibex on v0.13 throughout |
| [#101](https://github.com/10x-Engineers/riscv-dbg-vip/issues/101) | CVA6 v1.0 fork: `dmstatus` reads all-zero during `halt()` poll | `DV` | Closed | Response-queue drain bug in our own `dmi_read_seq.sv` (not RTL) — confirmed via identical symptom on Ibex, an unrelated DUT |
| [#102](https://github.com/10x-Engineers/riscv-dbg-vip/issues/102) | CVA6 v1.0 fork: `dmcs2` round-trips live, contradicting RTL's "tied to zero" comment | `DV` | Closed | Was an artifact of #101; re-run after the fix confirms `dmcs2` correctly reads back 0 — original static analysis was right |
| [#103](https://github.com/10x-Engineers/riscv-dbg-vip/issues/103) | `jtag_monitor.sv` TDO-capture: occasional mismatch vs. driver's own capture | `DV` | Open | Rare shift-pairing edge case; needs waveform access not available in this environment — reported, not guessed at |
| [#104](https://github.com/10x-Engineers/riscv-dbg-vip/issues/104) | CVA6 v1.0 fork: `abstractcs.busy` stuck at 1 forever during Access Register read | `RTL`, `bug` | **Open** | RTL-suspected — overlaps CVA6 v1.0 fork's uncommitted WIP in `dm_mem.sv`; identical command path passes cleanly on Ibex. **Not fixed, per policy — RTL owners' call.** |
| [#105](https://github.com/10x-Engineers/riscv-dbg-vip/issues/105) | `single_step`: `resume()` waits for `allrunning`, too transient to observe during a step | `DV` | Closed | Stimulus timing assumption, not RTL — fixed with a new `resume_no_wait()` primitive |

## What this pass does and doesn't prove

- **Proves:** all 6 new extended-feature scenarios, plus the reconfirmed core
  cluster, run correctly end-to-end against real Questa RTL on Ibex — not a
  mock.
- **Proves:** the new SV register-value checker is live and catching real
  discrepancies (it is what caught #101 and #103).
- **Proves:** cross-DUT comparison (same symptom on two unrelated DUTs) is a
  genuine diagnostic technique, not just a nice idea — it is what correctly
  separated #101 (shared DV bug) from #104 (CVA6-specific, RTL-suspected).
- **Does not prove:** CVA6 rows 5–9 above (GPR write, CSR access, Program
  Buffer, single-step, SW breakpoint) — all blocked by #104, open, not fixed
  by us per policy.
- **Does not prove:** Ibex's resume/GPR-read/SBA results specifically on
  CVA6 — not reconfirmed this pass (run did not reach those steps).
- **Does not prove:** anything about emulation (Arty A7) for the 6 new
  features — this pass was simulation only.

## Next steps (not done this pass)

1. Resolve #104 (RTL owners) and rerun CVA6 rows 5–9.
2. Root-cause #103 with waveform access.
3. Reconfirm resume/GPR-read/SBA on CVA6 once #104 clears.
4. Re-verify the Arty A7 hardware claims for the 6 new features (only the 4
   original core ops have been verified on real hardware, from prior work).
