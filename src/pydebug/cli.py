#!/usr/bin/env python3
"""
cli.py — Master CLI for the pydebug framework.

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
    pydebug run --config configs/halt_test.json
    pydebug run --config configs/halt_test.json --transport uvm
    pydebug run --scenario halt --transport uvm --mode batch
    pydebug sources --c
    pydebug sources --sv
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
import shutil

from pydebug.api import UVMTransport, OpenOCDTransport, RISCVDebug

log = logging.getLogger(__name__)

# ── Scenario registry ─────────────────────────────────────────────────────────

# Maps scenario names to their module paths and builder functions.
SCENARIO_REGISTRY = {
    "halt": {
        "module": "pydebug.sequences.halt_sequence",
        "builder": "build_halt_sequence",
    },
    "read_dmstatus": {
        "module": "pydebug.sequences.read_dmstatus_sequence",
        "builder": "build_read_dmstatus_sequence",
    },
    "mem_scan": {
        "module": "pydebug.sequences.mem_scan_sequence",
        "builder": "build_mem_scan_sequence",
    },
    "run_control": {
        "module": "pydebug.sequences.run_control_sequence",
        "builder": "build_run_control_sequence",
    },
    "reset_ctrl": {
        "module": "pydebug.sequences.reset_ctrl_sequence",
        "builder": "build_reset_ctrl_sequence",
    },
    "halt_on_reset": {
        "module": "pydebug.sequences.halt_on_reset_sequence",
        "builder": "build_halt_on_reset_sequence",
    },
    "dm_activation": {
        "module": "pydebug.sequences.dm_activation_sequence",
        "builder": "build_dm_activation_sequence",
    },
    "hart_selection": {
        "module": "pydebug.sequences.hart_selection_sequence",
        "builder": "build_hart_selection_sequence",
    },
    "gpr_write": {
        "module": "pydebug.sequences.gpr_write_sequence",
        "builder": "build_gpr_write_sequence",
    },
    "csr_access": {
        "module": "pydebug.sequences.csr_access_sequence",
        "builder": "build_csr_access_sequence",
    },
    "program_buffer": {
        "module": "pydebug.sequences.program_buffer_sequence",
        "builder": "build_program_buffer_sequence",
    },
    "single_step": {
        "module": "pydebug.sequences.single_step_sequence",
        "builder": "build_single_step_sequence",
    },
    "sw_breakpoint_progbuf": {
        "module": "pydebug.sequences.sw_breakpoint_progbuf_sequence",
        "builder": "build_sw_breakpoint_progbuf_sequence",
    },
    "external_trigger": {
        "module": "pydebug.sequences.external_trigger_sequence",
        "builder": "build_external_trigger_sequence",
    },
    "sba": {
        "module": "pydebug.sequences.sba_sequence",
        "builder": "build_sba_sequence",
    },
    "report_halt_status": {
        "module": "pydebug.sequences.report_halt_status_sequence",
        "builder": "build_report_halt_status_sequence",
    },
    "discovery": {
        "module": "pydebug.sequences.discovery_sequence",
        "builder": "build_discovery_sequence",
    },
    "trigger": {
        "module": "pydebug.sequences.trigger_sequence",
        "builder": "build_trigger_sequence",
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


# ── Shared: bring up whichever transport a config asks for ────────────────────
#
# Factored out of cmd_run unchanged (same logic, same log lines, same
# timeouts/behavior) so cmd_interactive can reuse it — cmd_run's own
# behavior is not modified by this extraction.

def connect_transport(cfg):
    """
    Start (if needed) and connect the transport described by `cfg`.
    Returns (transport, openocd_proc). Caller is responsible for
    `transport.connect()`'s context (e.g. `with transport:`) and for
    terminating `openocd_proc` (if not None) when done.
    """
    openocd_proc = None
    if cfg["transport"] == "openocd":
        ocd_cfg = cfg.get("openocd", {})
        ocd_bin = ocd_cfg.get("bin", "*openocd*")

        if ocd_bin == "*openocd*":
            ocd_bin = shutil.which("openocd") or "openocd"
        ocd_config_raw = ocd_cfg.get("config", "openocd_bitbang.cfg")
        # Resolve relative config names against cwd
        if not os.path.isabs(ocd_config_raw):
            ocd_config = os.path.join(os.getcwd(), ocd_config_raw)
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

    return transport, openocd_proc


# ── Sub-command: run ──────────────────────────────────────────────────────────

def cmd_run(args):
    """Execute a debug scenario."""
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

    transport, openocd_proc = connect_transport(cfg)

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


# ── Sub-command: interactive ──────────────────────────────────────────────────

def cmd_interactive(args):
    """Connect to a running target and drop into a live, GDB-style REPL."""
    from pydebug.api.interactive_shell import RiscvDebugShell

    cfg = {
        "transport": args.transport or "uvm",
        "uvm": {"socket_path": args.socket_path} if args.socket_path else {},
        "openocd": {},
    }
    if args.openocd_config:
        cfg["openocd"]["config"] = args.openocd_config
    if args.openocd_host:
        cfg["openocd"]["host"] = args.openocd_host
    if args.openocd_port:
        cfg["openocd"]["port"] = args.openocd_port

    log.info("Connecting (transport=%s) for an interactive session...", cfg["transport"])
    transport, openocd_proc = connect_transport(cfg)

    try:
        with transport:
            dm = RISCVDebug(transport)
            RiscvDebugShell(dm).cmdloop()
    finally:
        if openocd_proc:
            log.info("Terminating OpenOCD subprocess")
            openocd_proc.terminate()
            openocd_proc.wait(timeout=2.0)


# ── Sub-command: sources ──────────────────────────────────────────────────────

def cmd_sources(args):
    """Print paths to shipped C or SV source files."""
    from pydebug.bridge_utils import (
        get_c_bridge_dir, get_sv_kit_dir,
        get_c_bridge_files, get_sv_kit_files,
    )

    if args.c_dir:
        print(get_c_bridge_dir())
    elif args.sv_dir:
        print(get_sv_kit_dir())
    elif args.c:
        for f in get_c_bridge_files():
            print(f)
    elif args.sv:
        for f in get_sv_kit_files():
            print(f)
    else:
        print("C bridge sources:")
        for f in get_c_bridge_files():
            print(f"  {f}")
        print(f"\nSV integration kit:")
        for f in get_sv_kit_files():
            print(f"  {f}")
        print(f"\nC bridge dir:  {get_c_bridge_dir()}")
        print(f"SV kit dir:    {get_sv_kit_dir()}")


# ── Sub-command: init ─────────────────────────────────────────────────────────

def cmd_init(args):
    """Copy template files into a target directory for quick integration."""
    from pydebug.bridge_utils import get_template_dir, get_example_configs_dir

    output = args.output or "."
    os.makedirs(output, exist_ok=True)

    template_dir = get_template_dir()
    configs_dir = get_example_configs_dir()

    # Copy template testbench if specified
    if args.template:
        pattern = f"tb_top_{args.template}"
        found = False
        for f in template_dir.iterdir():
            if pattern in f.name:
                dst = os.path.join(output, f.name)
                shutil.copy2(f, dst)
                print(f"  Copied {f.name} → {dst}")
                found = True
        if not found:
            available = [f.stem for f in template_dir.glob("*.sv")]
            print(f"  Template '{args.template}' not found. Available: {available}")
            sys.exit(1)

    # Copy example configs
    configs_out = os.path.join(output, "configs")
    os.makedirs(configs_out, exist_ok=True)
    for f in configs_dir.iterdir():
        dst = os.path.join(configs_out, f.name)
        shutil.copy2(f, dst)
        print(f"  Copied {f.name} → {dst}")

    print(f"\n  ✅ pydebug integration files written to {output}/")
    print(f"  Edit the testbench top as needed, then run your simulation.")


# ── Main entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="pydebug",
        description="PyDebug — RISC-V Debug Compliance Framework",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── run ──
    run_parser = subparsers.add_parser("run", help="Execute a debug scenario")
    run_parser.add_argument("--config", "-c", help="Path to JSON config file")
    run_parser.add_argument("--scenario", "-s", help="Scenario name (overrides config)")
    run_parser.add_argument("--transport", "-t", choices=["uvm", "openocd"],
                            help="Transport type (overrides config)")
    run_parser.add_argument("--mode", "-m", choices=["batch", "interactive"],
                            help="Execution mode (overrides config)")
    run_parser.add_argument("--openocd-config", help="Path to OpenOCD config file")

    # ── interactive ──
    interactive_parser = subparsers.add_parser(
        "interactive", help="Connect to a running target and drop into a live REPL"
    )
    interactive_parser.add_argument("--transport", "-t", choices=["uvm", "openocd"],
                                     default="uvm", help="Transport type (default: uvm)")
    interactive_parser.add_argument("--socket-path", help="UVM bridge Unix socket path override")
    interactive_parser.add_argument("--openocd-config", help="Path to OpenOCD config file")
    interactive_parser.add_argument("--openocd-host", help="OpenOCD TCL host override")
    interactive_parser.add_argument("--openocd-port", type=int, help="OpenOCD TCL port override")

    # ── sources ──
    sources_parser = subparsers.add_parser("sources", help="Show shipped source file paths")
    sources_parser.add_argument("--c", action="store_true", help="Show C bridge sources only")
    sources_parser.add_argument("--sv", action="store_true", help="Show SV kit sources only")
    sources_parser.add_argument("--c-dir", action="store_true", help="Show only the C bridge directory")
    sources_parser.add_argument("--sv-dir", action="store_true", help="Show only the SV kit root directory")

    # `--log-level` is defined on the top-level parser (above), which only
    # recognizes it *before* the subcommand name -- but every real call site
    # in this project's Makefiles (soc_openocd, soc_interactive) passes it
    # *after* (e.g. `pydebug run --transport openocd ... --log-level DEBUG`),
    # which argparse's subparser mechanism otherwise rejects outright
    # ("unrecognized arguments"). Re-declaring the same flag on each
    # subparser with default=SUPPRESS makes both positions work: if the user
    # doesn't pass it at the subcommand level, SUPPRESS means it's simply
    # absent from that parser's contribution to the namespace, so it doesn't
    # clobber whatever the top-level parser already set.
    for _p in (run_parser, interactive_parser, sources_parser):
        _p.add_argument("--log-level", default=argparse.SUPPRESS,
                         help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    # ── init ──
    init_parser = subparsers.add_parser("init", help="Copy integration templates to a directory")
    # Not restricted to a fixed enum: cmd_init already matches any
    # tb_top_<template>.sv found in the shipped templates dir, so a new SoC
    # only needs a template file added, not a change here.
    init_parser.add_argument("--template",
                             help="Which testbench template to copy "
                                  "(e.g. standalone, ibex, cva6, or a custom one)")
    init_parser.add_argument("--output", "-o", help="Output directory (default: cwd)")
    init_parser.add_argument("--log-level", default=argparse.SUPPRESS,
                              help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    if args.command == "run":
        cmd_run(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    elif args.command == "sources":
        cmd_sources(args)
    elif args.command == "init":
        cmd_init(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
