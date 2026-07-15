"""
sequences/mem_scan_sequence.py — Memory region scan sequence.

Reads N consecutive 32-bit words from a base address and compares
them against an optional expected pattern.

Shows how the same library (riscv_dm) is reused without any changes.
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult


def build_mem_scan_sequence(
    dm:         RISCVDebug,
    base_addr:  int,
    word_count: int = 16,
    expected:   list[int] | None = None,
    mode:       str = "batch",
) -> DebugSession:
    """
    Scan `word_count` 32-bit words starting at `base_addr`.
    If `expected` is provided, each word is checked against expected[i].
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate DM", lambda: dm.activate())
    session.add_step("Halt hart",   lambda: dm.halt())

    for i in range(word_count):
        addr = base_addr + i * 4
        exp  = expected[i] if (expected and i < len(expected)) else None

        def make_step(a=addr, e=exp, idx=i):
            def step():
                val = dm.read_mem32(a)
                if e is None:
                    return StepResult(ok=True, msg=f"[{idx:03d}] {a:#010x} = {val:#010x}")
                ok  = val == e
                return StepResult(
                    ok=ok,
                    msg=f"[{idx:03d}] {a:#010x} = {val:#010x}  "
                        f"expected {e:#010x}  {'✓' if ok else '✗ MISMATCH'}",
                )
            return step

        session.add_step(f"Read mem[{addr:#010x}]", make_step())

    return session
