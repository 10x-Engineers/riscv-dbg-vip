#!/usr/bin/env python3
"""
run_benchmark.py — Transport-latency benchmark: PyDebug (direct UVM socket)
vs. OpenOCD + Remote Bit-Bang (RBB).

Both transports expose the identical `pydebug.api.RISCVDebug` surface (see
`src/pydebug/api/transport.py`) — this script drives the same sequence of
DMI-level operations against whichever one is selected and times every
individual operation, so the two runs are directly comparable.

Two invocation modes, matching how each transport is actually wired up in
this project (see cva6_sim/Makefile and ibex_sim/Makefile's `soc_test` vs
`soc_openocd` targets — this script's two modes are the exact same split,
just pointed at a benchmark body instead of a scenario config):

  --mode uvm
      Meant to be launched BY the simulator itself, the same way every
      other scenario's PYTHON_SEQ is (`rv_dbg_base_test.sv` runs
      `python3 -u <PYTHON_SEQ> &` from inside `run_phase`, then starts the
      C bridge's Unix-socket server). Connects over the Unix domain socket
      the C DPI bridge (`uvm_bridge.c`) exposes — no TCP, no bit-banging,
      one process hop.

  --mode openocd
      Meant to be launched EXTERNALLY, after a simulation with
      `+JTAG_MASTER=openocd` is already running and its remote-bitbang
      server is listening (see `scripts/launch_rbb_sim.sh`). This script
      spawns `openocd` itself pointed at the given RBB config, waits for
      JTAG examination to succeed, then drives the identical benchmark body
      over OpenOCD's TCL command port. Every operation crosses: Python ->
      TCP -> OpenOCD -> (bit-bang encode) -> TCP -> RBB DPI server ->
      simulator, and back.

Output: a single JSON file with per-phase and per-operation timing, meant
to be fed to `python/compare_transports.py` for the side-by-side report.
"""

import argparse
import json
import os
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time

from pydebug.api import UVMTransport, OpenOCDTransport, RISCVDebug
from pydebug.api.riscv_dm import DMI, dmcontrol
from pydebug.api.transport import TransportError


def timed(fn):
    """Run fn(), return (elapsed_seconds, return_value)."""
    t0 = time.perf_counter()
    result = fn()
    t1 = time.perf_counter()
    return t1 - t0, result


def stats(samples):
    """Summary stats for a list of per-op latencies (seconds)."""
    if not samples:
        return {"n": 0}
    ordered = sorted(samples)
    n = len(ordered)
    return {
        "n": n,
        "min_s": ordered[0],
        "max_s": ordered[-1],
        "mean_s": statistics.mean(ordered),
        "median_s": statistics.median(ordered),
        "stdev_s": statistics.stdev(ordered) if n > 1 else 0.0,
        "p95_s": ordered[int(round(0.95 * (n - 1)))],
        "total_s": sum(ordered),
    }


# ── Benchmark body — identical operation sequence for both transports ───────

def run_benchmark_body(dm: RISCVDebug, iterations: int, mem_addr: int) -> dict:
    result = {}

    # dmactive=1, no other side effect — safe to repeat, timed individually
    # as the "raw register write" primitive (single DMI write, no polling).
    idle_dmcontrol = dmcontrol(dmactive=True)

    t_activate, _ = timed(dm.activate)
    result["activate_s"] = t_activate

    t_halt, _ = timed(dm.halt)
    result["halt_s"] = t_halt

    # -- Raw register read latency: single DMI read, no abstract command,
    #    no polling loop (dmstatus). This is the closest proxy to "one DMI
    #    transaction" latency the spec exposes. --
    reg_read_samples = []
    for _ in range(iterations):
        dt, _ = timed(lambda: dm.t.read(DMI.DMSTATUS))
        reg_read_samples.append(dt)
    result["register_read"] = stats(reg_read_samples)

    # -- Raw register write latency: single idempotent DMI write. --
    reg_write_samples = []
    for _ in range(iterations):
        dt, _ = timed(lambda: dm.t.write(DMI.DMCONTROL, idle_dmcontrol))
        reg_write_samples.append(dt)
    result["register_write"] = stats(reg_write_samples)

    # -- GPR read via abstract command (write command + poll abstractcs +
    #    read data0 -- 2-3 DMI transactions per call). Representative of a
    #    real debugger "read a register" operation, not just a raw DMI op. --
    gpr_read_samples = []
    for _ in range(iterations):
        dt, _ = timed(lambda: dm.read_gpr(0x1001))  # x1 / ra
        gpr_read_samples.append(dt)
    result["gpr_read"] = stats(gpr_read_samples)

    gpr_write_samples = []
    for i in range(iterations):
        dt, _ = timed(lambda i=i: dm.write_gpr(0x1005, 0xDEAD_0000 | i))  # x5 / t0, scratch
        gpr_write_samples.append(dt)
    result["gpr_write"] = stats(gpr_write_samples)

    # -- Memory access via System Bus Access (sbcs+sbaddress0 [+sbdata0] +
    #    poll sbcs.sbbusy). --
    mem_write_samples = []
    for i in range(iterations):
        dt, _ = timed(lambda i=i: dm.write_mem32(mem_addr, 0xC0FFEE00 | i))
        mem_write_samples.append(dt)
    result["mem_write32"] = stats(mem_write_samples)

    mem_read_samples = []
    for _ in range(iterations):
        dt, _ = timed(lambda: dm.read_mem32(mem_addr))
        mem_read_samples.append(dt)
    result["mem_read32"] = stats(mem_read_samples)

    total_ops = (
        2  # activate + halt
        + len(reg_read_samples) + len(reg_write_samples)
        + len(gpr_read_samples) + len(gpr_write_samples)
        + len(mem_write_samples) + len(mem_read_samples)
    )
    total_time = (
        t_activate + t_halt
        + sum(reg_read_samples) + sum(reg_write_samples)
        + sum(gpr_read_samples) + sum(gpr_write_samples)
        + sum(mem_write_samples) + sum(mem_read_samples)
    )
    result["total_ops"] = total_ops
    result["total_time_s"] = total_time
    result["throughput_ops_per_s"] = total_ops / total_time if total_time > 0 else 0.0
    return result


# ── Mode: uvm (launched in-process by the simulator) ────────────────────────

def run_uvm(args) -> dict:
    output = {"transport": "uvm", "phases": {}}

    t_wait, _ = timed(lambda: _wait_for_path(args.socket_path, args.startup_wait))
    output["phases"]["socket_wait_s"] = t_wait

    transport = UVMTransport(socket_path=args.socket_path, timeout=args.timeout)
    t_connect, _ = timed(transport.connect)
    output["phases"]["connect_s"] = t_connect

    try:
        dm = RISCVDebug(transport)
        output["benchmark"] = run_benchmark_body(dm, args.iterations, args.mem_addr)
    finally:
        transport.disconnect()

    return output


def _wait_for_path(path: str, timeout: float) -> None:
    deadline = time.time() + timeout
    while not os.path.exists(path):
        if time.time() >= deadline:
            raise TimeoutError(f"UVM bridge socket {path!r} never appeared")
        time.sleep(0.05)


# ── Mode: openocd (launched externally, spawns openocd itself) ─────────────

def run_openocd(args) -> dict:
    output = {"transport": "openocd", "phases": {}}

    ocd_bin = shutil.which("openocd") or "openocd"
    ocd_config = os.path.abspath(args.openocd_config)

    exam_event = threading.Event()
    exam_failed = threading.Event()
    log_lines = []

    def stream(pipe):
        for raw in iter(pipe.readline, b""):
            line = raw.decode(errors="replace").rstrip()
            log_lines.append(line)
            if "Examination succeed" in line or "Examined RISC-V core" in line:
                exam_event.set()
            elif "Examination failed" in line:
                exam_failed.set()

    t_spawn_start = time.perf_counter()
    proc = subprocess.Popen(
        [ocd_bin, "-f", ocd_config],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    t = threading.Thread(target=stream, args=(proc.stdout,), daemon=True)
    t.start()

    deadline = time.time() + args.startup_wait
    while not exam_event.is_set():
        if exam_failed.is_set():
            proc.terminate()
            raise RuntimeError("OpenOCD JTAG examination failed:\n" + "\n".join(log_lines[-20:]))
        if proc.poll() is not None:
            raise RuntimeError(f"OpenOCD exited early (rc={proc.returncode}):\n" + "\n".join(log_lines[-20:]))
        if time.time() >= deadline:
            proc.terminate()
            raise TimeoutError("Timed out waiting for OpenOCD JTAG examination")
        time.sleep(0.05)
    output["phases"]["openocd_spawn_to_examined_s"] = time.perf_counter() - t_spawn_start

    transport = OpenOCDTransport(host=args.openocd_host, port=args.openocd_port, timeout=args.timeout)
    try:
        deadline = time.time() + args.startup_wait
        t_connect_start = time.perf_counter()
        connected = False
        while time.time() < deadline:
            try:
                transport.connect()
                connected = True
                break
            except (TransportError, OSError):
                if proc.poll() is not None:
                    raise RuntimeError(f"OpenOCD exited early (rc={proc.returncode})")
                time.sleep(0.1)
        if not connected:
            raise TimeoutError("Timed out connecting to OpenOCD TCL port")
        output["phases"]["connect_s"] = time.perf_counter() - t_connect_start

        dm = RISCVDebug(transport)
        output["benchmark"] = run_benchmark_body(dm, args.iterations, args.mem_addr)
    finally:
        transport.disconnect() if transport.connected else None
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()

    return output


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["uvm", "openocd"], required=True)
    p.add_argument("--iterations", type=int, default=20, help="repetitions per operation kind")
    p.add_argument("--mem-addr", type=lambda s: int(s, 0), default=0x8000_0000)
    p.add_argument("--timeout", type=float, default=30.0, help="per-transaction transport timeout (s)")
    p.add_argument("--startup-wait", type=float, default=60.0, help="max wait for backend to come up (s)")
    p.add_argument("--output", required=True, help="path to write the JSON results file")

    # uvm mode
    p.add_argument("--socket-path", default="/tmp/uvm_bridge.sock")

    # openocd mode
    p.add_argument("--openocd-config", help="path to an OpenOCD .cfg pointed at the RBB server")
    p.add_argument("--openocd-host", default="127.0.0.1")
    p.add_argument("--openocd-port", type=int, default=6666)

    args = p.parse_args()

    if args.mode == "openocd" and not args.openocd_config:
        p.error("--mode openocd requires --openocd-config")

    t0 = time.perf_counter()
    if args.mode == "uvm":
        result = run_uvm(args)
    else:
        result = run_openocd(args)
    result["wall_clock_total_s"] = time.perf_counter() - t0
    result["iterations"] = args.iterations

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[run_benchmark] mode={args.mode} wrote {args.output}")
    print(json.dumps(result.get("benchmark", {}).get("throughput_ops_per_s"), default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- top-level CLI entry, must not traceback-spam the sim log
        print(f"[run_benchmark] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
