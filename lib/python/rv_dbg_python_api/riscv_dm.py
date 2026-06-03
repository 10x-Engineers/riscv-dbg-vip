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
    SBCS        = 0x38
    SBADDRESS0  = 0x39
    SBDATA0     = 0x3C

# ── dmcontrol field helpers ───────────────────────────────────────────────────

def dmcontrol(
    dmactive:     bool = False,
    hartreset:    bool = False,
    resumereq:    bool = False,
    haltreq:      bool = False,
    ackhavereset: bool = False,
    hartsel:      int  = 0,
) -> int:
    v  = (1 if dmactive     else 0)
    v |= (1 if ackhavereset else 0) << 28
    v |= (1 if hartreset    else 0) << 29
    v |= (1 if resumereq    else 0) << 30
    v |= (1 if haltreq      else 0) << 31
    v |= (hartsel & 0x3FF) << 16
    return v


# ── dmstatus field accessors ─────────────────────────────────────────────────

def allhalted(dmstatus: int) -> bool:
    return bool((dmstatus >> 9) & 1)

def allrunning(dmstatus: int) -> bool:
    return bool((dmstatus >> 11) & 1)

def anyunavail(dmstatus: int) -> bool:
    return bool((dmstatus >> 12) & 1)

def version(dmstatus: int) -> int:
    return dmstatus & 0xF


# ── Core commands ─────────────────────────────────────────────────────────────

class RISCVDebug:
    """
    High-level RISC-V debug operations built on a DebugTransport.

    Example:
        from debug_lib import UVMTransport, RISCVDebug
        with UVMTransport() as t:
            dm = RISCVDebug(t)
            dm.activate()
            dm.halt()
    """

    POLL_INTERVAL = 0.001   # 1 ms between polls
    DEFAULT_TIMEOUT = 2.0   # seconds

    def __init__(self, transport: DebugTransport):
        self.t = transport

    # ── Activation ────────────────────────────────────────────────────────────

    def activate(self) -> None:
        """
        Assert dmactive — must be called before any other command.
        Translates to: write dmcontrol with dmactive=1
        """
        log.info("[DM] activate: writing dmcontrol dmactive=1")
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, ackhavereset=True))
        # Verify DM version
        status = self.t.read(DMI.DMSTATUS)
        v = version(status)
        log.info("[DM] dmstatus=0x%08x  version=%d", status, v)
        if v == 0:
            raise DebugError("DM version=0 — Debug Module not present or not responding")

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
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, haltreq=True))
        self._poll_until(
            lambda s: allhalted(s),
            register=DMI.DMSTATUS,
            msg="allhalted",
            timeout=timeout,
        )
        # Clear haltreq
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, haltreq=False))
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
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=True))
        self._poll_until(
            lambda s: allrunning(s),
            register=DMI.DMSTATUS,
            msg="allrunning",
            timeout=timeout,
        )
        self.t.write(DMI.DMCONTROL, dmcontrol(dmactive=True, resumereq=False))
        log.info("[DM] resume: hart is running ✓")

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
