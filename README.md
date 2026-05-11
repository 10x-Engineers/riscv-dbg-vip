# Pydebug: RISC-V Debug Compliance Framework

A dual-transport Python framework for RISC-V Debug Module verification. The same
debug scenarios run against both **UVM simulation** (via C DPI bridge) and
**real hardware** (via OpenOCD), driven by JSON configuration files.

---

## Directory Structure

```
pydebug/
├── configs/                 # JSON test configurations
│   ├── halt_uvm.json        #   Halt scenario → UVM simulation
│   └── halt_openocd.json    #   Halt scenario → OpenOCD hardware
├── c_bridge/
│   └── uvm_bridge.c         # C DPI socket server (runs inside simulator)
├── debug_lib/               # Python library (transport-agnostic)
│   ├── transport.py          #   Abstract base class (read/write/reset)
│   ├── uvm_transport.py      #   UVM transport (Unix socket + JSON)
│   ├── openocd_transport.py  #   OpenOCD transport (TCL over TCP)
│   ├── riscv_dm.py           #   RISC-V Debug Module command library
│   └── session.py            #   Step-based session runner
├── sequences/               # Scenario scripts
│   ├── halt_sequence.py      #   Halt + inspect registers + read memory
│   └── mem_scan_sequence.py  #   Scan a memory range
├── tb/                      # SystemVerilog testbench
│   ├── debug_if.sv           #   DMI interface definition
│   ├── debug_pkg.sv          #   UVM package (agent, bridge, test)
│   └── tb_top.sv             #   Top-level module + DUT stub
├── sim/                     # Simulation launch directory
│   └── Makefile              #   Build & run targets
└── run.py                   # Master Python runner (reads JSON configs)
```

---

## Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                        Python Layer                              │
 │                                                                  │
 │  run.py ──→ reads JSON config ──→ picks scenario                │
 │                                      │                           │
 │                    ┌─────────────────┘                           │
 │                    ▼                                              │
 │            halt_sequence.py  (or any scenario)                   │
 │                    │                                              │
 │          dm.write(0x10, val)   dm.read(0x11)                    │
 │                    │                                              │
 │              transport.read() / transport.write()                │
 │                    │                                              │
 │         ┌──────────┴──────────┐                                  │
 │         ▼                     ▼                                  │
 │   UVMTransport          OpenOCDTransport                        │
 │   (Unix socket)         (TCP port 6666)                         │
 └─────┬───────────────────────┬────────────────────────────────────┘
       │                       │
       ▼                       ▼
 ┌───────────┐           ┌───────────┐
 │  C Bridge │           │  OpenOCD  │
 │  (DPI)    │           │  Server   │
 └─────┬─────┘           └─────┬─────┘
       │ DPI poll                │ JTAG
       ▼                       ▼
 ┌───────────┐           ┌───────────┐
 │  UVM Test │           │  Target   │
 │  (bridge) │           │  Board    │
 └─────┬─────┘           └───────────┘
       │ sequencer
       ▼
 ┌───────────┐
 │  Agent    │   ← completely TB-agnostic
 │  Driver   │
 │  Monitor  │
 └─────┬─────┘
       │ DMI bus
       ▼
 ┌───────────┐
 │    DUT    │
 └───────────┘
```

---

## Simulation Flow (Python → C → UVM)

### Step-by-step communication:

1. **JSON config** tells `run.py` which scenario to run and which transport to use
2. **Python** loads the scenario (e.g., `halt_sequence.py`) and connects to the C bridge via Unix socket
3. **Python scenario** calls `dm.activate()` → translates to `transport.write(0x10, 1)` → sends JSON `{"op":"write", "addr":16, "data":1}` over the socket
4. **C bridge** receives the JSON, places the request in a mutex-protected buffer, blocks waiting for response
5. **UVM test** (`python_bridge.serve()`) polls `dpi_bridge_get_req()` — finds the request
6. **UVM test** creates a `dmi_write_seq`, starts it on the agent's sequencer
7. **Driver** picks up the sequence item, drives the DMI bus to the DUT
8. **Driver** captures the DUT's response, fills `rsp_data`
9. **UVM test** calls `dpi_bridge_put_rsp(rsp_data)` — signals the C thread
10. **C bridge** wakes up, sends JSON response `{"id":1, "status":"ok"}` back to Python
11. **Python** receives the response, proceeds to the next command
12. **Repeat** until the scenario is complete
13. **Python** calls `transport.disconnect()` → sends `{"op":"shutdown"}`
14. **UVM test** receives shutdown, exits the command loop, drops objection → simulation ends cleanly

### Key design principle:
> The `python_bridge` component is the **only** thing that knows about DPI/C.
> Everything below it (agent, driver, sequencer, monitor, scoreboard) is
> completely TB-agnostic and reusable.

---

## Hardware Flow (Python → OpenOCD → JTAG → Chip)

This path is used when you want to run the **exact same Python test** against a
real RISC-V chip (on a board or FPGA) instead of a simulation. No simulator, no
C bridge, no UVM — Python talks directly to the chip through OpenOCD.

### What is OpenOCD?

OpenOCD is an open-source tool that controls debug hardware. It connects to your
chip via a USB debug probe (like an Olimex or J-Link), speaks the JTAG protocol
over the wire, and exposes a **TCL command server** on TCP port 6666 that any
program can connect to and send debug commands.

### Prerequisites

```
┌──────────┐     USB      ┌────────────┐    JTAG     ┌──────────┐
│   Your   │◄────────────►│   Debug    │◄───────────►│  RISC-V  │
│   PC     │              │   Probe    │              │   Chip   │
│          │              │ (Olimex/   │              │ (FPGA/   │
│ OpenOCD  │              │  J-Link)   │              │  ASIC)   │
│ running  │              └────────────┘              └──────────┘
└──────────┘
```

You need OpenOCD running with TCL port enabled:
```bash
openocd -f interface/ftdi/olimex-arm-usb-ocd-h.cfg -f target/riscv.cfg
# OpenOCD is now listening on port 6666 for TCL commands
```

### Step-by-step communication:

1. **JSON config** tells `run.py` to use the `openocd` transport:
   ```json
   { "scenario": "halt", "transport": "openocd", "openocd": { "port": 6666 } }
   ```

2. **Python** connects to OpenOCD's TCL server via a plain TCP socket on port 6666

3. **Python scenario** calls `dm.halt()` — this translates to two register operations:
   - `transport.write(0x10, 0x80000001)` → Python sends the TCL string:
     ```
     riscv dmi_write 0x10 0x80000001\n
     ```
   - `transport.read(0x11)` → Python sends:
     ```
     riscv dmi_read 0x11\n
     ```

4. **OpenOCD receives** the TCL command, translates it into JTAG bit sequences,
   and shifts them through the debug probe's USB connection into the chip's
   JTAG TAP (Test Access Port)

5. **The chip's Debug Module** hardware processes the DMI request and returns
   the register value through JTAG

6. **OpenOCD reads** the JTAG response and sends the result back to Python as
   a text string (e.g., `0x00000602`) followed by a `0x1a` end-of-response marker

7. **Python parses** the hex string, checks the result (e.g., bit 9 = allhalted),
   and proceeds to the next command

8. **When done**, Python simply closes the TCP socket — no "shutdown" command
   needed since there's no simulation to stop

### Key difference from simulation:

| Aspect          | UVM Simulation Path              | OpenOCD Hardware Path        |
|-----------------|----------------------------------|------------------------------|
| Middle layer    | C bridge + DPI                   | None (direct TCP)            |
| Protocol        | JSON over Unix socket            | TCL text over TCP            |
| Read command    | `{"op":"read", "addr":17}`       | `riscv dmi_read 0x11`        |
| Write command   | `{"op":"write", "addr":16, ...}` | `riscv dmi_write 0x10 0x...` |
| Physical layer  | Simulated RTL signals            | Real JTAG wires              |
| Shutdown        | `{"op":"shutdown"}` → ends sim   | Just close socket            |
| Speed           | ~1μs per transaction (simulated) | ~1-10ms per transaction      |

### Why this matters:

The **Python scenario code is identical** for both paths. `halt_sequence.py`
calls `dm.halt()` — it has no idea whether it's talking to a QuestaSim
simulation or a real FPGA board. The transport layer handles everything.
This means you can:

1. **Develop and debug** your test scenarios in simulation (fast iteration)
2. **Run the exact same tests** on hardware (real validation)
3. **Compare results** — if simulation passes but hardware fails, you know
   the RTL is correct and the issue is in synthesis/physical design

---

## Third-Party Integration Guide

If you want to use this Python debug framework with your own UVM testbench,
you only need **3 lines of code** in your test class:

### Step 1: Import the package and compile the C bridge

```systemverilog
// In your test file:
import debug_pkg::*;
```

```bash
# Compile the C bridge:
gcc -shared -fPIC -std=c11 -I<path_to_c_bridge> \
    uvm_bridge.c -o uvm_bridge.so -lpthread
```

### Step 2: Instantiate the bridge in your test

```systemverilog
class my_test extends uvm_test;
    `uvm_component_utils(my_test)

    my_env         m_env;       // your own environment
    python_bridge  m_bridge;    // ← add this

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_env    = my_env::type_id::create("m_env", this);
        m_bridge = python_bridge::type_id::create("m_bridge", this);  // ← add this
    endfunction

    task run_phase(uvm_phase phase);
        phase.raise_objection(this);

        // Launch Python (or let user start it manually)
        void'($system("python3 -u ../run.py --config my_test.json 2>&1 &"));

        // This single call does everything:
        // - Starts C socket server
        // - Polls for Python commands
        // - Creates and runs dmi_read_seq / dmi_write_seq on YOUR sequencer
        // - Exits when Python sends "shutdown"
        m_bridge.serve(m_env.m_agent.m_sequencer);  // ← add this

        phase.drop_objection(this);
    endtask
endclass
```

### Step 3: Create a JSON config for your test

```json
{
    "scenario":  "halt",
    "transport": "uvm",
    "mode":      "batch",
    "params": {
        "mem_addr": "0x80000000"
    }
}
```

That's it. Your agent, driver, monitor, and scoreboard remain completely
untouched. The bridge starts native `dmi_read_seq` / `dmi_write_seq` sequences
on your sequencer — the driver just sees normal sequence items.

---

## JSON Configuration

Test configurations live in `configs/`. Example:

```json
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
```

| Field        | Description                                              |
|--------------|----------------------------------------------------------|
| `scenario`   | Name of scenario to run (maps to `sequences/` scripts)  |
| `transport`  | `"uvm"` or `"openocd"`                                  |
| `mode`       | `"batch"` (automated) or `"interactive"` (step-by-step)  |
| `params`     | Scenario-specific parameters (passed as kwargs)          |
| `uvm`        | UVM transport settings (socket path, timeout)            |
| `openocd`    | OpenOCD transport settings (host, port)                  |

---

## Quick Start

### Simulation (Questa)

```bash
cd sim
make questa_batch                    # Run with default config (halt_uvm.json)
make questa_batch CFG_FILE=../configs/my_custom_test.json   # Custom config
```

### Hardware (OpenOCD)

```bash
# Ensure OpenOCD is running with: tcl_port 6666
cd sim
make openocd_batch
```

### Direct Python

```bash
python3 run.py --config configs/halt_uvm.json
python3 run.py --scenario halt --transport uvm --mode batch
```

---

## Adding a New Scenario

1. Create `sequences/my_scenario.py` with a `build_my_scenario(dm, mode, **params)` function
2. Register it in `run.py`'s `SCENARIO_REGISTRY`:
   ```python
   SCENARIO_REGISTRY = {
       "halt": { "module": "sequences.halt_sequence", "builder": "build_halt_sequence" },
       "my_scenario": { "module": "sequences.my_scenario", "builder": "build_my_scenario" },
   }
   ```
3. Create a JSON config: `configs/my_scenario_uvm.json`
4. Run: `make questa_batch CFG_FILE=../configs/my_scenario_uvm.json`

---

## Protocol Reference

### Python → C (JSON over Unix socket)

| Operation | Request                                      | Response                              |
|-----------|----------------------------------------------|---------------------------------------|
| Read      | `{"id":1, "op":"read", "addr":17}`          | `{"id":1, "status":"ok", "data":3}`  |
| Write     | `{"id":2, "op":"write", "addr":16, "data":1}` | `{"id":2, "status":"ok"}`          |
| Reset     | `{"id":3, "op":"reset"}`                     | `{"id":3, "status":"ok"}`           |
| Shutdown  | `{"id":4, "op":"shutdown"}`                  | `{"id":4, "status":"ok"}`           |

### C → UVM (DPI polling)

| DPI Function           | Direction | Purpose                              |
|------------------------|-----------|--------------------------------------|
| `dpi_bridge_get_req()` | C → SV    | SV polls for pending request         |
| `dpi_bridge_put_rsp()` | SV → C    | SV returns response, unblocks C      |
| `uvm_bridge_start()`   | SV → C    | Start socket server thread           |
| `uvm_bridge_stop()`    | SV → C    | Stop server thread cleanly           |
