# pydebug — RISC-V Debug Compliance Framework

A Python-based RISC-V Debug Module (DM) verification framework. The same
Python-driven debug scenarios run unchanged against **UVM simulation** (via a
C DPI-C Unix/TCP socket bridge) and **real hardware / FPGA emulation** (via
OpenOCD and JTAG) — one stimulus, no rewrite, only the transport config
changes. See `INTEGRATION_GUIDE.md` for the full integration/simulation/
emulation walkthrough, and `CVA6-fork`/`ibex-demo-system` (submodules of this
repo) for two complete worked examples.

## What's in this repo

```
pyproject.toml / setup.py   — the installable pydebug package
src/pydebug/                — the package itself (see below)
tests/                      — unit tests for the package (pytest)
cva6_sim/                   — worked example: pydebug <-> CVA6-fork (Questa)
ibex_sim/                   — worked example: pydebug <-> ibex-demo-system (Questa)
CVA6-fork/                  — submodule, 10x-Engineers/CVA6-fork
ibex-demo-system/           — submodule, 10x-Engineers/ibex-demo-system
INTEGRATION_GUIDE.md         — integrate a new SoC / run sim tests / run emulation
```

## Installation

```bash
pip install -e .           # development (editable) — recommended
pip install .              # production
pip install -e ".[test]"   # with test dependencies
```

Once installed, `pydebug` is on `PATH` and importable from **any** project —
it is not tied to this repo's own `cva6_sim`/`ibex_sim` directories. Any
Makefile, anywhere, can resolve its sources with `pydebug sources --c/--sv`
and drive it with `pydebug run` / `pydebug init`. See `INTEGRATION_GUIDE.md`
for the full checklist of integrating a new, unrelated project against it.

## Quick start

### As a CLI tool

```bash
# Run a scenario over UVM simulation (socket transport)
pydebug run -c configs/halt_uvm.json

# Run the same scenario against real hardware / emulation via OpenOCD
pydebug run --scenario halt --transport openocd --openocd-config configs/openocd_arty_a7_100t.cfg

# Print the shipped C bridge source paths (for wiring into any Makefile)
pydebug sources --c

# Print the shipped SV kit source paths (JTAG VIP, UVM env)
pydebug sources --sv

# Scaffold a new SoC integration from a template
pydebug init --template ibex --output ./my_debug_tb/
```

### As a Python API

```python
from pydebug import OpenOCDTransport, RISCVDebug

with OpenOCDTransport(host="127.0.0.1", port=6666) as t:
    dm = RISCVDebug(t)
    dm.activate()
    dm.halt()
    print(f"PC = {dm.get_pc():#010x}")
    dm.resume()
```

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         USER / INTEGRATOR                          │
│   CLI:  pydebug run -c halt_uvm.json                               │
│   API:  from pydebug import RISCVDebug, OpenOCDTransport            │
└───────────────┬──────────────────────────────┬─────────────────────┘
                │                              │
     ┌──────────▼──────────┐        ┌──────────▼───────────────┐
     │  RISCVDebug / DMI    │        │  DebugSession /          │
     │  (dm.halt(), ...)    │        │  scenario sequences      │
     └──────────┬──────────┘        └──────────┬───────────────┘
                │        DebugTransport (abstract)               │
     ┌──────────▼──────────┐        ┌──────────▼───────────────┐
     │   UVMTransport       │        │   OpenOCDTransport        │
     │   Unix/TCP socket    │        │   TCP port 6666, TCL      │
     └──────────┬──────────┘        └──────────┬───────────────┘
                │                              │
     ┌──────────▼──────────┐        ┌──────────▼───────────────┐
     │  C Bridge (DPI-C)     │        │  OpenOCD server           │
     └──────────┬──────────┘        └──────────┬───────────────┘
                │                              │
     ┌──────────▼──────────┐        ┌──────────▼───────────────┐
     │  UVM test task        │        │  Target board              │
     │  (rv_dbg_base_test)   │        │  (Arty A7 / Genesys2 / ...)│
     └──────────┬──────────┘        └──────────┬───────────────┘
                │                              │
     ┌──────────▼──────────────────────────────▼───────────────┐
     │      JTAG/DMI Agent (driver + monitor, sv_kit/)          │
     └───────────────────────────┬───────────────────────────┘
                                 ▼
                          DUT Debug Module
                        (Ibex / CVA6 / your SoC)
```

The seam is `DebugTransport`: everything above it (CLI, `RISCVDebug`,
sequences) never knows or cares whether it's driving a simulator or real
silicon. Swapping platforms is a config change, not a code change.

## Package layout (`src/pydebug/`)

| Path | Purpose |
|---|---|
| `api/` | `RISCVDebug`/`DMI` command layer, `DebugTransport`/`UVMTransport`/`OpenOCDTransport`, `DebugSession` |
| `sequences/` | Pre-built scenarios (halt, memory scan, CSR access, single-step, ...) |
| `sv_kit/` | Shared JTAG/DMI UVM VIP (agent, driver, monitor, scoreboard) + per-SoC `templates/` |
| `c_bridge/` | DPI-C bridge sources compiled into the simulator's shared object |
| `cli.py` | `pydebug` console-script entry point (`run`, `init`, `sources`) |
| `bridge_utils.py` | Resolves shipped C/SV source paths for `pydebug sources` |

## Running the package's own tests

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## License

Apache-2.0 — see `LICENSE`.
