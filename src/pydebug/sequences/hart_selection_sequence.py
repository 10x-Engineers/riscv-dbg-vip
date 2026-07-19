"""
sequences/hart_selection_sequence.py — Hart Selection (hasel, hartsello, hartselhi).

Implements the single-field level of the Hart Selection CAT2 feature (Ch.3 op
9's mechanism, spec #3.14.2 hartsel/hasel). The hart-array-mask register
content itself (`hawindowsel`/`hawindow`) is a separate, not-yet-started slice
— this covers only what a single `dmcontrol` write/read can exercise.

Traces to: TC-HS-001, TC-HS-002, TC-HS-003

Usage:
    from pydebug.sequences.hart_selection_sequence import build_hart_selection_sequence
    session = build_hart_selection_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import (
    dmcontrol_hartsel, dmcontrol_hasel,
    allnonexistent, anynonexistent,
)

#: Spec #3.14.2 hartsel: "the spec allows for 20 hartsel bits ... an
#: implementation may choose to implement fewer." Writing all-1s across the
#: full 20-bit field and reading back which bits stuck is the spec's own
#: documented method for discovering the actual HARTSELLEN.
HARTSEL_ALL_ONES = (1 << 20) - 1

#: A hartsel value chosen to be very likely beyond any real implementation's
#: hart count, without colliding with the all-ones discovery write above (that
#: write means something different: HARTSELLEN discovery, not nonexistent-hart
#: selection). Not a spec-defined constant — just "large and distinct."
LIKELY_NONEXISTENT_HARTSEL = HARTSEL_ALL_ONES - 1


def _predictor(dm: RISCVDebug):
    """The golden-reference predictor backing this transport, if any (see
    run_control_sequence.py's identical helper for the full rationale)."""
    return getattr(dm.t, "predictor", None)


def build_hart_selection_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    **params,
) -> DebugSession:
    """
    Build and return a DebugSession exercising Hart Selection (spec #3.14.2).
    The session is NOT run yet — call session.run() when ready.

    Traces to: TC-HS-001, TC-HS-002, TC-HS-003
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-HS-001: HARTSELLEN discovery (WARL) ────────────────────────────
    def tc_hs_001():
        dm.write_dmcontrol(hartsel=HARTSEL_ALL_ONES)
        readback = dmcontrol_hartsel(dm.read_dmcontrol())
        # Whatever comes back IS the DUT's actual HARTSELLEN-implemented mask
        # — there is no "expected" value to assert beyond "the write/read
        # round-trip itself completed," per the spec's own discovery framing.
        dm.write_dmcontrol(hartsel=0)  # restore hart 0 selected for later steps
        return StepResult(
            ok=True,
            msg=f"TC-HS-001: wrote hartsel=all-1s (0x{HARTSEL_ALL_ONES:05x}), "
                f"read back 0x{readback:05x} — this DUT's implemented HARTSELLEN "
                f"mask, per spec #3.14.2's own discovery method",
        )
    session.add_step(
        "TC-HS-001: HARTSELLEN discovery (write all-1s to hartsel, read back)",
        tc_hs_001,
    )

    # ── TC-HS-002: nonexistent hart index selected ────────────────────────
    def tc_hs_002():
        dm.write_dmcontrol(hartsel=LIKELY_NONEXISTENT_HARTSEL)
        word = dm.read_dmstatus()
        observed_any = anynonexistent(word)
        observed_all = allnonexistent(word)
        p = _predictor(dm)
        if p is not None:
            # The model knows num_harts; a real DUT's actual hart count is not
            # otherwise discoverable from this sequence alone, so only assert
            # the expected value when a golden model is attached.
            ok = observed_any and observed_all
        else:
            ok = True  # informational only against a real transport
        dm.write_dmcontrol(hartsel=0)
        return StepResult(
            ok=ok,
            msg=f"TC-HS-002: selected hartsel={LIKELY_NONEXISTENT_HARTSEL} — "
                f"dmstatus.anynonexistent={observed_any} allnonexistent={observed_all} "
                f"(#3.14.1)",
        )
    session.add_step(
        "TC-HS-002: nonexistent hart index selected (spec #3.14.1 anynonexistent)",
        tc_hs_002,
    )

    # ── TC-HS-003: hasel discovery write ──────────────────────────────────
    def tc_hs_003():
        # Spec #3.14.2 hasel: "A debugger which wishes to use the hart array
        # mask register feature should set this bit and read back to see if
        # the functionality is supported." Whatever comes back is the answer
        # — 1 means the mask register exists, 0 means it's WARL-tied.
        dm.write_dmcontrol(hasel=True)
        supported = dmcontrol_hasel(dm.read_dmcontrol())
        dm.write_dmcontrol(hasel=False)
        return StepResult(
            ok=True,
            msg=f"TC-HS-003: wrote hasel=1, read back hasel={supported} — "
                f"{'hart array mask register present' if supported else 'not implemented (WARL-tied to 0)'}",
        )
    session.add_step(
        "TC-HS-003: hasel discovery write (spec #3.14.2)",
        tc_hs_003,
    )

    return session
