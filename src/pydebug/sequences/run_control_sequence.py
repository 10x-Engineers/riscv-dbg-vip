"""
sequences/run_control_sequence.py — Halt / Resume individual hart.

Implements the Halt/Resume individual hart CAT2 feature (Ch.3 op 2, spec #3.5),
`dmcontrol.haltreq`/`resumereq`, `dmstatus.allhalted`/`anyhalted`/`allrunning`/
`anyrunning` (#3.14.2 / #3.14.1).

Traces to: TC-RC-001, TC-RC-002, TC-RC-003, TC-RC-004, TC-RC-005, TC-RC-006,
TC-RC-007

Every check compares the observed dmstatus word against `DMPredictor.expect()`
when the attached transport carries one (`ModelBackedMockTransport`); against a
real simulator/hardware transport (no `.predictor` attribute) the same steps
still run and still check the architectural relationship the TC-ID asks for —
they just cannot cross-check against the golden model on top of that.

Usage:
    from pydebug.sequences.run_control_sequence import build_run_control_sequence
    session = build_run_control_sequence(dm, mode="batch")
    session.run()
"""

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult, DMI
from pydebug.api.riscv_dm import (
    allhalted, anyhalted, allrunning, anyrunning,
    allresumeack, anyresumeack,
)

#: Spec #3.5: "When halt or resume is requested, a hart must respond in less
#: than one second". This is the spec's own number, not an invented bound —
#: TC-RC-006's "Priority P2" latency check is this sentence and nothing else.
HALT_RESUME_RESPONSE_BOUND_S = 1.0


def _predictor(dm: RISCVDebug):
    """The golden-reference predictor backing this transport, if any.

    Only `ModelBackedMockTransport` carries one; a real UVM/OpenOCD transport
    does not, and every step below must therefore also make sense with this
    returning None (see module docstring).
    """
    return getattr(dm.t, "predictor", None)


def build_run_control_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    hartsel: int = 0,
    **params,
) -> DebugSession:
    """
    Build and return a DebugSession exercising Halt/Resume (spec #3.5).
    The session is NOT run yet — call session.run() when ready.

    Traces to: TC-RC-001, TC-RC-002, TC-RC-003, TC-RC-004, TC-RC-005, TC-RC-006,
    TC-RC-007

    Args:
        dm:      RISCVDebug instance (already has transport attached)
        mode:    "batch" or "interactive"
        hartsel: which hart to exercise (default 0 — the reset-value selection)
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    # Baseline observation before activation: spec #3.13 Version Detection is
    # explicit that dmstatus.version is "the very first thing a debugger reads
    # to decide the DM exists at all," and #3.14.2 dmactive=0 documents that
    # version "might not return correct data" in that state (typically 0, "no
    # Debug Module present"). Reading here, before dmcontrol.dmactive is ever
    # written, is what actually exercises that state — dm.activate() itself
    # writes dmactive=1 before its own dmstatus read, so no later step ever
    # observes dmactive=0.
    session.add_step(
        "Read dmstatus before DM activation (dmactive=0 baseline, spec #3.13/#3.14.2)",
        lambda: StepResult(ok=True, msg=f"pre-activation dmstatus={dm.read_dmstatus():#010x}"),
    )

    session.add_step(
        "Activate Debug Module (write dmcontrol.dmactive=1)",
        lambda: dm.activate(),
    )
    if hartsel:
        session.add_step(
            f"Select hart {hartsel} (write dmcontrol.hartsel)",
            lambda: dm.select_hart(hartsel),
        )

    # ── TC-RC-001: halt request on a running hart ─────────────────────────
    def tc_rc_001():
        dm.halt()
        word = dm.read_dmstatus()
        observed = anyhalted(word) and allhalted(word) and not anyrunning(word)
        p = _predictor(dm)
        if p is not None:
            predicted = p.expect(DMI.DMSTATUS)
            observed = observed and (anyhalted(predicted) and allhalted(predicted))
        return StepResult(
            ok=observed,
            msg=f"TC-RC-001: dmstatus after haltreq — anyhalted={anyhalted(word)} "
                f"allhalted={allhalted(word)} anyrunning={anyrunning(word)}",
        )
    session.add_step(
        "TC-RC-001: halt request on a running hart (write dmcontrol.haltreq=1)",
        tc_rc_001,
    )

    # ── TC-RC-002: halt request ignored once already halted ───────────────
    def tc_rc_002():
        before = dm.read_dmstatus()
        # Spec #3.5: "Halted harts ignore their halt request bit." Write
        # haltreq=1 again directly (dm.halt() would just poll-and-clear, which
        # cannot distinguish "ignored" from "re-halted" the way a raw write can).
        dm.write_dmcontrol(haltreq=True)
        after = dm.read_dmstatus()
        no_change = (
            allhalted(after) == allhalted(before)
            and anyhalted(after) == anyhalted(before)
            and allresumeack(after) == allresumeack(before)
        )
        # Leave haltreq deasserted so subsequent steps start clean.
        dm.write_dmcontrol(haltreq=False)
        return StepResult(
            ok=no_change and allhalted(after),
            msg=f"TC-RC-002: re-asserting haltreq on an already-halted hart left "
                f"allhalted={allhalted(after)} unchanged, resume ack unchanged",
        )
    session.add_step(
        "TC-RC-002: haltreq ignored once already halted (spec #3.5)",
        tc_rc_002,
    )

    # ── TC-RC-003: resume request on a halted hart ────────────────────────
    def tc_rc_003():
        dm.resume()
        word = dm.read_dmstatus()
        observed = (
            anyrunning(word) and allrunning(word)
            and not anyhalted(word)
            and allresumeack(word) and anyresumeack(word)
        )
        p = _predictor(dm)
        if p is not None:
            predicted = p.expect(DMI.DMSTATUS)
            observed = observed and allrunning(predicted) and allresumeack(predicted)
        return StepResult(
            ok=observed,
            msg=f"TC-RC-003: dmstatus after resumereq — allrunning={allrunning(word)} "
                f"allresumeack={allresumeack(word)} anyhalted={anyhalted(word)}",
        )
    session.add_step(
        "TC-RC-003: resume request on a halted hart (write dmcontrol.resumereq=1)",
        tc_rc_003,
    )

    # ── TC-RC-004: resume request ignored on a running hart ───────────────
    def tc_rc_004():
        # Precondition: hart is running from TC-RC-003. resumereq on a running
        # hart is a no-op on run state, but #3.5 still clears resume ack for
        # every selected hart with nothing to re-set it (the documented
        # asymmetry) — anyresumeack must therefore drop to 0.
        dm.write_dmcontrol(resumereq=True)
        word = dm.read_dmstatus()
        observed = allrunning(word) and not anyhalted(word) and not anyresumeack(word)
        dm.write_dmcontrol(resumereq=False)
        return StepResult(
            ok=observed,
            msg=f"TC-RC-004: resumereq on a running hart — allrunning={allrunning(word)} "
                f"(unchanged), anyresumeack={anyresumeack(word)} (cleared, per #3.5's "
                f"resume-ack-cleared-for-every-selected-hart rule)",
        )
    session.add_step(
        "TC-RC-004: resumereq ignored on a running hart (spec #3.5)",
        tc_rc_004,
    )

    # ── TC-RC-005: resumereq ignored when haltreq also set ────────────────
    def tc_rc_005():
        # Precondition: running (from TC-RC-004). Capture resume ack before —
        # #3.14.2: "resumereq is ignored if haltreq is set", so this write must
        # neither resume the hart nor touch resume ack at all.
        before = dm.read_dmstatus()
        ack_before = anyresumeack(before)
        dm.write_dmcontrol(haltreq=True, resumereq=True)
        after = dm.read_dmstatus()
        observed = (
            anyhalted(after) and not anyrunning(after)
            and anyresumeack(after) == ack_before
        )
        dm.write_dmcontrol(haltreq=False)
        return StepResult(
            ok=observed,
            msg=f"TC-RC-005: haltreq=1,resumereq=1 in one write — anyhalted={anyhalted(after)} "
                f"(haltreq wins), anyresumeack unchanged ({ack_before} -> {anyresumeack(after)})",
        )
    session.add_step(
        "TC-RC-005: resumereq ignored when haltreq set in the same write (spec #3.14.2)",
        tc_rc_005,
    )

    # ── TC-RC-006: halt/resume response latency ───────────────────────────
    def tc_rc_006():
        t0 = time.perf_counter()
        dm.halt()
        halt_latency = time.perf_counter() - t0
        t0 = time.perf_counter()
        dm.resume()
        resume_latency = time.perf_counter() - t0
        ok = (
            halt_latency < HALT_RESUME_RESPONSE_BOUND_S
            and resume_latency < HALT_RESUME_RESPONSE_BOUND_S
        )
        return StepResult(
            ok=ok,
            msg=f"TC-RC-006: halt latency={halt_latency*1e3:.3f}ms, "
                f"resume latency={resume_latency*1e3:.3f}ms "
                f"(spec bound: <{HALT_RESUME_RESPONSE_BOUND_S}s, #3.5)",
        )
    session.add_step(
        "TC-RC-006: halt/resume response latency under spec's 1s bound (#3.5)",
        tc_rc_006,
    )

    # ── TC-RC-007: resumereq while the hart is in reset ───────────────────
    def tc_rc_007():
        # Precondition: running (TC-RC-006 left it resumed). Hold the hart in
        # reset via ndmreset. #3.2 leaves which of the four DM states
        # (non-existent/unavailable/running/halted) a resetting hart reports
        # as "implementation dependent" — both project DUTs' dm_csrs.sv
        # compute allrunning/anyrunning combinationally as
        # ~halted & ~unavailable, so a hart held in ndmreset (halted forced
        # 0) reads running=1 throughout the window, not "neither" (confirmed
        # against real RTL, riscv-dbg-vip#117 investigation, 2026-07-25 —
        # this step used to assert running=False, which was itself the bug).
        # What #3.5 actually constrains is resumereq's *effect*: "each
        # selected, HALTED hart is sent a resume request" — a hart that was
        # never halted (as here) must not spuriously become halted, and its
        # resume-ack must not spuriously set, matching TC-RC-004's identical
        # rule for "resumereq on a running hart."
        dm.ndmreset(True)
        # write_dmcontrol()'s unset fields default to 0/False (dmcontrol writes
        # are absolute, not incremental) — ndmreset must be passed explicitly
        # here or this write silently deasserts it, releasing the hart from
        # reset before resumereq's effect (or lack of one) can be observed.
        dm.write_dmcontrol(resumereq=True, ndmreset=True)
        word = dm.read_dmstatus()
        no_spurious_halt = not anyhalted(word) and not anyresumeack(word)
        dm.write_dmcontrol(resumereq=False, ndmreset=True)
        dm.ndmreset(False)
        return StepResult(
            ok=no_spurious_halt,
            msg=f"TC-RC-007: resumereq written while in ndmreset — "
                f"anyhalted={anyhalted(word)} anyresumeack={anyresumeack(word)} "
                f"(expected both False: resumereq only affects a HALTED hart, "
                f"#3.5; this hart was never halted while in reset, #3.2)",
        )
    session.add_step(
        "TC-RC-007: resumereq while the hart is in reset (spec #3.2)",
        tc_rc_007,
    )

    return session
