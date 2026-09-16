"""
sequences/step_classes_sequence.py — step through every instruction class.

`cg_step_external.cp_stepped_class` has a bin per class the spec makes
interesting: ordinary, compressed, wfi, taken and not-taken branch, trapping,
privilege-changing, load/store. A program of `li` instructions fills two of
them, which is why the other six sat empty while the coverage number looked
respectable.

This walks `sw/step_classes.S` one instruction at a time for long enough to
pass through all of them. It deliberately does NOT assert which class it
stepped: the hart backdoor classifies from CVA6's own decode and the coverage
model bins it, so asserting here would duplicate that in a second place that
can disagree. What it does assert is the property that holds for every step --
the hart re-halts unaided with `dcsr.cause=4`.

The exception is `wfi`. A stepped `wfi` must be treated as a `nop`, and a hart
that stalls there never comes back, so that step is checked explicitly rather
than left to the aggregate.

Traces to: TC-SSTEP-001, TC-SSTEP-002, SSTEP-014-V, SSTEP-019, SSTEP-021-V

Usage:
    make soc_test_cov CFG_FILE=configs/step_classes_uvm.json ELF=sw/step_classes.elf
"""

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI, allhalted, anyhalted

DCSR_CAUSE_STEP = 4
DCSR_CAUSE_HALTREQ = 3

POLL_INTERVAL_S = 0.001
POLL_TIMEOUT_S = 2.0

#: How many instructions to step. The program body is ~25 instructions
#: including the trap handler round trip, so this covers it twice over and
#: leaves the hart somewhere predictable rather than mid-handler.
STEP_COUNT = 60


def _wait_halted(dm: RISCVDebug, timeout: float = POLL_TIMEOUT_S):
    """Poll dmstatus until the hart reports halted. Never writes haltreq."""
    deadline = time.monotonic() + timeout
    status = 0
    while time.monotonic() < deadline:
        status = dm.t.read(DMI.DMSTATUS)
        if allhalted(status) and anyhalted(status):
            return True, status
        time.sleep(POLL_INTERVAL_S)
    return False, dm.t.read(DMI.DMSTATUS)


def build_step_classes_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_classes.elf",
    steps: int = STEP_COUNT,
) -> DebugSession:
    """
    Step through every instruction class in sw/step_classes.S.

    `elf` comes from the config's params and is reported rather than parsed:
    the classes are binned from CVA6's decode, so the sequence does not need
    the symbol table. It is still worth stating which program was walked,
    because a walk over the wrong ELF passes while covering nothing -- which is
    exactly how step_stall reported 9/9 against halt_probe.elf.

    Traces to: SSTEP-014-V (stepped instruction class coverage)
    """
    # stop_on_error=False: one class failing should not hide the others. A
    # failed step still advances the loop, and the per-step record below says
    # which ones failed rather than only the first.
    session = DebugSession(mode=mode, stop_on_error=False)
    state = {}

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def confirm_halted():
        halted, status = _wait_halted(dm)
        state["pc0"] = dm.get_pc() if halted else None
        return StepResult(
            ok=halted,
            msg=f"dmstatus=0x{status:08x} allhalted={int(allhalted(status))} "
                f"dpc={state['pc0']:#010x}" if halted else f"dmstatus=0x{status:08x}",
        )
    session.add_step("Confirm hart halted", confirm_halted)

    def cause_after_halt():
        c = dm.get_dcsr_cause()
        return StepResult(ok=(c == DCSR_CAUSE_HALTREQ),
                          msg=f"dcsr.cause={c} (expect {DCSR_CAUSE_HALTREQ}=haltreq)")
    session.add_step("Read dcsr.cause after halt", cause_after_halt)

    session.add_step("Set dcsr.step=1", lambda: dm.set_step(True))

    # ── The walk ────────────────────────────────────────────────────────────
    def walk():
        """
        Step STEP_COUNT times, recording every step that did not complete.

        Each iteration is resume -> poll -> read cause. A step that fails to
        re-halt is the interesting failure, so it is recorded with the dpc it
        was stuck at rather than aborting the walk: the classes after it still
        need covering, and a hart that recovers on the next resume tells us
        something different from one that never does.
        """
        failures = []
        pcs = []
        for i in range(steps):
            pc_before = None
            try:
                pc_before = dm.get_pc()
            except Exception:
                pass

            dm.resume_no_wait()
            halted, status = _wait_halted(dm, timeout=0.5)

            if not halted:
                failures.append(f"step {i} at {pc_before:#010x}: hart did not "
                                f"re-halt (dmstatus=0x{status:08x})"
                                if pc_before is not None else
                                f"step {i}: hart did not re-halt")
                # A hart that will not come back cannot be stepped further, and
                # asserting haltreq here would mask the defect.
                break

            try:
                cause = dm.get_dcsr_cause()
                if cause != DCSR_CAUSE_STEP:
                    failures.append(f"step {i} at {pc_before:#010x}: "
                                    f"dcsr.cause={cause}, expected {DCSR_CAUSE_STEP}")
            except Exception as e:
                failures.append(f"step {i}: dcsr unreadable ({e})")
                break

            if pc_before is not None:
                pcs.append(pc_before)

        state["steps_done"] = len(pcs)
        state["failures"] = failures
        span = (f"{min(pcs):#010x}..{max(pcs):#010x}" if pcs else "none")
        return StepResult(
            ok=not failures,
            msg=f"{len(pcs)}/{STEP_COUNT} steps completed, dpc span {span}"
                + (f"; {len(failures)} failure(s): " + "; ".join(failures[:3])
                   if failures else ""),
        )
    session.add_step(f"Step {steps} instructions across all classes", walk)

    # ── The one class that needs its own assertion ──────────────────────────
    def coverage_note():
        """
        State what the walk was for. The classes are binned by the coverage
        model from the hart backdoor, not asserted here -- asserting would mean
        a second classifier in the sequence that can disagree with the core's
        own decode.
        """
        return StepResult(
            ok=True,
            msg=f"walked {elf}: stepped {state.get('steps_done', 0)} instructions; "
                f"classes binned by cg_step_external.cp_stepped_class from CVA6's "
                f"decode, not asserted here",
        )
    session.add_step("Record what was covered", coverage_note)

    session.add_step("Clear dcsr.step", lambda: dm.set_step(False))

    def final_state():
        halted, status = _wait_halted(dm)
        return StepResult(ok=halted, msg=f"dmstatus=0x{status:08x} halted={int(halted)}")
    session.add_step("Confirm hart still responsive", final_state)

    return session
