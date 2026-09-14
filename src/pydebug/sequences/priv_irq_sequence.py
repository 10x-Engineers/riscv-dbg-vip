"""
sequences/priv_irq_sequence.py — step in every privilege, at both stepie values.

Three coverpoints need a hart that leaves M mode and an interrupt that is
genuinely pending:

    cg_debug_entry.cp_prv            entry privilege seen as U, S and M
    cg_step_external.cp_prv_at_step  same, at the moment of a step
    cg_step_external.cp_stepie_irq   the {stepie, irq_pending} 2x2

`sw/priv_irq.S` cycles M -> S -> U -> M continuously with a CLINT timer
interrupt armed and left unserviced, so `mip.MTIP` stays asserted. This walks
it twice: once with `dcsr.stepie=0` and once with `stepie=1`, which is what
turns a 1-of-4 coverpoint into a full one.

Stepping with `stepie=1` and an interrupt pending is the interesting half. The
spec allows the interrupt to be taken during the step, so a step that lands in
the trap handler is a pass, not a failure -- what must not happen is the hart
failing to re-enter Debug Mode at all. The check below is written for that
distinction, because asserting `dpc` advanced by the instruction length would
fail on a legitimately-taken interrupt.

Traces to: DM-011-V, SSTEP-006, SSTEP-007, SSTEP-018-V, SSTEP-021-V, SSTEP-022-V

Usage:
    make soc_test_cov CFG_FILE=configs/priv_irq_uvm.json ELF=sw/priv_irq.elf
"""

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI, allhalted, anyhalted

DCSR_CAUSE_STEP = 4
DCSR_CAUSE_HALTREQ = 3

#: dcsr.stepie, bit 11 (spec: Sdext.html#csr-dcsr)
DCSR_STEPIE = 1 << 11
#: dcsr.step, bit 2
DCSR_STEP = 1 << 2
#: dcsr.prv, bits 1:0
DCSR_PRV_MASK = 0x3

REGNO_DCSR = 0x07B0
PRV_NAME = {0: "U", 1: "S", 3: "M"}

#: Enough steps to traverse M -> S -> U and back. The body is ~40 instructions
#: including two trap-handler round trips, so this covers the cycle twice.
STEPS_PER_PASS = 90


def _wait_halted(dm: RISCVDebug, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    status = 0
    while time.monotonic() < deadline:
        status = dm.t.read(DMI.DMSTATUS)
        if allhalted(status) and anyhalted(status):
            return True, status
        time.sleep(0.001)
    return False, dm.t.read(DMI.DMSTATUS)


def build_priv_irq_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/priv_irq.elf",
    steps: int = STEPS_PER_PASS,
) -> DebugSession:
    """
    Walk M/S/U with stepie=0 then stepie=1, an interrupt pending throughout.

    Traces to: SSTEP-022-V (stepped class x stepie x interrupt pending)
    """
    session = DebugSession(mode=mode, stop_on_error=False)
    state = {}

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def confirm():
        halted, status = _wait_halted(dm)
        return StepResult(ok=halted, msg=f"dmstatus=0x{status:08x}")
    session.add_step("Confirm hart halted", confirm)

    def set_stepie(enabled: bool):
        """
        Set dcsr.step and dcsr.stepie together.

        Read-modify-write rather than a blind write: dcsr carries ebreak* and
        prv, and clobbering those would change what the rest of the run means.
        """
        def run():
            d = dm.read_dcsr()
            new = (d | DCSR_STEP | DCSR_STEPIE) if enabled else \
                  ((d | DCSR_STEP) & ~DCSR_STEPIE)
            dm.write_dcsr(new)
            back = dm.read_dcsr()
            got = bool(back & DCSR_STEPIE)
            return StepResult(
                ok=(got == enabled) and bool(back & DCSR_STEP),
                msg=f"dcsr=0x{back:08x} step={int(bool(back & DCSR_STEP))} "
                    f"stepie={int(got)} (wanted stepie={int(enabled)})",
            )
        return run

    def walk(label: str, expect_stepie: bool):
        """
        Step `steps` times, recording the privileges seen.

        With stepie=1 and an interrupt pending the hart may legitimately take
        the interrupt during a step and land in the handler. That is a pass:
        the property under test is that Debug Mode is re-entered with
        cause=step, not that dpc advanced by one instruction.
        """
        def run():
            privs = {}
            pcs = []
            failures = []
            for i in range(steps):
                dm.resume_no_wait()
                halted, status = _wait_halted(dm, timeout=0.5)
                if not halted:
                    failures.append(f"step {i}: hart did not re-halt "
                                    f"(dmstatus=0x{status:08x})")
                    break
                try:
                    d = dm.read_dcsr()
                except Exception as e:
                    failures.append(f"step {i}: dcsr unreadable ({e})")
                    break
                cause = (d >> 6) & 0x7
                prv = d & DCSR_PRV_MASK
                privs[prv] = privs.get(prv, 0) + 1
                try:
                    pcs.append(dm.get_pc())
                except Exception:
                    pass
                if cause != DCSR_CAUSE_STEP:
                    failures.append(f"step {i}: dcsr.cause={cause}, "
                                    f"expected {DCSR_CAUSE_STEP}")
                    if len(failures) > 3:
                        break

            seen = ", ".join(f"{PRV_NAME.get(p, p)}={n}"
                             for p, n in sorted(privs.items()))
            state[label] = privs
            return StepResult(
                ok=(not failures) and len(privs) > 1,
                msg=f"{label}: privileges stepped in -- {seen or 'none'}; "
                    f"dpc {min(pcs):#x}..{max(pcs):#x} over {len(set(pcs))} distinct"
                    if pcs else f"{label}: no steps completed"
                    + (f"; {len(failures)} failure(s): {failures[0]}"
                       if failures else "")
                    + ("" if len(privs) > 1 else
                       "; only one privilege reached -- the program never left M, "
                       "so the privilege crosses stay unfilled"),
            )
        return run

    # ── Pass 1: stepie=0, interrupts masked during the step ────────────────
    session.add_step("Set dcsr.step=1, stepie=0", set_stepie(False))
    session.add_step(f"Walk {steps} steps with stepie=0", walk("stepie=0", False))

    # ── Pass 2: stepie=1, the interrupt may fire ───────────────────────────
    session.add_step("Set dcsr.step=1, stepie=1", set_stepie(True))
    session.add_step(f"Walk {steps} steps with stepie=1", walk("stepie=1", True))

    def summary():
        p0 = state.get("stepie=0", {})
        p1 = state.get("stepie=1", {})
        both = set(p0) | set(p1)
        names = ", ".join(PRV_NAME.get(p, str(p)) for p in sorted(both))
        return StepResult(
            ok=len(both) >= 2,
            msg=f"privileges reached across both passes: {names or 'none'}. "
                f"Binned by cp_prv, cp_prv_at_step and the stepie cross",
        )
    session.add_step("Record privileges covered", summary)

    session.add_step("Clear dcsr.step", lambda: dm.set_step(False))
    return session
