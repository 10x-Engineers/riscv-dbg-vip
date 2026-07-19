"""
tests/test_hart_selection.py — TC-HS-001..003, Hart Selection (spec #3.14.2).

Same pattern as test_run_control.py: run `build_hart_selection_sequence` once
per module against a 2-hart model-backed mock (so TC-HS-002's "nonexistent
hart" case has a real boundary to select past), then assert on each TC-ID's
`StepResult`(s) matched by message prefix.
"""

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.hart_selection_sequence import build_hart_selection_sequence


@pytest.fixture(scope="module")
def hs_results():
    t = ModelBackedMockTransport(num_harts=2)
    t.connect()
    dm = RISCVDebug(t)
    session = build_hart_selection_sequence(dm, mode="batch")
    return session.run()


def _steps_for(results, tc_id):
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult was produced for {tc_id} — sequence step missing or renamed"
    return matches


@pytest.mark.feature("hart_selection")
@pytest.mark.smoke
def test_tc_hs_001_hartsellen_discovery(hs_results):
    """TC-HS-001: writing all-1s across hartsello/hartselhi and reading back
    is the spec's own documented HARTSELLEN discovery method (spec #3.14.2)."""
    for r in _steps_for(hs_results, "TC-HS-001"):
        assert r.ok, r.msg


@pytest.mark.feature("hart_selection")
def test_tc_hs_002_nonexistent_hart_selected(hs_results):
    """TC-HS-002: selecting a hart index beyond the implemented count sets
    dmstatus.anynonexistent/allnonexistent (spec #3.14.1)."""
    for r in _steps_for(hs_results, "TC-HS-002"):
        assert r.ok, r.msg


@pytest.mark.feature("hart_selection")
def test_tc_hs_003_hasel_discovery_write(hs_results):
    """TC-HS-003: writing hasel=1 and reading back is the spec's own
    documented method for discovering hart-array-mask support (spec #3.14.2)."""
    for r in _steps_for(hs_results, "TC-HS-003"):
        assert r.ok, r.msg
