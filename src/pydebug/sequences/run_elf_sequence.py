"""
sequences/run_elf_sequence.py — run a self-checking program to completion and
report its own verdict.

The riscv-arch-test (ACT4) programs, among them the native-debug Sdtrig suite,
check themselves and finish by writing `tohost`: 1 for pass, 3 for fail
(`cva6_sim/act/cv64a6-sdtrig/rvmodel_macros.h`), then loop forever. They need no
debugger. The testbench boots the hart straight into the ELF (`+enable_boot`),
so this scenario only has to wait: it polls `tohost` over System Bus Access,
which reads memory without disturbing the running hart, then halts the hart
and reports where it stopped.

Time is simulated time (`sim_time_s`), not wall-clock: the simulator's speed
says nothing about whether the program finished within its budget.

Traces to: NATIVE-OP1..7 via the programs themselves (see the
`act_*` entries in cva6_sim/regress/regression.yaml).
"""

import subprocess

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.sequences.hart_control import DPC, MCAUSE, MEPC, symbol_addr

TOHOST_PASS = 1
TOHOST_FAIL = 3

#: Simulated seconds to wait for a verdict. The polls themselves are what
#: advances simulated time -- one System Bus Access read is a few tens of
#: microseconds of it -- so there is no separate wait: an idle loop of DMI
#: reads costs a JTAG scan each and, on a coverage build, wall-clock minutes.
DEFAULT_BUDGET_S = 0.2


def build_run_elf_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "",
    budget_s: float = DEFAULT_BUDGET_S,
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    info: dict = {}

    def setup():
        if not elf:
            return StepResult(ok=False, msg="no elf given (params.elf)")
        info["tohost"] = symbol_addr(elf, "tohost")
        info["name"] = elf.rsplit("/", 1)[-1]
        return StepResult(ok=True, msg=f"{info['name']}: tohost=0x{info['tohost']:x}")
    session.add_step("Resolve tohost", setup)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    def wait_verdict():
        clock = dm.t.sim_time_s
        start = clock()
        polls = 0
        value = 0
        while True:
            value = dm.read_mem32(info["tohost"])
            polls += 1
            if value in (TOHOST_PASS, TOHOST_FAIL):
                break
            if clock() - start > budget_s:
                break
        elapsed = clock() - start
        info["tohost_value"] = value
        verdict = {TOHOST_PASS: "PASS", TOHOST_FAIL: "FAIL"}.get(value, "no verdict")
        return StepResult(
            ok=value == TOHOST_PASS,
            msg=f"{info['name']}: tohost={value} ({verdict}) after {elapsed * 1e3:.1f} ms "
                f"simulated, {polls} SBA polls")
    session.add_step("Wait for the program's verdict (tohost)", wait_verdict)

    def report():
        dm.halt()
        dpc = dm.read_reg64(DPC)
        mcause = dm.read_reg64(MCAUSE)
        mepc = dm.read_reg64(MEPC)
        return StepResult(
            ok=True,
            msg=f"{info['name']}: halted at dpc=0x{dpc:x}{_where(elf, dpc)}; "
                f"last trap mcause=0x{mcause:x} mepc=0x{mepc:x}{_where(elf, mepc)}")
    session.add_step("Halt and report where the program stopped", report)

    def explain_failure():
        if info.get("tohost_value") != TOHOST_FAIL:
            return StepResult(ok=True, msg="no failure record to decode")
        return StepResult(ok=True, msg=f"{info['name']}: " + _failure_record(dm, elf))
    session.add_step("Decode the program's failure record", explain_failure)

    return session


#: Offsets in ACT4's begin_failure_scratch (tests/env/rvtest_failure_code.h).
#: The failing check's return address ends up in x5 (DEFAULT_LINK_REG) on every
#: entry point. The scratch copies are not reliable: the trap entry stores it at
#: +104, which failedtest_saveregs then overwrites with x13.
_FAIL_TYPE, _FAIL_ACTUAL, _FAIL_EXPECTED = 0, 272, 280
_FAIL_RET_SLOTS = (104, 40)
_X5_REGNO = 0x1005
_FAIL_TYPES = {0: "integer", 1: "fp", 2: "fflags", 3: "trap handler"}
_SBDATA1 = 0x3D


def _read64(dm, addr: int) -> int:
    """One 64-bit SBA read: sbaccess is hardwired to 64 bits on this DM
    (RTL-002), so the upper half of the same access is in sbdata1."""
    low = dm.read_mem32(addr)
    return (dm.t.read(_SBDATA1) << 32) | low


def _read_str(dm, addr: int, limit: int = 96) -> str:
    out = bytearray()
    while len(out) < limit:
        word = _read64(dm, addr + len(out))
        for i in range(8):
            b = (word >> (8 * i)) & 0xFF
            if b == 0:
                return out.decode(errors="replace")
            out.append(b)
    return out.decode(errors="replace") + "..."


def _failure_record(dm, elf: str) -> str:
    """The program's own account of its failure: native_*.S programs keep
    {check id, actual, expected} in `native_fail`; ACT4 programs keep a
    failure scratch area (see _act_failure_record)."""
    try:
        base = symbol_addr(elf, "native_fail")
    except RuntimeError:
        return _act_failure_record(dm, elf)
    check, actual, expected = (_read64(dm, base + 8 * i) for i in range(3))
    return (f"check 0x{check:x} failed: actual=0x{actual:x} expected=0x{expected:x} "
            f"(check ids are in the program source)")


def _act_failure_record(dm, elf: str) -> str:
    """Decode ACT4's failure scratch: which check failed, and with what.

    The failing check's `jal` leaves its return address pointing at two
    pointer words -- the check's own address and a description string.
    """
    try:
        base = symbol_addr(elf, "begin_failure_scratch")
    except RuntimeError as e:
        return f"cannot decode ({e})"
    kind = _read64(dm, base + _FAIL_TYPE)
    actual = _read64(dm, base + _FAIL_ACTUAL)
    expected = _read64(dm, base + _FAIL_EXPECTED)
    lo, hi = symbol_addr(elf, "rvtest_entry_point"), symbol_addr(elf, "_end")
    candidates = [dm.read_reg64(_X5_REGNO)] + [_read64(dm, base + o) for o in _FAIL_RET_SLOTS]
    check, text = None, ""
    for ret in candidates:
        if lo <= ret < hi:
            ptr = _read64(dm, ret)
            if lo <= ptr < hi:
                check, text = ptr, _read_str(dm, _read64(dm, ret + 8))
                break
    if check is None:
        return (f"{_FAIL_TYPES.get(kind, kind)} check failed: actual=0x{actual:x} "
                f"expected=0x{expected:x} (failing check not located)")
    return (f"{_FAIL_TYPES.get(kind, kind)} check at 0x{check:x}{_where(elf, check)} "
            f"failed: actual=0x{actual:x} expected=0x{expected:x} ({text!r})")


def _where(elf: str, addr: int) -> str:
    """` (symbol+off)` for addr, or '' if it cannot be resolved."""
    try:
        out = subprocess.run(["riscv64-unknown-elf-addr2line", "-f", "-e", elf, hex(addr)],
                             capture_output=True, text=True, check=True).stdout.split()
        return f" ({out[0]})" if out and out[0] != "??" else ""
    except (OSError, subprocess.CalledProcessError):
        return ""
