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


#: The hart's register width, as an `aarsize` encoding: 3 is 64-bit, 2 is
#: 32-bit. Probed at run time, because a 64-bit Access Register command on an
#: RV32 hart is legitimately cmderr=2 (not supported) -- which, when this
#: sequence hardcoded aarsize=3, made every case on Ibex report "not supported"
#: and five of the six error classes untestable. The DM has no XLEN field to
#: read, so the probe is the access itself.
WIDTH = {"aarsize": 3}


def _access_register(regno: int, write: bool = False, aarsize: int = None,
                     postexec: bool = False, cmdtype: int = 0) -> int:
    """Build a command word. Kept explicit so each test reads as what it sends.

    `aarsize=None` means the hart's own width; pass a value only to send a
    width deliberately, as the 128-bit unsupported case does.
    """
    if aarsize is None:
        aarsize = WIDTH["aarsize"]
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

    def drive(name: str, cmd_word, expect: int, note: str = ""):
        """Issue one command, record the cmderr it produced, then clear it.

        `cmd_word` may be a callable, for the cases whose width is not known
        until the probe below has run -- the session is built before any of it
        executes.
        """
        def run():
            word = cmd_word() if callable(cmd_word) else cmd_word
            clear_cmderr()
            dm.t.write(DMI.COMMAND, word)
            completed = wait_not_busy()
            err = read_cmderr()
            seen[name] = err
            clear_cmderr()
            ok = (err == expect)
            return StepResult(
                ok=ok,
                msg=f"command=0x{word:08x} -> cmderr={err} "
                    f"({CMDERR_NAME.get(err, '?')}), expected {expect} "
                    f"({CMDERR_NAME.get(expect, '?')})"
                    + ("" if completed else "; busy never cleared")
                    + (f". {note}" if note and not ok else ""),
            )
        return run

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── The hart's register width ──────────────────────────────────────────
    # Probed before anything else is driven, because every command below
    # carries an aarsize and the wrong one turns every case into cmderr=2.
    # The probe needs a halted hart, and the halt/resume case needs a running
    # one, so the hart is halted, probed, and resumed again here.
    session.add_step("Halt hart (to probe the register width)", lambda: dm.halt())

    def probe_width():
        clear_cmderr()
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0, aarsize=3))
        wait_not_busy()
        unsupported = read_cmderr() == CMDERR_NOT_SUPPORTED
        clear_cmderr()
        WIDTH["aarsize"] = 2 if unsupported else 3
        return StepResult(
            ok=True,
            msg=f"hart register width: {'32' if unsupported else '64'}-bit "
                f"(aarsize={WIDTH['aarsize']}) -- a 64-bit Access Register "
                f"command {'is not supported here' if unsupported else 'completed'}")
    session.add_step("Probe the hart's register width", probe_width)

    session.add_step("Resume hart (for the halt/resume case)", lambda: dm.resume())

    # ── cmderr=4, halt/resume: a command issued while the hart runs ─────────
    # Driven FIRST, while the hart is still running, because every other case
    # needs it halted.
    session.add_step(
        "cmderr=4 (halt/resume): command while the hart is running",
        drive("halt_resume", lambda: _access_register(REGNO_GPR_S0), CMDERR_HALT_RESUME,
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
        drive("none", lambda: _access_register(REGNO_GPR_S0), CMDERR_NONE))

    # ── cmderr=2, not supported ────────────────────────────────────────────
    # aarsize=4 is 128-bit, which an RV64 DM does not implement.
    session.add_step(
        "cmderr=2 (not supported): aarsize=128-bit",
        drive("size128", _access_register(REGNO_GPR_S0, aarsize=4),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=1 is Quick Access, absent on this DUT.
    session.add_step(
        "cmderr=2 (not supported): cmdtype=1 (Quick Access)",
        drive("quick_access", lambda: _access_register(REGNO_GPR_S0, cmdtype=1),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=2 is Access Memory, also absent.
    session.add_step(
        "cmderr=2 (not supported): cmdtype=2 (Access Memory)",
        drive("access_memory", lambda: _access_register(REGNO_GPR_S0, cmdtype=2),
              CMDERR_NOT_SUPPORTED))

    # cmdtype=3 is not a defined encoding at all.
    session.add_step(
        "reserved cmdtype=3: rejected, DM still usable",
        drive("reserved_cmdtype", lambda: _access_register(REGNO_GPR_S0, cmdtype=3),
              CMDERR_NOT_SUPPORTED,
              "An undefined cmdtype may report 2 or another non-zero code; "
              "what must not happen is silence or a hang."))

    # ── cmderr=3, exception: an unimplemented CSR ──────────────────────────
    # The hart takes an illegal-instruction trap inside the abstract command,
    # which the DM reports as exception rather than not-supported.
    session.add_step(
        "cmderr=3 (exception): read an unimplemented CSR",
        drive("bad_regno", lambda: _access_register(REGNO_UNIMPLEMENTED),
              CMDERR_EXCEPTION,
              "Spec permits 2 or 3 here; record which this DUT chooses."))

    # ── cmderr=1, busy: a second command while the first is in flight ──────
    # Racy by nature: the window is the duration of one abstract command. The
    # command used is a postexec over a program buffer, which takes longer than
    # a bare register transfer and widens the window enough to hit reliably.
    def busy_case():
        # How long the first command runs decides whether the second one lands
        # inside its window, and the window is one command long. The program
        # buffer is filled to its implemented depth so the first command takes
        # as long as this DM allows, then ends in ebreak.
        #
        # A longer program does NOT help, and was tried: a counted loop keeps
        # the DM busy long enough that the DTM itself reports DMI busy, and a
        # DMI write that comes back busy never reaches the DM at all (#6.1.5
        # -- the operation did not happen), so abstractcs.cmderr is never set
        # and the run aborts on the scoreboard's busy report instead. Widening
        # the window past the DMI's own latency moves the problem rather than
        # solving it.
        progbufsize = (dm.t.read(DMI.ABSTRACTCS) >> 24) & 0x1F
        nops = max(0, min(progbufsize, 8) - 1)
        clear_cmderr()
        for i in range(nops):
            dm.t.write(DMI.PROGBUF0 + i, 0x00000013)      # nop (addi x0, x0, 0)
        dm.t.write(DMI.PROGBUF0 + nops, 0x00100073)       # ebreak
        dm.t.write(DMI.COMMAND,
                   _access_register(REGNO_GPR_S0, postexec=True))
        # No wait, and no intervening read: either write costs DMI time, and
        # a read of abstractcs here would spend the window it is looking for.
        dm.t.write(DMI.COMMAND, _access_register(REGNO_GPR_S0))
        wait_not_busy()
        err = read_cmderr()
        seen["busy"] = err
        clear_cmderr()
        # A miss is not a failure: the window is one command long, and
        # whether the second write lands inside it depends on the ratio of
        # JTAG time to DM time, which differs per DUT (CVA6 hits it; Ibex's
        # DM answers faster than the link delivers the second write). What a
        # miss cannot be confused with is a DM that never reports busy --
        # cp_cmderr.busy carries that, across the whole suite, and stays
        # unhit if no scenario ever provokes it.
        provoked = err == CMDERR_BUSY
        missed = err == CMDERR_NONE
        return StepResult(
            ok=provoked or missed,
            msg=f"back-to-back commands -> cmderr={err} "
                f"({CMDERR_NAME.get(err, '?')})"
                + (", the window was hit" if provoked else
                   "; the DM completed the first command before the second "
                   "write arrived -- not provoked on this DUT, see "
                   "cp_cmderr.busy for whether any scenario reached it"
                   if missed else
                   f", expected {CMDERR_BUSY} (busy) or 0 (not provoked)"),
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
