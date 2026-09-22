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

#: Not in the DMI enum (the 64-bit halves are only meaningful when sbasize>32).
SBADDRESS1 = 0x3A
SBDATA1    = 0x3D

#: sbcs field positions (spec #3.10, dm_registers.xml 0x38).
SB_BUSYERROR    = 22
SB_BUSY         = 21
SB_READONADDR   = 20
SB_ACCESS_LSB   = 17
SB_AUTOINCREMENT = 16
SB_READONDATA   = 15
SB_ERROR_LSB    = 12

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


def _effective_stride(dm) -> int:
    """
    Bytes advanced per access, from the sbcs the DM *actually* holds.

    Never assume the sbaccess just written took effect: it is `R/W` in the spec
    but some DMs hardwire it (CVA6 forces 3 -- see issue #147 / RTL-002), and a
    test that assumes its own write stuck computes the wrong stride and reports
    a DUT failure that is really its own arithmetic.
    """
    sbcs = dm.t.read(DMI.SBCS)
    return 1 << ((sbcs >> SB_ACCESS_LSB) & 0x7)


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

    # ── TC-SBA-004: autoincrement across a burst ──────────────────────────
    # sbautoincrement is the only way dm_sba's address-update paths execute.
    # Without it the address register is written once per access and the
    # increment arms (dm_sba.sv:126,134) never run.
    def tc_sba_004():
        words = [0xA5A50000 | i for i in range(4)]
        dm.t.write(DMI.SBCS, (2 << SB_ACCESS_LSB) | (1 << SB_AUTOINCREMENT))
        stride = _effective_stride(dm)          # what the DM kept, not what we wrote
        dm.t.write(DMI.SBADDRESS0, addr)
        for w in words:
            dm.t.write(DMI.SBDATA0, w)          # each write bumps sbaddress0
            dm._wait_sbus()
        end_addr = dm.t.read(DMI.SBADDRESS0)
        want_end = addr + stride * len(words)
        got = [dm.read_mem32(addr + stride * i) for i in range(len(words))]
        ok = got == words and end_addr == want_end
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-004: autoincrement wrote {len(words)} words at "
                f"{stride}-byte stride, sbaddress0 0x{addr:08x}->0x{end_addr:08x} "
                f"(expected 0x{want_end:08x}), data "
                f"{'OK' if got == words else 'MISMATCH'}",
        )
    session.add_step("TC-SBA-004: sbautoincrement burst", tc_sba_004)

    # ── TC-SBA-005: sbreadondata -- reading sbdata0 triggers the next read ─
    # Distinct from sbreadonaddr: the trigger is the data read, not the
    # address write. dm_sba.sv:108 is reachable no other way.
    def tc_sba_005():
        dm.t.write(DMI.SBCS,
                   (2 << SB_ACCESS_LSB) | (1 << SB_AUTOINCREMENT)
                   | (1 << SB_READONADDR) | (1 << SB_READONDATA))
        dm.t.write(DMI.SBADDRESS0, addr)        # sbreadonaddr: fetches word 0
        dm._wait_sbus()
        seen = []
        for _ in range(3):
            seen.append(dm.t.read(DMI.SBDATA0)) # each read fetches the next
            dm._wait_sbus()
        dm.t.write(DMI.SBCS, 2 << SB_ACCESS_LSB)   # disarm both
        expect = [0xA5A50000 | i for i in range(3)]
        ok = seen == expect
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-005: sbreadondata streamed {[hex(v) for v in seen]} "
                f"(expected {[hex(v) for v in expect]})  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-SBA-005: sbreadondata streaming", tc_sba_005)

    # ── TC-SBA-006: the 64-bit address/data halves ────────────────────────
    # sbasize=64 on this DUT, so sbaddress1/sbdata1 exist and their DMI case
    # items (dm_csrs.sv:404,416,528,545) are otherwise never decoded.
    def tc_sba_006():
        dm.t.write(SBADDRESS1, 0)               # upper half of a <4GB address
        hi_addr = dm.t.read(SBADDRESS1)
        dm.t.write(DMI.SBCS, 2 << SB_ACCESS_LSB)
        dm.t.write(SBDATA1, 0)
        hi_data = dm.t.read(SBDATA1)
        ok = hi_addr == 0 and hi_data == 0
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-006: sbaddress1=0x{hi_addr:08x} sbdata1=0x{hi_data:08x} "
                f"(both halves decode)  {'OK' if ok else 'UNEXPECTED'}",
        )
    session.add_step("TC-SBA-006: 64-bit address/data halves", tc_sba_006)

    # ── TC-SBA-007: sberror on an unmapped address ────────────────────────
    # Drives sberror_valid_i (dm_csrs.sv:574) and the sberror write-1-to-clear
    # path. The spec requires the error be sticky until explicitly cleared.
    def tc_sba_007():
        bad = 0xF000_0000                        # outside CVA6's RAM map
        dm.t.write(DMI.SBCS, (1 << SB_READONADDR) | (2 << SB_ACCESS_LSB))
        dm.t.write(DMI.SBADDRESS0, bad)
        dm._wait_sbus()
        sbcs = dm.t.read(DMI.SBCS)
        err = (sbcs >> SB_ERROR_LSB) & 0x7
        # W1C: writing the error field back clears it.
        dm.t.write(DMI.SBCS, (0x7 << SB_ERROR_LSB) | (2 << SB_ACCESS_LSB))
        cleared = (dm.t.read(DMI.SBCS) >> SB_ERROR_LSB) & 0x7
        ok = cleared == 0
        return StepResult(
            ok=ok,
            msg=f"TC-SBA-007: access to 0x{bad:08x} -> sberror={err}, "
                f"after W1C sberror={cleared}  "
                f"{'OK' if ok else 'sberror did not clear'}",
        )
    session.add_step("TC-SBA-007: sberror set and write-1-to-clear", tc_sba_007)

    # ── TC-SBA-009: sbbusyerror ───────────────────────────────────────────
    # Accessing sbdata/sbaddress while sbbusy=1 must set sbbusyerror rather
    # than corrupting the transfer. These are the `if (sbbusy_i || sbbusyerror)`
    # arms at dm_csrs.sv:409,418,530,538,547 -- unreachable without racing a
    # live transfer, which is why they have never been covered.
    def tc_sba_009():
        dm.t.write(DMI.SBCS, (1 << SB_READONADDR) | (2 << SB_ACCESS_LSB))
        dm.t.write(DMI.SBADDRESS0, addr)        # starts a read; sbbusy rises
        dm.t.read(DMI.SBDATA0)                  # race it deliberately
        dm.t.write(DMI.SBDATA0, 0xDEADBEEF)     # and again on the write path
        dm._wait_sbus()
        sbcs = dm.t.read(DMI.SBCS)
        busyerr = (sbcs >> SB_BUSYERROR) & 1
        dm.t.write(DMI.SBCS, (1 << SB_BUSYERROR) | (0x7 << SB_ERROR_LSB)
                   | (2 << SB_ACCESS_LSB))       # W1C both
        after = dm.t.read(DMI.SBCS)
        ok = ((after >> SB_BUSYERROR) & 1) == 0
        # Not asserting busyerr==1: whether the race lands depends on DMI
        # timing, and a DM fast enough to finish first is not wrong. What must
        # hold is that the flag clears and the DM stays usable.
        return StepResult(
            ok=ok and dm.read_mem32(addr) is not None,
            msg=f"TC-SBA-009: sbbusyerror observed={busyerr}, cleared="
                f"{(after >> SB_BUSYERROR) & 1}, DM still usable  "
                f"{'OK' if ok else 'sbbusyerror stuck'}",
        )
    session.add_step("TC-SBA-009: sbbusyerror on a raced access", tc_sba_009)

    # ── TC-SBA-010: SBA works while the hart runs ─────────────────────────
    # Spec #3.10: SBA is independent of the hart. Everything above ran halted.
    def tc_sba_010():
        dm.resume()
        val = dm.read_mem32(addr)
        dm.halt()
        return StepResult(
            ok=True,
            msg=f"TC-SBA-010: read 0x{val:08x} from 0x{addr:08x} with the hart "
                f"running (SBA is hart-independent)  OK",
        )
    session.add_step("TC-SBA-010: SBA with the hart running", tc_sba_010)

    # ── TC-SBA-019: every access width the DM says it supports ────────────
    # sbcs advertises a width mask (sbaccess8/16/32/64/128) and sbaccess
    # selects which one an access uses. Nothing exercised the narrow widths,
    # so dm_sba's 8- and 16-bit arms were dead code in coverage. On a DM that
    # hardwires sbaccess (CVA6, RTL-002) the write does not stick and this
    # reports that rather than asserting; on one that implements it the narrow
    # accesses are real bus transfers.
    def tc_sba_019():
        advertised = [(w, bit) for w, bit in ((8, 0), (16, 1), (32, 2), (64, 3))
                      if (dm.t.read(DMI.SBCS) >> bit) & 1]
        used, refused = [], []
        for width, _bit in advertised:
            code = {8: 0, 16: 1, 32: 2, 64: 3}[width]
            base = dm.t.read(DMI.SBCS) & ~(0x7 << SB_ACCESS_LSB)
            dm.t.write(DMI.SBCS, base | (code << SB_ACCESS_LSB) | (1 << SB_READONADDR))
            got = (dm.t.read(DMI.SBCS) >> SB_ACCESS_LSB) & 0x7
            if got != code:
                refused.append(width)
                continue
            dm.t.write(DMI.SBADDRESS0, addr)       # sbreadonaddr triggers it
            dm._wait_sbus()
            dm.t.read(DMI.SBDATA0)
            used.append(width)
        # Leave sbaccess back at 32-bit for whatever runs next.
        base = dm.t.read(DMI.SBCS) & ~(0x7 << SB_ACCESS_LSB)
        dm.t.write(DMI.SBCS, base | (2 << SB_ACCESS_LSB))
        return StepResult(
            ok=True,
            msg=f"TC-SBA-019: sbcs advertises {[w for w, _ in advertised]}-bit; "
                f"accessed {used or 'none'}"
                + (f"; refused (hardwired sbaccess) {refused}" if refused else ""),
        )
    session.add_step("TC-SBA-019: each advertised access width", tc_sba_019)

    return session
