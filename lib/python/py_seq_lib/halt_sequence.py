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

Usage (batch, UVM):
    python run.py --mode batch --transport uvm

Usage (interactive, OpenOCD):
    python run.py --mode interactive --transport openocd --host 127.0.0.1 --port 6666

Usage (direct from Python):
    from debug_lib import UVMTransport, RISCVDebug, DebugSession
    from sequences.halt_sequence import build_halt_sequence

    with UVMTransport() as t:
        dm = RISCVDebug(t)
        session = build_halt_sequence(dm, mode="batch", mem_addr=0x80000000)
        session.run()
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rv_dbg_python_api import RISCVDebug, DebugSession, StepResult


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


# ── Standalone entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from rv_dbg_python_api import UVMTransport, OpenOCDTransport, RISCVDebug

    parser = argparse.ArgumentParser(description="Halt sequence")
    parser.add_argument("--mode",      choices=["batch", "interactive"], default="batch")
    parser.add_argument("--transport", choices=["uvm", "openocd"],       default="uvm")
    parser.add_argument("--sock",      default="/tmp/uvm_bridge.sock",   help="UVM socket path")
    parser.add_argument("--host",      default="127.0.0.1",              help="OpenOCD host")
    parser.add_argument("--port",      type=int, default=6666,           help="OpenOCD port")
    parser.add_argument("--mem-addr",  type=lambda x: int(x, 0), default=0x8000_0000)
    parser.add_argument("--resume",    action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    import logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    # ── Select transport (the only API difference between UVM and OpenOCD) ──
    if args.transport == "uvm":
        transport = UVMTransport(socket_path=args.sock)
    else:
        transport = OpenOCDTransport(host=args.host, port=args.port)

    with transport:
        dm      = RISCVDebug(transport)
        session = build_halt_sequence(
            dm,
            mode=args.mode,
            mem_addr=args.mem_addr,
            resume_after=args.resume,
        )
        session.run()
        sys.exit(0 if session.all_passed else 1)
