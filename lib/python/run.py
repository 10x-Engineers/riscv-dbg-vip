#!/usr/bin/env python3
"""
run.py — Master runner for pydebug test scenarios.

Reads a JSON test configuration file and executes the specified debug scenario
using the appropriate transport (UVM simulation or OpenOCD hardware).

JSON config format:
    {
        "scenario":  "halt",
        "transport": "uvm",
        "mode":      "batch",
        "params": {
            "mem_addr":     "0x80000000",
            "resume_after": false
        },
        "uvm": {
            "socket_path": "/tmp/uvm_bridge.sock",
            "timeout":     10.0
        },
        "openocd": {
            "host": "127.0.0.1",
            "port": 6666
        }
    }

Usage:
    python3 run.py --config configs/halt_test.json
    python3 run.py --config configs/halt_test.json --transport uvm
    python3 run.py --scenario halt --transport uvm --mode batch
"""

import sys
import os
import json
import argparse
import logging
import importlib
import subprocess
import threading
import time

PYTHON_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(PYTHON_DIR, "..", ".."))
sys.path.insert(0, PYTHON_DIR)
sys.path.insert(0, ROOT_DIR)

from rv_dbg_python_api import UVMTransport, OpenOCDTransport, RISCVDebug

log = logging.getLogger(__name__)

# ── Scenario registry ─────────────────────────────────────────────────────────

# Maps scenario names to their module paths and builder functions.
# Each builder function signature: build_<name>(dm, mode, **params) -> DebugSession
SCENARIO_REGISTRY = {
    "halt": {
        "module": "py_seq_lib.halt_sequence",
        "builder": "build_halt_sequence",
    },
    "read_dmstatus": {
        "module": "py_seq_lib.read_dmstatus_sequence",
        "builder": "build_read_dmstatus_sequence",
    },
    "mem_scan": {
        "module": "py_seq_lib.mem_scan_sequence",
        "builder": "build_mem_scan_sequence",
    },
}


def load_config(config_path: str) -> dict:
    """Load and validate a JSON config file."""
    with open(config_path, "r") as f:
        cfg = json.load(f)

    # Defaults
    cfg.setdefault("scenario", "halt")
    cfg.setdefault("transport", "uvm")
    cfg.setdefault("mode", "batch")
    cfg.setdefault("params", {})
    cfg.setdefault("uvm", {})
    cfg.setdefault("openocd", {})

    return cfg


def create_transport(cfg: dict):
    """Create the appropriate transport based on config."""
    transport_name = cfg["transport"]

    if transport_name == "uvm":
        uvm_cfg = cfg.get("uvm", {})
        return UVMTransport(
            socket_path=uvm_cfg.get("socket_path", "/tmp/uvm_bridge.sock"),
            timeout=uvm_cfg.get("timeout", 10.0),
        )
    elif transport_name == "openocd":
        ocd_cfg = cfg.get("openocd", {})
        return OpenOCDTransport(
            host=ocd_cfg.get("host", "127.0.0.1"),
            port=ocd_cfg.get("port", 6666),
        )
    else:
        raise ValueError(f"Unknown transport: {transport_name!r}")


def load_scenario_builder(scenario_name: str):
    """Dynamically load the builder function for a scenario."""
    if scenario_name not in SCENARIO_REGISTRY:
        raise ValueError(
            f"Unknown scenario: {scenario_name!r}. "
            f"Available: {list(SCENARIO_REGISTRY.keys())}"
        )

    entry = SCENARIO_REGISTRY[scenario_name]
    module = importlib.import_module(entry["module"])
    builder = getattr(module, entry["builder"])
    return builder


def convert_params(params: dict) -> dict:
    """Convert string hex values to integers in params."""
    converted = {}
    for k, v in params.items():
        if isinstance(v, str) and v.startswith("0x"):
            converted[k] = int(v, 16)
        else:
            converted[k] = v
    return converted


def main():
    parser = argparse.ArgumentParser(
        description="Pydebug master runner — JSON-driven debug test execution"
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to JSON config file"
    )
    parser.add_argument(
        "--scenario", "-s",
        help="Scenario name (overrides config)"
    )
    parser.add_argument(
        "--transport", "-t",
        choices=["uvm", "openocd"],
        help="Transport type (overrides config)"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["batch", "interactive"],
        help="Execution mode (overrides config)"
    )
    parser.add_argument(
        "--openocd-config",
        help="Path to OpenOCD config file (overrides JSON config)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    # Load config (from file or defaults)
    if args.config:
        cfg = load_config(args.config)
        log.info("Loaded config from %s", args.config)
    else:
        cfg = {
            "scenario": "halt",
            "transport": "uvm",
            "mode": "batch",
            "params": {},
            "uvm": {},
            "openocd": {},
        }

    # CLI overrides
    if args.scenario:
        cfg["scenario"] = args.scenario
    if args.transport:
        cfg["transport"] = args.transport
    if args.mode:
        cfg["mode"] = args.mode
    if args.openocd_config:
        cfg["openocd"]["config"] = args.openocd_config

    log.info("Scenario=%s  Transport=%s  Mode=%s",
             cfg["scenario"], cfg["transport"], cfg["mode"])

    # Load scenario builder
    builder = load_scenario_builder(cfg["scenario"])

    # Convert params
    params = convert_params(cfg.get("params", {}))

    # Create transport and run
    openocd_proc = None
    if cfg["transport"] == "openocd":
        ocd_cfg = cfg.get("openocd", {})
        import shutil
        # You requested asterisks to find openocd at any path:
        ocd_bin = ocd_cfg.get("bin", "*openocd*")
        
        # NOTE: Python's subprocess.Popen does not automatically expand '*' wildcards like bash does!
        # If you want Python to search all directories in your system PATH for openocd, 
        # the standard Pythonic way is to use shutil.which:
        if ocd_bin == "*openocd*":
            ocd_bin = shutil.which("openocd") or "openocd"
        ocd_config_raw = ocd_cfg.get("config", "openocd_bitbang.cfg")
        # Resolve relative config names against the configs directory
        if not os.path.isabs(ocd_config_raw):
            ocd_config = os.path.join(ROOT_DIR, "configs", ocd_config_raw)
        else:
            ocd_config = ocd_config_raw
        ocd_wait = ocd_cfg.get("startup_wait", 60.0)

        log.info("Starting OpenOCD: %s -f %s", ocd_bin, ocd_config)
        openocd_proc = subprocess.Popen(
            [ocd_bin, "-f", ocd_config],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # ── Wait for successful JTAG examination before connecting ────────
        # Monitor OpenOCD's stdout for "Examination succeed".  This ensures
        # the TAP was found, dtmcontrol was read, and the target is ready
        # before Python ever touches the TCL port.
        exam_event = threading.Event()
        exam_failed = threading.Event()

        def stream_and_watch(pipe):
            for raw in iter(pipe.readline, b''):
                line = raw.decode(errors='replace').rstrip()
                print(f"[OpenOCD] {line}")
                if "Examination succeed" in line or "Examined RISC-V core" in line:
                    exam_event.set()
                elif "Examination failed" in line:
                    exam_failed.set()

        t = threading.Thread(target=stream_and_watch,
                             args=(openocd_proc.stdout,), daemon=True)
        t.start()

        log.info("Waiting up to %.0fs for OpenOCD examination...", ocd_wait)
        deadline = time.time() + ocd_wait
        while not exam_event.is_set():
            if exam_failed.is_set():
                log.error("OpenOCD JTAG examination failed — aborting")
                openocd_proc.terminate()
                sys.exit(1)
            if openocd_proc.poll() is not None:
                log.error("OpenOCD exited prematurely (rc=%d) before examination",
                          openocd_proc.returncode)
                sys.exit(1)
            if time.time() >= deadline:
                log.error("Timed out waiting for OpenOCD examination to succeed")
                openocd_proc.terminate()
                sys.exit(1)
            time.sleep(0.25)

        log.info("OpenOCD examination succeeded — connecting to TCL port")

    # ── UVM: wait for the simulation bridge socket to appear ──────────────────
    if cfg["transport"] == "uvm":
        uvm_cfg = cfg.get("uvm", {})
        sock_path = uvm_cfg.get("socket_path", "/tmp/uvm_bridge.sock")
        uvm_wait  = uvm_cfg.get("startup_wait", 60.0)
        deadline  = time.time() + uvm_wait
        log.info("Waiting up to %.0fs for UVM socket %s ...", uvm_wait, sock_path)
        while not os.path.exists(sock_path):
            if time.time() >= deadline:
                log.error(
                    "Timed out waiting for UVM bridge socket %s — "
                    "is the simulation running?", sock_path
                )
                sys.exit(1)
            time.sleep(0.25)
        log.info("UVM bridge socket detected — proceeding to connect")

    transport = create_transport(cfg)

    # If using OpenOCD, retry connect until TCL port is ready
    if cfg["transport"] == "openocd" and openocd_proc:
        ocd_cfg = cfg.get("openocd", {})
        ocd_wait = ocd_cfg.get("startup_wait", 30.0)
        deadline = time.time() + ocd_wait
        connected = False
        while time.time() < deadline:
            try:
                transport.connect()
                connected = True
                break
            except Exception:
                if openocd_proc.poll() is not None:
                    log.error("OpenOCD process exited prematurely (rc=%d)", openocd_proc.returncode)
                    sys.exit(1)
                time.sleep(0.5)
        if not connected:
            log.error("Timed out waiting for OpenOCD TCL port")
            openocd_proc.terminate()
            sys.exit(1)
    

    try:
        with transport:
            dm = RISCVDebug(transport)
            session = builder(dm, mode=cfg["mode"], **params)
            session.run()
            sys.exit(0 if session.all_passed else 1)
    finally:
        if openocd_proc:
            log.info("Terminating OpenOCD subprocess")
            openocd_proc.terminate()
            openocd_proc.wait(timeout=2.0)


if __name__ == "__main__":
    main()
