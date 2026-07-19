"""
tests/test_halt_on_reset.py — TC-HOR-001..005, Halt-on-reset (spec #3.5, Optional).

Same pattern as test_run_control.py / test_reset_control.py: run
`build_halt_on_reset_sequence` once per module, assert on each TC-ID's
`StepResult`(s) matched by message prefix.

TC-HOR-001 is a gate (per the test plan): two module-scoped fixtures exist
specifically to prove the gate works *both* ways --

  * `hor_results` (hasresethaltreq=True, num_harts=2): the feature is
    implemented, so TC-HOR-002..005 must actually execute and pass.
  * `hor_results_unsupported` (hasresethaltreq=False): matches CVA6's
    dm_csrs.sv:235 (hasresethaltreq hardwired 0). TC-HOR-002..004 must report
    N/A, not failed -- that IS the correct, spec-compliant result on this DUT.
"""

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.halt_on_reset_sequence import build_halt_on_reset_sequence


@pytest.fixture(scope="module")
def hor_results():
    """Halt-on-reset implemented, 2 harts -- exercises every positive path,
    including TC-HOR-004's per-hart independence."""
    t = ModelBackedMockTransport(num_harts=2, hasresethaltreq=True)
    t.connect()
    dm = RISCVDebug(t)
    session = build_halt_on_reset_sequence(dm, mode="batch", num_harts=2)
    return session.run()


@pytest.fixture(scope="module")
def hor_results_unsupported():
    """CVA6-like DUT: dmstatus.hasresethaltreq=0 (dm_csrs.sv:235). Every HOR
    TC-ID except the gate itself and the ungated negative test must report
    N/A here, per the test plan's own instruction."""
    t = ModelBackedMockTransport(num_harts=1, hasresethaltreq=False)
    t.connect()
    dm = RISCVDebug(t)
    session = build_halt_on_reset_sequence(dm, mode="batch", num_harts=1)
    return session.run()


def _steps_for(results, tc_id):
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult was produced for {tc_id} — sequence step missing or renamed"
    return matches


@pytest.mark.feature("halt_on_reset")
@pytest.mark.smoke
def test_tc_hor_001_discover_halt_on_reset_support(hor_results):
    """TC-HOR-001: discover halt-on-reset support by reading
    dmstatus.hasresethaltreq (spec #3.14.1). Discovery always succeeds as a
    step; the *value* it finds is the thing under test."""
    for r in _steps_for(hor_results, "TC-HOR-001"):
        assert r.ok, r.msg
    assert "implemented" in _steps_for(hor_results, "TC-HOR-001")[0].msg


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_001_gate_reports_na_when_unsupported(hor_results_unsupported):
    """TC-HOR-001 as a gate on a DUT without halt-on-reset (CVA6
    dm_csrs.sv:235): the gate itself still reports its finding cleanly, and
    every downstream HOR TC-ID must report N/A rather than fail."""
    gate = _steps_for(hor_results_unsupported, "TC-HOR-001")[0]
    assert gate.ok
    assert "NOT implemented" in gate.msg
    for tc_id in ("TC-HOR-002", "TC-HOR-003", "TC-HOR-004"):
        for r in _steps_for(hor_results_unsupported, tc_id):
            assert r.ok, r.msg
            assert "N/A" in r.msg, f"{tc_id} should report N/A, not silently pass: {r.msg}"


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_002_setresethaltreq_causes_halt_on_reset(hor_results):
    """TC-HOR-002: setresethaltreq causes halt-on-reset -- the hart enters
    Debug Mode immediately on reset deassertion, regardless of reset cause
    (spec #3.5)."""
    for r in _steps_for(hor_results, "TC-HOR-002"):
        assert r.ok, r.msg


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_003_clrresethaltreq_clears_request(hor_results):
    """TC-HOR-003: clrresethaltreq clears the request -- the hart does not
    halt on the next reset deassertion (spec #3.14.2)."""
    for r in _steps_for(hor_results, "TC-HOR-003"):
        assert r.ok, r.msg


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_004_per_hart_independence(hor_results):
    """TC-HOR-004: per-hart independence -- only the hart with
    setresethaltreq set halts; the other hart's behaviour is undisturbed
    (spec #3.14.2's split set/clrresethaltreq design rationale)."""
    for r in _steps_for(hor_results, "TC-HOR-004"):
        assert r.ok, r.msg


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_005_illegal_simultaneous_bit_write(hor_results):
    """TC-HOR-005 (negative): writing more than one dmcontrol mutex bit in a
    single access is a protocol violation (spec #3.14.2); the DM must survive
    it without corrupting state. Not gated on hasresethaltreq -- the mutex
    rule applies to dmcontrol generally."""
    for r in _steps_for(hor_results, "TC-HOR-005"):
        assert r.ok, r.msg


@pytest.mark.feature("halt_on_reset")
def test_tc_hor_005_illegal_write_survives_even_when_hor_unsupported(hor_results_unsupported):
    """TC-HOR-005 is ungated: it must still run (and the DM must still
    survive it) on a DUT where halt-on-reset itself is not implemented."""
    for r in _steps_for(hor_results_unsupported, "TC-HOR-005"):
        assert r.ok, r.msg
