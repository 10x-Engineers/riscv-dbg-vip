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
    r(0x2F, 0)                                             # progbuf15: unimplemented, reads 0
    path = tmp_path / "t.model_trace"
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.smoke
def test_replay_agrees_with_a_consistent_trace(tmp_path):
    res = crosscheck.replay(_trace(tmp_path))
    assert res.divergences == []
    assert res.tallies[(SBCS, "R")].agree == 1 and res.tallies[(0x2F, "R")].agree == 1
    assert res.tallies[(DMSTATUS, "V")].agree == 1


def test_replay_reports_a_divergent_prediction(tmp_path):
    res = crosscheck.replay(_trace(tmp_path, tamper=True))
    assert [(a, why.split()[0]) for _, a, why in res.divergences] == [((SBCS, "R"), "prediction")]


# ── Every DMI register has a prediction ───────────────────────────────────────

DATA1, PROGBUF0, ABSTRACTAUTO, HALTSUM1, HALTSUM2 = 0x05, 0x20, 0x18, 0x13, 0x34
SBADDRESS1, SBDATA1 = 0x3A, 0x3D
AARSIZE64, TRANSFER, WRITE = 3 << 20, 1 << 17, 1 << 16


def test_unimplemented_registers_are_claimed_and_read_zero(model):
    """"Registers that are unimplemented or not mentioned in the table return 0
    when read": data2 (datacount=2), progbuf8 (progbufsize=8), progbuf0 (not
    readable on CVA6), confstrptr0, custom, and a hole in the map."""
    for addr in (0x06, 0x28, PROGBUF0, 0x19, 0x1F, 0x7F):
        assert model.has_model(addr), hex(addr)
        assert model.predict(addr) == 0, hex(addr)


def test_haltsum1_summarises_blocks_of_32_harts():
    p = DMPredictor(num_harts=70)
    p.set_config(load_dut_config("cva6").declared_config(num_harts=70))
    p.on_write(DMCONTROL, ACTIVE)
    p.harts[33].halted = True     # block 1
    p.harts[69].halted = True     # block 2
    assert p.predict(HALTSUM1) == 0b110
    assert p.predict(HALTSUM2) == 0b1       # all 70 harts are in group 0


def test_64bit_register_access_round_trips_through_data1(model):
    """aarsize=3: a write takes data0/data1; a read of the same register
    returns both words."""
    model.on_write(DATA0, 0x1111_1111)
    model.on_write(DATA1, 0x2222_2222)
    model.on_write(COMMAND, AARSIZE64 | TRANSFER | WRITE | 0x1008)
    model.on_write(DATA0, 0)
    model.on_write(DATA1, 0)
    model.on_write(COMMAND, AARSIZE64 | TRANSFER | 0x1008)
    assert (model.predict(DATA0), model.predict(DATA1)) == (0x1111_1111, 0x2222_2222)


def test_autoexec_replays_the_last_command_on_a_data_access(model):
    """abstractauto.autoexecdata[0]: writing data0 re-runs the last command --
    here a register write, so the new value lands in the shadow."""
    model.on_write(DATA0, 5)
    model.on_write(COMMAND, TRANSFER | WRITE | 0x1008)
    model.on_write(ABSTRACTAUTO, 1)
    model.on_write(DATA0, 7)                             # replays the write
    model.on_write(ABSTRACTAUTO, 0)
    model.on_write(COMMAND, TRANSFER | 0x1008)
    assert model.predict(DATA0) == 7


def test_sba_autoincrement_carries_into_sbaddress1(model):
    """sbasize=64: a 64-bit access at 0xFFFFFFF8 increments into sbaddress1."""
    model.on_write(SBCS, 1 << 16)                        # sbautoincrement
    model.on_write(SBADDRESS1, 0)
    model.on_write(SBADDRESS0, 0xFFFF_FFF8)
    model.on_write(SBDATA0, 0)
    assert (model.predict(SBADDRESS0), model.predict(SBADDRESS1)) == (0, 1)


def test_replay_applies_read_side_effects(tmp_path):
    """An "A" record (observe_read) must reach the Python model, or a replayed
    autoexec on a data read would leave the two models apart."""
    lines = [f"C {CVA6_CFG}", f"W {DMCONTROL:02x} {ACTIVE:08x}",
             f"W {DATA0:02x} 00000009", f"W {COMMAND:02x} {TRANSFER | WRITE | 0x1008:08x}",
             f"W {ABSTRACTAUTO:02x} 00000001", f"A {DATA0:02x}"]
    path = tmp_path / "a.model_trace"
    path.write_text("\n".join(lines) + "\n")
    res = crosscheck.replay(path)
    assert res.divergences == [] and res.inputs == 5
