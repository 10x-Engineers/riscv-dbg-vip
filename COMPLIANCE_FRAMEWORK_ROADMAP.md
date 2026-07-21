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
2026-07-20, now restated below as Milestones 1-20 (alongside the pre-existing
Milestone 0, plus Milestones 10/16 added the same day for coverage tooling),
each broken into the concrete tasks needed to achieve it.
Confirmed scope: **the 2026-08-17 target covers External-Debug/DM-only
verification only** (Milestones 1-16, gated by Milestone 20's completion
criteria). Native Debug (Sdext/Sdtrig) and the SV-UVM architectural model are
a separate, later track (Milestones 14-16) with no date attached yet — a real
scope reduction from the prior draft, which had folded Sdext/Sdtrig's 63
TC-IDs into the same Aug-17 window.

Staffing: solo (Jahanzeb Khalid) directing AI agents.

**Target dates (2026-07-20, estimates added 2026-07-21, paper date moved
2026-07-21):** four dates were concretely discussed — 2026-07-22 (paper
content ready), 2026-07-24 (paper review done), 2026-07-25 (paper
submission), and 2026-08-17 (final DM-only sign-off), all originally set in
the superseded R1-R9 draft. Reapplied onto the closest-matching milestones:
**Milestone 14** (paper final draft), **Milestone 15** (review + DVCon
submission), **Milestone 20** → 2026-08-17 (unchanged). Milestone 14 was
then moved from 2026-07-22 to **2026-07-24** per Jahanzeb Khalid's
2026-07-21 instruction ("paper can move to the 25th at most") — Milestone
15's review (07-24) and submission (07-25) are unchanged, with 2026-07-25
confirmed as the hard outer cap for the whole paper track.

Milestones 8-13 and 16 never had concrete dates in either the old or current
draft (the old plan explicitly left this range TBD, calling it the single
biggest schedule risk). Per Jahanzeb Khalid's confirmation on 2026-07-21
("estimated dates are fine for now"), these now carry a **backward-planned
estimate** from 2026-08-17, based on relative effort/blockers already noted
elsewhere in this document (e.g. Milestone 12's Program Buffer flagged as
needing driver support from zero) — **explicitly estimates, not confirmed
commitments**, unlike the four dates above:

| Milestone | Estimated target |
|---|---|
| 8 — Component-by-Component Review | 2026-07-24 |
| 9 — All DV flow reviewed and finalized | 2026-07-26 |
| 10 — Coverage Tooling Enablement (Functional) | 2026-07-27 |
| 11 — Stimulus Generation | 2026-07-31 |
| 12 — External Debug verified on sim, 100% functional coverage | 2026-08-07 |
| 13 — External Debug on Arty-A7 emulation | 2026-08-12 |
| 16 — Coverage Tooling Enablement (Code) | 2026-08-15 |

Milestones 17-19 (native debug, no longer part of the Aug-17 gate — see their
own sections) were dated 2026-08-30 per Jahanzeb Khalid's 2026-07-21 "by
month end" instruction. Milestone 7 (CVA6 emulation, blocked on FPGA access)
remains deliberately undated.

**This creates a real scheduling tension, flagged in Known Risks below**:
Milestone 14 (07-24) explicitly depends on Milestone 12/13 results, which
under this estimate don't land until 08-07/08-12 — *after* the paper's own
target date. See Known Risks for how that's reconciled. The old plan's
**infinite-loop-test requirement did not carry forward** into this Milestone
structure at all (checked: no mention anywhere in this file) — flagged here
since it's a real dropped requirement, not a decision to drop it.

### Milestone 1 — Testplan Development

**Status: Done — not reviewed.**

| Task | Tangible output | Target date |
|---|---|---|
| Clause-parse the RISC-V Debug Spec v1.0-rc3 into a CAT1/CAT2/CAT3 traceability table | Feature Traceability Table — done | — |
| Write TC-IDs for every CAT2 row | `pydebug/testplans/riscv_debug_testplan.md`, 161 TC-IDs across 25 prefixes — done | — |
| Review and merge | PR #3 reviewed and merged — **not done** | TBD |

### Milestone 2 — Verification Strategy Development

**Status: Done — not reviewed.**

| Task | Tangible output | Target date |
|---|---|---|
| Define verification levels, component map, phased approach | `VERIFICATION_STRATEGY.md` — done | — |
| Build Operation Catalogs (external DM, external Trigger Module, native Sdext/Sdtrig) | Same file, 3 catalog sections — done | — |
| Decide a git home for the document | Currently lives outside any git repo — **not done** | TBD |
| Review | **not done**, blocked on the git-home decision above | TBD |

### Milestone 3 — PyDebug framework initial structure

**Status: Done — not reviewed.**

| Task | Tangible output | Target date |
|---|---|---|
| Transport abstraction (mock/UVM/OpenOCD) | `api/transport.py`, `api/uvm_transport.py`, `api/openocd_transport.py` — done, predates this session (PR #1) | — |
| DMI command layer | `api/riscv_dm.py` (`RISCVDebug`, `DMI`) — done, extended this session | — |
| Session/CLI scaffolding | `api/session.py`, `cli.py` — done | — |
| Review | **not done** | TBD |

### Milestone 4 — Simulation Testbench structure (Agents, Model, interfaces, Tests, Sequences, TB)

**Status: Complete — not reviewed.**

| Task | Tangible output | Target date |
|---|---|---|
| Golden reference model | `model/registers.py`, `predictor.py`, `coverage.py`, `invariants.py`, `mock_transport.py` — done | — |
| Transport-agnostic observer hook | `api/observer.py` — done | — |
| SV coverage + protocol-tier assertions | `sv_kit/covergroups.sv`, `sv_kit/dmi_assertions.sv` — done | — |
| Stimulus sequences + pytest for the run-control cluster | `sequences/{run_control,reset_ctrl,halt_on_reset,dm_activation,hart_selection}_sequence.py`, matching `tests/*.py` — done | — |
| Regression tiering (smoke/static) | `regressions.json`, `Makefile`, `tests/test_regression_integrity.py` — done | — |
| Review | **not done** | TBD |

### Milestone 5 — Basic feature tests on CVA6 and Ibex-demo-system

**Status: Complete — authenticity not reviewed.**

| Task | Tangible output | Target date |
|---|---|---|
| 8-feature stimulus-migration case study | Paper's Table II — done | — |
| CVA6 UVM scoreboard clean run | Checked=42, Errors=0 — done, per paper | — |
| Ibex UVM scoreboard clean run | Checked=38, Errors=0 — done, per paper | — |
| Independently re-run/cross-check these numbers this session | **not done** — currently only cited from the paper draft, a real open item, not a formality | TBD |

### Milestone 6 — Emulation smoke tests on Arty A7 with Ibex-demo-system

**Status: Complete.**

| Task | Tangible output | Target date |
|---|---|---|
| OpenOCD transport + board config for Arty A7 | `openocd_arty_a7_100t.cfg`, `halt_hw.json` — done | — |
| Halt/resume/GPR-read/SBA proven on real hardware | Paper's "Pass, real HW" rows — done | — |

### Milestone 7 — Emulation smoke tests on CVA6

**Status: Deferred — FPGA unavailability.**

| Task | Tangible output | Target date |
|---|---|---|
| Genesys2 board bring-up | **Blocked** — FPGA currently unavailable | TBD |
| OpenOCD config for Genesys2 | `openocd_genesys2_cva6.cfg`, `halt_genesys2.json` — already authored, per `EMULATION_PLAN.md` | — |
| Resume once FPGA access is restored | Not scheduled — no date until access returns | TBD |

### Milestone 8 — Component-by-Component Review

Added 2026-07-20: reviewing PR #3 as one undifferentiated blob isn't real
review. Each component gets its own task/issue, reviewed individually,
before Milestone 9's merge/sign-off happens.

**Estimated target: 2026-07-24** (backward-planned, not confirmed — see the
Target dates note above).

| Task | Tangible output | Target date |
|---|---|---|
| Review Agents (JTAG VIP stack: driver, monitor, sequencer, agent) | `sv_kit/` reviewed, including the known `jtag_monitor.sv` TDO-sampling gap | 2026-07-24 (est.) |
| Review Golden Reference Model | `model/{registers,predictor,coverage,invariants,mock_transport}.py` reviewed | 2026-07-24 (est.) |
| Review Interfaces (observer hook + transport/DMI API layer) | `api/{observer,transport,riscv_dm}.py` reviewed | 2026-07-24 (est.) |
| Review Stimulus Sequences | `sequences/*.py` reviewed | 2026-07-24 (est.) |
| Review Tests + Regression Tiering | `tests/*.py`, `regressions.json` reviewed | 2026-07-24 (est.) |
| Review Testbench wiring (env.sv, debug_pkg.sv, SV covergroups/assertions) | `sv_kit/{env,debug_pkg,covergroups,dmi_assertions}.sv` reviewed | 2026-07-24 (est.) |
| Review Testplan document | `testplans/riscv_debug_testplan.md` reviewed — signs off Milestone 1 | 2026-07-24 (est.) |
| Review Verification Strategy document | `VERIFICATION_STRATEGY.md` reviewed — signs off Milestone 2 | 2026-07-24 (est.) |

### Milestone 9 — All DV flow reviewed and finalized

Depends on Milestone 8's component reviews completing first.

**Estimated target: 2026-07-26** (backward-planned, not confirmed).

| Task | Tangible output | Target date |
|---|---|---|
| Merge PR #3 (testplan, model, TB structure) | Merged PR, Milestones 1/3/4 signed off | — done |
| Decide git home for `VERIFICATION_STRATEGY.md`, then review it | Milestone 2 signed off | 2026-07-26 (est.) |
| Re-run/cross-check Milestone 5's CVA6/Ibex numbers | Milestone 5's "authenticity" concern closed | 2026-07-26 (est.) |
| Formal sign-off recorded for Milestones 1-7 collectively | This section updated with sign-off dates | 2026-07-26 (est.) |

### Milestone 10 — Coverage Tooling Enablement (Functional Coverage)

Added 2026-07-20: neither coverage substrate's readiness had a dedicated
milestone before now, despite Milestone 20 depending on it working. **Code
coverage specifically is sequenced later (Milestone 16, after paper
submission)** — functional coverage is the near-term need, since Milestone
12's 100% functional-coverage claim feeds the paper.

**Estimated target: 2026-07-27** (backward-planned, not confirmed — the
Xcelium task is externally blocked on RAVI/Apollo access regardless of any
date).

| Task | Tangible output | Status | Target date |
|---|---|---|---|
| Diagnose local Questa's coverage support | Confirmed live: SV functional coverage (covergroups) works (`cg.get_coverage()` returns real percentages) — usable now. Code coverage (`+cover=`/`-coverage`/`vcover`) silently no-ops — zero errors, but no `.ucdb` produced even from a clean rebuild; that gap is Milestone 16's problem, not this one's. | **Done** | — |
| Diagnose and confirm Xcelium functional coverage on the RAVI/Apollo server | Not attempted from this environment per instruction — `jk-ravi` (port 1020) times out from here, `jk-apollo-remote` (port 1015) is reachable but rejects every locally-available key, `jk-apollo` is a LAN-only address unreachable from this sandbox. To be diagnosed directly by Jahanzeb Khalid, or this environment's access fixed first. | Not started | 2026-07-27 (est., blocked on server access) |

### Milestone 11 — Stimulus Generation from Testplan, Specification and Functional Coverpoints

**Estimated target: 2026-07-31** (backward-planned, not confirmed).

| Task | Tangible output | Target date |
|---|---|---|
| Model the registers/fields for each Milestone-12 feature group not yet modeled (external trigger `dmcs2`, abstract commands, program buffer, multi-hart halt/resume mask) | `model/` additions | 2026-07-31 (est.) |
| Build SV covergroups + coverpoints for the same | `sv_kit/covergroups.sv` additions | 2026-07-31 (est.) |
| Build Python stimulus sequences + pytest for the same | New `sequences/*.py` + `tests/*.py` | 2026-07-31 (est.) |
| Register new scenarios | `SCENARIO_REGISTRY` entries + sim configs | 2026-07-31 (est.) |

### Milestone 12 — External Debug features verified on simulation, 100% functional coverage

Each feature group below is its own functional-coverpoint target, mapped to
the testplan prefix that already covers it:

**Estimated target: 2026-08-07** (backward-planned, not confirmed — the
heaviest milestone in this range; Program Buffer alone needs driver support
built from zero).

| Feature group | Testplan prefix(es) | Task | Status | Target date |
|---|---|---|---|---|
| Halt — single | `RC` | Already built | Stimulus exists | — |
| Halt — multiple | `HG`/`HS` array-mask rows | Build hart-array-mask stimulus | Not started | 2026-08-07 (est.) |
| Resume — single | `RC` | Already built | Stimulus exists | — |
| Resume — multiple | `HG`/`HS` array-mask rows | Build hart-array-mask stimulus | Not started | 2026-08-07 (est.) |
| Active (`dmactive`) | `DMA` | Already built | Stimulus exists | — |
| Reset | `RST`/`HOR` | Already built | Stimulus exists | — |
| External trigger | `HG`/`EXT-TRIG` rows | Build register-level stimulus | Not started — **likely register-level only**, per the paper's own Finding 3/4 precedent (group halt/resume needed a bigger RTL change than either DUT's IP supports) | 2026-08-07 (est.) |
| SBA | `SBA` | Build stimulus (real-HW path already proven in the paper) | Not started | 2026-08-07 (est.) |
| Abstract command | `AC`/`QA`/`AM` | Build stimulus (GPR path partially exists in `riscv_dm.py`) | Not started | 2026-08-07 (est.) |
| Program buffer execution | `PB` | Build driver support **from zero**, then stimulus | Not started — highest-effort item in this milestone | 2026-08-07 (est.) |
| Close coverage | — | Every `DebugCoverageModel` bin above closed or excluded-with-reason | Not started | 2026-08-07 (est.) |

### Milestone 13 — External Debug features run and pass on Emulation on Arty-A7 with Ibex-demo-system as SoC

**Estimated target: 2026-08-12** (backward-planned, not confirmed).

| Task | Tangible output | Target date |
|---|---|---|
| Port each Milestone-12 scenario to `--transport openocd` | Config entries per scenario | 2026-08-12 (est.) |
| Run against Arty A7 hardware | Recorded pass/fail per feature | 2026-08-12 (est.) |
| Reproduce any emulation failure on simulation for root-cause | `testplans/results/` entries, emulation-fail→sim-reproduce workflow | 2026-08-12 (est.) |

### Milestone 14 — Paper final draft completion

**Target: 2026-07-24** (moved from 2026-07-22 per Jahanzeb Khalid's
2026-07-21 confirmation — "paper can move to the 25th at most." Set to
07-24, one day before Milestone 15's fixed 07-25 submission cap, so the
existing 07-24 internal-review task still has a completed draft to review
against; if 2026-07-25 itself was intended for the draft rather than 07-24,
flag it and this gets adjusted).

| Task | Tangible output | Target date |
|---|---|---|
| Incorporate Milestone 12/13 results, extending the paper's Table II | Updated draft | 2026-07-24 |
| Update methodology/discussion sections if results change the narrative | Updated draft | 2026-07-24 |

### Milestone 15 — Review of Final Draft for DVCon paper submission

**Target: 2026-07-25** (review 2026-07-24, submission 2026-07-25 — both
reused from the superseded R1-R9 draft's R2/R3 dates).

| Task | Tangible output | Target date |
|---|---|---|
| Internal review pass | Comments resolved | 2026-07-24 |
| Submit | Submission confirmation | 2026-07-25 |

**Milestone 20 is the gate for Milestones 1-15** (see below) — reached when
Milestones 8-13 and 16 close, independent of Milestones 17-19.

### Milestone 16 — Coverage Tooling Enablement (Code Coverage)

**Sequenced after paper submission (Milestone 15)**, per instruction —
code coverage isn't needed for the paper, only for Milestone 20's sign-off.

**Estimated target: 2026-08-15** (backward-planned, not confirmed — the
Xcelium task is externally blocked on RAVI/Apollo access regardless of any
date).

| Task | Tangible output | Target date |
|---|---|---|
| Resolve the local Questa code-coverage gap diagnosed in Milestone 10 | Either a working license/config fix, or a confirmed decision to rely on Xcelium instead | 2026-08-15 (est.) |
| Diagnose and add Xcelium code-coverage support on the RAVI/Apollo server | Same access blockers as Milestone 10 apply — needs direct diagnosis by Jahanzeb Khalid or fixed environment access | 2026-08-15 (est., blocked on server access) |
| Verify a real UCDB gets produced against the actual CVA6/Ibex sims (not just a trivial testbench) | Recorded proof, `testplans/results/` | 2026-08-15 (est.) |
| Wire the working tool into Milestone 20's code-coverage task | `Makefile`/regression config updated | 2026-08-15 (est.) |

### Milestone 17 — SV-UVM Arch-Model for the RISC-V Debug Module, external-debug features only

**Target: 2026-08-30** (set by Jahanzeb Khalid on 2026-07-21 — "by month end").
Still a separate track from the Aug-17 DM-only sign-off gate, not part of
Milestone 20's completion criteria — see the note below the M19 table.

| Task | Tangible output | Target date |
|---|---|---|
| Design the SV-UVM architectural model's class structure | Design note | 2026-08-30 |
| Implement register/predictor logic in SystemVerilog, mirroring the Python model | New `sv_kit/` model classes | 2026-08-30 |
| Integrate into the existing UVM env | `env.sv` wiring | 2026-08-30 |
| Cross-check against the Python model | Agreement report | 2026-08-30 |

### Milestone 18 — Native Debug support tests in ASM/C

**Target: 2026-08-30** (set 2026-07-21, "by month end"). Separate track,
not gated by Milestone 20.

| Task | Tangible output | Target date |
|---|---|---|
| Write firmware test programs per `NATIVE-OP1-7` (ebreak, trigger-based breakpoints, `icount` single-step) | ASM/C sources | 2026-08-30 |
| Build the cross-compile + preload flow | Build scripts | 2026-08-30 |
| Self-checking trap handlers (sentinel PASS/FAIL, per `VERIFICATION_STRATEGY.md`'s native-debugging firmware pattern) | Firmware + readback harness | 2026-08-30 |

### Milestone 19 — Native Debug support in the Model

**Target: 2026-08-30** (set 2026-07-21, "by month end"). Separate track,
not gated by Milestone 20.

| Task | Tangible output | Target date |
|---|---|---|
| Model `dcsr`/`dpc`/`dscratch0-1` | `model/` additions (`DCSR` testplan prefix) | 2026-08-30 |
| Model Sdtrig registers, native (`action=0`) variants | `model/` additions (`TRIG` testplan prefix) | 2026-08-30 |
| Coverage + assertions for native paths | Python + SV | 2026-08-30 |

Milestones 17-19 together deliver the Sdext/Sdtrig work already scoped in
the testplan (`DCSR`/`SSTEP`/`TRIG`, 40 TC-IDs) — deferred out of the Aug-17
window per the 2026-07-20 scope confirmation, not dropped, and now dated
2026-08-30 as a separate downstream milestone rather than gating the
DM-only sign-off.

### Milestone 20 — System-Level Verification Complete (DM-only) — target 2026-08-17

**The Aug-17 gate.** Reached once Milestones 8-13 and 16 close.

| Task | Tangible output | Target date |
|---|---|---|
| Full regression (`make static`) green on Ibex, and CVA6 wherever access allows | Recorded results, `testplans/results/` | 2026-08-17 |
| 100% functional coverage (DM only) | Every `DebugCoverageModel` bin closed or excluded-with-reason — not a silently-inflated percentage | 2026-08-17 |
| 100% RTL code coverage (DM only) | Depends on Milestone 16 closing first — flagged, not assumed achievable by stimulus alone even once tooling works; some lines may need an explicit waiver list (see Known Risks) | 2026-08-17 |
| 0 regression failures | Confirmed across the full DM-only suite | 2026-08-17 |
| Final sign-off | Go/no-go recorded, residual open items named explicitly | 2026-08-17 |

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
| 8 — Component-by-Component Review | 2026-07-24 (est.) | In progress — 8 review issues open |
| 9 — DV flow reviewed and finalized | 2026-07-26 (est.) | Not started |
| 10 — Coverage Tooling Enablement (Functional Coverage) | 2026-07-27 (est.) | In progress — local-Questa functional coverage confirmed working, Xcelium/RAVI-Apollo task open |
| 11 — Stimulus generation | 2026-07-31 (est.) | Not started |
| 12 — External-debug features, 100% functional coverage (sim) | 2026-08-07 (est.) | Not started — 4 of 10 rows already have stimulus |
| 13 — External-debug features on emulation | 2026-08-12 (est.) | Not started |
| 14 — Paper final draft | **2026-07-24** | Not started |
| 15 — Paper review for DVCon | **2026-07-25** | Not started |
| 16 — Coverage Tooling Enablement (Code Coverage) | 2026-08-15 (est.) | Not started — sequenced after Milestone 15, local-Questa gap already diagnosed under Milestone 10 |
| 20 — System-level verification complete (DM-only) | **2026-08-17** | Not started |
| 17 — SV-UVM arch-model, external-debug only | **2026-08-30** | Not started |
| 18 — Native debug tests (ASM/C) | **2026-08-30** | Not started |
| 19 — Native debug model support | **2026-08-30** | Not started |

## Known Risks

- **Milestones 8-13 and 16's dates are backward-planned estimates, not
  measured schedule commitments.** No real velocity data exists for this
  range (the one completed slice's telemetry, cited in Context above, covers
  only the coverage+assertions phase of the architecturally simplest area —
  stimulus-phase timing was never measured, and every remaining milestone is
  structurally larger). Treat 2026-07-24 through 2026-08-15 as a working
  plan to check progress against and revise, not a commitment communicated
  externally.
- **Milestone 14/15's dates (2026-07-24/07-25) conflict with Milestone
  12/13's estimated dates (2026-08-07/08-12).** Milestone 14's own task list
  says "incorporate Milestone 12/13 results" — but under the backward-planned
  estimate, M12/M13 don't land until *two to three weeks after* the paper's
  target date, and M12 alone includes Program Buffer "from zero" driver work,
  already flagged as the highest-effort item in the whole plan. **Confirmed
  by Jahanzeb Khalid (2026-07-21):** "paper can move to the 25th at most" —
  i.e. 2026-07-25 is a hard outer cap on the paper track, it will not slip
  further to align with Milestone 12/13's fuller completion. The paper
  draft/submission proceeds on 2026-07-24/07-25 using whatever M12/M13
  results exist by then (the paper already has its own 8-feature case study
  drawn from Milestone 5, independent of M12's fuller scope) — full
  M12/M13/M16 completion continues in parallel toward the 2026-08-17 gate
  regardless of the paper's submission date. This is now a confirmed
  decision, not an open question.
- **The old plan's infinite-loop-test requirement was dropped, not carried
  forward.** The superseded R1-R9 draft required an "infinite loop test" per
  feature area alongside interactive/non-interactive mode coverage; this
  Milestone structure has no equivalent task anywhere. Flagging since this was
  found while reusing the old plan's dates, not because a decision was made to
  drop it.
- **CVA6 emulation deferral removes cross-platform proof from the Aug-17
  target.** Milestone 20's DM-only scope now closes on Ibex/Arty-A7 alone if
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
  feature group in Milestone 12 needs the same RTL-verified (not assumed)
  N/A-detection gate before claiming completion.
- **External trigger and Program Buffer are the two highest-effort items in
  Milestone 12's list** — External trigger likely caps out at register-level
  proof (per the paper's own precedent); Program Buffer has zero driver
  support today and needs new `api/riscv_dm.py` code before any stimulus can
  exist at all.
- **RAVI/Apollo server access is unresolved from this environment.**
  `jk-ravi` (port 1020) times out, `jk-apollo-remote` (port 1015) rejects
  every locally-available SSH key, and `jk-apollo` is a LAN-only address —
  none reachable from this sandbox. Milestones 10 and 16's Xcelium tasks
  are blocked on this until either access is fixed here or Jahanzeb Khalid
  diagnoses Xcelium availability directly.
