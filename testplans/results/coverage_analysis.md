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

All 36 tests, one compile, one coverage model, merged with `imc`
(2026-09-18, `bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/`).

**263 of 263 reachable bins covered — 100%.** 19 bins are excluded at report
time by `mk/fcov_exclusions.tcl`, each because this DUT cannot produce it.
Without the exclusions: 263 of 282 (93.26%). Both reports are written on every
run (`out/functional.rpt`, `out/functional_excl.rpt`).

| Covergroup | Raw | With exclusions | Excluded |
|---|---:|---:|---|
| `cg_dmi_access` | 22/26 | 22/22 | op status `failed` ×4 |
| `cg_debug_entry` | 23/28 | 23/23 | cause=trigger ×5 (RTL-012) |
| `cg_abstract_cmd` | 5/6 | 5/5 | `cmderr` other |
| `cg_sba` | 3/12 | 3/3 | widths ×4, `sberror` ×5 (RTL-002) |
| every other covergroup (15 of 19) | 100% | 100% | — |

### Why each exclusion is unreachable

| Bins | Reason |
|---|---|
| `cg_dmi_access` `failed` | `dmi_jtag.sv` only ever assigns `DMIBusy` or `DMINoError` (lines 169, 173) |
| `cg_abstract_cmd` `other` | `CmdErrorOther` is declared in `dm_pkg.sv` and assigned nowhere |
| `cg_sba` widths, `sberror` | RTL-002: `dm_csrs.sv:618` forces `sbaccess`=3 every cycle; `dm_sba.sv` raises `sberror` only for `sbaccess`>3 and has no bus-error input |
| `cg_debug_entry` trigger | RTL-012 (#161): triggers fire on this build, but CVA6 reports every `action=1` trigger as `dcsr.cause`=3, so cause=2 is never sampled |

Bins that cannot be sampled at all, as opposed to bins the DUT cannot produce,
are `ignore_bins` in `covergroups.sv` with the reason beside them:
`cg_hart_mode.stayed_running` (the group samples only on a mode change), the
off-diagonal `x_cause_x_dpc` cells (the origin is derived from the cause), and
`wfi`/`priv_change` × U in `x_class_x_prv` (illegal at U on a hart with S).

### How the remaining holes were closed

- **`debug_entry` rewritten** — ebreak entry at M, S and U, halt requests that
  interrupt S and U code, steps from S and U, and the `ebreakm=0` negative case
  now requires the breakpoint trap. It had been failing 5/7 because a 32-bit
  abstract write of `dpc` sign-extends to `0xFFFFFFFF8000xxxx`; addresses are
  now written 64-bit (`read_reg64`/`write_reg64`).
- **`step_matrix` (new)** — every class in `step_loop` under all four
  `{stepie, interrupt pending}` combinations in M, runs long enough for the
  17–64 consecutive-step bin, then from S and U, a `wfi` at U, and an `sret` at
  S. The pending interrupt is the CLINT timer (`mtimecmp` resets to 0) gated by
  `mie.MTIE`, with `mstatus.MIE=0` so it is never taken in M.
- **`dmi_error`** — the sticky-busy case now also scans a read and a write.
- **Three testbench defects, each of which hid a class:**
  - *Trapping steps were never seen.* CVA6 never acks an instruction that
    traps, so the TB's `commit_valid` missed every trap; it now includes
    `ex_commit.valid`.
  - *The wrong instruction was recorded.* The class latched was the **last**
    to complete in a step; under RTL-010 that is the handler's first
    instruction, not the trap. It now latches the first, together with the
    privilege it ran at (`dcsr.prv` reads M after any trap).
  - *No branch was ever not-taken.* The TB compared `op` with `BRANCH`, but
    CVA6 encodes conditional branches by comparison (`EQ`, `NE`, …), so every
    branch classified as taken. Taken is now decided at commit from the
    resolved target the scoreboard stores in `bp.predict_address`.

### Two CVA6 defects found on the way

`step_matrix` checks where every trap and xRET step lands, and finds both
wrong — see `rtl_findings.md`:

- **RTL-010** (upstream openhwgroup/cva6#3429) — a stepped instruction that
  traps halts after the handler's first instruction.
- **RTL-011** (#159) — a stepped `mret`/`sret` reports `dpc`=pc+4 and the
  pre-return privilege.

`step_matrix` is therefore an expected fail (12/13), and it repairs `dpc`/`prv`
after each xRET so the rest of the run still steps where intended.

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

## Code coverage — the debug subsystem

Scope, decided deliberately: **everything a debug transaction passes through**,
not the whole SoC and not the DM alone.

| Part | Instances |
|---|---|
| JTAG TAP, DTM, DMI clock-domain crossing | `i_dmi_jtag` and below (7) |
| Debug Module | `i_dm_top` and below (6) |
| DM ↔ system bus | `i_dm_axi2mem` (hart's path to the debug ROM, program buffer and data), `i_dm_axi_master` (SBA) |
| `ndmreset` | `i_rstgen_main`, `i_rstgen_bypass` |
| DM ↔ processor / harness glue | `tb_top_soc.dut`, `i_ariane` — boundary only: `debug_req_i`, the DM's bus and DMI/JTAG signals, `ndmreset` and the `debug_req` gating |

CVA6's internal debug logic is deliberately **not** counted here: it has no
instance of its own, and measuring it would mean closing the core's CSR file
and decoder. The boundary instances are scoped by name in
`mk/dm_cov_exclude.py` (`BOUNDARY`), and those exclusions are labelled
`boundary-scope:` so scope is never mistaken for unreachability.

Merged across the suite (2026-09-18):

| Metric | Raw | Excluded | Result |
|---|---:|---:|---:|
| Block | 84.38% (578/685) | 119 | **100%** (566/566) |
| Expression | 82.22% (74/90) | 19 | **100%** (74/74) |
| Toggle | 27.45% (11981/43650) | 35133 | **100%** (8517/8517) |
| FSM states | 86.67% (39/45) | 6 | **100%** (39/39) |
| FSM transitions | 80.00% (56/70) | 14 | **100%** (56/56) |

Most of the toggle exclusions are the two boundary instances being scoped out
(≈31k bits of the rest of the SoC). The rest are constants: the debug ROM,
the abstract-command program bits proven constant by enumeration, tied AXI
attributes, and undriven multi-hart vectors.

### Collecting and reporting it

Block, expression, toggle and FSM coverage come from the same `-coverage all`
build — `make regress_cov`, no separate run — as `.ucd` databases plus one
`.ucm` design model under `cva6_sim/sim_outputs/coverage/scope/`.
`bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/` merges and reports them.

**Reporting works locally**, with one catch worth keeping: `imc` *is* licence-
blocked, but only the **23.03** build, which dies in its Java licence layer
(LMF-01513, FLEXnet `-8`) before opening anything, while `xrun` authenticates
against the very same `license.dat`. The **21.09** vManager install reads the
23.03 databases correctly — a per-product licence gap, not a broken licence —
and `mk/dm_cov.sh` defaults to it.

Two things silently corrupt a merged number:

- **Never merge across coverage models.** Each compile writes its own `.ucm`,
  and `merge` keeps only what the models share. Merging runs from two compiles
  once reported `cg_step_external` at 0.00% when the same runs on their own
  model gave 51.98%. Check `scope/*.ucm` is a single file before trusting a
  merge — and after any change to the testbench or the covergroups, re-run the
  whole suite rather than merging old databases with new.
- **`mk/xcelium_cov.ccf` is load-bearing.** Without it Xcelium skips
  type-parameterised modules (the entire DMI clock-domain crossing) and
  multi-dimensional arrays (the program buffer, the abstract-command program,
  the haltsum trees). IMC's `-metrics code` also omits FSM, so `dm_cov.sh` asks
  for `code:fsm`.

### What the bus bridges cost

`axi2mem` and CVA6's `axi_adapter` are generic IP. The DM uses them in one
narrow way — single-beat 64-bit accesses, `type_i = SINGLE_REQ`,
`amo_i = AMO_NONE`, id `'0`, one outstanding access, a 4 KiB region at address
0 — so their burst, wrapping-address and atomic logic is unreachable here: 86
blocks, 11 expression rows, 5 FSM states and 14 transitions, each excluded with
that wiring cited. Two waivers are testbench limits rather than impossibilities:
the crossbar has never backpressured the DM master's AW/W, and `+debug_disable`
is never passed.

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
| **Waiver — testbench limit**: one power-on reset and one TRST per run, `+debug_disable` never passed, crossbar never backpressures the DM master | `waiver-*`, `testbench-debug-always-enabled`, `dm-master-bus-never-backpressures` | — | — | 25 |
| The DM's bus bridges used one narrow way — single-beat 64-bit accesses, no bursts, no atomics, one outstanding access, tied AXI attributes, a 4 KiB region at 0 | `dm-slave-*`, `dm-master-*`, `dm-bridge-*`, `dm-region-address-bits`, `rstgen-parameter-check` | 87 | 10 | 1385 signals |
| **Scope, not unreachability** — the rest of the testharness and the `ariane` wrapper, excluded by name so the subsystem total neither counts nor claims them | `boundary-scope` | 17 | — | 807 signals (≈31.8k bits) |

The bridge rules also exclude 6 FSM states and 14 transitions (the burst,
atomic and wait-for-ready states of `axi2mem` and `axi_adapter`).

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

## What is left

Against `covergroups.sv` the reachable closure is complete (263/263). The 19
excluded bins move only with the DUT:

1. **Resolve RTL-002.** Restores `sbaccess` and makes the SBA width and
   `sberror` bins reachable — 9 of the 19.
2. **A CVA6 build with `SDTRIG=1`.** Makes `cause=trigger` reachable — 5 more.
   `TC-DCSR-011` already arms the trigger and reports N/A on this build.
3. **`DMIOPFailed` and `CmdErrorOther`** have no driver in this RTL; they stay
   excluded unless the DM grows one.

The architectural model (`coverage_model.yaml`) is a separate, larger target and
is not what these numbers measure.
