"""
sequences/step_matrix_sequence.py — single-step every instruction class under
every stepie/interrupt combination, at M, S and U, in long unbroken runs, and
check where each step lands.

`cg_step_external` crosses the class of the instruction a step retired with
dcsr.stepie and a pending interrupt, with the privilege level, and with how
many steps in a row preceded it. The ordinary flow steps a handful of
instructions in M with nothing pending, so most of that matrix was empty.

The debugger builds each condition itself and then steps round `step_loop`
(sw/step_classes.S), which holds one instruction of every class:

- **Interrupt pending.** The CLINT's `mtimecmp` resets to 0, so the machine
  timer interrupt is posted from reset; `mie.MTIE` decides whether it counts
  as pending (`|(mip & mie)`). With `mstatus.MIE=0` in M-mode it is never
  taken, so the step still retires the instruction under test -- in both
  stepie settings. Below M an enabled M interrupt is always taken, so the S
  and U runs keep MTIE clear.
- **Privilege.** `dcsr.prv` chooses the level the step runs in; PMP entry 0
  is opened first so S and U can fetch and load at all.
- **Runs.** Each M-mode combination is stepped long enough that every class
  also lands in the 2-16 and 17-64 consecutive-step bins.

Every step is checked against Sdext's `dcsr.step` rule for the instruction it
stepped:

- a trap: Debug Mode is re-entered at the handler's first instruction, before
  it runs. CVA6 runs that instruction first (RTL-010, openhwgroup/cva6#3429):
  its single-step entry waits for a commit that a trapping instruction never
  gets.
- an xRET: `dpc` is the return address and `dcsr.prv` the level returned to.
  CVA6 reports pc+4 and the old level (RTL-011): its step logic tests
  `eret_o` before the same always_comb assigns it.

Both deviations are recorded and reported by the last check step rather than
stopping the run. After an xRET step the debugger puts dpc/prv where the
xRET should have gone, as a debugger working around the defect would, so the
remaining classes are still stepped at the intended privilege.

Traces to: SSTEP-006 (stepie=0 with an interrupt pending), SSTEP-007
(stepie=1), SSTEP-008 (trap), SSTEP-009 (xRET), SSTEP-019/015 (classes),
SSTEP-020 (runs), SSTEP-021-V (class x privilege), SSTEP-022-V (class x
stepie).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.sequences.hart_control import (
    CAUSE_STEP, DCSR, DCSR_STEP, DCSR_STEPIE, DPC, MCAUSE, MEPC, MIE, MIE_MTIE,
    MSTATUS, MSTATUS_MIE, PRV_M, PRV_S, PRV_U, cause_of, ensure_halted,
    modify_dcsr, open_pmp, place, step_once, symbol_addr,
)

S0_REGNO = 0x1008
SEPC = 0x0141
PRV_NAME = {PRV_U: "U", PRV_S: "S", PRV_M: "M"}

#: Steps per M-mode combination. One pass of step_loop, including the two
#: trips through the trap handler, is 14 steps, so 40 puts every class past
#: step 17 at least once.
M_STEPS = 40
LOW_STEPS = 24

SYMBOLS = ("step_loop", "cls_sret", "sret_insn", "scratch_area",
           "trap_handler", "handler_mret", "handler_end")


def build_step_matrix_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_classes.elf",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    addrs: dict = {}
    #: Spec deviations seen across all runs: kind -> list of descriptions.
    deviations: dict = {"trap": [], "xret": []}

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        for sym in SYMBOLS:
            addrs[sym] = symbol_addr(elf, sym)
        open_pmp(dm)
        dm.write_reg64(S0_REGNO, addrs["scratch_area"])     # step_loop loads through s0
        mstatus = dm.read_reg64(MSTATUS)
        dm.write_reg64(MSTATUS, mstatus & ~MSTATUS_MIE)     # an M interrupt is never taken
        return StepResult(ok=True, msg="PMP opened, s0 -> scratch_area, mstatus.MIE=0 "
                                       + ", ".join(f"{k}=0x{v:x}" for k, v in addrs.items()))
    session.add_step("Resolve symbols, open PMP, disable M interrupts", setup)

    def in_handler(pc: int) -> bool:
        return addrs["trap_handler"] <= pc < addrs["handler_end"]

    def run(label: str, start: int, prv: int, steps: int, stepie: bool, irq: bool):
        """Step `steps` times from `start` at `prv`. Returns (ok, detail).

        ok covers what a step must always do -- halt again with cause=4.
        Where it lands is checked per instruction and recorded in
        `deviations`.
        """
        if not ensure_halted(dm):
            return False, "hart would not halt"
        dm.write_reg64(MIE, MIE_MTIE if irq else 0)
        modify_dcsr(dm, set_bits=DCSR_STEP | (DCSR_STEPIE if stepie else 0),
                    clear_bits=0 if stepie else DCSR_STEPIE)
        place(dm, start, prv)
        pc, cur_prv = start, prv
        levels = set()
        trail = []
        for n in range(steps):
            # What the spec says this step must do, for an xRET. The return
            # address is read before the step.
            if pc == addrs["handler_mret"]:
                expect = (dm.read_reg64(MEPC), prv)       # MPP is the run's level
            elif pc == addrs["sret_insn"]:
                expect = (dm.read_reg64(SEPC), PRV_S)     # SPP=S, set by cls_sret
            else:
                expect = None

            if not step_once(dm):
                return False, f"step {n + 1} did not re-halt; path {' '.join(trail)}"
            dcsr = dm.read_gpr(DCSR)
            if cause_of(dcsr) != CAUSE_STEP:
                return False, f"step {n + 1} halted with cause={cause_of(dcsr)}"
            new_prv = dcsr & 0x3
            dpc = dm.read_reg64(DPC)
            mark = f"{PRV_NAME[new_prv]}{dpc & 0xFFF:03x}"

            if expect is not None:
                want_pc, want_prv = expect
                if (dpc, new_prv) != (want_pc, want_prv):
                    deviations["xret"].append(
                        f"{label}: xRET at 0x{pc:x} -> dpc=0x{dpc:x} prv={PRV_NAME[new_prv]} "
                        f"(expect 0x{want_pc:x} {PRV_NAME[want_prv]})")
                    # Resume where the xRET should have gone.
                    place(dm, want_pc, want_prv)
                    dpc, new_prv = want_pc, want_prv
                    mark += f">{PRV_NAME[new_prv]}{dpc & 0xFFF:03x}"
            elif in_handler(dpc) and not in_handler(pc):
                # The stepped instruction trapped: the spec halts at the
                # handler's first instruction, before it runs.
                cause = dm.read_reg64(MCAUSE) & 0xFF
                mark += f"(c{cause})"
                if dpc != addrs["trap_handler"]:
                    deviations["trap"].append(
                        f"{label}: trap (mcause={cause}) at 0x{pc:x} -> dpc=0x{dpc:x} "
                        f"(expect the handler entry 0x{addrs['trap_handler']:x})")

            levels.add(PRV_NAME[cur_prv])
            trail.append(mark)
            pc, cur_prv = dpc, new_prv
        return True, (f"{steps} steps, ran at {''.join(sorted(levels))}; "
                      f"path {' '.join(trail)}")

    def m_combo(stepie: bool, irq: bool):
        label = f"M stepie={int(stepie)} irq={int(irq)}"

        def step():
            ok, detail = run(label, addrs["step_loop"], PRV_M, M_STEPS, stepie, irq)
            return StepResult(
                ok=ok,
                msg=f"TC-SSTEP-M: stepie={int(stepie)} irq_pending={int(irq)}: {detail}  "
                    + ("OK" if ok else "step broke"))
        return step
    for stepie in (False, True):
        for irq in (False, True):
            session.add_step(f"Step in M, stepie={int(stepie)}, interrupt pending={int(irq)}",
                             m_combo(stepie, irq))

    def low(prv: int):
        def step():
            # From step_loop+4: in U the wfi is illegal, and starting on it
            # would only re-test the trap at U (done separately below).
            ok, detail = run(PRV_NAME[prv], addrs["step_loop"] + 4, prv, LOW_STEPS,
                             False, False)
            return StepResult(
                ok=ok,
                msg=f"TC-SSTEP-{PRV_NAME[prv]}: {detail}  " + ("OK" if ok else "step broke"))
        return step
    session.add_step("Step in S", low(PRV_S))
    session.add_step("Step in U", low(PRV_U))

    def wfi_in_u():
        # wfi at U with S implemented is an illegal instruction (Priv. 3.1.6.5):
        # stepping it is a trap at U.
        ok, detail = run("U wfi", addrs["step_loop"], PRV_U, 1, False, False)
        return StepResult(ok=ok, msg=f"TC-SSTEP-U-wfi: {detail}  " + ("OK" if ok else "step broke"))
    session.add_step("Step a wfi in U", wfi_in_u)

    def sret_in_s():
        # cls_sret: la (2), csrw sepc, li, csrs sstatus, sret, then step_loop.
        ok, detail = run("S sret", addrs["cls_sret"], PRV_S, 8, False, False)
        return StepResult(ok=ok, msg=f"TC-SSTEP-S-sret: {detail}  " + ("OK" if ok else "step broke"))
    session.add_step("Step an sret in S", sret_in_s)

    def spec_check():
        lines = []
        for kind, ref in (("trap", "SSTEP-008, RTL-010 (openhwgroup/cva6#3429)"),
                          ("xret", "SSTEP-009, RTL-011")):
            seen = deviations[kind]
            if seen:
                lines.append(f"{len(seen)} {kind} step(s) off-spec [{ref}], first: {seen[0]}")
        ok = not lines
        return StepResult(
            ok=ok,
            msg=("TC-SSTEP-008/009: every trap and xRET step landed where Sdext requires"
                 if ok else "TC-SSTEP-008/009: " + "; ".join(lines)))
    session.add_step("Check trap and xRET steps against Sdext", spec_check)

    def restore():
        if not ensure_halted(dm):
            return StepResult(ok=False, msg="hart would not halt")
        dm.write_reg64(MIE, 0)
        modify_dcsr(dm, clear_bits=DCSR_STEP | DCSR_STEPIE, prv=PRV_M)
        return StepResult(ok=True, msg="dcsr.step/stepie cleared, prv=M, mie=0")
    session.add_step("Restore", restore)

    return session
