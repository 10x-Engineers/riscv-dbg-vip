"""
sequences/report_halt_status_sequence.py — Report hart halt status via the
halt-status summary (spec #3.14.9, Ch.3 op 3).

`haltsum0` is a bitmap: bit i is set iff hart i (within the low 32-hart window)
is halted. This test reads it in both states — with the hart running (bit clear)
and halted (bit set) — which is the only way to prove the summary tracks the
hart's actual run state rather than reading a constant.

`read_haltsum0()` is a new `riscv_dm` primitive added alongside this sequence.

Traces to: TC-DHS-001

Usage:
    from pydebug.sequences.report_halt_status_sequence import build_report_halt_status_sequence
    session = build_report_halt_status_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult


def build_report_halt_status_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    hart: int = 0,
) -> DebugSession:
    """
    Build a DebugSession that reads haltsum0 while the hart is running and then
    while it is halted, confirming the hart's summary bit follows its state
    (spec #3.14.9, TC-DHS-001).

    Traces to: TC-DHS-001
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-DHS-001 (part 1): running hart -> its haltsum0 bit is clear ────
    def tc_dhs_001_running():
        summ = dm.read_haltsum0()
        bit = (summ >> hart) & 1
        ok = bit == 0
        return StepResult(
            ok=ok,
            msg=f"TC-DHS-001: haltsum0=0x{summ:08x} while running, "
                f"hart{hart} bit={bit} (expect 0)  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-DHS-001: haltsum0 with hart running", tc_dhs_001_running)

    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-DHS-001 (part 2): halted hart -> its haltsum0 bit is set ───────
    def tc_dhs_001_halted():
        summ = dm.read_haltsum0()
        bit = (summ >> hart) & 1
        ok = bit == 1
        return StepResult(
            ok=ok,
            msg=f"TC-DHS-001: haltsum0=0x{summ:08x} while halted, "
                f"hart{hart} bit={bit} (expect 1)  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-DHS-001: haltsum0 with hart halted", tc_dhs_001_halted)

    return session
