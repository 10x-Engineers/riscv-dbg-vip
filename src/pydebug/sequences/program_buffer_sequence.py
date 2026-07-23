"""
sequences/program_buffer_sequence.py — Program Buffer write/read-back and
execution via postexec (spec #3.8, Ch.3 op 8).

Nothing in `RISCVDebug` modeled the Program Buffer at all before this study
(no PROGBUF0-15 address, no postexec helper) -- `write_progbuf()`/
`read_progbuf()`/`execute_progbuf()` in `api/riscv_dm.py` are new, added
alongside this sequence.

Instruction encodings used here (plain RV32I, no assembler dependency):
    addi x5, x5, 1   = 0x00128293
    ebreak           = 0x00100073

Traces to: TC-AC-013, TC-PB-001, TC-PB-002, TC-PB-003

Usage:
    from pydebug.sequences.program_buffer_sequence import build_program_buffer_sequence
    session = build_program_buffer_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult

ADDI_X5_X5_1 = 0x00128293
EBREAK       = 0x00100073

#: GPR regno for x5/t0 (spec #3.7.1.1: x0=0x1000, so x5=0x1005).
X5_REGNO = 0x1005


def build_program_buffer_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build and return a DebugSession exercising the Program Buffer: discovery
    (abstractcs.progbufsize), write/read-back, write-isolation, and executing
    a short `addi x5,x5,1; ebreak` sequence via postexec.

    Traces to: TC-AC-013, TC-PB-001, TC-PB-002, TC-PB-003
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-AC-013: progbufsize/impebreak discovery (gate) ─────────────────
    progbufsize_holder: dict = {}

    def tc_ac_013():
        abstractcs = dm.read_abstractcs()
        progbufsize = (abstractcs >> 24) & 0x1F
        impebreak = bool((abstractcs >> 22) & 1)
        progbufsize_holder["size"] = progbufsize
        progbufsize_holder["impebreak"] = impebreak
        # progbufsize=0 means no Program Buffer at all -- everything below is N/A.
        return StepResult(
            ok=True,
            msg=f"TC-AC-013: abstractcs.progbufsize={progbufsize}, "
                f"impebreak={impebreak}  (gate for TC-PB-* below; "
                f"progbufsize=0 => Program Buffer not implemented, rest is N/A)",
        )
    session.add_step("TC-AC-013: abstractcs discovery", tc_ac_013)

    # ── TC-PB-001: write/read-back progbuf0/1 ─────────────────────────────
    def tc_pb_001():
        if progbufsize_holder.get("size", 0) < 2:
            return StepResult(ok=True, msg="TC-PB-001: N/A -- progbufsize < 2")
        dm.write_progbuf(0, ADDI_X5_X5_1)
        dm.write_progbuf(1, EBREAK)
        r0 = dm.read_progbuf(0)
        r1 = dm.read_progbuf(1)
        ok = (r0 == ADDI_X5_X5_1) and (r1 == EBREAK)
        return StepResult(
            ok=ok,
            msg=f"TC-PB-001: progbuf0=0x{r0:08x} (expect 0x{ADDI_X5_X5_1:08x}), "
                f"progbuf1=0x{r1:08x} (expect 0x{EBREAK:08x})  "
                f"{'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-PB-001: progbuf0/1 write/read-back", tc_pb_001)

    # ── TC-PB-002: write-isolation across progbuf slots ───────────────────
    def tc_pb_002():
        if progbufsize_holder.get("size", 0) < 2:
            return StepResult(ok=True, msg="TC-PB-002: N/A -- progbufsize < 2")
        before = dm.read_progbuf(1)
        dm.write_progbuf(0, 0xDEADBEEF)
        after = dm.read_progbuf(1)
        ok = before == after
        return StepResult(
            ok=ok,
            msg=f"TC-PB-002: progbuf1 before/after writing progbuf0: "
                f"0x{before:08x}/0x{after:08x}  "
                f"{'OK -- unaffected' if ok else 'FAIL -- disturbed'}",
        )
    session.add_step("TC-PB-002: progbuf1 unaffected by progbuf0 write", tc_pb_002)

    # ── TC-PB-003: execute addi x5,x5,1 ; ebreak via postexec ─────────────
    def tc_pb_003():
        if progbufsize_holder.get("size", 0) < 2:
            return StepResult(ok=True, msg="TC-PB-003: N/A -- progbufsize < 2")
        dm.write_gpr(X5_REGNO, 0)              # known baseline
        dm.write_progbuf(0, ADDI_X5_X5_1)
        dm.write_progbuf(1, EBREAK)
        dm.execute_progbuf()
        x5 = dm.read_gpr(X5_REGNO)
        ok = x5 == 1
        return StepResult(
            ok=ok,
            msg=f"TC-PB-003: x5 after addi-x5-x5-1;ebreak via postexec = "
                f"0x{x5:08x} (expect 0x00000001)  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step(
        "TC-PB-003: execute addi x5,x5,1; ebreak via postexec",
        tc_pb_003,
    )

    return session
