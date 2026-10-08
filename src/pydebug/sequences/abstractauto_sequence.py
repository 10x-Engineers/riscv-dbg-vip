"""
sequences/abstractauto_sequence.py — abstractauto re-runs the last command.

`abstractauto` (dm_registers.xml 0x18): "When a bit in this field is 1, read
or write accesses to the corresponding `data` word cause the DM to act as if
the current value in `command` was written there again after the access to
`data` completes." `autoexecprogbuf` does the same for the Program Buffer.
It is how a debugger streams a block of memory or registers with one DMI
access per word instead of three.

cmd_busy only writes `abstractauto` and reads it back (TC-AC-024); nothing
checked that an access actually re-runs the command, or that it re-runs it
exactly once. Each step here counts: the Program Buffer adds to x5, so the
final x5 says how many times the command ran.

It also checks the one rule that stops autoexec from running away: `command`
says "If `cmderr` is non-zero, writes to this register are ignored", and an
autoexec access acts "as if" `command` were written, so it is ignored too.
cmderr is raised with an autoexec access while the hart runs (cmderr=4), which
leaves `command` itself unchanged.

Traces to: TC-AC-040 (autoexecdata on data0 read), TC-AC-041 (autoexecdata
on data0 write), TC-AC-042 (autoexecprogbuf), TC-AC-043 (no command while
cmderr is set) -- testplan AC-014-S/C.
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

# Assembled with riscv64-unknown-elf-as -march=rv64i, .option norvc.
ADDI_X5_1    = 0x00128293   # addi x5, x5, 1
ADD_X5_X6    = 0x006282B3   # add  x5, x5, x6
EBREAK       = 0x00100073   # ebreak
JAL_SELF     = 0x0000006F   # j .
NOP          = 0x00000013   # nop

ABSTRACTAUTO = 0x18
AUTOEXEC_DATA0    = 1 << 0
AUTOEXEC_PROGBUF1 = 1 << 17

X5_REGNO, X6_REGNO = 0x1005, 0x1006
DPC = 0x07B1

# command (0x17) fields (#3.7.1.1)
AARSIZE32 = 2 << 20
POSTEXEC, TRANSFER, WRITE = 1 << 18, 1 << 17, 1 << 16
CMD_READ_X5_POST  = AARSIZE32 | POSTEXEC | TRANSFER | X5_REGNO
CMD_WRITE_X6_POST = AARSIZE32 | POSTEXEC | TRANSFER | WRITE | X6_REGNO
CMD_POSTEXEC_ONLY = AARSIZE32 | POSTEXEC

ABSTRACTCS_BUSY, ABSTRACTCS_CMDERR = 12, 8
CMDERR_NONE, CMDERR_HALTRESUME = 0, 4

#: A `j .` the hart can run while TC-AC-043 provokes cmderr=4: it touches no
#: register, so x5 still says how many commands ran. DRAM, clear of
#: halt_probe.elf and of the RAM cmd_outcome (0x80180000) and dm_corners use.
SPIN_ADDR = 0x801A0000

READS, WRITES = 5, (1, 2, 3, 4)


def _cmderr(acs: int) -> int:
    return (acs >> ABSTRACTCS_CMDERR) & 0x7


def build_abstractauto_sequence(dm: RISCVDebug, mode: str = "batch") -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    saved = {}

    def wait_not_busy(limit: int = 400) -> int:
        """Poll abstractcs (never data/progbuf: those would re-trigger)."""
        for _ in range(limit):
            acs = dm.t.read(DMI.ABSTRACTCS)
            if not (acs >> ABSTRACTCS_BUSY) & 1:
                return acs
        return acs

    def clear_cmderr() -> None:
        wait_not_busy()
        dm.t.write(DMI.ABSTRACTCS, 0x7 << ABSTRACTCS_CMDERR)

    def disarm() -> None:
        dm.t.write(ABSTRACTAUTO, 0)
        clear_cmderr()

    def load_progbuf(*words) -> None:
        for i, w in enumerate(words):
            dm.write_progbuf(i, w)

    def issue(cmd: int) -> int:
        """Write `command` from a clean cmderr and return the cmderr it ends with."""
        clear_cmderr()
        dm.t.write(DMI.COMMAND, cmd)
        return _cmderr(wait_not_busy())

    # ── Setup ─────────────────────────────────────────────────────────────
    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        saved["x5"] = dm.read_reg64(X5_REGNO)
        saved["x6"] = dm.read_reg64(X6_REGNO)
        saved["dpc"] = dm.read_reg64(DPC)
        dm.t.write(ABSTRACTAUTO, AUTOEXEC_DATA0 | AUTOEXEC_PROGBUF1)
        auto = dm.t.read(ABSTRACTAUTO)
        disarm()
        saved["auto"] = auto
        return StepResult(
            ok=True,
            msg=f"abstractauto takes 0x{auto:08x} for autoexecdata[0]+autoexecprogbuf[1] "
                f"(WARL; an unimplemented bit reads 0 and its step reports N/A)")
    session.add_step("Save x5/x6/dpc, probe which autoexec bits exist", setup)

    # ── TC-AC-040: a data0 READ re-runs the command ───────────────────────
    # command = read x5 into data0, then postexec `addi x5,x5,1`. Each read of
    # data0 returns the value the previous run transferred and starts the next
    # run, so the reads see x5 counting up one per access.
    def tc_ac_040():
        if not saved["auto"] & AUTOEXEC_DATA0:
            return StepResult(ok=True, msg="TC-AC-040: N/A -- autoexecdata[0] not implemented")
        load_progbuf(ADDI_X5_1, EBREAK)
        clear_cmderr()
        dm.write_gpr(X5_REGNO, 100)
        first = issue(CMD_READ_X5_POST)              # data0=100, x5=101
        dm.t.write(ABSTRACTAUTO, AUTOEXEC_DATA0)
        got, errs = [], []
        for _ in range(READS):
            got.append(dm.t.read(DMI.DATA0))
            errs.append(_cmderr(wait_not_busy()))
        dm.t.write(ABSTRACTAUTO, 0)
        idle = dm.t.read(DMI.DATA0)                  # disarmed: no further run
        clear_cmderr()
        x5 = dm.read_gpr(X5_REGNO)
        want = list(range(100, 100 + READS))
        # The explicit command and each of the READS ran once: x5 = 100 + 1 + READS.
        ok = (first == CMDERR_NONE and got == want and not any(errs)
              and idle == 100 + READS and x5 == 101 + READS)
        return StepResult(
            ok=ok,
            msg=f"TC-AC-040: data0 reads {got} (expect {want}), cmderr per run {errs}; "
                f"after disarm data0={idle} (expect {100 + READS}), x5={x5} "
                f"(expect {101 + READS})  " + ("OK" if ok else "command not re-run once per read"))
    session.add_step("TC-AC-040: autoexecdata re-runs the command on a data0 read", tc_ac_040)

    # ── TC-AC-041: a data0 WRITE re-runs the command ──────────────────────
    # command = write data0 into x6, then postexec `add x5,x5,x6`: x5 sums the
    # words streamed in through data0, exactly as a block write would.
    def tc_ac_041():
        if not saved["auto"] & AUTOEXEC_DATA0:
            return StepResult(ok=True, msg="TC-AC-041: N/A -- autoexecdata[0] not implemented")
        load_progbuf(ADD_X5_X6, EBREAK)
        clear_cmderr()
        dm.write_gpr(X5_REGNO, 0)
        dm.t.write(DMI.DATA0, 0)
        first = issue(CMD_WRITE_X6_POST)             # x6=0, x5=0
        dm.t.write(ABSTRACTAUTO, AUTOEXEC_DATA0)
        errs = []
        for v in WRITES:
            dm.t.write(DMI.DATA0, v)
            errs.append(_cmderr(wait_not_busy()))
        disarm()
        x5 = dm.read_gpr(X5_REGNO)
        ok = first == CMDERR_NONE and not any(errs) and x5 == sum(WRITES)
        return StepResult(
            ok=ok,
            msg=f"TC-AC-041: wrote data0 = {list(WRITES)}, cmderr per run {errs}; "
                f"x5={x5} (expect their sum, {sum(WRITES)})  "
                + ("OK" if ok else "command not re-run once per write"))
    session.add_step("TC-AC-041: autoexecdata re-runs the command on a data0 write", tc_ac_041)

    # ── TC-AC-042: a progbuf access re-runs the command ───────────────────
    # command = postexec only, buffer = `addi x5,x5,1; ebreak`. Writing
    # progbuf1 (rewriting the same ebreak) and reading it each start one run.
    def tc_ac_042():
        if not saved["auto"] & AUTOEXEC_PROGBUF1:
            return StepResult(ok=True, msg="TC-AC-042: N/A -- autoexecprogbuf[1] not implemented")
        load_progbuf(ADDI_X5_1, EBREAK)
        clear_cmderr()
        dm.write_gpr(X5_REGNO, 0)
        first = issue(CMD_POSTEXEC_ONLY)             # x5=1
        dm.t.write(ABSTRACTAUTO, AUTOEXEC_PROGBUF1)
        errs = []
        for access in ("write", "write", "write", "read", "read"):
            if access == "write":
                dm.t.write(DMI.PROGBUF0 + 1, EBREAK)
            else:
                dm.t.read(DMI.PROGBUF0 + 1)
            errs.append(_cmderr(wait_not_busy()))
        disarm()
        x5 = dm.read_gpr(X5_REGNO)
        ok = first == CMDERR_NONE and not any(errs) and x5 == 6
        return StepResult(
            ok=ok,
            msg=f"TC-AC-042: 3 writes + 2 reads of progbuf1, cmderr per run {errs}; "
                f"x5={x5} (expect 6: the explicit command plus one run per access)  "
                + ("OK" if ok else "command not re-run once per access"))
    session.add_step("TC-AC-042: autoexecprogbuf re-runs the command on a progbuf access", tc_ac_042)

    # ── TC-AC-043: nothing runs while cmderr is set ───────────────────────
    # The TC-AC-041 accumulator again, so x5 counts runs. cmderr is raised
    # without touching `command`: with the hart running a `j .`, a data0 write
    # autoexecs against a running hart and fails with cmderr=4. Halted again,
    # with cmderr still 4, one access that would start the command must be
    # ignored. The two kinds -- an autoexec data0 write, and a write to
    # `command` itself -- get an episode each, waited out separately: written
    # back to back, the second meets the first still busy and is refused for
    # that reason instead, which hides whether it would have run.
    def raise_cmderr_running() -> int:
        """Arm the accumulator with x5=0, provoke cmderr=4, halt. Returns it."""
        clear_cmderr()
        # Every helper here issues its own command, which replaces the one
        # autoexec re-runs -- so all of them come before the accumulator.
        dm.write_reg64(DPC, SPIN_ADDR)
        dm.write_gpr(X5_REGNO, 0)
        dm.t.write(DMI.DATA0, 0)
        issue(CMD_WRITE_X6_POST)                     # x5 stays 0
        dm.t.write(ABSTRACTAUTO, AUTOEXEC_DATA0)
        dm.resume()
        dm.t.write(DMI.DATA0, 5)                     # autoexec on a running hart
        err = _cmderr(wait_not_busy())
        dm.halt()
        return err

    def runs_since(access) -> tuple:
        """Raise cmderr, make `access`, return (cmderr raised, cmderr after, x5)."""
        raised = raise_cmderr_running()
        access()
        held = _cmderr(wait_not_busy())
        disarm()
        return raised, held, dm.read_gpr(X5_REGNO)

    def tc_ac_043():
        if not saved["auto"] & AUTOEXEC_DATA0:
            return StepResult(ok=True, msg="TC-AC-043: N/A -- autoexecdata[0] not implemented")
        # The spin over SBA, 64-bit: `j .` then a nop to fill the doubleword.
        dm.t.write(DMI.SBCS, 3 << 17)
        dm.t.write(DMI.SBADDRESS0, SPIN_ADDR)
        dm.t.write(0x3D, NOP)                        # sbdata1
        dm.t.write(DMI.SBDATA0, JAL_SELF)            # starts the write
        dm._wait_sbus()
        load_progbuf(ADD_X5_X6, EBREAK)

        def autoexec_write():
            dm.t.write(DMI.DATA0, 7)

        def command_write():
            # abstractauto off first, so nothing but `command` can start a run.
            dm.t.write(ABSTRACTAUTO, 0)
            dm.t.write(DMI.COMMAND, CMD_WRITE_X6_POST)

        rows, ok = [], True
        for label, access in (("autoexec data0 write", autoexec_write),
                              ("command write", command_write)):
            raised, held, x5 = runs_since(access)
            good = raised == CMDERR_HALTRESUME and held == CMDERR_HALTRESUME and x5 == 0
            ok &= good
            rows.append(f"{label}: cmderr {raised}->{held} (expect {CMDERR_HALTRESUME}), "
                        f"x5={x5} (expect 0{'' if good else '; it ran'})")
        return StepResult(
            ok=ok,
            msg="TC-AC-043: with cmderr=4 raised by an autoexec on a running hart -- "
                + "; ".join(rows)
                + ("  OK" if ok else "  a command ran while cmderr was set"))
    session.add_step("TC-AC-043: no command runs while cmderr is set", tc_ac_043)

    # ── Restore ───────────────────────────────────────────────────────────
    def restore():
        disarm()
        dm.write_reg64(X5_REGNO, saved["x5"])
        dm.write_reg64(X6_REGNO, saved["x6"])
        dm.write_reg64(DPC, saved["dpc"])
        return StepResult(ok=dm.is_halted(), msg="abstractauto disarmed; x5, x6, dpc restored")
    session.add_step("Restore", restore)

    return session
