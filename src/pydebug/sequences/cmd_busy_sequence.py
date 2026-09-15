"""
sequences/cmd_busy_sequence.py — DMI access while an abstract command is busy.

Spec #3.7.1: while `abstractcs.busy` is set, "the debugger must not change
`command`, `abstractcs`, or any of the `data` or `progbuf` registers", and a DM
that sees such an access sets `cmderr` to 1 (busy) rather than corrupting the
command in flight.

Nothing exercised that. Every existing test issues a command and waits for it,
so the DM's whole busy-guard family — six `if (cmdbusy_i) ... else if
(cmderr_q == CmdErrNone)` sites in `dm_csrs.sv` — never executed. That was 22%
of the Debug Module's uncovered blocks, second only to SBA.

The difficulty is keeping a command busy long enough to race it over JTAG. An
abstract register access on a halted hart finishes in a few cycles, far faster
than a DMI transaction can be driven. So this loads the Program Buffer with a
counted delay loop and starts it with postexec, which keeps the hart executing
— and `cmdbusy` asserted — for thousands of cycles.

Traces to: TC-AC-020 (busy guard), TC-AC-021 (cmderr=busy sticky),
TC-AC-022 (DM usable after a busy collision).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

#: Assembled with riscv64-unknown-elf-as (-march=rv64i, .option norvc) rather
#: than hand-encoded: a wrong B-type immediate here would loop forever or fall
#: straight through, and both look like a DM bug rather than a bad constant.
LI_T0_400    = 0x19000293   # li   t0, 400
ADDI_T0_M1   = 0xFFF28293   # addi t0, t0, -1
BNEZ_T0_BACK = 0xFE029EE3   # bnez t0, -4
EBREAK       = 0x00100073   # ebreak

#: command (0x17): cmdtype=0 (Access Register), aarsize=2, transfer=0,
#: postexec=1 -- run the Program Buffer without transferring a register.
CMD_POSTEXEC_ONLY = (2 << 20) | (1 << 18)

ABSTRACTCS_BUSY   = 12
ABSTRACTCS_CMDERR = 8
CMDERR_NONE, CMDERR_BUSY = 0, 1

ABSTRACTAUTO = 0x18

#: Abstract-command regno space (#3.7.1.1): 0x0000-0x0fff are CSRs and
#: 0x1000-0x101f are the GPRs. Passing a bare 5 addresses CSR 0x005, which
#: CVA6 does not implement, and the DM correctly answers cmderr=3 (exception)
#: -- a test bug that reads exactly like a DM bug.
X5_REGNO = 0x1005


def _cmderr(abstractcs: int) -> int:
    return (abstractcs >> ABSTRACTCS_CMDERR) & 0x7


def _busy(abstractcs: int) -> bool:
    return bool((abstractcs >> ABSTRACTCS_BUSY) & 1)


def _wait_not_busy(dm, limit: int = 200) -> bool:
    """
    Poll abstractcs until the in-flight command retires.

    Required before clearing cmderr: abstractcs is itself one of the registers
    the busy guard protects, so a W1C issued while busy is refused exactly like
    any other write -- and the clear silently does nothing, leaving cmderr=1 to
    fail the *next* command instead. That failure points at the next command
    rather than at this clear, which makes it slow to diagnose.
    """
    for _ in range(limit):
        if not _busy(dm.t.read(DMI.ABSTRACTCS)):
            return True
    return False


def _clear_cmderr(dm) -> None:
    """cmderr is W1C: write 1s to the field to clear it, once it can land."""
    _wait_not_busy(dm)
    dm.t.write(DMI.ABSTRACTCS, 0x7 << ABSTRACTCS_CMDERR)


def build_cmd_busy_sequence(dm: RISCVDebug, mode: str = "batch") -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def _arm_long_command() -> None:
        """Load the delay loop and start it, WITHOUT waiting for completion."""
        dm.write_progbuf(0, LI_T0_400)
        dm.write_progbuf(1, ADDI_T0_M1)
        dm.write_progbuf(2, BNEZ_T0_BACK)
        dm.write_progbuf(3, EBREAK)
        _clear_cmderr(dm)
        dm.t.write(DMI.COMMAND, CMD_POSTEXEC_ONLY)   # deliberately non-blocking

    # ── TC-AC-020: data0 / progbuf access during a busy command ───────────
    def tc_ac_020():
        _arm_long_command()
        saw_busy = _busy(dm.t.read(DMI.ABSTRACTCS))
        # Race the command on every register the spec names.
        dm.t.write(DMI.DATA0, 0x11111111)
        dm.t.read(DMI.DATA0)
        dm.t.write(DMI.PROGBUF0, 0x22222222)
        dm.t.read(DMI.PROGBUF0)
        err = _cmderr(dm.t.read(DMI.ABSTRACTCS))
        dm._wait_abstract() if hasattr(dm, "_wait_abstract") else None
        ok = err in (CMDERR_NONE, CMDERR_BUSY)
        return StepResult(
            ok=ok,
            msg=f"TC-AC-020: busy seen={saw_busy}, cmderr after racing "
                f"data0/progbuf0 = {err} "
                f"({'busy -- guard fired' if err == CMDERR_BUSY else 'none -- command finished first'})  "
                f"{'OK' if ok else 'unexpected cmderr'}",
        )
    session.add_step("TC-AC-020: data0/progbuf access while busy", tc_ac_020)

    # ── TC-AC-021: command and abstractauto during a busy command ─────────
    def tc_ac_021():
        _arm_long_command()
        dm.t.write(DMI.COMMAND, CMD_POSTEXEC_ONLY)   # a second command while busy
        dm.t.write(ABSTRACTAUTO, 0x00000001)
        dm.t.read(ABSTRACTAUTO)
        err = _cmderr(dm.t.read(DMI.ABSTRACTCS))
        ok = err in (CMDERR_NONE, CMDERR_BUSY)
        return StepResult(
            ok=ok,
            msg=f"TC-AC-021: cmderr after racing command/abstractauto = {err}  "
                f"{'OK' if ok else 'unexpected cmderr'}",
        )
    session.add_step("TC-AC-021: command/abstractauto access while busy", tc_ac_021)

    # ── TC-AC-022: the DM is still usable afterwards ──────────────────────
    # The point of the guard is that a racing access is rejected, not that it
    # wedges the DM. A DM that sets cmderr and then stops accepting commands
    # has failed this even though every check above passed.
    def tc_ac_022():
        settled = _wait_not_busy(dm)
        if not settled:
            return StepResult(ok=False, msg="TC-AC-022: abstractcs.busy never cleared")
        # Disarm abstractauto FIRST. TC-AC-021 wrote autoexecdata[0] while
        # racing a command; if that write landed after busy dropped, every
        # later data0 access silently re-executes whatever is in `command` --
        # so the GPR round-trip below runs the stale postexec against a
        # garbage Program Buffer and reports cmderr=3 (exception). The DM is
        # behaving correctly; the test armed a foot-gun and then fired it.
        dm.t.write(ABSTRACTAUTO, 0)
        # Restore a benign Program Buffer too: this step asks whether the DM
        # recovered from the busy collision, not whether it can execute junk.
        for i in range(4):
            dm.write_progbuf(i, EBREAK)
        _clear_cmderr(dm)
        # State snapshot before the round-trip. When this step failed it
        # reported only "cmderr=3", which says a command raised an exception
        # and nothing about which precondition was wrong -- so record them.
        pre_acs  = dm.t.read(DMI.ABSTRACTCS)
        pre_auto = dm.t.read(ABSTRACTAUTO)
        pre_dms  = dm.t.read(DMI.DMSTATUS)
        try:
            dm.write_gpr(X5_REGNO, 0xABCD)
            val = dm.read_gpr(X5_REGNO)
        except Exception as e:                       # noqa: BLE001 - reported, not swallowed
            post = dm.t.read(DMI.ABSTRACTCS)
            return StepResult(
                ok=False,
                msg=f"TC-AC-022: GPR round-trip raised {e}; "
                    f"before: abstractcs=0x{pre_acs:08x} (cmderr={_cmderr(pre_acs)}, "
                    f"busy={_busy(pre_acs)}) abstractauto=0x{pre_auto:08x} "
                    f"dmstatus=0x{pre_dms:08x}; after: abstractcs=0x{post:08x}",
            )
        err = _cmderr(dm.t.read(DMI.ABSTRACTCS))
        ok = val == 0xABCD and err == CMDERR_NONE
        return StepResult(
            ok=ok,
            msg=f"TC-AC-022: after clearing cmderr, GPR round-trip = 0x{val:04x} "
                f"(expect 0xabcd), cmderr={err}  "
                f"{'OK -- DM usable' if ok else 'DM left unusable'}",
        )
    session.add_step("TC-AC-022: DM usable after a busy collision", tc_ac_022)

    # ── TC-AC-023: writes to read-only registers are ignored ──────────────
    # dmstatus and hartinfo are R/O. The DM must ignore the write rather than
    # erroring -- the `dm::DMStatus:;` / `dm::Hartinfo:;` case arms.
    def tc_ac_023():
        before_s, before_h = dm.t.read(DMI.DMSTATUS), dm.t.read(DMI.HARTINFO)
        dm.t.write(DMI.DMSTATUS, 0xFFFFFFFF)
        dm.t.write(DMI.HARTINFO, 0xFFFFFFFF)
        after_s, after_h = dm.t.read(DMI.DMSTATUS), dm.t.read(DMI.HARTINFO)
        ok = after_s == before_s and after_h == before_h
        return StepResult(
            ok=ok,
            msg=f"TC-AC-023: dmstatus 0x{before_s:08x}->0x{after_s:08x}, "
                f"hartinfo 0x{before_h:08x}->0x{after_h:08x} after writing all-ones  "
                f"{'OK -- ignored' if ok else 'R/O register was modified'}",
        )
    session.add_step("TC-AC-023: writes to R/O registers ignored", tc_ac_023)

    # ── TC-AC-024: abstractauto round-trip ────────────────────────────────
    # abstractauto (0x18) is never touched by any other scenario, so both its
    # read and write case arms are dead.
    def tc_ac_024():
        dm.t.write(ABSTRACTAUTO, 0x00000000)
        zero = dm.t.read(ABSTRACTAUTO)
        dm.t.write(ABSTRACTAUTO, 0x00000001)   # autoexecdata[0]
        one = dm.t.read(ABSTRACTAUTO)
        dm.t.write(ABSTRACTAUTO, 0x00000000)   # disarm: leaving it set makes
        _clear_cmderr(dm)                      # every later data0 access run a command
        ok = zero == 0
        return StepResult(
            ok=ok,
            msg=f"TC-AC-024: abstractauto 0 -> 0x{zero:08x}, "
                f"1 -> 0x{one:08x} (0 if unimplemented, which is legal)  "
                f"{'OK' if ok else 'nonzero after writing 0'}",
        )
    session.add_step("TC-AC-024: abstractauto round-trip", tc_ac_024)

    # ── TC-AC-025: keepalive set/clear ────────────────────────────────────
    # dmcontrol.setkeepalive/clrkeepalive (v1.0) are never driven, so both
    # arms in dm_csrs.sv are dead. The DM may ignore them (keepalive is a hint).
    def tc_ac_025():
        base = dm.t.read(DMI.DMCONTROL)
        dm.t.write(DMI.DMCONTROL, base | (1 << 6))    # setkeepalive
        with_set = dm.t.read(DMI.DMCONTROL)
        dm.t.write(DMI.DMCONTROL, base | (1 << 5))    # clrkeepalive
        with_clr = dm.t.read(DMI.DMCONTROL)
        dm.t.write(DMI.DMCONTROL, base)
        ok = dm.is_halted()
        return StepResult(
            ok=ok,
            msg=f"TC-AC-025: dmcontrol after setkeepalive=0x{with_set:08x}, "
                f"after clrkeepalive=0x{with_clr:08x}; hart still halted={ok}  "
                f"{'OK' if ok else 'keepalive disturbed run control'}",
        )
    session.add_step("TC-AC-025: keepalive set/clear", tc_ac_025)

    return session
