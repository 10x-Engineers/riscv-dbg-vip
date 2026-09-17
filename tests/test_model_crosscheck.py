"""
test_model_crosscheck.py -- the Python reference model's ported behaviour, and
the replay tool that holds it to dm_ref_model.sv (riscv-dbg-vip#75).

No simulator: traces here are synthetic. A real cross-check replays the traces
a simulation writes with +DM_MODEL_TRACE.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from pydebug.model.dut_config import load_dut_config
from pydebug.model.predictor import DMPredictor

ROOT = Path(__file__).resolve().parent.parent
CVA6_CFG = ROOT / "src" / "pydebug" / "dut_configs" / "cva6.json"

_spec = importlib.util.spec_from_file_location("model_crosscheck", ROOT / "mk" / "model_crosscheck.py")
crosscheck = importlib.util.module_from_spec(_spec)
sys.modules["model_crosscheck"] = crosscheck   # @dataclass looks its module up here
_spec.loader.exec_module(crosscheck)

DMCONTROL, DMSTATUS, DATA0, COMMAND, SBCS, SBADDRESS0, SBDATA0 = 0x10, 0x11, 0x04, 0x17, 0x38, 0x39, 0x3C
ACTIVE = 0x1


pytestmark = pytest.mark.feature("reference_model")


@pytest.fixture
def model():
    p = DMPredictor()
    p.set_config(load_dut_config("cva6").declared_config())
    p.on_write(DMCONTROL, ACTIVE)
    return p


def test_declared_registers_match_the_rtl_values_seen_in_simulation(model):
    # Values the CVA6 DM returned in the regression, predicted from the
    # declaration alone.
    assert model.predict(0x38) == 0x2006_0808      # sbcs
    assert model.predict(0x12) == 0x0021_2380      # hartinfo
    assert model.predict(0x16) & model.predict_mask(0x16) == 0x0800_0002  # abstractcs


def test_nothing_with_a_preset_is_claimed_before_the_config_is_applied():
    p = DMPredictor()
    assert p.has_model(DMSTATUS) and p.has_model(DMCONTROL)
    assert not any(p.has_model(a) for a in (0x12, 0x16, 0x17, 0x18, 0x38, 0x40))


def test_resume_with_dcsr_step_rehalts(model):
    model.on_write(DMCONTROL, ACTIVE | 1 << 31)            # halt
    model.on_write(DATA0, 1 << 2)                           # dcsr.step=1
    model.on_write(COMMAND, (2 << 20) | (1 << 17) | (1 << 16) | 0x07B0)
    model.on_write(DMCONTROL, ACTIVE | 1 << 30)             # resume
    status = model.predict(DMSTATUS)
    assert status >> 9 & 1 and not status >> 11 & 1        # halted again


def test_writes_are_dropped_while_a_command_is_busy(model):
    model.on_write(DATA0, 0x1234)
    model.on_write(COMMAND, (2 << 20) | (1 << 17) | (1 << 16) | 0x1005)
    model.set_observed_cmdbusy(True)
    model.on_write(DATA0, 0x9999)                           # refused
    model.on_write(COMMAND, (2 << 20) | (1 << 17) | 0x1005)  # refused too
    model.set_observed_cmdbusy(False)
    model.on_write(COMMAND, (2 << 20) | (1 << 17) | 0x1005)  # read x5
    assert model.has_model(DATA0) and model.predict(DATA0) == 0x1234


def test_sba_autoincrement_follows_the_hardwired_size(model):
    model.on_write(SBCS, 1 << 16)                           # autoincrement, no read-on-addr
    model.on_write(SBADDRESS0, 0x8000_0000)
    model.on_write(SBDATA0, 0xA)
    model.on_write(SBDATA0, 0xB)                            # lands 8 bytes on: sbaccess is 3
    model.on_write(SBCS, 1 << 20)
    model.on_write(SBADDRESS0, 0x8000_0008)
    assert model.predict(SBDATA0) == 0xB


def _trace(tmp_path, tamper=False):
    """A trace written the way dm_ref_model.sv writes one, predictions taken
    from a second model instance so the replay has something to agree with."""
    ref = DMPredictor()
    ref.set_config(load_dut_config("cva6").declared_config())
    lines = [f"C {CVA6_CFG}"]

    def w(addr, value):
        lines.append(f"W {addr:02x} {value:08x}")
        ref.on_write(addr, value)

    def rec(kind, addr, rtl):
        pred = ref.predict(addr) ^ (1 if tamper and addr == SBCS else 0)
        lines.append(f"{kind} {addr:02x} {rtl:08x} {int(ref.has_model(addr))} "
                     f"{ref.predict_mask(addr):08x} {pred:08x}")

    def r(addr, rtl):
        rec("R", addr, rtl)
        if addr == DMSTATUS:
            lines.append(f"S {rtl:08x}")
            ref.sync_observed_hart_signals(rtl)
            rec("V", addr, rtl)

    w(DMCONTROL, ACTIVE)
    r(DMSTATUS, 0x0040_0c83)
    w(SBCS, 1 << 20)
    r(SBCS, 0x2016_0808)
    r(0x2F, 0)                                             # unclaimed by both
    path = tmp_path / "t.model_trace"
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.smoke
def test_replay_agrees_with_a_consistent_trace(tmp_path):
    res = crosscheck.replay(_trace(tmp_path))
    assert res.divergences == []
    assert res.tallies[(SBCS, "R")].agree == 1 and res.tallies[(0x2F, "R")].claimed == 0
    assert res.tallies[(DMSTATUS, "V")].agree == 1


def test_replay_reports_a_divergent_prediction(tmp_path):
    res = crosscheck.replay(_trace(tmp_path, tamper=True))
    assert [(a, why.split()[0]) for _, a, why in res.divergences] == [((SBCS, "R"), "prediction")]
