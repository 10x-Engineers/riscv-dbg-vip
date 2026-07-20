"""
tests/test_reset_control.py — TC-RST-001..006, Reset signal / debug from first
instruction (spec #3.2).

Same pattern as test_run_control.py: run `build_reset_ctrl_sequence` once per
module, then assert on each TC-ID's `StepResult`(s) matched by message prefix.

Two DUT-shaped gaps are exercised here, matching the known CVA6 facts this
stimulus was designed around (see reset_ctrl_sequence.py's module docstring):

  * A "fully-featured" pass (`supports_hartreset=True`) proves TC-RST-002's
    positive path actually works when a DUT does implement hartreset.
  * A separate "CVA6-like" pass (`supports_hartreset=False`) proves the
    discovery mechanism correctly reports N/A rather than failing when it
    does not -- this is the divergence CVA6's dm_csrs.sv:511 (hartreset tied
    0) actually produces, so it must be tested honestly, not just assumed.
"""

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.reset_ctrl_sequence import build_reset_ctrl_sequence


@pytest.fixture(scope="module")
def rst_results():
    """One continuous run against a fully-featured mock (hartreset
    implemented), so TC-RST-002/003's positive paths are actually exercised."""
    t = ModelBackedMockTransport(supports_hartreset=True)
    t.connect()
    dm = RISCVDebug(t)
    session = build_reset_ctrl_sequence(dm, mode="batch")
    return session.run()


@pytest.fixture(scope="module")
def rst_results_no_hartreset():
    """A second run against a CVA6-like mock (hartreset NOT implemented, per
    dm_csrs.sv:511 tying it to 0), so the TC-RST-002 discovery mechanism's N/A
    branch is exercised and confirmed honest rather than assumed."""
    t = ModelBackedMockTransport(supports_hartreset=False)
    t.connect()
    dm = RISCVDebug(t)
    session = build_reset_ctrl_sequence(dm, mode="batch")
    return session.run()


def _steps_for(results, tc_id):
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult was produced for {tc_id} — sequence step missing or renamed"
    return matches


@pytest.mark.feature("reset_control")
@pytest.mark.smoke
def test_tc_rst_001_ndmreset_platform_reset(rst_results):
    """TC-RST-001: ndmreset platform reset -- every hart resets; the
    ndmresetpending clause is checked against the golden model, per the
    CVA6 dm_pkg.sv gap this stimulus is designed around (spec #3.2/#3.14.1)."""
    for r in _steps_for(rst_results, "TC-RST-001"):
        assert r.ok, r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_002_hartreset_selected_hart_reset(rst_results):
    """TC-RST-002: hartreset selected-hart reset, on a DUT that implements it
    (spec #3.14.2 hartreset)."""
    for r in _steps_for(rst_results, "TC-RST-002"):
        assert r.ok, r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_002_hartreset_is_na_when_not_implemented(rst_results_no_hartreset):
    """TC-RST-002 on a DUT where hartreset is WARL-tied to 0 (CVA6
    dm_csrs.sv:511): the discovery write must report N/A, not a failure."""
    for r in _steps_for(rst_results_no_hartreset, "TC-RST-002"):
        assert r.ok, r.msg
        assert "N/A" in r.msg or "not implemented" in r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_003_havereset_set_regardless_of_cause(rst_results):
    """TC-RST-003: havereset set regardless of reset cause -- exercised via
    both ndmreset and hartreset causes (spec #3.2)."""
    for r in _steps_for(rst_results, "TC-RST-003"):
        assert r.ok, r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_004_ackhavereset_clears_sticky_bit(rst_results):
    """TC-RST-004: ackhavereset clears the sticky havereset bit for the
    selected hart(s) (spec #3.14.2 ackhavereset)."""
    for r in _steps_for(rst_results, "TC-RST-004"):
        assert r.ok, r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_005_dmi_access_restrictions_during_ndmreset(rst_results):
    """TC-RST-005: DMI access restrictions while ndmreset is asserted -- the
    DM must not hang or corrupt state; the specific read-back value during
    the restricted window is UNSPECIFIED per spec #3.2 and not asserted on."""
    for r in _steps_for(rst_results, "TC-RST-005"):
        assert r.ok, r.msg


@pytest.mark.feature("reset_control")
def test_tc_rst_006_ackhavereset_noop_when_already_clear(rst_results):
    """TC-RST-006: ackhavereset written when havereset is already clear must
    be a harmless no-op (spec #3.14.2 says nothing special about this case,
    which is exactly why it needs its own directed test)."""
    for r in _steps_for(rst_results, "TC-RST-006"):
        assert r.ok, r.msg
