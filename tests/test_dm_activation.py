"""
tests/test_dm_activation.py — TC-DMA-001..002, DM Activation (spec #3.14.2).

Same pattern as test_run_control.py: run `build_dm_activation_sequence` once
per module, then assert on each TC-ID's `StepResult`(s) matched by message
prefix.
"""

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.sequences.dm_activation_sequence import build_dm_activation_sequence


@pytest.fixture(scope="module")
def dma_results():
    t = ModelBackedMockTransport()
    t.connect()
    dm = RISCVDebug(t)
    session = build_dm_activation_sequence(dm, mode="batch")
    return session.run()


def _steps_for(results, tc_id):
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult was produced for {tc_id} — sequence step missing or renamed"
    return matches


@pytest.mark.feature("dm_activation")
@pytest.mark.smoke
def test_tc_dma_001_deactivate_resets_dm(dma_results):
    """TC-DMA-001: writing dmcontrol.dmactive=0 takes the DM to its reset
    state (spec #3.14.2)."""
    for r in _steps_for(dma_results, "TC-DMA-001"):
        assert r.ok, r.msg


@pytest.mark.feature("dm_activation")
def test_tc_dma_002_known_state_reset_sequence(dma_results):
    """TC-DMA-002: the spec's own documented write0/poll/write1/poll known-state
    recovery procedure (spec #3.14.2 dmactive) actually works end to end."""
    for r in _steps_for(dma_results, "TC-DMA-002"):
        assert r.ok, r.msg
