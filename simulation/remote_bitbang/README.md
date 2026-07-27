# Remote Bit-Bang (RBB) Simulation Module

Simulation-only OpenOCD + Remote Bit-Bang debug flow for `riscv-dbg-vip`,
packaged as a self-contained, benchmarkable module — separate from
PyDebug's own direct UVM-socket transport and from the hardware/FPGA
OpenOCD flow. See **`documentation/architecture.md`** for the full design
and flow diagrams; this file is just the map + quick start.

```
scripts/         launch/orchestrate a Questa+RBB+OpenOCD run
tcl/             OpenOCD launch config + pure-TCL control script + a Questa
                 run-control .do file
python/          the benchmark harness + comparison-report generator
examples/        minimal standalone usage + example scenario configs
documentation/   architecture, flow diagrams, performance comparison, figures
```

## Quick start

```bash
# Full PyDebug-vs-OpenOCD+RBB benchmark + report for one DUT:
./scripts/run_comparison.sh ibex 20      # or: cva6

# Just the RBB half, e.g. to poke at it manually afterward:
./scripts/launch_rbb_benchmark.sh ibex 5

# Pure-TCL, no Python at all (once a +JTAG_MASTER=openocd sim is running):
openocd -f tcl/rbb_launch.tcl -c "set DUT ibex" -c "source tcl/rbb_control.tcl"
```

Results already committed in this repo (real, measured on this machine, not
placeholders — see `documentation/performance_comparison.md` for the full
writeup):

| | Ibex | CVA6 |
|---|---|---|
| Register read, RBB vs. direct | **56.1x** slower | **2.5x** slower |
| Full benchmark throughput, RBB vs. direct | **63.1x** slower | **2.9x** slower |

## Requirements

Same as the rest of this repo's simulation flows: Questa (`vsim`) on
`PATH`, `openocd` on `PATH` (RBB support built in — this project vendors
`remote_bitbang.c`/`.h`, it does not need OpenOCD's own bundled RBB), and
the `pydebug` package installed (`pip install -e .` from the repo root) so
`python/run_benchmark.py` can `import pydebug.api`.

## Where things are not duplicated

This module deliberately reuses, rather than copies, everything that
already exists per-DUT:
- RBB DPI server: `src/pydebug/c_bridge/remote_bitbang.c`/`.h`
- SV RBB agent: `src/pydebug/sv/agents/jtag/jtag_bitbang.sv`
- Per-DUT OpenOCD configs: `ibex_sim/configs/openocd_bitbang_ibex.cfg`,
  `cva6_sim/configs/openocd_bitbang_soc.cfg`
- Compile recipes: `ibex_sim/Makefile`, `cva6_sim/Makefile`
  (`scripts/common.sh`'s `ensure_compiled()` shells out to
  `make -C <dut>_sim soc_compile` rather than re-deriving the `vlog`
  invocation)

See `documentation/architecture.md`'s "Design decisions and trade-offs"
section for why each new piece here was added alongside those instead of
folded into them.
