# Integration Guide: integrate a new SoC, run simulation tests, run emulation tests

This is the practical, repeatable guide for using `pydebug` — written from what
actually happened porting it to CVA6 and Ibex, not a theoretical recipe. It
covers three things in order: (a) how to integrate the tool with a new
project, (b) how to run its tests in simulation, (c) how to run its tests in
emulation on real hardware. `cva6_sim/` and `ibex_sim/` in this repo are the
two worked examples referenced throughout.

---

## Part A — Integrating `pydebug` with a project

### A.1 The checklist

1. **Locate the target's debug module and confirm its JTAG IDCODE.**
   `pydebug` speaks the RISC-V Debug Spec's DMI protocol over JTAG. Your
   target needs a `dm_top`-equivalent (PULP `riscv-dbg`, or your own, as long
   as it implements `dmcontrol`/`dmstatus`/`abstractcs`/`sbcs`) already wired
   to a JTAG TAP. Find the constant that drives the TAP's IDCODE register —
   you'll need it for the OpenOCD `.cfg` (`-expected-id`).

2. **Identify how to get code into memory before the core runs.** Either a
   hierarchical path to a behavioral memory array pydebug's DPI ELF loader
   can write directly (what both CVA6 and Ibex use — see `` `MAIN_MEM``/
   `` `IBEX_MEM`` in `cva6_sim/tb_top_cva6.sv` / `ibex_sim/tb_top_ibex.sv`),
   or a bootloader/bootrom path if direct memory injection isn't available.

3. **Scaffold with the CLI:**
   ```bash
   pydebug init --template {standalone|ibex|cva6} --output <dir>
   ```
   Use `standalone` as the starting point for a SoC with no dedicated
   template yet — the CLI accepts any template name, so adding your own
   `tb_top_<soc>.sv` to the package later needs no CLI change. Edit only the
   memory-macro path and IDCODE in the generated file.

4. **Wire pydebug's sources into your own build, not the other way around**
   — this is what makes the tool a true third-party dependency instead of
   something glued into one project:
   ```makefile
   PYDEBUG_C_DIR  := $(shell pydebug sources --c-dir)
   PYDEBUG_SV_DIR := $(shell pydebug sources --sv-dir)
   ```
   `pydebug sources --sv` (no `-dir`) lists every shared VIP/kit `.sv` file
   individually, recursively, across the kit's `model/`/`agents/`/
   `sequences/`/`assertions/`/`fcov/`/`env/` subdirectories — testbench
   templates are intentionally excluded (`bridge_utils.py` filters
   `sv/templates/` out), so this is safe to compile verbatim alongside your
   own `tb_top_<soc>.sv` without pulling in an unrelated SoC's top module.
   This works from **any** Makefile in **any** project, on any machine where
   `pip install`'d `pydebug` is on `PATH` — see `cva6_sim/Makefile` and
   `ibex_sim/Makefile` for two complete, real examples.

5. **Pick a transport.**
   - `uvm` — Unix-socket DPI bridge, launched from inside the sim via
     `+PYTHON_SEQ="-m pydebug.cli run --config <file>"`. Works when your
     simulator supports DPI-C sockets.
   - `openocd` — remote-bitbang over TCP. Works with any simulator that can
     drive plain I/O pins, and is also how you move to a real board/FPGA
     with **no code changes** — only the config file changes.

6. **Run a scenario**:
   ```bash
   pydebug run -c configs/halt_uvm.json
   # or: pydebug run --transport openocd --scenario halt --openocd-config configs/openocd_arty_a7_100t.cfg
   ```
   A full pass looks like `Session complete - 8/8 passed`.

### A.2 Two worked examples

| Step | CVA6 (`CVA6-fork`, Questa) | Ibex (`ibex-demo-system`, Questa) |
|---|---|---|
| DM / IDCODE | `corev_apu/riscv-dbg` (PULP `riscv-dbg` v0.4.1), IDCODE `0x00000001` | Same PULP `riscv-dbg` core, IDCODE `0x11001cdf` (`jtag_id_pkg.sv`) |
| Memory preload path | `` `MAIN_MEM(P) dut.i_sram.gen_cut[0].i_tc_sram_wrapper.i_tc_sram.sram[(P)]`` | `` `IBEX_MEM(P) dut.u_ram.u_ram.gen_generic.u_impl_generic.mem[(P)]`` |
| Template edits needed | **0** — `pydebug init --template cva6` matched this checkout byte-for-byte | **0** — same for `--template ibex` |
| Build glue written | One `Makefile` (flist via CVA6's own `util/flist_flattener.py` + pydebug sources) | One `Makefile` + generic `flist_ibex.f`/`prim_shims/` Questa glue (not pydebug-specific) |
| Result | Compiled 0 errors; DM activation + halt request verified live over real JTAG/DMI | `Session complete - 8/8 passed`, `Errors=0` |

The only difference between the two integrations is which memory macro and
IDCODE go in the generated template — everything else (the Python package,
the CLI invocation, the JTAG/DPI kit) was identical. Edits inside the
installed package: **0** in both cases.

### A.3 Things that will trip you up (found during real bring-up)

- **`+PYTHON_SEQ` must be a module/script argument, not a shell command.**
  The UVM test launches it as `python3 -u %s`, so use
  `-m pydebug.cli run --config <file>`, not `pydebug run --config <file>`.
- **Small-immediate test programs (`li`, `j`) assemble identically under
  RV32 and RV64** — one ELF built with an RV64 toolchain can be reused
  directly against an RV32 core (like Ibex) with no separate build, as long
  as the instructions used don't depend on register width.
- **A simulator's optimizer may not tolerate the debug-module RTL** (Questa's
  `vopt` segfaults on `dm_mem`/`fpnew_cast_multi` on some CVA6-fork commits)
  — fall back to unoptimized elaboration (`-novopt` in Questa) rather than
  fighting the optimizer.
- **RTL/IP version pinning matters.** A `dm_mem` simulation-convergence
  glitch appeared on one CVA6-fork commit that didn't reproduce on another,
  differing only in the vendored `riscv-dbg` submodule version — if a fresh
  clone of a known-integrated SoC misbehaves, check whether the commit pin
  drifted before assuming it's a `pydebug` bug.

---

## Part B — Running tests in simulation

Both `cva6_sim/` and `ibex_sim/` in this repo follow the same pattern: a
`Makefile` that resolves pydebug's sources via the installed CLI (never
hardcoded paths into the package), a `tb_top_<soc>.sv` testbench top, and a
`sw/` test program.

### B.1 One-time setup

```bash
pip install -e .                      # from this repo's root
git submodule update --init --recursive   # pulls CVA6-fork / ibex-demo-system
```

### B.2 CVA6 (`cva6_sim/`)

```bash
cd cva6_sim
make soc_test          # compiles CVA6-fork + pydebug's JTAG/DPI kit, runs the
                        # halt/read-PC/resume session over the UVM socket transport
make soc_openocd        # same session, but over OpenOCD remote-bitbang instead
make clean
```
`CVA6_REPO_DIR` in the Makefile points at `../CVA6-fork` (the submodule) by
default. `CFG_FILE` defaults to `configs/halt_uvm.json`; override with
`make soc_test CFG_FILE=configs/read_dmstatus_uvm.json` to run a different
scenario. Output is logged to `sim_outputs/soc_test_<N>.log`.

### B.3 Ibex (`ibex_sim/`)

```bash
cd ibex_sim
make soc_test
make soc_openocd
make clean
```
Same pattern; `flist_ibex.f` and `prim_shims/` are generic Questa RTL glue
needed to compile `ibex-demo-system` standalone (not pydebug-specific — any
Questa-based integration of this SoC needs them regardless of `pydebug`).

### B.4 What "passing" looks like

A full pass prints `Session complete - N/N passed, Errors=0` from the
Python side, inside the Questa transcript / the `sim_outputs/*.log` file.

---

## Part C — Running tests in emulation (real FPGA hardware)

This is the actual proof of the portability claim: the exact same Python
scenario that ran over `uvm` in Part B runs over `openocd` here — only the
transport and the OpenOCD `.cfg` change.

### C.1 Prerequisites

| Tool | Purpose | Notes |
|---|---|---|
| Vivado (or your vendor's toolchain) | FPGA synthesis & programming | Match your board's part number |
| RISC-V GCC toolchain | Cross-compiling the test program | Match the core's ISA (e.g. `rv32imc` for Ibex) |
| OpenOCD | JTAG debug bridge | ≥ 0.12.0, with support for your board's JTAG adapter |
| Python 3 | `pydebug` itself | 3.8+ |

udev rules (Linux, so your user can access the board's USB-JTAG without
root) are typically needed for the FTDI-based adapters on boards like Arty
A7 — add a rule matching the adapter's USB vendor/product ID and reload
`udevadm`.

### C.2 Build and program the bitstream

This step is entirely target/vendor-specific — `pydebug` has no involvement
until the board is JTAG-reachable. Broadly: confirm the `.core`/project file
targets your exact part number (not a similar-but-different part on the same
board family), build the bitstream, and program it via your vendor's tool
(Vivado Hardware Manager GUI, a headless TCL script, or a lighter tool like
`openFPGALoader`).

### C.3 Point OpenOCD at the board, not the simulator

The whole point of the transport abstraction: the OpenOCD `.cfg` is the
**only** thing that changes between "OpenOCD driving a simulator's
remote-bitbang DPI server" and "OpenOCD driving a real board's onboard
USB-JTAG." Compare `configs/openocd_bitbang_ibex.cfg` (simulation) against
`configs/openocd_arty_a7_100t.cfg` (real Arty A7-100T board) — same
structure, different adapter driver and IDCODE.

```bash
openocd -f configs/openocd_arty_a7_100t.cfg
```

Confirm the config's `_EXPECTED_ID` matches your board's actual part —
boards in the same family (e.g. Arty A7-35T vs A7-100T) commonly ship
different default IDCODEs in vendor example configs.

### C.4 Load a test program and run a scenario

```bash
# Load your ELF and leave the core halted (vendor-provided or OpenOCD-direct load)
openocd -f configs/openocd_arty_a7_100t.cfg \
        -c "load_image ./halt_probe.elf 0x0" \
        -c "verify_image ./halt_probe.elf 0x0" \
        -c "reset halt"

# In a separate terminal, once OpenOCD's TCL port (6666) is up:
pydebug run --config configs/halt_hw.json --transport openocd --log-level DEBUG
```

`configs/halt_hw.json` differs from the simulation config only in
`mem_addr` (your board's actual SRAM/DRAM base — e.g. `0x00100000` for Ibex
vs `0x80000000` for CVA6/Genesys2) and the `openocd.config` field pointing
at the board-specific `.cfg`. Everything else — the scenario name, the
Python sequence module, the pass/fail checks — is byte-identical to the
simulation config.

### C.5 The three-stage portability claim

| | Simulation | Emulation (FPGA) | Post-silicon |
|---|---|---|---|
| Transport | `uvm` (DPI socket bridge) or `openocd` (remote-bitbang into the sim) | `openocd` | `openocd` |
| What's behind OpenOCD | A DPI-C remote-bitbang server inside the simulator | A real board's onboard USB-JTAG talking to the FPGA bitstream | A real JTAG probe wired to the chip's debug pins |
| What changes between stages | — | OpenOCD `.cfg`: adapter driver + IDCODE | OpenOCD `.cfg`: adapter driver + IDCODE (probe may differ) |
| What does **not** change | — | CLI, sequences, `DebugSession`, `RISCVDebug` command layer | same |

Going from emulation to post-silicon is not a third integration effort —
it's the second one's config swapped again, as long as the target's debug
module implements the RISC-V Debug Spec DMI register set. What's genuinely
new work at each stage is physical JTAG bring-up (probe selection,
voltage/adapter compatibility, boundary-scan chain length, board/chip-
specific OpenOCD config) — real hardware effort, but the *same class* of
effort each time, not a repeat of the software integration.

---

## Troubleshooting

Issues actually hit during real bring-up, and their fixes:

- **OpenOCD/simulation race: `TimeoutError`, `Connection reset by peer`,
  `couldn't bind gdb to socket ... Address already in use`.** Root cause is
  usually the simulation's watchdog timeout being far shorter than OpenOCD
  needs for a full JTAG handshake over bitbang (which can take 5–30s,
  not milliseconds). Fixes, in order of impact:
  1. Extend the simulation's watchdog for the OpenOCD path specifically
     (seconds, not the ~100ms that's fine for the DPI-socket path).
  2. Have the testbench wait on the bitbang server's own "quit" signal
     before `$finish`, rather than a hard timeout — this also prevents
     mid-transaction socket corruption.
  3. Raise `OpenOCDTransport`'s socket timeout to match (comfortably above
     worst-case bitbang latency, e.g. 30s).
  4. Add pre-run cleanup (`pkill` any leftover `vsim`/`openocd` processes)
     and startup verification (poll for the bitbang port before assuming
     it's ready) to your run script — leftover processes holding ports from
     a previous failed run is a common false-failure cause.
- **`pydebug sources --sv` leaking testbench templates into a shared-kit
  file list.** Fixed in `bridge_utils.py` (excludes `sv/templates/`
  from the shared-kit glob) — if you're on an older package version,
  exclude that directory yourself in your Makefile's file list.
- **A board's vendor example OpenOCD config defaults to the wrong part's
  IDCODE.** Boards sold in multiple part-number variants (e.g. Arty A7-35T
  vs A7-100T) often ship one IDCODE uncommented and the other commented out
  in example configs — always confirm `_EXPECTED_ID` against your board's
  actual part before assuming a JTAG failure is a wiring problem.
