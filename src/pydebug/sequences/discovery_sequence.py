"""
sequences/discovery_sequence.py — Discover DM / hart implementation info
(spec #3.14.3 hartinfo, Ch.3 op 1).

`hartinfo` reports the selected hart's abstract-data configuration: whether the
abstract data registers are CSR- or memory-backed (`dataaccess`), how many there
are (`datasize`), the scratch count (`nscratch`), and the data region address
(`dataaddr`). A Program-Buffer flow that falls back to memory-mapped data must
read this first, so it is verified on its own.

`read_hartinfo()` is a new `riscv_dm` primitive added alongside this sequence.

Traces to: TC-DIS-003

Usage:
    from pydebug.sequences.discovery_sequence import build_discovery_sequence
    session = build_discovery_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult


def _decode_hartinfo(hi: int) -> str:
    nscratch   = (hi >> 20) & 0xF
    dataaccess = (hi >> 16) & 1
    datasize   = (hi >> 12) & 0xF
    dataaddr   = hi & 0xFFF
    return (f"nscratch={nscratch} dataaccess={dataaccess} "
            f"({'memory' if dataaccess else 'register'}-backed) "
            f"datasize={datasize} dataaddr=0x{dataaddr:03x}")


def build_discovery_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build a DebugSession that reads hartinfo and confirms it reads consistently
    across repeated reads (spec #3.14.3, TC-DIS-003). Content is DUT-specific;
    the check is that the fields are stable and the read is honoured, not a fixed
    value.

    Traces to: TC-DIS-003
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-DIS-003: hartinfo discovery, stable across repeated reads ──────
    def tc_dis_003():
        first  = dm.read_hartinfo()
        second = dm.read_hartinfo()
        ok = first == second
        return StepResult(
            ok=ok,
            msg=f"TC-DIS-003: hartinfo=0x{first:08x} ({_decode_hartinfo(first)}); "
                f"re-read 0x{second:08x}  {'stable OK' if ok else 'UNSTABLE'}",
        )
    session.add_step("TC-DIS-003: hartinfo discovery", tc_dis_003)

    return session
