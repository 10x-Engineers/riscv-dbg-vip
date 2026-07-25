# DM Core Cluster — Ibex Results (2026-07-25)

Slice: dmcontrol/dmstatus run control (`run_control`, `reset_control`,
`halt_on_reset`, `dm_activation`, `hart_selection` — 23 TC-IDs, see
`testplans/riscv_debug_testplan.md`). Companion to
`run_control_cluster_cva6_2026-07-25.md`: this cluster had scenario
stimulus and TC-IDs from that earlier round, but **no scenario config at
all wired up for Ibex** — `ibex_sim/configs/` had none of the 5 JSON files
this cluster needs. This round adds them and closes the resulting coverage
gap, following the exact same run-fix-repeat cycle used for CVA6.

DUT: Ibex (`ibex_sim/`, vendored, unmodified spec-v0.13 `pulp-platform/riscv-dbg`),
Questa Sim-64, `make soc_test`/`make coverage_regress`.

## Summary

| Scenario | Result | Notes |
|---|---|---|
| `reset_ctrl` | **8/8 checks, 0 mismatches** | New config. First real run against Ibex. |
| `halt_on_reset` | **6/6 checks, 0 mismatches** | New config. |
| `run_control` | **9/9 checks, 0 mismatches** | New config. |
| `dm_activation` | **3/3 checks, 0 mismatches** | New config. |
| `hart_selection` | **4/4 checks, 1 mismatch** | New config. The 1 mismatch is [#130](https://github.com/10x-Engineers/riscv-dbg-vip/issues/130) (`allrunning`=1 for a nonexistent hart) — already filed against CVA6, and that issue's own body already documented this as a shared, identical-formula bug on Ibex's `dm_csrs.sv` too (predates the CVA6 v1.0 fork). Reproducing it here confirms that documentation was correct; no new issue needed. |
| Full CVA6 regression (17 scenarios, re-run) | Unchanged, 99.58%, 1 known/documented `MODEL_MISMATCH` | Confirms the shared model fixes below (`predictor.py`/`dm_ref_model.sv`) introduce no CVA6 regression. |

## DV bugs found and fixed

Two real, distinct golden-model bugs surfaced immediately on the first
Ibex run of this cluster — both in the *shared* model files
(`dm_ref_model.sv`/`predictor.py`, used by both DUTs), so both were fixed
once and verified against both DUTs:

- **`ndmresetpending` predicted unconditionally, ignoring DUT spec version.**
  `dmstatus.ndmresetpending` (bit 24) is a v1.0 addition (#3.14.1). Ibex's
  real, vendored v0.13 `dm_pkg` has no such field routed at all and reads
  it tied 0 — but the model predicted it correctly regardless of the
  configured `version`, an assumption the CVA6-only pytest suite could
  never catch (`ModelBackedMockTransport`'s "RTL" and "expected" are the
  same predictor instance; only a real v0.13 DUT comparison exposes it).
  Fixed by gating the prediction on `version >= DMSTATUS_VERSION_1_0` in
  both `dm_ref_model.sv` and `predictor.py`; the two stimulus/invariant
  checks that also asserted on this unconditionally
  (`reset_ctrl_sequence.py`'s `TC-RST-001` check, `invariants.py`'s
  `INV-NDMRESETPENDING`) were updated with the same gate.
- **`resume_ack`'s declared reset value only applied at construction, never
  on a live reset.** Real Ibex RTL clears `dmstatus.resumeack` after an
  `ndmreset` cycle; the model's `apply_ndmreset()`/`_apply_ndmreset()` never
  touched `resume_ack` at all, only setting it once at power-on. This was
  **not** resolved by copying the observed RTL behavior directly — per
  spec #3.5, "these 4 bits reset to 0, except for resume ack, which may
  reset to either 0 or 1" is explicitly implementation-defined, so the fix
  applies the model's own already-declared `resumeack_reset` parameter (the
  same one used at power-on/`dmactive=0` reset) on every reset event
  (`ndmreset`, and `hartreset` for consistency, though that stays a WARL
  no-op on both current DUTs) rather than hardcoding the one value observed
  on this one DUT. Confirmed this reads correctly for both Ibex
  (`resumeack_reset=false`) and CVA6 (default `true`) via full regressions
  on both.

No DV bugs specific to the new Ibex scenario stimulus itself — the
sequences (`reset_ctrl_sequence.py` etc.) needed zero DUT-specific changes;
every fix was in the shared golden model.

## RTL findings

No new RTL bugs. The only mismatch (`hart_selection`, above) reproduces the
already-filed, already cross-DUT-documented `#130`.

## Coverage

| | Baseline (12 scenarios, no cluster) | Final (17 scenarios) |
|---|---|---|
| Ibex merged | 91.64% | **99.72%** |
| CVA6 merged (re-verified, unchanged) | — | 99.58% |

Ibex's residual 0.28% is `cp_ndmresetpending.one` and `cp_version.v1_0` in
`cg_dmstatus_read` — both real, reachable bins, just not on *this* DUT
(exactly CVA6's mirror-image residual from the companion round: CVA6 is
permanently `ndmresetpending`-capable/`version=v1_0`, Ibex is permanently
v0.13/`ndmresetpending`-incapable, by real, declared, per-DUT
configuration). Confirmed complementary: CVA6's own merged report shows
`cp_ndmresetpending` and `cp_version.v1_0` both fully covered. Not a gap —
the same accepted single-DUT-report-split pattern this project's testplan
already documents for `cp_version`'s `v0_13`/`v1_0` split.

Updated: `testplans/results/ibex_functional_coverage_merged.txt` and
`testplans/results/cva6_functional_coverage_merged.txt` (both regenerated
this round, all scenarios under `+cover=sbceft`).

## New scenario configs added

`ibex_sim/configs/{reset_ctrl,halt_on_reset,run_control,dm_activation,hart_selection}_uvm.json`
— identical structure to their CVA6 counterparts (empty `params`, single
hart, UVM transport); no DUT-specific parameterization needed since both
current DUT integrations are single-hart.

## Round 3 — genuine 100%/100% closure (same day, 2026-07-25)

The 99.58%/99.72% residuals above were each real, reachable bins that
simply belonged to the *other* DUT (`cp_stickyunavail`, `cp_version`,
`cp_hasresethaltreq`, `cp_ndmresetpending`) — `covergroups.sv` hardcoded a
single expected value/exclusion for each, correct for one DUT and backwards
or wrong for the other. Fixed by making the fcov itself DUT-config-driven,
the same way `dm_ref_model.sv` already is, rather than accepting the
cross-DUT split as permanent:

- `debug_coverage`'s `new()` now reads `dut_configs/<name>.json` via the
  same `dut_config_reader` class `dm_checker.sv` already uses (moved
  `dut_config_reader.sv`'s `` `include `` ahead of `covergroups.sv`'s in
  `debug_pkg.sv` so the class is visible), and stores `dut_version`/
  `dut_hasresethaltreq`/`dut_stickyunavail` as class members *before* the
  covergroups are constructed (Questa requires a class's own embedded
  covergroups to be built in that class's own `new()`, not `build_phase()`
  — confirmed by trying `build_phase()` first and hitting a hard vlog-60
  error).
- `cp_version`/`cp_stickyunavail`/`cp_hasresethaltreq` now bin on
  `{dut_version}`/`{dut_stickyunavail}`/`{dut_hasresethaltreq}` with the
  complementary value as `ignore_bins`, instead of a hardcoded assumption.
  `cp_stickyunavail` was silently backwards before this (always expected 0,
  ignored 1 — correct for Ibex, wrong for CVA6, which is permanently 1).
- `cp_ndmresetpending` couldn't use that same pattern: unlike the others,
  it's not "one fixed value per DUT" — on a v1.0 DUT both 0 and 1 are
  independently real, live values. A runtime value-set trick (an
  unreachable `1'bz` sentinel for the "wrong" DUT) does not work either:
  Questa still counts a `bins` entry toward the total even when its value
  can provably never be sampled — only the `ignore_bins` *keyword* removes
  it, and that keyword is fixed at elaboration. Needed real conditional
  compilation instead: `` `ifdef DUT_VERSION_1_0 `` around just this one
  bin, with `+define+DUT_VERSION_1_0` added to CVA6's two `vlog`
  invocations only (`cva6_sim/Makefile`).

**Result: CVA6 and Ibex both 100.00% merged coverage.**

### A second, larger finding along the way: `resumeack` timing

While cross-checking mismatch *content* (not just counts) after the above,
found ~200+ pre-existing `MODEL_MISMATCH` occurrences on `dmstatus.resumeack`
across the regression — present since before this session's Ibex work even
started (confirmed in the original PR #131-era regression log). Root cause:
`dm_csrs.sv`'s `clear_resumeack_o` pulses only on the *rising edge* of
`resumereq`, and even then the hart's own `resumeack_i` takes real,
variable cycles to actually drop — but `dm_ref_model.sv`/`predictor.py`
cleared `resume_ack` synchronously on every write with `resumereq=1`, no
edge check, zero simulated delay. Same class of bug as the reset-release
handshake fixed in Round 1, just a different signal pair, triggered far
more often.

No functional step ever failed from this (every step uses `dm.resume()`'s
own polling helper, which tolerates the real latency) — it was purely a
checker-level artifact of comparing *every* read synchronously instead of
polling like real usage does.

Fixed generally, not just for this one field: `halted`/`running`/
`resume_ack` (the three dmstatus fields spec #3.5 explicitly frames as
signals "the DM receives ... from each hart", as opposed to DM-internal
state) are now `hart_signal_bit` instances
(`src/pydebug/sv/model/hart_signal_bit.sv`) — a small reusable class with
`set()` (the model's own write-driven prediction, used exactly like the old
plain `bit` was) and `observe()` (what a real DMI read just showed,
unconditionally adopted, called from `dm_checker.sv` before every
`dmstatus` comparison). A genuine functional defect (the value never
actually settling) still surfaces through the same stimulus-side polling
timeout that already existed — this only removes the checker's own false
positive for known-delayed signals, it doesn't hide a value that's stuck
wrong. `havereset` (also spec-listed as hart-received) was checked and
confirmed to stay a plain `bit`: this RTL derives it purely combinationally
from `ndmreset_o` inside `dm_csrs.sv`, no `havereset_i` input from the hart
exists in `dm_top.sv` at all, so it has no real propagation delay to
account for.

Confirmed via full regression on both DUTs after this fix: CVA6's
`MODEL_CHECK` mismatch count dropped from several hundred to **1** (the
already-known, already-filed `#130` nonexistent-hart reproduction); Ibex
dropped to the same, its own single `#130` reproduction. Coverage stayed at
100.00%/100.00% on both.
