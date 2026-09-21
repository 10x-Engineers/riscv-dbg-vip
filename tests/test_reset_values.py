"""
tests/test_reset_values.py — RST-030 … RST-043, the post-reset register sweep.

The sequence reads every DM register immediately after `dmactive` 0→1 and
compares it with the spec's reset column and the DUT's declared presets. Run
here against the model-backed mock, whose predictor is loaded with the same
`dut_configs/cva6.json` declaration the sequence checks against: the two agree
only if both read the declaration the same way, which is the point — a typo in
either side's field position shows up as a failing check rather than as a
number nobody compares.

The second fixture flips a preset (`progbufsize`) in the model without telling
the sequence, so the negative path is exercised too: a check that cannot fail
is not a check.
"""

import dataclasses

import pytest

from pydebug.api.riscv_dm import RISCVDebug
from pydebug.model.dut_config import load_dut_config
from pydebug.model.mock_transport import ModelBackedMockTransport
from pydebug.model.predictor import DMPredictor
from pydebug.sequences.reset_values_sequence import build_reset_values_sequence

pytestmark = pytest.mark.feature("reset_control")


def _run(cfg_mutation=None):
    cfg = load_dut_config("cva6").declared_config()
    if cfg_mutation:
        cfg = dataclasses.replace(cfg, **cfg_mutation)
    predictor = DMPredictor()
    predictor.set_config(cfg)
    t = ModelBackedMockTransport(predictor=predictor)
    t.connect()
    return build_reset_values_sequence(RISCVDebug(t), mode="batch").run()


@pytest.fixture(scope="module")
def results():
    return _run()


def _step(results, tc_id):
    matches = [r for r in results if r.msg.startswith(f"{tc_id}:")]
    assert matches, f"no StepResult for {tc_id} — step missing or renamed"
    return matches[0]


#: The two checks the mock cannot satisfy, and why. `data0` and `sbdata0` are
#: not modelled by the predictor, so ModelBackedMockTransport answers them from
#: its canned table with deliberate sentinels (0xdeadbeef, 0xcafe0000) that
#: exist precisely so a test cannot mistake them for modelled values. On the DUT
#: these registers do read 0 after a DM reset; here they must not, and saying so
#: is better than weakening the check until the mock passes it.
MOCK_SENTINEL_CHECKS = {"RST-036-C", "RST-039-C"}


@pytest.mark.smoke
def test_every_check_runs_and_passes_against_the_declared_config(results):
    """Every RST-03x/04x check produces a result, and the model — built from the
    same declaration — satisfies all of them bar the two the mock answers with
    sentinels."""
    ids = [r.msg.split(":")[0] for r in results if r.msg.startswith("RST-")]
    assert ids == ["RST-030-C", "RST-032-C", "RST-033-C", "RST-034-C",
                   "RST-035-C", "RST-036-C", "RST-037-C", "RST-038-C",
                   "RST-039-C", "RST-040-C", "RST-042-C", "RST-043-C"]
    failed = {r.msg.split(":")[0] for r in results if not r.ok}
    assert failed == MOCK_SENTINEL_CHECKS, (
        "unexpected failures: " + "\n".join(r.msg for r in results if not r.ok))


def test_the_sentinel_failures_name_the_register_that_was_not_zero(results):
    """A failing reset check must say which register and what it read, or it
    cannot be acted on."""
    assert "data0=0xdeadbeef" in _step(results, "RST-036-C").msg
    assert "sbdata0=0xcafe0000" in _step(results, "RST-039-C").msg


def test_dmcontrol_reports_only_dmactive_set(results):
    """RST-030: after a DM reset the only bit set is dmactive — in particular
    hartsel is 0, so a later test cannot inherit a stale hart selection."""
    assert "dmcontrol=0x00000001" in _step(results, "RST-030-C").msg


def test_hartinfo_matches_the_declared_presets(results):
    """RST-032: nscratch=2, dataaccess=1, datasize=2, dataaddr=0x380 — the DM
    borrows dscratch0/1 and puts `data` at 0x380 (dut_configs/cva6.json)."""
    assert _step(results, "RST-032-C").ok


def test_abstractcs_reports_no_command_and_no_error(results):
    """RST-033: busy=0 and cmderr=0 are architectural; progbufsize=8 and
    datacount=2 are this DUT's declared parameters."""
    msg = _step(results, "RST-033-C").msg
    assert "abstractcs=0x0800" in msg.replace("_", "")   # progbufsize=8


def test_command_and_abstractauto_read_zero(results):
    assert _step(results, "RST-034-C").ok
    assert _step(results, "RST-035-C").ok


def test_halt_summaries_are_zero_with_nothing_halted(results):
    """RST-040. On the DUT this is where RTL-007 shows (haltsum1 bit 0 reads
    X); the model has no such defect, so here it passes."""
    assert _step(results, "RST-040-C").ok


def test_dtmcs_is_reported_not_available_on_a_dmi_only_transport(results):
    """RST-043: dtmcs is a JTAG register with no DMI address. A transport that
    cannot reach it must say so, not pass silently as if it had checked."""
    assert "N/A" in _step(results, "RST-043-C").msg


def test_a_wrong_preset_is_caught():
    """The negative path: if the DM came up with a different progbufsize from
    the one it was configured with, RST-033 must fail."""
    results = _run({"progbufsize": 4})
    step = _step(results, "RST-033-C")
    assert not step.ok and "progbufsize=4 (expect 8)" in step.msg
