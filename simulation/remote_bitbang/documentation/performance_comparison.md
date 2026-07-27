# PyDebug vs. OpenOCD + Remote Bit-Bang — Performance Comparison

**Method.** `python/run_benchmark.py` drives the identical operation
sequence (activate DM, halt, 20x raw register read, 20x raw register write,
20x GPR read via abstract command, 20x GPR write, 20x 32-bit memory write
via SBA, 20x 32-bit memory read) against each transport, timing every
individual operation with `time.perf_counter()`. Both runs, for a given
DUT, use the same compiled Questa `work` library, the same ELF
(`sw/halt_probe.elf`), and were run back-to-back on the same machine.
`python/compare_transports.py` reads the two resulting JSON files and
produces the tables/charts below and in the per-DUT reports — every number
here is measured, not estimated. Full per-DUT detail (min/max/stdev/p95,
not just mean) is in `performance_comparison_ibex.md` and
`performance_comparison_cva6.md`; this file is the cross-DUT summary plus
the qualitative analysis.

## Headline numbers

| Metric | Ibex — PyDebug | Ibex — OpenOCD+RBB | Ratio | CVA6 — PyDebug | CVA6 — OpenOCD+RBB | Ratio |
|---|---|---|---|---|---|---|
| Register read (mean) | 2.93 ms | 164.60 ms | **56.1x** | 134.87 ms | 338.50 ms | **2.5x** |
| Register write (mean) | 1.60 ms | 164.57 ms | **103.1x** | 70.43 ms | 363.15 ms | **5.2x** |
| GPR read (mean) | 9.41 ms | 493.23 ms | **52.4x** | 472.86 ms | 1.137 s | **2.4x** |
| Memory read32 (mean) | 11.63 ms | 658.00 ms | **56.6x** | 416.17 ms | 1.292 s | **3.1x** |
| Transport connect | 83.9 us | 502.2 ms | **5985x** | 107.5 us | 1.003 s | **9329x** |
| Throughput (benchmark body) | 144.4 ops/s | 2.3 ops/s | **63.1x** | 3.2 ops/s | 1.1 ops/s | **2.9x** |
| Full wall-clock (incl. startup) | 847 ms | 58.88 s | **69.5x** | 37.83 s | 121.25 s | **3.2x** |

(All "Ratio" columns are OpenOCD+RBB / PyDebug — how many times slower RBB
was for that metric, on that DUT.)

![Ibex latency comparison](figures/latency_comparison_ibex.svg)
![CVA6 latency comparison](figures/latency_comparison_cva6.svg)

## Analysis: why the ratio itself differs so much between DUTs

The direct PyDebug path is *also* far slower on CVA6 than on Ibex (134.87 ms
vs. 2.93 ms for the same raw register read) — CVA6 is a full
application-class SoC (caches, AXI interconnect, CLINT, ...) vs. Ibex's
much smaller core-plus-minimal-uncore harness, so every simulated clock
edge costs Questa more wall-clock time on CVA6 regardless of which
transport is asking for it.

RBB adds a roughly **fixed per-bit wall-clock tax** on top of whatever the
simulator's own per-cycle cost already is: each JTAG clock bit becomes one
real TCP round trip between `openocd` and the RBB DPI server (see
`architecture.md`'s sequence diagram), and a DMI transaction is dozens of
bits. On Ibex, where the simulator's own per-cycle cost is small, that
fixed tax dominates and the result is a 50-100x slowdown. On CVA6, the
simulator's own per-cycle cost is already large, so the same fixed RBB tax
is a proportionally smaller addition — a 2.5-9x slowdown instead. **The
absolute RBB overhead per operation is actually similar in both cases (RBB
minus PyDebug ≈ 160-650 ms on Ibex, ≈ 200-870 ms on CVA6) — what differs is
the size of the baseline it's being compared against**, not RBB's own cost
changing with DUT size.

**A caveat on the Ibex numbers, unrelated to timing.** The Ibex benchmark
run's memory-write/read pairs reproduce a real, already-tracked RTL bug
(`riscv-dbg-vip` issue #111 — 32-bit SBA writes lose their upper 16 bits on
this Ibex RTL build) — visible as `MODEL_MISMATCH` errors in the raw sim
log, not a benchmark artifact and not something this module fixes or works
around. It does not affect any timing number above (the mismatched value
still completes the same read/write protocol sequence in the same number
of DMI transactions), but is called out here for transparency rather than
silently omitted.

## Advantages

**PyDebug (direct UVM socket)**
- One process boundary, no protocol translation, no bit-level TCP traffic
  — 50-100x lower per-operation latency on a small DUT, several x lower
  even on a large one.
- Python runs *inside* the simulator's own process lifecycle
  (`rv_dbg_base_test.sv` spawns it) — no separate process to start, wait
  for, or clean up; a scenario failure and a sim failure surface through
  the same log.
- Directly reuses every existing `pydebug.sequences.*` scenario and the
  `dm_ref_model.sv` checker unmodified.

**OpenOCD + RBB**
- Exercises the *actual* JTAG TAP protocol end-to-end through a real,
  independent, widely-used debugger (OpenOCD) rather than a synthetic
  Unix-socket shortcut — this is the only one of the two paths that can
  catch a JTAG-TAP-level or DMI-protocol-level bug that a hand-rolled
  socket bridge could paper over.
- The exact same OpenOCD config and command surface used against real
  hardware (`*_sim/configs/openocd_arty_a7_100t.cfg`,
  `openocd_genesys2_cva6.cfg`) — a scenario proven over RBB in simulation
  gives real, if not perfect, confidence about the hardware flow (same
  OpenOCD RISC-V target driver either way), without needing an FPGA on
  hand.
- Works with any RBB-, not just pydebug-, aware client: GDB attached to
  OpenOCD, a raw `nc`/telnet session to the TCL port, or
  `tcl/rbb_control.tcl` in this module, all drive the exact same
  simulation.

## Limitations

**PyDebug (direct UVM socket)**
- Bypasses the real JTAG TAP shift-register protocol entirely at the
  Python-to-simulator boundary (the *simulated DUT's own* JTAG TAP is
  still exercised internally by `jtag_driver.sv`/`jtag_monitor.sv` — see
  `architecture.md` — but nothing external ever bit-bangs it). A bug that
  only manifests in how an *external* JTAG adapter drives TCK/TMS/TDI
  timing would not be caught this way.
- Not usable against real hardware — Unix-socket DPI bridge only exists
  inside a simulator process.

**OpenOCD + RBB**
- 2.5-100x higher latency, worse the smaller/simpler the DUT — makes large
  iteration-count regressions (e.g. this project's own functional-coverage
  regressions, hundreds of DMI transactions per scenario, run across
  a dozen scenarios) impractical at RBB speed; the existing
  `coverage_regress` Make target deliberately uses the UVM transport, not
  RBB, for exactly this reason.
- Extra moving parts: OpenOCD must be installed, spawned, and correctly
  configured (IDCODE, ports) per DUT; failures can originate in three
  different places (OpenOCD itself, the RBB server, or the DPI/SV JTAG
  agent) instead of one.
- `soc_openocd`'s Makefile target (and this module's
  `launch_rbb_benchmark.sh`) both still depend on the simulator's own
  `+JTAG_MASTER=openocd` build — RBB in this project is always
  simulation-only; it is not itself a path to real hardware (that's the
  separate FPGA OpenOCD configs, not part of this module).

## Recommended use cases

- **Day-to-day scenario development, functional-coverage regression,
  CI.** Use the direct UVM-socket transport (`soc_test`,
  `coverage_regress`) — this is already this project's default for good
  reason: the measured throughput gap (63x on Ibex, 2.9x on CVA6) makes
  RBB impractical at the iteration counts those workflows run.
- **JTAG/DMI protocol-conformance checks, OpenOCD-compatibility
  validation, and dry-running a scenario before it ever touches an FPGA.**
  Use OpenOCD + RBB (this module) — the whole point is exercising the real
  external JTAG debugger stack, and the latency cost is acceptable at the
  much lower iteration counts those checks need (a handful of scenarios,
  not hundreds of DMI transactions across a full regression).
- **Bring-up of a new DUT's DM integration.** Start with
  `tcl/rbb_control.tcl` (pure OpenOCD TCL, no Python) to confirm the
  JTAG TAP and RBB wiring work at all, independent of any pydebug
  transport code, before layering the Python side back on top.

## Which is better suited for simulation, and why

**For simulation specifically — PyDebug's direct transport is the better
default**, and this project's own Makefiles already reflect that (`soc_test`/
`coverage_regress` use it, `soc_openocd` is the explicitly opt-in
alternative). The entire value RBB adds over the direct path — exercising a
real, independent JTAG debugger and protocol stack — is about **external
tool compatibility**, not simulation fidelity: the simulated DUT's own JTAG
TAP is exercised identically either way (see `architecture.md`). Once that
compatibility question is answered for a given scenario, re-running the
same scenario at 3-100x higher throughput over the direct transport is
the better choice for everything iterative (development, regression,
functional coverage). RBB earns its cost specifically when the thing under
test *is* the external debugger/protocol stack itself, or as a lower-risk
rehearsal of a flow that will later run unmodified against real hardware
over the same OpenOCD configuration.
