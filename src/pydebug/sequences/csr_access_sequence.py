"""
sequences/csr_access_sequence.py — CSR access via Access Register (TC-AC-005),
using dscratch0/1 as the concrete CSR target (TC-DCSR-003).

CSR access is optional per spec #3.7.1.1 and is discovered by attempting it,
not by querying a capability bit first — abstractcs.cmderr=2 ("not supported")
is a legitimate pass here, same as TC-AC-005's own description states; only a
hang or a wrong value is a real failure. dscratch0/1 are chosen as the target
CSRs because spec #4.8 guarantees them as private Debug-Mode scratch
registers on any DUT that implements Debug Mode at all, so "unsupported" is
not expected in practice the way it would be for an arbitrary CSR.

Traces to: TC-AC-005, TC-DCSR-003

Usage:
    from pydebug.sequences.csr_access_sequence import build_csr_access_sequence
    session = build_csr_access_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult

#: dscratch0/1 CSR numbers (spec #4.8) -- private Debug-Mode scratch space.
DSCRATCH0_REGNO = 0x07B2
DSCRATCH1_REGNO = 0x07B3

# abstractcs.cmderr (bits[10:8]): 0=none, 2=not supported (spec #3.7.1.1).
CMDERR_NOT_SUPPORTED = 2


def build_csr_access_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    pattern0: int = 0xC5C5C5C5,
    pattern1: int = 0x3A3A3A3A,
) -> DebugSession:
    """
    Build and return a DebugSession exercising CSR access via Access Register
    (spec #3.7.1.1, TC-AC-005) using dscratch0/dscratch1, plus the
    resume/re-halt preservation check from TC-DCSR-003.

    Traces to: TC-AC-005, TC-DCSR-003
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-AC-005: CSR write + read-back, discovery-by-attempting ─────────
    def tc_ac_005():
        dm.write_gpr(DSCRATCH0_REGNO, pattern0)
        cmderr = (dm.read_abstractcs() >> 8) & 0x7
        if cmderr == CMDERR_NOT_SUPPORTED:
            return StepResult(
                ok=True,
                msg="TC-AC-005: dscratch0 access reports cmderr=2 (not "
                    "supported) -- a legitimate pass per spec #3.7.1.1's "
                    "discovery-by-attempting discipline",
            )
        readback = dm.read_gpr(DSCRATCH0_REGNO)
        ok = readback == pattern0
        return StepResult(
            ok=ok,
            msg=f"TC-AC-005: dscratch0 wrote 0x{pattern0:08x}, read back "
                f"0x{readback:08x}  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-AC-005: dscratch0 write/read-back", tc_ac_005)

    # ── TC-DCSR-003: dscratch0/1 survive a resume/halt cycle ──────────────
    def tc_dcsr_003():
        dm.write_gpr(DSCRATCH0_REGNO, pattern0)
        dm.write_gpr(DSCRATCH1_REGNO, pattern1)
        dm.resume()
        dm.halt()
        r0 = dm.read_gpr(DSCRATCH0_REGNO)
        r1 = dm.read_gpr(DSCRATCH1_REGNO)
        ok = (r0 == pattern0) and (r1 == pattern1)
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-003: dscratch0/1 after resume->halt: "
                f"0x{r0:08x}/0x{r1:08x}, expected 0x{pattern0:08x}/0x{pattern1:08x} "
                f"{'OK' if ok else 'MISMATCH'} (private Debug-Mode scratch, "
                f"must not be disturbed by the hart running)",
        )
    session.add_step(
        "TC-DCSR-003: dscratch0/1 preserved across resume/halt",
        tc_dcsr_003,
    )

    return session
