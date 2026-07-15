"""
sequences/halt_sequence.py — Halt + inspect sequence.

This sequence:
    1. Activates the Debug Module
    2. Halts the hart
    3. Reads PC, sp (x2), ra (x1)
    4. Reads a memory word at a configurable address
    5. (Optional) resumes the hart

Supports both interactive and batch mode.
Supports both UVM and OpenOCD transports — just pass the right transport in.

Usage (direct from Python):
    from pydebug import UVMTransport, RISCVDebug
    from pydebug.sequences.halt_sequence import build_halt_sequence

    with UVMTransport() as t:
        dm = RISCVDebug(t)
        session = build_halt_sequence(dm, mode="batch", mem_addr=0x80000000)
        session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult


def build_halt_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    mem_addr: int = 0x8000_0000,
    resume_after: bool = False,
) -> DebugSession:
    """
    Build and return a DebugSession for halt + register inspection.
    The session is NOT run yet — call session.run() when ready.

    Args:
        dm:           RISCVDebug instance (already has transport attached)
        mode:         "batch" or "interactive"
        mem_addr:     32-bit address to read from target memory
        resume_after: if True, final step resumes the hart
    """
    session = DebugSession(mode=mode, stop_on_error=True)

    # ── Step 1: Activate DM ────────────────────────────────────────────────
    session.add_step(
        "Activate Debug Module (write dmcontrol.dmactive=1)",
        lambda: dm.activate(),
    )

    # ── Step 2: Halt ───────────────────────────────────────────────────────
    session.add_step(
        "Halt hart (write dmcontrol.haltreq=1, poll dmstatus.allhalted)",
        lambda: dm.halt(),
    )

    # ── Step 3: Verify halted ──────────────────────────────────────────────
    def check_halted():
        halted = dm.is_halted()
        return StepResult(
            ok=halted,
            msg=f"dmstatus.allhalted = {halted}",
        )
    session.add_step("Verify hart is halted (read dmstatus)", check_halted)

    # ── Step 4: Read PC ────────────────────────────────────────────────────
    def read_pc():
        pc = dm.get_pc()
        return StepResult(ok=True, msg=f"PC = {pc:#010x}")
    session.add_step("Read PC (abstract command on DPC CSR 0x7B1)", read_pc)

    # ── Step 5: Read ra (x1) ───────────────────────────────────────────────
    def read_ra():
        ra = dm.read_gpr(0x1001)   # GPR regno: x0=0x1000, x1=0x1001
        return StepResult(ok=True, msg=f"ra (x1) = {ra:#010x}")
    session.add_step("Read ra / x1 (abstract GPR access regno=0x1001)", read_ra)

    # ── Step 6: Read sp (x2) ───────────────────────────────────────────────
    def read_sp():
        sp = dm.read_gpr(0x1002)
        return StepResult(ok=True, msg=f"sp (x2) = {sp:#010x}")
    session.add_step("Read sp / x2 (abstract GPR access regno=0x1002)", read_sp)

    # ── Step 7: Read memory ────────────────────────────────────────────────
    def read_memory():
        val = dm.read_mem32(mem_addr)
        return StepResult(ok=True, msg=f"mem[{mem_addr:#010x}] = {val:#010x}")
    session.add_step(
        f"Read memory word at {mem_addr:#010x} (system bus access)",
        read_memory,
    )

    # ── Step 8 (optional): Resume ──────────────────────────────────────────
    if resume_after:
        def resume_core():
            dm.resume()
            running = dm.is_running()
            return StepResult(
                ok=running,
                msg=f"dmstatus.allrunning = {running}",
            )
        session.add_step(
            "Resume hart (write dmcontrol.resumereq=1, poll dmstatus.allrunning)",
            resume_core,
        )

    return session
