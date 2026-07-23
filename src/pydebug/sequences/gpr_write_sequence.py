"""
sequences/gpr_write_sequence.py — GPR write + read-back (TC-AC-002).

`RISCVDebug.write_gpr()` already existed as a library primitive, but no
sequence ever called it — GPR read/write round-trip had no test case at all
before this file. x0 is checked separately: spec #3.7.1.1 / the base ISA both
require it to read back 0 regardless of what was written.

Traces to: TC-AC-002

Usage:
    from pydebug.sequences.gpr_write_sequence import build_gpr_write_sequence
    session = build_gpr_write_sequence(dm, mode="batch", regno=0x1005, pattern=0xA5A5A5A5)
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult

#: GPR regno encoding (spec #3.7.1.1): x0 = 0x1000, x1 = 0x1001, ... x31 = 0x101F.
GPR_X0_REGNO = 0x1000


def build_gpr_write_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    regno: int = 0x1005,      # x5 / t0 by default
    pattern: int = 0xA5A5A5A5,
) -> DebugSession:
    """
    Build and return a DebugSession exercising GPR write + read-back
    (spec #3.7.1.1, Access Register, TC-AC-002). The hart must be halted
    first (Access Register requires it — TC-AC-008).

    Traces to: TC-AC-002
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-AC-002: write a known pattern, read it back ────────────────────
    def tc_ac_002_roundtrip():
        dm.write_gpr(regno, pattern)
        readback = dm.read_gpr(regno)
        ok = readback == pattern
        return StepResult(
            ok=ok,
            msg=f"TC-AC-002: wrote regno=0x{regno:04x} <- 0x{pattern:08x}, "
                f"read back 0x{readback:08x}  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step(
        f"TC-AC-002: write/read-back regno=0x{regno:04x}",
        tc_ac_002_roundtrip,
    )

    # ── TC-AC-002 (x0 special case): x0 must always read back 0 ───────────
    def tc_ac_002_x0():
        # Deliberately try to write a nonzero pattern to x0 first -- the
        # point of this check is that it must NOT stick, per the base ISA.
        dm.write_gpr(GPR_X0_REGNO, 0xFFFFFFFF)
        readback = dm.read_gpr(GPR_X0_REGNO)
        ok = readback == 0
        return StepResult(
            ok=ok,
            msg=f"TC-AC-002 (x0): wrote 0xffffffff, read back 0x{readback:08x} "
                f"(must be 0 regardless of what was written) {'OK' if ok else 'FAIL'}",
        )
    session.add_step("TC-AC-002: x0 always reads back 0", tc_ac_002_x0)

    return session
