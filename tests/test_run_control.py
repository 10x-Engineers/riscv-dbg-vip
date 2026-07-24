"""
tests/test_run_control.py — TC-RC-001..007, Halt/Resume individual hart (spec #3.5).

Runs `build_run_control_sequence` once per module against the model-backed mock
(`ModelBackedMockTransport` / `DMPredictor`), then asserts on the specific
`StepResult`s belonging to each TC-ID — matched by the "TC-RC-NNN:" prefix every
sequence step's message carries, rather than by step index, so the tests stay
correct if steps are re-ordered or new ones inserted.

The sequence itself does the self-checking (`StepResult.ok`), cross-checked
against `DMPredictor.expect()` wherever the transport carries one — see
`run_control_sequence.py`'s own docstring for the rationale. These tests confirm
that self-check actually ran and actually passed for each TC-ID; they do not
duplicate the sequence's assertion logic.
"""

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.run_control_sequence import build_run_control_sequence


@pytest.fixture(scope="module")
def rc_results():
    """One continuous run of the whole run-control sequence, shared by every
    TC-RC test in this module — TC-RC-004/005 are only meaningful as
    continuations of TC-RC-003's resumed state, exactly as the test plan's own
    stimulus column implies ("With hart running, write resumereq=1", etc.)."""
    t = ModelBackedMockTransport()
    t.connect()
    dm = RISCVDebug(t)
    session = build_run_control_sequence(dm, mode="batch")
    return session.run()


def _steps_for(results, tc_id):
    """Every StepResult produced by the given TC-ID's step(s), in order."""
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult was produced for {tc_id} — sequence step missing or renamed"
    return matches


@pytest.mark.feature("run_control")
@pytest.mark.smoke
def test_tc_rc_001_halt_request_on_running_hart(rc_results):
    """TC-RC-001: Halt request on a running hart -> halted asserted, running
    deasserted, dmstatus.anyhalted/allhalted=1 (spec #3.5)."""
    for r in _steps_for(rc_results, "TC-RC-001"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_002_halt_request_ignored_once_halted(rc_results):
    """TC-RC-002: Halt request ignored once already halted -- "Halted harts
    ignore their halt request bit" (spec #3.5)."""
    for r in _steps_for(rc_results, "TC-RC-002"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_003_resume_request_on_halted_hart(rc_results):
    """TC-RC-003: Resume request on a halted hart -> running asserted, halted
    deasserted, resume-ack set, dmstatus.allresumeack/anyresumeack=1 (spec #3.5)."""
    for r in _steps_for(rc_results, "TC-RC-003"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_004_resume_request_ignored_on_running_hart(rc_results):
    """TC-RC-004: Resume request ignored on a running hart -- "Resume requests
    are ignored by running harts" (spec #3.5), though resume ack is still
    cleared (the documented asymmetry)."""
    for r in _steps_for(rc_results, "TC-RC-004"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_005_resumereq_ignored_when_haltreq_set(rc_results):
    """TC-RC-005: resumereq ignored when haltreq also set in the same write --
    "resumereq is ignored if haltreq is set" (spec #3.14.2)."""
    for r in _steps_for(rc_results, "TC-RC-005"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_006_halt_resume_response_latency(rc_results):
    """TC-RC-006: Halt/resume response latency under the spec's own 1-second
    bound (spec #3.5: "a hart must respond in less than one second")."""
    for r in _steps_for(rc_results, "TC-RC-006"):
        assert r.ok, r.msg


@pytest.mark.feature("run_control")
def test_tc_rc_007_resumereq_while_in_reset(rc_results):
    """TC-RC-007: resumereq written while the hart is held in ndmreset --
    #3.5 only sends a resume request to a HALTED hart, so a hart that was
    never halted (in reset, per both DUTs' real ~halted & ~unavailable
    running formula, #3.2) must not spuriously become halted or resume-ack."""
    for r in _steps_for(rc_results, "TC-RC-007"):
        assert r.ok, r.msg
