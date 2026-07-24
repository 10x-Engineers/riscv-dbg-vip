"""
sequences/sba_sequence.py — System Bus Access (spec #3.10, Ch.3 op 11).

Direct memory access over the System Bus, independent of the hart. The
`read_mem32`/`write_mem32` primitives already existed in `riscv_dm`, but no
sequence exercised SBA as a first-class feature with its own discovery and
round-trip checks (the `mem_scan` helper only reads, and traces to nothing).

Traces to: TC-SBA-001 (sbcs discovery), TC-SBA-002 (read via sbreadonaddr),
TC-SBA-003 (write via sbdata + read-back).

Usage:
    from pydebug.sequences.sba_sequence import build_sba_sequence
    session = build_sba_sequence(dm, mode="batch", addr=0x80000000)
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

#: Standard RISC-V DRAM base; valid RAM on CVA6's memory map. On
#: ibex-demo-system this address is GPIO_START, not RAM (see issue #111) —
#: Ibex configs must override `addr` to a real RAM address for this DUT.
DEFAULT_SBA_ADDR = 0x80000000


def _decode_sbcs(sbcs: int) -> str:
    sbversion = (sbcs >> 29) & 0x7
    sbasize   = (sbcs >> 5) & 0x7F
    widths = [w for w, b in (("8", 0), ("16", 1), ("32", 2), ("64", 3), ("128", 4))
              if (sbcs >> b) & 1]
    return (f"sbversion={sbversion} sbasize={sbasize} "
            f"sbaccess={{{','.join(widths)}}}-bit")


def build_sba_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    addr: int = DEFAULT_SBA_ADDR,
    pattern: int = 0xC0FFEE00,
) -> DebugSession:
    """
    Build a DebugSession exercising System Bus Access discovery + round-trip
    (spec #3.10). SBA does not require the hart to be halted (TC-SBA-008), but
    we halt first so the target word is not concurrently written by the hart.

    Traces to: TC-SBA-001, TC-SBA-002, TC-SBA-003
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-SBA-001: sbcs discovery ────────────────────────────────────────
    def tc_sba_001():
        sbcs = dm.t.read(DMI.SBCS)
        ok = sbcs != 0  # a DUT with SBA reports a non-zero sbversion/sbaccess mask
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-001: sbcs=0x{sbcs:08x} ({_decode_sbcs(sbcs)})  "
                f"{'OK' if ok else 'no SBA on this DUT'}",
        )
    session.add_step("TC-SBA-001: sbcs discovery", tc_sba_001)

    # ── TC-SBA-003 then TC-SBA-002: write a word, read it back ────────────
    def tc_sba_003_002():
        dm.write_mem32(addr, pattern)          # TC-SBA-003 (write via sbdata0)
        readback = dm.read_mem32(addr)         # TC-SBA-002 (read via sbreadonaddr)
        ok = readback == pattern
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-002/003: wrote mem[0x{addr:08x}]<-0x{pattern:08x}, "
                f"read back 0x{readback:08x}  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-SBA-002/003: SBA write + read-back round-trip", tc_sba_003_002)

    return session
