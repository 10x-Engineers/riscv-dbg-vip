"""
sequences/cmderr_sequence.py — provoke every abstract-command error class.

`abstractcs.cmderr` has a distinct encoding per failure, and a debugger reacts
differently to each: busy means retry, not-supported means stop asking,
halt/resume means halt first, exception means the hart faulted. A suite that
only ever runs commands that succeed leaves all of that untested, and
`cp_cmderr` sitting at one bin of six is what that looks like from the coverage
side.

Each case below drives one error and then checks the DM is still usable, which
is the property that actually matters -- an error that wedges the DM is worse
than the error.

`cmderr` is sticky and W1C, so every case clears it before the next. Forgetting
that is a real debugger bug: the next failure gets misattributed to whatever
went wrong first.

Traces to: AC-005, AC-006, AC-007, AC-008, AC-009, AC-013, AC-018, AC-019,
           AC-020, AC-022-V, RAP-042

Usage:
    make soc_test_cov CFG_FILE=configs/cmderr_uvm.json
"""

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI, allhalted, anyhalted

# abstractcs field positions (spec: debug_module.html#abstractcs)
ABS_CMDERR_LSB = 8
ABS_CMDERR_MASK = 0x7 << ABS_CMDERR_LSB
ABS_BUSY = 1 << 12

CMDERR_NONE, CMDERR_BUSY, CMDERR_NOT_SUPPORTED = 0, 1, 2
CMDERR_EXCEPTION, CMDERR_HALT_RESUME, CMDERR_BUS, CMDERR_OTHER = 3, 4, 5, 7

CMDERR_NAME = {
    0: "none", 1: "busy", 2: "not supported", 3: "exception",
    4: "halt/resume", 5: "bus", 7: "other",
}

# command field positions (Access Register, cmdtype=0)
CMD_REGNO_LSB = 0
CMD_WRITE = 1 << 16
CMD_TRANSFER = 1 << 17
CMD_POSTEXEC = 1 << 18
CMD_AARSIZE_LSB = 20
CMD_CMDTYPE_LSB = 24

REGNO_GPR_S0 = 0x1008
REGNO_CSR_DCSR = 0x07B0
REGNO_UNIMPLEMENTED = 0x0FFF   # a CSR address nothing implements


def _access_register(regno: int, write: bool = False, aarsize: int = 3,
                     postexec: bool = False, cmdtype: int = 0) -> int:
    """Build a command word. Kept explicit so each test reads as what it sends."""
    w = (cmdtype << CMD_CMDTYPE_LSB) | (aarsize << CMD_AARSIZE_LSB) | (regno & 0xFFFF)
    w |= CMD_TRANSFER
    if write:
        w |= CMD_WRITE
    if postexec:
        w |= CMD_POSTEXEC
    return w


def build_cmderr_sequence(dm: RISCVDebug, mode: str = "batch", **_) -> DebugSession:
    """
    Drive one abstract command per error class and confirm the DM recovers.

    Traces to: AC-022-V (cmdtype x cmderr)
    """
    # Not stop_on_error: each case is independent, and an RTL defect in one
    # error path should not hide whether the other five are implemented.
    session = DebugSession(mode=mode, stop_on_error=False)
    seen = {}

    def read_cmderr() -> int:
        return (dm.t.read(DMI.ABSTRACTCS) & ABS_CMDERR_MASK) >> ABS_CMDERR_LSB

    def clear_cmderr() -> None:
        """cmderr is W1C: write 1s to the field, not 0s."""
        dm.t.write(DMI.ABSTRACTCS, ABS_CMDERR_MASK)

    def wait_not_busy(timeout: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not (dm.t.read(DMI.ABSTRACTCS) & ABS_BUSY):
                return True
            time.sleep(0.001)
        return False

    def drive(name: str, cmd_word: int, expect: int, note: str = ""):
        """Issue one command, record the cmderr it produced, then clear it."""
        def run():
            clear_cmderr()
            dm.t.write(DMI.COMMAND, cmd_word)
            completed = wait_not_busy()
            err = read_cmderr()
            seen[name] = err
            clear_cmderr()
            ok = (err == expect)
            return StepResult(
                ok=ok,
                msg=f"command=0x{cmd_word:08x} -> cmderr={err} "
                    f"({CMDERR_NAME.get(err, '?')}), expected {expect} "
                    f"({CMDERR_NAME.get(expect, '?')})"
                    + ("" if completed else "; busy never cleared")
                    + (f". {note}" if note and not ok else ""),
            )
        return run

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── cmderr=4, halt/resume: a command issued while the hart runs ─────────
    # Driven FIRST, while the hart is still running, because every other case
    # needs it halted.
    session.add_step(
        "cmderr=4 (halt/resume): command while the hart is running",
        drive("halt_resume", _access_register(REGNO_GPR_S0), CMDERR_HALT_RESUME,
              "An abstract command requires a halted hart."))

    session.add_step("Halt hart", lambda: dm.halt())

    def confirm_halted():
        status = dm.t.read(DMI.DMSTATUS)
        return StepResult(ok=allhalted(status) and anyhalted(status),
                          msg=f"dmstatus=0x{status:08x}")
    session.add_step("Confirm hart halted", confirm_halted)

    # ── cmderr=0, the control ──────────────────────────────────────────────
    session.add_step(
        "cmderr=0 (none): a valid GPR read",
        drive("none", _access_register(REGNO_GPR_S0), CMDERR_NONE))

    # ── cmderr=2, not supported ────────────────────────────────────────────
    # aarsize=4 is 128-bit, which an RV64 DM does not implement.
    session.add_step(
        "cmderr=2 (not supported): aarsize=128-bit",
        drive("size128", _access_register(REGNO_GPR_S0, aarsize=4),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=1 is Quick Access, absent on this DUT.
    session.add_step(
        "cmderr=2 (not supported): cmdtype=1 (Quick Access)",
        drive("quick_access", _access_register(REGNO_GPR_S0, cmdtype=1),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=2 is Access Memory, also absent.
    session.add_step(
        "cmderr=2 (not supported): cmdtype=2 (Access Memory)",
        drive("access_memory", _access_register(REGNO_GPR_S0, cmdtype=2),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=3 is not a defined encoding at all.
    session.add_step(
        "reserved cmdtype=3: rejected, DM still usable",
        drive("reserved_cmdtype", _access_register(REGNO_GPR_S0, cmdtype=3),
              CMDERR_NOT_SUPPORTED,
              "An undefined cmdtype may report 2 or another non-zero code; "
              "what must not happen is silence or a hang."))

    # ── cmderr=3, exception: an unimplemented CSR ──────────────────────────
    # The hart takes an illegal-instruction trap inside the abstract command,
    # which the DM reports as exception rather than not-supported.
    session.add_step(
        "cmderr=3 (exception): read an unimplemented CSR",
        drive("bad_regno", _access_register(REGNO_UNIMPLEMENTED),
              CMDERR_EXCEPTION,
              "Spec permits 2 or 3 here; record which this DUT chooses."))

    # ── cmderr=1, busy: a second command while the first is in flight ──────
    # Racy by nature: the window is the duration of one abstract command. The
    # command used is a postexec over a program buffer, which takes longer than
    # a bare register transfer and widens the window enough to hit reliably.
    def busy_case():
        clear_cmderr()
        # A long-running command: transfer plus program-buffer execution.
        dm.t.write(DMI.PROGBUF0, 0x00100013)   # addi x0, x0, 1
        dm.t.write(DMI.PROGBUF0 + 1, 0x00100073)   # ebreak
        dm.t.write(DMI.COMMAND,
                   _access_register(REGNO_GPR_S0, postexec=True))
        # No wait: issue the second command immediately.
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0))
        wait_not_busy()
        err = read_cmderr()
        seen["busy"] = err
        clear_cmderr()
        return StepResult(
            ok=(err == CMDERR_BUSY),
            msg=f"back-to-back commands -> cmderr={err} "
                f"({CMDERR_NAME.get(err, '?')}), expected {CMDERR_BUSY} (busy). "
                f"The window is one command long, so a miss here means the DM "
                f"completed the first command before the second arrived, not "
                f"that busy is unimplemented",
        )
    session.add_step("cmderr=1 (busy): command issued while busy", busy_case)

    # ── Stickiness and recovery ────────────────────────────────────────────
    def sticky_case():
        """
        A failing command then a VALID one. cmderr must survive the valid
        command: a debugger that assumes success clears it misattributes the
        next failure to whatever went wrong first.
        """
        clear_cmderr()
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0, aarsize=4))
        wait_not_busy()
        after_fail = read_cmderr()
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0))
        wait_not_busy()
        after_ok = read_cmderr()
        return StepResult(
            ok=(after_fail != CMDERR_NONE and after_ok == after_fail),
            msg=f"cmderr={after_fail} after the failing command, {after_ok} after a "
                f"subsequent valid one -- must be unchanged (sticky, W1C only)",
        )
    session.add_step("cmderr is sticky across a successful command", sticky_case)

    def recovery_case():
        clear_cmderr()
        before = read_cmderr()
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0))
        wait_not_busy()
        after = read_cmderr()
        return StepResult(
            ok=(before == CMDERR_NONE and after == CMDERR_NONE),
            msg=f"after W1C clear: cmderr={before}; valid command then gives "
                f"cmderr={after} -- the DM is usable again",
        )
    session.add_step("cmderr clears on W1C and the DM recovers", recovery_case)

    def summary():
        got = sorted(set(seen.values()))
        names = ", ".join(f"{v}={CMDERR_NAME.get(v, '?')}" for v in got)
        return StepResult(
            ok=True,
            msg=f"cmderr encodings produced this run: {names}. "
                f"Binned by cg_abstract_cmd.cp_cmderr",
        )
    session.add_step("Record which cmderr encodings were produced", summary)

    return session
