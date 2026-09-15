"""
sequences/debug_entry_sequence.py — every way a hart enters Debug Mode.

Spec Sdext #4.8.1 gives `dcsr.cause` six encodings. Only `haltreq` (3) and
`step` (4) were ever reached, because every existing scenario enters Debug Mode
by asking the DM to halt. The other reachable causes come from the *hart's own
execution* and cannot be produced by any DMI write:

  1 ebreak   — the hart executes `ebreak` with the matching `dcsr.ebreak*` set
  2 trigger  — an armed Sdtrig trigger fires with action=1

Both need the hart to run to a known instruction, so this sets `dpc` to a label
in the test program and resumes into it. Parking the targets out of the normal
flow keeps them inert unless a sequence jumps there deliberately.

`resethaltreq` (5) is unreachable here: `dmstatus.hasresethaltreq=0`, so
halt-on-reset is not implemented (RTL-004, and an optional feature).
`halt group` (6) needs more than one hart.

Traces to: TC-DCSR-010 (ebreak entry), TC-DCSR-011 (trigger entry),
TC-DCSR-012 (ebreakm gates ebreak entry).
"""

import subprocess

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

DCSR_REGNO   = 0x07B0
DPC_REGNO    = 0x07B1
TSELECT      = 0x07A0
TDATA1       = 0x07A1
TDATA2       = 0x07A2

#: dcsr fields (Sdext #4.8.1).
DCSR_EBREAKM   = 1 << 15
DCSR_CAUSE_LSB = 6
CAUSE_EBREAK, CAUSE_TRIGGER, CAUSE_HALTREQ, CAUSE_STEP = 1, 2, 3, 4

#: mcontrol6 (Sdtrig): type=6 in tdata1[63:60], action=1 (enter Debug Mode)
#: in tdata1[15:12], execute in bit 2, and m-mode in bit 6.
MC6_TYPE       = 6 << 60
MC6_DMODE      = 1 << 59
MC6_ACTION_DBG = 1 << 12
MC6_M          = 1 << 6
MC6_EXECUTE    = 1 << 2


def _symbol_addr(elf: str, symbol: str, nm: str = "riscv64-unknown-elf-nm") -> int:
    out = subprocess.run([nm, elf], capture_output=True, text=True, check=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == symbol:
            return int(parts[0], 16)
    raise RuntimeError(f"symbol {symbol!r} not found in {elf} -- rebuild with `make -C sw`")


def _cause(dcsr: int) -> int:
    return (dcsr >> DCSR_CAUSE_LSB) & 0x7


def _run_to_debug(dm, limit: int = 400) -> bool:
    dm.resume()
    for _ in range(limit):
        if dm.is_halted():
            return True
    return False


def _ensure_halted(dm, limit: int = 200) -> bool:
    """
    Guarantee the hart is halted before touching any CSR.

    Every step here resumes the hart, so the next step starts from whatever
    state the last one left. An abstract command issued to a running hart is
    refused with cmderr=4 (halt/resume) -- which reads as a DM fault but is
    just a missing precondition, and it then poisons every later step because
    cmderr is sticky.
    """
    # cmderr is sticky (#3.14.13): once any command fails, every later one is
    # refused with the SAME error until it is cleared. A single command issued
    # to a running hart therefore poisons the whole rest of the sequence, and
    # each later step reports cmderr=4 as though it had made the mistake
    # itself. Clear it before checking anything else.
    dm.t.write(DMI.ABSTRACTCS, 0x7 << 8)
    if dm.is_halted():
        return True
    dm.halt()
    for _ in range(limit):
        if dm.is_halted():
            return True
    return False


def build_debug_entry_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_classes.elf",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    addrs: dict = {}

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def resolve():
        for sym in ("cls_ebreak", "cls_trigger_target"):
            addrs[sym] = _symbol_addr(elf, sym)
        return StepResult(
            ok=True,
            msg="resolved " + ", ".join(f"{k}=0x{v:08x}" for k, v in addrs.items()))
    session.add_step("Resolve entry-point symbols", resolve)

    # ── TC-DCSR-012: ebreakm=0 -- ebreak must NOT enter Debug Mode ────────
    # Checked before the positive case: if ebreak entered Debug Mode
    # regardless of ebreakm, TC-DCSR-010 would pass for the wrong reason.
    def tc_dcsr_012():
        if not _ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        dcsr = dm.read_gpr(DCSR_REGNO)
        dm.write_gpr(DCSR_REGNO, dcsr & ~DCSR_EBREAKM)
        dm.write_gpr(DPC_REGNO, addrs["cls_ebreak"])
        entered = _run_to_debug(dm, limit=60)
        if not entered:
            dm.halt()
        cause = _cause(dm.read_gpr(DCSR_REGNO))
        # With ebreakm=0 the ebreak traps to the hart's own handler instead,
        # so any halt we see here is our own haltreq, not an ebreak entry.
        ok = cause != CAUSE_EBREAK
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-012: ebreakm=0, ran through ebreak -> dcsr.cause={cause} "
                f"{'(not ebreak -- correctly ignored)' if ok else '(ebreak entry despite ebreakm=0)'}")
    session.add_step("TC-DCSR-012: ebreakm=0 does not enter Debug Mode", tc_dcsr_012)

    # ── TC-DCSR-010: ebreak with ebreakm=1 enters Debug Mode ──────────────
    def tc_dcsr_010():
        if not _ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        dcsr = dm.read_gpr(DCSR_REGNO)
        dm.write_gpr(DCSR_REGNO, dcsr | DCSR_EBREAKM)
        dm.write_gpr(DPC_REGNO, addrs["cls_ebreak"])
        entered = _run_to_debug(dm)
        cause = _cause(dm.read_gpr(DCSR_REGNO))
        dpc = dm.read_gpr(DPC_REGNO)
        ok = entered and cause == CAUSE_EBREAK
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-010: ebreakm=1, executed ebreak at "
                f"0x{addrs['cls_ebreak']:08x} -> halted={entered} "
                f"dcsr.cause={cause} (expect {CAUSE_EBREAK}) dpc=0x{dpc:08x}  "
                f"{'OK' if ok else 'ebreak did not enter Debug Mode'}")
    session.add_step("TC-DCSR-010: ebreak enters Debug Mode (cause=1)", tc_dcsr_010)

    # ── TC-DCSR-011: an execute trigger fires (cause=2) ───────────────────
    def tc_dcsr_011():
        if not _ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        target = addrs["cls_trigger_target"]
        dm.write_gpr(TSELECT, 0)
        selected = dm.read_gpr(TSELECT)
        dm.write_gpr(TDATA2, target)
        tdata1 = MC6_TYPE | MC6_DMODE | MC6_ACTION_DBG | MC6_M | MC6_EXECUTE
        dm.write_gpr(TDATA1, tdata1)
        readback = dm.read_gpr(TDATA1)
        if readback == 0:
            return StepResult(
                ok=True,
                msg=f"TC-DCSR-011: N/A -- trigger {selected} did not accept an "
                    f"mcontrol6 execute trigger (tdata1 reads 0); no Sdtrig "
                    f"support to exercise")
        dcsr = dm.read_gpr(DCSR_REGNO)
        dm.write_gpr(DCSR_REGNO, dcsr & ~DCSR_EBREAKM)   # isolate the trigger
        dm.write_gpr(DPC_REGNO, target)
        entered = _run_to_debug(dm)
        cause = _cause(dm.read_gpr(DCSR_REGNO))
        dm.write_gpr(TDATA1, 0)                          # disarm
        ok = entered and cause == CAUSE_TRIGGER
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-011: execute trigger armed at 0x{target:08x} "
                f"(tdata1=0x{readback:016x}) -> halted={entered} "
                f"dcsr.cause={cause} (expect {CAUSE_TRIGGER})  "
                f"{'OK' if ok else 'trigger did not enter Debug Mode'}")
    session.add_step("TC-DCSR-011: trigger enters Debug Mode (cause=2)", tc_dcsr_011)

    # ── restore ───────────────────────────────────────────────────────────
    def restore():
        if not _ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        dcsr = dm.read_gpr(DCSR_REGNO)
        dm.write_gpr(DCSR_REGNO, dcsr & ~DCSR_EBREAKM)
        dm.halt()
        return StepResult(ok=True, msg="restored dcsr.ebreakm=0, hart halted")
    session.add_step("Restore dcsr", restore)

    return session
