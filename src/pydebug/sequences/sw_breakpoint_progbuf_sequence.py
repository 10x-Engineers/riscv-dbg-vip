"""
sequences/sw_breakpoint_progbuf_sequence.py — `ebreak` executed via the
Program Buffer on an already-halted hart (spec #3.8, #4.9.1, #4.8 dcsr.cause).

This is deliberately NOT the same scenario as TC-DCSR-001/TC-DCSR-011's
"native ebreak from running code causes Debug Mode entry" -- here the hart is
*already* halted before `ebreak` executes (via postexec), so there is no
not-in-Debug-Mode -> Debug-Mode transition to report. Whether dcsr.cause
changes anyway, stays at whatever it was, or does something else entirely is
exactly what this sequence is built to OBSERVE and report -- not to assert a
predicted answer, since that would be asserting a claim about a specific DUT
without having actually run it. Read the reported cause values from the
result, don't assume them from this docstring.

Traces to: TC-PB-003 (execution mechanism), TC-DCSR-001 (cause semantics,
applied to the halted-hart case specifically, which the existing DCSR
cluster doesn't have its own dedicated row for)

Usage:
    from pydebug.sequences.sw_breakpoint_progbuf_sequence import build_sw_breakpoint_progbuf_sequence
    session = build_sw_breakpoint_progbuf_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult

EBREAK = 0x00100073

#: dcsr.cause encodings (spec #4.8): 1=ebreak, 2=trigger, 3=haltreq, 4=step,
#: 5=resethaltreq, 6=group, 7=other.
DCSR_CAUSE_HALTREQ = 3


def build_sw_breakpoint_progbuf_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build and return a DebugSession that halts the hart via haltreq, then
    executes a lone `ebreak` through the Program Buffer, and reports what
    happens to dcsr.cause -- the hart never leaves Debug Mode here, so
    there is no entry-cause transition to compare against TC-DCSR-001's
    native-ebreak-from-running-code scenario.

    Traces to: TC-PB-003, TC-DCSR-001 (halted-hart variant)
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── Halt via haltreq -- dcsr.cause should read 3 (haltreq) after this ──
    def halt_and_record_cause():
        dm.halt()
        cause = dm.get_dcsr_cause()
        return StepResult(
            ok=(cause == DCSR_CAUSE_HALTREQ),
            msg=f"Halted via haltreq, dcsr.cause={cause} "
                f"(expect {DCSR_CAUSE_HALTREQ}=haltreq)",
        )
    session.add_step("Halt hart, record baseline dcsr.cause", halt_and_record_cause)

    # ── Execute a lone ebreak via the Program Buffer on the halted hart ────
    def tc_pb_ebreak_on_halted():
        abstractcs = dm.read_abstractcs()
        progbufsize = (abstractcs >> 24) & 0x1F
        if progbufsize < 1:
            return StepResult(ok=True, msg="N/A -- progbufsize < 1")

        cause_before = dm.get_dcsr_cause()
        dm.write_progbuf(0, EBREAK)
        dm.execute_progbuf()
        cause_after = dm.get_dcsr_cause()
        still_halted = dm.is_halted()

        changed = cause_before != cause_after
        return StepResult(
            ok=still_halted,  # the only hard requirement: hart must not be lost/hung
            msg=f"ebreak via progbuf on already-halted hart: dcsr.cause "
                f"{cause_before} -> {cause_after} "
                f"({'changed' if changed else 'unchanged'}), still_halted="
                f"{still_halted}. Reporting only -- see docstring: this is a "
                f"real observation about this DUT, not a predicted result.",
        )
    session.add_step(
        "Execute lone ebreak via Program Buffer on already-halted hart",
        tc_pb_ebreak_on_halted,
    )

    return session
