# Reference-model cross-check — 2026-09-17

Resolves [#75](https://github.com/10x-Engineers/riscv-dbg-vip/issues/75): the SV
reference model the checker uses (`dm_ref_model.sv`) and the Python model
(`pydebug.model.predictor.DMPredictor`) are compared **by execution**, on the
real input stream of the full CVA6 regression, not by reading one against the
other.

## Method

1. `dm_checker` runs with `+DM_MODEL_TRACE=<file>` (both `make soc_test` and
   `make soc_test_cov` pass it). `dm_ref_model` then records every input it
   receives — DMI writes, the RTL's `abstractcs.busy`, the hart signals synced
   from each `dmstatus` read, `sbdata0` read triggers — and, at every read the
   checker examines, its `has_model`, `predict_mask` and prediction.
2. `mk/model_crosscheck.py` builds a `DMPredictor` from the same
   `dut_configs/cva6.json`, feeds it the same inputs in the same order, and
   compares the two models at every read: which addresses each claims, which
   bits, and the predicted value over them. It also scores both against the
   value the RTL returned.
3. `dmstatus` is compared twice. Before each comparison the checker copies the
   RTL's halted/running/resumeack into the model, because those reach the DM
   with a latency an untimed model cannot know. After that copy those bits agree
   by construction, so the record taken **before** it is the one that tests the
   run-control logic. The record taken after it is the comparison the checker
   actually made.

To bring the two to the same scope, `DMPredictor` was extended to everything
`dm_ref_model` predicts: `hartinfo`, `abstractcs`, `command`, `abstractauto`,
`sbcs`, `haltsum0`, `hawindowsel` and `nextdm` from the declared configuration;
the `data0` and `sbdata0` self-consistency shadows; the abstract-command busy
guard; and the single-step re-halt (#119).

## Result

Full regression, 26 tests, plain build, `make regress` (`python3 mk/run_regression.py`),
every test matching its declared `expect`. Reproduce with
`make -C cva6_sim model_crosscheck` after a regression.

26 trace(s), 3278 model inputs replayed, 2265 reads compared (plus 839 dmstatus reads after the hart-signal sync). **The models agree on every read.**

| Register | Reads | Both claim | Same prediction | SV ≠ RTL | Python ≠ RTL |
|---|---:|---:|---:|---:|---:|
| `data0` | 226 | 11 | 11 | 0 | 0 |
| `0x05` | 3 | 0 | 0 | 0 | 0 |
| `dmcontrol` | 16 | 16 | 16 | 0 | 0 |
| `dmstatus (before hart-signal sync: run-control logic)` | 839 | 839 | 839 | 117 | 117 |
| `dmstatus (after hart-signal sync: the checker's verdict)` | 839 | 839 | 839 | 1 | 1 |
| `hartinfo` | 4 | 4 | 4 | 0 | 0 |
| `0x13` | 1 | 0 | 0 | 0 | 0 |
| `abstractcs` | 957 | 957 | 957 | 0 | 0 |
| `command` | 1 | 1 | 1 | 0 | 0 |
| `abstractauto` | 5 | 5 | 5 | 0 | 0 |
| `0x20` | 2 | 0 | 0 | 0 | 0 |
| `0x21` | 3 | 0 | 0 | 0 | 0 |
| `0x2f` | 1 | 0 | 0 | 0 | 0 |
| `0x32` | 3 | 0 | 0 | 0 | 0 |
| `0x34` | 1 | 0 | 0 | 0 | 0 |
| `0x35` | 1 | 0 | 0 | 0 | 0 |
| `sbcs` | 92 | 92 | 92 | 0 | 0 |
| `0x39` | 1 | 0 | 0 | 0 | 0 |
| `0x3a` | 1 | 0 | 0 | 0 | 0 |
| `sbdata0` | 68 | 13 | 13 | 0 | 0 |
| `0x3d` | 38 | 0 | 0 | 0 | 0 |
| `haltsum0` | 2 | 2 | 2 | 0 | 0 |

A row with 0 under "Both claim" is an address that neither model predicts,
such as `data1` (0x05), the Program Buffer, `sbdata1` and `haltsum1-3`. The
models agree on that too: a claim by only one of them would count as a
divergence. `data0` and `sbdata0` are claimed only where this traffic wrote the
value being read back.

| Trace | Inputs | Reads | Divergences |
|---|---:|---:|---:|
| `cmd_busy_uvm.model_trace` | 214 | 180 | 0 |
| `cmderr_uvm.model_trace` | 73 | 30 | 0 |
| `csr_access_uvm.model_trace` | 36 | 20 | 0 |
| `debug_entry_uvm.model_trace` | 549 | 509 | 0 |
| `discovery_uvm.model_trace` | 3 | 3 | 0 |
| `dm_activation_uvm.model_trace` | 12 | 7 | 0 |
| `dm_corners_uvm.model_trace` | 611 | 398 | 0 |
| `dmi_error_uvm.model_trace` | 23 | 36 | 0 |
| `external_trigger_uvm.model_trace` | 11 | 4 | 0 |
| `gpr_write_uvm.model_trace` | 20 | 12 | 0 |
| `halt_on_reset_uvm.model_trace` | 24 | 7 | 0 |
| `halt_uvm.model_trace` | 25 | 16 | 0 |
| `hart_selection_uvm.model_trace` | 10 | 3 | 0 |
| `mem_scan_uvm.model_trace` | 72 | 34 | 0 |
| `priv_irq_uvm.model_trace` | 507 | 302 | 0 |
| `program_buffer_uvm.model_trace` | 26 | 14 | 0 |
| `read_dmstatus_uvm.model_trace` | 1 | 1 | 0 |
| `report_halt_status_uvm.model_trace` | 8 | 4 | 0 |
| `reset_ctrl_uvm.model_trace` | 69 | 20 | 0 |
| `run_control_uvm.model_trace` | 53 | 15 | 0 |
| `sba_uvm.model_trace` | 101 | 42 | 0 |
| `single_step_uvm.model_trace` | 29 | 22 | 0 |
| `step_classes_uvm.model_trace` | 626 | 500 | 0 |
| `step_stall_uvm.model_trace` | 52 | 38 | 0 |
| `sw_breakpoint_progbuf_uvm.model_trace` | 19 | 15 | 0 |
| `trigger_uvm.model_trace` | 104 | 33 | 0 |

In the "before the sync" `dmstatus` row, both models differ from the RTL on
the same 117 reads. That is the hart-signal latency the sync exists for, not a
disagreement between models. In the "after the sync" row, the one remaining
difference is RTL-003 (#130): with a nonexistent hart selected, the RTL reports
it running. `hart_selection` is expected to be partial for that reason, and
both models reach that same verdict.

## Does the comparison detect anything?

A first version compared `dmstatus` only after the hart-signal copy and could
not tell the models apart on run control. To check that the final version has
teeth, three rules were broken in the Python model, in memory only, and the
same 26 traces replayed:

| Rule broken in `DMPredictor` | Divergences found | Traces |
|---|---:|---|
| resume with `dcsr.step=1` does not re-halt | 5 | priv_irq, single_step, step_classes, step_stall |
| resume-ack is never set | 127 | 12 traces, led by step_classes (60) and priv_irq (52) |
| `ndmreset` does not set `havereset` | 30 | halt_on_reset, reset_ctrl, run_control |
| none (the committed model) | **0** | — |

## What this does and does not show

- **Run control** (`dmcontrol`, `dmstatus`) was written independently on each
  side: `predictor.py` first, `dm_ref_model.sv` ported from it earlier. Their
  agreement on 839 `dmstatus` and 16 `dmcontrol` reads is evidence that the
  port is faithful.
- **Everything else** was ported into Python from the SV model in this change,
  so agreement there shows that the port matches, not that either model is
  right. Correctness against the DUT is what the checker's model-vs-RTL
  comparison, and the regression, establish.
- **The functional-coverage twin is separate work.** `coverage.py` still models
  only the run-control covergroups; the external-debug covergroups remain
  SV-only.
