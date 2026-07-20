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

## Final product decision: Option B — internal verification-IP portfolio (decided 2026-07-20)

**Decided: B**, with a more specific business framing than the original
option table's wording. This is **not** "10x-Engineers builds a scorecard/
report generator to sell to customers." It's an **internal reusable
verification-IP portfolio**: when a customer hires 10x-Engineers for a
verification engagement, this Debug VIP (and the company's other VIPs for
other IPs) is used as part of delivering that engagement, at no extra
licensing cost to the customer — 10x-Engineers doesn't need to buy a
third-party debug VIP from an external vendor, and the customer isn't paying
to license this VIP as a standalone product. The "product" is the service
engagement itself; this framework (and the sim/emulation debug-VIP category
it belongs to) is internal tooling that makes engagements faster and more
complete, the same role the company's other IP-specific VIPs already play.

**Implication for the roadmap**: the old Option-A framing (public self-
certification suite, third-party CLI/report polish) does not apply — there
is no external/self-serve user to polish for. Investment goes toward
internal reusability instead: solid, reviewed, reusable model/coverage/
assertion/stimulus machinery (Milestones 1-14, unaffected by this decision)
that this and future engagements can pick up directly — the same reuse
pattern the model/checker layer is already built around across CVA6/Ibex,
now extended to "across future customer engagements" rather than just
"across DUTs."

The original four-option comparison, kept for rationale/context:

| Option | What ships | Who consumes it |
|---|---|---|
| A. Open self-certification suite | The framework itself, public, runnable by anyone against their own DM RTL | Chip/IP teams, directly |
| **B. Internal verification-IP portfolio (chosen)** | This framework, used internally to deliver verification engagements | 10x-Engineers' own delivery teams, across customer engagements |
| C. Licensable reference-model core | The golden model + coverage/assertion library as standalone IP | Other verification teams / EDA-adjacent integration |
| D. Combination | Open core (A) with a paid layer (B) on the same engine (C) | Both of the above |

## Roadmap to Project End — DM-only / External-Debug scope, target 2026-08-17

**Superseded 2026-07-20.** The R1-R9 release breakdown drafted 2026-07-17 is
replaced by the 17-item status/plan Jahanzeb Khalid wrote directly on
2026-07-20, now restated below as Milestones 1-17 (alongside the pre-existing
Milestone 0), each broken into the concrete tasks needed to achieve it.
Confirmed scope: **the 2026-08-17 target covers External-Debug/DM-only
verification only** (Milestones 1-13, gated by Milestone 17's completion
criteria). Native Debug (Sdext/Sdtrig) and the SV-UVM architectural model are
a separate, later track (Milestones 14-16) with no date attached yet — a real
scope reduction from the prior draft, which had folded Sdext/Sdtrig's 63
TC-IDs into the same Aug-17 window.

Staffing: solo (Jahanzeb Khalid) directing AI agents.

### Milestone 1 — Testplan Development

**Status: Done — not reviewed.**

| Task | Tangible output |
|---|---|
| Clause-parse the RISC-V Debug Spec v1.0-rc3 into a CAT1/CAT2/CAT3 traceability table | Feature Traceability Table — done |
| Write TC-IDs for every CAT2 row | `pydebug/testplans/riscv_debug_testplan.md`, 161 TC-IDs across 25 prefixes — done |
| Review and merge | PR #3 reviewed and merged — **not done** |

### Milestone 2 — Verification Strategy Development

**Status: Done — not reviewed.**

| Task | Tangible output |
|---|---|
| Define verification levels, component map, phased approach | `VERIFICATION_STRATEGY.md` — done |
| Build Operation Catalogs (external DM, external Trigger Module, native Sdext/Sdtrig) | Same file, 3 catalog sections — done |
| Decide a git home for the document | Currently lives outside any git repo — **not done** |
| Review | **not done**, blocked on the git-home decision above |

### Milestone 3 — PyDebug framework initial structure

**Status: Done — not reviewed.**

| Task | Tangible output |
|---|---|
| Transport abstraction (mock/UVM/OpenOCD) | `api/transport.py`, `api/uvm_transport.py`, `api/openocd_transport.py` — done, predates this session (PR #1) |
| DMI command layer | `api/riscv_dm.py` (`RISCVDebug`, `DMI`) — done, extended this session |
| Session/CLI scaffolding | `api/session.py`, `cli.py` — done |
| Review | **not done** |

### Milestone 4 — Simulation Testbench structure (Agents, Model, interfaces, Tests, Sequences, TB)

**Status: Complete — not reviewed.**

| Task | Tangible output |
|---|---|
| Golden reference model | `model/registers.py`, `predictor.py`, `coverage.py`, `invariants.py`, `mock_transport.py` — done |
| Transport-agnostic observer hook | `api/observer.py` — done |
| SV coverage + protocol-tier assertions | `sv_kit/covergroups.sv`, `sv_kit/dmi_assertions.sv` — done |
| Stimulus sequences + pytest for the run-control cluster | `sequences/{run_control,reset_ctrl,halt_on_reset,dm_activation,hart_selection}_sequence.py`, matching `tests/*.py` — done |
| Regression tiering (smoke/static) | `regressions.json`, `Makefile`, `tests/test_regression_integrity.py` — done |
| Review | **not done** |

### Milestone 5 — Basic feature tests on CVA6 and Ibex-demo-system

**Status: Complete — authenticity not reviewed.**

| Task | Tangible output |
|---|---|
| 8-feature stimulus-migration case study | Paper's Table II — done |
| CVA6 UVM scoreboard clean run | Checked=42, Errors=0 — done, per paper |
| Ibex UVM scoreboard clean run | Checked=38, Errors=0 — done, per paper |
| Independently re-run/cross-check these numbers this session | **not done** — currently only cited from the paper draft, a real open item, not a formality |

### Milestone 6 — Emulation smoke tests on Arty A7 with Ibex-demo-system

**Status: Complete.**

| Task | Tangible output |
|---|---|
| OpenOCD transport + board config for Arty A7 | `openocd_arty_a7_100t.cfg`, `halt_hw.json` — done |
| Halt/resume/GPR-read/SBA proven on real hardware | Paper's "Pass, real HW" rows — done |

### Milestone 7 — Emulation smoke tests on CVA6

**Status: Deferred — FPGA unavailability.**

| Task | Tangible output |
|---|---|
| Genesys2 board bring-up | **Blocked** — FPGA currently unavailable |
| OpenOCD config for Genesys2 | `openocd_genesys2_cva6.cfg`, `halt_genesys2.json` — already authored, per `EMULATION_PLAN.md` |
| Resume once FPGA access is restored | Not scheduled — no date until access returns |

### Milestone 8 — Component-by-Component Review

Added 2026-07-20: reviewing PR #3 as one undifferentiated blob isn't real
review. Each component gets its own task/issue, reviewed individually,
before Milestone 9's merge/sign-off happens.

| Task | Tangible output |
|---|---|
| Review Agents (JTAG VIP stack: driver, monitor, sequencer, agent) | `sv_kit/` reviewed, including the known `jtag_monitor.sv` TDO-sampling gap |
| Review Golden Reference Model | `model/{registers,predictor,coverage,invariants,mock_transport}.py` reviewed |
| Review Interfaces (observer hook + transport/DMI API layer) | `api/{observer,transport,riscv_dm}.py` reviewed |
| Review Stimulus Sequences | `sequences/*.py` reviewed |
| Review Tests + Regression Tiering | `tests/*.py`, `regressions.json` reviewed |
| Review Testbench wiring (env.sv, debug_pkg.sv, SV covergroups/assertions) | `sv_kit/{env,debug_pkg,covergroups,dmi_assertions}.sv` reviewed |
| Review Testplan document | `testplans/riscv_debug_testplan.md` reviewed — signs off Milestone 1 |
| Review Verification Strategy document | `VERIFICATION_STRATEGY.md` reviewed — signs off Milestone 2 |

### Milestone 9 — All DV flow reviewed and finalized

Depends on Milestone 8's component reviews completing first.

| Task | Tangible output |
|---|---|
| Merge PR #3 (testplan, model, TB structure) | Merged PR, Milestones 1/3/4 signed off |
| Decide git home for `VERIFICATION_STRATEGY.md`, then review it | Milestone 2 signed off |
| Re-run/cross-check Milestone 5's CVA6/Ibex numbers | Milestone 5's "authenticity" concern closed |
| Formal sign-off recorded for Milestones 1-7 collectively | This section updated with sign-off dates |

### Milestone 10 — Stimulus Generation from Testplan, Specification and Functional Coverpoints

| Task | Tangible output |
|---|---|
| Model the registers/fields for each Milestone-11 feature group not yet modeled (external trigger `dmcs2`, abstract commands, program buffer, multi-hart halt/resume mask) | `model/` additions |
| Build SV covergroups + coverpoints for the same | `sv_kit/covergroups.sv` additions |
| Build Python stimulus sequences + pytest for the same | New `sequences/*.py` + `tests/*.py` |
| Register new scenarios | `SCENARIO_REGISTRY` entries + sim configs |

### Milestone 11 — External Debug features verified on simulation, 100% functional coverage

Each feature group below is its own functional-coverpoint target, mapped to
the testplan prefix that already covers it:

| Feature group | Testplan prefix(es) | Task | Status |
|---|---|---|---|
| Halt — single | `RC` | Already built | Stimulus exists |
| Halt — multiple | `HG`/`HS` array-mask rows | Build hart-array-mask stimulus | Not started |
| Resume — single | `RC` | Already built | Stimulus exists |
| Resume — multiple | `HG`/`HS` array-mask rows | Build hart-array-mask stimulus | Not started |
| Active (`dmactive`) | `DMA` | Already built | Stimulus exists |
| Reset | `RST`/`HOR` | Already built | Stimulus exists |
| External trigger | `HG`/`EXT-TRIG` rows | Build register-level stimulus | Not started — **likely register-level only**, per the paper's own Finding 3/4 precedent (group halt/resume needed a bigger RTL change than either DUT's IP supports) |
| SBA | `SBA` | Build stimulus (real-HW path already proven in the paper) | Not started |
| Abstract command | `AC`/`QA`/`AM` | Build stimulus (GPR path partially exists in `riscv_dm.py`) | Not started |
| Program buffer execution | `PB` | Build driver support **from zero**, then stimulus | Not started — highest-effort item in this milestone |
| Close coverage | — | Every `DebugCoverageModel` bin above closed or excluded-with-reason | Not started |

### Milestone 12 — External Debug features run and pass on Emulation on Arty-A7 with Ibex-demo-system as SoC

| Task | Tangible output |
|---|---|
| Port each Milestone-11 scenario to `--transport openocd` | Config entries per scenario |
| Run against Arty A7 hardware | Recorded pass/fail per feature |
| Reproduce any emulation failure on simulation for root-cause | `testplans/results/` entries, emulation-fail→sim-reproduce workflow |

### Milestone 13 — Paper final draft completion

| Task | Tangible output |
|---|---|
| Incorporate Milestone 11/12 results, extending the paper's Table II | Updated draft |
| Update methodology/discussion sections if results change the narrative | Updated draft |

### Milestone 14 — Review of Final Draft for DVCon paper submission

| Task | Tangible output |
|---|---|
| Internal review pass | Comments resolved |
| Submit | Submission confirmation |

**Milestone 18 is the gate for Milestones 1-14** (see below) — reached when
Milestones 8-12 close, independent of Milestones 15-17.

### Milestone 15 — SV-UVM Arch-Model for the RISC-V Debug Module, external-debug features only

**No date — separate track.**

| Task | Tangible output |
|---|---|
| Design the SV-UVM architectural model's class structure | Design note |
| Implement register/predictor logic in SystemVerilog, mirroring the Python model | New `sv_kit/` model classes |
| Integrate into the existing UVM env | `env.sv` wiring |
| Cross-check against the Python model | Agreement report |

### Milestone 16 — Native Debug support tests in ASM/C

**No date — separate track.**

| Task | Tangible output |
|---|---|
| Write firmware test programs per `NATIVE-OP1-7` (ebreak, trigger-based breakpoints, `icount` single-step) | ASM/C sources |
| Build the cross-compile + preload flow | Build scripts |
| Self-checking trap handlers (sentinel PASS/FAIL, per `VERIFICATION_STRATEGY.md`'s native-debugging firmware pattern) | Firmware + readback harness |

### Milestone 17 — Native Debug support in the Model

**No date — separate track.**

| Task | Tangible output |
|---|---|
| Model `dcsr`/`dpc`/`dscratch0-1` | `model/` additions (`DCSR` testplan prefix) |
| Model Sdtrig registers, native (`action=0`) variants | `model/` additions (`TRIG` testplan prefix) |
| Coverage + assertions for native paths | Python + SV |

Milestones 15-17 together deliver the Sdext/Sdtrig work already scoped in
the testplan (`DCSR`/`SSTEP`/`TRIG`, 40 TC-IDs) — deferred out of the Aug-17
window per the 2026-07-20 scope confirmation, not dropped.

### Milestone 18 — System-Level Verification Complete (DM-only) — target 2026-08-17

**The Aug-17 gate.** Reached once Milestones 8-12 close.

| Task | Tangible output |
|---|---|
| Full regression (`make static`) green on Ibex, and CVA6 wherever access allows | Recorded results, `testplans/results/` |
| 100% functional coverage (DM only) | Every `DebugCoverageModel` bin closed or excluded-with-reason — not a silently-inflated percentage |
| 100% RTL code coverage (DM only) | Flagged, not assumed achievable by stimulus alone — some lines may need an explicit waiver list (see Known Risks) |
| 0 regression failures | Confirmed across the full DM-only suite |
| Final sign-off | Go/no-go recorded, residual open items named explicitly |

## Completion Tracker

| Milestone | Target | Status |
|---|---|---|
| 0 — Foundations | Done | **Done** |
| 1 — Testplan Development | — | Done, not reviewed |
| 2 — Verification Strategy Development | — | Done, not reviewed (no git home yet) |
| 3 — PyDebug framework initial structure | — | Done, not reviewed |
| 4 — Simulation Testbench structure | — | Complete, not reviewed |
| 5 — Basic feature tests, CVA6+Ibex | — | Complete, authenticity not reviewed |
| 6 — Emulation smoke tests, Arty A7/Ibex | — | Complete |
| 7 — Emulation smoke tests, CVA6 | — | Deferred (FPGA unavailable) |
| 8 — Component-by-Component Review | TBD | In progress — 8 review issues open |
| 9 — DV flow reviewed and finalized | TBD | Not started |
| 10 — Stimulus generation | TBD | Not started |
| 11 — External-debug features, 100% functional coverage (sim) | TBD | Not started — 4 of 10 rows already have stimulus |
| 12 — External-debug features on emulation | TBD | Not started |
| 13 — Paper final draft | TBD | Not started |
| 14 — Paper review for DVCon | TBD | Not started |
| 18 — System-level verification complete (DM-only) | **2026-08-17** | Not started |
| 15 — SV-UVM arch-model, external-debug only | No date | Not started |
| 16 — Native debug tests (ASM/C) | No date | Not started |
| 17 — Native debug model support | No date | Not started |

## Known Risks

- **CVA6 emulation deferral removes cross-platform proof from the Aug-17
  target.** Item 17's DM-only scope now closes on Ibex/Arty-A7 alone if
  CVA6/Genesys2 access doesn't return in time — the paper's own central
  portability thesis would rest on one platform for this milestone, with
  CVA6 named as a documented gap, not silently dropped.
- **`VERIFICATION_STRATEGY.md` has no git home.** Needs a decision (move
  into `pydebug/`? add a repo at the workspace root? explicitly leave
  out of version control?) before item 2 can be meaningfully reviewed in a
  PR the way items 1/3/4 now can be (PR #3).
- **Item 5's "authenticity not reviewed" is a real open item, not a
  formality** — the CVA6/Ibex numbers currently only come from the paper
  draft, not from a fresh run this session. Worth re-running before citing
  them again in the DVCon draft.
- **100% RTL code coverage may not be achievable through spec-legal stimulus
  alone**, even scoped to DM-only. Defensive/dead code paths in the DUT's
  own RTL can be unreachable via any sequence a real debugger would legally
  issue. Resolution: a documented waiver list (same discipline this project
  already applies to functional-coverage exclusions), not silently claiming
  100%.
- **Model/DUT divergence that is legal on both sides.** Already observed
  once: CVA6 computes `allrunning = ~halted & ~unavailable` so a hart held in
  reset reports `running=1`, while the Python predictor models "neither
  halted nor running" — both conform to spec #3.2. Fallback: document the
  divergence per-DUT rather than "fixing" either side.
- **Verification-IP bugs, not just DUT bugs.** Two were found in this
  project's own SV kit during M0 (the TDO-sampling gap, the wrong
  reset-value constant). Expect more as coverage/assertions reach parts of
  the kit that have never had a consumer before.
- **Optional-feature variance across DUTs makes "100% coverage" DUT-relative,
  not spec-absolute.** CVA6 already can't exercise 6 of 16 run-control-cluster
  TC-IDs because it doesn't implement `hasresethaltreq`/`hartreset`. Every
  feature group in item 10 needs the same RTL-verified (not assumed)
  N/A-detection gate before claiming completion.
- **External trigger and Program Buffer are the two highest-effort items in
  item 10's list** — External trigger likely caps out at register-level
  proof (per the paper's own precedent); Program Buffer has zero driver
  support today and needs new `api/riscv_dm.py` code before any stimulus can
  exist at all.
