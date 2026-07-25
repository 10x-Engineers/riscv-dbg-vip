# RISC-V Debug Specification v1.0.0-rc3 — Verification Test Plan

This test plan is derived directly from the RISC-V Debug Specification v1.0.0-rc3 (Frozen). It is organized the way the spec itself is: starting from *why* debug support exists (Background, #1.4), then *what* capabilities serve those reasons (the operations a debugger can perform, per Ch.2's System Overview and Ch.3's own introductory list), and only then the concrete registers and protocol elements that implement each capability. A single table carries all three layers so that scanning any one column shows what's covered from that angle, and scanning a full row shows how intention, feature, and mechanism fit together.

This is a **skeleton pass**: every row below is populated at the feature/mechanism-name level, but no `TC-ID` test-case rows exist yet. Those get added incrementally, one CAT2 feature at a time, in the exact `TC-ID | Test Description | Stimulus/Scenario | Expected Result/Check | Priority` table format used for each mechanism once that pass begins, matching the reference test-plan conventions this project has already established.

## Scope and Methodology

### Verification categories

- **Directed tests**: explicit register-write/read sequences verifying each field as specified. Covers all mandatory behaviours and documented enumerations.
- **Constrained-random tests**: randomised hart selection, command sequences, trigger configurations, and system-bus access patterns with functional coverage collection driving closure.
- **Corner-case tests**: boundary values, concurrent operations, reset during active debug, unavailable harts, maximum chain lengths.
- **Negative tests**: illegal command sequences, unsupported register accesses, authentication-bypass attempts, wrong-privilege accesses.
- **Assertion-based checking**: SVA properties embedded in DUT bind modules to catch protocol violations cycle-accurately.

### Priority scheme

| Priority | Meaning |
|---|---|
| P0 | Must-pass. Blocks tapeout. |
| P1 | Should-pass. Required for compliance. |
| P2 | Recommended. Corner case / robustness. |
| P3 | Optional / advanced feature. |

### DUT assumptions

Written generically — these are placeholders to be confirmed per actual DUT, not fixed for any one implementation (this plan itself stays architecture-neutral; per-DUT specifics belong in that DUT's own integration config, per `INTEGRATION_GUIDE.md`):

- DUT implements the JTAG DTM (IR width ≥ 5, IDCODE present).
- `PROGBUF_SIZE` and `DATA_COUNT` are DUT-configurable; confirm actual values before writing Program-Buffer/Abstract-Command TC-IDs.
- Confirm which Sdtrig trigger types (`mcontrol`/`mcontrol6`, `icount`, `itrigger`, `etrigger`, `tmexttrigger`) are implemented via `tinfo` before writing Trigger Module TC-IDs.
- SBA block presence and supported access widths (8/16/32/64/128-bit) are DUT-configurable; confirm via `sbcs.sbaccess*` bits.
- Authentication is optional; test only if `HAS_AUTHENTICATION=1` for that DUT.

## Feature Traceability Table (CAT1 | CAT2 | CAT3)

**CAT1 (intention)** is the use case from #1.4 Background. **CAT2 (feature)** is the operation/capability from Ch.2's System Overview and Ch.3's own introductory numbered list of DM operations (Required/Optional tags are the spec's own). **CAT3 (mechanism)** is the concrete register/protocol element that implements that feature, with its spec citation.

Underlying every row: the JTAG Debug Transport Module (Ch.6 — IDCODE, `dtmcs`, `dmi`, BYPASS) carries every DMI operation listed here; that dependency is noted once here rather than repeated per row, but the DTM/DMI protocol itself gets its own CAT2 row above (and its own `DTM`-prefixed TC-IDs below) since the protocol layer's own behavior — sticky busy/error, `nextdm` chaining, IR/DR shift lengths — is directly testable and is the cheapest, first thing to verify on any new DUT (per `VERIFICATION_STRATEGY.md`'s phased approach). The JTAG connector pinout (#6.1.7) is physical/mechanical and out of scope for a functional test plan.

| CAT1 (intention, #1.4) | CAT2 (feature) | CAT3 (mechanism) |
|---|---|---|
| External debug | DMI register access protocol (op/busy/error, `nextdm` chaining) [Ch.6, underlies every row below] | `dtmcs.dmistat`/`dmireset`/`idle`/`abits`, `dmi.op`/`address`/`data`, `nextdm` (multi-DM chaining pointer) (#3.1, #6.1.4–5) |
| External debug | Discover DM/implementation info [Ch.3 op 1, Required] | `dmstatus.version`, `confstrptr0-3`/`confstrptrvalid`, `hartinfo` (#3.13 Version Detection, #3.14.1/.3/.9–12) |
| External debug | Version detection — exact spec-mandated procedure [#3.13, own subsection] | `dmcontrol` read/preserve-bits/write/poll sequence, `dmstatus.version` (#3.13) |
| External or native debug | Halt / resume individual hart [Ch.3 op 2, Required] | `dmcontrol.haltreq`/`resumereq`, `dmstatus.allhalted`/`anyhalted`/`allrunning`/`anyrunning` (#3.5, #3.14.2) |
| External or native debug | Report hart halt status [Ch.3 op 3, Required] | `dmstatus` halt-status bits, `haltsum0-3` (#3.14.1, #3.14.18–21) |
| External debug (accessing HW with no working CPU; low-level SW debug) | Abstract GPR read/write [Ch.3 op 4, Required] | Access Register abstract command (`cmdtype=0`), `data0-11` (#3.7.1.1, #3.14.14) |
| Bootstrapping before any executable code path; low-level SW debug | Reset signal / debug from first instruction [Ch.3 op 5, Required] | `dmcontrol.ndmreset`/`hartreset`, `dmstatus.allhavereset`/`anyhavereset`/`ackhavereset` (#3.2, #3.14.2) |
| Bootstrapping before any executable code path | Halt-on-reset [Ch.3 op 6, Optional] | `dmstatus.hasresethaltreq`, `dmcontrol.setresethaltreq`/`clrresethaltreq` (#3.5, #3.14.1–2) |
| Debugging low-level software; debugging the OS itself | Abstract access to non-GPR registers (CSRs) [Ch.3 op 7, Optional] | Access Register on CSR `regno`s (#3.7.1.1, Table 4) |
| Debugging low-level software with no OS present | Program Buffer — execute arbitrary instructions on a halted hart [Ch.3 op 8, Optional] | `progbuf0-15`, `postexec` (#3.8, #3.14.15) |
| Accessing hardware with minimal intrusion on a running system | Quick Access — run one abstract command without a full halt [Ch.3 op 8 sibling, #3.7.1.2, Optional] | `command` (`cmdtype=1`), implicit haltreq/resumereq around the command (#3.7.1.2) |
| Debugging the OS itself; debugging processes on an OS | Multi-hart halt/resume/reset (hart array mask) [Ch.3 op 9, Optional] | `hasel`, `hawindowsel`/`hawindow` (#3.3.2, #3.14.4–5) |
| Debugging low-level software; debugging the OS itself | Memory access from the hart's point of view [Ch.3 op 10, Optional] | Access Memory abstract command (`cmdtype=2`) (#3.7.1.3) |
| Accessing hardware with no working CPU | Direct System Bus Access [Ch.3 op 11, Optional] | `sbcs`, `sbaddress0-3`, `sbdata0-3` (#3.10, #3.14.22–30) |
| Debugging the OS itself; debugging processes on an OS | Hart grouping — halt group [Ch.3 op 12, Optional] | `dmcs2.grouptype`/`group`/`hgselect`/`hgwrite` (#3.6, #3.14.17) |
| Debugging processes on an OS (multi-component sync) | External trigger halt response [Ch.3 op 13, Optional] | `dmcs2.dmexttrigger` + halt-group notification (#3.6, #3.14.17) |
| Debugging processes on an OS (multi-component sync) | External trigger resume signaling [Ch.3 op 14, Optional] | `dmcs2` resume-group notification (#3.6, #3.14.17) |
| Debugging processes on an OS (multi-component sync) | Resume group assignment & propagation [Ch.3 op 12 sibling, #3.6, Optional] | `dmcs2.grouptype=1`/`group`/`hgselect`/`hgwrite` (#3.6, #3.14.17) |
| External debug (IP protection) | Authentication / DM locking [#3.12, own subsection, not in Ch.3's numbered list] | `dmstatus.authenticated`/`authbusy`, `authdata` (#3.12, #3.14.16) |
| Native debug (per #1.4's own framing) | Hart-side Trigger Module — halt on match [Fig.1 box + #1.5 feature 16] | Ch.5 Sdtrig in full: `tselect`/`tdata1-3`, `mcontrol`/`mcontrol6`, `icount`, `itrigger`, `etrigger`, `tmexttrigger` |
| External debug (entry) or native debug (from within Debug Mode itself) | Sdext — Debug Mode entry/exit & Core Debug Registers [Ch.4, #4.1–#4.9, own subsection] | `dcsr` (`cause`/`ebreakm/s/u/vs/vu`/`prv`/`v`/`stepie`/`stopcount`/`stoptime`/`mprven`/`nmip`), `dpc`, `dscratch0-1` (#4.1, #4.5, #4.9.1–2) |
| Debugging low-level software; debugging processes on an OS | Hardware single-step [#1.5 feature 8] | `dcsr.step` (#4.5), `icount` trigger as native-debugger alternative |

## Test Cases

This pass covers every CAT2 row in the Feature Traceability Table above — 161 TC-IDs total across ISA (Sdext debug-mode/core-debug-registers, single-step, Sdtrig trigger module) and non-ISA (DTM/JTAG, DMI protocol, DM registers, run control, abstract commands, program buffer, system bus access, halt/resume groups, authentication) feature areas, plus the four cross-cutting process areas (coverage model, SVA assertions, negative/error-injection, regression tiers). Every row states its directed tests first, then corner-case/negative variants as distinct TC-IDs, per this project's established discipline.

**Be honest about what's behind each TC-ID, since this document only specifies *what* to verify, not that it's all been run.** Only the Reset Control / Run Control cluster (`RC`/`RST`/`HOR`, plus `DMA` and the single-field slice of `HS`) has a live golden model (`src/pydebug/model/predictor.py`), stimulus (`src/pydebug/sequences/*.py`), and recorded simulation runs (CVA6, `testplans/results/run_control_cluster_cva6_2026-07-17.md` then `..._2026-07-25.md` — the later run gets all five scenarios clean against CVA6 for the first time, `run_control` and `reset_control`/`halt_on_reset`/`hart_selection` having been blocked or never wired before) behind it — 23 TC-IDs, closing 88/103 functional-coverage bins for that cluster (measured, not estimated; `cross.hart_state_transition.halted_to_in_reset` is excluded as of 2026-07-25, confirmed unreachable via any stimulus on either DUT — see the later results file). Every other prefix added in this pass (`DTM`, `DMI`, `DHS`, `DIS`, `VER`, the rest of `HS`, `AC`, `QA`, `AM`, `PB`, `SBA`, `MID`, `HG`, `AUTH`, `DCSR`, `SSTEP`, `TRIG`, and the cross-cutting `COV`/`SVA`/`NEG`/`REG` clusters) is a **testplan-level specification with no model or stimulus behind it yet** — `src/pydebug/model/registers.py` only encodes `dmcontrol`/`dmstatus` fields today, so this is a real, stated gap, not a silently-assumed one. Their **Bins** columns state the *intended* combinatorial coverage scope for when a model exists, not a measured count (see `TC-COV-002`). This is exactly the "has a test-plan row, zero stimulus" gap the project's own gap-matrix ranking (in `VERIFICATION_STRATEGY.md`) is built to surface — that document's gap matrix should be re-walked against this expanded table next, rather than assuming everything below is closed because it has a TC-ID.

Every row below carries a **Bins** entry: the count of functional-coverage bins
(`src/pydebug/model/coverage.py`'s `DebugCoverageModel`) that TC-ID is the
designated owner of, driving the actual coverage-closure numbers reported per
section. These were measured, not estimated — replaying each TC-ID's write
sequence through the golden model and reading back `DebugCoverageModel.report()`.

### Halt / Resume individual hart (Ch.3 op 2, #3.5) — prefix `RC`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-RC-001 | Halt request on a running hart | Select hart, write `dmcontrol.haltreq=1` | Hart halts: `running` deasserted, `halted` asserted; `dmstatus.anyhalted`/`allhalted=1` | 41 (the activation/baseline row — every dmcontrol/dmstatus field's reset-adjacent value, `haltreq×resumereq=h1_r0`, `running→halted` transition) | P0 |
| TC-RC-002 | Halt request ignored once already halted | With hart halted, write `haltreq=1` again | No effect — spec: "Halted harts ignore their halt request bit" | 0 (idempotency; no new bin — this is an invariant check, not a coverage bin) | P1 |
| TC-RC-003 | Resume request on a halted hart | Select halted hart, write `dmcontrol.resumereq=1` | Hart resumes: `halted` deasserted, `running` asserted, resume-ack bit set; `dmstatus.allresumeack`/`anyresumeack=1`, `allrunning`/`anyrunning=1` | 14 (`haltreq×resumereq=h0_r1`, `halted→running` transition, `resumereq_x_prior_state=resumereq_when_halted`, mutex bit `one`) | P0 |
| TC-RC-004 | Resume request ignored on a running hart | With hart running, write `resumereq=1` | No effect — spec: "Resume requests are ignored by running harts" | 4 (`resumereq_x_prior_state=resumereq_when_running`, `all/anyresumeack=0` — the #3.5 asymmetry: resume-ack is cleared even though the request itself is ignored) | P1 |
| TC-RC-005 | `resumereq` ignored when `haltreq` also set | Write `dmcontrol` with both `haltreq=1` and `resumereq=1` in the same access | `resumereq` has no effect — spec: "resumereq is ignored if haltreq is set" | 1 (`haltreq×resumereq=h1_r1` — the only stimulus that reaches this cross bin) | P1 |
| TC-RC-006 | Halt/resume response latency | Measure cycles between request and status-bit update | Hart responds in under 1 second (spec bound); typical implementations: a few clock cycles | 0 (cycle-domain property; no meaning in the untimed Python model — SVA-only, see Uncertain bucket below) | P2 |
| TC-RC-007 | `resumereq` while the hart is in reset | Assert `ndmreset`/`hartreset`, then write `resumereq=1` while still asserted | No effect — the hart is neither halted nor running while in reset, so "resume ack is cleared, halted hart resumes" does not apply; confirm no spurious halt/run transition | 1 (`resumereq_x_prior_state=resumereq_when_in_reset`) | P2 |

### Reset signal / debug from first instruction (Ch.3 op 5, #3.2) — prefix `RST`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-RST-001 | `ndmreset` platform reset | Write `dmcontrol.ndmreset=1`, then `0` | Every hart and platform component except DM/DTM/DMI resets; `dmstatus.ndmresetpending=1` while asserted | 6 (`ndmreset=0/1`, `ndmresetpending=0/1`, `running↔in_reset` transitions, `ndmreset_x_reset_haltreq=assert_rhr0`) | P0 |
| TC-RST-001 (cont'd) | `haltreq` asserted while a hart is in `ndmreset` | Assert `ndmreset`, write `dmcontrol.haltreq=1` while still in reset, then deassert `ndmreset` | Hart stays reported not-halted while reset is asserted; enters Debug Mode the moment reset deasserts (#3.5: a pending halt request takes effect on reset release) — this is the universally-supported substitute for `TC-HOR-002`'s `setresethaltreq` on any DUT with `hasresethaltreq=0` (both project DUTs), and is what actually owns the `in_reset→halted` transition bin on those DUTs | 1 (`hart_state_transition.in_reset_to_halted`) | P1 |
| TC-RST-002 | `hartreset` selected-hart reset | Write `dmcontrol.hartreset=1` for the currently selected hart(s), then `0` | Only currently selected hart(s) reset (implementation may reset more; discover via `anyhavereset`/`allhavereset` on other harts) | 3 (`hartreset=1`, `halted→in_reset` transition, `dmcontrol` read-back/WARL discovery) | P1 |
| TC-RST-003 | `havereset` set regardless of reset cause | Trigger reset via each cause the DUT supports (`ndmreset`, `hartreset`, external reset if present) | `dmstatus.anyhavereset`/`allhavereset` becomes set after each, regardless of which cause was used | 4 (`all/anyhavereset=1`, `havereset_x_ackhavereset=noack_when_set` — proves stickiness) | P1 |
| TC-RST-004 | `ackhavereset` clears the sticky bit | After a reset, write `dmcontrol.ackhavereset=1` for the selected hart(s) | `dmstatus.anyhavereset`/`allhavereset` clears for those harts | 5 (`ackhavereset=1`, `all/anyhavereset=0`, `havereset_x_ackhavereset=ack_when_set`) | P0 |
| TC-RST-005 | DMI access restrictions while reset is asserted | While `ndmreset` (or external reset) is asserted, attempt DMI operations other than `dmcontrol` read/write and `ndmresetpending` read | Behavior for other accesses is UNSPECIFIED per spec — check does not hang/crash the DM, not a specific value | 0 (UNSPECIFIED by spec; see Uncertain bucket) | P2 |
| TC-RST-006 | `ackhavereset` when `havereset` is already clear (no-op) | Write `dmcontrol.ackhavereset=1` for a hart whose `havereset` is already 0 | No effect — must be a harmless no-op, not an error | 1 (`havereset_x_ackhavereset=ack_when_clear`) | P2 |

### Halt-on-reset (Ch.3 op 6, #3.5, optional) — prefix `HOR`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-HOR-001 | Discover halt-on-reset support | Read `dmstatus.hasresethaltreq` | If 0, mechanism not implemented — remaining `HOR` cases are N/A for this DUT, not failures | 2 (`hasresethaltreq=0/1` — the gate itself) | P0 (gate) |
| TC-HOR-002 | `setresethaltreq` causes halt-on-reset | Write `dmcontrol.setresethaltreq=1` for selected hart, then assert/deassert reset (any cause). The write itself now always happens (2026-07-25), gated only for the functional halt assertion, so `setresethaltreq=1` write-coverage and the `ndmreset_x_reset_haltreq=assert_rhr1`/`deassert_rhr1` bins close on every DUT regardless of `hasresethaltreq` | Hart enters Debug Mode immediately on reset deassertion, regardless of reset cause — checked only when `hasresethaltreq=1`; on both project DUTs (`hasresethaltreq=0`) the write still happens but the functional check is N/A, and `in_reset→halted` is instead owned by `TC-RST-001 (cont'd)`'s universally-supported `haltreq`-during-reset path | 3 (`setresethaltreq=1`, `ndmreset_x_reset_haltreq=assert_rhr1`/`deassert_rhr1`; `in_reset→halted` moved to `TC-RST-001 (cont'd)`) | P1 |
| TC-HOR-003 | `clrresethaltreq` clears the request | After `setresethaltreq=1`, write `clrresethaltreq=1` before the next reset. Same "always write, gate only the functional check" pattern as `TC-HOR-002` (2026-07-25) | Hart does *not* halt on the next reset deassertion — checked only when `hasresethaltreq=1`, N/A otherwise | 2 (`clrresethaltreq=1`, `ndmreset_x_reset_haltreq=deassert_rhr0` — this bin is shared proof that `clrresethaltreq` worked) | P1 |
| TC-HOR-004 | Per-hart independence | With two harts selected differently (one `setresethaltreq`, one untouched), reset both | Only the configured hart halts on reset; the other's behavior is undisturbed — the specific reason `set`/`clrresethaltreq` are split into two write-only bits | 2 (`hartsel=nonzero`/`max_implemented` — this is the only TC-ID that selects a hart other than 0) | P2 |
| TC-HOR-005 | Illegal simultaneous bit writes (negative) | Write `dmcontrol` with more than one of `{resumereq, hartreset, ackhavereset, setresethaltreq, clrresethaltreq}` set to 1 at once | Spec requires at most one such bit per write; confirm the DUT's documented/defined handling and that DM state is not corrupted | 1 (`dmcontrol_mutex_bits=multiple`) | P2 |

### Keep-alive (`dmcontrol.setkeepalive`/`clrkeepalive`, #3.14.2, optional) — prefix `KA`

Confirmed present in this project's exact targeted spec tag (`riscv/riscv-debug-spec` **v1.0.0-rc3**, checked directly against that tag's `xml/dm_registers.xml`, 2026-07-25) — resolves the previously-open "was keepalive added after rc3?" question below and in the Uncertain bucket. Same optional, write-only-discovery status as `set`/`clrresethaltreq`: `keepalive` cannot be read back (#3.14.2), and neither `registers.py`/`predictor.py` nor `dmstatus` model/report a `keepalive` hart-state field, so there is no functional golden-model behavior to check beyond "the DM survives the write."

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-KA-001 | `setkeepalive`/`clrkeepalive` discovery probe | Write `dmcontrol.setkeepalive=1`, read back, then write `dmcontrol.clrkeepalive=1`, read back | DM remains alive (`dmactive=1`) throughout both writes — discovery-only, no readable `keepalive` state to assert on (#3.14.2) | 2 (`setkeepalive=1`, `clrkeepalive=1`) | P2 |

### DM Activation (`dmactive`) — prefix `DMA`

Not a Ch.3-numbered operation in its own right, but every other row in this
document depends on it, and it was a genuine coverage gap: no TC-ID above ever
writes `dmactive=0` even though #3.14.2 prescribes a specific known-state
recovery sequence for it.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DMA-001 | Deactivate resets DM to defaults | Write `dmcontrol.dmactive=0` | All DM state (including authentication) returns to reset values; `dmactive` is the only bit guaranteed writable to something other than reset while inactive | 1 (`dmactive=0`) | P1 |
| TC-DMA-002 | Known-state reset sequence | Write 0 → poll until 0 → write 1 → poll until 1 (spec's own documented procedure, #3.14.2 dmactive) | DM reaches a known-good state; usable as a shared precondition fixture for every other suite in this document | 0 (procedural; no new bin beyond TC-DMA-001/existing `dmactive=1`) | P1 |

### Hart Selection (`hasel`, `hartsello`, `hartselhi`) — prefix `HS`

Ch.3 op 9's mechanism (`hasel`), tested here at the single-field level; the
hart-array-mask register content itself (`hawindowsel`/`hawindow`) is a
separate, not-yet-started slice.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-HS-001 | `HARTSELLEN` discovery (WARL) | Write all-1s across the full 20-bit `hartsello`+`hartselhi` field, read back | Only the implemented low `HARTSELLEN` bits stick — the spec's own documented discovery method | 2 (`hartsel=all_ones`, `hartselhi_nonzero`) | P0 |
| TC-HS-002 | Nonexistent hart index selected | Write `hartsel` to an index beyond the DUT's implemented hart count | `dmstatus.anynonexistent`/`allnonexistent` set for that selection | 3 (`hartsel=nonexistent`, `all/anynonexistent=1`) | P1 |
| TC-HS-003 | `hasel` discovery write | Write `hasel=1`, read back | 1 if the hart-array-mask register is implemented, 0 (WARL-tied) otherwise — per spec: "should set this bit and read back to see if the functionality is supported" | 1 (`hasel=1`) | P2 |

### Report hart halt status (Ch.3 op 3, #3.4/#3.14.1) — prefix `DHS`

`allhalted`/`anyhalted`/`allrunning`/`anyrunning` themselves are already exercised as a side effect of every `RC` TC-ID above; this cluster is what's left — the summary/aggregate mechanisms (`haltsum0-3`) and the two states beyond halted/running (`nonexistent`, `unavail`) that `RC` never touches.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DHS-001 | `haltsum0` reflects the halted-hart bitmap | Halt a known subset of harts (via `RC`'s `TC-RC-001` per hart), read `haltsum0` | Bit `i` of `haltsum0` set iff hart `i` (within the current 32-hart window) is halted, matching `dmstatus.anyhalted` for that same selection | 2 (`haltsum0` all-clear / at-least-one-bit-set) | P1 |
| TC-DHS-002 | `haltsum1`–`haltsum3` window selection (>32 harts, gated) | Read `dmstatus`-adjacent hart count; if ≤32 harts implemented, mark N/A. Otherwise write `hawindowsel`-equivalent select field and read `haltsum1`/`haltsum2`/`haltsum3` | Each level correctly summarizes the next-lower level's all-zero/any-set state for its window, per #3.14.19–21 | 1 (gate: N/A vs. exercised) | P2 |
| TC-DHS-003 | `anynonexistent`/`allnonexistent` for an out-of-range hart | Cross-reference: covered by `TC-HS-002` (Hart Selection) — not re-tested here to avoid duplication, since it's the same stimulus and the same bit | n/a | 0 (see `TC-HS-002`) | — |
| TC-DHS-004 | `anyunavail`/`allunavail` set for an unavailable hart | Drive a hart into an implementation-defined "unavailable" state (DUT-specific — e.g. powered down, held in a non-DM reset domain); read `dmstatus` | `anyunavail`/`allunavail` set for that hart's selection | 2 (`anyunavail`/`allunavail` = 0/1) | P2 — confirmed N/A on both current SoC integrations: `CVA6-fork/corev_apu/tb/ariane_testharness.sv` and `ibex-demo-system/rtl/system/ibex_demo_system.sv` both hardwire the DM's `unavailable_i` input to constant 0 (checked directly against RTL, 2026-07-25), so this state is structurally unreachable via any DMI stimulus on either DUT, not just unimplemented; excluded in `coverage.py`/`covergroups.sv` with this citation |
| TC-DHS-005 | `stickyunavail` latches through a transient unavailable→available transition | With `stickyunavail=1` (DUT-configurable, #3.14.1), drive a hart unavailable then available again, read `dmstatus.allunavail` before `ackunavail` | `allunavail` remains 1 across the transition — this is what "sticky" means | 1 (`stickyunavail=1` path) | P2 — CVA6 now reports `stickyunavail=1` (`dut_configs/cva6.json`, closed via riscv-dbg-vip#117/#128/#131); Ibex still reports 0. The `stickyunavail=1` capability bit itself is exercised (Pass C, `test_coverage_and_assertions.py`), but the full unavailable→available transition still needs `TC-DHS-004`'s hart-availability drive mechanism, which is N/A on both DUTs per that row — so this remains blocked on the same root cause, not stickyunavail's config value |
| TC-DHS-006 | `ackunavail` clears only currently-available harts | With one hart unavailable and one available-but-previously-unavailable (sticky bit set), write `dmcontrol.ackunavail=1` for both via a hart-array-mask selection | Sticky bit clears for the now-available hart only; the still-unavailable hart's bit is unaffected (conditional-clear semantics, #3.14.2 `ackunavail`) | 2 (`ack_when_available`, `ack_when_still_unavailable`) | P2 — write-only half (the `ackunavail=1` write itself, DM stays alive) now closed via a discovery probe in `reset_ctrl_sequence.py` (2026-07-25); the full conditional-clear semantics above still needs `TC-DHS-004`'s hart-availability mechanism, which is N/A on both current DUTs — see that row |

### Discover DM/implementation info (Ch.3 op 1, #3.13/#3.14) — prefix `DIS`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DIS-001 | `confstrptrvalid` gates `confstrptr0-3` | Read `dmstatus.confstrptrvalid` | If 0, `confstrptr0-3` content is meaningless (spec leaves it unspecified) — remaining rows below are N/A for this DUT unless `confstrptrvalid=1` | 1 (gate) | P1 (gate) |
| TC-DIS-002 | `confstrptr0-3` read (config string pointer), gated by `TC-DIS-001` | With `confstrptrvalid=1`, read all four `confstrptr` registers | Concatenated value is a valid pointer to the DUT's configuration string per #3.14.9–12 — DUT-specific content, check only that the four registers read consistently across repeated reads | 1 (`confstrptrvalid=1` path) | P2 |
| TC-DIS-003 | `hartinfo.nscratch`/`dataaddr`/`datasize`/`dataaccess` discovery | Read `hartinfo` for the selected hart | Fields report the DUT's actual scratch-register/memory-mapped-`data` configuration (WARL-adjacent, read-only) — used later by Abstract Command TC-IDs that fall back to memory-mapped `data0-11` | 4 (`dataaccess=0` register-backed / `=1` memory-backed, `nscratch=0`/`nonzero`) | P1 |
| TC-DIS-004 | Per-hart `hartinfo` independence | Read `hartinfo` for two different `hartsel` values (if the DUT implements >1 hart with heterogeneous config) | Each hart's `hartinfo` may legitimately differ — confirm the read tracks `hartsel`, not a single DM-wide value | 1 (`hartinfo` varies across `hartsel`) | P2 |

### Version detection — exact procedure (#3.13, own CAT2 row) — prefix `VER`

Distinct from `TC-DMA-002`'s known-state *reset* sequence: this is the spec's documented procedure for a debugger encountering a DM in an **unknown prior state** (first contact), which must not clobber whatever the DM was already doing.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-VER-001 | Version read without disturbing prior DM state | Read `dmcontrol` first (do not write), then read `dmstatus.version` without ever writing `dmactive` | `version` is readable and non-`custom`/non-`0.11`-for-this-project even before this debugger session ever activates the DM itself — proves version discovery doesn't require a write | 1 (pre-activation `version` read) — same bin as `RC`'s pre-activation baseline step, cited here for the CAT2 row's own traceability | P0 |
| TC-VER-002 | `version=0` (no DM present) is distinguishable | Point the same read at a DMI address with no DM behind it (if the platform has one) or use the "before first `dmactive` write" window | Reading all-zero / `version=0` is treated as "no Debug Module," not as a valid DM reporting v0.11-equivalent | 1 (`version=0`) | P2 — platform-dependent; see Uncertain if no such address exists on either project DUT |

### JTAG Debug Transport Module (Ch.6, #6.1) — prefix `DTM`

Cheapest, first thing to verify on any new DUT (per `VERIFICATION_STRATEGY.md`'s phased approach) — everything above depends on this layer working. No TC-IDs here touch `dmcontrol`/`dmstatus` content; they only prove the transport carrying those registers is sound.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DTM-001 | IDCODE read after TAP reset | Force TAP to Test-Logic-Reset, shift IR to select IDCODE, shift out DR | IDCODE read back matches the DUT's known manufacturer/part/version encoding, LSB=1 (#6.1.1) | 1 | P0 |
| TC-DTM-002 | IR width covers all defined instructions (≥5 bits) | Shift IR through every value 0..2^IRLEN−1 | DTMCS/DMI/BYPASS/IDCODE all remain selectable; no illegal-IR value corrupts DR shift length | 1 (IR width sufficiency) | P0 |
| TC-DTM-003 | BYPASS mode single-bit shift | Select BYPASS instruction, shift a known bit pattern through DR | DR behaves as exactly one bit of delay — output matches input shifted by one TCK | 1 | P1 |
| TC-DTM-004 | `dtmcs.version`/`abits` discovery | Select DTMCS instruction, read DR | `version` reports the DTM's spec version (0.11 vs 1.0 encodings differ); `abits` reports the actual DMI address width implemented | 2 (`version`, `abits` values) | P0 |
| TC-DTM-005 | `dtmcs.idle` — DUT-required idle cycles are honored | Read `dtmcs.idle`, then run exactly that many Run-Test/Idle cycles between DMI scans (not more, not fewer) | DMI operations complete without spurious busy/error, confirming the debugger-side driver actually reads and respects this field rather than hardcoding a guess | 1 | P1 |
| TC-DTM-006 | `dtmcs.dmireset` clears sticky DMI error | Force a sticky DMI error (see `TC-DMI-004` below), then write `dtmcs.dmireset=1` | Sticky error state clears; subsequent DMI operations proceed normally | 1 | P1 |
| TC-DTM-007 | `dtmcs.dmihardreset` resets the DTM itself | Write `dtmcs.dmihardreset=1` mid-session (with a pending or stuck DMI operation) | DTM returns to its power-on state; in-flight DMI operation is abandoned rather than silently completed — DM-side state (`dmcontrol`/`dmstatus`) is unaffected, since this resets the DTM, not the DM | 1 | P2 |

### DMI Protocol (#3.1, #6.1.5) — prefix `DMI`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DMI-001 | `dmi.op=0` (nop) round trip | Issue a DMI nop | No register side effect; `data`/`address` from the previous operation are returned per #6.1.5's documented nop semantics | 1 | P1 |
| TC-DMI-002 | `dmi.op=1` (read) valid address | Read a known-implemented DMI address (e.g. `dmstatus`) | Correct register content returned, `op` on readback indicates success | 1 | P0 |
| TC-DMI-003 | `dmi.op=2` (write) valid address round trip | Write then read back a known R/W DMI register (`dmcontrol`) | Written value observed on next read (modulo WARL/W1 fields' own documented behavior, tested per-register above) | 1 | P0 |
| TC-DMI-004 | Access to an unimplemented DMI address | Issue `dmi.op=1`/`2` at an address the DUT does not implement | Sticky error indicated per #6.1.5 (not silently accepted as a no-op with success status) — this is the fixture `TC-DTM-006` clears | 1 | P1 |
| TC-DMI-005 | Sticky busy under back-to-back scans with insufficient idle | Issue two DMI operations with fewer than `dtmcs.idle` Run-Test/Idle cycles between them | Second operation reports sticky busy; the *first* operation's result is not corrupted/lost — sticky specifically so a debugger that didn't poll can still tell something needs retrying | 1 | P1 |
| TC-DMI-006 | Batched-scan-with-injected-failure (named use case, #6.1.5) | Queue a multi-operation batch (e.g. write `progbuf0-3` then issue an abstract command) without checking status after each individual scan, deliberately forcing one intermediate scan to hit busy | The sticky error correctly identifies that *some* operation in the batch failed; the debugger can distinguish "all succeeded" from "one failed" without having polled every step — the specific design intent #6.1.5 documents for making busy/error sticky rather than per-transaction | 1 | P1 |
| TC-DMI-007 | `nextdm` chaining (multi-DM platform only) | On a platform implementing more than one DM, read the first DM's `nextdm`-equivalent pointer | Value correctly identifies the DMI base address of the next DM in the chain; N/A on a single-DM platform (both project DUTs) | 1 | P3 — mark N/A on single-DM DUTs |

### Multi-hart halt/resume/reset — hart array mask (Ch.3 op 9, #3.3.2) — prefix `HS` (continues from `TC-HS-003`)

`TC-HS-003` already proves `hasel` itself is discoverable; these rows exercise the actual hart-array-mask register content and the simultaneous multi-hart operations it exists for.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-HS-004 | `hawindowsel` selects a 32-hart window | Write `hawindowsel` across its implemented range, read back | Only the DUT's actually-implemented window-select bits stick (WARL, discovery pattern mirrors `TC-HS-001`) | 1 | P1 |
| TC-HS-005 | `hawindow` bit-to-hart mapping | With `hasel=1` and a given `hawindowsel`, write a single bit of `hawindow`, read back | Bit `i` of `hawindow` maps to hart `(hawindowsel × 32 + i)` per #3.3.2 — confirmed via a walking-one pattern across the register | 1 | P0 |
| TC-HS-006 | Simultaneous multi-hart halt via mask | Set `hasel=1`, mark two harts in `hawindow`, write a single `haltreq=1` | Both marked harts halt from one request (`dmstatus.allhalted` true for that pair) — the actual value-add over single-hart `hartsel` | 1 | P0 |
| TC-HS-007 | Simultaneous multi-hart resume via mask | With both harts halted (`TC-HS-006`), write a single `resumereq=1` | Both marked harts resume together | 1 | P0 |
| TC-HS-008 | Hart outside the mask is undisturbed (independence proof) | Repeat `TC-HS-006` with a third hart deliberately left unmarked in `hawindow` | The unmarked hart's halt/run state is unaffected — the write-isolation discipline this project already applies to Features 4/6 in `VERIFICATION_STRATEGY.md`, here at the register-mask level instead of the constrained-random level | 1 | P1 |
| TC-HS-009 | `hawindow` write does not disturb `hartsel` | Write `hawindow`, then read `dmcontrol.hartsel` | `hartsel` (the single-hart selector) is unchanged — proves the two selection mechanisms (`hartsel` vs. `hasel`/`hawindow`) are independent registers, not aliased | 1 | P2 |

### Abstract Command: Access Register — GPR + CSR (Ch.3 op 4/7, #3.7.1.1) — prefix `AC`

Baseline assumption stated once here, not per row: hart is halted before every `AC` row below unless the row is itself testing what happens when it isn't (`TC-AC-008`).

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-AC-001 | GPR read via Access Register (mandatory) | Access Register command, `cmdtype=0`, `transfer=1`, `write=0`, `regno`=GPR encoding, for each of `x0`–`x31` | Correct register content returned in `data0` (widened per `aarsize` for `x0`/`ra`/`sp` spot checks); `cmderr=0` | 32 (one per GPR) | P0 |
| TC-AC-002 | GPR write + read-back (mandatory) | Access Register `write=1` with a known pattern, then `write=0` read-back, for each of `x0`–`x31` | Written value observed on read-back, except `x0` which must read back 0 regardless of what was written (base-ISA invariant, worth its own directed check) | 32 | P0 |
| TC-AC-003 | `aarsize` WARL discovery | Attempt Access Register at each of the spec's defined `aarsize` encodings (8/16/32/64/128-bit) | Sizes the DUT's XLEN doesn't support report `cmderr=2` (not supported); supported sizes complete with `cmderr=0` | 5 (one per `aarsize` encoding) | P1 |
| TC-AC-004 | Register write-isolation | Write `x1` via Access Register, then read `x2` | `x2` unchanged — write-isolation discipline for the `data0-11`/`regno`-indexed register group | 1 | P1 |
| TC-AC-005 | CSR access is optional — discovered by attempting it, not by querying capability | Access Register on a `regno` mapping to a CSR | `cmderr=0` with correct CSR content if implemented; `cmderr=2` if not — either is a pass, per the Design Rationale Notes callout above; only a hang or a wrong value is a failure | 1 (implemented) + 1 (unsupported, `cmderr=2`) | P1 |
| TC-AC-006 | `cmderr=1` (busy) — new command issued while one is in flight | Issue an Access Register command, then issue a second one before the first's `abstractcs.busy` clears | Second command is rejected with `cmderr=1`; first command's result is not corrupted | 1 | P1 |
| TC-AC-007 | `cmderr=3` (exception) — the transfer itself traps | Access Register on a `regno`/CSR combination that causes an exception on the hart (e.g. a CSR the current privilege mode cannot access) | `cmderr=3`, hart remains halted in Debug Mode, no side effect beyond the reported error | 1 | P1 |
| TC-AC-008 | `cmderr=4` (halt/resume) — command issued on a running hart | Resume the hart (`OP8`/`TC-RC-003`), then issue an Access Register command before halting again | `cmderr=4` — Access Register requires the target hart to be halted first | 1 | P1 |
| TC-AC-009 | `cmderr` is sticky until acknowledged | After forcing any `cmderr≠0` above, issue a fresh valid Access Register command without first clearing `cmderr` | New command is rejected (or `cmderr` remains the stale value) until the debugger explicitly acknowledges/clears it per #3.7.1's documented `cmderr`-clear procedure | 1 | P1 |
| TC-AC-010 | `postexec` triggers Program Buffer execution after the register transfer | Access Register with `postexec=1`, `progbuf0-N` pre-loaded (forward reference to `PB` cluster below) | Register transfer completes, then the Program Buffer executes immediately afterward, in the same command | 1 (cross-references `TC-PB` cluster) | P1 |
| TC-AC-011 | `abstractauto.autoexecdata` triggers automatic command re-issue | Set `abstractauto.autoexecdata` bit for `data0`, then perform a plain DMI access to `data0` | The Access Register command automatically re-executes on that `data0` touch — the batch-register-dump acceleration path | 1 | P2 |
| TC-AC-012 | `aarpostincrement` auto-increments `regno` | Access Register with `aarpostincrement=1`, issue twice in a row without rewriting `regno` | Second transfer targets `regno+1` automatically — confirms the auto-increment sweep path used for bulk GPR dumps | 1 | P2 |
| TC-AC-013 | `abstractcs.datacount`/`progbufsize`/`impebreak` discovery | Read `abstractcs` | Reports the DUT's actual `data0-11` count and Program Buffer size — every later `PB`/`AC` row that assumes a minimum size must first confirm it here, not hardcode it | 3 (`datacount`, `progbufsize`, `impebreak`) | P0 (gate) |

### Abstract Command: Quick Access (Ch.3 op 8 sibling, #3.7.1.2, Optional) — prefix `QA`

Quick Access is a self-contained implicit halt→command→resume, intended for minimally-intrusive single-command debugging of a running hart — the mechanism `VERIFICATION_STRATEGY.md`'s OP18 composite scenario re-runs alongside `AC` (non-halting) and `SBA`.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-QA-001 | Quick Access on a running hart | With hart running, issue `command` (`cmdtype=1`) | Hart is implicitly halted, the pre-loaded Program Buffer executes, hart implicitly resumes — all without the debugger issuing separate `haltreq`/`resumereq` | 1 | P1 |
| TC-QA-002 | Quick Access disturbance bound | Time the running hart's execution gap during `TC-QA-001` | Disturbance is within the spec's documented "hundred or less cycles" bound — SVA/cycle-domain check, not meaningful in an untimed model (mirrors `TC-RC-006`'s treatment) | 0 (cycle-domain; SVA-only, see Uncertain) | P2 |
| TC-QA-003 | Quick Access is unavailable/rejected while `haltreq` is asserted | Assert `haltreq`, then issue Quick Access | `cmderr` reports the documented rejection rather than a corrupted double-halt sequence | 1 | P2 |
| TC-QA-004 | Quick Access `cmderr=2` when unsupported | On a DUT that doesn't implement Quick Access, issue `command` (`cmdtype=1`) | `cmderr=2` — same discovery-by-attempting discipline as CSR access in `TC-AC-005` | 1 | P1 |

### Abstract Command: Access Memory (Ch.3 op 10, #3.7.1.3, Optional) — prefix `AM`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-AM-001 | Physical memory read via Access Memory | `command` (`cmdtype=2`), `write=0`, address in `arg1`/`data1` | Correct memory content returned in `data0` | 1 | P1 |
| TC-AM-002 | Memory write + read-back | `write=1` with a known pattern, then `write=0` read-back at the same address | Written value observed on read-back | 1 | P1 |
| TC-AM-003 | `aamsize` WARL discovery | Attempt Access Memory at each defined `aamsize` encoding | Unsupported widths report `cmderr=2`; supported widths complete with `cmderr=0` — mirrors `TC-AC-003`'s discovery discipline for `aarsize` | 5 | P1 |
| TC-AM-004 | `aampostincrement` auto-increments the address | Two consecutive Access Memory reads with `aampostincrement=1`, same base address written once | Second transfer targets `address + aamsize` automatically — the bulk-memory-dump acceleration path | 1 | P2 |
| TC-AM-005 | `aamvirtual` address translation (MMU-present DUTs only) | Access Memory with `aamvirtual=1` at a mapped virtual address vs. `aamvirtual=0` at the equivalent physical address | Both resolve to the same underlying memory content; N/A on an MMU-less DUT | 2 (`virtual`, `physical`) | P2 — mark N/A if no MMU |
| TC-AM-006 | `cmderr=3` on a bad address | Access Memory at an unmapped or misaligned address | `cmderr=3`, hart remains halted, no side effect beyond the reported error | 1 | P1 |
| TC-AM-007 | `cmderr=2` on unsupported `aamvirtual`/size combination | Attempt a combination the DUT documents as unsupported | `cmderr=2` — discovery-by-attempting, same discipline as `TC-AC-005`/`TC-AM-003` | 1 | P2 |

### Program Buffer (Ch.3 op 8, #3.8, Optional) — prefix `PB`

`abstractcs.progbufsize`/`impebreak` discovery is `TC-AC-013`'s job, not repeated here — every row below assumes that gate already ran.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-PB-001 | `progbuf0-15` write/read-back | Write a distinct pattern to each implemented `progbufN` (per `TC-AC-013`'s `progbufsize`), read back | Values observed unchanged | `progbufsize` (typically ≤16) | P0 |
| TC-PB-002 | Register write-isolation across `progbuf0-15` | Write `progbuf0`, then read `progbuf1` | `progbuf1` unchanged — write-isolation, same discipline as `TC-AC-004` | 1 | P1 |
| TC-PB-003 | Execute a simple instruction sequence via `postexec` | Load a short instruction sequence ending in `ebreak`/`c.ebreak` into the Program Buffer, trigger via Access Register `postexec=1` (`TC-AC-010`) | Sequence executes on the halted hart; hart re-enters Debug Mode at the `ebreak` | 1 | P0 |
| TC-PB-004 | `progbufsize=1` ⇒ `impebreak=1` minimal configuration | On a DUT reporting `progbufsize=1`, confirm `abstractcs.impebreak=1` and execute a one-instruction sequence with no explicit `ebreak` | Hart returns to Debug Mode correctly even though the single buffer slot held no room for an explicit `ebreak` — the specific accommodation #3.8 documents this field pairing for | 1 | P1 — N/A if `progbufsize>1` |
| TC-PB-005 | Exception mid-Program-Buffer execution | Load a sequence whose middle instruction traps (e.g. an illegal instruction or a memory access to an unmapped address) | `cmderr=3`, execution stops at the faulting instruction, hart remains halted in Debug Mode with partial-execution state observable — not a hang, not a silent skip | 1 | P1 |
| TC-PB-006 | `dpc` save/restore discipline around Program Buffer execution | Read `dpc` before triggering Program Buffer execution, execute a sequence, read `dpc` again afterward | `dpc` is restored to its pre-execution value once back in Debug Mode (or is documented UNSPECIFIED during execution itself, per #4.9.2) — a directed check, not just "dpc is readable," per the Design Rationale Notes callout above | 1 | P1 |

### Direct System Bus Access (Ch.3 op 11, #3.10, Optional) — prefix `SBA`

Value proposition over Program Buffer: minimal-impact access to a system that may still be running, plus reaching devices a hart itself cannot address (Design Rationale Notes above) — `TC-SBA-008` is where that's actually proven, not assumed.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-SBA-001 | `sbcs` discovery (`sbversion`/`sbasize`/`sbaccess8-128`) | Read `sbcs` | Reports the DUT's actual SBA version, address width, and supported access widths — gate for every row below | 1 (gate) | P0 (gate) |
| TC-SBA-002 | Read via `sbaddress`+`sbreadonaddr` | Set `sbcs.sbreadonaddr=1`, write `sbaddress0` | Read auto-triggers; result appears in `sbdata0` without a separate read command | 1 | P0 |
| TC-SBA-003 | Write via `sbdata` | Write `sbaddress0`, then write `sbdata0` | Value observed at that system-bus address on next read | 1 | P0 |
| TC-SBA-004 | `sbautoincrement` auto-increments `sbaddress` | Two consecutive accesses with `sbautoincrement=1` | Second access targets `address + access_width` automatically | 1 | P2 |
| TC-SBA-005 | `sbreadondata` triggers streaming auto-read | Set `sbcs.sbreadondata=1`, read `sbdata0` twice in a row | Second read auto-triggers the next bus read (with autoincrement if also set) — the streaming-read acceleration path | 1 | P2 |
| TC-SBA-006 | `sberror` sticky error, cleared by write | Attempt an access to an unmapped/misaligned system-bus address | `sbcs.sberror` sets and stays set (sticky) until explicitly cleared; subsequent accesses are held per #3.10's documented recovery procedure | 1 | P1 |
| TC-SBA-007 | `sbbusy`/`sbbusyerror` — access while busy | Access `sbcs`/`sbdata` while a prior SBA transaction is still in flight (`sbbusy=1`) | `sbbusyerror` sets; the in-flight transaction itself is not corrupted | 1 | P1 |
| TC-SBA-008 | SBA works while the hart is running | With the target hart left running (not halted), issue an `SBA` read/write to a memory location the hart is not currently touching | Access completes correctly without requiring `haltreq` — the specific value proposition over Program Buffer that #3.10 documents; if this row is skipped, SBA's differentiator over `AC`/`PB` is never actually verified | 1 | P0 |
| TC-SBA-009 | Multi-word address/data (`sbaddress0-3`/`sbdata0-3`) | On a DUT with `sbasize`/access width wider than one DMI register, exercise the higher-order `sbaddress1-3`/`sbdata1-3` registers | Multi-word value assembled/disassembled correctly across the register set; N/A on a DUT whose `sbasize` fits in `sbaddress0` alone | 1 | P2 — N/A if `sbasize` ≤32 |

### Minimally intrusive debugging (composite) (#3.11) — cross-cutting, no dedicated register — prefix `MID`

Not a new mechanism — the spec explicitly groups non-halting `AC`/`AM` transfers, `QA`, and `SBA` (all already covered above) as jointly answering "how do I debug a hart I can barely afford to stop." This cluster's only job is to prove the *combination* holds, not to re-verify any one of them again.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-MID-001 | Back-to-back non-halting access with disturbance bound | Re-run `TC-AC-001` (non-halting variant, if the DUT supports register transfer without a full halt), `TC-QA-001`, and `TC-SBA-008` back-to-back on a hart running a known instruction stream | The hart's own instruction stream is undisturbed beyond each mechanism's documented bound (zero for non-halting `AC`/SBA, "hundred or less cycles" for Quick Access, per `TC-QA-002`) — checked via an independent monitor on the hart's execution, not just the debug-side transaction status | 1 | P1 |

### Hart grouping — halt group / resume group / external trigger (Ch.3 op 12/13/14, #3.6, Optional) — prefix `HG`

A multi-component system-level scenario, not a RISC-V-only one (Design Rationale Notes above) — several rows below need an External Trigger Agent standing in for a non-RISC-V core or off-chip signal, the same agent `VERIFICATION_STRATEGY.md`'s `OP12` flow uses.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-HG-001 | Halt-group support discovery | Read/write `dmcs2.hgselect`/`grouptype` | Reports whether halt groups are implemented at all — gate for the rest of this cluster | 1 (gate) | P0 (gate) |
| TC-HG-002 | Assign a hart to a halt group | `hgselect=0` (halt-group addressing), write `group`+`hgwrite=1` for a selected hart | Hart's halt-group membership readable back via `group` | 1 | P1 |
| TC-HG-003 | Halt-group propagation | With two harts in the same halt group (`TC-HG-002` ×2), halt only one via `haltreq` | The other hart in the same group also halts, without its own `haltreq` ever being written — the actual point of grouping | 1 | P0 |
| TC-HG-004 | Halt-group isolation (independence proof) | Repeat `TC-HG-003` with a third hart deliberately left in a different group | The third hart is unaffected — same write-isolation discipline as `TC-HS-008` | 1 | P1 |
| TC-HG-005 | Assign a hart to a resume group | `hgselect=1` (resume-group addressing), write `group`+`hgwrite=1` | Hart's resume-group membership readable back | 1 | P1 |
| TC-HG-006 | Resume-group propagation | With two harts in the same resume group, all halted, resume only one via `resumereq` | The other hart in the same resume group also resumes | 1 | P0 |
| TC-HG-007 | External trigger halt-group notify | External Trigger Agent asserts a trigger line assigned (via `dmexttrigger`) to halt group N | Every hart in group N halts in response — the multi-component-sync use case #3.6 documents | 1 | P1 |
| TC-HG-008 | External trigger resume-group notify | External Trigger Agent asserts a trigger line assigned to resume group N, harts pre-halted | Every hart in resume group N resumes in response | 1 | P1 |
| TC-HG-009 | Halt-group and resume-group membership are independent | Assign a hart to halt group 1 and resume group 2 (different numbers) | Both memberships hold independently — a hart's halt-group assignment does not imply the same resume-group assignment | 1 | P2 |

### Authentication / DM locking (#3.12, Optional) — prefix `AUTH`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-AUTH-001 | `authenticated=0` blocks DM operations | Before completing the DUT's authentication handshake, attempt `haltreq`/Access Register/any non-authentication DMI operation | Operation is blocked or has no observable effect — the IP-protection intent #3.12 exists for | 1 | P0 |
| TC-AUTH-002 | `authenticated=0` still permits `dmstatus`/`authdata` access | With `authenticated=0`, read `dmstatus` and read/write `authdata` | Both remain reachable — the two things that must stay accessible in order to authenticate at all | 1 | P0 (gate) |
| TC-AUTH-003 | Authentication handshake round trip | Drive the DUT's documented challenge/response sequence through `authdata` | `dmstatus.authenticated` transitions 0→1; DM operations blocked by `TC-AUTH-001` now succeed | 1 | P0 |
| TC-AUTH-004 | `authbusy` during in-progress computation | Read `authdata`/`authenticated` while the DUT's authentication algorithm is still computing a response | `authbusy=1`; debugger is expected to poll rather than treat a mid-computation read as a final answer | 1 | P1 |
| TC-AUTH-005 | Failed authentication attempt | Drive an incorrect challenge/response | `authenticated` remains 0; DM stays locked; no crash/hang/lockout side effect from the failed attempt itself | 1 | P1 |
| TC-AUTH-006 | Re-locking (if supported) | On a DUT that supports deasserting authentication after a successful handshake, do so, then retry a blocked operation | Operation is blocked again — confirms locking isn't a one-time gate that's forgotten after the first success | 1 | P2 — N/A if the DUT has no re-lock mechanism |

### Sdext — Debug Mode entry/exit & Core Debug Registers (Ch.4, #4.1–#4.9) — prefix `DCSR`

Both perspectives apply here (per `VERIFICATION_STRATEGY.md`'s Sdext native-debugging strategy section): most of this cluster is reached through the DM's Access Register command (external), but `TC-DCSR-010`/`011` are specifically about what happens *without* a debugger attached at all.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-DCSR-001 | `dcsr.cause` reports the correct Debug Mode entry reason | Enter Debug Mode via each distinct cause the DUT supports (`ebreak`, trigger match, `haltreq`, single-step, halt-on-reset, halt-group) | `dcsr.cause` reports the specific cause each time — a debugger reconstructing "why did I stop" depends entirely on this field being accurate per-cause, not just present | 6 (one per entry cause) | P0 |
| TC-DCSR-002 | `dpc` holds the correct PC at Debug Mode entry, per cause | Same entry causes as `TC-DCSR-001`, read `dpc` each time | `dpc` matches the expected PC for that specific entry mechanism (e.g. the `ebreak` instruction's own address for the `ebreak` cause) | 6 | P0 |
| TC-DCSR-003 | `dscratch0-1` are private Debug-Mode scratch registers | Write `dscratch0`/`dscratch1` while halted, resume, re-halt, read back | Values preserved across a resume/halt cycle without disturbing any GPR — the mechanism a debugger uses for temporary storage without corrupting hart state | 2 | P1 |
| TC-DCSR-004 | `ebreakm`/`s`/`u`/`vs`/`vu` gate `ebreak`'s Debug-Mode-entry behavior, per privilege mode | For each implemented privilege mode X, set `ebreakX=1`, execute `ebreak` in mode X | Hart enters Debug Mode (`dcsr.cause=ebreak`) only for modes with their bit set — re-verified per mode separately, not once generically, since implementations may gate this per-mode differently | 5 (one per mode) | P0 |
| TC-DCSR-005 | `prv`/`v` save/restore around Debug Mode entry/exit | Enter Debug Mode from each implemented privilege mode / virtualization state, read `dcsr.prv`/`v`, resume | Previous privilege and virtualization state is correctly saved on entry and restored on resume, for every implemented mode | 5 (one per mode) | P0 |
| TC-DCSR-006 | `stepie` gates interrupts during single-step | Set `stepie=0` vs `1`, single-step (`SSTEP` cluster below) with a pending enabled interrupt | With `stepie=0`, the interrupt is masked for the stepped instruction; with `1`, the interrupt may be taken instead — confirm whichever behavior the DUT implements is internally consistent, not undefined | 2 | P1 |
| TC-DCSR-007 | `stopcount`/`stoptime` freeze counters/timer while halted | Set `stopcount=1`/`stoptime=1`, halt for a known duration, resume, read the relevant counter/timer CSR | Counter/timer did not advance while halted; with the bits `0`, it did | 2 | P2 |
| TC-DCSR-008 | `mprven` gates `MPRV` effect during Debug Mode memory access | With `mprven=0` vs `1`, perform a Debug-Mode memory access while `mstatus.mprv=1` | `MPRV`'s effect on the access's effective privilege is applied only when `mprven=1` — DUT-assumption-dependent, per the Design Rationale Notes callout above | 2 | P2 |
| TC-DCSR-009 | `nmip` visible while halted | Force an NMI-pending condition, halt, read `dcsr.nmip` | Bit correctly reflects the pending NMI without it having actually been taken (hart is halted) | 1 | P2 |
| TC-DCSR-010 | Debug-Mode-CSR isolation boundary (`NATIVE-OP7`, negative test) | From ordinary (non-Debug-Mode) native code, attempt to read/write `dcsr`/`dpc`/`dscratch0-1` | Illegal instruction exception — these CSRs are genuinely unreachable outside Debug Mode, which is *why* native single-step must route through `icount` instead (`TC-SSTEP-005` below) rather than a DUT-specific implementation detail | 3 (`dcsr`, `dpc`, `dscratch0/1`) | P0 |
| TC-DCSR-011 | `ebreakX=0` — native breakpoint exception, per mode (`NATIVE-OP1`) | For each implemented mode X with `ebreakX=0`, execute `ebreak` in mode X from native (non-Debug-Mode) code | Ordinary `Breakpoint` exception (`mcause=3`) taken to the mode's own trap handler — Debug Mode is never entered; this is the native side of the same field `TC-DCSR-004` tests from the external side | 5 (one per mode) | P0 |

### Single Step (#4.5, `dcsr.step`, Appendix B.3.1) — prefix `SSTEP`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-SSTEP-001 | External single-step — exactly one instruction | Set `dcsr.step=1`, resume | Hart executes exactly one instruction, then re-halts with `dcsr.cause=step` | 1 | P0 |
| TC-SSTEP-002 | Single-step across a taken branch/jump | Step onto a taken branch/jump instruction | `dpc` on re-halt is the branch **target**, not the sequential next PC — confirms the step logic tracks actual control flow, not `pc+4`/`pc+2` | 1 | P0 |
| TC-SSTEP-003 | Single-step onto an instruction that itself traps | Step an instruction that raises an exception (e.g. illegal instruction, page fault) | Trap is taken correctly; `dcsr.cause=step` bookkeeping and the trap handler's own entry do not corrupt each other — this is the scenario the Appendix B.3.1 heuristic (`TC-SSTEP-004`) exists to make safe | 1 | P1 |
| TC-SSTEP-004 | PC-change-or-side-effect invariant (Appendix B.3.1) | Across a representative instruction mix (arithmetic, load/store, branch/jump, trap-causing), single-step each and classify | Every instruction either changes the PC or has side effects, but never both — the invariant the debugger-side double-step-on-trap-restart logic depends on; a directed test confirming it holds (or documents a DUT where it doesn't), per the Design Rationale Notes callout | 1 | P1 |
| TC-SSTEP-005 | Native single-step via `icount` (`NATIVE-OP3`) | From native code (no DM attached), configure an `icount` trigger with `count=1` in the current privilege mode, execute one instruction | Trigger fires after exactly one instruction, taken as a trap to the native handler — the documented native-debugger alternative to `dcsr.step`, which `TC-DCSR-010` proves is otherwise unreachable | 1 | P0 |
| TC-SSTEP-006 | `icount` count>1 sweep (native) | Configure `icount` with `count=2,4,16` | Trigger fires after exactly that many instructions each time, not one-off — boundary-value sweep on the count field rather than a single sampled value | 3 | P1 |

### Sdtrig — Trigger Module, external + native (Ch.5, #5.1–#5.7.18) — prefix `TRIG`

Both perspectives converge on the same registers (per `VERIFICATION_STRATEGY.md`'s Trigger Module strategy sections): `action=1`/`dmode=1` is the external hardware-breakpoint path (Debug Mode entry), `action=0`/`dmode=0` is the native path (ordinary trap to the ISA-level handler) — most rows below are written once and note which `action` value each variant needs, rather than duplicating the whole row per perspective. **Shared baseline unless a row states otherwise**: `tdata1.m/s/u/vs/vu = 1/0/0/0/0` (M-mode only), `tcontrol.mte = 1`.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Bins | Priority |
|---|---|---|---|---|---|
| TC-TRIG-001 | `tinfo` enumerates supported trigger types | Read `tinfo` for each `tselect` index | Reports exactly the trigger types this DUT implements (`mcontrol`/`mcontrol6`/`icount`/`itrigger`/`etrigger`/`tmexttrigger`) — gate for every row below that assumes a specific type exists | 6 (one bit per type) | P0 (gate) |
| TC-TRIG-002 | `tselect` trigger-count discovery | Write `tselect` across its full range, read back (WARL) | Only indices for implemented triggers stick — same discovery discipline as `TC-HS-001`'s `HARTSELLEN` | 1 | P0 |
| TC-TRIG-003 | Write-0-then-configure sequencing | Reconfigure an already-armed trigger: write `tdata1=0` first, then `tdata2`/`tdata3`, then `tdata1` last | No spurious match fires mid-reconfiguration — a procedural/ordering hazard, not a value-based corner case, called out on its own per the skill's sequencing-hazard discipline | 1 | P0 |
| TC-TRIG-004 | `tdata1`/`tdata2`/`tdata3` write-isolation | Write `tdata2` for trigger index N, then read `tdata1`/`tdata3` for the same index | Neither is disturbed — write-isolation for the `tselect`-indexed register triple, same discipline as `TC-AC-004`/`TC-PB-002` | 1 | P1 |
| TC-TRIG-005 | `mcontrol`/`mcontrol6` address match, external (`action=1`, `EXT-TRIG-OP3`) | Configure `execute=1`, `tdata2`=target address, `dmode=1`, `action=1`; execute that address natively | Hart enters Debug Mode, `dcsr.cause=trigger`, `tdata1.hit` set on the matching trigger | 1 | P0 |
| TC-TRIG-006 | `mcontrol`/`mcontrol6` address match, native (`action=0`, `NATIVE-OP2`) | Same configuration as `TC-TRIG-005` but `dmode=0`, `action=0` | Ordinary `Breakpoint` exception taken to the native trap handler; Debug Mode never entered | 1 | P0 |
| TC-TRIG-007 | Data watchpoint (`load=1`/`store=1`), both perspectives | Configure a data watchpoint at a target address, both `action=1` and `action=0` variants, trigger via a native load/store to that address | External variant halts into Debug Mode; native variant traps to the handler — same mechanism as `TC-TRIG-005`/`006`, different access type | 2 (`action=0`, `action=1`) | P0 |
| TC-TRIG-008 | `match` mode sweep with boundary values | For each documented `match` encoding (equal / NAPOT / greater-or-equal / less-than / masked-bits) implemented, sweep `tdata2` at target−1/target/target+1 | Each mode fires exactly on its own documented boundary — a separate TC-ID and boundary sweep per mode, not one test at the reset-default mode | 5 modes × 3 boundary values = 15 | P0 |
| TC-TRIG-009 | `timing` field — before vs. after the matching instruction | Configure `timing=0` (before) and `timing=1` (after) variants of the same address match | `dpc`/trap PC on entry differs by exactly one instruction between the two — confirms the DUT actually implements the distinction rather than always firing at one fixed point | 2 | P1 |
| TC-TRIG-010 | `select` field — address vs. data comparison | Configure `select=0` (address) and `select=1` (data value) on an `mcontrol`/`mcontrol6` trigger | Trigger fires on address match in one case, data-value match in the other — confirms `select` actually changes what's compared, not just documented intent | 2 | P1 |
| TC-TRIG-011 | Trigger chaining (`EXT-TRIG-OP9`, `chain` field) | Configure two adjacent trigger indices with `chain=1`, each matching a different address | Neither fires alone; both firing together (in sequence) is required before Debug Mode entry / the native trap occurs | 1 | P0 |
| TC-TRIG-012 | `icount` external (`action=1`), `count` boundary sweep | Configure `icount` with `dmode=1`, `action=1`, sweep `count=1,2,4,16` | Debug Mode entered after exactly `count` instructions each time — external counterpart to `TC-SSTEP-006`'s native sweep | 4 | P0 |
| TC-TRIG-013 | `itrigger` — walk the full enabled-interrupt code space | Configure `itrigger` with `tdata2` selecting each implemented interrupt code individually (not just one sampled value) | Fires exactly when the selected interrupt is taken, for every implemented interrupt code — enumerate-the-space discipline, not sample-one-value | implemented interrupt count | P1 |
| TC-TRIG-014 | `etrigger` — walk the full enabled-exception code space | Configure `etrigger` with `tdata2` selecting each implemented synchronous exception code individually | Fires exactly when the selected exception occurs, for every implemented exception code | implemented exception count | P1 |
| TC-TRIG-015 | `tmexttrigger` — external trigger source | Configure `tmexttrigger` with `select` choosing a specific TM external-trigger input line; External Trigger Agent asserts that line | Trigger fires only for the selected input line, not others | 1 per implemented input line | P2 |
| TC-TRIG-016 | Multi-trigger disambiguation via `hit`/`hit0`/`hit1` (`NATIVE-OP5`) | Configure two triggers to both plausibly match the same instruction (e.g. same address, different `select`), fire the event | `hit` bits identify which specific trigger(s) actually fired — `mcause` alone is ambiguous per #5.3; sweeping `tselect` and reading `hit` is the only way to disambiguate | 1 | P1 |
| TC-TRIG-017 | Trigger firing priority (#5.3, Table 13) | Configure two triggers of different types that could both fire on the same instruction | The documented priority order determines which is reported/acted on first | 1 | P2 |
| TC-TRIG-018 | `dmode=1` triggers unreachable from non-Debug-Mode writes | From native (non-Debug-Mode) code, attempt to write `tdata1` for a trigger already configured with `dmode=1` | Write has no effect on a `dmode=1` trigger's configuration — protects an external debugger's trigger setup from being clobbered by the program under test, per #5.2's own intent | 1 | P0 |
| TC-TRIG-019 | Context-scoped trigger (`EXT-TRIG-OP8`/`NATIVE-OP6`, `mcontext`/`scontext`/`hcontext`/`textra32-64`) | Configure a trigger with a context filter (ASID/VMID or process context via `textra32`/`textra64`), execute the matching address under two different context values | Trigger fires only when the current context matches the configured filter — both as an external hardware breakpoint and as an in-kernel native mechanism (mirrors `EXT-TRIG-OP8`/`NATIVE-OP6` exactly, differing only in who configures/consumes it) | 2 (external, native) | P1 |
| TC-TRIG-020 | `mcontrol6.uncertain`/`uncertainen` — imprecise-match flag | Trigger a memory access the DUT cannot perfectly observe (e.g. a decomposed vector/push/pop access, if V/Zcmp implemented) | `uncertain` sets appropriately rather than every trigger fire being silently treated as precise — the documented false-positive-risk field, per Design Rationale Notes | 1 | P2 — N/A without V/Zcmp |
| TC-TRIG-021 | `icount.pending` fires on all traps, not just re-executable ones | Configure `icount`, force a trap on the instruction it would have fired on | `pending`/fire behavior treats all traps uniformly per #5.7.13's documented simplification, rather than distinguishing "trap causes re-execution" from "trap doesn't" | 1 | P1 |
| TC-TRIG-022 | Reentrancy protection during a native trap handler (`NATIVE-OP4`, #5.4) | Determine which of the two spec-permitted schemes the DUT implements (`tcontrol.mte`/`mpte` context save/restore, or hardware interrupt-disable-in-M-mode) — this can't be a single universal TC-ID per the Design Rationale Notes callout — then: re-enter the trap handler recursively via a second trigger match while already inside the first handler | The DUT's chosen scheme prevents runaway reentrant trigger firing, per whichever mechanism it implements | 2 (one per scheme; only one applies per DUT) | P1 |
| TC-TRIG-023 | Cross-extension interaction — A-extension decomposition | On an A-extension DUT, configure a data watchpoint (`load`/`store`), execute `lr`/`sc`/an AMO at the watched address | `lr` matches as a load, `sc` matches as a store, the AMO matches as both — "as if it were a load/store" is a standing invitation to check every instruction class that qualifies, not just plain `lw`/`sw` | 3 (`lr`, `sc`, `amo`) | P1 — N/A without A-extension |

### Cross-cutting: Coverage Model — prefix `COV`

Not a register area — these rows verify the verification infrastructure itself (`src/pydebug/model/coverage.py`'s `DebugCoverageModel`, `sv/fcov/covergroups.sv`), the same substrate the **Bins** column above reports against.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Priority |
|---|---|---|---|---|
| TC-COV-001 | `assert_slice_complete()` passes per closed feature area | Run the full TC-ID suite for a feature area, call `assert_slice_complete()` | Passes, with any residual bins accounted for in that area's own Intentionally-Not-Tested/Uncertain buckets — no silent gap | P0 |
| TC-COV-002 | Bins column honesty — measured vs. stated scope | Cross-check this document's **Bins** entries against `coverage.py` for areas with a live model (currently `RC`/`RST`/`HOR`/`DMA`/`HS`) | Numbers match exactly (measured, per the note at the top of Test Cases); for every other area added in this pass, the Bins column is explicitly the *intended* combinatorial scope, not yet a measured count, since no model exists for those registers yet — this is a stated, honest gap, not a silent one | P0 |
| TC-COV-003 | SV covergroups cross-check the Python model | Run the same stimulus against live RTL with `sv/fcov/covergroups.sv` bound, compare reported bin percentages against the Python model's bins for the same operations | Numbers agree (demonstrated repeatedly for the full `run_control`/`reset_control`/`halt_on_reset`/`dm_activation`/`hart_selection` cluster on CVA6 — see `testplans/results/run_control_cluster_cva6_2026-07-25.md`); any divergence is a VIP bug (as `jtag_monitor.sv`'s TDO-sampling gap and `covergroups.sv`'s DMI read-response pipelining bug already were), not a DUT bug | P1 |

### Cross-cutting: SVA Assertions — prefix `SVA`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Priority |
|---|---|---|---|---|
| TC-SVA-001 | Protocol-tier SVA (`dmi_assertions.sv`, bound to `jtag_if`) | Drive illegal `dmi_op` sequences, violate sticky busy/error semantics | Assertions fire on the violation, cycle-accurately, independent of whatever the Python-side scoreboard concludes | P0 |
| TC-SVA-002 | Register-tier SVA (per-DUT `dm_csrs_assertions.sv`, bound to `dm_csrs` internals) | Drive WARZ/WARL/W1 field writes documented in each register's own TC-IDs above (e.g. `dmcontrol.haltreq` WARZ) | Assertion fires on any DUT that violates its own documented field access type — already proven live against CVA6 RTL (a real `haltreq` WARZ violation, see the same results file) | P0 |
| TC-SVA-003 | Cycle-domain timing properties | `TC-RC-006`'s <1s halt/resume bound, `TC-QA-002`'s "hundred or less cycles" Quick Access disturbance bound | These live exclusively at the SVA tier — the untimed Python model cannot express either; still open per the Uncertain bucket above | P2 |

### Cross-cutting: Negative / Error-Injection Tests — prefix `NEG`

Most negative-test coverage already lives inside each feature area's own TC-IDs (illegal `dmcontrol` mutex-bit writes: `TC-HOR-005`; DMI access during reset: `TC-RST-005`; abstract-command `cmderr` paths: `TC-AC-006`–`009`; unauthenticated access: `TC-AUTH-001`) — not repeated here. This cluster is only what doesn't already have a home in a specific register area.

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Priority |
|---|---|---|---|---|
| TC-NEG-001 | Malformed trigger type configuration | Write `tdata1.type` to an encoding the DUT doesn't implement (per `TC-TRIG-001`'s `tinfo` gate) | Write is rejected/WARL-clamped rather than silently accepted and later mismatching `tinfo` | P1 |
| TC-NEG-002 | Illegal JTAG IR / truncated DR shift | Shift an IR value outside the DUT's defined instruction set, or terminate a DR shift early | DTM does not lock up or corrupt the next legitimate scan — recoverable via TAP reset at worst | P1 |

### Cross-cutting: Regression Tiers — prefix `REG`

| TC-ID | Test Description | Stimulus / Scenario | Expected Result / Check | Priority |
|---|---|---|---|---|
| TC-REG-001 | Smoke tier — one representative test per feature area | Run the `smoke` tier | Every feature area above with at least one TC-ID contributes exactly one representative test; tier completes quickly and green before any deeper run | P0 |
| TC-REG-002 | Static tier — full suite, max coverage | Run the `static` tier | Every TC-ID in this document that has stimulus implemented executes; `assert_slice_complete()` gates closure per area | P0 |
| TC-REG-003 | Tier-membership integrity | Run the project's tier-integrity check (already implemented per this project's regression harness) | Every test function is tagged into exactly one tier — a test cannot silently fall out of both `smoke` and `static` by omission | P1 |

## Intentionally Not Tested

Structured like the main tables above but with a **Reason** column instead of
**Priority** — a permanent, documented scope boundary, not a TODO.

| Coverpoint | Reason |
|---|---|
| `dmstatus.all_any.*` where `all=0, any=1` (6 pairs: halted, havereset, nonexistent, resumeack, running, unavail) | Requires a selection split across harts — some in the state, some not. With `hasel` tied to 0 (no hart-array-mask register in scope for this slice), there is exactly one currently selected hart, so `all*` and `any*` are always equal. Reachable only once the Hart Selection slice's `HS` prefix grows to cover `hawindowsel`/`hawindow`. |
| `dmstatus.all_any.*` where `all=1, any=0` (same 6 pairs) | Architecturally impossible — `all_x` implies `any_x` for any non-empty selection (#3.14.1). This is an invariant (`invariants.py`'s `INV-ALL-IMPLIES-ANY`), not a coverage hole; a DUT that ever reports this combination has a bug, not a missing test. |
| `dmstatus.authbusy=1`, `dmstatus.authenticated=0`, `dmstatus.confstrptrvalid=1` | Belong to the Authentication (#3.12) and "Discover DM/implementation info" (Ch.3 op 1) feature rows respectively — later slices. Run-control stimulus never touches `authdata` or `confstrptr0-3`. |
| `dmstatus.impebreak=1` | A Program Buffer property (#3.14.1) — Program Buffer is a later slice; no run-control stimulus executes the program buffer. |
| `dmstatus.allunavail`/`anyunavail=1` and `all_any.unavail` | Both current SoC integrations (`CVA6-fork/corev_apu/tb/ariane_testharness.sv`, `ibex-demo-system/rtl/system/ibex_demo_system.sv`) hardwire the DM's `unavailable_i` input to constant 0 (confirmed against RTL, 2026-07-25) — `unavail` is structurally unreachable via any DMI stimulus on either DUT regardless of `stickyunavail`'s config value. `stickyunavail` itself is no longer in this bucket: CVA6 now reports `stickyunavail=1` (`dut_configs/cva6.json`, closed via riscv-dbg-vip#117/#128/#131) and that capability-bit coverage is real/hit; only the downstream unavailable-hart bins stay excluded, on this `unavailable_i` root cause, not stickyunavail. See `TC-DHS-004`. |
| `dmstatus.version` = `v0_11` (1) or `custom` (15) | `v0_11` predates the dmcontrol/dmstatus field layout this model encodes entirely — a 0.11 DM would not have these registers at these addresses. `custom` (15) is "not conforming to any available standard" by definition; no spec-derived stimulus can require a DUT to report it, and neither project DUT does. |
| `dmi_access.write:dmstatus` | Every `dmstatus` field is R (#3.14.1); a write has no spec-defined behaviour. Registered rather than silently dropped so that if stimulus ever *does* write it, the coverage model's excluded-hit mechanism flags that as a stimulus bug. |
| TC-RC-006 (halt/resume response latency) | #3.5's "less than one second" bound is a cycle-domain property with no meaning in an untimed Python transaction model. Belongs to the SVA tier exclusively — see Uncertain below for whether that SVA property has been written yet. |
| TC-RST-005 (DMI access restrictions during reset) | The spec's own text is UNSPECIFIED here ("the only supported DM operations are..."; behavior for others isn't defined) — the check is "does not hang/crash," not a specific value, by design. |
| `dmcontrol.ackunavail` full conditional-clear semantics (`TC-DHS-006`'s `ack_when_available`/`ack_when_still_unavailable` bins) | Needs `TC-DHS-004`'s hart-availability drive mechanism, which is structurally unreachable on both current SoC integrations (`unavailable_i` hardwired to 0, see the `allunavail`/`anyunavail=1` row above) — the write-only half is closed separately (`TC-DHS-006`'s discovery probe). |

## Uncertain

Conceptually valid coverpoints currently blocked by a tooling/environment gap
or an unresolved spec-version question — revisit later, not a permanent
exclusion.

| Coverpoint | Blocker |
|---|---|
| TC-RC-006's "under 1 second" bound | Needs a cycle-accurate SVA property (not yet written) measuring `haltreq`-to-`allhalted` and `resumereq`-to-`allrunning` latency directly on the DUT; the Python model cannot express it at all. |
| `dmcontrol.ackunavail` full conditional-clear semantics (`ack_when_available` vs `ack_when_still_unavailable`), and the `unavail`-state `dmstatus` bins it depends on | **Resolved as N/A, not just blocked** (2026-07-25): the write-only half (`ackunavail=1` write-coverage, DM stays alive) is closed via `TC-DHS-006`'s discovery probe. The full semantics above needs `TC-DHS-004`'s hart-availability drive mechanism first, which is confirmed structurally unreachable on both current SoC integrations (`unavailable_i` hardwired to 0) — moved to Intentionally Not Tested rather than left Uncertain, since the blocker is a permanent RTL-integration fact, not a tooling gap that revisits later. |

## Design Rationale Notes

The spec's own italic "why" call-outs carry design intent that plain register field tables lose. These should drive corner-case and negative-test design once TC-IDs are written for the corresponding row above — captured here so the reasoning isn't rediscovered later:

- **Reset Control**: "There is no general, reliable way for the debugger to know when reset has actually begun" (#3.2) — no timing-assertion tests should be written against reset-start latency.
- **Halt Groups / External Triggers** (#3.6): exist partly to synchronize halting across non-RISC-V cores in the same platform — a multi-component system-level scenario, not a RISC-V-only one.
- **Abstract Commands** (#3.7): the `cmderr=2` ("not supported") path is load-bearing — e.g. Access Register on GPRs is mandatory but on CSRs is not, and the debugger discovers this by *attempting* the command, not by querying capability up front. `aarsize`/`aamsize` encodings deliberately match `sbaccess` in `sbcs` — worth a cross-section consistency check once both rows have TC-IDs.
- **Program Buffer** (#3.8): the `progbufsize=1` ⇒ `impebreak=1` requirement exists specifically to accommodate implementations that stuff instructions directly into the pipeline rather than mapping the Program Buffer into address space — a directed test should exist for exactly this minimal-`progbufsize` configuration.
- **System Bus Access** (#3.10): its value over Program Buffer is minimal-impact access to a *running* system, plus performance and access to devices a hart can't reach — SBA tests should include at least one scenario with the hart left running, not just halted.
- **Halt-on-reset** (#3.14.2): `setresethaltreq`/`clrresethaltreq` are split into two write-only bits specifically so per-hart halt-on-reset config can change without disturbing other selected harts — a multi-hart corner case worth its own TC-ID.
- **Debug Mode / `mprven`** (#4.1): recommended tied to 1; if 0, the external debugger must simulate all MPRV effects itself — this is DUT-assumption-dependent and must be parameterized, not hardcoded.
- **LR/SC** (#4.2): halting between `lr` and `sc` can lose the reservation, so `sc` may never succeed — a documented, *expected* corner case, not a bug. Negative/error-injection testing should confirm this is tolerated, not flagged as a checker error.
- **`dpc`** (#4.9.2): may become UNSPECIFIED during Program Buffer execution, by design, to allow implementations with no separate PC register — save/restore discipline around Program Buffer execution needs its own TC-ID, not just a "dpc is readable" test.
- **Sdtrig actions 8–9** (#5.2): intended for custom event counters but may also drive external logic outputs — implementation-defined, flag as DUT-assumption-dependent rather than universally testable.
- **Native Triggers reentrancy** (#5.4): two competing solutions exist (disable triggers in M-mode with interrupts disabled, vs. `mte`/`mpte` context save/restore) with different limitations — the test plan must ask which one a DUT implements before writing reentrancy tests; this can't be a single universal TC-ID.
- **`mcontrol6.uncertain`/`uncertainen`** (#5.7.12): exists for triggers that can't perfectly observe every memory access (e.g. vector/push/pop instructions) — explicitly documented as a false-positive risk, so a dedicated test should confirm `uncertain` is set appropriately rather than assuming every trigger fire is precise.
- **`icount`/`pending`** (#5.7.13): deliberately fires on *all* traps, not just ones where the instruction won't be re-executed, because distinguishing the two cases was judged too complex — a test verifying this "all traps match, no exceptions" rule is directly spec-mandated.
- **`dmi` sticky busy/error status** (#6.1.5): sticky specifically to support debuggers that batch multiple scans (e.g. writing then executing a Program Buffer) without checking status after each one — a batched-scan-with-injected-failure scenario is a named use case in the spec text itself, not an edge case to invent.
- **Single-step PC-change heuristic** (Appendix B.3.1): "every RISC-V instruction either changes the PC or has side effects when repeated, but never both" — this invariant is what makes the debugger-side double-step-on-trap-restart logic safe, worth a test that confirms it holds (or documents a DUT where it doesn't).

## Next pass

Done: every CAT2 row in the Feature Traceability Table now has a TC-ID cluster (161 TC-IDs total, see the honesty note at the top of Test Cases) — this document itself is no longer the gap. The gap moved one layer down, to the model/stimulus/RTL-run columns behind each TC-ID, and that's where the next pass belongs:

1. **Extend `src/pydebug/model/registers.py`/`predictor.py`** for the next-highest-leverage cluster before writing its stimulus — per this project's own discipline, stimulus should self-check against a real prediction, not a hardcoded expected value. Candidates in spec order: `DTM`/`DMI` (cheapest, first thing any new DUT needs — no model exists at all yet, not even a register table), then the rest of `HS` (hart-array-mask), then `AC`/`QA`/`AM`/`PB` (abstract commands + program buffer, the next foundational cluster after run control).
2. **`TRIG`'s 23 TC-IDs are the richest and most valuable cluster to close next** once the foundational clusters above are stable — it's also the one area with an explicit dedicated `VERIFICATION_STRATEGY.md` operation catalog (`EXT-TRIG-OP1-9`, `NATIVE-OP1-7`) already reasoned through from both the external and native-debugging perspectives, so the design work for its stimulus is already done; only the model/predictor and the actual Python+SV sequences remain.
3. **Re-walk `VERIFICATION_STRATEGY.md`'s gap matrix** against this expanded table — it currently only reflects the pre-this-pass state (`OP1`/`OP11`/`OP14`/`OP20`/`EXT-TRIG-*`/`NATIVE-*` marked "open, new row"); every one of those rows now has a concrete TC-ID cluster here to point at.
4. Cross-cutting `COV`/`SVA`/`NEG`/`REG` TC-IDs are process checks on the verification infrastructure itself — they become meaningful incrementally, as each feature cluster above gets real model/stimulus/coverage/assertions behind it, not as a standalone pass.
