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

import time

from pydebug.api import RISCVDebug, DebugSession, StepResult, DMI
from pydebug.api.riscv_dm import (
    DebugError,
    allhalted, anyhalted, allrunning, anyrunning,
    allhavereset, anyhavereset, ndmresetpending,
    dmcontrol_hartreset,
)
from pydebug.model.registers import DMSTATUS_VERSION_1_0

POLL_INTERVAL_S = 0.001
POLL_TIMEOUT_S = 2.0



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
        if p is not None and p.version >= DMSTATUS_VERSION_1_0:
            # ndmresetpending (#3.14.1) is a v1.0 addition -- the predictor
            # itself now only claims to predict it for a v1.0-configured DUT
            # (a v0.13 dm_pkg dmstatus_t has no such field routed at all and
            # reads it tied 0, confirmed against real Ibex RTL, 2026-07-25).
            # Checking against the model rather than the DUT read-back still
            # matters even at v1.0: some forks' own dm_pkg.sv predates the
            # field despite the DUT otherwise reporting version=v1_0.
            predicted = p.expect(DMI.DMSTATUS)
            model_pending = ndmresetpending(predicted)
            dut_pending = ndmresetpending(word)
            if dut_pending != model_pending:
                note += (
                    f" [divergence: DUT ndmresetpending={int(dut_pending)} vs "
                    f"model={int(model_pending)} — some v1.0-reporting dm_pkg "
                    f"forks still lack a routed ndmresetpending field; checked "
                    f"against the model instead, per #3.14.1]"
                )
            ok = mutex_ok and model_pending
        else:
            # No predictor, or a v0.13-configured one: ndmresetpending isn't
            # meaningfully predictable either way, so only the universal
            # mutex invariant is checked here.
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

    # ── TC-RST-001 (cont'd): haltreq asserted while a hart is in ndmreset ──
    # cross.hart_state_transition.in_reset_to_halted needs a hart to come out
    # of reset already-requested-halted (#3.5: "the hart will immediately
    # enter debug mode on the next deassertion of its reset"). TC-HOR-002 is
    # the *documented* owner of this transition, but it can never actually
    # produce it on either project DUT: dmcontrol.setresethaltreq is
    # WARL-tied to 0 (dm_csrs.sv, both DUTs -- same family as hartreset,
    # confirmed 2026-07-25), and the model's own reset_haltreq shadow is
    # correctly gated off to match (hasresethaltreq=false in both
    # dut_configs/*.json). haltreq (plain, universally-supported, unlike
    # resethaltreq) reaches the exact same code path though -- both
    # dm_ref_model.sv's release_from_reset() and (confirmed) real RTL check
    # "was a halt requested, by whatever means" on release, not specifically
    # resethaltreq -- so asserting ordinary haltreq *while* ndmreset is
    # already asserted, then releasing, exercises the identical spec clause
    # through a mechanism both DUTs actually implement.
    def tc_rst_001_haltreq_during_reset():
        dm.ndmreset(True)
        # write_dmcontrol()'s unset fields default to 0/False -- ndmreset
        # must be passed explicitly here or this write deasserts it early.
        dm.write_dmcontrol(haltreq=True, ndmreset=True)
        still_in_reset = not anyhalted(dm.read_dmstatus())
        # NOT dm.ndmreset(False): that helper is a raw absolute dmcontrol
        # write with no haltreq param, so it defaults haltreq back to 0 --
        # silently withdrawing the very halt request this step is trying to
        # test, at the exact edge (reset release) where the spec requires it
        # to still be observed. A real CVA6 UVM MODEL_MISMATCH first looked
        # like an RTL bug (hart stayed running forever) until a waveform
        # trace (dut.i_dm_top.debug_req_o) showed haltreq_o dropping to 0 in
        # the same delta cycle as ndmreset_o's deassertion -- traced to this
        # exact stimulus bug, not RTL (dm_csrs.sv's haltreq_o mux and
        # dm_top.sv's wiring have no reset-dependent gating at all; the DM
        # was behaving correctly the whole time), 2026-07-25.
        dm.write_dmcontrol(haltreq=True, ndmreset=False)
        # The halt handshake (hart exits reset, fetches, observes haltreq,
        # enters Debug Mode) takes real clock cycles, unlike the untimed
        # Python mock where the transition is instantaneous -- poll like
        # dm.halt() does, rather than trusting a single read.
        #
        # A single transient MODEL_MISMATCH on the first poll iteration is
        # expected and accepted here, not a bug to engineer away: a CVA6 UVM
        # waveform trace confirmed the real handshake takes ~4.6us of sim
        # time (fetch resume -> observe debug_req -> execute debug-ROM entry
        # -> write halted_q) that dm_ref_model.sv/predictor.py idealize as
        # instantaneous. Two mitigations were tried and rejected: a real
        # time.sleep() before the first read does nothing (this environment's
        # sim only advances with actual DMI/JTAG transactions, confirmed --
        # 0.01s of real sleep moved the mismatch's timestamp by 420ns); a
        # spacer dmcontrol read consumes real sim time but surfaces a
        # separate, unrelated, pre-existing model gap (expect_dmcontrol()
        # hardcodes haltreq/resumereq readback to 0, while real CVA6 persists
        # the last-written value -- out of scope for this step, not filed
        # here). This mirrors TC-RC-006's established precedent (testplan's
        # Uncertain bucket): the untimed model cannot express real handshake
        # latency, and that gap is documented, not silently forced closed
        # (2026-07-25).
        deadline = time.monotonic() + POLL_TIMEOUT_S
        halted_on_release = dm.is_halted()
        while not halted_on_release and time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_S)
            halted_on_release = dm.is_halted()
        # Deliberately not resuming: TC-RST-002 (next) halts the hart itself
        # as its own first action regardless of the state left here (same
        # reasoning as the removed trailing dm.resume() bug from the first
        # attempt at this step, 2026-07-25 -- haltreq is now persistently
        # set and resuming would just hang).
        return StepResult(
            ok=still_in_reset and halted_on_release,
            msg=f"TC-RST-001 (cont'd): haltreq written while ndmreset "
                f"asserted — still not halted mid-reset={still_in_reset}, "
                f"halted on release={halted_on_release} (spec #3.5: a "
                f"pending halt request takes effect the moment reset "
                f"deasserts)",
        )
    session.add_step(
        "TC-RST-001 (cont'd): haltreq asserted while a hart is in ndmreset (spec #3.5)",
        tc_rst_001_haltreq_during_reset,
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

    # ── TC-DHS-006 (write-only half): ackunavail discovery probe ──────────
    # Full TC-DHS-006 (conditional-clear semantics: ackunavail clears only
    # currently-available harts) needs the hart-availability transition
    # mechanism modeled first (testplan's own noted gap -- no sequence
    # drives a hart through an actual unavailable->available transition
    # yet). This is just the write itself: a legitimate thing for a
    # debugger to probe regardless, and the thing dmcontrol.ackunavail's
    # own coverage bin is actually asking about (was it ever written),
    # not the full conditional-clear behavior.
    def tc_dhs_006_probe():
        dm.ackunavail()
        readback = dm.read_dmcontrol()
        alive = bool(readback & 1)  # dmactive still 1 -- DM state not corrupted
        return StepResult(
            ok=alive,
            msg=f"TC-DHS-006 (write-only half): wrote dmcontrol.ackunavail=1 "
                f"— DM alive afterward (dmactive={alive}). Full conditional-"
                f"clear semantics (#3.14.2: clears only currently-available "
                f"harts) not checked here -- needs hart-availability "
                f"transition modeling, a later slice.",
        )
    session.add_step(
        "TC-DHS-006 (write-only half): ackunavail discovery probe (spec #3.14.2)",
        tc_dhs_006_probe,
    )

    # ── TC-KA-001: setkeepalive/clrkeepalive discovery probe ──────────────
    # Confirmed present in the exact spec version this project targets
    # (v1.0.0-rc3, riscv/riscv-debug-spec tag -- resolves the testplan's own
    # previously-unresolved "was keepalive added after rc3?" question,
    # 2026-07-25). Optional (like resethaltreq), and this project's
    # golden model does not track a `keepalive` hart-state field (no
    # dmstatus bit reports it either -- #3.14.2 keepalive itself "cannot be
    # read", same family as resethaltreq), so this is discovery-only: the
    # write happened, the DM survived it, no functional claim beyond that.
    def tc_ka_001():
        dm.write_dmcontrol(setkeepalive=True)
        after_set = dm.read_dmcontrol()
        dm.write_dmcontrol(clrkeepalive=True)
        after_clr = dm.read_dmcontrol()
        alive = bool(after_clr & 1)  # dmactive still 1
        return StepResult(
            ok=alive,
            msg=f"TC-KA-001: wrote setkeepalive=1 (readback=0x{after_set:08x}), "
                f"then clrkeepalive=1 (readback=0x{after_clr:08x}) — DM alive "
                f"throughout (dmactive={alive}). keepalive cannot be read back "
                f"(#3.14.2), so this is discovery-only, same as resethaltreq.",
        )
    session.add_step(
        "TC-KA-001: setkeepalive/clrkeepalive discovery probe (spec #3.14.2)",
        tc_ka_001,
    )

    return session
