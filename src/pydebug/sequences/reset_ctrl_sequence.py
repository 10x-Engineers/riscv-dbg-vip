"""
sequences/reset_ctrl_sequence.py — Reset signal / debug from first instruction.

Implements the Reset Control CAT2 feature (Ch.3 op 5, spec #3.2), driven through
`dmcontrol.ndmreset`/`hartreset`, and observed through `dmstatus.allhavereset`/
`anyhavereset`/`ackhavereset` (#3.14.2).

Traces to: TC-RST-001, TC-RST-002, TC-RST-003, TC-RST-004, TC-RST-005,
TC-RST-006

A DUT-specific gap is handled honestly rather than papered over:

  * TC-RST-002 (`hartreset`) is discovery, per spec #3.14.2's own instruction:
    "If this feature is not implemented, the bit always stays 0." The sequence
    writes 1 and reads back; if it did not stick, the rest of that step reports
    N/A rather than a failure -- confirmed WARL-tied to 0 on **both** project
    DUTs (`dm_csrs.sv`'s `dmcontrol_d.hartreset = 1'b0` is unconditional on
    each, not CVA6-specific), so it always reports N/A currently. This also
    means `dut_configs/*.json`'s `supports_hartreset` must stay `false` for
    both -- the golden model needs to agree hartreset is a no-op, or its own
    `dmcontrol` prediction diverges from real RTL on this bit.

  * TC-RST-001's `ndmresetpending` clause is checked against the golden model
    (`DMPredictor`), not the DUT read-back, when a predictor is attached: some
    v0.13 `dm_pkg` implementations (CVA6's `dm_pkg.sv` `dmstatus_t`) have no
    such field at all, so a DUT read-back of that bit is not meaningful there.

Not a gap, but worth noting: both DUTs' `dm_csrs.sv` compute
`allrunning = ~halted & ~unavailable` combinationally, so a hart held in
ndmreset reads `running=1` throughout the reset window, not "neither" --
confirmed against real RTL and now the golden model's own prediction too
(spec #3.2 leaves "which states a hart that is reset goes through" explicitly
implementation dependent).

A second, real DUT-specific gap, found the hard way (a real CVA6 UVM
timeout, 2026-07-25): `cross.hart_state_transition.halted_to_in_reset`
cannot currently be produced via *any* stimulus on either DUT. Not via
`hartreset` (WARL-tied to 0, above). Not via `ndmreset` either: both DUTs'
`dm_mem.sv` only resets `halted_q` on `!rst_ni` (the DM's own reset) --
`ndmreset` deliberately does not touch the DM's own registers (that's the
whole point: the debugger stays in control while the target resets), so a
hart that was already halted stays reported as halted throughout an
`ndmreset` cycle, completely unaffected by it. This bin is excluded in
`model/coverage.py` with this citation rather than forced with stimulus
that doesn't actually produce the transition.

Usage:
    from pydebug.sequences.reset_ctrl_sequence import build_reset_ctrl_sequence
    session = build_reset_ctrl_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult, DMI
from pydebug.api.riscv_dm import (
    DebugError,
    allhalted, anyhalted, allrunning, anyrunning,
    allhavereset, anyhavereset, ndmresetpending,
    dmcontrol_hartreset,
)


def _predictor(dm: RISCVDebug):
    """The golden-reference predictor backing this transport, if any (see
    run_control_sequence.py's identical helper for the full rationale)."""
    return getattr(dm.t, "predictor", None)


def build_reset_ctrl_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    hartsel: int = 0,
    **params,
) -> DebugSession:
    """
    Build and return a DebugSession exercising Reset Control (spec #3.2).
    The session is NOT run yet — call session.run() when ready.

    Traces to: TC-RST-001, TC-RST-002, TC-RST-003, TC-RST-004, TC-RST-005,
    TC-RST-006

    Args:
        dm:      RISCVDebug instance (already has transport attached)
        mode:    "batch" or "interactive"
        hartsel: which hart to exercise (default 0)
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    if hartsel:
        session.add_step(
            f"Select hart {hartsel}", lambda: dm.select_hart(hartsel),
        )

    # ── TC-RST-001: ndmreset platform reset ───────────────────────────────
    def tc_rst_001_assert():
        dm.ndmreset(True)
        word = dm.read_dmstatus()
        # #3.5 / INV-HALT-RUN-MUTEX: true of every implementation, always.
        mutex_ok = not (anyhalted(word) and anyrunning(word))
        note = ""
        p = _predictor(dm)
        if p is not None:
            predicted = p.expect(DMI.DMSTATUS)
            model_pending = ndmresetpending(predicted)
            dut_pending = ndmresetpending(word)
            if dut_pending != model_pending:
                note += (
                    f" [divergence: DUT ndmresetpending={int(dut_pending)} vs "
                    f"model={int(model_pending)} — some v0.13 dm_pkg DUTs (e.g. "
                    f"CVA6 dm_pkg.sv dmstatus_t) have no ndmresetpending field at "
                    f"all; checked against the model instead, per #3.14.1]"
                )
            ok = mutex_ok and model_pending
        else:
            ok = mutex_ok
        return StepResult(ok=ok, msg=f"TC-RST-001: ndmreset asserted, dmstatus={word:#010x}{note}")
    session.add_step(
        "TC-RST-001: assert dmcontrol.ndmreset=1 (spec #3.2)", tc_rst_001_assert,
    )

    def tc_rst_001_deassert():
        dm.ndmreset(False)
        word = dm.read_dmstatus()
        # #3.2: "if the hart was initially running it will execute normally" —
        # no halt request of any kind was raised, so it must not come out halted.
        ok = not anyhalted(word)
        return StepResult(
            ok=ok,
            msg=f"TC-RST-001: ndmreset deasserted, anyhalted={anyhalted(word)} "
                f"(expected False — no halt request was raised)",
        )
    session.add_step(
        "TC-RST-001: deassert dmcontrol.ndmreset=0", tc_rst_001_deassert,
    )

    # ── TC-RST-002: hartreset selected-hart reset (discovery) ────────────
    def tc_rst_002():
        # Halt first: the spec places no restriction on hartreset only
        # applying to a running hart, and asserting it against an already
        # halted hart is what actually exercises the halted -> in-reset
        # transition (#3.2) rather than just running -> in-reset (TC-RST-001
        # already covers that leg).
        dm.halt()
        dm.hartreset(True)
        readback = dm.read_dmcontrol()
        supported = dmcontrol_hartreset(readback)
        if not supported:
            dm.hartreset(False)
            dm.resume()
            return StepResult(
                ok=True,
                msg="TC-RST-002: dmcontrol.hartreset read back 0 after being "
                    "written 1 — not implemented on this DUT (WARL tied 0, spec "
                    "#3.14.2 hartreset). N/A per the spec's own discovery "
                    "mechanism, not a failure (matches CVA6 dm_csrs.sv:511).",
            )
        # Observe the in-reset window itself before releasing.
        dm.read_dmstatus()
        dm.hartreset(False)
        after = dm.read_dmstatus()
        released_ok = not anyhalted(after)
        return StepResult(
            ok=released_ok,
            msg=f"TC-RST-002: hartreset supported on this DUT — halted, "
                f"reset-asserted, then released; anyhalted after release="
                f"{anyhalted(after)}",
        )
    session.add_step(
        "TC-RST-002: discover/exercise dmcontrol.hartreset (spec #3.14.2)", tc_rst_002,
    )

    # ── TC-RST-003: havereset set regardless of reset cause ───────────────
    def tc_rst_003():
        results = []

        # Cause 1: ndmreset — universally supported.
        dm.ndmreset(True)
        dm.ndmreset(False)
        word = dm.read_dmstatus()
        results.append(("ndmreset", anyhavereset(word) and allhavereset(word)))
        dm.ackhavereset()

        # Cause 2: hartreset — only if this DUT implements it (see TC-RST-002).
        dm.hartreset(True)
        supported = dmcontrol_hartreset(dm.read_dmcontrol())
        if supported:
            dm.hartreset(False)
            word = dm.read_dmstatus()
            results.append(("hartreset", anyhavereset(word) and allhavereset(word)))
            dm.ackhavereset()
        else:
            dm.hartreset(False)
            results.append(("hartreset", None))  # None = N/A, not failed

        ok = all(v is not False for _, v in results)
        detail = ", ".join(f"{cause}={'set' if v else ('N/A' if v is None else 'NOT SET')}"
                            for cause, v in results)
        return StepResult(
            ok=ok,
            msg=f"TC-RST-003: havereset observed per reset cause — {detail} "
                f"(spec #3.2: 'must be set regardless of the cause of the reset')",
        )
    session.add_step(
        "TC-RST-003: havereset set regardless of reset cause (spec #3.2)", tc_rst_003,
    )

    # ── TC-RST-004: ackhavereset clears the sticky bit ────────────────────
    def tc_rst_004():
        dm.ndmreset(True)
        dm.ndmreset(False)
        before = dm.read_dmstatus()
        was_set = anyhavereset(before) and allhavereset(before)
        dm.ackhavereset()
        after = dm.read_dmstatus()
        cleared = not anyhavereset(after) and not allhavereset(after)
        return StepResult(
            ok=was_set and cleared,
            msg=f"TC-RST-004: havereset was_set={was_set} before ack, "
                f"cleared={cleared} after ackhavereset (spec #3.14.2)",
        )
    session.add_step(
        "TC-RST-004: ackhavereset clears the sticky havereset bit (spec #3.14.2)", tc_rst_004,
    )

    # ── TC-RST-005: DMI access restrictions while reset asserted ──────────
    def tc_rst_005():
        dm.ndmreset(True)
        # #3.2: "the only supported DM operations are reading/writing dmcontrol
        # and reading ndmresetpending. The behavior of other accesses is
        # undefined." Attempt one anyway (abstract GPR read touches COMMAND/
        # DATA0/ABSTRACTCS) via the existing higher-level helper — never a bare
        # transport call from inside a sequence — and confirm the DM survives:
        # a *response* (even an error response), not a hang/no-response, and
        # dmcontrol/dmstatus remain readable and sane afterward. The specific
        # read-back value (or which cmderr, if any) is explicitly not asserted
        # on (UNSPECIFIED).
        #
        # DebugError from _wait_abstractcs specifically (message contains
        # "cmderr=") means the DM *did* respond -- it processed the abstract
        # command and reported a definite error code (e.g. cmderr=4
        # halt/resume, since the hart is in reset, not halted -- confirmed via
        # a real CVA6 run, 2026-07-24/25) -- that is affirmative evidence of
        # survival, not the DM being dead. Only a genuine non-response
        # (DebugError timeout, or any other exception) counts as "did not
        # survive" here.
        survived = True
        try:
            dm.read_gpr(0x1000)  # x0 — content is irrelevant, only survival matters
        except DebugError as e:
            if "cmderr=" not in str(e):
                survived = False  # timeout or other non-response -- a real hang
        except Exception:
            survived = False
        dm.ndmreset(False)
        post = dm.read_dmcontrol()
        dm_alive = bool(post & 1)  # dmactive still 1 — DM state not corrupted
        return StepResult(
            ok=survived and dm_alive,
            msg=f"TC-RST-005: DMI access during ndmreset survived={survived}, "
                f"DM alive afterward (dmactive={dm_alive}) — the specific "
                f"read-back value is UNSPECIFIED per #3.2 and not checked",
        )
    session.add_step(
        "TC-RST-005: DMI access restrictions while ndmreset asserted (spec #3.2)", tc_rst_005,
    )

    # ── TC-RST-006: ackhavereset when havereset is already clear (no-op) ──
    def tc_rst_006():
        # Force the clear precondition explicitly rather than assume it: an
        # intervening ndmreset cycle (TC-RST-005) sets havereset again as a
        # side effect of releasing from reset (#3.2), so "TC-RST-004 already
        # ack'd it" does not survive to this step — ack once here first to
        # guarantee the starting state, then do the actual no-op check.
        dm.ackhavereset()
        before = dm.read_dmstatus()
        already_clear = not anyhavereset(before) and not allhavereset(before)
        # Spec #3.14.2 ackhavereset only says what happens when havereset IS
        # set ("clears havereset for any selected harts"); it says nothing
        # special about acking when already clear, so a second ack right here
        # must be a harmless no-op, not an error.
        dm.ackhavereset()
        after = dm.read_dmstatus()
        still_clear = not anyhavereset(after) and not allhavereset(after)
        return StepResult(
            ok=already_clear and still_clear,
            msg=f"TC-RST-006: ackhavereset written with havereset already clear "
                f"(before={already_clear}, after={still_clear}) — no-op, no error (#3.14.2)",
        )
    session.add_step(
        "TC-RST-006: ackhavereset is a no-op when havereset is already clear (spec #3.14.2)",
        tc_rst_006,
    )

    return session
