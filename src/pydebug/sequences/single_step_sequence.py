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
from pydebug.api.riscv_dm import DMI, allhalted, anyhalted

#: dcsr.cause encoding for "single-step" (spec #4.8).
DCSR_CAUSE_STEP = 4

#: dcsr.cause encoding for an external halt request (spec #4.8).
DCSR_CAUSE_HALTREQ = 3

POLL_INTERVAL_S = 0.001
POLL_TIMEOUT_S = 2.0


def _wait_halted(dm: RISCVDebug, timeout: float = POLL_TIMEOUT_S):
    """
    Poll dmstatus until both allhalted and anyhalted are set.

    Never writes haltreq: the point is to observe the hart's own state, not to
    put it where we want it. Returns (halted, dmstatus) so the caller can report
    the value it actually saw rather than just a verdict.
    """
    deadline = time.monotonic() + timeout
    status = 0
    while time.monotonic() < deadline:
        status = dm.t.read(DMI.DMSTATUS)
        if allhalted(status) and anyhalted(status):
            return True, status
        time.sleep(POLL_INTERVAL_S)
    status = dm.t.read(DMI.DMSTATUS)
    return (allhalted(status) and anyhalted(status)), status


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

    # ── Confirm the halt from dmstatus ──────────────────────────────────────
    def confirm_halted():
        halted, status = _wait_halted(dm)
        return StepResult(
            ok=halted,
            msg=f"dmstatus=0x{status:08x} allhalted={int(allhalted(status))} "
                f"anyhalted={int(anyhalted(status))}",
        )
    session.add_step("Confirm hart halted (dmstatus allhalted/anyhalted)", confirm_halted)

    # ── Cause after the halt request ────────────────────────────────────────
    # Captured before step is written, so the read after the step has something
    # to be compared against.
    causes = {}

    def cause_after_halt():
        causes["pc_before"] = dm.get_pc()
        causes["halt"] = dm.get_dcsr_cause()
        return StepResult(
            ok=(causes["halt"] == DCSR_CAUSE_HALTREQ),
            msg=f"dcsr.cause={causes['halt']} (expect {DCSR_CAUSE_HALTREQ}=haltreq)",
        )
    session.add_step("Read dcsr.cause after halt request", cause_after_halt)

    # ── Set single step ─────────────────────────────────────────────────────
    session.add_step("Set dcsr.step=1", lambda: dm.set_step(True))

    # dcsr.step acts "when set and not in Debug Mode" (spec, dcsr.step), so the
    # armed bit does nothing until the hart leaves. resumereq is what makes it
    # leave -- the hart executes dret, retires exactly one instruction, and
    # re-enters Debug Mode on its own with dcsr.cause=4.
    #
    # resume_no_wait(), not resume(): resume() polls dmstatus.allrunning, and a
    # single step re-halts too quickly for allrunning to be a reliable
    # observable in between (issue #105). The autonomous re-halt is polled for
    # in the next step instead, and no haltreq is ever written -- the hart
    # halting itself is the property under test.
    session.add_step("Resume (resumereq) to let the step execute",
                     lambda: dm.resume_no_wait())

    # ── Wait for halted again, then read the cause ──────────────────────────
    def wait_halted_after_step():
        halted, status = _wait_halted(dm)
        return StepResult(
            ok=halted,
            msg=f"dmstatus=0x{status:08x} allhalted={int(allhalted(status))} "
                f"anyhalted={int(anyhalted(status))}",
        )
    session.add_step("Wait for dmstatus allhalted and anyhalted", wait_halted_after_step)

    def cause_after_step():
        causes["step"] = dm.get_dcsr_cause()
        cause = causes["step"]
        # Must be 4 (step). A 3 here means the hart re-entered Debug Mode for
        # the original halt request and never stepped at all -- the failure
        # this test exists to catch, and one that reports as a pass if the
        # cause is merely printed rather than checked.
        note = ""
        if cause == DCSR_CAUSE_HALTREQ:
            note = " -- still the halt request: the hart never stepped"
        return StepResult(
            ok=(cause == DCSR_CAUSE_STEP),
            msg=f"dcsr.cause={cause} after step "
                f"(expect {DCSR_CAUSE_STEP}=step; was {causes.get('halt')} "
                f"after halt request){note}",
        )
    session.add_step("Read dcsr.cause after single step", cause_after_step)

    # ── PC at the end of the test ───────────────────────────────────────────
    # dpc holds the M-mode PC the hart was executing when it entered Debug
    # Mode -- i.e. where it will resume to. With the ELF running this should be
    # inside the loaded program at DRAMBase (0x8000_0000), not the bootrom; a
    # bootrom address here means the hart never reached the test program.
    def read_pc_at_end():
        pc = dm.get_pc()
        before = causes.get("pc_before")
        delta = None if before is None else (pc - before)
        # The program loops over 31 two-byte writes, so a step that executed
        # shows up here as the PC advancing by exactly one instruction. If
        # setting dcsr.step alone stepped the hart, this delta would be 2 (or
        # the loop's wrap); if nothing executed, the PC is unchanged.
        return StepResult(
            ok=True,
            msg=f"dpc before={before:#010x} after={pc:#010x} "
                f"delta={delta:+d} bytes -> "
                f"{'hart executed' if delta else 'hart did NOT execute'}",
        )
    session.add_step("Read PC (dpc) at end of test", read_pc_at_end)

    return session
