"""
riscv_dm.py — RISC-V Debug Module (DM) command library.

This is the translation layer between high-level debug intents
(halt, resume, read_gpr, read_mem, ...) and low-level DMI
register reads/writes per the RISC-V Debug Specification v0.13/1.0.

DMI register addresses used:
    0x04  data0         — abstract command data
    0x05  data1
    0x10  dmcontrol     — DM control (haltreq, dmactive, ...)
    0x11  dmstatus      — DM status (allhalted, allrunning, ...)
    0x16  abstractcs    — abstract command status/error
    0x17  command       — abstract command trigger
    0x18  abstractauto
    0x38  sbcs          — system bus control/status
    0x39  sbaddress0    — system bus address
    0x3c  sbdata0       — system bus data

Every method signature takes a transport and returns a result.
No sequence logic lives here — sequences import and call these.
"""

import time
import logging
from .transport import DebugTransport, TransportError

log = logging.getLogger(__name__)

# ── DMI register map ──────────────────────────────────────────────────────────

class DMI:
    DATA0       = 0x04
    DATA1       = 0x05
    DMCONTROL   = 0x10
    DMSTATUS    = 0x11
    HARTINFO    = 0x12
    ABSTRACTCS  = 0x16
    COMMAND     = 0x17
    PROGBUF0    = 0x20
    PROGBUF15   = 0x2F
    DMCS2       = 0x32  # spec v1.0 only -- no DMI 0x32 register exists pre-v1.0
    SBCS        = 0x38
    SBADDRESS0  = 0x39
    SBDATA0     = 0x3C

# ── dmcontrol field helpers ───────────────────────────────────────────────────
#
# Bit positions below are taken verbatim from the ratified spec's own register
# table (#3.14.2 dmcontrol), the same source `pydebug.model.registers.DMCONTROL`
# encodes. The two are deliberately NOT unified via a shared import: mock_transport.py
# already imports `DMI` from this module, and `pydebug.model`'s package __init__
# imports mock_transport.py, so an import of `pydebug.model.registers` from here
# would close a circular-import loop (pydebug.model -> mock_transport ->
# api.riscv_dm -> model.registers -> pydebug.model, mid-initialization). Verified
# with `python3 -c "import pydebug"` after every change to this boundary. A few
# duplicated shift expressions is the cheaper price to pay.

def dmcontrol(
    dmactive:        bool = False,
    hartreset:       bool = False,
    resumereq:       bool = False,
    haltreq:         bool = False,
    ackhavereset:    bool = False,
    hartsel:         int  = 0,
    ndmreset:        bool = False,
    setresethaltreq: bool = False,
    clrresethaltreq: bool = False,
    ackunavail:      bool = False,
    hasel:           bool = False,
) -> int:
    """
    Encode a dmcontrol (DMI 0x10) word, spec #3.14.2.

    `hartsel` is the full 20-bit hart index (spec #3.14.2 hartsel: "hartsello
    ... hartselhi ... form a single field called hartsel"), assembled from two
    disjoint 10-bit fields: hartsello at bits[25:16], hartselhi at bits[15:6].
    Splitting across both — instead of masking to 10 bits — is what makes hart
    indices >= 1024 reachable at all; a debugger discovers the DUT's actual
    HARTSELLEN (0..20) by writing all ones and reading back which bits stuck.
    """
    v  = (1 if dmactive        else 0)
    v |= (1 if ndmreset        else 0) << 1
    v |= (1 if clrresethaltreq else 0) << 2
    v |= (1 if setresethaltreq else 0) << 3
    # bits 4:5 are set/clrkeepalive — not yet exercised by any TC-ID, so left
    # unencoded here rather than half-implemented; see testplan coverage notes.
    v |= ((hartsel >> 10) & 0x3FF)     << 6    # hartselhi, bits[15:6]
    v |= (hartsel & 0x3FF)             << 16   # hartsello, bits[25:16]
    v |= (1 if hasel           else 0) << 26
    v |= (1 if ackunavail      else 0) << 27
    v |= (1 if ackhavereset    else 0) << 28
    v |= (1 if hartreset       else 0) << 29
    v |= (1 if resumereq       else 0) << 30
    v |= (1 if haltreq         else 0) << 31
    return v


def dmcontrol_hartsel(dmcontrol_word: int) -> int:
    """Assemble the 20-bit hartsel back out of a dmcontrol read-back word."""
    hi = (dmcontrol_word >> 6) & 0x3FF
    lo = (dmcontrol_word >> 16) & 0x3FF
    return (hi << 10) | lo


def dmcontrol_dmactive(dmcontrol_word: int) -> bool:
    return bool(dmcontrol_word & 1)


def dmcontrol_ndmreset(dmcontrol_word: int) -> bool:
    return bool((dmcontrol_word >> 1) & 1)


def dmcontrol_hartreset(dmcontrol_word: int) -> bool:
    """Read back dmcontrol.hartreset (WARL, #3.14.2 hartreset).

    Spec: "If this feature is not implemented, the bit always stays 0." A
    debugger discovers support by writing 1 and reading back this bit — the
    exact mechanism TC-RST-002 uses.
    """
    return bool((dmcontrol_word >> 29) & 1)


def dmcontrol_hasel(dmcontrol_word: int) -> bool:
    return bool((dmcontrol_word >> 26) & 1)


# ── dmstatus field accessors ─────────────────────────────────────────────────
#
# Same rationale as above: bit positions mirror registers.py's DMSTATUS (#3.14.1)
# but are re-derived here as plain shifts to keep this module import-cycle-free.

def allhalted(dmstatus: int) -> bool:
    return bool((dmstatus >> 9) & 1)

def anyhalted(dmstatus: int) -> bool:
    return bool((dmstatus >> 8) & 1)

def allrunning(dmstatus: int) -> bool:
    return bool((dmstatus >> 11) & 1)

def anyrunning(dmstatus: int) -> bool:
    return bool((dmstatus >> 10) & 1)

def anyunavail(dmstatus: int) -> bool:
    return bool((dmstatus >> 12) & 1)

def allresumeack(dmstatus: int) -> bool:
    return bool((dmstatus >> 17) & 1)

def anyresumeack(dmstatus: int) -> bool:
    return bool((dmstatus >> 16) & 1)

def allhavereset(dmstatus: int) -> bool:
    return bool((dmstatus >> 19) & 1)

def anyhavereset(dmstatus: int) -> bool:
    return bool((dmstatus >> 18) & 1)

def allnonexistent(dmstatus: int) -> bool:
    return bool((dmstatus >> 15) & 1)

def anynonexistent(dmstatus: int) -> bool:
    return bool((dmstatus >> 14) & 1)

def hasresethaltreq(dmstatus: int) -> bool:
    """dmstatus.hasresethaltreq (#3.14.1) — the TC-HOR-001 gate bit.

    0 means set/clrresethaltreq are not implemented; every other HOR TC-ID
    is then N/A for this DUT rather than a failure (spec #3.5 halt-on-reset
    is explicitly Optional, Ch.3 op 6).
    """
    return bool((dmstatus >> 5) & 1)

def ndmresetpending(dmstatus: int) -> bool:
    """dmstatus.ndmresetpending (#3.14.1) — not present at all in some DUTs'
    v0.13 dm_pkg (e.g. CVA6's dm_pkg.sv dmstatus_t). Verify against the golden
    model in that case rather than the DUT's read-back (see TC-RST-001)."""
    return bool((dmstatus >> 24) & 1)

def version(dmstatus: int) -> int:
    return dmstatus & 0xF


# ── dmcs2 field helpers (spec v1.0 #3.14.3 -- halt groups #404, resume groups
# #506) ────────────────────────────────────────────────────────────────────────
#
# No DMI 0x32 register exists at all pre-v1.0 -- this is only reachable when
# running against a v1.0-compliant DM. Bit positions confirmed against the
# v1.0 riscv-dbg fork's own dm_pkg.sv `dmcs2_t` packed struct
# (CVA6-fork/corev_apu/riscv-dbg/src/dm_pkg.sv) rather than re-derived from
# the spec text alone: hgselect=bit0, hgwrite=bit1 (W1), group=bits[6:2],
# dmexttrigger=bits[10:7], grouptype=bit11. On CVA6's current v1.0 fork every
# field is tied to the "not implemented" value (halt/resume groups aren't
# wired up on this target) -- TC-HG-001 exists specifically to observe and
# report whatever a given DUT actually does here, not to assume either way.

def dmcs2(
    hgselect:     bool = False,
    hgwrite:      bool = False,
    group:        int  = 0,
    dmexttrigger: int  = 0,
    grouptype:    bool = False,
) -> int:
    """Encode a dmcs2 (DMI 0x32) word."""
    v  = (1 if hgselect  else 0)
    v |= (1 if hgwrite   else 0) << 1
    v |= (group & 0x1F)          << 2
    v |= (dmexttrigger & 0xF)    << 7
    v |= (1 if grouptype else 0) << 11
    return v


def dmcs2_hgselect(word: int) -> bool:
    return bool(word & 1)

def dmcs2_group(word: int) -> int:
    return (word >> 2) & 0x1F

def dmcs2_dmexttrigger(word: int) -> int:
    return (word >> 7) & 0xF

def dmcs2_grouptype(word: int) -> bool:
    return bool((word >> 11) & 1)


# ── Core commands ─────────────────────────────────────────────────────────────

class RISCVDebug:
    """
    High-level RISC-V debug operations built on a DebugTransport.

    Example:
        from pydebug import UVMTransport, RISCVDebug
        with UVMTransport() as t:
            dm = RISCVDebug(t)
            dm.activate()
            dm.halt()
    """

    POLL_INTERVAL = 0.001   # 1 ms between polls
    DEFAULT_TIMEOUT = 2.0   # seconds

    def __init__(self, transport: DebugTransport):
        self.t = transport
        #: hartsel currently in force (spec #3.14.2: "Writes apply to the new
        #: value of hartsel"). Tracked here, not on the transport, so every
        #: subsequent dmcontrol-writing method folds in the right selection
        #: without every sequence having to thread a hartsel argument through.
        self._hartsel = 0

    # ── Activation ────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """
        Assert dmactive — must be called before any other command.
        Translates to: write dmcontrol with dmactive=1
        """
        log.info("[DM] activate: writing dmcontrol dmactive=1")
        self._hartsel = 0
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, ackhavereset=True))
        # Verify DM version
        status = self.t.read(DMI.DMSTATUS)
        v = version(status)
        log.info("[DM] dmstatus=0x%08x  version=%d", status, v)
        if v == 0:
            raise DebugError("DM version=0 — Debug Module not present or not responding")

    def deactivate(self) -> None:
        """
        Deassert dmactive — resets the Debug Module to its reset state.

        Translates to: write dmcontrol with dmactive=0
        Spec #3.14.2 dmactive: "This bit serves as a reset signal for the
        Debug Module itself ... When this value is written, the module's
        state, including authentication mechanism, takes its reset values
        (the dmactive bit is the only bit which can be written to something
        other than its reset value)." Any other bits written in the same
        word are therefore without effect, so this writes dmactive=0 alone.
        `sequences/dm_activation_sequence.py` (TC-DMA-001/002) already
        exercises this exact write via the lower-level `write_dmcontrol(
        dmactive=False)` escape hatch, deliberately, to name the field being
        tested explicitly — this method is the named convenience primitive
        for every other/future caller that just wants "deactivate," the same
        way `activate()` sits alongside `write_dmcontrol(dmactive=True, ...)`.
        """
        log.info("[DM] deactivate: writing dmcontrol dmactive=0")
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=False))
        self._hartsel = 0

    # ── Hart selection ────────────────────────────────────────────────────────

    def select_hart(self, hartsel: int) -> None:
        """
        Select a hart for every subsequent dmcontrol-writing call.

        Translates to: write dmcontrol with dmactive=1, hartsel=<hartsel>
        Spec #3.14.2 hartsel: a 20-bit index split across hartselhi/hartsello;
        "Writes apply to the new value of hartsel and hasel," which is why this
        performs a real write rather than only updating local bookkeeping.
        """
        self._hartsel = hartsel
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, hartsel=hartsel))

    # ── Halt ──────────────────────────────────────────────────────────────────

    def halt(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Halt the hart.

        Translates to:
            1. write dmcontrol: dmactive=1, haltreq=1
            2. poll dmstatus until allhalted=1
            3. write dmcontrol: dmactive=1, haltreq=0  (clear haltreq)
        """
        log.info("[DM] halt: requesting halt")
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, haltreq=True, hartsel=self._hartsel))
        self._poll_until(
            lambda s: allhalted(s),
            register=DMI.DMSTATUS,
            msg="allhalted",
            timeout=timeout,
        )
        # Clear haltreq
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, haltreq=False, hartsel=self._hartsel))
        log.info("[DM] halt: hart is halted ✓")

    # ── Resume ────────────────────────────────────────────────────────────────

    def resume(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Resume the hart.

        Translates to:
            1. write dmcontrol: dmactive=1, resumereq=1
            2. poll dmstatus until allrunning=1
            3. write dmcontrol: dmactive=1, resumereq=0
        """
        log.info("[DM] resume: requesting resume")
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=True, hartsel=self._hartsel))
        self._poll_until(
            lambda s: allrunning(s),
            register=DMI.DMSTATUS,
            msg="allrunning",
            timeout=timeout,
        )
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=False, hartsel=self._hartsel))
        log.info("[DM] resume: hart is running ✓")

    def resume_no_wait(self) -> None:
        """
        Request resume without polling dmstatus.allrunning (spec #3.5).

        Fixes a real bug found this session (GitHub issue #105): single-step
        (`dcsr.step=1`) executes exactly one instruction and re-halts so
        quickly that `allrunning` may never be observed asserted by a
        DMI-speed poll — `resume()`'s wait-for-allrunning then times out
        even though the step itself completed correctly. Ordinary resume
        should keep using `resume()`, where `allrunning` is a reliable
        observable; single-step callers should use this method instead and
        poll for re-halt directly (see `single_step_sequence.py`), never for
        `allrunning`.

        Translates to: write dmcontrol resumereq=1, then resumereq=0 —
        no poll in between.
        """
        log.info("[DM] resume_no_wait: requesting resume (no allrunning poll)")
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=True, hartsel=self._hartsel))
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=False, hartsel=self._hartsel))

    # ── Reset control (#3.2, #3.14.2) ────────────────────────────────────────

    def ndmreset(self, assert_reset: bool = True) -> None:
        """
        Assert or deassert the platform (non-debug-module) reset.

        Translates to: write dmcontrol: dmactive=1, ndmreset=<assert_reset>
        Spec #3.2: "the debugger writes 1, and then writes 0 to deassert the
        reset" — ndmreset is a level, not a pulse, so the caller controls both
        edges explicitly rather than this method polling anything.
        """
        log.info("[DM] ndmreset: %s", "asserting" if assert_reset else "deasserting")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, ndmreset=assert_reset, hartsel=self._hartsel),
        )

    def hartreset(self, assert_reset: bool = True) -> None:
        """
        Assert or deassert hartreset for the currently selected hart(s).

        Translates to: write dmcontrol: dmactive=1, hartreset=<assert_reset>
        Spec #3.14.2 hartreset (WARL): "If this feature is not implemented,
        the bit always stays 0" — read back dmcontrol after calling this with
        assert_reset=True to discover support (see TC-RST-002).
        """
        log.info("[DM] hartreset: %s", "asserting" if assert_reset else "deasserting")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, hartreset=assert_reset, hartsel=self._hartsel),
        )

    def ackhavereset(self) -> None:
        """
        Clear havereset for the currently selected hart(s).

        Translates to: write dmcontrol: dmactive=1, ackhavereset=1
        Spec #3.14.2 ackhavereset (W1): "Writing 1 to this bit clears havereset
        for any selected harts."
        """
        log.info("[DM] ackhavereset")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, ackhavereset=True, hartsel=self._hartsel),
        )

    def ackunavail(self) -> None:
        """
        Clear stickyunavail for currently-available selected harts.

        Translates to: write dmcontrol: dmactive=1, ackunavail=1
        Spec #3.14.2 ackunavail (W1): "Clears unavail for any selected harts
        that are currently available."
        """
        log.info("[DM] ackunavail")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, ackunavail=True, hartsel=self._hartsel),
        )

    # ── Halt-on-reset (#3.5, optional) ───────────────────────────────────────

    def set_reset_haltreq(self) -> None:
        """
        Request halt-on-reset for the currently selected hart(s).

        Translates to: write dmcontrol: dmactive=1, setresethaltreq=1
        Spec #3.14.2 setresethaltreq (W1) / #3.5: "the hart will immediately
        enter debug mode on the next deassertion of its reset."
        """
        log.info("[DM] set_reset_haltreq")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, setresethaltreq=True, hartsel=self._hartsel),
        )

    def clr_reset_haltreq(self) -> None:
        """
        Clear the halt-on-reset request for the currently selected hart(s).

        Translates to: write dmcontrol: dmactive=1, clrresethaltreq=1
        Spec #3.14.2 clrresethaltreq (W1).
        """
        log.info("[DM] clr_reset_haltreq")
        self.t.write(
            DMI.DMCONTROL,
            dmcontrol(dmactive=True, clrresethaltreq=True, hartsel=self._hartsel),
        )

    # ── Low-level dmcontrol / dmstatus access ────────────────────────────────
    #
    # For stimulus that needs an exact field combination the helpers above do
    # not (and, for the illegal ones, deliberately must not) expose — e.g.
    # TC-RC-005's simultaneous haltreq=1/resumereq=1, or TC-HOR-005's illegal
    # multi-mutex-bit write. Still goes through RISCVDebug/dmcontrol(), never
    # a bare transport write from inside a sequence.

    def write_dmcontrol(self, **fields) -> int:
        """
        Write an arbitrary dmcontrol field combination.

        `dmactive` and `hartsel` default to their currently-tracked values
        unless explicitly overridden, so callers only need to name the fields
        they actually care about. Returns the encoded word that was written.
        """
        fields.setdefault("dmactive", True)
        fields.setdefault("hartsel", self._hartsel)
        word = dmcontrol(**fields)
        self.t.write(DMI.DMCONTROL, word)
        return word

    def read_dmstatus(self) -> int:
        """Raw dmstatus (DMI 0x11) word, for fields this class does not wrap
        as a single-purpose method (e.g. ndmresetpending, hasresethaltreq)."""
        return self.t.read(DMI.DMSTATUS)

    def read_dmcontrol(self) -> int:
        """Raw dmcontrol (DMI 0x10) read-back word — WARL/hartsel discovery."""
        return self.t.read(DMI.DMCONTROL)

    # ── GPR access (abstract commands) ───────────────────────────────────────

    def read_gpr(self, regno: int) -> int:
        """
        Read a general-purpose register (x0–x31) or CSR.
        regno: 0x1000–0x101F for GPRs (x0=0x1000), or CSR number.

        Translates to:
            1. write command: cmdtype=0 (reg access), regno, transfer=1, write=0
            2. poll abstractcs until busy=0
            3. read data0
        """
        log.debug("[DM] read_gpr: regno=0x%04x", regno)
        cmd = (0 << 24) | (2 << 20) | (regno & 0xFFFF) | (1 << 17)  # transfer=1, write=0
        self.t.write(DMI.COMMAND, cmd)
        self._wait_abstractcs()
        val = self.t.read(DMI.DATA0)
        log.debug("[DM] read_gpr: regno=0x%04x → 0x%08x", regno, val)
        return val

    def write_gpr(self, regno: int, value: int) -> None:
        """Write a GPR or CSR."""
        log.debug("[DM] write_gpr: regno=0x%04x ← 0x%08x", regno, value)
        self.t.write(DMI.DATA0, value)
        cmd = (0 << 24) | (2 << 20) | (regno & 0xFFFF) | (1 << 17) | (1 << 16)  # write=1
        self.t.write(DMI.COMMAND, cmd)
        self._wait_abstractcs()

    def read_abstractcs(self) -> int:
        """
        Raw abstractcs (DMI 0x16) word.

        TC-AC-013: progbufsize/datacount/impebreak discovery — the gate every
        Program Buffer row (TC-PB-*) and every multi-slot Access Register row
        assumes has already run before relying on a specific slot count.
        """
        return self.t.read(DMI.ABSTRACTCS)

    # ── Program Buffer (#3.8, optional) ──────────────────────────────────────

    def write_progbuf(self, index: int, instruction: int) -> None:
        """
        Write one 32-bit instruction word into Program Buffer slot `index`
        (TC-PB-001 write/read-back).

        Translates to: write progbuf<index> (DMI 0x20+index). Implemented
        slot count is abstractcs.progbufsize (read_abstractcs(), TC-AC-013) —
        this method does not itself range-check `index` against it.
        """
        log.debug("[DM] write_progbuf[%d]: 0x%08x", index, instruction)
        self.t.write(DMI.PROGBUF0 + index, instruction)

    def read_progbuf(self, index: int) -> int:
        """Read back Program Buffer slot `index` (TC-PB-001/TC-PB-002)."""
        val = self.t.read(DMI.PROGBUF0 + index)
        log.debug("[DM] read_progbuf[%d] -> 0x%08x", index, val)
        return val

    def execute_progbuf(self) -> None:
        """
        Trigger execution of the Program Buffer exactly once (TC-PB-003,
        TC-AC-010).

        Translates to: write command with cmdtype=0 (Access Register),
        postexec=1, transfer=0. Spec #3.7.1.1 postexec: "Execute the program
        in the Program Buffer exactly once after performing the transfer, if
        any." No register transfer is requested here — only the postexec
        side effect — so the hart must already be halted and the buffer
        already loaded (write_progbuf()) before calling this.
        """
        log.info("[DM] execute_progbuf: triggering Program Buffer via postexec")
        cmd = (0 << 24) | (1 << 18)  # cmdtype=0, postexec=1, transfer=0
        self.t.write(DMI.COMMAND, cmd)
        self._wait_abstractcs()

    # ── Sdext Debug-Mode CSRs / single-step (#4.5, #4.8) ─────────────────────

    #: dcsr CSR number, spec #4.8 (dpc is 0x7B1, already used by get_pc()).
    DCSR_REGNO = 0x07B0

    def read_dcsr(self) -> int:
        """Read dcsr via abstract command (TC-DCSR-* baseline)."""
        return self.read_gpr(self.DCSR_REGNO)

    def write_dcsr(self, value: int) -> None:
        """Write dcsr via abstract command."""
        self.write_gpr(self.DCSR_REGNO, value)

    def set_step(self, enable: bool = True) -> None:
        """
        Enable or disable hardware single-step (spec #4.5, dcsr.step, bit 2).

        Reads the current dcsr and flips only bit 2, preserving every other
        field (ebreak*/prv/etc.) rather than blindly overwriting the whole
        register — same discipline as write_dmcontrol() preserving hartsel.
        """
        dcsr = self.read_dcsr()
        if enable:
            dcsr |= (1 << 2)
        else:
            dcsr &= ~(1 << 2)
        self.write_dcsr(dcsr)

    def get_dcsr_cause(self) -> int:
        """
        Read dcsr.cause (bits[8:6]) — why the hart last entered Debug Mode
        (spec #4.8). Encodings: 1=ebreak, 2=trigger, 3=haltreq, 4=step,
        5=resethaltreq, 6=group, 7=other. TC-DCSR-001/TC-SSTEP-001's check.
        """
        return (self.read_dcsr() >> 6) & 0x7

    # ── Halt groups / external trigger (#3.6, optional, spec v1.0 only) ──────

    def write_dmcs2(self, **fields) -> int:
        """
        Write an arbitrary dmcs2 field combination (DMI 0x32, spec #3.6/
        #3.14.3). Returns the encoded word written, so a caller can compare
        it directly against the read-back (TC-HG-001).

        No DMI 0x32 register exists at all pre-v1.0 — only meaningful against
        a v1.0-compliant DM.
        """
        word = dmcs2(**fields)
        self.t.write(DMI.DMCS2, word)
        return word

    def read_dmcs2(self) -> int:
        """Raw dmcs2 (DMI 0x32) read-back word (TC-HG-001)."""
        return self.t.read(DMI.DMCS2)

    # ── Memory access via system bus ─────────────────────────────────────────

    def read_mem32(self, addr: int) -> int:
        """
        Read a 32-bit word from target memory via the System Bus Access.

        Translates to:
            1. write sbcs: sbaccess=2 (32-bit), sbreadonaddr=1, sbautoincrement=0
            2. write sbaddress0: addr
            3. poll sbcs until sbbusy=0
            4. read sbdata0
        """
        log.debug("[DM] read_mem32: addr=0x%08x", addr)
        # sbcs: sbaccess=2 (32-bit), sbreadonaddr=1
        sbcs_val = (1 << 20) | (2 << 17)
        self.t.write(DMI.SBCS,      sbcs_val)
        self.t.write(DMI.SBADDRESS0, addr)
        self._wait_sbus()
        val = self.t.read(DMI.SBDATA0)
        log.debug("[DM] read_mem32: addr=0x%08x → 0x%08x", addr, val)
        return val

    def write_mem32(self, addr: int, data: int) -> None:
        """Write a 32-bit word via the System Bus."""
        log.debug("[DM] write_mem32: addr=0x%08x ← 0x%08x", addr, data)
        sbcs_val = (2 << 17)   # sbaccess=32-bit, no autoread
        self.t.write(DMI.SBCS,      sbcs_val)
        self.t.write(DMI.SBADDRESS0, addr)
        self.t.write(DMI.SBDATA0,   data)
        self._wait_sbus()

    # ── Status helpers ────────────────────────────────────────────────────────

    def is_halted(self) -> bool:
        return allhalted(self.t.read(DMI.DMSTATUS))

    def is_running(self) -> bool:
        return allrunning(self.t.read(DMI.DMSTATUS))

    def get_pc(self) -> int:
        """Read PC (DPC CSR = 0x7B1 → regno = 0x07B1)."""
        return self.read_gpr(0x07B1)

    # ── Internal polling helpers ──────────────────────────────────────────────

    def _poll_until(self, predicate, register: int, msg: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            val = self.t.read(register)
            if predicate(val):
                return
            if time.monotonic() > deadline:
                raise DebugError(
                    f"Timeout ({timeout}s) waiting for {msg} "
                    f"(last read from reg 0x{register:02x} = 0x{val:08x})"
                )
            time.sleep(self.POLL_INTERVAL)

    def _wait_abstractcs(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Wait until abstract command is no longer busy; raise on error."""
        def check(v):
            busy  = bool((v >> 12) & 1)
            error = (v >> 8) & 0x7
            if error:
                raise DebugError(f"Abstract command error cmderr={error}")
            return not busy
        self._poll_until(check, DMI.ABSTRACTCS, "abstractcs.busy=0", timeout)

    def _wait_sbus(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Wait for system bus to be not busy."""
        def check(v):
            sbbusy  = bool((v >> 21) & 1)
            sberror = (v >> 12) & 0x7
            if sberror:
                raise DebugError(f"System bus error sberror={sberror}")
            return not sbbusy
        self._poll_until(check, DMI.SBCS, "sbcs.sbbusy=0", timeout)


class DebugError(RuntimeError):
    """Raised when a debug operation fails (timeout, protocol error, etc.)."""
    pass
