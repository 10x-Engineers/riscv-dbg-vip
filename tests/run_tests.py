"""
tests/run_tests.py — Run all tests without pytest (stdlib only).
Usage: python3 tests/run_tests.py
"""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from debug_lib.transport import TransportError
from debug_lib.riscv_dm  import RISCVDebug, DebugError, DMI
from debug_lib.session   import DebugSession, StepResult

# ── MockTransport (copy from test file, no external deps) ─────────────────────
from debug_lib.transport import DebugTransport

class MockTransport(DebugTransport):
    def __init__(self):
        super().__init__(name="MockTransport")
        self.regfile = {}
        self.halted  = False
        self.log     = []

    def connect(self):    self._connected = True
    def disconnect(self): self._connected = False

    def write(self, addr, data):
        self.log.append(("write", addr, data))
        self.regfile[addr] = data
        if addr == DMI.DMCONTROL:
            if data & (1 << 31): self.halted = True
            if data & (1 << 30): self.halted = False

    def read(self, addr):
        self.log.append(("read", addr, None))
        if addr == DMI.DMSTATUS:
            v = 0x0000_0402
            if self.halted: v |= (1 << 9) | (1 << 10)
            else:           v |= (1 << 11) | (1 << 12)
            return v
        if addr == DMI.ABSTRACTCS: return 0x0400_0000   # progsize=4, busy=0, cmderr=0
        if addr == DMI.DATA0:      return self.regfile.get(DMI.DATA0, 0xDEAD_BEEF)
        if addr == DMI.SBCS:       return 0x0004_0000   # sbaccess32 ok, sbbusy=0
        if addr == DMI.SBDATA0:    return self.regfile.get(DMI.SBDATA0, 0xCAFE_0000)
        return self.regfile.get(addr, 0)

def fresh():
    t = MockTransport(); t.connect()
    return RISCVDebug(t), t

# ── Test cases ────────────────────────────────────────────────────────────────
PASS = []; FAIL = []

def test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✓  {name}")
    except Exception as e:
        FAIL.append(name)
        print(f"  ✗  {name}")
        traceback.print_exc()

def assert_eq(a, b, msg=""):
    if a != b: raise AssertionError(f"{msg}: {a!r} != {b!r}")
def assert_true(v, msg=""): 
    if not v: raise AssertionError(msg or f"Expected True, got {v!r}")
def assert_false(v, msg=""):
    if v: raise AssertionError(msg or f"Expected False, got {v!r}")
def assert_in(item, container, msg=""):
    if item not in container: raise AssertionError(msg or f"{item!r} not in container")

print("\n" + "═"*55)
print("  debug_lib unit tests")
print("═"*55)

# DMI constants
def t_constants():
    assert_eq(DMI.DMCONTROL,  0x10)
    assert_eq(DMI.DMSTATUS,   0x11)
    assert_eq(DMI.COMMAND,    0x17)
    assert_eq(DMI.DATA0,      0x04)
    assert_eq(DMI.SBADDRESS0, 0x39)
    assert_eq(DMI.SBDATA0,    0x3C)
test("DMI register constants", t_constants)

# Activate
def t_activate_writes_dmcontrol():
    dm, t = fresh(); dm.activate()
    assert_true(any(op=="write" and addr==DMI.DMCONTROL for op,addr,_ in t.log))
test("activate() writes dmcontrol", t_activate_writes_dmcontrol)

def t_activate_reads_dmstatus():
    dm, t = fresh(); dm.activate()
    assert_in(("read", DMI.DMSTATUS, None), t.log)
test("activate() reads dmstatus", t_activate_reads_dmstatus)

# Halt
def t_halt_sets_halted():
    dm, t = fresh(); dm.activate(); dm.halt()
    assert_true(t.halted)
test("halt() sets halted flag", t_halt_sets_halted)

def t_halt_clears_haltreq():
    dm, t = fresh(); dm.activate(); dm.halt()
    writes = [(a, d) for op,a,d in t.log if op=="write" and a==DMI.DMCONTROL]
    last = writes[-1][1]
    assert_false(last >> 31 & 1, "haltreq should be cleared")
test("halt() clears haltreq in final write", t_halt_clears_haltreq)

def t_is_halted_after_halt():
    dm, t = fresh(); dm.activate(); dm.halt()
    assert_true(dm.is_halted())
test("is_halted() True after halt()", t_is_halted_after_halt)

def t_is_running_false_after_halt():
    dm, t = fresh(); dm.activate(); dm.halt()
    assert_false(dm.is_running())
test("is_running() False after halt()", t_is_running_false_after_halt)

# Resume
def t_resume_clears_halted():
    dm, t = fresh(); dm.activate(); dm.halt(); dm.resume()
    assert_false(t.halted)
test("resume() clears halted flag", t_resume_clears_halted)

def t_is_running_after_resume():
    dm, t = fresh(); dm.activate(); dm.halt(); dm.resume()
    assert_true(dm.is_running())
test("is_running() True after resume()", t_is_running_after_resume)

# GPR / memory
def t_read_gpr_writes_command():
    dm, t = fresh(); dm.activate(); dm.halt(); dm.read_gpr(0x1001)
    assert_true(any(op=="write" and addr==DMI.COMMAND for op,addr,_ in t.log))
test("read_gpr() writes COMMAND register", t_read_gpr_writes_command)

def t_read_mem32_writes_sbaddress():
    dm, t = fresh(); dm.activate(); dm.halt(); dm.read_mem32(0x8000_0000)
    writes = [a for op,a,_ in t.log if op=="write"]
    assert_in(DMI.SBADDRESS0, writes)
test("read_mem32() writes SBADDRESS0", t_read_mem32_writes_sbaddress)

def t_write_mem32_stores_data():
    dm, t = fresh(); dm.activate(); dm.halt(); dm.write_mem32(0x8000_0004, 0xABCD_1234)
    assert_eq(t.regfile.get(DMI.SBDATA0), 0xABCD_1234)
test("write_mem32() stores data in SBDATA0", t_write_mem32_stores_data)

# Session
def t_batch_session_all_pass():
    dm, _ = fresh()
    s = DebugSession(mode="batch")
    s.add_step("activate", lambda: dm.activate())
    s.add_step("halt",     lambda: dm.halt())
    s.add_step("check",    lambda: StepResult(ok=dm.is_halted(), msg="ok"))
    s.run()
    assert_true(s.all_passed)
test("batch session: all steps pass", t_batch_session_all_pass)

def t_session_stops_on_error():
    dm, _ = fresh()
    s = DebugSession(mode="batch", stop_on_error=True)
    s.add_step("ok",    lambda: None)
    s.add_step("fail",  lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    s.add_step("never", lambda: None)
    results = s.run()
    assert_eq(len(results), 2, "third step should not run")
    assert_false(s.all_passed)
test("batch session: stops on error", t_session_stops_on_error)

def t_exception_captured_as_fail():
    s = DebugSession(mode="batch", stop_on_error=False)
    s.add_step("divide", lambda: 1/0)
    results = s.run()
    assert_false(results[0].ok)
    assert_true("division by zero" in results[0].msg)
test("session: exception captured as failure", t_exception_captured_as_fail)

# Transport swap
def t_transport_swap():
    from sequences.halt_sequence import build_halt_sequence
    t = MockTransport(); t.connect()
    dm = RISCVDebug(t)
    s = build_halt_sequence(dm, mode="batch", resume_after=False)
    s.run()
    assert_true(s.all_passed)
test("transport swap: halt_sequence runs on MockTransport", t_transport_swap)

# ── Summary ───────────────────────────────────────────────────────────────────
print("═"*55)
print(f"  Results: {len(PASS)} passed  |  {len(FAIL)} failed")
print("═"*55 + "\n")
sys.exit(1 if FAIL else 0)
