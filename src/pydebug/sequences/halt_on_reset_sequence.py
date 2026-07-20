"""
sequences/halt_on_reset_sequence.py — Halt-on-reset (Ch.3 op 6, spec #3.5, Optional).

Driven through `dmcontrol.setresethaltreq`/`clrresethaltreq`, gated by
`dmstatus.hasresethaltreq` (#3.14.1/#3.14.2).

Traces to: TC-HOR-001, TC-HOR-002, TC-HOR-003, TC-HOR-004, TC-HOR-005

TC-HOR-001 is a **gate**, per the test plan: "If [hasresethaltreq is] 0,
mechanism not implemented — remaining HOR cases are N/A for this DUT, not
failures." That gate result is captured in `_state` and every later step
checks it first, reporting `ok=True` with an explicit N/A message rather than
attempting hardware actions the DUT does not implement (CVA6's dm_csrs.sv:235
hardwires hasresethaltreq to 0, which is exactly the case this exists for).

TC-HOR-005 (the mutex-bit negative test) is deliberately NOT gated on
hasresethaltreq: the "at most one mutex bit per write" rule (#3.14.2) applies
to dmcontrol in general, independent of whether halt-on-reset itself is
implemented, so it is exercised unconditionally.

Usage:
    from pydebug.sequences.halt_on_reset_sequence import build_halt_on_reset_sequence
    session = build_halt_on_reset_sequence(dm, mode="batch", num_harts=2)
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult, DMI
from pydebug.api.riscv_dm import allhalted, anyhalted, hasresethaltreq


def _predictor(dm: RISCVDebug):
    """See run_control_sequence.py's identical helper for the full rationale."""
    return getattr(dm.t, "predictor", None)


def build_halt_on_reset_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    num_harts: int = 1,
    **params,
) -> DebugSession:
    """
    Build and return a DebugSession exercising Halt-on-reset (spec #3.5).
    The session is NOT run yet — call session.run() when ready.

    Traces to: TC-HOR-001, TC-HOR-002, TC-HOR-003, TC-HOR-004, TC-HOR-005

    Args:
        dm:        RISCVDebug instance (already has transport attached)
        mode:      "batch" or "interactive"
        num_harts: implemented hart count, needed only by TC-HOR-004's
            per-hart-independence check — no SoC-specific value is hardcoded
            here, the caller states what the DUT actually implements.
    """
    session = DebugSession(mode=mode, stop_on_error=False)
    #: Shared across closures: the TC-HOR-001 gate result, so every later step
    #: can report N/A instead of attempting hardware the DUT does not implement.
    state = {"has_resethaltreq": None}

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-HOR-001: discover halt-on-reset support (gate) ─────────────────
    def tc_hor_001():
        word = dm.read_dmstatus()
        supported = hasresethaltreq(word)
        state["has_resethaltreq"] = supported
        return StepResult(
            ok=True,  # discovery always "passes" — the *value* is the finding
            msg=f"TC-HOR-001: dmstatus.hasresethaltreq={int(supported)} — "
                f"{'halt-on-reset implemented' if supported else 'NOT implemented; TC-HOR-002..005 are N/A for this DUT (spec #3.5, Optional)'}",
        )
    session.add_step(
        "TC-HOR-001: discover halt-on-reset support (dmstatus.hasresethaltreq)", tc_hor_001,
    )

    def _na(tc_id: str) -> StepResult:
        return StepResult(
            ok=True,
            msg=f"{tc_id}: N/A — dmstatus.hasresethaltreq=0 on this DUT "
                f"(gated by TC-HOR-001, per spec #3.5's Optional halt-on-reset)",
        )

    # ── TC-HOR-002: setresethaltreq causes halt-on-reset ──────────────────
    def tc_hor_002():
        if not state["has_resethaltreq"]:
            return _na("TC-HOR-002")
        dm.set_reset_haltreq()
        dm.ndmreset(True)
        dm.read_dmstatus()  # observe the in-reset window before releasing
        dm.ndmreset(False)
        word = dm.read_dmstatus()
        ok = anyhalted(word) and allhalted(word)
        p = _predictor(dm)
        if p is not None:
            predicted = p.expect(DMI.DMSTATUS)
            ok = ok and allhalted(predicted)
        return StepResult(
            ok=ok,
            msg=f"TC-HOR-002: setresethaltreq + reset cycle — allhalted={allhalted(word)} "
                f"(spec #3.5: hart enters Debug Mode immediately on reset deassertion, "
                f"regardless of reset cause)",
        )
    session.add_step(
        "TC-HOR-002: setresethaltreq causes halt-on-reset (spec #3.5)", tc_hor_002,
    )

    # ── TC-HOR-003: clrresethaltreq clears the request ────────────────────
    def tc_hor_003():
        if not state["has_resethaltreq"]:
            return _na("TC-HOR-003")
        dm.clr_reset_haltreq()
        dm.ndmreset(True)
        dm.ndmreset(False)
        word = dm.read_dmstatus()
        ok = not anyhalted(word)
        return StepResult(
            ok=ok,
            msg=f"TC-HOR-003: clrresethaltreq + reset cycle — anyhalted={anyhalted(word)} "
                f"(expected False: the hart must run normally, not halt on reset)",
        )
    session.add_step(
        "TC-HOR-003: clrresethaltreq clears the halt-on-reset request (spec #3.14.2)", tc_hor_003,
    )

    # ── TC-HOR-004: per-hart independence ─────────────────────────────────
    def tc_hor_004():
        if not state["has_resethaltreq"]:
            return _na("TC-HOR-004")
        if num_harts < 2:
            return StepResult(
                ok=True,
                msg="TC-HOR-004: N/A — this DUT/config implements only 1 hart "
                    "(num_harts param); per-hart independence needs >= 2 harts "
                    "to be meaningful, per the testplan's own multi-hart framing",
            )
        hart_a, hart_b = 0, num_harts - 1
        # Configure hart_a for halt-on-reset; hart_b is left untouched, per the
        # test plan's design rationale for why set/clrresethaltreq are two
        # separate write-only bits: "per-hart halt-on-reset config can change
        # without disturbing other selected harts."
        dm.select_hart(hart_a)
        dm.set_reset_haltreq()
        dm.select_hart(hart_b)  # select only — no action bit written for hart_b

        dm.ndmreset(True)
        dm.ndmreset(False)

        dm.select_hart(hart_a)
        a_halted = anyhalted(dm.read_dmstatus())
        dm.select_hart(hart_b)
        b_halted = anyhalted(dm.read_dmstatus())

        # Clean up hart_a's standing request so later runs of this sequence
        # against the same predictor/DUT session start from a known state.
        dm.select_hart(hart_a)
        dm.clr_reset_haltreq()

        ok = a_halted and not b_halted
        return StepResult(
            ok=ok,
            msg=f"TC-HOR-004: hart {hart_a} (setresethaltreq) halted={a_halted}, "
                f"hart {hart_b} (untouched) halted={b_halted} after a shared reset cycle",
        )
    session.add_step(
        "TC-HOR-004: per-hart independence of set/clrresethaltreq (spec #3.14.2)", tc_hor_004,
    )

    # ── TC-HOR-005: illegal simultaneous bit writes (negative, ungated) ───
    def tc_hor_005():
        # #3.14.2: "a debugger may only write 1 to at most one of the
        # following bits: resumereq, hartreset, ackhavereset, setresethaltreq,
        # clrresethaltreq." This deliberately breaks that rule with two of
        # them (resumereq, hartreset) in a single write and checks only that
        # the DM survives it and stays in a queryable state — the spec places
        # no constraint on the DM's response to an illegal debugger write, so
        # there is no specific resulting value to assert (see
        # invariants.INV-STIM-DMCONTROL-MUTEX, a stimulus-legality finding,
        # not a DUT one).
        dm.write_dmcontrol(resumereq=True, hartreset=True)
        dm.write_dmcontrol(resumereq=False, hartreset=False)
        readback = dm.read_dmcontrol()
        status = dm.read_dmstatus()
        alive = bool(readback & 1)  # dmactive still 1
        from pydebug.api.riscv_dm import version
        responsive = version(status) != 0
        return StepResult(
            ok=alive and responsive,
            msg=f"TC-HOR-005: wrote resumereq=1,hartreset=1 simultaneously "
                f"(illegal per #3.14.2) — DM state not corrupted "
                f"(dmactive={alive}, dmstatus.version={version(status)})",
        )
    session.add_step(
        "TC-HOR-005: illegal simultaneous dmcontrol mutex-bit write (spec #3.14.2, negative)",
        tc_hor_005,
    )

    return session
