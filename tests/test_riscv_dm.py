"""
tests/test_riscv_dm.py — Unit tests for the debug library.
Uses a MockTransport so no simulator or hardware is needed.

Run with:
    python3 -m pytest tests/ -v
or:
    make python_test
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from debug_lib.transport import DebugTransport, TransportError
from debug_lib.riscv_dm  import RISCVDebug, DebugError, DMI
from debug_lib.session   import DebugSession, StepResult


# ── Mock transport ────────────────────────────────────────────────────────────

class MockTransport(DebugTransport):
    """
    In-memory transport that simulates a minimal RISC-V Debug Module.
    Replicates the debug_module_stub RTL logic in Python.
    """

    def __init__(self):
        super().__init__(name="MockTransport")
        self.regfile = {}
        self.halted  = False
        self.log     = []   # list of (op, addr, data)

    def connect(self):    self._connected = True
    def disconnect(self): self._connected = False

    def write(self, addr: int, data: int) -> None:
        self.log.append(("write", addr, data))
        self.regfile[addr] = data
        if addr == DMI.DMCONTROL:
            if data & (1 << 31):   # haltreq
                self.halted = True
            if data & (1 << 30):   # resumereq
                self.halted = False

    def read(self, addr: int) -> int:
        self.log.append(("read", addr, None))
        if addr == DMI.DMSTATUS:
            v = 0x0000_0402   # version=2, authenticated
            if self.halted:
                v |= (1 << 9) | (1 << 10)    # allhalted, anyhalted
            else:
                v |= (1 << 11) | (1 << 12)   # allrunning, anyrunning
            return v
        if addr == DMI.ABSTRACTCS:
            return 0x0000_1000   # busy=0, cmderr=0, progsize=1
        if addr == DMI.DATA0:
            return self.regfile.get(DMI.DATA0, 0xDEAD_BEEF)
        if addr == DMI.SBCS:
            return 0x0020_0000   # sbbusy=0, sbaccess=32-bit supported
        if addr == DMI.SBDATA0:
            return self.regfile.get(DMI.SBDATA0, 0xCAFE_0000)
        return self.regfile.get(addr, 0)

    def ops(self):
        return [(op, addr) for op, addr, _ in self.log]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_dm():
    t  = MockTransport()
    t.connect()
    dm = RISCVDebug(t)
    return dm, t


# ── Tests: activation ─────────────────────────────────────────────────────────

def test_activate_writes_dmcontrol(mock_dm):
    dm, t = mock_dm
    dm.activate()
    assert any(op == "write" and addr == DMI.DMCONTROL for op, addr, _ in t.log)

def test_activate_reads_dmstatus(mock_dm):
    dm, t = mock_dm
    dm.activate()
    assert ("read", DMI.DMSTATUS, None) in t.log


# ── Tests: halt ───────────────────────────────────────────────────────────────

def test_halt_sets_halted(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    assert t.halted is True

def test_halt_clears_haltreq(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    # Final dmcontrol write should have haltreq=0
    writes = [(addr, data) for op, addr, data in t.log if op == "write" and addr == DMI.DMCONTROL]
    last_dmcontrol = writes[-1][1]
    assert not (last_dmcontrol >> 31 & 1), "haltreq should be cleared after halt"

def test_is_halted_true_after_halt(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    assert dm.is_halted() is True

def test_is_running_false_after_halt(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    assert dm.is_running() is False


# ── Tests: resume ─────────────────────────────────────────────────────────────

def test_resume_clears_halted(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    dm.resume()
    assert t.halted is False

def test_is_running_after_resume(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    dm.resume()
    assert dm.is_running() is True


# ── Tests: GPR / mem access ───────────────────────────────────────────────────

def test_read_gpr_triggers_command_write(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    _ = dm.read_gpr(0x1001)   # ra (x1)
    assert any(op == "write" and addr == DMI.COMMAND for op, addr, _ in t.log)

def test_read_mem32_uses_sbaddress(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    _ = dm.read_mem32(0x8000_0000)
    writes = [addr for op, addr, _ in t.log if op == "write"]
    assert DMI.SBADDRESS0 in writes

def test_write_mem32_writes_sbdata(mock_dm):
    dm, t = mock_dm
    dm.activate()
    dm.halt()
    dm.write_mem32(0x8000_0004, 0xABCD_1234)
    assert t.regfile.get(DMI.SBDATA0) == 0xABCD_1234


# ── Tests: session (batch) ────────────────────────────────────────────────────

def test_batch_session_all_pass(mock_dm):
    dm, _ = mock_dm
    session = DebugSession(mode="batch")
    session.add_step("activate", lambda: dm.activate())
    session.add_step("halt",     lambda: dm.halt())
    session.add_step("check",    lambda: StepResult(ok=dm.is_halted(), msg="halted check"))
    results = session.run()
    assert session.all_passed

def test_batch_session_fails_on_error(mock_dm):
    dm, _ = mock_dm
    session = DebugSession(mode="batch", stop_on_error=True)
    session.add_step("good",  lambda: None)
    session.add_step("bad",   lambda: (_ for _ in ()).throw(RuntimeError("injected failure")))
    session.add_step("never", lambda: None)
    results = session.run()
    assert not session.all_passed
    assert len(results) == 2   # third step never runs

def test_step_exception_captured(mock_dm):
    dm, _ = mock_dm
    session = DebugSession(mode="batch", stop_on_error=False)
    session.add_step("raises", lambda: 1/0)
    results = session.run()
    assert results[0].ok is False
    assert "division by zero" in results[0].msg


# ── Tests: transport swap (OpenOCD mock) ──────────────────────────────────────

def test_transport_swap_same_sequence():
    """
    The halt sequence is unaware of the transport.
    Swapping MockTransport for any other transport changes nothing.
    """
    from debug_lib.riscv_dm import RISCVDebug
    from sequences.halt_sequence import build_halt_sequence

    t  = MockTransport()
    t.connect()
    dm = RISCVDebug(t)

    session = build_halt_sequence(dm, mode="batch", resume_after=False)
    session.run()

    assert session.all_passed


# ── Tests: DMI register constants ────────────────────────────────────────────

def test_dmi_constants():
    assert DMI.DMCONTROL  == 0x10
    assert DMI.DMSTATUS   == 0x11
    assert DMI.COMMAND    == 0x17
    assert DMI.DATA0      == 0x04
    assert DMI.SBADDRESS0 == 0x39
    assert DMI.SBDATA0    == 0x3C
