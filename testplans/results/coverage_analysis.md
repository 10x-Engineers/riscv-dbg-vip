# Functional coverage — analysis

What is measured, what is reachable, and what stands between the two.

Read alongside:
- [`src/pydebug/sv/fcov/covergroups.sv`](../../src/pydebug/sv/fcov/covergroups.sv) — **the coverage of record**; what the regression actually collects
- [`testplans/generated/coverage_model.yaml`](../generated/coverage_model.yaml) — the architectural model, kept as the spec-traceable reference
- [`generated_vs_implemented.md`](generated_vs_implemented.md) — how the two relate, and why they are not one number
- [`cva6_sim/regress/README.md`](../../cva6_sim/regress/README.md) — how to run and collect
- [`rtl_findings.md`](rtl_findings.md) — the defects blocking some of it

---

## The number to quote, and the one not to

**100% of the architectural model is not achievable on CVA6, and chasing it
would mean gaming the model rather than verifying the DUT.**

The model is deliberately architectural: it describes Debug v1.0, not this
implementation. That is what makes it reusable and what makes its holes
meaningful. But it therefore contains bins CVA6 cannot reach for reasons that
are not defects:

| Unreachable on this DUT | Why |
|---|---|
| Multi-hart aggregation (`some_not_all`, `hart_to_hart`) | Single-hart SoC |
| Authentication states | `authenticated=1` permanently; no authentication implemented |
| Quick Access, Access Memory (`cmdtype` 1 and 2 succeeding) | Not implemented — they correctly return `cmderr=2` |
| `wrs.sto` / `wrs.nto` step class | Zawrs absent; they decode as illegal instructions |
| `dcsr.cause=5` (resethaltreq) | `dmstatus.hasresethaltreq=0`; halt-on-reset is optional |
| `cmderr=5` (bus) | Requires abstract memory access |
| `mcontrol` (v0.13 trigger type) | This DUT reports v1.0 and implements `mcontrol6` |

Each is an `ignore_bins` in the executable model **naming the reason**, and a
`reachable: false` entry in the YAML naming the DUT feature that would make it
reachable. They are retained rather than deleted so a DUT that implements them
gets measured — deleting a bin because this DUT cannot hit it makes the model
untrue of the architecture.

**So the meaningful figure is closure against reachable bins**, with every
exclusion justified. A model reporting 100% because its hard bins were deleted
is worth less than one reporting 70% and saying which 30% and why.

---

## Where the coverage comes from

One file: **`src/pydebug/sv/fcov/covergroups.sv`** — 19 covergroups, 72
coverpoints, 14 crosses, included by `debug_pkg.sv`. It is the coverage of
record. Nothing else in the tree is compiled for coverage.

It samples two sources, and the split within it matters:

- **DM registers over DMI** (14 covergroups) — the JTAG transaction stream, via
  `uvm_subscriber #(jtag_txn_c)`.
- **The hart backdoor** (5 covergroups, merged in from what was
  `dm_spec_coverage.sv`) — `dcsr`, `dpc`, privilege and which instruction a step
  stepped over all live in the core and are reachable over DMI only through an
  abstract command, so they need their own source and a clocked sampling process.

The second group exists because of a concrete failure: the `wfi` single-step
deadlock (RTL-001) **could not have appeared as a coverage hole**. No bin
represented "a step over a stalling instruction", because nothing sampled which
instruction a step stepped over. It was found by a directed test someone thought
to write, which does not repeat. `cp_stepped_class.wfi` now represents it, and
`cp_step_transition.stuck_running` (`DEBUG => RUNNING [* 2]`) is an illegal bin
that makes a regression of it a coverage failure rather than a timeout.

---

## What moved, and what each test bought

Measured per run with `make soc_test_cov`. Covergroups collect **only** under a
`-coverage all` build; `make soc_test` reports zeros by construction.

| Coverpoint | Before | After | What closed it |
|---|---:|---:|---|
| `cp_cmderr` | 16.67% | **83.33%** | `cmderr` — every error class driven deliberately |
| `cp_stepped_class` | 12.50% | **62.50%** | `step_classes` — one instruction per class |
| `cp_consecutive` | — | **100%** | `step_classes` — 60-step walk |
| `cp_haltreq_guard` | — | **100%** | guarded correctly (see below) |
| `cp_prv` | 33.33% | partial | `priv_walk` reaches S; U not yet |

`cp_cmderr` is the clearest result: five of six encodings, driven one at a time,
with the DM confirmed usable after each. The sixth (`other`) means the DM could
not classify its own failure, and not reaching it is arguably correct.

---

## Measured: merged functional coverage

All 25 tests, one compile, one coverage model, merged with `imc`
(2026-09-15). **13 of 19 covergroups are at 100%**; 208 of 295
bins covered.

| Covergroup | Merged |
|---|---:|
| `cg_dmcontrol_write` | 100.00% |
| `cg_dmstatus_read` | 100.00% |
| `cg_hart_transition` | 100.00% |
| `cg_command_write` | 100.00% |
| `cg_abstractcs_read` | 100.00% |
| `cg_progbuf` | 100.00% |
| `cg_sbcs` | 100.00% |
| `cg_sb_access` | 100.00% |
| `cg_dmcs2_write` | 100.00% |
| `cg_hartinfo_read` | 100.00% |
| `cg_haltsum0_read` | 100.00% |
| `cg_data0_access` | 100.00% |
| `cg_trigger` | 100.00% |
| `cg_hart_mode` | 87.50% |
| `cg_abstract_cmd` | 83.33% |
| `cg_dmi_access` | 67.71% |
| `cg_step_external` | 52.58% |
| `cg_debug_entry` | 49.33% |
| `cg_sba` | 25.00% |

Movement from unblocking SBA and adding the busy-guard and DTM tests:
`cg_sbcs` 25% → 100%, `cg_sb_access` 33% → 100%, `cg_dmcontrol_write`
97.37% → 100%.

`cg_sba` at 25% is **not** a stimulus gap: the width bins other than the
hardwired one cannot be reached while #147 stands, and are excluded at report
time by `mk/dm_cov_exclude.py` rather than in the covergroup — see the note in
`cp_sbaccess` for why SystemVerilog forces that.

---

## What is still open, honestly

**Privilege bins (`cp_prv`, `cp_prv_at_step`, and the crosses over them).**
`priv_walk.S` cycles M → S → U. The halt phase catches S, and `dcsr.prv` reports
it correctly — so an earlier reading of this as an RTL defect was wrong. U is not
reached, and the step walk confines itself to a small PC span. The program still
spends more time in M than intended. Not solved; recorded rather than worked
around.

**The `{stepie, irq_pending}` cross.** Needs an interrupt genuinely pending
while stepping. The first attempt armed a CLINT timer in the same program as the
privilege walk and spent more instructions on setup than the S and U bodies
contained. It needs its own test.

**Everything under `cg_sba`.** Blocked behind RTL-002: the reference model
predicts the spec's reset constant for `sbaccess` and the RTL forces 3, so
fail-fast aborts the SBA scenarios before their verdict. Roughly 15 testplan rows
and a whole covergroup sit behind one RTL line.

**`cp_dmi_result.failed` and `.busy`.** Provoking a DMI busy response reliably
means overrunning `dtmcs.idle`, which the JTAG driver currently does not do
deliberately. A directed transport-error test would close both.

**`cp_cause.trigger`.** `trigger` enumerates and disables triggers but does not
yet arm one and let it fire.

---

## Two bugs the coverage model itself had

Worth recording, because both looked like DUT failures.

**`cp_haltreq_guard` reported legitimate behaviour as a conformance failure.** It
sampled on *every* hart mode transition, so an ordinary deliberate halt — where
`haltreq` is asserted precisely because the debugger meant to halt — tripped its
`illegal_bins`. It is meaningful only while a step is outstanding, and is now
guarded on `dcsr.step`.

**A coverage model that samples one source cannot check itself.** `cp_prv` reads
`dcsr.prv`; when it showed M only, that was indistinguishable from "the hart
never left M" and "`dcsr.prv` does not record the privilege". A separate
diagnostic sampling `priv_lvl_q` directly was needed to tell them apart — and it
showed the RTL was fine. A coverpoint and the thing that validates it must not
share a source.

---

## Code coverage

Block, expression, toggle and FSM coverage is collected by the same
`-coverage all` build — `make regress_cov` produces it, no separate run. 20
`.ucd` databases plus the `.ucm` design model, about 3.2 MB, under
`cva6_sim/sim_outputs/coverage/scope/`.

**Reporting works locally** — an earlier version of this document said it was
licence-blocked, and that was wrong in a way worth recording. `imc` *is* blocked,
but only the **23.03** build: it dies in its Java licence layer (LMF-01513,
FLEXnet `-8 Authentication Failed`) before opening anything, while `xrun`
authenticates against the very same `license.dat`. That is a per-product licence
gap, not a broken licence, and the conclusion "no coverage reporting on this
machine" did not follow from it.

The **21.09** vManager install on the same machine authenticates and reads the
23.03 databases correctly — it prints a version-difference note and proceeds,
which is what UCIS versioning is for. `mk/dm_cov.sh` now defaults to it:

```bash
bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/
```

Two things that silently corrupt the merged number:

- **Never merge across coverage models.** Each compile writes its own `.ucm`, and
  `merge` keeps only what the models share. Merging 21 runs from one compile with
  1 run from another reported `cg_step_external` at **0.00%** when the same runs
  merged on their own model give **51.98%**. Check `scope/*.ucm` is a single file
  before trusting a merge.
- **Coverage data goes stale against the covergroups.** The databases currently
  on disk predate the covergroup consolidation and still contain `cg_dtm_dmi`,
  which no longer exists. Re-run the suite from one compile before quoting a
  number.

That scopes the report to the five instances that **are** the Debug Module —
`i_dm_top`, `i_dm_csrs`, `i_dm_sba`, `i_dm_mem` and `i_dmi_jtag`. Each must be
named: `report -inst X` covers only X and does not recurse, and the legacy
`report` command has no `-recursive` option. Naming only `i_dm_top`, as this
script originally did, measured the wrapper's port toggles and not one line of
the logic.

**Whole-SoC code coverage would be dominated by CVA6 itself and would say
nothing about the DM**, which is the DUT here.

Merged across all 26 tests, 2026-09-16, one compile. The Debug Module is 19
instances: `i_dm_top` and `i_dmi_jtag` and everything under them.

| Instance | Block | Expression | Toggle | FSM states | FSM trans. |
|---|---:|---:|---:|---:|---:|
| `i_dm_top` | — | — | 99.00% (1188/1200) | — | — |
| `i_dm_csrs` (+ `gen_haltsum0_single`) | 96.88% (155/160) | 75.00% (6/8) | 78.39% (1999/2550) | — | — |
| `i_dm_sba` | 86.36% (38/44) | 88.89% (8/9) | 98.94% (558/564) | 5/5 | 6/6 |
| `i_dm_mem` | 100% (94/94) | 100% (20/20) | 74.28% (1421/1913) | 4/4 | 5/5 |
| `i_debug_rom` | 100% (6/6) | — | 9.84% (133/1351) | — | — |
| `i_dmi_jtag` | 92.73% (51/55) | 94.12% (16/17) | 97.33% (365/375) | 5/5 | 6/6 |
| `i_dmi_jtag_tap` (+ clock cells) | 100% (78/78) | — | 97.75% (174/178) | 16/16 | 26/26 |
| `i_dmi_cdc` (+ 2 × `cdc_2phase`, src/dst) | 100% (42/42) | 88.89% (16/18) | 95.65% (835/873) | — | — |
| **Total** | **96.87%** (464/479) | **91.67%** (66/72) | **74.11%** (6673/9004) | **30/30** | **43/43** |

With the generated exclusions applied (`out/dm_code_excl.rpt`), every row is
100%: 15 blocks, 8 expression rows (2 of them constants imc excludes itself)
and 2331 toggle bits excluded; FSM needs no exclusions.

Before this pass the quoted figure covered five instances only, left out FSM,
and missed the CDC and every multi-dimensional array entirely. Its "100%" was
not comparable to this one.

---

## How the code coverage closed

Every uncovered item was classified against the RTL before anything was
written: reachable ones got stimulus, the rest got an exclusion rule that
states why the code cannot run here and what would make it run. Nothing is
excluded for being hard, and a rule that stops matching is reported so it can be
deleted.

### Reached by stimulus

| Gap | Why it was missed | Now |
|---|---|---|
| Busy guard with `cmderr`=0 on data/progbuf reads, progbuf writes, `abstractauto`, `abstractcs` | `cmd_busy` raced several accesses against one command; the first set `cmderr`, so the rest took the other branch | `TC-AC-020/021`: one command per access |
| `regno` corner arms on the read path | `TC-AC-026` only wrote | reads added |
| `command` read, unmapped write | never done | `TC-AC-028` |
| DTM busy capture, sticky error, `test_logic_reset` | every DMI access scans IR first, which always gives the DTM time; the "TAP reset" op was a BYPASS IR scan | raw DR-scan op, real TMS reset; `TC-DTM-014/015` |
| `sbbusy` true during a DMI access | a JTAG scan (~90 clocks) outlasts any bus transfer | `ndmreset` stalls the transfer; `TC-DMC-003` |
| `dm_mem` default write, idle `whereto`, `whereto` with `resumereq`, another hart's flags | only the hart touches DM memory | SBA into DM memory; `TC-DMC-001/002` |
| `haltsum1-3` read arms | believed multi-hart only; the decode answers them anyway | `TC-DMC-008` (and found RTL-007) |
| Upper halves of every 64-bit bus, WARL/reserved register bits, `relaxedpriv` | every access used 32-bit values and in-range writes | `TC-DMC-005/006` (and found RTL-006) |
| TAP: IDCODE and BYPASS never selected; Pause/Exit2 and five other TAP arcs never taken | every scan went RTI → IR → DR → RTI | raw JTAG scan and TMS walk; `TC-DTM-002/017/019` |
| `dmihardreset` | the old check passed on a DTM that ignores it | `TC-DTM-012` (and found RTL-009) |
| Per-hart state slot 1 in `dm_mem` | believed single-hart only; the slot is indexed by the hart id written | SBA writes of id 1; `TC-DMC-009` |
| `abstract_cmd` operand bits | no command used those regno bits | regno/size walk; `TC-DMC-010` |

The earlier toggle waiver for "the upper half of every SBA bus has no reachable
value" was wrong: `sbaddress1` and `sbdata1` exist for exactly that, and it was
deleted once they were driven.

### Excluded, by basis

| Basis | Rules | Blocks | Expr rows | Toggle bits |
|---|---|---:|---:|---:|
| Constant by construction — ROM array, fixed register fields, WARL masks, `dmcs2`, padded single-hart slots, flag-word padding | `debug-rom-*`, `*-constants`, `abstractauto-warl`, `dmcs2-not-implemented`, `single-hart`, `flag-word-constants`, `shutdown-counter-range` | — | — | 1461 |
| Constant by enumeration of every program `dm_mem` generates | `abstract-command-constant-bits` (`mk/dm_abstract_cmd_bits.py`) | — | — | 420 |
| Parameters (`DataCount`, `ReadByteEnable`) | `datacount-param`, `readbyteenable-param` | 2 | — | — |
| Testharness tie-offs (`test_en`, `unavailable_i`) | `tied-off-inputs`, `hart-never-unavailable` | 1 | — | 15 |
| Dead code behind RTL-002 / RTL-005 | `sba-*`, `sbaccess-hardwired`, `keepalive-dead-code` | 8 | 1 | 24 |
| X for the whole run, RTL-007 | `haltsum-undriven` | — | — | 320 |
| DTM encodings no transition produces; forced-constant DMI response | `dtm-parasitic-state`, `dtm-unencoded-error`, `dmi-response-constants` | 2 | 1 | 32 |
| **Argued from the RTL, not proven** — response FIFO never fills, CDC always ready | `dmi-resp-fifo-never-full`, `dmi-request-always-ready`, `dtm-request-backpressure` | 2 | 4 | 9 |
| **Waiver — testbench limit**: one power-on reset and one TRST per run | `waiver-*` | — | — | 20 |

The `abstract_cmd` rule first excluded every untoggled bit "left constant
after the walk". Enumerating the generator showed three of those 423 bits were
reachable (a CSR write to a CSR that does not exist still builds its program);
the walk now attempts those writes and covers them, and the rule excludes only
bits the enumeration proves constant.

### What the measurement itself was missing

- **Sub-instances.** The text report named five instances; the TAP (68/78
  blocks at the time), the CDC and the ROM were outside every quoted number.
- **Type-parameterised modules.** Xcelium does not score block, expression,
  toggle or FSM coverage in them by default, so `cdc_2phase` had no data at
  all. `mk/xcelium_cov.ccf` sets `set_parameterized_module_coverage`.
- **Multi-dimensional arrays** (`*W,COVMDD`): progbuf, the abstract-command
  program and the haltsum trees were never toggle-scored. The CCF enables
  `-sv_mda`; arrays of structs (`-sv_mda_of_struct`) crash `xmelab` and stay
  unscored.
- **FSM.** Recorded all along, but IMC's `-metrics code` omits it.
- **IMC silently dropped every struct-field exclusion** (`*W,NOMATCH`);
  `dm_cov.sh` now surfaces that warning.

### What closing it found

Four RTL defects no functional check had caught — RTL-006, RTL-007, RTL-008,
RTL-009 — and testbench defects that had been hiding things:

- DMI read data crossed the DPI bridge as a 2-state `int`, so X read as 0; a
  check on `haltsum1-3` passed while they were X.
- The TAP-reset op never reset the TAP; TC-DTM-014 passed without reaching the
  code it was written for.
- TC-DTM-012 and DTM-002 passed without testing anything: one wrote
  `dmihardreset` with no error pending, the other was never run.
- TC-RC-006 timed the simulator's wall clock against the spec's one-second
  bound; a slower coverage build failed it with the design unchanged. It now
  measures simulated time.

---

## What would move the number most

In order of coverage gained per unit of work:

1. **Resolve RTL-002.** One RTL line unblocks a whole covergroup, ~15 testplan
   rows and the `sba` scenario.
2. **A transport-error test.** `busy` is now provoked on purpose
   (`TC-DTM-015`). `failed` is not reachable on this DUT: the DM always
   answers `DTM_SUCCESS`. The `x_op_x_result` cross is still open.
3. **Arm a trigger and let it fire.** Closes `cp_cause.trigger` and starts the
   trigger crosses, which are 5 of the model's coverpoints.
4. **Get U-mode execution working** in `priv_walk`, then the privilege crosses
   follow.
5. **A dedicated interrupt test** for the `stepie` cross.

Items 2 and 3 are each a single sequence against existing infrastructure. Item 1
is not ours to fix.
