# RISC-V Debug Compliance Framework — Roadmap

This is a living planning document, edited in place as scope, status, or
findings change — same discipline as `INTEGRATION_GUIDE.md` and
`PORTING_DELTA_REPORT.md` in this repo. It is public (this repo is
`10x-Engineers/riscv-dbg-vip`, public, default branch `master`): nothing here
should be sensitive — no customer names, no pricing, no internal commitments.

## Context

`pydebug` already does one half of what a RISC-V Debug compliance framework
needs: **portable stimulus**. A transport-agnostic Python library
(`src/pydebug/api/`) drives a real DMI-speaking core through a mock, a Questa
UVM simulation, or real hardware over OpenOCD, with the same sequences
unchanged across all three. That thesis is proven, not aspirational — CVA6 and
Ibex both have working, previously-run Questa simulations under this repo.

What was missing was the other half: **a golden reference model, functional
coverage, and architectural assertions** — the machinery that turns "we ran
some stimulus" into "we know what the spec requires and can prove whether the
DUT does it." This roadmap exists because that other half has now been started
and *works*: one vertical slice (DM run control — halt/resume/reset/
halt-on-reset) went end-to-end through model → coverage → assertions →
regression tiering, in Python and SystemVerilog, and immediately found two real
spec-conformance bugs and two bugs in the project's own verification IP. The
question this document answers is how that same pipeline replicates across the
rest of the RISC-V Debug specification, and what the finished thing is *for*.

**How the estimates below are grounded:** this repo's `testplans/
riscv_debug_testplan.md` already enumerates the spec's structure precisely —
19 TC-ID rows exist today across 6 subsections, out of a 17-feature-area
traceability table where only 3 CAT2 rows (Halt/Resume, Reset, Halt-on-Reset)
have any TC-IDs at all. The one completed slice's actual build telemetry is
real, not estimated: the coverage sub-agent ran 25 min wall-clock (166,905
tokens, 59 tool calls) and the assertions sub-agent ran 25.3 min wall-clock
(207,315 tokens, 70 tool calls), in parallel, plus additional un-logged time
for the scaffolding, integration, and regression-tier work done directly
rather than by a sub-agent. That is **one data point from one of the
architecturally simpler areas**, and the stimulus/pytest phase for that same
slice was never finished (stopped mid-session) — so it contributes no timing
data at all. Sizing below is relative to that one known point, explicitly
flagged where later areas are structurally harder (more fields, more
cross-extension interaction surface, optional-feature variance across DUTs)
and therefore not simply "the same again."

## What's already done (Milestone 0 — complete)

Not a future milestone — recorded here because it's the pattern every
following milestone reuses, and because a roadmap that hides finished work
undersells where the project actually is.

- **Golden reference model** (`src/pydebug/model/`): `registers.py` (field
  definitions traced to the ratified spec's own machine-readable register XML,
  not hand-transcribed), `predictor.py` (an executable `DMPredictor` — write
  in, predicted state/read-back out), `mock_transport.py` (a spec-accurate
  mock backed by the predictor, replacing the ad-hoc canned-value mock the
  test suite used before).
- **Universal observation hook** (`src/pydebug/api/observer.py`):
  `ObservingTransport` wraps any transport and exposes every DMI transaction
  to registered callbacks — the same hook coverage and assertions both key
  off, and it works identically on the mock, a live Questa sim, or real
  hardware, because `RISCVDebug` only ever calls `read`/`write`.
- **Functional coverage**, both substrates: `src/pydebug/model/coverage.py`
  (104 architectural bins for the run-control slice, each un-hit bin
  traceable to a spec clause and a proposed TC-ID, each excluded bin carrying
  a spec-cited reason so exclusions can't silently inflate a percentage) and
  `src/pydebug/sv_kit/covergroups.sv` (bound into the UVM env via a
  `uvm_subscriber` on the existing monitor's analysis port).
- **Architectural assertions**, both substrates: `src/pydebug/model/
  invariants.py` (19 invariants, a "never raises" contract, each backed to
  specific TC-IDs) and two SVA tiers — `src/pydebug/sv_kit/dmi_assertions.sv`
  (protocol tier, reusable, bound to `jtag_if`) and `integration_with_cva6/
  cva6_sim/dm_csrs_assertions.sv` (register tier, DUT-specific, bound to
  CVA6's `dm_csrs` internals at `dut...i_dm_top.i_dm_csrs`).
- **Regression tiering**: `regressions.json` declares a smoke tier (one basic
  test per feature) and a static tier (everything, maximum coverage); markers
  on the tests themselves are authoritative, and `tests/
  test_regression_integrity.py` enforces the policy against the live pytest
  session so a test cannot silently fall out of a tier.
- **The three-agent generation pattern, proven**: a coverpoints agent, an
  assertions agent, and a stimulus agent, each required to *prove* its target
  complete (not just assert it) before reporting. This is what surfaced real
  bugs during construction rather than after: the assertions agent's own
  first-draft SVA had a 1-bit-cast defect that made every DMI property
  vacuously true until it was actually exercised against a forced violation;
  the coverage agent caught and reversed two of its own over-broad exclusions
  rather than let them inflate its completion percentage.

**Findings this one slice already produced** (the actual point of the
exercise — a framework that doesn't find anything isn't worth building):

| Finding | Where |
|---|---|
| `dmcontrol.haltreq`/`resumereq` read back non-zero; spec requires WARZ/W1 fields to read 0 | CVA6 `riscv-dbg` v0.13, found by the register-tier SVA |
| DM presents `haltreq` and `resumereq` to the same hart simultaneously; spec #3.14.2 requires `resumereq` be ignored when `haltreq` is set | CVA6 `riscv-dbg` v0.13 — the exact case TC-RC-005 exists to catch |
| `jtag_monitor.sv` never samples TDO, so `dmi_rdata`/`dmi_status` are permanently zero | This project's own VIP (`src/pydebug/sv_kit/jtag_monitor.sv`) — blocks SV-side `dmstatus` coverage collection until fixed |
| `DMSTATUS_RESET_VAL` uses bits 24/25 for allrunning/anyrunning; spec places them at 11/10 | This project's own VIP (`src/pydebug/sv_kit/dm_defines_pkg.sv:74`) — currently dead code, a latent trap |
| 6 of 16 TC-IDs are legitimately N/A on CVA6 (`hasresethaltreq` and `hartreset` hardwired 0; v0.13 `dmstatus_t` has no `ndmresetpending` field at all) | Verified directly against `CVA6-fork/corev_apu/riscv-dbg/src/dm_csrs.sv` and `dm_pkg.sv`, not assumed |

## The open decision: what is the final product?

This has to be decided before Milestone 7 (packaging), and probably should be
revisited after Milestone 2 once more of the spec surface is covered and the
shape of the framework is easier to judge from real output rather than from
one slice. Presented here as a genuine decision, not resolved unilaterally:

| Option | What ships | Who consumes it | Implication for the roadmap below |
|---|---|---|---|
| **A. Open self-certification suite** | The framework itself, public, runnable by anyone against their own DM RTL via the existing transport swap (mock/UVM-sim/OpenOCD-HW) | Chip/IP teams, directly | Milestones unchanged; Milestone 7 becomes "polish the CLI/report output for a third-party user," not just an internal proof |
| **B. Certification/scoring service** | A report or scorecard 10x-Engineers generates *for* a customer's DUT, using this framework as internal tooling | Customers, via a report, not the tool | Framework can stay rougher at the edges; investment shifts toward the report generator and scoring rubric, less toward external-user CLI ergonomics |
| **C. Licensable reference-model core** | The golden model + coverage/assertion library as standalone IP, with `pydebug` stimulus as one consumer among several (other UVM environments could integrate the model directly) | Other verification teams / EDA-adjacent integration | Changes Milestone 6+ priorities toward decoupling `src/pydebug/model/` from the rest of the package, stable public API, versioning discipline |
| **D. Combination** | Open core (A) with a paid certification layer (B) built on the same engine (C) | Both of the above | Highest total effort; only makes sense once A's core is far enough along to demonstrate the pattern |

Nothing below depends on choosing now — Milestones 1–6 build the same
underlying model/coverage/assertion/stimulus machinery regardless of which
product this becomes. The decision mainly changes Milestone 7's shape and how
much polish the CLI/reporting layer needs.

## Full Plan to Project End — target 2026-08-17

**This target date and the paper-submission milestone were set by Jahanzeb
Khalid / program management, not independently re-derived from timing data.**
The one real velocity data point this project has (M0's model+coverage+
assertions phase, ~25 min wall-clock for two parallel sub-agents, on the
*smallest* cluster) does not extrapolate linearly across the remaining
138 TC-IDs — Sdtrig alone is flagged below as plausibly larger than everything
done so far combined. Where the plan below is aggressive relative to that
known velocity, it's flagged in **Known Risks**, not silently assumed to fit.

Staffing: solo (Jahanzeb Khalid) directing AI agents; no other human
assignees confirmed yet — every release below lists Jahanzeb Khalid as
assignee. Testplan reference: `pydebug/testplans/riscv_debug_testplan.md`
(161 TC-IDs across 25 prefixes, all CAT2 rows populated as of 2026-07-17).

### R1 — Paper validation push (2026-07-17 → 2026-07-22)

**Assignee:** Jahanzeb Khalid. **Goal:** one basic-but-real test per feature
area (not full TC-ID depth — that's R4-R7 below), each run through
simulation → emulation, both interactive and non-interactive modes, plus an
infinite loop test pass, feeding the paper's extended results table.

| Day | Feature areas (testplan prefix) | Tangible output | Status |
|---|---|---|---|
| Jul 17 | Infinite loop test mechanism (new `--loop` mode in `session.py`/`cli.py`, alongside existing `batch`/`interactive`) | Repeats a scenario's session indefinitely/to a large iteration count, reports first-failure-onward | Not started |
| Jul 17 | `RC`/`RST`/`HOR`/`DMA`/`HS` (stimulus already exists) — run on emulation + infinite loop test | Emulation results for the 23 already-stimulated TC-IDs | Not started — `RC` already known-blocked on CVA6 sim (`dm_top.sv:191`), expect same on CVA6 emulation; Ibex is the clean path |
| Jul 18 | `DTM`, `DMI`, discovery cluster (`DHS`/`DIS`/`VER`) — zero model exists today | Basic model + one TC-ID stimulus each, sim + emulation | Not started |
| Jul 19 | `AC` (Abstract Commands), `QA` (Quick Access) | GPR path extends existing partial driver; CSR/Quick-Access new | Not started |
| Jul 20 | `PB` (Program Buffer, **zero driver support today** — highest build-risk day), `AM` (Access Memory), `SBA` | New `api/riscv_dm.py` Program Buffer support; `SBA` reuses the paper's already-proven real-HW path | Not started |
| Jul 21 | `HG`, `AUTH`, `DCSR`/`SSTEP`, `TRIG` | `HG` likely register-round-trip only (dmcs2, per the paper's Finding 3/4, not full causality); `AUTH` likely N/A on both DUTs (verify against RTL); `DCSR`/`SSTEP` reuse the paper's proven single-step/progbuf-breakpoint scenarios; `TRIG` realistically sim-only this cycle (paper: "partial, register-level... not attempted" on emulation) | Not started |
| Jul 22 | Compile all results (sim + emulation + both modes + infinite loop test, per feature); emulation-fail → simulation-reproduce wherever a real-HW run diverges; extend the paper's Table II from 8 → 17 features | Updated paper draft, results appendix | Not started |

**R1 complete when:** every one of the 17 feature areas has at least one
real, spec-traced pass/fail result recorded on simulation, with emulation
results wherever the DUT/board combination supports it, and the paper draft
reflects all of it.

### R2 — Paper review (2026-07-22 → 2026-07-24)

**Assignee:** Jahanzeb Khalid. Two days, per program management's own
stated cadence ("22nd at most, then 2 days for review of the full paper").
Tangible output: reviewed draft with comments resolved.

### R3 — Paper submission (~2026-07-24 → 2026-07-25)

**Assignee:** Jahanzeb Khalid. Tangible output: submitted paper. This is a
named milestone in its own right, not folded into R2, per program
management's explicit instruction ("full paper submission is one of the
milestones").

### R4 — DM Core Cluster + DTM/JTAG, full TC-ID depth

Extends R1's basic tests to full depth for the clusters already partially
proven. Covers testplan prefixes `RC`(7)/`RST`(6)/`HOR`(5)/`DMA`(2)/`HS`(9,
including the hart-array-mask rows R1 doesn't reach) + `DTM`(7)/`DMI`(7) +
discovery `DHS`(6)/`DIS`(4)/`VER`(2) = 55 TC-IDs.

| Task | Tangible output |
|---|---|
| Fix the circular-import trap between `api/riscv_dm.py` and `model/registers.py` if not already resolved | Documented import ordering |
| Testplan back-fill already done this session (Bins/Intentionally-not-tested/Uncertain) — carry to full stimulus | `sequences/*.py` for every TC-ID in scope |
| Fix `jtag_monitor.sv` TDO sampling (blast radius on Ibex sim — needs explicit sign-off before touching) | Unblocks SV-side `dmstatus` coverage |
| Fix `dm_defines_pkg.sv:74` reset-value constant | One-line correction, dead code today |

### R5 — Command Execution Cluster, full TC-ID depth

`AC`(13)/`QA`(4)/`AM`(7)/`PB`(6)/`SBA`(9)/`MID`(1) = 40 TC-IDs. Program
Buffer has zero existing driver support — this is where that gets built out
past R1's basic pass to the full `cmderr`/write-isolation/postexec depth.

### R6 — Multi-Hart & Access Control, full TC-ID depth

`HG`(9)/`AUTH`(6) = 15 TC-IDs. Optional features — R1 already established
whether either DUT implements halt groups/external triggers/authentication
beyond a register round-trip; this release is bounded by that finding, not
by effort. Explicit capability gating per DUT, same N/A-detection discipline
as the rest of this project.

### R7 — Native Debug Mechanisms (Sdext / Sdtrig), full TC-ID depth

`DCSR`(11)/`SSTEP`(6)/`TRIG`(23) = 40 TC-IDs. **The largest single release —
Sdtrig alone has more WARL fields and match-mode combinations than the
entire R4 cluster.** Apply the testplan skill's cross-extension interaction
discipline (A/V/Zcmp/Zicbom/Zicboz/Zicbop/Zicfilp/Zawrs/Smdbltrp/Ssdbltrp) to
whichever extensions the actual DUTs implement, per `TC-TRIG-023`'s existing
scoping.

### R8 — Cross-Cutting Hardening

`COV`(3)/`SVA`(3)/`NEG`(2)/`REG`(3) = 11 TC-IDs, plus aggregate coverage
rollup (`report()` across every area's `DebugCoverageModel`, not per-slice
only) and a structured multi-DUT capability matrix (CVA6 vs. Ibex optional-
feature support, as data, not prose).

### R9 — Full Regression, Coverage Closure, VIP Sign-off (target 2026-08-17)

| Task | Tangible output |
|---|---|
| Full regression (`make static`) green on CVA6 and Ibex | Recorded results, `testplans/results/` |
| 100% functional coverage | Every `DebugCoverageModel` bin closed or in the Intentionally-Not-Tested/Uncertain buckets with a stated reason — **not** a silently-inflated percentage |
| 100% RTL code coverage | **Flagged, not assumed achievable by direct stimulus alone** — see Known Risks below; some RTL lines may be genuinely unreachable via spec-legal DMI sequences (defensive/dead code), which conventionally needs an explicit waiver list, not a claimed 100% |
| FPGA/emulation full-regression pass | Extends R1's per-feature emulation results to the full TC-ID set, wherever board access holds |
| VIP sign-off | Final go/no-go, with residual open items (if any) named explicitly rather than hidden |

## Completion Tracker

| Release | Feature areas / TC-IDs | ETA | Assignee | Status |
|---|---|---|---|---|
| M0 — Foundations | cross-cutting infra (model architecture, observer hook, regression tiers, agent pattern) | Done | Jahanzeb Khalid | **Done** |
| R1 — Paper validation push | 1 basic test × 17 feature areas, sim+emulation+both modes+infinite loop test | 2026-07-22 | Jahanzeb Khalid | Not started |
| R2 — Paper review | — | 2026-07-24 | Jahanzeb Khalid | Not started |
| R3 — Paper submission | — | 2026-07-25 | Jahanzeb Khalid | Not started |
| R4 — DM Core + DTM/JTAG, full depth | `RC`/`RST`/`HOR`/`DMA`/`HS`/`DTM`/`DMI`/`DHS`/`DIS`/`VER` (55 TC-IDs) | TBD — see Known Risks | Jahanzeb Khalid | Not started |
| R5 — Command Execution, full depth | `AC`/`QA`/`AM`/`PB`/`SBA`/`MID` (40 TC-IDs) | TBD | Jahanzeb Khalid | Not started |
| R6 — Multi-Hart/Access Control, full depth | `HG`/`AUTH` (15 TC-IDs) | TBD | Jahanzeb Khalid | Not started |
| R7 — Native Debug Mechanisms, full depth | `DCSR`/`SSTEP`/`TRIG` (40 TC-IDs) — largest release | TBD | Jahanzeb Khalid | Not started |
| R8 — Cross-Cutting Hardening | `COV`/`SVA`/`NEG`/`REG` (11 TC-IDs) | TBD | Jahanzeb Khalid | Not started |
| R9 — Full Regression + Coverage + Sign-off | all 161 TC-IDs, 100% code+functional coverage | 2026-08-17 | Jahanzeb Khalid | Not started |

**R4-R8's ETAs are marked TBD rather than filled with invented dates**: the
window between R3 (2026-07-25) and R9's 2026-08-17 target is 23 days for
138 TC-IDs' full model/coverage/assertion/stimulus depth plus 100%
code+functional coverage closure — a scope this project's own one real
timing data point cannot honestly back-fill into 5 sub-deadlines without
guessing. Recommend fixing R4-R8's individual dates once R1 produces a
second real timing data point (the "basic test per feature" pass gives an
actual per-feature-area effort sample, not just the one from M0/M1).

## Known Risks

- **The 2026-08-17 full-depth + 100%-coverage target is aggressive relative
  to known velocity, and R7 (Sdtrig) is the specific point most likely to
  blow through it.** Sdtrig alone has more WARL fields and match-mode
  combinations than the entire R4 cluster combined, per the sizing flag
  above. Fallback options, not yet decided: (a) sign off R9 with Sdtrig's
  exhaustive depth carried as a named residual open item, (b) extend the
  R7/R9 dates specifically while holding R1-R3's paper dates fixed, (c) scope
  R9's coverage claim to "100% of the P0/P1 TC-IDs" rather than all 161.
  Needs a decision checkpoint after R1 (2026-07-22), once a second real
  timing sample exists.
- **100% RTL code coverage may not be achievable through spec-legal stimulus
  alone.** Defensive/dead code paths in the DUT's own RTL can be
  unreachable via any sequence a real debugger would legally issue. The
  conventional resolution is a documented waiver list (same discipline this
  project already applies to functional-coverage exclusions), not silently
  claiming 100%. Flag any such lines explicitly in R9 rather than force
  coverage through illegal/synthetic stimulus.
- **Model/DUT divergence that is legal on both sides.** Already observed
  once: CVA6 computes `allrunning = ~halted & ~unavailable` so a hart held in
  reset reports `running=1`, while the Python predictor models "neither
  halted nor running" — both conform to spec #3.2. Every later release will
  hit more of these as optional-feature latitude increases (Sdtrig
  especially). Fallback: document the divergence per-DUT rather than
  "fixing" either side, exactly as done for this first instance.
- **Verification-IP bugs, not just DUT bugs.** Two were found in this
  project's own SV kit during M0 (the TDO-sampling gap, the wrong
  reset-value constant). Expect more as coverage/assertions reach into parts
  of the kit that have never had a consumer before. Fallback: the same
  "prove it fires against a forced violation, don't just assert it compiles"
  discipline that caught the assertions agent's own 1-bit-cast bug.
- **Optional-feature variance across DUTs makes "100% coverage" DUT-relative,
  not spec-absolute.** CVA6 already can't exercise 6 of 16 R4-cluster TC-IDs
  because it doesn't implement `hasresethaltreq`/`hartreset`. Every future
  release needs the same RTL-verified (not assumed) N/A-detection gate
  before claiming completion. Fallback: the coverage model's existing
  excluded-bins mechanism, extended with a reason category for "DUT does not
  implement this optional feature."
- **Board/emulation reliability.** Confirmed reachable as of 2026-07-17, but
  `EMULATION_PLAN.md`'s own risk section already flagged intermittent SSH/
  server connectivity to the boards during the emulation bring-up session.
  Treat R1's Jul-20/21 emulation runs as at-risk if that recurs, with the
  documented fallback of running on simulation only and noting emulation as
  deferred for that specific feature.
