"""
sequences/mem_scan_sequence.py — Memory region scan sequence.

Reads N consecutive 32-bit words from a base address and compares
them against an optional expected pattern.

Shows how the same library (riscv_dm) is reused without any changes.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from debug_lib import RISCVDebug, DebugSession, StepResult


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


if __name__ == "__main__":
    import argparse, logging
    from debug_lib import UVMTransport, OpenOCDTransport, RISCVDebug

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",      choices=["batch", "interactive"], default="batch")
    parser.add_argument("--transport", choices=["uvm", "openocd"],       default="uvm")
    parser.add_argument("--sock",      default="/tmp/uvm_bridge.sock")
    parser.add_argument("--host",      default="127.0.0.1")
    parser.add_argument("--port",      type=int, default=6666)
    parser.add_argument("--base",      type=lambda x: int(x, 0), default=0x8000_0000)
    parser.add_argument("--count",     type=int, default=16)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")

    transport = UVMTransport(args.sock) if args.transport == "uvm" \
                else OpenOCDTransport(args.host, args.port)

    with transport:
        dm = RISCVDebug(transport)
        session = build_mem_scan_sequence(dm, args.base, args.count, mode=args.mode)
        session.run()
        sys.exit(0 if session.all_passed else 1)
