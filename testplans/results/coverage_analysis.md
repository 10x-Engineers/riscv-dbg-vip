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

All 22 tests, one compile, one coverage model, merged with `imc`. Produced by
`bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/` on 2026-09-15.

| Covergroup | Merged |
|---|---:|
| `cg_dmstatus_read` | 100.00% |
| `cg_hart_transition` | 100.00% |
| `cg_command_write` | 100.00% |
| `cg_abstractcs_read` | 100.00% |
| `cg_progbuf` | 100.00% |
| `cg_dmcs2_write` | 100.00% |
| `cg_hartinfo_read` | 100.00% |
| `cg_haltsum0_read` | 100.00% |
| `cg_data0_access` | 100.00% |
| `cg_trigger` | 100.00% |
| `cg_dmcontrol_write` | 97.37% |
| `cg_hart_mode` | 87.50% |
| `cg_abstract_cmd` | 83.33% |
| `cg_dmi_access` | 65.62% |
| `cg_step_external` | 52.58% |
| `cg_debug_entry` | 41.00% |
| `cg_sb_access` | 33.33% |
| `cg_sbcs` | 25.00% |
| `cg_sba` | 25.00% |

This is a **real merge**, not the per-run maxima the regression driver prints —
those are a lower bound and labelled as such wherever they appear.

Two cautions on reading it. The ten at 100% are the register-centric
covergroups, and a field that toggled is easier to hit than a behaviour that was
exercised — see [`generated_vs_implemented.md`](generated_vs_implemented.md).
And `report -detail` without `-all` emits the *Uncovered* report, where a
covergroup at 100% is absent rather than missing; the table above used `-all`.

The three lowest — `cg_sba`, `cg_sbcs`, `cg_sb_access` — are all one RTL line
(RTL-002), not three separate gaps.

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

Merged across all 22 tests, 2026-09-15:

| Instance | Block | Expression | Toggle |
|---|---:|---:|---:|
| `i_dm_top` | — | — | 33.33% |
| `i_dm_csrs` | 67.30% (107/159) | 75.00% (6/8) | 23.92% (342/1430) |
| `i_dm_sba` | 61.36% (27/44) | 77.78% (7/9) | 6.38% (36/564) |
| `i_dm_mem` | 89.36% (84/94) | 90.00% (18/20) | 71.88% (501/697) |
| `i_dmi_jtag` | 80.00% (44/55) | 58.82% (10/17) | 94.67% (355/375) |
| **Total** | **74.43%** (262/352) | **75.93%** (41/54) | **38.79%** (1506/3882) |

`i_dm_top` has no block or expression section because it is a wrapper with no
logic of its own — that is an absent metric, not a hole.

The lowest row is `i_dm_sba`, and it is the same RTL-002 blockage that holds
`cg_sba` down: the SBA paths are reachable but the scenarios abort before
exercising them. Functional and code coverage agree on where the gap is, which
is a useful cross-check that neither number is an artefact.

---

## What would move the number most

In order of coverage gained per unit of work:

1. **Resolve RTL-002.** One RTL line unblocks a whole covergroup, ~15 testplan
   rows and the `sba` scenario.
2. **A transport-error test.** Deliberately under-idle the DMI to provoke `busy`,
   and force a sticky error to provoke `failed`. Closes `cp_dmi_result` and the
   `x_op_x_result` cross.
3. **Arm a trigger and let it fire.** Closes `cp_cause.trigger` and starts the
   trigger crosses, which are 5 of the model's coverpoints.
4. **Get U-mode execution working** in `priv_walk`, then the privilege crosses
   follow.
5. **A dedicated interrupt test** for the `stepie` cross.

Items 2 and 3 are each a single sequence against existing infrastructure. Item 1
is not ours to fix.
