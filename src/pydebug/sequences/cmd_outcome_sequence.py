"""
sequences/cmd_outcome_sequence.py — abstract-command outcomes by kind, flags,
Program Buffer fill and DM state.

Every other scenario issues commands that succeed, or fail one way at a time,
so cg_cmd_outcome and cg_gated_access (fcov/covergroups.sv) had 30 bins no
test reached. This walks them on purpose:

- cmderr for each {transfer, postexec} combination: busy, not supported,
  exception, halt/resume (#3.7.1, abstractcs.cmderr);
- busy for each command kind -- Quick Access, Access Memory and a reserved
  cmdtype written while a command is in flight;
- a reserved aarsize, and a 64-bit access outside the GPR/FPR/CSR ranges;
- Program Buffer fill (one word, part, all eight) x {busy, exception,
  halt/resume};
- dmcontrol, dmstatus and sbcs accessed while a command is busy.

Order matters. cg_cmd_outcome bins the fill level as the highest progbuf slot
written since the last DM reset, and it only grows, so the one-word cases run
first, before anything writes slot 1. That is also why this is its own
scenario rather than steps in cmd_busy: there, the delay loop fills four slots
before anything else runs.

Holding a command busy with one progbuf word: the counted delay loop lives in
RAM, written there over SBA, and progbuf0 is `jr t1` with t1 pointing at it.
The loop ends in ebreak, which returns the hart to Debug Mode and completes the
command as an ebreak in the buffer would.

Each probed command starts with cmderr cleared: cmderr is sticky, so a stale
error would be binned against the next command.

A rejected command must not be modelled as having run. dm_ref_model applies a
command's transfer whatever cmderr it ends with, so a refused register WRITE
would leave a stale shadow value behind; the failing commands here therefore
transfer by READ, and data0 is rewritten after each before anything reads it.

Traces to: TC-AC-030..035, TC-PB-010..012 (testplan AC-021/022/023-V,
PB-014-V, RAP-048-V).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

# Assembled with riscv64-unknown-elf-as -march=rv64i, .option norvc.
JR_T1        = 0x00030067   # jalr x0, 0(t1)
LI_T0_400    = 0x19000293   # li   t0, 400
ADDI_T0_M1   = 0xFFF28293   # addi t0, t0, -1
BNEZ_T0_BACK = 0xFE029EE3   # bnez t0, -4
EBREAK       = 0x00100073   # ebreak
ILLEGAL      = 0x00000000   # all-zero word: illegal in every base ISA

#: Where the delay loop goes: DRAM, 8-byte aligned, inside the 2 MB the CVA6
#: testbench memory decodes and well clear of halt_probe.elf at 0x80000000 and
#: of the addresses dm_corners uses (0x80001000, 0x801FE000 after aliasing).
LOOP_ADDR = 0x80180000

SBDATA1 = 0x3D
SB_BUSY = 21

T0_REGNO, T1_REGNO, T2_REGNO, X5_REGNO = 0x1005, 0x1006, 0x1007, 0x1005

#: An abstract-command regno above the FPRs (0x1020-0x103f): the spec leaves
#: it to the implementation; TC-AC-026 uses it at 32 bits.
OTHER_REGNO = 0xC001

# command (0x17) fields (#3.7.1.1)
CMDTYPE_LSB, AARSIZE_LSB = 24, 20
POSTEXEC, TRANSFER, WRITE = 1 << 18, 1 << 17, 1 << 16
AARSIZE32, AARSIZE64 = 2 << AARSIZE_LSB, 3 << AARSIZE_LSB
AARSIZE_RESERVED = 5 << AARSIZE_LSB

CMD_POSTEXEC_ONLY     = AARSIZE32 | POSTEXEC
CMD_NEITHER           = AARSIZE32
CMD_XFER_READ_X5      = AARSIZE32 | TRANSFER | X5_REGNO
CMD_XFER_READ_X5_POST = CMD_XFER_READ_X5 | POSTEXEC

ABSTRACTCS_BUSY, ABSTRACTCS_CMDERR = 12, 8
CMDERR_NONE, CMDERR_BUSY, CMDERR_NOTSUP, CMDERR_EXC, CMDERR_HALTRESUME = 0, 1, 2, 3, 4


def _cmderr(acs: int) -> int:
    return (acs >> ABSTRACTCS_CMDERR) & 0x7


def _busy(acs: int) -> bool:
    return bool((acs >> ABSTRACTCS_BUSY) & 1)


def build_cmd_outcome_sequence(dm: RISCVDebug, mode: str = "batch") -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    saved = {}

    def wait_not_busy(limit: int = 400) -> bool:
        for _ in range(limit):
            if not _busy(dm.t.read(DMI.ABSTRACTCS)):
                return True
        return False

    def clear_cmderr() -> None:
        wait_not_busy()
        dm.t.write(DMI.ABSTRACTCS, 0x7 << ABSTRACTCS_CMDERR)

    def run(cmd: int) -> int:
        """Issue one command from a clean cmderr, wait, return its cmderr."""
        clear_cmderr()
        dm.t.write(DMI.COMMAND, cmd)
        wait_not_busy()
        return _cmderr(dm.t.read(DMI.ABSTRACTCS))

    def race(cmd: int, during=()) -> tuple:
        """
        Start the long command (progbuf0 must already be `jr t1`), run the
        `during` accesses and then write `cmd` while it is still busy.
        Returns (cmderr, busy-still-set-after-the-accesses).
        """
        clear_cmderr()
        dm.t.write(DMI.COMMAND, CMD_POSTEXEC_ONLY)        # non-blocking
        for access in during:
            access()
        dm.t.write(DMI.COMMAND, cmd)                      # refused: busy
        still_busy = _busy(dm.t.read(DMI.ABSTRACTCS))
        wait_not_busy()
        return _cmderr(dm.t.read(DMI.ABSTRACTCS)), still_busy

    # 64-bit accesses throughout: an aarsize=2 write of 0x80180000 sign-extends
    # to 0xFFFFFFFF80180000 on RV64 and `jr t1` faults.
    def point_t1_at_loop() -> None:
        dm.write_reg64(T1_REGNO, LOOP_ADDR)

    def while_running(cmd: int) -> int:
        """Resume the program with its own t0/t1, issue `cmd`, halt again.

        cmderr is cleared around the register accesses: the API's own
        abstract commands raise on a cmderr left over from the probe."""
        clear_cmderr()
        dm.write_reg64(T0_REGNO, saved["t0"])
        dm.write_reg64(T1_REGNO, saved["t1"])
        dm.resume()
        err = run(cmd)
        dm.halt()
        clear_cmderr()
        point_t1_at_loop()
        dm.t.write(DMI.DATA0, 0)       # a refused transfer read left data0 as it was
        return err

    def sba_write64(addr: int, value: int) -> None:
        dm.t.write(DMI.SBCS, 3 << 17)                     # 64-bit, no read-on-addr
        dm.t.write(DMI.SBADDRESS0, addr)
        dm.t.write(SBDATA1, value >> 32)
        dm.t.write(DMI.SBDATA0, value & 0xFFFFFFFF)       # starts the write
        dm._wait_sbus()

    def sba_read64(addr: int) -> int:
        dm.t.write(DMI.SBCS, (1 << 20) | (3 << 17))       # read on address
        dm.t.write(DMI.SBADDRESS0, addr)
        dm._wait_sbus()
        return (dm.t.read(SBDATA1) << 32) | dm.t.read(DMI.SBDATA0)

    def verdict(tc: str, got: dict, want: dict, extra: str = "") -> StepResult:
        bad = {k: v for k, v in got.items() if v not in want[k]}
        return StepResult(
            ok=not bad,
            msg=f"{tc}: " + ", ".join(f"{k} cmderr={v}" for k, v in got.items())
                + (f"; {extra}" if extra else "")
                + ("  OK" if not bad else f"  unexpected: {bad}"),
        )

    # ── Setup ─────────────────────────────────────────────────────────────
    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        saved["t0"] = dm.read_reg64(T0_REGNO)
        saved["t1"] = dm.read_reg64(T1_REGNO)
        words = [(ADDI_T0_M1 << 32) | LI_T0_400, (EBREAK << 32) | BNEZ_T0_BACK]
        for i, w in enumerate(words):
            sba_write64(LOOP_ADDR + 8 * i, w)
        back = [sba_read64(LOOP_ADDR + 8 * i) for i in range(len(words))]
        point_t1_at_loop()
        ok = back == words
        return StepResult(
            ok=ok,
            msg=f"Delay loop at 0x{LOOP_ADDR:08x} over SBA: "
                + " ".join(f"0x{b:016x}" for b in back)
                + ("  OK" if ok else "  read-back differs"),
        )
    session.add_step("Load the delay loop into RAM, t1 -> loop", setup)

    # ── TC-PB-010: one-word buffer -- busy, exception, halt/resume ────────
    # Only progbuf0 is written in this step, so pb_fill = 1 throughout.
    # The busy window also carries the dmcontrol/dmstatus/sbcs accesses
    # cg_gated_access has no other source for.
    def tc_pb_010():
        dm.write_progbuf(0, JR_T1)
        busy_err, in_window = race(
            CMD_POSTEXEC_ONLY,
            during=(lambda: dm.t.read(DMI.DMSTATUS),
                    lambda: dm.t.write(DMI.DMCONTROL, 1),          # dmactive only
                    lambda: dm.t.read(DMI.SBCS)))
        dm.write_progbuf(0, ILLEGAL)
        exc_err = run(CMD_POSTEXEC_ONLY)
        hr_err = while_running(CMD_POSTEXEC_ONLY)
        return verdict(
            "TC-PB-010 (progbuf0 only)",
            {"busy": busy_err, "exception": exc_err, "halt_resume": hr_err},
            {"busy": {CMDERR_BUSY}, "exception": {CMDERR_EXC},
             "halt_resume": {CMDERR_HALTRESUME}},
            f"dmstatus/dmcontrol/sbcs accessed while busy={in_window}")
    session.add_step("TC-PB-010: one-word Program Buffer outcomes", tc_pb_010)

    # ── TC-PB-011: four words -- exception, halt/resume ───────────────────
    # (busy with a partly filled buffer is cmd_busy's own race.)
    def tc_pb_011():
        for i in range(1, 4):
            dm.write_progbuf(i, EBREAK)
        dm.write_progbuf(0, ILLEGAL)
        exc_err = run(CMD_POSTEXEC_ONLY)
        hr_err = while_running(CMD_POSTEXEC_ONLY)
        return verdict(
            "TC-PB-011 (progbuf0-3)",
            {"exception": exc_err, "halt_resume": hr_err},
            {"exception": {CMDERR_EXC}, "halt_resume": {CMDERR_HALTRESUME}})
    session.add_step("TC-PB-011: four-word Program Buffer outcomes", tc_pb_011)

    # ── TC-PB-012: all eight words -- busy, exception, halt/resume ────────
    def tc_pb_012():
        for i in range(4, 8):
            dm.write_progbuf(i, EBREAK)
        dm.write_progbuf(0, JR_T1)
        busy_err, in_window = race(CMD_POSTEXEC_ONLY)
        dm.write_progbuf(0, ILLEGAL)
        exc_err = run(CMD_POSTEXEC_ONLY)
        hr_err = while_running(CMD_POSTEXEC_ONLY)
        return verdict(
            "TC-PB-012 (progbuf0-7)",
            {"busy": busy_err, "exception": exc_err, "halt_resume": hr_err},
            {"busy": {CMDERR_BUSY}, "exception": {CMDERR_EXC},
             "halt_resume": {CMDERR_HALTRESUME}},
            f"race landed while busy={in_window}")
    session.add_step("TC-PB-012: full Program Buffer outcomes", tc_pb_012)

    # ── TC-AC-030: busy for every command kind ────────────────────────────
    # #3.7.1: a command written while one is in flight sets cmderr=1, whatever
    # the new command is. Quick Access and Access Memory are not implemented
    # here and cmdtype 3 is reserved -- busy must still win over "not
    # supported", because the DM never gets to decode the refused write.
    def tc_ac_030():
        dm.write_progbuf(0, JR_T1)
        got = {}
        for name, cmdtype in (("quick_access", 1), ("access_memory", 2), ("reserved", 3)):
            got[name], _ = race(cmdtype << CMDTYPE_LSB)
        return verdict("TC-AC-030 busy by cmdtype", got,
                       {k: {CMDERR_BUSY} for k in got})
    session.add_step("TC-AC-030: busy for Quick Access, Access Memory, reserved", tc_ac_030)

    # ── TC-AC-031: postexec only, with an aarsize nothing implements ──────
    # Access Register, transfer: "This bit can be used to just execute the
    # Program Buffer without having to worry about placing valid values into
    # aarsize or regno." So with transfer=0 the reserved aarsize must not
    # matter and the buffer runs (cmderr=0). This DM rejects it with cmderr=2:
    # dm_mem.sv checks `aarsize >= MaxAar` whatever transfer is -- inherited
    # from pulp upstream, where it is pulp-platform/riscv-dbg#32 (agreed in
    # 2019, closed, never changed in the code).
    def tc_ac_031():
        dm.write_progbuf(0, EBREAK)
        err = run(AARSIZE_RESERVED | POSTEXEC)
        return verdict("TC-AC-031 postexec-only, aarsize=5",
                       {"postexec_only": err}, {"postexec_only": {CMDERR_NONE}},
                       "cmderr=2 here is the aarsize check ignoring transfer=0 "
                       "(pulp-platform/riscv-dbg#32)" if err == CMDERR_NOTSUP else "")
    session.add_step("TC-AC-031: postexec-only command with a reserved aarsize", tc_ac_031)

    # ── TC-AC-032: transfer + postexec -- every failure ───────────────────
    # #3.7.1.1: transfer happens before postexec, and a failure in either
    # stops the command. Each failure is provoked once.
    def tc_ac_032():
        dm.write_progbuf(0, JR_T1)
        busy_err, _ = race(CMD_XFER_READ_X5_POST)
        notsup = run(AARSIZE_RESERVED | TRANSFER | POSTEXEC | X5_REGNO)
        dm.write_progbuf(0, ILLEGAL)
        exc = run(CMD_XFER_READ_X5_POST)
        dm.t.write(DMI.DATA0, 0)
        hr = while_running(CMD_XFER_READ_X5_POST)
        dm.write_progbuf(0, EBREAK)
        return verdict(
            "TC-AC-032 transfer+postexec",
            {"busy": busy_err, "not_supported": notsup, "exception": exc, "halt_resume": hr},
            {"busy": {CMDERR_BUSY}, "not_supported": {CMDERR_NOTSUP},
             "exception": {CMDERR_EXC}, "halt_resume": {CMDERR_HALTRESUME}})
    session.add_step("TC-AC-032: transfer+postexec failures", tc_ac_032)

    # ── TC-AC-033: neither transfer nor postexec ──────────────────────────
    # A legal no-op: with transfer=0 nothing is copied and with postexec=0
    # nothing runs, so there is nothing to fail and a halted hart must answer
    # cmderr=0. On a running hart the spec leaves it open (an implementation
    # may need the hart halted for any Access Register), so 0 and 4 are both
    # accepted there.
    #
    # This DM answers 3 on a halted hart: dm_mem.sv's WhereTo jump takes the
    # Program Buffer shortcut only for transfer=0 *with* postexec, so the
    # no-op jumps to the abstract-command ROM, whose first word is still its
    # default dm::illegal() (no Access Register branch replaces it when
    # transfer=0). Same code in pulp upstream.
    def tc_ac_033():
        none = run(CMD_NEITHER)
        dm.write_progbuf(0, JR_T1)
        busy_err, _ = race(CMD_NEITHER)
        dm.write_progbuf(0, EBREAK)
        hr = while_running(CMD_NEITHER)
        return verdict(
            "TC-AC-033 neither",
            {"halted": none, "busy": busy_err, "running": hr},
            {"halted": {CMDERR_NONE}, "busy": {CMDERR_BUSY},
             "running": {CMDERR_NONE, CMDERR_HALTRESUME}})
    session.add_step("TC-AC-033: no-op command (neither transfer nor postexec)", tc_ac_033)

    # ── TC-AC-034: reserved aarsize on a GPR ──────────────────────────────
    # aarsize 5 is not a defined size: "If aarsize specifies a size larger
    # than the register's actual size, then the access must fail."
    def tc_ac_034():
        err = run(AARSIZE_RESERVED | TRANSFER | X5_REGNO)
        dm.t.write(DMI.DATA0, 0)
        return verdict("TC-AC-034 aarsize=5 on x5",
                       {"not_supported": err}, {"not_supported": {CMDERR_NOTSUP}})
    session.add_step("TC-AC-034: reserved aarsize on a GPR", tc_ac_034)

    # ── TC-AC-035: 64-bit access to a regno above the FPRs ────────────────
    # Nothing is implemented there on this DUT, so it must fail; 2 and 3 are
    # both accepted (not supported, or the access raised an exception).
    def tc_ac_035():
        err = run(AARSIZE64 | TRANSFER | OTHER_REGNO)
        dm.t.write(DMI.DATA0, 0)
        return verdict(f"TC-AC-035 64-bit read of regno 0x{OTHER_REGNO:04x}",
                       {"other_regno": err}, {"other_regno": {CMDERR_NOTSUP, CMDERR_EXC}})
    session.add_step("TC-AC-035: 64-bit access outside GPR/FPR/CSR", tc_ac_035)

    # ── The DM is still usable, and the program's registers are restored ──
    def restore():
        clear_cmderr()
        for i in range(8):
            dm.write_progbuf(i, EBREAK)
        dm.write_reg64(T0_REGNO, saved["t0"])
        dm.write_reg64(T1_REGNO, saved["t1"])
        t2 = dm.read_reg64(T2_REGNO)
        dm.write_gpr(T2_REGNO, 0xABCD)                     # round-trip probe
        val = dm.read_gpr(T2_REGNO)
        dm.write_reg64(T2_REGNO, t2)
        err = _cmderr(dm.t.read(DMI.ABSTRACTCS))
        ok = val == 0xABCD and err == CMDERR_NONE
        return StepResult(
            ok=ok,
            msg=f"DM usable afterwards: GPR round-trip 0x{val:x} (expect 0xabcd), "
                f"cmderr={err}  " + ("OK" if ok else "DM left unusable"),
        )
    session.add_step("DM usable afterwards; registers restored", restore)

    return session
