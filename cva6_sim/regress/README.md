# Running the CVA6 Debug VIP regression

How to run the suite, collect functional and code coverage, and read the
results. Everything here is a command you can run; nothing is automated behind
your back.

---

## Prerequisites

| Need | Check | If missing |
|---|---|---|
| Xcelium | `xrun -version` | Source your Cadence setup |
| RISC-V toolchain | `riscv64-unknown-elf-gcc --version` | `export PATH=/opt/riscv/bin:$PATH` |
| pydebug, in **python3.9** | `/usr/local/bin/python3 -c "import pydebug"` | see below |
| PyYAML | `python3 -c "import yaml"` | `python3 -m pip install --user pyyaml` |

**pydebug must be installed into the interpreter the testbench launches**, which
is `python3` → `/usr/local/bin/python3` (3.9), not whatever `pip` alone resolves
to:

```bash
cd /work/10x-jkhalid/riscv-dbg-vip
/usr/local/bin/python3 -m pip install -e . --user
```

Installing into the wrong interpreter fails at run time with an import error
inside the simulator, which reads like a testbench problem and is not one.

Build the test programs once:

```bash
make -C cva6_sim/sw
bash mk/act_build.sh     # riscv-arch-test Sdtrig programs; needs its own tools, see the top-level README
```

---

## Running

```bash
cd cva6_sim

make regress_list        # what is in the suite and what each is expected to do
make regress             # all 36 tests, no coverage
make regress_cov         # all 36 tests with coverage      (~1 h)
make regress ONLY=cmderr,step_classes,priv_irq
```

A report lands in `testplans/results/regression_report.md`. Per-test logs go to
`cva6_sim/sim_outputs/<test>/regress.log`, alongside the trace and waves that
run already collects.

### Reading the verdict table

```
test                     result    expected    steps  errors
--------------------------------------------------------------
step_classes             pass      pass          9/9       0
csr_access               fail      fail          3/4       0
sba                      partial   partial         -       0
hart_selection           fail      fail            -       0
```

`expected` comes from `regress/regression.yaml` and records **what happens
today**, not what should happen. Thirteen tests are expected to fail and one
to abort early (the sample output above is from an older suite); each is listed
under "Known-failing tests" below, and the RTL defects are written up in
[`testplans/results/rtl_findings.md`](../../testplans/results/rtl_findings.md).

**The regression fails only when a result differs from `expected`**, and the
driver exits non-zero and prints what changed. That is the signal — a suite
where the known failures still fail is a suite telling you nothing changed.

If a result changes, either the RTL moved or the `expect` field is stale. Update
`regression.yaml` deliberately. Changing it to make the run green defeats the
whole mechanism.

| result | meaning |
|---|---|
| `pass` | every step passed, zero UVM errors |
| `fail` | ran to completion, at least one step failed |
| `partial` | died before reporting a verdict — usually fail-fast on a known defect |
| `timeout` | did not finish; the log is still collected |

---

## Functional coverage

### Collect

```bash
make regress_cov
```

Covergroups **only collect when the snapshot is built with `-coverage all`**.
`make regress` (and `make soc_test`) report `0.00%` by construction. If every
number is zero, check which target you ran before assuming the testbench broke.

### Read it

Two places, and they answer different questions.

**Per run, at the end of each log** — the per-coverpoint breakdown:

```
CG  cg_step_external        41.96%
CP    cp_stepped_class      62.50%
CP    cp_stepie_irq         25.00%
CP    x_class_x_stepie      12.50%
SPEC_TOTAL 41.50%
```

Lines are tagged `CG ` and `CP ` precisely so you can grep them without parsing
prose:

```bash
grep -E "^.*(CG|CP)  " cva6_sim/sim_outputs/step_classes/regress.log
grep -o "SPEC_TOTAL.*" cva6_sim/sim_outputs/*/regress.log
```

**Across the suite** — `make regress_cov` prints the best value per coverpoint
and writes the same into the report.

### What the merged number is, and is not

The suite-level figure is the **maximum per coverpoint across runs**, which is a
**lower bound** on true merged coverage: if two runs hit different bins of the
same coverpoint, the max credits only the higher one. It is not the merged
number and is labelled as such everywhere it appears.

A real merge needs `imc`, and **it works here** — an earlier version of this
document said it was licence-blocked, which was wrong in a way worth recording.
`imc` *is* blocked, but only the **23.03** build: it dies in its Java licence
layer (`LMF-01513`, FLEXnet `-8 Authentication Failed`) before opening anything,
while `xrun` authenticates against the very same `license.dat`. That is a
per-product licence gap, not a broken licence — and "no coverage reporting on
this machine" never followed from it. Nobody had checked whether another `imc`
was installed. One is.

### Merging and reporting with `imc`

```bash
export IMC_ROOT=/home/icdesign/cadence/installs/VMANAGER2109
export PATH="$IMC_ROOT/tools.lnx86/bin:$IMC_ROOT/bin:$PATH"
imc -version        # IMC: 21.09-s001
```

Use **21.09, not 23.03**. It warns that it is older than the 23.03 coverage data
and then reads it correctly; UCIS is versioned for exactly that. The `PATH`
export is not optional either — the `imc` wrapper resolves its own installation
from `PATH`, and without it exits with *Unable to find the Cadence installation
in your path* even when invoked by absolute path.

Then either use the packaged script:

```bash
# merge every run; functional coverage + code coverage scoped to the DM
bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/
#   out/functional.rpt   out/dm_code.rpt
```

or drive `imc` yourself:

```bash
imc -batch                      # interactive Tcl shell, no GUI
imc -execcmd "<tcl>; exit"      # one-liner
imc -exec script.tcl            # a script
imc -gui -load <abs run path>   # GUI, needs X11/VNC
```

```tcl
# ABSOLUTE paths only -- a relative -run path is silently prefixed with
# cov_work/ and reports "Directory not found".
load -run /abs/.../cva6_sim/sim_outputs/coverage/scope/step_classes_uvm
merge /abs/.../scope/run1 /abs/.../scope/run2 -out /abs/.../merged -overwrite
load -run /abs/.../merged

report -detail -metrics covergroup -out func.rpt                        ;# text
report -detail -metrics code -inst tb_top_soc.dut.i_dm_top -out dm.rpt  ;# text
report_metrics -detail -metrics covergroup -out html_dir                ;# HTML
report_metrics -summary -out summary_dir                                ;# HTML
exit
```

**HTML is the easiest to read**, and needs no GUI or X11:

```bash
cd cva6_sim/sim_outputs/coverage
imc -execcmd "load -run $PWD/scope/step_classes_uvm; \
              report_metrics -detail -metrics covergroup -out /tmp/cov_html; exit"
firefox /tmp/cov_html/index.html
```

### `imc` gotchas

Each of these fails quietly or misleadingly rather than with a clear error.

| Gotcha | Symptom |
|---|---|
| `-batch` and `-exec` are **mutually exclusive** | prints the usage text and **exits 0** — looks like success |
| A **relative** `-run` path | silently prefixed with `cov_work/` → *Directory not found* |
| `report_metrics -summary` takes **no** `-metrics` flag | *Incompatible options specified* |
| `report` (legacy) **requires** `-metrics` | same error, opposite cause |
| `-overwrite` on a **text** report | ignored, with a warning |
| `report -detail` **without `-all`** | emits the *Uncovered* report — a covergroup at 100% is **absent**, not missing. Add `-all` for the full list |

`report` is deprecated but is the one that emits greppable plain text with
covergroup names, which is why `mk/dm_cov.sh` uses it.

### Two ways a merged number goes wrong silently

- **Never merge across coverage models.** Each compile writes its own `.ucm`,
  and `merge` keeps only what the models share. Merging 21 runs from one compile
  with 1 from another reported `cg_step_external` at **0.00%**, where the 21 that
  share a model give **51.98%**. Check before trusting a merge:

  ```bash
  ls cva6_sim/sim_outputs/coverage/scope/*.ucm   # must be exactly one file
  ```

  Nothing clears `sim_outputs/coverage` between runs, so this is easy to hit —
  `rm -rf sim_outputs/coverage` before a coverage sweep avoids it entirely.

- **Coverage data goes stale against the covergroups.** Databases written before
  a covergroup change still describe the old model, and nothing warns you. After
  editing `covergroups.sv`, re-run the suite from one compile before quoting a
  number. To check what a database actually contains:

  ```bash
  gunzip -c cva6_sim/sim_outputs/coverage/scope/*.ucm | strings | grep -oE '\bcg_[a-z0-9_]+' | sort -u
  ```

### Coverage database format

Xcelium writes **UCIS** (Accellera Unified Coverage Interoperability Standard),
physically a *gzipped Boost serialization archive* — not text:

| File | Contents |
|---|---|
| `scope/icc_<hash>_<hash>.ucm` | the coverage **model** — every covergroup, coverpoint and bin, plus the design. One per **compile** |
| `scope/<test>/icc_<hash>_<hash>.ucd` | the coverage **data** — which bins that run hit. One per test |

A `.ucd` is only readable against its matching `.ucm`, which is the mechanism
behind the cross-model merge trap above.

### Closing a hole

1. Find the short coverpoint in a run log (`CP` lines).
2. Look it up in [`testplans/generated/coverage_model.yaml`](../../testplans/generated/coverage_model.yaml)
   — every bin carries its spec anchor, why it matters, and the testplan item
   that owns it.
3. Check the owning item exists in
   [`testplans/riscv_debug_testplan.md`](../../testplans/riscv_debug_testplan.md).
4. If no test drives it, that is the hole. Write the test.

The two artifacts are cross-checked mechanically:

```bash
python3 ~/.claude/skills/functional-coverage/scripts/reconcile.py \
    testplans/generated/coverage_model.yaml \
    --testplan testplans/riscv_debug_testplan.md
```

---

## Code coverage

Block, expression, toggle and FSM coverage are collected by the same
`-coverage all` build that collects functional coverage — `make regress_cov`
already produces it. There is no separate run.

```bash
make regress_cov
ls cva6_sim/sim_outputs/coverage/scope/     # one directory per test
```

Reporting it needs `imc`, blocked as above. To scope it to the Debug Module
rather than the whole SoC — which is what matters here, since CVA6's core is not
the DUT:

```bash
bash mk/dm_cov.sh cva6_sim/sim_outputs/coverage out/
```

It reports the five instances that **are** the Debug Module — `i_dm_top`,
`i_dm_csrs`, `i_dm_sba`, `i_dm_mem` and `i_dmi_jtag` (that last one a sibling of
`dm_top`, in `ariane_testharness`) — and prints a per-instance table plus a DM
total. Whole-SoC code coverage would be dominated by CVA6 itself and would say
nothing about the DM.

**Each instance must be named.** `report -inst X` covers only X; it does not
recurse, and the legacy `report` command has no `-recursive` option (only
`report_metrics` does). Naming just `i_dm_top` — which this script originally
did — measured the wrapper's port toggles and not one line of `dm_csrs`,
`dm_mem` or `dm_sba`. An unknown instance path produces an **empty section, not
an error**, so the script warns when an instance reports nothing.

Current figures (DM code coverage, functional coverage, with and without the
stated exclusions) are in
[`testplans/results/coverage_analysis.md`](../../testplans/results/coverage_analysis.md).

---

## Adding a test

1. Write the sequence in `src/pydebug/sequences/`.
2. Register it in `src/pydebug/cli.py`'s scenario table.
3. Add a config in `cva6_sim/configs/`. If it needs its own program, put the
   ELF in `params.elf` — the regression passes it through, and a scenario run
   against the wrong program **passes while covering nothing**.
4. Add an entry to `regress/regression.yaml` with `covers:` naming the testplan
   items and `why:` saying what it is for.
5. `make regress ONLY=<name>` until it does what you meant, then
   `make regress_cov` to see what it moved.

---

## Known-failing tests

Fourteen entries are not expected to pass. They are in the suite deliberately —
removing a test because it fails is how a defect stops being tracked.

| Test | Why | Detail |
|---|---|---|
| `hart_selection` (partial) | RTL-003 | A nonexistent hart reports `allrunning=1` |
| `csr_access` | testplan bug, not RTL | `TC-DCSR-003` expects `dscratch0/1` to survive a program-buffer command; `hartinfo.nscratch=2` means the DM owns them |
| `priv_irq` | test-side | The M→S→U walk does not drive the hart where the bins need it |
| `dmi_error` | RTL-009 | `dmihardreset` is not implemented |
| `dm_corners` | RTL-006/007/008 | `sbcs` reserved bits, `haltsum1-3` and `dmstatus` for a nonexistent hart |
| `debug_entry` | RTL-012 | A trigger enters Debug Mode with `dcsr.cause`=3 |
| `step_matrix` | RTL-010/011 | Stepped traps and xRETs land in the wrong place |
| `trigger` | RTL-013 | `tdata1=0` does not disable a trigger on RV64 |
| `act_sdtrig_mcontrol6` | RTL-013 | The same, seen from native code |
| `act_sdtrig_icount`, `native_icount` | RTL-014 | `icount` counts in disabled modes |
| `native_etrigger` | RTL-015 | `etrigger` never matches in S without `textra` |
| `native_itrigger` | RTL-016 | `itrigger` fires after the handler returns |
| `native_reentrancy` | RTL-017 | No re-entrancy protection (a Sdtrig SHOULD) |

`step_stall` is the regression for RTL-001 and passes **only with the
`csr_regfile.sv` `wfi` fix applied**. Without it the hart deadlocks and the test
reports `partial`. That is the intended behaviour: it is the test that catches
the defect coming back.
