# Pydebug: RISC-V Debug Compliance Framework

A dual-transport Python framework for RISC-V Debug Module (DM) verification. The same Python-driven debug scenarios run against both **UVM simulation** (via a C DPI Unix socket bridge) and **real hardware / emulation** (via OpenOCD and JTAG), driven by JSON configuration files.

---

## Architecture Overview

The framework decouples high-level test intent (written in Python) from the physical or simulated transport layer. This allows you to write a test sequence once and run it unchanged against a simulator or real silicon.

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                        Python Layer                              │
 │                                                                  │
 │  run.py ──→ reads JSON config ──→ picks scenario                │
 │                                      │                           │
 │                    ┌─────────────────┘                           │
 │                    ▼                                             │
 │            halt_sequence.py  (or any scenario)                   │
 │                    │                                             │
 │          dm.write(0x10, val)   dm.read(0x11)                    │
 │                    │                                             │
 │              transport.read() / transport.write()                │
 │                    │                                             │
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
       │ DPI poll              │ JTAG / remote_bitbang
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

## Directory Structure

```
pydebug/
├── configs/                            # JSON test configurations & OpenOCD config
│   ├── halt_openocd.json               #   Halt scenario -> OpenOCD hardware config
│   ├── halt_uvm.json                   #   Halt scenario -> UVM simulation config
│   ├── openocd_bitbang.cfg             #   OpenOCD target configuration for remote JTAG bitbang
│   └── read_dmstatus_uvm.json          #   Read dmstatus scenario -> UVM simulation config
├── dv/                                 # UVM verification components
│   ├── agents/                         #   UVM Agents
│   │   ├── axi/                        #     AXI monitoring/driving agent (tie-offs/verifications)
│   │   ├── cpu_sb/                     #     CPU sideband monitor agent
│   │   └── jtag/                       #     JTAG UVM Agent (drives JTAG protocol)
│   │       ├── debug_if.sv             #       Debug Interface (DMI bus wires & definitions)
│   │       ├── dm_defines_pkg.sv       #       Debug Module register map & field constants package
│   │       ├── jtag_agent.sv           #       UVM JTAG Agent class
│   │       ├── jtag_bitbang.sv         #       SV wrapper for C remote bitbang server DPI functions
│   │       ├── jtag_driver.sv          #       Drives physical JTAG lines (TCK, TMS, TDI, etc.)
│   │       ├── jtag_if.sv              #       Standard physical JTAG pin interface
│   │       ├── jtag_monitor.sv         #       Monitors JTAG pin activity and reconstructs DMI packets
│   │       ├── jtag_pkg.sv             #       UVM JTAG Package grouping all JTAG agent files
│   │       ├── jtag_sequencer.sv       #       JTAG Agent sequencer
│   │       ├── jtag_txn.sv             #       JTAG transaction sequence items (IR/DR shift representations)
│   │       └── types.sv                #       Global JTAG types and enums
│   ├── env/                            #   UVM Environments
│   │   ├── debug_pkg.sv                #     Master package importing all agents and bridge components
│   │   └── rv_dbg/                     #     Debug Environment classes
│   │       ├── env.sv                  #       Top-level UVM Env instantiating agents & scoreboards
│   │       ├── py_bridge.sv            #       UVM Bridge component routing DPI command requests to JTAG sequences
│   │       └── scoreboard.sv           #       Scoreboard verifying DM behavior
│   └── seq_lib/                        #   UVM sequence library
│       └── rv_dbg/                     #     DMI JTAG low-level driver sequences
│           ├── dmi_read_seq.sv         #       Sequence conducting DMI read JTAG pin scans
│           ├── dmi_write_seq.sv        #       Sequence conducting DMI write JTAG pin scans
│           └── reset_tap_seq.sv        #       Sequence resetting JTAG TAP state machine
├── lib/                                # Shared libraries (C and Python APIs)
│   ├── C/                              #   C/C++ DPI source code
│   │   └── py_uvm_bridge/              #     DPI interface shared libraries
│   │       ├── remote_bitbang.c/.h     #       C implementation of the OpenOCD remote bitbang JTAG server
│   │       └── uvm_bridge.c/.h         #       C Unix socket server for communicating JSON commands to simulator
│   └── python/                         #   Python sequencer files
│       ├── run.py                      #     Master runner script (parses JSON, launches OpenOCD, runs scenario)
│       ├── py_seq_lib/                 #     Python test sequences
│       │   ├── halt_sequence.py        #       Halt sequence: Activates DM, halts core, reads PC & GPRs, reads memory
│       │   ├── mem_scan_sequence.py    #       Memory scanning sequence: Scans memory range using system bus
│       │   └── read_dmstatus_sequence.py #     Status checking sequence: Reads dmstatus register
│       └── rv_dbg_python_api/          #     Python API/Driver Package
│           ├── transport.py            #       Abstract base class defining read/write/reset APIs
│           ├── uvm_transport.py        #       Unix Socket IPC transport routing commands to C DPI bridge
│           ├── openocd_transport.py    #       TCP Socket transport routing commands to OpenOCD TCL port
│           ├── riscv_dm.py             #       Debug Module register maps, field formatters, and abstract commands
│           └── session.py              #       Session runner (handles step execution, interactive prompts, CI batch run)
├── tb/                                 # Verification Testbenches
│   ├── tb_top.sv                       #   Top-level module for block-level Debug Module (dm_top) simulations
│   ├── tb_top_soc.sv                   #   Top-level module for full-SoC simulations (ariane_testharness + CVA6)
│   └── tests/                          #   UVM Tests
│       └── rv_dbg_base_test.sv         #     Base UVM Test running python subprocesses & serving DPI requests
└── sim/                                # Simulation build and execution directory
    ├── Makefile                        #   Makefile coordinating compilation, optimization, & run targets
    ├── run_openocd_sim.sh              #   Helper script launching OpenOCD daemon alongside simulation
    └── run_openocd_sim.sh              #   Shell script wrapping simulation startup and verification checks
```

---

## File-by-File Details

### 1. Python Sequencer Files (`lib/python/`)
*   **`run.py`**: The master entry point. It parses CLI arguments and loads a JSON config. If using UVM, it waits for the Unix socket to appear. If using OpenOCD, it launches the OpenOCD subprocess, monitors stdout for JTAG examination success (`"Examination succeed"`), connects to the OpenOCD TCL port, instantiates the selected Python test sequence, and runs it.
*   **`rv_dbg_python_api/transport.py`**: Defines `DebugTransport`, an abstract base class (interface) enforcing `connect()`, `disconnect()`, `read(addr)`, `write(addr, data)`, and `reset()`.
*   **`rv_dbg_python_api/uvm_transport.py`**: A subclass of `DebugTransport`. Implements IPC via JSON messages (`{"op": "read", "addr": A}`) sent over a Unix socket (`/tmp/uvm_bridge.sock`) to communicate with the C DPI bridge.
*   **`rv_dbg_python_api/openocd_transport.py`**: A subclass of `DebugTransport`. Communicates with OpenOCD via a TCP connection (port `6666`). It translates high-level register reads/writes into JTAG instruction/data scan TCL strings (`irscan` and `drscan`) which are processed by OpenOCD.
*   **`rv_dbg_python_api/riscv_dm.py`**: The RISC-V Debug Module translation layer. It defines register addresses (e.g. `DMCONTROL`, `DMSTATUS`, `COMMAND`) and wraps them in high-level APIs like `activate()`, `halt()`, `resume()`, `read_gpr()`, and `read_mem32()`. It implements error-checking logic (polling abstract command status `abstractcs` or system bus status `sbcs`).
*   **`rv_dbg_python_api/session.py`**: Manages test execution. In `batch` mode, steps are run sequentially, and errors abort execution. In `interactive` mode, the user is prompted at every step to execute, skip, or quit.
*   **`py_seq_lib/halt_sequence.py`**: Implements a standard debug compliance scenario. It activates the DM, halts the core, reads the program counter (`DPC`), registers `ra` and `sp`, reads memory at a specified address, and resumes.
*   **`py_seq_lib/mem_scan_sequence.py`**: Implements a memory scan test by reading consecutive 32-bit addresses using the Debug Module's System Bus Access (`SBA`) interface.
*   **`py_seq_lib/read_dmstatus_sequence.py`**: Reads and logs the `dmstatus` register to inspect debug module capabilities and status.

### 2. C DPI Bridges (`lib/C/py_uvm_bridge/`)
*   **`uvm_bridge.c` / `uvm_bridge.h`**: Spawns a Unix domain socket server thread inside the simulator. It receives JSON requests from the Python `UVMTransport`, queues them, blocks until the SystemVerilog UVM environment processes them via DPI, and returns JSON-formatted responses back to Python.
*   **`remote_bitbang.c` / `remote_bitbang.h`**: Implements the OpenOCD remote bitbang protocol server over TCP (port `9824`). It parses single-character JTAG commands sent by OpenOCD (`0`-`7` for pin states, `R` to read `TDO`, `Q` to quit) and translates them to JTAG pin updates in the simulator.

### 3. UVM Environment & Agents (`dv/`)
*   **`agents/jtag/jtag_if.sv`**: Defines physical JTAG pin interfaces (`tck`, `tms`, `tdi`, `trst_n`, `tdo`).
*   **`agents/jtag/debug_if.sv`**: Defines high-level Debug Module Interface (`DMI`) bus signals.
*   **`agents/jtag/jtag_driver.sv`**: Drives the physical JTAG pins state machine based on transaction packets.
*   **`agents/jtag/jtag_monitor.sv`**: Decodes pin toggles to rebuild JTAG instruction (`IR`) and data (`DR`) scan packets.
*   **`agents/jtag/jtag_bitbang.sv`**: A SystemVerilog module that invokes the C DPI `remote_bitbang` server. When enabled, it updates JTAG pins in the simulator with the state requested by OpenOCD over the socket.
*   **`env/rv_dbg/py_bridge.sv`**: Polled continuously via DPI by the UVM test. When it fetches a pending command from `uvm_bridge.c`, it starts the corresponding UVM sequence (`dmi_read_seq`, `dmi_write_seq`, `reset_tap_seq`) on the JTAG sequencer, receives the result, and returns it to C.
*   **`seq_lib/rv_dbg/dmi_read_seq.sv` / `dmi_write_seq.sv`**: Low-level UVM sequences that translate DMI accesses into physical JTAG JTAG Shift-IR and Shift-DR states.

### 4. Testbenches & Tests (`tb/`)
*   **`tb_top.sv`**: Connecting the JTAG VIP or OpenOCD Remote Bitbang server to the standalone Debug Module DUT (`dm_top` and `dmi_jtag`). Contains a CPU simulator block to acknowledge halts and handle debug ROM loops.
*   **`tb_top_soc.sv`**: Simulates the full CVA6 SoC wrapper (`ariane_testharness`), connecting the JTAG VIP or JTAG Bitbang server to the processor core.
*   **`tests/rv_dbg_base_test.sv`**: The base UVM test. In UVM mode, it spawns the Python runner in the background and runs the `py_bridge.sv` server loop. In OpenOCD mode, it keeps the simulation running until the Remote Bitbang server gets a quit signal (`bb_quit`).

---

## Detailed Methodologies

### Methodology 1: UVM Simulation Mode (Python → C → UVM)

Use this path for fast block-level or SoC-level simulation testing.

```
 ┌──────────────┐             JSON over Unix Socket            ┌──────────────┐
 │ Python Test  │ ◄──────────────────────────────────────────► │   C Bridge   │
 │ (run.py)     │          /tmp/uvm_bridge.sock                │(uvm_bridge.c)│
 └──────────────┘                                              └──────┬───────┘
                                                                      │ Mutex / Cond
                                                                      ▼
 ┌──────────────┐           Starts JTAG Sequences             ┌──────────────┐
 │  JTAG Driver │ ◄──────────────────────────────────────────  │  UVM Bridge  │
 │(jtag_driver) │             on JTAG Sequencer                │(py_bridge.sv)│
 └──────┬───────┘                                              └──────────────┘
        │
        ▼ JTAG Pins (TCK/TMS/TDI/TDO)
 ┌──────────────┐
 │  Debug DUT   │
 │   (dm_top)   │
 └──────────────┘
```

1.  **Simulation Starts**: The simulator executes `tb_top.sv` and starts the `debug_test` UVM test class.
2.  **Launching Python**: In `rv_dbg_base_test.sv`, the test's `run_phase` executes `python3 run.py --config configs/halt_uvm.json` in a background shell subprocess.
3.  **Bridge Server Starts**: Simultaneously, the UVM test launches `m_bridge.serve()`, which calls the C DPI function `uvm_bridge_start()`. This spawns a background thread listening on `/tmp/uvm_bridge.sock`.
4.  **Python Connection**: The Python runner detects the socket file and connects via `UVMTransport`. It loads the specified scenario (e.g. `halt_sequence.py`).
5.  **DMI Requests**: When the Python sequence calls `dm.halt()`, `riscv_dm.py` translates it to a write to register `0x10` (dmcontrol) with the haltreq bit set.
6.  **Socket Write**: `uvm_transport.py` writes the JSON line `{"id": 1, "op": "write", "addr": 16, "data": 2147483649}` to the Unix socket and blocks.
7.  **C Bridge Queueing**: `uvm_bridge.c` reads the message, parses the fields, saves them to global request variables, marks the request as valid, and waits on a condition variable.
8.  **DPI Polling**: In `py_bridge.sv`, the SystemVerilog side runs a loop polling the DPI function `dpi_bridge_get_req()` every cycle.
9.  **UVM Sequence Execution**: Upon detecting the request, `py_bridge.sv` instantiates a `jtag_dmi_write_seq` sequence, sets its `addr` and `data` parameters, and starts it on the JTAG sequencer.
10. **JTAG Pin Wiggle**: The `jtag_driver.sv` translates the transaction into clock-cycles and state-transitions on the physical JTAG pins (`TCK`, `TMS`, `TDI`).
11. **DUT Registers updated**: The `dmi_jtag` RTL decodes the JTAG shift, writes to the Debug Module registers, and updates the core's status.
12. **Response Routing**: Once the UVM sequence finishes, `py_bridge.sv` collects any return data and calls the DPI function `dpi_bridge_put_rsp()`.
13. **C Bridge Unblock**: `uvm_bridge.c` updates response variables, signals the blocked thread, packages the status as JSON `{"id": 1, "status": "ok"}\n`, and sends it back over the Unix socket.
14. **Iteration & Exit**: Python reads the response, unblocks, and runs the next step. When the scenario finishes, Python sends `{"op": "shutdown"}`. The UVM bridge shuts down the socket server, returns from `serve()`, drops the objection, and the simulation terminates cleanly.

---

### Methodology 2: OpenOCD Mode (Python → OpenOCD → JTAG → RTL/Board)

Use this path to test the exact same Python scenarios against real hardware, FPGA boards, or in simulations executing raw JTAG via OpenOCD.

```
 ┌──────────────┐            JSON / TCL commands (TCP)         ┌──────────────┐
 │ Python Test  │ ◄──────────────────────────────────────────► │   OpenOCD    │
 │ (run.py)     │                Port 6666                     │    Daemon    │
 └──────────────┘                                              └──────┬───────┘
                                                                      │ JTAG Bitbang
                                                                      ▼
 ┌──────────────┐             Bitbang Pins (TCP)               ┌──────────────┐
 │ JTAG Bitbang │ ◄──────────────────────────────────────────► │ Remote B-Bang│
 │(jtag_bitbang)│                Port 9824                     │(remote_b-bag)│
 └──────┬───────┘                                              └──────────────┘
        │
        ▼ JTAG Pins (TCK/TMS/TDI/TDO)
 ┌──────────────┐
 │  Debug DUT   │
 │   (dm_top)   │
 └──────────────┘
```

1.  **Simulator Ready**: If running in simulation, the simulator launches `tb_top.sv` with the `+JTAG_MASTER=openocd` plusarg.
2.  **Bitbang Server Initialized**: This activates `jtag_bitbang.sv`, which calls the DPI function `rbs_init(9824)`. This starts a TCP server listening on port `9824` for OpenOCD Remote Bitbang commands.
3.  **Launching OpenOCD**: The master Python script `run.py` launches the OpenOCD daemon in the background using `openocd -f configs/openocd_bitbang.cfg`.
4.  **Bitbang Link**: OpenOCD connects to the simulator on port `9824`. It sends commands to toggle `TCK`, `TMS`, and `TDI` pins in the simulator and reads the returning `TDO` pin states.
5.  **JTAG Examination**: OpenOCD conducts JTAG scans to discover the CPU TAP. Once it reads the IDCODE and initializes successfully, it outputs `Examination succeed`.
6.  **Python Connection**: The master script `run.py` monitors OpenOCD's log. Upon detecting success, it instantiates `OpenOCDTransport` and connects to OpenOCD's TCL command port (`6666`).
7.  **DMI Requests**: The Python test calls `dm.halt()`.
8.  **TCL Command Translation**: `openocd_transport.py` translates the register request into JTAG scan commands:
    *   `irscan riscv.cpu 0x11` (Selects DMI register IR)
    *   `drscan riscv.cpu 41 0x...` (Shifts address, data, and read/write op)
    *   `drscan riscv.cpu 41 0x0` (Shifts a NOP to scan out the DMI response)
9.  **JTAG execution**: OpenOCD receives the TCL commands, translates them to bitbang packets, drives JTAG pins in the simulator (or on physical pins if connected to an FPGA via a JTAG adapter), and reads back the shifted values.
10. **Result Returned**: OpenOCD returns the scanned data as a hex string to Python. Python parses the result and unblocks to run the next test step.

---

## JSON Configuration Reference

Configurations live in `configs/`. Below is a detailed explanation of each option:

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
        "timeout":     300.0,
        "startup_wait": 60.0
    },
    "openocd": {
        "host": "127.0.0.1",
        "port": 6666,
        "bin": "/usr/bin/openocd",
        "config": "../configs/openocd_bitbang.cfg",
        "startup_wait": 60.0
    }
}
```

### JSON Fields Table
| Field Name | Type | Options | Description |
| :--- | :--- | :--- | :--- |
| `scenario` | String | `halt`, `read_dmstatus`, `mem_scan` | Maps to the Python test sequence inside `lib/python/py_seq_lib/` |
| `transport` | String | `uvm`, `openocd` | Selects socket IPC directly to simulator vs TCL connection to OpenOCD |
| `mode` | String | `batch`, `interactive` | `batch` executes automatically; `interactive` prompts on every step |
| `params` | Object | *Scenario-dependent* | Key-value pairs passed directly to the sequence builder function |
| `uvm.socket_path`| String | Path | Path to the Unix Socket file used for IPC communication |
| `uvm.timeout` | Float | Seconds | Transaction timeout waiting for simulation to complete a DMI access |
| `openocd.host` | String | IP Address | Host address running the OpenOCD daemon |
| `openocd.port` | Integer | Port | TCP port exposing the OpenOCD TCL command server (default `6666`) |
| `openocd.bin` | String | Path | Path to the local OpenOCD binary |

---

## Third-Party Integration Guide

Integrating this framework into an external UVM testbench is simple and only requires editing your top-level UVM Test:

### Step 1: Import the Package & Compile the C library
Import the debug package in your files:
```systemverilog
import debug_pkg::*;
```
Compile the C DPI library:
```bash
gcc -shared -fPIC -std=c11 -I../lib/C/py_uvm_bridge \
    ../lib/C/py_uvm_bridge/uvm_bridge.c -o uvm_bridge.so -lpthread
```

### Step 2: Instantiate & Serve the Bridge inside your Test
Add the python bridge to your UVM Test:
```systemverilog
class my_test extends uvm_test;
    `uvm_component_utils(my_test)

    my_env         m_env;
    python_bridge  m_bridge; // Instantiate bridge

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_env    = my_env::type_id::create("m_env", this);
        m_bridge = python_bridge::type_id::create("m_bridge", this);
    endfunction

    task run_phase(uvm_phase phase);
        phase.raise_objection(this);

        // Spawn Python test runner in background
        void'($system("python3 -u ../lib/python/run.py --config my_config.json 2>&1 &"));

        // Serve requests on your agent's JTAG sequencer
        m_bridge.serve(m_env.m_jtag_agent.m_sequencer);

        phase.drop_objection(this);
    endtask
endclass
```

---

## Quick Start Guide

Navigate to the `sim/` directory to compile and run tests.

### 1. UVM Simulation Mode (Questa)
Run standard halt sequence:
```bash
make questa_batch
```
Run memory scan sequence:
```bash
make questa_mem_scan
```
Run with a custom JSON configuration:
```bash
make questa_batch CFG_FILE=../configs/read_dmstatus_uvm.json
```
Run interactive step-by-step debug:
```bash
make questa_interactive
```

### 2. OpenOCD JTAG Emulation Mode (Questa)
Compiles the design, starts the remote bitbang JTAG server, launches OpenOCD, and executes the Python test:
```bash
make questa_openocd
```

### 3. SoC-level UVM Simulation Mode (Questa)
Compiles CVA6 core within the full APU SoC architecture and runs the halt sequence:
```bash
make questa_soc_batch
```
To run OpenOCD JTAG emulation at the SoC level:
```bash
make questa_soc_openocd
```

### 4. VCS & Xcelium Simulators
To run UVM batch tests using VCS or Xcelium:
```bash
make vcs_batch
make xrun_batch
```

### 5. Cleanup
To delete work directories, compiled binaries, and temporary log files:
```bash
make clean
```

---

## Adding a New Debug Scenario

To write and register a new Python-driven debug scenario:

1.  **Create your sequence file**: Create a file named `my_test_sequence.py` inside `lib/python/py_seq_lib/`. Define a builder function returning a `DebugSession`:
    ```python
    from rv_dbg_python_api import RISCVDebug, DebugSession, StepResult

    def build_my_scenario(dm: RISCVDebug, mode: str = "batch", **params) -> DebugSession:
        session = DebugSession(mode=mode)

        # Add high-level debug steps
        session.add_step("Activate DM", lambda: dm.activate())
        session.add_step("Read custom GPR x10", lambda: StepResult(ok=True, msg=f"x10={dm.read_gpr(0x100A):#x}"))

        return session
    ```
2.  **Register the Builder**: In `lib/python/run.py`, import your file and add it to `SCENARIO_REGISTRY`:
    ```diff
     SCENARIO_REGISTRY = {
         "halt": {
             "module": "py_seq_lib.halt_sequence",
             "builder": "build_halt_sequence",
         },
    +    "my_test": {
    +        "module": "py_seq_lib.my_test_sequence",
    +        "builder": "build_my_scenario",
    +    }
     }
    ```
3.  **Create config & run**: Create a JSON configuration pointing to your new scenario (e.g. `"scenario": "my_test"`) and run:
    ```bash
    make questa_batch CFG_FILE=../configs/my_test_config.json
    ```
