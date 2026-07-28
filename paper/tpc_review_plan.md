# TPC Reviewer Analysis — Submission #76, DVCon Europe 2026

*Adversarial review of the accepted abstract against the current paper draft.
Written from the position of a reviewer who wants this paper accepted, and who
will therefore be hardest on the claims most likely to be challenged in
committee.*

Sources: accepted abstract (submission #76), the three TPC reviews, the DVCon
Europe 2026 Engineer Paper Template, and the current state of the work in
`10x-Engineers/riscv-dbg-vip`.

---

## Phase 0 — A formatting finding that precedes everything

**The DVCon Europe template is single-column, full-width A4. It is not a
two-column IEEE layout.** Every body paragraph in the template spans the full
text width; the left margin carries the conference logo on page 1. Concretely,
the template prescribes:

| Element | Template rule |
|---|---|
| Page | A4 (8.27" × 11.69"), **single column** |
| Title | "Paper Title" style, centred |
| Subtitle | "Paper Subtitle" style, centred |
| Authors | One line per author: `Name, Affiliation, Organization, City, Country (e-mail)` |
| Abstract | Run-in head `Abstract—`, **bold body text**, italic head |
| Keywords | Run-in head `Keywords—`, bold italic |
| Heading 1 | `I. INTRODUCTION` — centred, small caps, auto-numbered |
| Heading 2 | `A. Subsection` — italic, left |
| Component heads | `ACKNOWLEDGMENT`, `REFERENCES` use **Heading 5** (centred, small caps, unnumbered) |
| Table caption | **Above** the table: `Table I. Caption`, 8 pt Times New Roman |
| Figure caption | **Below** the figure: `Figure 1. Caption`, 8 pt |
| Cross-references | Full name, `Figure 1`, even at sentence start; `[3]`, never `Ref. [3]` |
| Pagination | **Do not add any** — the template does it |
| Vector figures | Convert SVG → EMF (Inkscape) and insert in a text box |
| Sponsors | Unnumbered footnote on page 1, or delete the text box |

Two consequences worth acting on before any content work:

1. Everything below assumes single-column. Wide tables are *easier* here than
   in IEEE two-column, so the Table I / Table II / Table IV width problem
   disappears — but a table sized for a 3.15" column will now look sparse and
   must be re-proportioned to ~6.7".
2. The template's own Section IV is explicit: finish content editing first,
   then `Save As` the template and import the text. That ordering is the right
   one here too — do not restyle until Phases 8–11 below are closed.

---

## Phase 1 — What the accepted abstract actually promises

The TPC accepted *this* abstract. The final paper is judged against these
promises, not against a better abstract written later. Sentence by sentence:

| # | Claim from the accepted abstract | Evidence required | Section that must contain it | Status today |
|---|---|---|---|---|
| 1 | RISC-V debug infrastructure (DTM/DMI/DM) verification "remains a fragmented challenge" | Citation + a concrete statement of the two-workflow split | I. Introduction | ✅ |
| 2 | The spec "defines a highly stateful interaction" | Citation [1]; ideally one concrete stateful sequence shown | I. Introduction | ✅ |
| 3 | "Existing verification methodologies offer limited support for unified stimulus reuse" | A Related Work section that names the alternatives and says what each cannot do | II. Related Work | ✅ (added) |
| 4 | Pre-silicon uses UVM/C; post-silicon uses OpenOCD/GDB over JTAG | Description of both, ideally cited | I / II | ✅ |
| 5 | The disconnect causes "duplicated effort, inconsistent test coverage, difficulty reproducing corner cases, delayed bring-up" | **Four separate claims.** At minimum, a quantified duplication figure (LOC that would need writing twice) and a reproduction-gap example | II + VII (Evaluation) | 🟡 duplication argued, not measured |
| 6 | "Write-once, execute-anywhere" methodology | Proof that the *same file*, byte-identical, runs on both targets. A diff, or a checksum table | VII. Evaluation | 🟡 asserted, never demonstrated as a diff |
| 7 | Python orchestration layer "abstracts the transport while preserving protocol intent" | Architecture figure + the API seam shown in code | IV. Architecture | ✅ Figure 1 |
| 8 | Python beats TCL: "more expressive," enabling "reusable libraries," "advanced automation, scenario composition, data-driven test generation" | **Weakest area.** Needs a side-by-side code listing (same scenario in both), plus one *actual* data-driven generation instance | V. Implementation + VII | ❌ currently a bullet list of assertions |
| 9 | "High-performance socket-based bridge"; "without requiring complex SystemVerilog sequence development" | Latency/throughput numbers; LOC comparison against the SV sequence it replaces | VII | 🟡 latency exists (Table IV); LOC-vs-SV missing |
| 10 | Same API "transparently switches" to OpenOCD; halt/resume, register access, **program buffer execution** run "unmodified over JTAG" | Hardware results for *those specific* operations, including program buffer | VII | 🟡 reported, not tabulated per-operation for HW |
| 11 | "Enables true shift-left ... post-silicon scenarios validated in RTL simulation prior to tape-out" | A worked example: scenario written, run in sim, then run on FPGA, same file | VII case study | 🟡 claimed, no narrated instance |
| 12 | "Experimental results on a RISC-V Debug **v1.0 compliant** implementation demonstrate **near-complete stimulus reuse**, **reduced testbench complexity**, **improved debuggability**" | **Three distinct metrics.** Reuse %, complexity delta, debuggability evidence — all on a v1.0 DUT | VII | ❌ complexity and debuggability unmeasured; hardware results are v0.13 (Ibex), not v1.0 |
| 13 | "Scalable, modular, and vendor-independent" | Scalability: more harts or more scenarios. Vendor independence: ≥2 simulators, or ≥2 debug probes, or ≥2 DUT vendors | VIII. Discussion | ❌ multi-hart explicitly out of scope; only Questa; only one board |

**Blunt summary:** rows 8, 12, and 13 are the ones that will lose you the
"best paper" slot. Rows 12 and 13 are worse than weak — they are promises the
current draft quietly walks away from. A reviewer holding the accepted
abstract in one hand and the paper in the other will notice.

### The v1.0 / v0.13 problem, stated plainly

The abstract says results are on "a RISC-V Debug v1.0 compliant
implementation." In the current draft the *hardware* results are Ibex, which
is v0.13, and the strongest per-scenario simulation evidence is also Ibex. CVA6
is the v1.0 target. You now have a clean full-regression pass on CVA6, so this
is fixable — but the paper must **lead with CVA6 as the v1.0 evidence** and
present Ibex as the second, older-spec DUT that demonstrates portability across
spec versions. Framed that way the two-DUT choice becomes a *strength* answering
"vendor-independent." Framed the current way it looks like the v1.0 claim was
retired.

---

## Phase 2 — Reviewer analysis: what each one is really saying

### Reviewer 1 — the methodologist

**Liked:** the framing. Says outright the abstract "sells the idea very well,"
motivation well described, solution "looks promising," and is "looking forward
to reading the paper." This is a favourably disposed reviewer.

**Hidden concern:** they wrote *"does not mention the Portable Stimulus
Methodology which should be given some consideration."* The word "should" is
doing real work. This is not a request for a citation. This reviewer suspects
the authors may not know PSS exists, or know it and are avoiding the comparison
because it is unflattering. Either would be disqualifying for a methodology
paper at DVCon. They are testing whether the authors are *aware of the field*.

**What they expect:** a subsection, not a sentence, that shows genuine command
of what PSS does — action graphs, constraint solving, resource models,
`exec` blocks, the runtime backend concept — and an honest statement of where
this framework sits relative to it.

**What fully satisfies them:** an argument that PSS and this work are
*orthogonal*, with the specific technical reason: PSS standardises *scenario
description* and deliberately leaves the execution backend to the
implementation, while this work's entire contribution is *in* that backend.
Bonus: state that a PSS `exec` block could target this framework's transport
layer. That converts a perceived weakness into a roadmap.

**What disappoints them:** one defensive paragraph saying "PSS is expensive and
declarative, we chose Python." That reads as dismissal, and this reviewer will
downgrade for it.

**Also from Reviewer 1:** *"authors are missing from the abstract."* Trivially
fixed, but do not forget it — it is the single easiest reviewer point to close
and leaving it open signals carelessness.

### Reviewer 2 — the sceptic, and the one who can sink this

**Liked:** the engineering sense. "This makes absolute sense."

**Did not like:** *"but this is not really original. This somehow
re-implements the transactor pattern for debug purpose. Related work shall be
extended to cover also this category of activities."*

**Psychology:** this reviewer has seen transactors, BFMs, and layered testbench
abstraction for twenty years. To them, "high-level call → bus activity, with a
swappable backend" is textbook — Bergeron, Chapter 1. They are not saying the
work is bad; they are saying **the claimed novelty is misplaced**. The word
"somehow" is important: they suspect the authors don't realise they are
describing a known pattern. That is the accusation to defeat.

**What they expect:** that you name the pattern yourself, cite it, and then
draw a precise line: *here is what a transactor does; here is what this does
that a transactor cannot.*

**What fully satisfies them:** a claim narrow enough to be obviously true. Not
"we invented cross-platform stimulus" but: *a transactor is scoped to one
execution environment and is recompiled per target; the contribution here is a
transport abstraction whose two implementations reach a simulator and a
physical chip from one unmodified stimulus artifact, applied to a protocol
(RISC-V debug) whose pre- and post-silicon toolchains are maintained by
different teams.* Then prove the "unmodified" part with a diff.

**What disappoints them, fatally:** any sentence claiming general novelty for
transaction-level abstraction. If the paper says "we introduce a novel
transaction abstraction layer," this reviewer will vote reject and be right.

**Note on the current draft:** Section II already does most of this well — it
cites Bergeron [4] and argues the five properties. The remaining gap is that
the argument is *asserted*, not *demonstrated*. Reviewer 2 wants a table or a
diff, not five bullet points of prose.

### Reviewer 3 — the enthusiast with a warning

**Liked, genuinely:** *"The author(s) and their team created their own PSS. I
enjoy this so much."* They value the pragmatism — a free tool you fully
control. They also make a market argument in your favour: "vertical reuse is
probably still the biggest time saving mechanic if done right."

**The warning, easy to miss:** *"The paper requires some work."* No specifics
given. Combined with "(rest in peace)" about PSS and the title complaint, this
reviewer's real position is: *the idea is known; the execution and the
presentation are what will make this paper worth reading.* They are giving you
a conditional accept on quality of delivery.

**Hidden concern:** that the paper will be a tool description rather than an
engineering results paper. "Requires some work" from an enthusiastic reviewer
almost always means "the abstract is thin on evidence."

**What fully satisfies them:** hard numbers and honest lessons. This reviewer
will reward a Limitations section and a "what went wrong" narrative more than
another architecture diagram. Your two self-inflicted verification bugs, the
`resumeack` timing model error, and the reporting-not-patching policy are
*exactly* what this reviewer wants to read.

**The title point:** they could not suggest a better one, which means they will
not press it. But "I was a bit surprised about the paper's contents and I
wouldn't have been able to tell what it was from the title" is worth one
consideration. A subtitle carrying the concrete nouns costs nothing:
*"Bridging Pre- and Post-Silicon Stimulus Generation for RISC-V Debug: One
Python Stimulus Library Across UVM Simulation and FPGA Silicon."*

---

## Phase 3 — Reviewer satisfaction matrix

| Reviewer | Concern | Section that must address it | Figures | Experiments | References | Risk if ignored | P(satisfied) |
|---|---|---|---|---|---|---|---|
| R1 | No PSS positioning | New §III-A "Relation to Portable Stimulus" | Fig. 4: PSS layer stack vs. this framework's layer stack, showing the shared seam | None required; a worked sketch of a PSS `exec` block targeting this transport is enough | Accellera PSS 3.0 [2] | Reads as unaware of the field → reject risk | 0.9 with the subsection, 0.3 with a paragraph |
| R1 | Authors missing | Title block | — | — | — | Trivial but signals carelessness | 1.0 |
| R2 | "Re-implements the transactor pattern" | §III-B "Relation to the Transactor Pattern" | Fig. 5: conventional transactor (one env, recompiled per target) vs. this (one stimulus, two transports) | **Diff experiment**: byte-identical stimulus across sim and FPGA | Bergeron [4]; Hua *et al.* [3] | This reviewer votes reject | 0.85 with diff evidence, 0.4 with prose alone |
| R2 | Related work too narrow | §III, Table I | — | — | Add ≥2: a cocotb-class Python/HDL reference, and one RISC-V debug verification paper | "Related work shall be extended" was an explicit instruction — ignoring an explicit instruction is the fastest reject | 0.9 |
| R3 | "Paper requires some work" | §VII Evaluation, §IX Lessons, §X Limitations | Fig. 6: coverage closure curve over the campaign | All of Phase 8 | — | Reads as a tool brochure | 0.8 |
| R3 | Title unclear | Title + subtitle | — | — | — | Low; they self-withdrew the point | 0.95 |
| All | Abstract promises unmeasured (complexity, debuggability, scalability, vendor independence) | §VII, §X | Table VI, VII | Exp. 2, 3, 5, 6 | — | **Highest risk.** A reviewer with the abstract in hand finds three broken promises | 0.75 if measured, 0.2 if left as prose |

---

## Phase 4 — Paper blueprint

Target: 8–10 pages, single column A4. Current draft is ~8 pages two-column,
which is materially more text than a single-column 10-page budget allows —
expect to cut roughly 25–30% during the pour-in. Cut from §III prose, not from
§VII results.

### I. Introduction — 0.75 page
- **Purpose:** establish that the pre/post-silicon split is a *structural*
  problem, not a tooling inconvenience.
- **Answers:** Why does debug verification specifically suffer? Who pays?
- **Must contain:** the two-workflow description; the reproduction gap stated
  as a concrete scenario ("a halt fails on the bench at 3 a.m. — what does the
  engineer do next?"); contribution list as explicit numbered bullets.
- **Must NOT contain:** architecture detail, tool names beyond context, any
  results.
- **Figures/Tables:** none.
- **References:** [1] spec.

### II. Background — 0.5 page
- **Purpose:** give a non-RISC-V-debug reader enough DM/DMI/DTM vocabulary to
  read §VII.
- **Must contain:** `dmcontrol`/`dmstatus`/`abstractcs`/`command`/`progbuf`
  and the abstract-command flow, in one short paragraph plus one figure.
- **Must NOT contain:** a spec tutorial. Two paragraphs maximum.
- **Figure 1:** DM register map / debug session state machine.

### III. Related Work — 1.25 pages ← **the reviewer-critical section**
Three mandatory subsections:
- **III-A Relation to Portable Stimulus** (Phase 7 below) — R1, R3.
- **III-B Relation to the Transactor Pattern** — R2. Cite Bergeron [4].
- **III-C Python in Verification** — cite Hua *et al.* [3] and at least one
  cocotb-class reference. R2 asked for the category to be broadened.
- **Table I:** approach comparison (already drafted — keep).
- **Must NOT contain:** any claim that transaction abstraction is novel.

### IV. Architecture — 1 page
- **Purpose:** the seam, and only the seam.
- **Must contain:** the `DebugTransport` interface as an actual code listing
  (6–10 lines) — an interface with two implementations is worth more to a
  reviewer than a block diagram.
- **Figure 2:** dual-transport architecture (existing Figure 1 — reuse).
- **Listing 1:** the transport ABC + both concrete classes' signatures.

### V. Implementation — 1.25 pages
- **V-A Simulation path:** DPI-C bridge, socket, pull architecture. Figure 3.
- **V-B Hardware path:** OpenOCD low-level DMI. Figure 4.
- **V-C Self-checking:** reference model + checker + covergroups, and the
  config-driven per-DUT declaration. This subsection is what makes it a
  verification paper rather than a scripting paper — do not cut it.
- **V-D Batch and interactive modes.**
- **Listing 2:** one complete scenario in Python (≤15 lines) — the same
  scenario used in the TCL comparison of Table V.

### VI. Test Plan and Coverage Model — 0.75 page
- **Purpose:** answer "how do you know you tested the right things?"
- **Must contain:** CAT1/CAT2/CAT3 derivation; 162 TC-IDs across 26 clusters;
  how a TC-ID maps to a scenario file and to covergroup bins.
- **Table II:** feature cluster → TC-ID count → scenario → covergroups.

### VII. Experimental Results — 2.5 pages ← **the section that wins or loses it**
- VII-A Setup: two DUTs, two spec versions, simulator, board.
- VII-B Functional results (Table III).
- VII-C Coverage closure (Table IV + Figure 5 closure curve).
- VII-D Cross-platform reuse — **the diff experiment** (Table V).
- VII-E Effort and complexity — LOC vs. the SV+TCL alternative (Table VI).
- VII-F Transport cost (Table VII — existing Table IV, keep).
- VII-G Debuggability — time-to-root-cause evidence.

### VIII. Discussion — 0.5 page
Scalability, modularity, vendor independence — the three abstract adjectives,
each answered explicitly and honestly, including where the answer is "not yet."

### IX. Lessons Learned — 0.5 page
The two DV bugs, the `resumeack` model-timing class of error, the
sampler-vs-stimulus coverage diagnostic, the report-don't-patch policy paying
off. **R3 will read this section most carefully.**

### X. Limitations and Threats to Validity — 0.4 page
**Non-negotiable.** Absent this, the paper reads as a sales document.

### XI. Conclusion and Future Work — 0.3 page

### ACKNOWLEDGMENT / REFERENCES — Heading 5 style.

---

## Phase 5 — Logical story flow

```
Debug verification is split across two teams and two toolchains   (§I)
        ↓  what does the reader now ask? "split how, exactly?"
Here is the protocol and where the split falls                    (§II)
        ↓  "surely someone solved this — PSS? transactors?"
They solved adjacent problems; here is precisely which            (§III)
        ↓  "fine — what would a solution have to look like?"
One stimulus API above one transport seam                         (§IV)
        ↓  "does that actually work against real RTL and real silicon?"
Here is how both sides are built, and how it self-checks          (§V)
        ↓  "how do you know you tested the right things?"
Test plan derived from the spec, traced to coverage               (§VI)
        ↓  "show me numbers"
Regression, coverage closure, reuse diff, effort, transport cost  (§VII)
        ↓  "do the abstract's adjectives hold?"
Scalable? modular? vendor-independent? — answered one by one      (§VIII)
        ↓  "what did you learn that I could use?"
Lessons that transfer to other protocols                          (§IX)
        ↓  "where does this break?"
Limitations, stated before the reviewer finds them                (§X)
        ↓
Conclusion                                                        (§XI)
```

The two transitions that currently do not hold in the draft: **§VI → §VII**
(the test plan is described but never traced to a specific result), and
**§VII → §VIII** (the adjectives are never revisited). Both are cheap to fix
and both are where a reviewer's attention naturally lands.

---

## Phase 6 — Novelty analysis

### What is genuinely new
1. **A transport abstraction whose two implementations span the pre/post-silicon
   boundary for one protocol, validated by an unmodified-artifact diff.** Not
   the abstraction itself — the demonstrated identity of the artifact across a
   simulator and a physical chip.
2. **A spec-derived reference model shared by both transports**, so a hardware
   run is self-checking against the same predictor as the simulation run. This
   is genuinely uncommon and is currently *underclaimed* in the draft.
3. **The cross-DUT differential diagnostic as a method**: running one stimulus
   against two designs sharing no RTL, and using the *shape* of a failure
   (both DUTs vs. one) to localise it to verification code vs. design. You
   have two concrete instances. This is the most publishable idea in the paper
   and it is currently buried in §IV-E.
4. **The measured finding that OpenOCD/RBB overhead scales inversely with how
   thin the direct path is** — a real, generalisable, counter-intuitive result.

### What is NOT new — never claim it
- Transaction-level abstraction. (Bergeron, 2003.)
- Separating stimulus intent from transport. (Standard layered testbench.)
- Driving a UVM testbench from Python. (Hua *et al.*; cocotb.)
- Socket or DPI-C bridges between a scripting language and a simulator.
- OpenOCD as a low-level DMI conduit.
- "Write once, run anywhere" as a concept.

### What should be claimed, in this wording
> We do not claim novelty in transaction-level abstraction or in driving a
> simulator from Python; both are established. Our contribution is the
> application of a single transport seam to the RISC-V debug protocol such
> that one unmodified stimulus artifact, checked against one specification-
> derived reference model, executes against both a UVM simulation and physical
> silicon — and the demonstration that this arrangement yields a differential
> diagnostic across dissimilar DUTs that neither environment provides alone.

### How to satisfy Reviewer 2 completely
Open §III-B by conceding the point *before* they can make it: "The
architecture described in §IV is, at the transaction level, a transactor in
the classical sense [4]." Then spend the subsection on the delta. A reviewer
whose objection you have stated more precisely than they did cannot maintain
the objection.

---

## Phase 7 — The Portable Stimulus subsection (§III-A)

Structure this in five short paragraphs. Do **not** claim replacement.

1. **What PSS is.** Declarative action/activity graphs over a resource model,
   solved by a constraint engine to generate scenario variants; targets are
   reached through generated `exec` blocks. Its axis of power is *scenario
   space exploration*.
2. **What this framework is.** An imperative stimulus library over a transport
   seam. Its axis of power is *execution-target portability*. These are
   different axes — that sentence is the whole argument.
3. **Similarities.** Both separate intent from realisation; both aim at
   vertical reuse; both treat the target as pluggable.
4. **Differences, stated as a table** (Table VIII below): abstraction level,
   generation model, transport concept, tooling cost, learning curve, target
   audience.
5. **When each is better, honestly.**
   - **PSS is better** when the problem is combinatorial scenario coverage
     across a large resource model, when a commercial toolchain is already
     licensed, and when scenarios must be portable across *abstraction levels*
     (UVM → C test → post-silicon) rather than across transports.
   - **This framework is better** when the protocol is narrow and deeply
     stateful (debug is a small register space with long causal chains), when
     the same engineers must read the stimulus on both sides of tape-out, and
     when zero tooling cost matters.
   - **Complementary:** PSS generates the activity graph; this framework's
     transport layer serves as the execution backend a PSS `exec` block calls
     into. Say this explicitly and put it in Future Work. R1 and R3 will both
     read it as command of the field rather than defensiveness.

**Sentence to avoid at all costs:** anything resembling "PSS is too expensive
/ too complex / dead." R3's "(rest in peace)" is *their* joke to make, not
yours.

---

## Phase 8 — Experiments, one per abstract promise

### Experiment 1 — "Write-once, execute-anywhere" (the diff experiment)
- **Goal:** prove the stimulus artifact is *identical*, not merely *similar*,
  across targets. This is the single highest-value missing experiment.
- **Setup:** for all 17 scenarios, compute a SHA-256 of each scenario `.py`
  file as executed in simulation and as executed on the Arty A7. Record the
  per-scenario byte-count of the only files that *do* differ (the JSON target
  configs).
- **Metrics:** files shared / files total; lines shared / lines total; lines
  that differ per target.
- **Table V:** `Scenario | Stimulus LOC | SHA match sim vs. HW | Target-config LOC differing`
- **Interpretation:** "N of N stimulus files are byte-identical; the entire
  per-target delta is M lines of declarative configuration."
- **Threats to validity:** if any scenario has a `if transport == ...` branch,
  it must be disclosed — a single such branch, undisclosed and later found by
  a reader, would discredit the whole claim.

#### Experiment 1 — result, measured 2026-07-28

I ran it. It passes cleanly, and it is the strongest single piece of evidence
the paper is currently not using:

- **19 stimulus files, 2259 lines of Python, zero transport-conditional
  branches.** No `if transport == ...`, no `is_hw` flag, no OpenOCD-specific
  path anywhere in the stimulus layer.
- **17 of 17 Ibex scenarios reference an identical stimulus entry point**
  between their simulation and hardware configurations.
- Across all 17 pairs the differing configuration keys are exactly
  `transport`, `uvm`, `openocd` — pure transport declaration.

**One honest exception, which must be disclosed in the paper.** The `halt`
scenario additionally differs in one parameter: `mem_addr` is `0x80000000` in
simulation and `0x00100000` on the Arty A7, because the two targets have
different memory maps. This is *data*, declared in configuration, not logic in
stimulus — which is precisely the argument the architecture makes. Stated
up front it strengthens the claim; discovered by a reviewer after reading
"17/17 identical," it damages it.

**Suggested wording for §VII-D:**
> Across all 17 scenarios, the stimulus files executed against the simulator
> and against the Arty A7 are the same files, and contain no transport-
> conditional logic of any kind (19 files, 2259 lines). The complete per-target
> delta is declarative: a `transport` selector and its connection parameters,
> plus, in one scenario, a memory address reflecting the two targets'
> differing memory maps.

This is Table V. It costs nothing further to produce and it converts the
abstract's central promise from asserted to demonstrated.

### Experiment 2 — "Reduced testbench complexity"
- **Goal:** convert an adjective into a number.
- **Setup:** pick 3 representative scenarios (one simple: halt; one medium:
  GPR write; one complex: program buffer execution). For each, count: (a) the
  Python implementation LOC; (b) the SystemVerilog UVM sequence LOC that would
  be required for the same scenario, measured from the equivalent sequences
  that already exist in the repo; (c) the OpenOCD TCL LOC for the hardware
  equivalent. The alternative workflow needs (b) + (c); this framework needs
  (a) once.
- **Metrics:** LOC ratio; number of languages; number of artifacts to keep in
  sync.
- **Table VI + Figure 6** (grouped bar chart, 3 scenarios × 3 approaches).
- **Threats:** LOC is a weak proxy — say so, and pair it with the "artifacts
  to keep in sync" count, which is the metric that actually reflects
  maintenance cost.

### Experiment 3 — "Improved debuggability"
- **Goal:** the hardest to quantify and therefore the most impressive if done.
- **Setup:** use the two DV bugs and the CVA6 `abstractcs.busy` finding as
  three case studies. For each, record: how the failure presented, what
  localised it, and how many transactions of evidence were needed.
- **Metrics:** the differential signal itself — for each of the 3 defects,
  state whether it appeared on 1 or 2 DUTs, and what that immediately excluded.
- **Table VII:** `Defect | Symptom | Appeared on | Immediately excluded | Located in`
- **Interpretation:** "cross-DUT execution reduced the initial search space
  from {DV code ∪ DUT-A RTL ∪ DUT-B RTL} to one of those three, before any
  waveform was opened."
- **Threats:** n=3 anecdotes, not a controlled study. State that. An honest
  n=3 with mechanism beats a fabricated metric.

### Experiment 4 — Transport cost
Already done and sound. Keep Table IV as-is (becomes Table IX). Add one
sentence naming the practical recommendation, which it already has.

### Experiment 5 — Scalability
- **Goal:** answer the abstract's "scalable" honestly.
- **Setup:** you cannot do multi-hart. Measure the *other* scalability axis
  instead: cost of adding the Nth scenario. Plot cumulative scenario count vs.
  cumulative shared-library LOC over the campaign's git history (512 → 702 →
  718). The shape — scenarios growing while shared library flattens — *is* the
  scalability result.
- **Figure 7:** two lines, scenario count and library LOC, over commit history.
- **Interpretation:** "marginal cost per scenario declines as the primitive
  set saturates."
- **Threats:** does not address hart-count scalability. Say so in §X, and be
  explicit that multi-hart is unaddressed.

### Experiment 6 — Vendor independence
- **Goal:** the abstract claims it; nothing currently supports it.
- **Options, cheapest first:**
  1. **Run one scenario under a second simulator.** Even a single scenario on
     Verilator or Xcelium converts ❌ to 🟡. Your notes indicate Xcelium access
     was being pursued on another server — one scenario is enough.
  2. **Two DUTs from unrelated vendors** (lowRISC Ibex, OpenHW CVA6) with two
     different debug-module versions — you *already have this* and are not
     claiming it. This is the strongest available evidence and it is free.
  3. **Two transports** (DPI-C, OpenOCD) — already have.
- **Recommendation:** claim vendor independence at the *DUT and transport*
  level, which you can prove, and explicitly scope out simulator independence
  unless (1) lands. Do not leave the unqualified adjective standing.

---

## Phase 9 — Figures

| # | Title | Purpose | Contents | Caption | Why necessary | Reviewer addressed |
|---|---|---|---|---|---|---|
| 1 | Debug session state machine | Orient the non-specialist | Idle → activate → halt → abstract cmd → resume, with the DMI registers driving each edge | *Figure 1. Debug Module session states and the DMI registers that drive each transition.* | §VII is unreadable without this vocabulary | All |
| 2 | Dual-transport architecture | The core idea in one image | Existing Figure 1 — stimulus above, seam, two branches below | *Figure 2. Identical Python stimulus above the transport interface reaches a UVM simulation or physical silicon unmodified.* | The paper's thesis | All |
| 3 | Simulation path sequence | Show the bridge is real | Existing Figure 2 | *Figure 3. A Python DMI request crossing the DPI-C bridge into the UVM sequencer.* | Substantiates "high-performance bridge" | R2 |
| 4 | Hardware path sequence | Show symmetry with Fig. 3 | Existing Figure 3 | *Figure 4. The identical request reaching OpenOCD and a physical JTAG scan chain.* | Visual proof the seam is the only difference | R2 |
| 5 | **PSS vs. this framework, layer stack** | Defuse R1/R3 | Two stacks side by side: PSS (model → solver → exec) and this (stimulus → transport → target), with an arrow showing where a PSS `exec` would attach | *Figure 5. Portable Stimulus and this framework operate on different axes; a PSS exec block could target this framework's transport layer.* | **Converts the PSS objection into a roadmap** | R1, R3 |
| 6 | **Coverage closure curve** | Show the campaign, not just the endpoint | Merged coverage % vs. campaign milestone, annotated with what moved each step (sampler fix 77.81→82.44, config-driven bins, new stimulus, → 100.00) | *Figure 6. Functional coverage closure on both DUTs, annotated with the change responsible for each increase.* | The 77.81→82.44 sampler-bug jump is a genuine methodological lesson | R3 |
| 7 | **Effort comparison** | Quantify "reduced complexity" | Grouped bars, 3 scenarios × {Python, SV sequence, OpenOCD TCL} | *Figure 7. Implementation effort per scenario; the conventional workflow requires the second and third bars together.* | Turns the abstract's adjective into a measurement | R2, R3 |

**Template note:** convert all figures SVG → EMF via Inkscape before the
pour-in. You have the SVG sources. The template explicitly calls for this and
raster PNGs in a Word file will look worse than the rest of the proceedings.

---

## Phase 10 — Tables

| # | Table | Purpose | Status |
|---|---|---|---|
| I | Approach comparison (UVM / TCL / manual / PSS / this) | Frames Related Work | ✅ drafted |
| II | Feature cluster → TC-ID count → scenario → covergroups | Proves the test plan is traced, not decorative | ❌ **missing — build it** |
| III | Full regression, both DUTs, per scenario | Core functional result | ✅ drafted (verified numbers) |
| IV | Merged functional coverage | The headline result | ✅ drafted |
| V | **Reuse diff: SHA match per scenario** | Proves "write-once" | ❌ **missing — Experiment 1** |
| VI | **Effort: Python vs. SV+TCL LOC** | Proves "reduced complexity" | ❌ **missing — Experiment 2** |
| VII | **Defect localisation via cross-DUT signal** | Proves "improved debuggability" | ❌ **missing — Experiment 3** |
| VIII | **PSS vs. this framework** | Defuses R1/R3 | ❌ **missing — Phase 7** |
| IX | Transport cost (direct vs. OpenOCD+RBB) | Honest cost accounting | ✅ drafted |
| X | Limitations, each with its scope statement | Pre-empts criticism | ❌ **missing** |

Four of the ten tables that this paper needs do not exist yet, and three of
those four are precisely the ones that discharge the abstract's unmeasured
promises.

---

## Phase 11 — What is missing, and exactly where it goes

| Missing | Belongs in | Severity |
|---|---|---|
| Limitations section | §X, new | **Critical** — its absence is the clearest "this is a brochure" signal |
| Threats to validity per experiment | §VII, one sentence per subsection | **Critical** |
| Assumptions (single hart, JTAG DTM only, no authentication, no native debug) | §IV, stated once up front | High |
| Scalability discussion | §VIII | High — abstract claims it |
| Vendor independence evidence | §VIII + Exp. 6 | High — abstract claims it |
| Complexity measurement | §VII-E + Table VI | High — abstract claims it |
| Debuggability evidence | §VII-G + Table VII | High — abstract claims it |
| API code listings | §IV Listing 1, §V Listing 2 | High — R2 wants to see the seam, not read about it |
| PSS subsection | §III-A | **Critical** — R1 and R3 |
| Transactor delta subsection | §III-B | **Critical** — R2 |
| Broader Python-in-verification related work | §III-C | High — R2's explicit instruction |
| Adoption effort ("what does it cost a team to adopt this?") | §VIII | Medium — R3's "vertical reuse time saving" interest |
| Execution timeline / campaign narrative | §VII-C via Figure 6 | Medium |
| Authors on the abstract | Title block | Trivial, do not forget |

---

## Phase 12 — Risk assessment: how I would reject this paper

**R1. "The novelty claim does not survive contact with Bergeron."**
→ Fix: §III-B concedes the pattern explicitly and narrows the claim to the
cross-boundary artifact identity. Prove it with Table V.

**R2. "The abstract promises reduced complexity and improved debuggability; the
paper measures neither."**
→ Fix: Experiments 2 and 3, Tables VI and VII. This is the most likely
rejection reason and it is entirely within your control.

**R3. "Claims vendor independence, evaluated on one simulator."**
→ Fix: either run one scenario under a second simulator, or re-scope the claim
to DUT-and-transport independence, which you can prove. Do not leave it
unqualified.

**R4. "Claims scalability, then defers multi-hart to future work."**
→ Fix: Experiment 5 measures the scalability axis you *can* measure; §X states
plainly that hart-count scalability is unaddressed. A limitation you name
yourself is not a weakness; one the reviewer finds is.

**R5. "Results are on v0.13 hardware but the abstract claims v1.0."**
→ Fix: lead §VII with CVA6 (v1.0). Present the v0.13/v1.0 pair as the
portability-across-spec-versions result.

**R6. "The 100% coverage number is not credible without knowing what was
excluded."**
→ Fix: you already exclude bins with RTL citations. Put the exclusion list in
the paper as a short table, with the RTL construct justifying each. A reviewer
who sees 100.00% and no exclusion accounting assumes the denominator was
gamed. This is a *presentation* risk on a genuinely sound result.

**R7. "Only 17 directed scenarios; no randomisation, no bug-hunting evidence."**
→ Fix: §X states directed-only as a deliberate scope choice tied to the
CAT1/2/3 derivation; Future Work proposes constrained-random layering. Note
also that the campaign *did* find real defects — cite them as bug-hunting
evidence.

**R8. "The framework was evaluated by its own authors on their own DUTs."**
→ Fix: unavoidable, and true of most DVCon engineering papers. Mitigate by
making everything reproducible: name the commit, the simulator version, the
board, and the exact make targets.

**R9. "The performance comparison is unfair — CVA6 runs unoptimised."**
→ Already handled honestly in the draft. Keep that caveat verbatim; it is a
credibility asset.

**R10. "This is a tool paper, not a methodology paper."**
→ Fix: §IX Lessons Learned, framed so each lesson transfers to a protocol
that is not RISC-V debug. The `hart_signal_bit` insight — that signals a model
receives from another agent with real latency must not be predicted
synchronously — is a general modelling lesson and should be written as one.

---

## Phase 13 — Final checklist against the accepted abstract

| Abstract claim | Status | What closes it |
|---|---|---|
| Debug verification is fragmented | ✅ | — |
| Spec defines stateful interaction | ✅ | — |
| Existing methods lack unified reuse | ✅ | §III + Table I |
| Pre/post-silicon toolchain split | ✅ | — |
| Duplicated effort | 🟡 | Table VI quantifies it |
| Inconsistent test coverage | 🟡 | Table IV, framed as "one coverage model, both targets" |
| Difficulty reproducing corner cases | 🟡 | §VII-D narrative: a scenario run on HW, replayed in sim |
| Delayed silicon bring-up | ❌ | **Either evidence, or cut this clause.** Nothing in the work measures bring-up schedule |
| Write-once, execute-anywhere | 🟡 | **Table V (SHA diff) makes it ✅** |
| Python abstracts transport, preserves intent | ✅ | Figure 2 + Listing 1 |
| Python > TCL: expressive, reusable libraries | 🟡 | Listing 2 side-by-side + Table VI |
| ...advanced automation, scenario composition | 🟡 | Show one composed scenario built from primitives |
| ...data-driven test generation | ❌ | **Either show one data-driven generation instance, or drop this phrase.** Config-driven scenario selection is arguably it — if so, show it |
| High-performance socket bridge | ✅ | Table IX latency figures |
| Without complex SV sequence development | 🟡 | Table VI |
| Same API switches to OpenOCD | ✅ | §V-B, Figure 4 |
| Halt/resume, reg access, **program buffer** unmodified over JTAG | 🟡 | Per-operation hardware results table, program buffer row explicitly |
| True shift-left, validated prior to tape-out | 🟡 | §VII-D worked example |
| Results on a **v1.0 compliant** implementation | 🟡 | Lead with CVA6 |
| Near-complete stimulus reuse | 🟡 | Table V |
| Reduced testbench complexity | ❌ | **Experiment 2 / Table VI** |
| Improved debuggability | ❌ | **Experiment 3 / Table VII** |
| Scalable | ❌ | **Experiment 5, plus honest scoping in §X** |
| Modular | 🟡 | Argued by architecture; make it explicit in §VIII |
| Vendor-independent | ❌ | **Experiment 6, or re-scope the claim** |

**Six ❌ and thirteen 🟡.** The ❌ rows are the paper's real risk, and five of
the six are closable with work you can do without new RTL access:
Tables V, VI, VII, Figure 7, and honest re-scoping in §VIII/§X.

---

## Recommended order of work

1. **§III-A PSS + §III-B transactor subsections** — highest reviewer-risk
   reduction per hour, no experiments needed.
2. **Table V (reuse diff)** — one afternoon, and it converts the paper's
   central claim from asserted to demonstrated.
3. **Table VI (effort)** — the counting is mechanical; the data is in the repo.
4. **Table VII (defect localisation)** — pure writing, the data already exists.
5. **§X Limitations** — pure writing, removes the single clearest reject signal.
6. **Figure 6 (closure curve), Figure 7 (effort)** — the two figures that make
   this look like a results paper.
7. **Re-scope "scalable" and "vendor-independent"** in §VIII.
8. **Template pour-in last** — single column, A4, Heading 5 for
   ACKNOWLEDGMENT/REFERENCES, EMF figures.
