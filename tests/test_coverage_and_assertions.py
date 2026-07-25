"""
tests/test_coverage_and_assertions.py — Coverage closure and architectural
invariants across the full run-control/reset/halt-on-reset stimulus.

Feeds every TC-RC/TC-RST/TC-HOR sequence, run across the DUT configurations
that let each one reach its intended positive path, through both
`DebugCoverageModel` (feature `coverage_model`) and `invariants.check_all`
(feature `assertions`) simultaneously, off one shared `ObservingTransport`
per pass -- exactly the wiring `coverage.py`/`invariants.py`'s own module
docstrings describe.

Three passes feed the same coverage model and violation list:

  A. Fully-featured (num_harts=2, hasresethaltreq=True, supports_hartreset=True):
     every TC-ID's positive path, including TC-HOR-004's per-hart independence
     and TC-RST-002/003's hartreset leg.
  B. CVA6-like (hasresethaltreq=False): exercises the TC-HOR-001 gate's "0"
     bin, which pass A (feature enabled) cannot reach.
  C. The real declared CVA6 config (dut_configs/cva6.json, riscv-dbg-vip#117):
     exercises dmstatus.version=v1_0 and its declared capability bits
     (stickyunavail etc.) together -- Ibex stays v0.13, so this is still the
     only pass that reaches the v1_0 bin.

The one thing the earlier (stopped) instance of this task diagnosed and got
right, preserved here: `invariants.check_all`'s `prev_state` argument must be a
`predictor.snapshot()` taken *before* the transaction it is being asked about,
not a stale or post-transaction one. `_SnapshotBeforeTransport` below exists
for exactly that reason -- `ObservingTransport`'s callback only fires *after*
the delegate op completes, so the pre-state has to be captured by wrapping
`read`/`write` themselves, one layer further out.
"""

import pytest

from pydebug.api.observer import ObservingTransport
from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.coverage import DebugCoverageModel
from pydebug.model.dut_config import load_dut_config
from pydebug.model.invariants import check_all
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.dm_activation_sequence import build_dm_activation_sequence
from pydebug.sequences.halt_on_reset_sequence import build_halt_on_reset_sequence
from pydebug.sequences.hart_selection_sequence import build_hart_selection_sequence
from pydebug.sequences.reset_ctrl_sequence import build_reset_ctrl_sequence
from pydebug.sequences.run_control_sequence import build_run_control_sequence


class _SnapshotBeforeTransport(ObservingTransport):
    """An ObservingTransport that also snapshots predictor state immediately
    BEFORE each transaction, in `self.prev` -- the piece `check_all` needs
    that the observer callback alone cannot provide, since that callback only
    fires after the delegate op has already completed."""

    def __init__(self, delegate, predictor):
        super().__init__(delegate)
        self._predictor = predictor
        self.prev = None

    def read(self, addr):
        self.prev = self._predictor.snapshot()
        return super().read(addr)

    def write(self, addr, data):
        self.prev = self._predictor.snapshot()
        return super().write(addr, data)


@pytest.fixture(scope="module")
def full_trace():
    """Runs all three passes described in the module docstring, returning
    (coverage_model, violations, per_pass_results)."""
    cov = DebugCoverageModel(num_harts=2, supports_stickyunavail=True)
    violations = []
    pass_session_results = []

    def run_pass(predictor_kwargs, build):
        backend = ModelBackedMockTransport(**predictor_kwargs)
        t = _SnapshotBeforeTransport(backend, backend.predictor)

        def observe(op, addr, data, readback):
            violations.extend(check_all(t.prev, op, addr, data, readback, backend.predictor))
            cov.sample(op, addr, data, readback)

        t.add_observer(observe)
        t.connect()
        dm = RISCVDebug(t)
        pass_session_results.append(build(dm))

    # Pass A — fully-featured DUT: every TC-ID's positive path. The full
    # run_control cluster is 5 sequences/23 TC-IDs (testplan's own framing)
    # -- dm_activation and hart_selection were missing here entirely until
    # 2026-07-25, which is why dmcontrol.dmactive.0/hasel.1/hartsel.* sat
    # permanently unhit despite having real, working stimulus all along.
    def pass_a(dm):
        results = []
        results.append(build_run_control_sequence(dm, mode="batch").run())
        results.append(build_reset_ctrl_sequence(dm, mode="batch").run())
        results.append(build_halt_on_reset_sequence(dm, mode="batch", num_harts=2).run())
        results.append(build_dm_activation_sequence(dm, mode="batch").run())
        results.append(build_hart_selection_sequence(dm, mode="batch").run())
        return results
    run_pass(dict(num_harts=2, hasresethaltreq=True, supports_hartreset=True), pass_a)

    # Pass B — CVA6-like DUT: hasresethaltreq=0 (dm_csrs.sv:235), for the gate bin.
    def pass_b(dm):
        return [build_halt_on_reset_sequence(dm, mode="batch", num_harts=1).run()]
    run_pass(dict(num_harts=1, hasresethaltreq=False), pass_b)

    # Pass C — the real declared CVA6 config (dut_configs/cva6.json), for
    # dmstatus.version=v1_0 and its declared capability bits (stickyunavail
    # etc.) together, rather than a hand-picked partial override that can
    # silently miss a field -- exactly the gap riscv-dbg-vip#117 found
    # (stickyunavail wasn't declared here, so its coverage bin was still
    # wrongly excluded even after the model started predicting it).
    def pass_c(dm):
        return [build_run_control_sequence(dm, mode="batch").run()]
    run_pass(load_dut_config("cva6").predictor_kwargs(), pass_c)

    return cov, violations, pass_session_results


@pytest.mark.feature("coverage_model")
@pytest.mark.smoke
def test_run_control_slice_coverage_closure(full_trace):
    """Every dmcontrol/dmstatus run-control bin that has a TC-ID assigned to
    it (in coverage.py's own Bin.tc field) is hit by this stimulus. The only
    bins left un-hit are architectural test-plan gaps that no TC-ID covers —
    a finding about the test plan, not about this stimulus (see coverage.py's
    own module docstring on why 'unhit' and 'excluded' are kept separate, and
    this suite's report on which specific bins these are)."""
    cov, _violations, _results = full_trace
    report = cov.report()

    # No excluded bin was ever hit — a false exclusion would be a hole the
    # model claims doesn't exist, which is worse than a known un-hit bin.
    assert not report["excluded_hits"], (
        f"excluded bins were hit — their exclusion reason is wrong: {report['excluded_hits']}"
    )

    # Every un-hit bin must be a genuine test-plan gap (Bin.tc is None) —
    # anything with a real TC-ID assigned that stayed un-hit is a stimulus bug.
    unhit_with_tc = [u for u in report["unhit"] if u["tc"] is not None]
    assert not unhit_with_tc, (
        "these bins have a TC-ID assigned but were not hit by that TC-ID's "
        f"stimulus: {unhit_with_tc}"
    )

    # The number the coverage agent originally reported (16 TC-IDs -> 89/104,
    # 15 test-plan gaps) — pinned here so a future regression in either the
    # stimulus or the bin set is caught precisely, not just "coverage dropped."
    # riscv-dbg-vip#117 changed two things that net back to the same 89/104:
    #  - dmstatus.stickyunavail=1 for v1.0 DUTs is now legitimately hit by
    #    pass C's real CVA6 config (dut_configs/cva6.json), not excluded.
    #  - dmstatus.version is confirmed NOT gated by dmactive on either real
    #    DUT (dm_csrs.sv assigns it unconditionally), so version=0 pre-
    #    activation was a model bug, not real behavior; "version.none" moved
    #    from a (spuriously) hit bin to a properly excluded one, since no
    #    real DUT stimulus can produce it.
    # 88/103/15 (was 89/104/15): cross.hart_state_transition.halted_to_in_
    # reset moved from a (wrongly) tc-owned unhit bin to a properly excluded
    # one. It looked reachable via ndmreset while a hart is halted, but a
    # real CVA6 UVM run proved otherwise: both DUTs' dm_mem.sv only resets
    # halted_q on !rst_ni (the DM's own reset) -- ndmreset deliberately
    # doesn't touch the DM's own registers, so an already-halted hart stays
    # reported halted throughout an ndmreset cycle, unaffected by it. Its
    # other candidate mechanism, hartreset (TC-RST-002), is WARL-tied to 0
    # on both DUTs. Neither produces this transition on real hardware, so
    # it is excluded (model/coverage.py), not forced with stimulus that
    # doesn't actually work (riscv-dbg-vip, 2026-07-25) -- verified via the
    # unhit_with_tc check above that every TC-ID-owned bin is covered.
    #
    # 100/100/0 (was 88/103/15) -- full closure of every remaining test-plan
    # gap, 2026-07-25:
    #  - dmactive.0/hasel.1/hartsel.* (5 bins): full_trace's own pass_a was
    #    missing build_dm_activation_sequence/build_hart_selection_sequence
    #    entirely despite having real, working stimulus all along -- fixed
    #    in this fixture, not a model or RTL change.
    #  - allnonexistent.1/anynonexistent.1/all_any.nonexistent.all1_any1
    #    (3 bins): mislabeled permanent gaps -- genuinely reachable via
    #    TC-HS-002, now correctly attributed in coverage.py.
    #  - cross.ndmreset_x_reset_haltreq.assert_rhr1/deassert_rhr1 (2 bins)
    #    + cross.hart_state_transition.in_reset_to_halted (1 bin, re-owned
    #    from TC-HOR-002 to TC-RST-001 (cont'd)): TC-HOR-002/003 now always
    #    perform the setresethaltreq/clrresethaltreq write regardless of the
    #    hasresethaltreq gate (gating only the functional assertion), and
    #    TC-RST-001 gained a new haltreq-during-reset step exercising the
    #    universally-supported substitute for the DUT-unsupported
    #    resethaltreq path.
    #  - cross.resumereq_x_prior_state.resumereq_when_in_reset (1 bin):
    #    TC-RC-007's dm.ndmreset(True) is write-only with no read-back; an
    #    intervening dm.read_dmstatus() now lets cur_state actually observe
    #    "in reset" before the resumereq write is evaluated.
    #  - dmcontrol.setresethaltreq.1/clrresethaltreq.1/ackunavail.1 (write-
    #    coverage, 3 bins) + dmcontrol.setkeepalive.1/clrkeepalive.1 (2
    #    bins): closed by discovery-probe steps (TC-DHS-006, TC-KA-001) that
    #    always perform the write and check only "DM stays alive" -- same
    #    pattern as the resethaltreq gate fix above.
    #  - dmstatus.allunavail.1/anyunavail.1/all_any.unavail.all1_any1 (3
    #    bins): properly excluded, not forced -- both current SoC
    #    integrations (CVA6-fork/corev_apu/tb/ariane_testharness.sv,
    #    ibex-demo-system/rtl/system/ibex_demo_system.sv) hardwire the DM's
    #    unavailable_i input to constant 0, confirmed against real RTL.
    #  See testplans/riscv_debug_testplan.md (2026-07-25 revision) for the
    #  corresponding testplan-side updates to every TC-ID referenced above.
    assert report["summary"]["hit"] == 100, report["summary"]
    assert report["summary"]["bins"] == 100, report["summary"]
    assert len(report["unhit"]) == 0, report["unhit"]


@pytest.mark.feature("assertions")
@pytest.mark.smoke
def test_zero_dut_invariant_violations_across_full_trace(full_trace):
    """No DUT-kind architectural invariant is violated anywhere in the trace.

    Two TC-IDs (TC-RST-005, TC-HOR-005) deliberately violate a
    *stimulus-legality* rule on purpose (accessing other DMI registers during
    ndmreset; writing more than one dmcontrol mutex bit at once) — per
    invariants.py's own design, those must be observable as data, not treated
    as failures, so they are asserted on separately below rather than folded
    into "zero violations."
    """
    _cov, violations, _results = full_trace
    dut_violations = [v for v in violations if not v.stimulus_legality]
    assert not dut_violations, "\n".join(str(v) for v in dut_violations)


@pytest.mark.feature("assertions")
def test_expected_stimulus_legality_violations_fire_as_designed(full_trace):
    """The two deliberately-illegal TC-IDs actually produce the
    stimulus-legality violation they exist to provoke (TC-RST-005:
    INV-STIM-DMI-DURING-NDMRESET; TC-HOR-005: INV-STIM-DMCONTROL-MUTEX) — if
    neither fires, the negative tests are not actually exercising the illegal
    path they claim to."""
    _cov, violations, _results = full_trace
    stim_violations = [v for v in violations if v.stimulus_legality]
    rules_seen = {v.rule for v in stim_violations}
    assert "INV-STIM-DMI-DURING-NDMRESET" in rules_seen, (
        "TC-RST-005 did not provoke INV-STIM-DMI-DURING-NDMRESET"
    )
    assert "INV-STIM-DMCONTROL-MUTEX" in rules_seen, (
        "TC-HOR-005 did not provoke INV-STIM-DMCONTROL-MUTEX"
    )
    assert all(v.tc_ids for v in stim_violations), (
        "every stimulus-legality violation must trace back to the TC-ID that provokes it"
    )
