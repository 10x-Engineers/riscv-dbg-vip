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
cva6_sim/                   — worked example: pydebug <-> CVA6-fork
ibex_sim/                   — worked example: pydebug <-> ibex-demo-system
mk/simulator.mk             — Questa/Xcelium selection shared by both (SIM=...)
mk/run_regression.py        — regression driver (verdicts + merged coverage)
mk/dm_cov.sh                — merge coverage and report, scoped to the DM
testplans/                  — the verification plan and the coverage model
testplans/results/          — coverage analysis, RTL findings
cva6_sim/regress/           — the regression suite (regression.yaml + README)
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

### Interactive, GDB-style live session

Alongside the batch mode above (a scenario runs start-to-finish
unattended), `pydebug interactive` drops you into a live REPL against an
already-running target — type one command at a time (`halt`, `resume`,
`read_gpr a0`, `read_mem 0x80000000`, ...) and see the result immediately,
the same way GDB's own prompt works. Every command is a thin wrapper
around a real `RISCVDebug` method — see `pydebug.api.interactive_shell`.

For simulation, this needs the target running with the UVM bridge active
but *no* auto-launched Python client (`+JTAG_MASTER=external` instead of
the default `uvm`) — `make soc_interactive` in `cva6_sim/`/`ibex_sim/`
does exactly that:

```bash
cd ibex_sim && make soc_interactive
(pydebug) activate
(pydebug) halt
halted, PC = 0x001000be
(pydebug) read_gpr a0
a0 = 0x0000000a
(pydebug) resume
running
(pydebug) quit
```

Works identically over OpenOCD/hardware — connect to an already-running
target with `pydebug interactive --transport openocd --openocd-config <cfg>`.

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
     │      JTAG/DMI Agent (driver + monitor, sv/agents/jtag/)  │
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
| `sv/` | Shared UVM VIP: `model/` (register/predictor model), `agents/jtag/` (driver, monitor, sequencer), `sequences/`, `assertions/`, `fcov/` (covergroups), `env/` (env, checker, scoreboard, base test) + per-SoC `templates/` |
| `c_bridge/` | DPI-C bridge sources compiled into the simulator's shared object |
| `cli.py` | `pydebug` console-script entry point (`run`, `init`, `sources`) |
| `bridge_utils.py` | Resolves shipped C/SV source paths for `pydebug sources` |

## Verification: testplan, coverage, regression

Everything below is about verifying a **DUT's** Debug Module with this
framework. It is separate from `tests/`, which tests the Python package itself.

### The testplan

[`testplans/riscv_debug_testplan.md`](testplans/riscv_debug_testplan.md) — derived
from the RISC-V Debug Specification **v1.0 ratified** (Sdext, Sdtrig), organised
as Reset / Register-access permissions / Functional verification.

| | |
|---|---:|
| Testplan items | 256 |
| Rows (Stimulate / Check / Cover) | 408 |
| Items exercised by ≥1 regression test | 65 (25%) |

Row statuses across all 408: **95 Pass · 257 Not started · 37 Blocked · 9 Fail ·
10 N/A**. Every row is one concrete executable item — a row that cannot name a
specific action, condition or bin does not belong in the plan, which is why
there are three rows where a prose paragraph would otherwise sit.

**25% is a lower bound, and the traceability is currently broken in both
directions.** Three `covers` tags in `regression.yaml` (`RC-001`, `HALT-013`,
`RST-025`) name rows that do not exist in the plan, and 18 rows marked `Pass`
have no test claiming them even though the plan's own Test column names one.
The mapping lives in two hand-maintained places and they have drifted. Do not
quote a coverage-of-plan figure without checking it.

### Functional coverage

Two artifacts, deliberately kept separate, and **they are not two views of one
thing** — see [`generated_vs_implemented.md`](testplans/results/generated_vs_implemented.md).

| | What it is |
|---|---|
| [`src/pydebug/sv/fcov/covergroups.sv`](src/pydebug/sv/fcov/covergroups.sv) | **The coverage of record.** 19 covergroups, 72 coverpoints, 14 crosses. Included by `debug_pkg.sv`; this is what the regression collects and the number to quote. |
| [`testplans/generated/coverage_model.yaml`](testplans/generated/coverage_model.yaml) | The architectural model: 16 covergroups, 70 coverpoints, 33 crosses, 271 bins, every bin citing its spec clause. Describes Debug v1.0, not this DUT. Not compiled. |

The implemented file is **register-centric**; the model is **behaviour-centric**.
Their numbers must never be summed. The model is generated into SystemVerilog via
a per-DUT binding layer ([`bindings/cva6.yaml`](testplans/generated/bindings/cva6.yaml),
35 of 70 coverpoints bound) and kept as a standing gap list, not as a build input.

`covergroups.sv` samples two sources: the DMI transaction stream (14 covergroups,
via `uvm_subscriber #(jtag_txn_c)`) and a **hart backdoor** (5 covergroups) for
`dcsr`, `dpc`, privilege and which instruction a step stepped over. The second
exists because the `wfi` single-step deadlock **could not have appeared as a
coverage hole** — nothing sampled which instruction a step stepped over.

**100% is not the target and not achievable here.** The model is architectural, so
it contains bins CVA6 cannot reach for reasons that are not defects: single-hart
aggregation, authentication, Quick Access, Access Memory, Zawrs, halt-on-reset,
`mcontrol`. Each is an `ignore_bins` naming its reason plus a `reachable: false`
entry naming the DUT feature that would make it reachable — retained, not deleted,
so a DUT that has the feature still gets measured. A model reporting 100% because
its hard bins were deleted is worth less than one reporting 55% and saying which
45%. [`coverage_analysis.md`](testplans/results/coverage_analysis.md) says which.

### The regression

22 tests, in [`cva6_sim/regress/regression.yaml`](cva6_sim/regress/regression.yaml).
Full instructions: [`cva6_sim/regress/README.md`](cva6_sim/regress/README.md).

```bash
cd cva6_sim
make regress          # all 22, no coverage (fast)
make regress_cov      # all 22 with -coverage all
make regress_list     # names, expectations, configs
make regress ONLY=step_classes,cmderr
```

Each entry names the ELF it needs, the testplan items it covers, and its
**known** result — `expect: pass|partial|fail`, currently 17/3/2. The driver
reports only results that *differ*: a suite where the known failures still fail
tells you nothing changed. Exit status is non-zero on any difference.

Every entry names its ELF because a scenario run against the wrong program
**passes while covering nothing** — which is how `step_stall` once reported 9/9
against `halt_probe.elf`.

### Collecting and reading coverage

Covergroups collect **only** under a `-coverage all` build; `make soc_test`
reports zeros by construction.

**Database format.** Xcelium writes **UCIS** (Accellera Unified Coverage
Interoperability Standard), physically a *gzipped Boost serialization archive* —
not text. Under `cva6_sim/sim_outputs/coverage/scope/`:

| File | Contents |
|---|---|
| `icc_<hash>_<hash>.ucm` | The coverage **model** — every covergroup, coverpoint and bin, plus the design. ~2.2 MB uncompressed. One per **compile**, shared by all its runs. |
| `<test>/icc_<hash>_<hash>.ucd` | The coverage **data** — which bins that run hit. ~480 KB. One per test. |

A `.ucd` is only readable against its matching `.ucm`.

**Reporting — use the 21.09 `imc`, not 23.03.** Both vManager installs are
present on this machine and only one works. The 23.03 `imc` dies in its Java
licence layer (`LMF-01513`, FLEXnet `-8 Authentication Failed`) before opening
anything, while `xrun` authenticates against the very same `license.dat` — a
per-product licence gap, not a broken licence. The 21.09 `imc` authenticates,
warns that it is older than the 23.03 data, and reads it correctly; UCIS is
versioned for exactly that.

```bash
# CLI — merge every run, report functional coverage + DM-scoped code coverage
bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/
#   -> out/functional.rpt   out/dm_code.rpt

# GUI
R=/home/icdesign/cadence/installs/VMANAGER2109
PATH=$R/tools.lnx86/bin:$R/bin:$PATH $R/bin/imc -gui \
  -load $PWD/cva6_sim/sim_outputs/coverage/scope/step_classes_uvm
```

Two `imc` flag traps, both of which `mk/dm_cov.sh` already handles: `-batch` and
`-exec` are **mutually exclusive** (passing both prints the usage text and exits
0), and a **relative** `-run` path is silently prefixed with `cov_work/`.

**Two things that corrupt a merged number without raising an error:**

- **Never merge across coverage models.** Each compile writes its own `.ucm`, and
  `merge` keeps only what the models share. Merging 21 runs from one compile with
  1 from another reports `cg_step_external` at **0.00%**, where the 21 that share
  a model give **51.98%**. Check `ls cva6_sim/sim_outputs/coverage/scope/*.ucm`
  returns a single file before trusting a merge.
- **Coverage data goes stale against the covergroups.** Databases from before a
  covergroup change still describe the old model. Re-run the suite from one
  compile before quoting a number.

Without `imc`, `make regress_cov` still prints per-coverpoint lines tagged
`CG`/`CP`, and `run_regression.py` merges them by taking the **max** per
coverpoint. That is a **lower bound**, not a merge: two runs hitting different
bins of one coverpoint credit only the higher.

**Code coverage** (block, expression, toggle, FSM) comes from the same
`-coverage all` build — no separate run. `mk/dm_cov.sh` scopes it to
`tb_top_soc.dut.i_dm_top`, recursing into `dm_csrs`, `dm_mem`, `dm_sba` and
`dmi_jtag`. Whole-SoC code coverage would be dominated by CVA6 itself and would
say nothing about the DM, which is the DUT here.

### RTL findings

[`testplans/results/rtl_findings.md`](testplans/results/rtl_findings.md) —
**recorded, not fixed.** Fixing RTL from the DV side hides the defect from
whoever owns the design, and a testbench that works around a bug stops measuring
it.

| ID | Finding | Status |
|---|---|---|
| RTL-001 | Single-step over `wfi` deadlocks the hart | filed, `openhwgroup/cva6#3549` (duplicate of `#3497`; PR `#3525` open) |
| RTL-002 | `sbcs.sbaccess` hardwired, and reset to 3 rather than 2 | unfiled — blocks all SBA coverage |
| RTL-003 | `allrunning`/`anyrunning` asserted for a nonexistent hart | unfiled, tracked internally as `#130` |
| RTL-004 | Halt-on-reset not implemented | not a defect — optional feature, recorded so it is not re-diagnosed |

The file also records observations that are **not** defects but cost time to
diagnose, so nobody re-diagnoses them.

## Running the package's own tests

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## License

Apache-2.0 — see `LICENSE`.
