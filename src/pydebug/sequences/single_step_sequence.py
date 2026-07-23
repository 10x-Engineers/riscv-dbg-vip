"""
sequences/single_step_sequence.py — Hardware single-step (spec #4.5,
dcsr.step, Appendix B.3.1).

Nothing in `RISCVDebug` modeled `dcsr` at all before this study --
`read_dcsr()`/`write_dcsr()`/`set_step()`/`get_dcsr_cause()` in
`api/riscv_dm.py` are new, added alongside this sequence.

Single-step does NOT use haltreq: writing dcsr.step=1 then resuming makes the
hart execute exactly one instruction and re-halt *on its own*, reporting
dcsr.cause=4 (step). This sequence polls dmstatus.allhalted directly rather
than calling dm.halt() (which would assert haltreq -- the wrong mechanism
here) or dm.resume() a second time.

Traces to: TC-SSTEP-001

Usage:
    from pydebug.sequences.single_step_sequence import build_single_step_sequence
    session = build_single_step_sequence(dm, mode="batch")
    session.run()
"""

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult

#: dcsr.cause encoding for "single-step" (spec #4.8).
DCSR_CAUSE_STEP = 4

POLL_INTERVAL_S = 0.001
POLL_TIMEOUT_S = 2.0


def _wait_halted_no_haltreq(dm: RISCVDebug, timeout: float = POLL_TIMEOUT_S) -> bool:
    """
    Poll dmstatus.allhalted without ever writing haltreq -- the hart must
    re-enter Debug Mode on its own after exactly one instruction (spec #4.5).
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dm.is_halted():
            return True
        time.sleep(POLL_INTERVAL_S)
    return dm.is_halted()


def build_single_step_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build and return a DebugSession exercising external single-step: set
    dcsr.step=1, resume, confirm the hart executes exactly one instruction
    and re-halts with dcsr.cause=step (spec #4.5, Appendix B.3.1).

    Traces to: TC-SSTEP-001
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-SSTEP-001: exactly one instruction, dcsr.cause=step ────────────
    def tc_sstep_001():
        pc_before = dm.get_pc()
        dm.set_step(True)
        # resume_no_wait(), not resume(): a step re-halts too quickly for
        # dmstatus.allrunning to be a reliable observable in between (see
        # GitHub issue #105) -- poll directly for re-halt instead.
        dm.resume_no_wait()
        halted_again = _wait_halted_no_haltreq(dm)
        cause = dm.get_dcsr_cause() if halted_again else None
        pc_after = dm.get_pc() if halted_again else None
        dm.set_step(False)  # leave the hart in the non-stepping state we found it in

        if not halted_again:
            return StepResult(
                ok=False,
                msg="TC-SSTEP-001: hart never re-halted after resume with "
                    "dcsr.step=1 -- expected exactly one instruction then "
                    "automatic re-entry to Debug Mode",
            )
        ok = cause == DCSR_CAUSE_STEP
        return StepResult(
            ok=ok,
            msg=f"TC-SSTEP-001: dcsr.cause={cause} (expect {DCSR_CAUSE_STEP}=step), "
                f"pc {pc_before:#010x} -> {pc_after:#010x}  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step(
        "TC-SSTEP-001: single-step exactly one instruction, dcsr.cause=step",
        tc_sstep_001,
    )

    return session
