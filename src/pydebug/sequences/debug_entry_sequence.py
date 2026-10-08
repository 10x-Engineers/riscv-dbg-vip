"""
sequences/debug_entry_sequence.py — every way a hart enters Debug Mode, at
every privilege level it can enter from.

Spec Sdext 4.9.1 gives `dcsr.cause` its encodings. Only `haltreq` (3) and
`step` (4) come from DMI writes; `ebreak` (1) and `trigger` (2) come from the
hart's own execution. The ebreak cases point `dpc` at a parked `ebreak` in the
test program, choose `dcsr.prv`, and resume into it. Which privilege the
ebreak is taken from is exactly what `dcsr.ebreakm/s/u` gate, so each level is
exercised with its own bit set and, for M, with it clear.

History worth keeping: this scenario used to write `dpc` with a 32-bit
abstract command. 0x80000050 then landed as 0xFFFFFFFF80000050 and the hart
faulted instead of reaching the ebreak, while a 32-bit read-back showed the
intended value. TC-DCSR-012 passed anyway -- a hart that never reached the
ebreak did not enter Debug Mode from it either -- so it now also requires the
ebreak to have trapped where it should.

`trigger` (2) needs Sdtrig, which this CVA6 build compiles out (`Sdtrig: 0` in
cv64a6_imafdc_sv39_config_pkg.sv); the trigger CSRs do not exist and the step
reports N/A. `resethaltreq` (5) needs halt-on-reset (RTL-004); `group` (6)
needs more than one hart.

Load and store watchpoints (TC-DCSR-016..018) arm mcontrol6 with action=1
on watch_data and resume into watch_load: the hart must halt on the access by
itself, at the instruction that made it, and only in the privilege modes the
trigger's m/s/u bits select. Triggers are disarmed by writing an mcontrol6
with no mode or match bits rather than tdata1=0, which this core ignores on
RV64 (RTL-013) -- a "disarmed" trigger left armed would fire in a later step.

Traces to: TC-DCSR-010 (ebreak entry, M), TC-DCSR-011 (trigger entry),
TC-DCSR-012 (ebreakm/s/u gate ebreak entry), TC-DCSR-013 (ebreak entry, S and
U), TC-DCSR-014 (haltreq from S and U), TC-DCSR-015 (step from S and U),
TC-DCSR-016 (load watchpoint), TC-DCSR-017 (store watchpoint), TC-DCSR-018
(watchpoint privilege filter).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DebugError
from pydebug.sequences.hart_control import (
    CAUSE_EBREAK, CAUSE_HALTREQ, CAUSE_STEP, CAUSE_TRIGGER,
    DCSR, DCSR_EBREAKM, DCSR_EBREAKS, DCSR_EBREAKU, DCSR_STEP, DPC,
    MCAUSE, MEPC, PRV_M, PRV_S, PRV_U,
    cause_of, ensure_halted, modify_dcsr, open_pmp, place,
    run_until_halted, step_once, symbol_addr,
)

TSELECT = 0x07A0
TDATA1 = 0x07A1
TDATA2 = 0x07A2

#: mcontrol6 (Sdtrig): type=6 in tdata1[63:60], dmode, action=1 (enter Debug
#: Mode) in [15:12], m/s/u in bits 6/4/3, execute in bit 2.
MC6_TYPE = 6 << 60
MC6_DMODE = 1 << 59
MC6_ACTION_DBG = 1 << 12
MC6_M, MC6_S, MC6_U = 1 << 6, 1 << 4, 1 << 3
MC6_EXECUTE, MC6_STORE, MC6_LOAD = 1 << 2, 1 << 1, 1 << 0
#: A valid mcontrol6 that matches nothing: no mode and no match bits.
MC6_DISARMED = MC6_TYPE | MC6_DMODE
MC6_MODE = {PRV_M: MC6_M, PRV_S: MC6_S, PRV_U: MC6_U}

S1_REGNO = 0x1009

#: mcause for a breakpoint exception (Priv. spec 3.1.15).
MCAUSE_BREAKPOINT = 3

PRV_NAME = {PRV_U: "U", PRV_S: "S", PRV_M: "M"}
EBREAK_BIT = {PRV_M: DCSR_EBREAKM, PRV_S: DCSR_EBREAKS, PRV_U: DCSR_EBREAKU}


def build_debug_entry_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_classes.elf",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    addrs: dict = {}

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        for sym in ("cls_ebreak", "ebreak_park", "cls_trigger_target", "trigger_lead", "step_loop",
                    "watch_load", "watch_store", "watch_park", "watch_data"):
            addrs[sym] = symbol_addr(elf, sym)
        open_pmp(dm)
        return StepResult(
            ok=True,
            msg="resolved " + ", ".join(f"{k}=0x{v:08x}" for k, v in addrs.items())
                + "; PMP entry 0 opened for S/U")
    session.add_step("Resolve entry points, open PMP", setup)

    def enter_via_ebreak(prv: int, ebreak_bits: int):
        """Resume at the parked ebreak in `prv` with the given ebreak* bits.
        Returns (entered, cause, dpc, prv_at_entry)."""
        modify_dcsr(dm, set_bits=ebreak_bits,
                    clear_bits=(DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU | DCSR_STEP) & ~ebreak_bits)
        place(dm, addrs["cls_ebreak"], prv)
        entered = run_until_halted(dm)
        if not entered:
            ensure_halted(dm)
        dcsr = dm.read_gpr(DCSR)
        return entered, cause_of(dcsr), dm.read_reg64(DPC), dcsr & 0x3

    # ── TC-DCSR-012: ebreakm=0 -- ebreak must NOT enter Debug Mode ────────
    # Checked first: if ebreak entered Debug Mode regardless of ebreakm, the
    # positive case would pass for the wrong reason. And the ebreak must
    # really have run -- as a breakpoint exception into the hart's handler.
    # S and U as well: each ebreak* bit gates its own privilege, so a core
    # that wired ebreaks/ebreaku to ebreakm passes the M case alone. With
    # medeleg clear the breakpoint traps to M from any level.
    def no_ebreak_entry(prv: int):
        def step():
            if not ensure_halted(dm):
                return StepResult(ok=False, msg="hart would not halt")
            dm.write_reg64(MCAUSE, 0)
            entered, cause, _, _ = enter_via_ebreak(prv, 0)
            mcause, mepc = dm.read_reg64(MCAUSE), dm.read_reg64(MEPC)
            reached = mcause == MCAUSE_BREAKPOINT and mepc in (addrs["cls_ebreak"], addrs["cls_ebreak"] + 4)
            ok = cause != CAUSE_EBREAK and reached
            bit = f"ebreak{PRV_NAME[prv].lower()}"
            return StepResult(
                ok=ok,
                msg=f"TC-DCSR-012: {bit}=0 in {PRV_NAME[prv]} -> dcsr.cause={cause} (not ebreak), "
                    f"mcause={mcause} mepc=0x{mepc:x} (breakpoint trap at the ebreak: {reached})  "
                    + ("OK" if ok else "entered Debug Mode, or never reached the ebreak"))
        return step
    session.add_step("TC-DCSR-012: ebreakm=0 does not enter Debug Mode", no_ebreak_entry(PRV_M))
    session.add_step("TC-DCSR-012: ebreaks=0 does not enter Debug Mode from S", no_ebreak_entry(PRV_S))
    session.add_step("TC-DCSR-012: ebreaku=0 does not enter Debug Mode from U", no_ebreak_entry(PRV_U))

    # ── TC-DCSR-010 / 013: ebreak enters Debug Mode from M, S and U ───────
    def ebreak_entry(prv: int, tc: str):
        def step():
            if not ensure_halted(dm):
                return StepResult(ok=False, msg="hart would not halt")
            entered, cause, dpc, prv_seen = enter_via_ebreak(prv, EBREAK_BIT[prv])
            ok = (entered and cause == CAUSE_EBREAK and dpc == addrs["cls_ebreak"]
                  and prv_seen == prv)
            return StepResult(
                ok=ok,
                msg=f"{tc}: ebreak{PRV_NAME[prv].lower()}=1 in {PRV_NAME[prv]} -> "
                    f"halted={entered} cause={cause} (expect {CAUSE_EBREAK}) "
                    f"dpc=0x{dpc:x} (expect the ebreak, 0x{addrs['cls_ebreak']:x}) "
                    f"dcsr.prv={prv_seen}  "
                    + ("OK" if ok else "wrong entry"))
        return step
    session.add_step("TC-DCSR-010: ebreak enters Debug Mode from M", ebreak_entry(PRV_M, "TC-DCSR-010"))
    session.add_step("TC-DCSR-013: ebreak enters Debug Mode from S", ebreak_entry(PRV_S, "TC-DCSR-013"))
    session.add_step("TC-DCSR-013: ebreak enters Debug Mode from U", ebreak_entry(PRV_U, "TC-DCSR-013"))

    # ── TC-DCSR-014: haltreq interrupts S- and U-mode code ────────────────
    def haltreq_entry(prv: int):
        def step():
            if not ensure_halted(dm):
                return StepResult(ok=False, msg="hart would not halt")
            modify_dcsr(dm, clear_bits=DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU | DCSR_STEP)
            place(dm, addrs["ebreak_park"], prv)      # a one-instruction spin
            dm.resume()
            running = dm.is_running()
            dm.halt()
            dcsr = dm.read_gpr(DCSR)
            dpc = dm.read_reg64(DPC)
            ok = (running and cause_of(dcsr) == CAUSE_HALTREQ and dcsr & 0x3 == prv
                  and dpc == addrs["ebreak_park"])
            return StepResult(
                ok=ok,
                msg=f"TC-DCSR-014: running in {PRV_NAME[prv]}={running}, halted -> "
                    f"cause={cause_of(dcsr)} (expect {CAUSE_HALTREQ}) prv={dcsr & 0x3} "
                    f"dpc=0x{dpc:x} (expect the spin, 0x{addrs['ebreak_park']:x})  "
                    + ("OK" if ok else "wrong entry"))
        return step
    session.add_step("TC-DCSR-014: haltreq from S", haltreq_entry(PRV_S))
    session.add_step("TC-DCSR-014: haltreq from U", haltreq_entry(PRV_U))

    # ── TC-DCSR-015: a single step from S and from U ──────────────────────
    def step_entry(prv: int):
        def step():
            if not ensure_halted(dm):
                return StepResult(ok=False, msg="hart would not halt")
            start = addrs["step_loop"] + 4               # `li t3, 1`: an ordinary instruction
            modify_dcsr(dm, set_bits=DCSR_STEP,
                        clear_bits=DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU)
            place(dm, start, prv)
            entered = step_once(dm)
            dcsr = dm.read_gpr(DCSR)
            dpc = dm.read_reg64(DPC)
            modify_dcsr(dm, clear_bits=DCSR_STEP)
            ok = (entered and cause_of(dcsr) == CAUSE_STEP and dcsr & 0x3 == prv
                  and dpc == start + 4)
            return StepResult(
                ok=ok,
                msg=f"TC-DCSR-015: step in {PRV_NAME[prv]} -> halted={entered} "
                    f"cause={cause_of(dcsr)} (expect {CAUSE_STEP}) prv={dcsr & 0x3} "
                    f"dpc=0x{dpc:x} (expect 0x{start + 4:x})  "
                    + ("OK" if ok else "wrong entry"))
        return step
    session.add_step("TC-DCSR-015: step from S", step_entry(PRV_S))
    session.add_step("TC-DCSR-015: step from U", step_entry(PRV_U))

    # ── TC-DCSR-011: an execute trigger fires (cause=2) ───────────────────
    def tc_dcsr_011():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        target = addrs["cls_trigger_target"]
        try:
            dm.write_gpr(TSELECT, 0)
            dm.write_reg64(TDATA2, target)
            dm.write_reg64(TDATA1, MC6_TYPE | MC6_DMODE | MC6_ACTION_DBG | MC6_M | MC6_EXECUTE)
            readback = dm.read_reg64(TDATA1)
        except DebugError as e:
            ensure_halted(dm)
            return StepResult(
                ok=True,
                msg=f"TC-DCSR-011: N/A -- the trigger CSRs raise an exception ({e}); "
                    f"this CVA6 build has Sdtrig=0, so no trigger can fire")
        if readback >> 60 != 6:
            return StepResult(
                ok=True,
                msg=f"TC-DCSR-011: N/A -- trigger 0 did not accept an mcontrol6 "
                    f"execute trigger (tdata1=0x{readback:016x})")
        modify_dcsr(dm, clear_bits=DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU | DCSR_STEP)
        place(dm, addrs["trigger_lead"], PRV_M)      # run INTO the target
        entered = run_until_halted(dm)       # no halt request: only the trigger can halt it
        if not entered:
            ensure_halted(dm)
        cause = cause_of(dm.read_gpr(DCSR))
        dpc = dm.read_reg64(DPC)
        dm.write_reg64(TDATA1, 0)
        # An execute trigger with timing=before halts with dpc on the matched
        # instruction (Sdtrig #5.7.12). A self-halt there is the trigger firing,
        # whatever dcsr.cause says.
        fired = entered and dpc == target
        ok = fired and cause == CAUSE_TRIGGER
        if ok:
            verdict = "OK"
        elif fired:
            verdict = f"trigger fired but dcsr.cause={cause}, not {CAUSE_TRIGGER} -- RTL-012"
        else:
            verdict = "trigger did not enter Debug Mode"
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-011: execute trigger at 0x{target:x} -> self-halted={entered} "
                f"dpc=0x{dpc:x} cause={cause} (expect {CAUSE_TRIGGER})  {verdict}")
    session.add_step("TC-DCSR-011: trigger enters Debug Mode (cause=2)", tc_dcsr_011)

    # ── TC-DCSR-016..018: load and store watchpoints (action=1) ───────────
    def arm_watch(match: int, addr: int, modes: int):
        """Arm trigger 0. Returns None, or a StepResult saying why it cannot be."""
        try:
            dm.write_gpr(TSELECT, 0)
            dm.write_reg64(TDATA1, MC6_DISARMED)
            dm.write_reg64(TDATA2, addr)
            dm.write_reg64(TDATA1, MC6_TYPE | MC6_DMODE | MC6_ACTION_DBG | modes | match)
            readback = dm.read_reg64(TDATA1)
        except DebugError as e:
            ensure_halted(dm)
            return f"N/A -- the trigger CSRs raise an exception ({e})"
        if readback & (modes | match) != modes | match:
            return f"N/A -- trigger 0 did not take the configuration (tdata1=0x{readback:016x})"
        return None

    def run_watch(prv: int, limit: int = 400):
        """Resume at watch_load in `prv` with s1 -> watch_data. Returns
        (self-halted, cause, dpc, dcsr.prv) and leaves the trigger disarmed."""
        modify_dcsr(dm, clear_bits=DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU | DCSR_STEP)
        dm.write_reg64(S1_REGNO, addrs["watch_data"])
        place(dm, addrs["watch_load"], prv)
        entered = run_until_halted(dm, limit)    # no halt request: only the trigger can halt it
        if not entered:
            ensure_halted(dm)
        dcsr = dm.read_gpr(DCSR)
        dpc = dm.read_reg64(DPC)
        dm.write_reg64(TDATA1, MC6_DISARMED)
        return entered, cause_of(dcsr), dpc, dcsr & 0x3

    def watch_verdict(tc: str, what: str, target: int, entered: bool, cause: int, dpc: int,
                      at: int) -> StepResult:
        fired = entered and dpc == at
        ok = fired and cause == CAUSE_TRIGGER
        if ok:
            verdict = "OK"
        elif fired:
            verdict = f"trigger fired but dcsr.cause={cause}, not {CAUSE_TRIGGER} -- RTL-012"
        else:
            verdict = "watchpoint did not halt the hart at the access"
        return StepResult(
            ok=ok,
            msg=f"{tc}: {what} watchpoint on 0x{target:x} -> self-halted={entered} "
                f"dpc=0x{dpc:x} (expect the {what}, 0x{at:x}) cause={cause} "
                f"(expect {CAUSE_TRIGGER})  {verdict}")

    def tc_dcsr_016():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        why = arm_watch(MC6_LOAD, addrs["watch_data"], MC6_M)
        if why:
            return StepResult(ok=True, msg=f"TC-DCSR-016: {why}")
        entered, cause, dpc, _ = run_watch(PRV_M)
        return watch_verdict("TC-DCSR-016", "load", addrs["watch_data"], entered, cause, dpc,
                             addrs["watch_load"])
    session.add_step("TC-DCSR-016: load watchpoint enters Debug Mode", tc_dcsr_016)

    def tc_dcsr_017():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        # The load reads watch_data; only the store, to the next doubleword,
        # matches -- so a store trigger that also fired on loads halts early.
        why = arm_watch(MC6_STORE, addrs["watch_data"] + 8, MC6_M)
        if why:
            return StepResult(ok=True, msg=f"TC-DCSR-017: {why}")
        entered, cause, dpc, _ = run_watch(PRV_M)
        return watch_verdict("TC-DCSR-017", "store", addrs["watch_data"] + 8, entered, cause, dpc,
                             addrs["watch_store"])
    session.add_step("TC-DCSR-017: store watchpoint enters Debug Mode", tc_dcsr_017)

    # Every (enabled mode, running mode) pair: the load must halt the hart
    # exactly when they match. A miss runs on to watch_park, where the
    # debugger's own halt request stops it.
    def tc_dcsr_018():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        bad, cells = [], []
        for enabled in (PRV_M, PRV_S, PRV_U):
            for running in (PRV_M, PRV_S, PRV_U):
                ensure_halted(dm)
                why = arm_watch(MC6_LOAD, addrs["watch_data"], MC6_MODE[enabled])
                if why:
                    return StepResult(ok=True, msg=f"TC-DCSR-018: {why}")
                want = enabled == running
                entered, cause, dpc, prv = run_watch(running, 400 if want else 100)
                fired = entered and dpc == addrs["watch_load"]
                cell = f"{PRV_NAME[enabled]}-only in {PRV_NAME[running]}: fired={fired}"
                cells.append(cell)
                if fired != want or (fired and prv != running):
                    bad.append(cell + (f" prv={prv}" if fired else ""))
        ok = not bad
        return StepResult(
            ok=ok,
            msg="TC-DCSR-018: load watchpoint, enabled mode x running mode -- "
                + ("; ".join(cells) + "  OK" if ok else f"wrong cells: {bad}"))
    session.add_step("TC-DCSR-018: watchpoint fires only in its enabled modes", tc_dcsr_018)

    # ── restore ───────────────────────────────────────────────────────────
    def restore():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        modify_dcsr(dm, clear_bits=DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU | DCSR_STEP,
                    prv=PRV_M)
        dm.write_reg64(DPC, addrs["ebreak_park"])
        return StepResult(ok=True, msg="restored dcsr (M, no ebreak*/step), hart halted")
    session.add_step("Restore dcsr", restore)

    return session
