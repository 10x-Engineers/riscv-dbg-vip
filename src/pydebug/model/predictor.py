"""
predictor.py — Executable golden-reference model of RISC-V Debug Module run control.

Given the current modeled state and a DMI write, this predicts the resulting
state and what a subsequent DMI read *should* return. It is the authority that
stimulus self-checks against (`StepResult.ok`), that `invariants.py` inspects,
and that `mock_transport.ModelBackedMockTransport` is backed by.

This models what the *spec* mandates, not what any one implementation happens to
do. Where the spec leaves behaviour UNSPECIFIED or implementation-defined, the
choice is exposed as a constructor parameter and named in a comment, so that a
divergence between this model and a DUT is always attributable to either a real
bug or a declared configuration difference — never to an undocumented guess.

Scope: dmcontrol/dmstatus run control (halt, resume, reset, halt-on-reset) —
spec #3.5 Run Control, #3.2 Reset, #3.14.1 dmstatus, #3.14.2 dmcontrol.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .registers import (
    DMCONTROL,
    DMSTATUS,
    DMSTATUS_VERSION_0_13,
    DMSTATUS_VERSION_1_0,
    hartsel_of,
    register_at,
)

log = logging.getLogger(__name__)


@dataclass
class HartState:
    """State the DM tracks for, and observes from, one hart.

    Spec #3.5: "For every hart, the Debug Module tracks 4 conceptual bits of
    state: halt request, resume ack, halt-on-reset request, and hart reset. ...
    These 4 bits reset to 0, except for resume ack, which may reset to either 0
    or 1. The DM receives halted, running, and havereset signals from each hart."
    """

    # ── The 4 DM-tracked conceptual bits (not directly observable) ────────────
    halt_request: bool = False
    resume_ack: bool = False
    reset_haltreq: bool = False
    hart_reset: bool = False

    # ── Signals the DM receives from the hart (observable via dmstatus) ───────
    halted: bool = False
    running: bool = True
    havereset: bool = False  # sticky until ackhavereset

    #: Whether the hart is available *right now* (e.g. powered and clocked).
    #: Harts may be unavailable while reset is asserted (#3.2).
    available: bool = True
    #: Sticky record that the hart was unavailable, only meaningful when the DM
    #: reports dmstatus.stickyunavail=1. Cleared by ackunavail (#3.14.2).
    unavail_sticky: bool = False

    #: True while this hart index exceeds the implemented hart count.
    nonexistent: bool = False

    @property
    def unavail(self) -> bool:
        """The value dmstatus.any/allunavail reflects for this hart.

        #3.14.1 anyunavail: "1 when any currently selected hart is unavailable,
        or (if stickyunavail is 1) was unavailable without that being
        acknowledged."
        """
        return (not self.available) or self.unavail_sticky


class DMPredictor:
    """Predicts Debug Module run-control behaviour from DMI writes.

    Usage:
        p = DMPredictor()
        p.on_write(DMCONTROL.address, some_word)
        assert transport.read(DMSTATUS.address) == p.expect(DMSTATUS.address)
    """

    def __init__(
        self,
        num_harts: int = 1,
        version: int = DMSTATUS_VERSION_0_13,
        authenticated: bool = True,
        impebreak: bool = False,
        hasresethaltreq: bool = True,
        supports_hartreset: bool = True,
        supports_hasel: bool = False,
        resumeack_reset: bool = False,
        stickyunavail: bool = False,
        havereset_poweron: bool = False,
    ):
        """
        Args:
            num_harts: Implemented hart count. hartsel >= num_harts is nonexistent.
            version: dmstatus.version to report. Defaults to 2 (0.13) because both
                project DUTs use PULP riscv-dbg v0.13; spec v1.0 mandates 3. This
                is a declared DUT difference, not a model guess.
            authenticated: dmstatus.authenticated. Authentication is optional
                (#3.12); both DUTs report authenticated=1 with no auth required.
            impebreak: dmstatus.impebreak (#3.14.1) — implicit ebreak after progbuf.
            hasresethaltreq: Whether the DM implements set/clrresethaltreq (#3.5).
                When False, those writes are ignored and dmstatus.hasresethaltreq=0,
                which makes the halt-on-reset tests N/A rather than failures.
            supports_hartreset: Whether dmcontrol.hartreset is implemented. When
                False the WARL field ties to 0 (#3.14.2 hartreset: "If this feature
                is not implemented, the bit always stays 0").
            supports_hasel: Whether the hart array mask register exists. When False,
                hasel is WARL-tied to 0 (#3.14.2 hasel: "An implementation which
                does not implement the hart array mask register must tie this
                field to 0").
            resumeack_reset: Reset value of the per-hart resume-ack bit. Spec #3.5
                explicitly permits either 0 or 1 ("except for resume ack, which may
                reset to either 0 or 1"), so this is implementation-defined and
                must not be asserted on generically.
            stickyunavail: dmstatus.stickyunavail (#3.14.1, reset="Preset") — a
                declared capability bit, not derivable from version or anything
                else: whether allunavail/anyunavail behave sticky. Must be told
                explicitly per target (riscv-dbg-vip#117).
            havereset_poweron: Whether a hart's havereset bit reads 1 immediately
                after power-on, before any DMI activity (#3.2's reset value for
                havereset is implementation-defined, "-"). Cleared the moment
                anything acks it (e.g. activate()'s bundled ackhavereset=1).
        """
        self.num_harts = num_harts
        self.version = version
        self.authenticated = authenticated
        self.impebreak = impebreak
        self.hasresethaltreq = hasresethaltreq
        self.supports_hartreset = supports_hartreset
        self.supports_hasel = supports_hasel
        self.resumeack_reset = resumeack_reset
        self.stickyunavail = stickyunavail
        self.havereset_poweron = havereset_poweron

        self.harts: List[HartState] = []
        self.dmactive = False
        self.ndmreset = False
        self.hartsel = 0
        self.hasel = False
        self._hartreset_level = False

        self.reset_dm(power_on=True)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset_dm(self, power_on: bool = False) -> None:
        """Take the DM to its reset state (dmactive=0 or power-up).

        Spec #3.14.2 dmactive=0: "The module's state, including authentication
        mechanism, takes its reset values (the dmactive bit is the only bit which
        can be written to something other than its reset value)."

        Note the harts' own halted/running state is NOT reset here: the DM reset
        resets the DM, not the harts. Spec #3.5: "If the DM is reset while a hart
        is halted, it is UNSPECIFIED whether that hart resumes." This model keeps
        the hart where it was; tests must not assert on that transition.
        """
        prev = self.harts
        self.dmactive = False
        self.ndmreset = False
        self.hartsel = 0
        self.hasel = False
        self._hartreset_level = False

        self.harts = []
        for i in range(max(self.num_harts, 1)):
            h = HartState(
                halt_request=False,
                resume_ack=self.resumeack_reset,
                reset_haltreq=False,
                hart_reset=False,
            )
            if power_on:
                h.halted = False
                h.running = True
                h.havereset = self.havereset_poweron
            else:
                # Preserve hart-side signals across a DM reset (see docstring).
                h.halted = prev[i].halted if i < len(prev) else False
                h.running = prev[i].running if i < len(prev) else True
                h.havereset = prev[i].havereset if i < len(prev) else False
            self.harts.append(h)

    # ── Hart selection ────────────────────────────────────────────────────────

    def selected_indices(self) -> List[int]:
        """Indices of the currently selected harts (spec #3.14.2 hasel).

        With hasel=0 there is exactly one selected hart, chosen by hartsel. The
        hart array mask (hasel=1) is not modeled — `supports_hasel` ties hasel
        to 0, matching a DUT without the hart array mask register.
        """
        return [self.hartsel]

    def _selected(self) -> List[HartState]:
        out = []
        for i in self.selected_indices():
            if 0 <= i < len(self.harts):
                out.append(self.harts[i])
        return out

    def _is_nonexistent(self, index: int) -> bool:
        return index >= self.num_harts

    # ── Write prediction ──────────────────────────────────────────────────────

    def on_write(self, addr: int, value: int) -> None:
        """Update modeled state for a DMI write. Unmodeled addresses are ignored."""
        reg = register_at(addr)
        if reg is None or reg.address != DMCONTROL.address:
            return
        self._write_dmcontrol(value)

    def _write_dmcontrol(self, value: int) -> None:
        f = DMCONTROL.decode(value)

        # dmactive=0 resets the DM. Spec #3.14.2: "When this value is written, the
        # DM may ignore any other bits written to dmcontrol in the same write."
        # This model takes that permission — other bits in the same write are dropped.
        if not f["dmactive"]:
            self.reset_dm()
            return

        was_active = self.dmactive
        self.dmactive = True
        if not was_active:
            # Coming out of DM reset: nothing else to do; state is already at reset.
            pass

        # Selection updates first — spec #3.14.2 states repeatedly, per action bit:
        # "Writes apply to the new value of hartsel and hasel."
        self.hartsel = hartsel_of(value)
        self.hasel = bool(f["hasel"]) if self.supports_hasel else False
        for i, h in enumerate(self.harts):
            h.nonexistent = self._is_nonexistent(i)

        # ndmreset is a level (#3.14.2: write 1 then write 0 to deassert).
        self._apply_ndmreset(bool(f["ndmreset"]))

        # hartreset is a level over the selected harts, WARL-tied to 0 if absent.
        hartreset = bool(f["hartreset"]) and self.supports_hartreset
        self._apply_hartreset(hartreset)

        # Halt-on-reset request bits (optional feature, #3.5).
        if self.hasresethaltreq:
            if f["setresethaltreq"] and not f["clrresethaltreq"]:
                for h in self._selected():
                    h.reset_haltreq = True
            if f["clrresethaltreq"]:
                # clr wins over a simultaneous set (mirrors the documented
                # set/clrkeepalive precedence in #3.14.2).
                for h in self._selected():
                    h.reset_haltreq = False

        # havereset acknowledgment (#3.14.2 ackhavereset: "Clears havereset for
        # any selected harts").
        if f["ackhavereset"]:
            for h in self._selected():
                h.havereset = False

        if f["ackunavail"]:
            # #3.14.2 ackunavail: "Clears unavail for any selected harts that are
            # currently available." The condition is on *current availability*,
            # not on the sticky bit: a hart that is still unavailable keeps its
            # unavail reported, and only a hart that has since become available
            # gets its sticky record cleared.
            for h in self._selected():
                if h.available:
                    h.unavail_sticky = False

        # Halt request is a persistent per-hart bit; writing 0 clears it.
        # #3.5: "When a debugger writes 1 to haltreq, each selected hart's halt
        # request bit is set." / #3.14.2: "Writing 0 clears the halt request bit".
        haltreq = bool(f["haltreq"])
        for h in self._selected():
            h.halt_request = haltreq

        # #3.5: "When a running hart ... sees its halt request bit high, it
        # responds by halting ... Halted harts ignore their halt request bit."
        if haltreq:
            for h in self._selected():
                if h.nonexistent or h.unavail:
                    continue
                if h.running and not h.halted:
                    h.halted = True
                    h.running = False

        # #3.14.2 resumereq: "resumereq is ignored if haltreq is set."
        if f["resumereq"] and not haltreq:
            self._apply_resumereq()

        self._settle_reset_state()

    def _apply_resumereq(self) -> None:
        """Model resumereq exactly as spec #3.5 words it.

        "When a debugger writes 1 to resumereq, each selected hart's resume ack
        bit is cleared and each selected, halted hart is sent a resume request.
        Harts respond by resuming, clearing their halted signal, and asserting
        their running signal. At the end of this process the resume ack bit is
        set. ... Resume requests are ignored by running harts."

        Note the asymmetry, which is easy to get wrong: the resume-ack bit is
        cleared for EVERY selected hart, but only HALTED harts are sent the
        request and therefore only they set resume-ack again. A hart that was
        already running when resumereq was written ends up with resume_ack=0
        and no way to re-set it until it is halted and resumed.

        Known scope gap (riscv-dbg-vip#119): this predictor never observes
        abstract-command writes (only DMCONTROL, per this module's declared
        scope in the file header), so unlike `dm_ref_model.sv` -- which
        additionally shadows abstract-command traffic and can therefore tell
        a dcsr.step=1 write apart from an ordinary resume -- this model
        always predicts `running=True` here, even for a hardware single-step
        resume that should autonomously re-halt. `dm_ref_model.sv` is the
        checker actually used against RTL for TC-SSTEP-001 (see its own file
        header); this gap is declared, not silently guessed past, per this
        module's own stated documentation discipline.
        """
        for h in self._selected():
            if h.nonexistent or h.unavail:
                continue
            h.resume_ack = False
            if h.halted:
                h.halted = False
                h.running = True
                h.resume_ack = True

    def _apply_ndmreset(self, asserted: bool) -> None:
        """ndmreset resets every hart and the rest of the platform (#3.2)."""
        if asserted and not self.ndmreset:
            self.ndmreset = True
            for h in self.harts:
                h.halted = False
                # Spec #3.2: "Which states a hart that is reset goes through
                # is implementation dependent." Both current DUTs' dm_csrs.sv
                # compute allrunning/anyrunning combinationally as
                # ~halted & ~unavailable -- with halted forced False above,
                # a hart not independently marked unavailable reads
                # running=True throughout the reset window, not "neither"
                # (confirmed on real RTL, not guessed; see
                # dv_model_derive_from_spec).
                h.running = not (h.unavail_sticky or not h.available)
                # Both DUTs' dm_csrs.sv set havereset_d combinationally on
                # ndmreset_o ("if (ndmreset_o) havereset_d_aligned = '1") --
                # immediately on assertion, not deferred to release.
                h.havereset = True
                # #3.5: "These 4 [DM-tracked] bits reset to 0, except for
                # resume ack, which may reset to either 0 or 1" -- explicitly
                # declared implementation-defined, per-DUT, same category as
                # havereset_poweron (riscv-dbg-vip#117). Applies to every
                # reset event this bit is exposed to, not just power-on --
                # self.resumeack_reset is the single declared parameter that
                # governs it everywhere, mirroring the constructor's own use
                # of the same field.
                h.resume_ack = self.resumeack_reset
        elif not asserted and self.ndmreset:
            self.ndmreset = False
            for h in self.harts:
                self._release_from_reset(h)

    def _apply_hartreset(self, asserted: bool) -> None:
        """hartreset resets only the currently selected harts (#3.14.2)."""
        if asserted and not self._hartreset_level:
            self._hartreset_level = True
            for h in self._selected():
                h.hart_reset = True
                h.halted = False
                h.running = False
                # Same declared, implementation-defined reset value as
                # _apply_ndmreset's identical resume_ack handling above
                # (#3.5) -- not currently exercised on either DUT (hartreset
                # is WARL-tied 0 on both), kept for correctness/consistency
                # should a future DUT implement it.
                h.resume_ack = self.resumeack_reset
        elif not asserted and self._hartreset_level:
            self._hartreset_level = False
            for h in self._selected():
                h.hart_reset = False
                self._release_from_reset(h)

    def _release_from_reset(self, h: HartState) -> None:
        """A hart coming out of reset.

        #3.2: "When a hart comes out of reset ... havereset becomes set."
        #3.5: "the hart will immediately enter debug mode on the next deassertion
        of its reset" if its halt-on-reset request bit is set — "This is true
        regardless of the reset's cause."
        Combined with #3.5's "a hart just coming out of reset, sees its halt
        request bit high, it responds by halting".
        """
        if h.nonexistent:
            return
        h.havereset = True  # sticky until ackhavereset
        if h.reset_haltreq or h.halt_request:
            h.halted = True
            h.running = False
        else:
            h.halted = False
            h.running = True

    def _settle_reset_state(self) -> None:
        """Harts held in reset report halted=False -- and, per both DUTs'
        real ~halted & ~unavailable combinational formula (see
        _apply_ndmreset), running=True unless independently unavailable,
        not "neither"."""
        for h in self.harts:
            if self.ndmreset or (h.hart_reset and not h.nonexistent):
                h.halted = False
                h.running = not (h.unavail_sticky or not h.available)

    # ── Read prediction ───────────────────────────────────────────────────────

    def expect(self, addr: int) -> int:
        """Predict the value a DMI read of `addr` should return."""
        reg = register_at(addr)
        if reg is None:
            raise KeyError(f"predictor does not model DMI address 0x{addr:02x}")
        if reg.address == DMSTATUS.address:
            return self._expect_dmstatus()
        if reg.address == DMCONTROL.address:
            return self._expect_dmcontrol()
        raise KeyError(f"predictor has no read model for {reg.name}")

    def _expect_dmstatus(self) -> int:
        sel = self._selected()
        idx = self.selected_indices()
        nonexistent = [self._is_nonexistent(i) for i in idx]

        def all_any(pred) -> Dict[str, int]:
            vals = [pred(h) for h in sel]
            return {
                "all": int(bool(vals) and all(vals)),
                "any": int(any(vals)),
            }

        halted = all_any(lambda h: h.halted)
        running = all_any(lambda h: h.running)
        havereset = all_any(lambda h: h.havereset)
        resumeack = all_any(lambda h: h.resume_ack)
        unavail = all_any(lambda h: h.unavail)

        return DMSTATUS.encode(
            # ndmresetpending (dmstatus bit 24) is a v1.0 addition (#3.14.1);
            # a v0.13 DUT's dm_pkg dmstatus_t has no such field routed at all
            # and reads it tied 0, regardless of self.ndmreset -- confirmed
            # against real Ibex RTL (vendored, unmodified v0.13 riscv-dbg),
            # 2026-07-25. Previously unconditional here, which the mock-only
            # pytest suite could never catch (ModelBackedMockTransport's
            # "RTL" and "expected" are the same predictor instance) -- only
            # surfaced via a real v0.13 DUT UVM comparison.
            ndmresetpending=int(self.ndmreset) if self.version >= DMSTATUS_VERSION_1_0 else 0,
            stickyunavail=int(self.stickyunavail),
            impebreak=int(self.impebreak),
            allhavereset=havereset["all"],
            anyhavereset=havereset["any"],
            allresumeack=resumeack["all"],
            anyresumeack=resumeack["any"],
            allnonexistent=int(bool(nonexistent) and all(nonexistent)),
            anynonexistent=int(any(nonexistent)),
            allunavail=unavail["all"],
            anyunavail=unavail["any"],
            allrunning=running["all"],
            anyrunning=running["any"],
            allhalted=halted["all"],
            anyhalted=halted["any"],
            authenticated=int(self.authenticated),
            authbusy=0,
            hasresethaltreq=int(self.hasresethaltreq),
            confstrptrvalid=0,
            # NOT gated by dmactive on either real DUT: dm_csrs.sv assigns
            # dmstatus.version unconditionally on both, confirmed by a
            # pre-activation dmstatus read returning the true version, not 0
            # (riscv-dbg-vip#117).
            version=self.version,
        )

    def _expect_dmcontrol(self) -> int:
        """Predict a dmcontrol read-back.

        Only R/W and WARL fields read back. Every W1 and WARZ field reads 0 by
        definition (see registers.ACCESS_READS_ZERO), which is itself a checkable
        architectural property rather than an accident of this model.
        """
        from .registers import with_hartsel

        word = DMCONTROL.encode(
            dmactive=int(self.dmactive),
            ndmreset=int(self.ndmreset),
            hasel=int(self.hasel),
            hartreset=int(self._hartreset_level and self.supports_hartreset),
        )
        return with_hartsel(word, self.hartsel)

    # ── Introspection (used by invariants.py and coverage.py) ─────────────────

    def snapshot(self) -> Dict[str, object]:
        """A plain-data copy of modeled state, safe to diff across a transaction."""
        return {
            "dmactive": self.dmactive,
            "ndmreset": self.ndmreset,
            "hartsel": self.hartsel,
            "hasel": self.hasel,
            "harts": [
                {
                    "halted": h.halted,
                    "running": h.running,
                    "havereset": h.havereset,
                    "resume_ack": h.resume_ack,
                    "halt_request": h.halt_request,
                    "reset_haltreq": h.reset_haltreq,
                    "unavail": h.unavail,
                    "nonexistent": h.nonexistent,
                }
                for h in self.harts
            ],
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        h = self.harts[self.hartsel] if self.hartsel < len(self.harts) else None
        state = "?" if h is None else ("halted" if h.halted else "running" if h.running else "in-reset")
        return f"<DMPredictor dmactive={self.dmactive} hartsel={self.hartsel} hart={state}>"
