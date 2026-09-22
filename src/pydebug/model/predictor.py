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

Scope, the same as `sv/model/dm_ref_model.sv`, which is checked against this
model by replaying a simulation's model-input trace (`mk/model_crosscheck.py`):

- dmcontrol/dmstatus run control (halt, resume, reset, halt-on-reset) --
  spec #3.5 Run Control, #3.2 Reset, #3.14.1 dmstatus, #3.14.2 dmcontrol.
- Registers the spec fully determines once the implementation is declared
  (`set_config()`): hartinfo, abstractcs (static fields), command, abstractauto,
  sbcs (static and R/W fields), haltsum0, hawindowsel, nextdm.
- Abstract-command (data0/command) and System Bus Access (sbaddress0/sbdata0)
  self-consistency shadows: values this same DMI traffic wrote, read back. Not
  a model of a DUT's initial register or memory content.
- Hardware single-step: a resume with dcsr.step=1 (as last written through an
  abstract command) re-halts (riscv-dbg-vip#119).
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
)

log = logging.getLogger(__name__)

# DMI addresses beyond dmcontrol/dmstatus (spec #3.14), as dm_defines_pkg.sv
# names them.
ADDR_DATA0 = 0x04
ADDR_DATA11 = 0x0F
ADDR_HARTINFO = 0x12
ADDR_HAWINDOWSEL = 0x14
ADDR_ABSTRACTCS = 0x16
ADDR_COMMAND = 0x17
ADDR_ABSTRACTAUTO = 0x18
ADDR_NEXTDM = 0x1D
ADDR_PROGBUF0 = 0x20
ADDR_PROGBUF15 = 0x2F
ADDR_SBCS = 0x38
ADDR_SBADDRESS0 = 0x39
ADDR_SBDATA0 = 0x3C
ADDR_HALTSUM0 = 0x40

#: regno of GPR x0 (hardwired 0 by the base ISA) and of dcsr (spec #4.8).
GPR_X0_REGNO = 0x1000
DCSR_REGNO = 0x07B0
DCSR_STEP_BIT = 2

MASK32 = 0xFFFF_FFFF


def _reads_back_as_written(regno: int) -> bool:
    """Mirror of dm_ref_model.sv reads_back_as_written(): the trigger CSRs
    (0x7A0-0x7AF) legalize what is written (tselect is WARL, tdata1-3 depend on
    the trigger type), so the last write is not a prediction."""
    return not (0x07A0 <= regno <= 0x07AF)


@dataclass(frozen=True)
class DeclaredConfig:
    """The declared implementation, field for field `dm_defines_pkg::dm_cfg_t`.

    Loaded from dut_configs/<name>.json by `dut_config.load_dut_config()`.
    Until one is applied with `DMPredictor.set_config()`, every register that
    carries a Preset field is unmodelled, exactly as in dm_ref_model.sv.
    """

    sba_enable: bool = False
    abstractauto_enable: bool = False
    hartarray_enable: bool = False
    authentication_enable: bool = False
    haltgroups_enable: bool = False
    num_harts: int = 1
    version: int = DMSTATUS_VERSION_0_13
    authenticated: bool = False
    impebreak: bool = False
    hasresethaltreq: bool = False
    stickyunavail: bool = False
    havereset_poweron: bool = False
    supports_hartreset: bool = False
    supports_hasel: bool = False
    resumeack_reset: bool = False
    progbufsize: int = 0
    datacount: int = 0
    relaxedpriv_reset: bool = False
    nscratch: int = 0
    dataaccess: bool = False
    datasize: int = 0
    dataaddr: int = 0
    sbversion: int = 0
    sbasize: int = 0
    sbaccess_reset: int = 0
    sbaccess_writable: bool = False
    sbaccess128: bool = False
    sbaccess64: bool = False
    sbaccess32: bool = False
    sbaccess16: bool = False
    sbaccess8: bool = False
    nextdm: int = 0


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
        # The declared implementation. dm_ref_model.sv starts from an all-zero
        # dm_cfg_t and only claims Preset-carrying registers once set_config()
        # has run; this does the same.
        self.cfg = DeclaredConfig()
        self.cfg_valid = False

        # Write-tracked registers whose read-back the spec determines.
        self.abstractauto = 0
        self.hawindowsel = 0
        self.authdata = 0
        self.sbreadonaddr = False
        self.sbaccess = 0
        self.sbautoincrement = False
        self.sbreadondata = False
        self.relaxedpriv = False

        # Abstract-command self-consistency shadow. Like dm_ref_model.sv, a
        # DM reset does not clear it: it describes the hart, not the DM.
        self.shadow_regs: Dict[int, int] = {}
        self.staged_data0 = 0
        self.data0_pending_valid = False
        self.data0_pending_value = 0

        # System Bus Access self-consistency shadow.
        self.shadow_mem: Dict[int, int] = {}
        self.sbaddress0 = 0
        self.sbcs_read_on_addr_armed = False
        self.sbdata0_pending_valid = False
        self.sbdata0_pending_value = 0

        #: The RTL's abstractcs.busy as last observed by the checker (#3.7.1).
        self.observed_cmdbusy = False

        self.dmactive = False
        self.ndmreset = False
        self.hartsel = 0
        self.hasel = False
        self._hartreset_level = False

        self.reset_dm(power_on=True)

    # ── Declared configuration ────────────────────────────────────────────────

    def set_config(self, cfg: DeclaredConfig) -> None:
        """Apply the declared implementation, as dm_ref_model.sv's set_config().

        Also re-applies the run-control parameters it carries and takes the DM
        to its power-on state.
        """
        self.cfg = cfg
        self.cfg_valid = True
        self.num_harts = cfg.num_harts
        self.version = cfg.version
        self.authenticated = cfg.authenticated
        self.impebreak = cfg.impebreak
        self.hasresethaltreq = cfg.hasresethaltreq
        self.supports_hartreset = cfg.supports_hartreset
        self.supports_hasel = cfg.supports_hasel
        self.resumeack_reset = cfg.resumeack_reset
        self.stickyunavail = cfg.stickyunavail
        self.havereset_poweron = cfg.havereset_poweron
        self.reset_dm(power_on=True)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _reset_declared_regs(self) -> None:
        """Spec reset values (dm_registers.xml): abstractauto 0, hawindowsel 0,
        sbaccess 2 (or the declared value), relaxedpriv Preset, the rest 0."""
        self.abstractauto = 0
        self.hawindowsel = 0
        self.authdata = 0
        self.sbreadonaddr = False
        self.sbaccess = self.cfg.sbaccess_reset
        self.sbautoincrement = False
        self.sbreadondata = False
        self.relaxedpriv = self.cfg.relaxedpriv_reset

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
        self._reset_declared_regs()
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

    def set_observed_cmdbusy(self, busy: bool) -> None:
        """The RTL's abstractcs.busy, fed in by the checker before each write.

        #3.7.1: a write to command, abstractcs, data* or progbuf* while a
        command is in flight is refused by the DM. This model is untimed, so
        it is told rather than guessing.
        """
        self.observed_cmdbusy = bool(busy)

    @staticmethod
    def _guarded_while_busy(addr: int) -> bool:
        return (addr in (ADDR_COMMAND, ADDR_ABSTRACTCS, ADDR_ABSTRACTAUTO)
                or ADDR_DATA0 <= addr <= ADDR_DATA11
                or ADDR_PROGBUF0 <= addr <= ADDR_PROGBUF15)

    def on_write(self, addr: int, value: int) -> None:
        """Update modeled state for a DMI write. Unmodeled addresses are ignored."""
        value &= MASK32
        if self.observed_cmdbusy and self._guarded_while_busy(addr):
            # Dropped, as the DM drops it. cmderr is tracked front-door by the
            # checker, not invented here.
            return
        if addr == DMCONTROL.address:
            self._write_dmcontrol(value)
        elif addr == ADDR_DATA0:
            self.staged_data0 = value
        elif addr == ADDR_COMMAND:
            self._write_command(value)
        elif addr == ADDR_SBCS:
            self._write_sbcs(value)
        elif addr == ADDR_SBADDRESS0:
            self._write_sbaddress0(value)
        elif addr == ADDR_SBDATA0:
            self._write_sbdata0(value)
        elif addr == ADDR_ABSTRACTAUTO:
            self.abstractauto = value
        elif addr == ADDR_HAWINDOWSEL:
            self.hawindowsel = value & 0x7FFF
        elif addr == ADDR_ABSTRACTCS:
            # A 1.0 field (#3.14.6): a 0.13 DM has no such bit, so a write
            # to it does nothing and it reads back 0.
            if self.version >= DMSTATUS_VERSION_1_0:
                self.relaxedpriv = bool((value >> 11) & 1)

    # ── Abstract command (spec #3.7.1.1): cmd[18]=postexec, cmd[17]=transfer,
    #    cmd[16]=write, cmd[15:0]=regno ──────────────────────────────────────

    def _write_command(self, value: int) -> None:
        postexec = (value >> 18) & 1
        transfer = (value >> 17) & 1
        write = (value >> 16) & 1
        regno = value & 0xFFFF
        if transfer:
            if write:
                self.shadow_regs[regno] = self.staged_data0
            elif regno == GPR_X0_REGNO:
                self.data0_pending_valid = True
                self.data0_pending_value = 0
            elif regno in self.shadow_regs and _reads_back_as_written(regno):
                self.data0_pending_valid = True
                self.data0_pending_value = self.shadow_regs[regno]
            else:
                self.data0_pending_valid = False
        if postexec:
            # The Program Buffer may change any register (#110).
            self.shadow_regs.clear()

    # ── System Bus Access (spec #3.10) ────────────────────────────────────────

    def _write_sbcs(self, value: int) -> None:
        self.sbcs_read_on_addr_armed = bool((value >> 20) & 1)
        self.sbreadonaddr = bool((value >> 20) & 1)
        if self.cfg.sbaccess_writable:
            self.sbaccess = (value >> 17) & 0x7
        self.sbautoincrement = bool((value >> 16) & 1)
        self.sbreadondata = bool((value >> 15) & 1)

    def _sba_autoincrement(self) -> None:
        if self.sbautoincrement:
            self.sbaddress0 = (self.sbaddress0 + (1 << self.sbaccess)) & MASK32

    def _sba_arm_read(self, address: int) -> None:
        if address in self.shadow_mem:
            self.sbdata0_pending_valid = True
            self.sbdata0_pending_value = self.shadow_mem[address]
        else:
            self.sbdata0_pending_valid = False

    def _write_sbaddress0(self, value: int) -> None:
        self.sbaddress0 = value
        if self.sbcs_read_on_addr_armed:
            self._sba_arm_read(value)
            self._sba_autoincrement()

    def _write_sbdata0(self, value: int) -> None:
        self.shadow_mem[self.sbaddress0] = value
        self._sba_autoincrement()

    def observe_sbdata0_read(self) -> None:
        """#3.10: with sbreadondata set, reading sbdata0 starts the next read,
        at the address sbaddress0 holds now; only then does it autoincrement."""
        if self.sbreadondata:
            self._sba_arm_read(self.sbaddress0)
            self._sba_autoincrement()

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

        Hardware single-step (riscv-dbg-vip#119): the abstract-command shadow
        records the last dcsr written, so a resume with dcsr.step=1 is
        predicted to re-halt, as in `dm_ref_model.sv`.
        """
        for h in self._selected():
            if h.nonexistent or h.unavail:
                continue
            h.resume_ack = False
            if h.halted:
                # Hardware single-step (#4.5, riscv-dbg-vip#119): if the last
                # dcsr written through an abstract command had step=1, the
                # hart runs one instruction and re-halts on its own.
                step_armed = bool((self.shadow_regs.get(DCSR_REGNO, 0) >> DCSR_STEP_BIT) & 1)
                h.halted = step_armed
                h.running = not step_armed
                h.resume_ack = True
                # A resumed hart runs code the shadow cannot follow (#110, #113).
                self.shadow_regs.clear()

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

    def has_model(self, addr: int) -> bool:
        """Whether a read of `addr` has a checkable prediction right now.

        Same answer as dm_ref_model.sv's has_model() for every address. A
        caller must check it before trusting predict().
        """
        if addr in (DMCONTROL.address, DMSTATUS.address):
            return True
        if addr == ADDR_DATA0:
            return self.data0_pending_valid
        if addr == ADDR_SBDATA0:
            return self.cfg.sba_enable and self.sbdata0_pending_valid
        if addr in (ADDR_HARTINFO, ADDR_HALTSUM0, ADDR_COMMAND, ADDR_NEXTDM, ADDR_ABSTRACTCS):
            return self.cfg_valid
        if addr == ADDR_ABSTRACTAUTO:
            return self.cfg_valid and self.cfg.abstractauto_enable
        if addr == ADDR_HAWINDOWSEL:
            return self.cfg_valid and self.cfg.hartarray_enable
        if addr == ADDR_SBCS:
            return self.cfg_valid and self.cfg.sba_enable
        return False

    def predict(self, addr: int) -> int:
        """The predicted read value; 0 for an address has_model() rejects."""
        if addr == DMCONTROL.address:
            return self._expect_dmcontrol()
        if addr == DMSTATUS.address:
            return self._expect_dmstatus()
        if addr == ADDR_DATA0:
            return self.data0_pending_value
        if addr == ADDR_SBDATA0:
            return self.sbdata0_pending_value
        if addr == ADDR_HARTINFO:
            c = self.cfg
            return ((c.nscratch & 0xF) << 20 | int(c.dataaccess) << 16
                    | (c.datasize & 0xF) << 12 | (c.dataaddr & 0xFFF))
        if addr == ADDR_ABSTRACTCS:
            return ((self.cfg.progbufsize & 0x1F) << 24 | int(self.relaxedpriv) << 11
                    | (self.cfg.datacount & 0xF))
        if addr == ADDR_COMMAND:
            return 0  # cmdtype and control are WARZ
        if addr == ADDR_ABSTRACTAUTO:
            progbuf = (self.abstractauto >> 16) & ((1 << self.cfg.progbufsize) - 1)
            data = (self.abstractauto & 0xFFF) & ((1 << self.cfg.datacount) - 1)
            return (progbuf << 16 | data) & MASK32
        if addr == ADDR_SBCS:
            c = self.cfg
            return ((c.sbversion & 0x7) << 29 | int(self.sbreadonaddr) << 20
                    | (self.sbaccess & 0x7) << 17 | int(self.sbautoincrement) << 16
                    | int(self.sbreadondata) << 15 | (c.sbasize & 0x7F) << 5
                    | int(c.sbaccess128) << 4 | int(c.sbaccess64) << 3
                    | int(c.sbaccess32) << 2 | int(c.sbaccess16) << 1 | int(c.sbaccess8))
        if addr == ADDR_HALTSUM0:
            word = 0
            for i in range(min(self.num_harts, 32)):
                if i < len(self.harts) and self.harts[i].halted:
                    word |= 1 << i
            return word
        if addr == ADDR_HAWINDOWSEL:
            return self.hawindowsel & 0x7FFF
        if addr == ADDR_NEXTDM:
            return self.cfg.nextdm & MASK32
        return 0

    @staticmethod
    def predict_mask(addr: int) -> int:
        """The bits predict() claims. abstractcs busy/cmderr and sbcs
        sbbusyerror/sbbusy/sberror are dynamic and left to the front door."""
        if addr == ADDR_ABSTRACTCS:
            return 0x1F00_080F
        if addr == ADDR_SBCS:
            return 0xE01F_8FFF
        return MASK32

    def expect(self, addr: int) -> int:
        """Predict the value a DMI read of `addr` should return.

        Raises KeyError for an address this model makes no claim about, so a
        caller can never mistake "unmodelled" for a prediction of 0.
        """
        if not self.has_model(addr):
            raise KeyError(f"predictor does not model DMI address 0x{addr:02x}")
        return self.predict(addr)

    def sync_observed_hart_signals(self, dmstatus_word: int) -> None:
        """Take the selected hart's halted/running/resume-ack from a real
        dmstatus read, as dm_ref_model.sv does before comparing one: they
        reach the DM through hart-side hardware an untimed model cannot time."""
        sel = self.hartsel
        if 0 <= sel < len(self.harts):
            h = self.harts[sel]
            h.halted = bool((dmstatus_word >> 9) & 1)
            h.running = bool((dmstatus_word >> 11) & 1)
            h.resume_ack = bool((dmstatus_word >> 17) & 1)

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
