# cva6-debug-vip — regression report

Generated 2026-09-17, one `--coverage` build of all 27 tests (`python3 mk/run_regression.py --coverage`).
Every result matches its declared `expect`. Merged functional coverage: 263/263
reachable bins (100%), 19 excluded by `mk/fcov_exclusions.tcl`; 263/282 raw.

| Test | Result | Expected | Steps | UVM errors | Covers |
|---|---|---|---:|---:|---|
| discovery | pass | pass | 2/2 | 0 | `DIS-001`, `DIS-002`, `RST-025` |
| dm_activation | pass | pass | 3/3 | 0 | `ACT-001`, `ACT-002`, `ACT-003`, `RAP-040` |
| read_dmstatus | pass | pass | 1/1 | 0 | `RST-031`, `DIS-001` |
| halt | pass | pass | 8/8 | 0 | `HALT-001`, `HALT-002`, `RC-001` |
| run_control | pass | pass | 9/9 | 0 | `HALT-001`, `RES-001`, `RES-002`, `RES-003` |
| report_halt_status | pass | pass | 4/4 | 0 | `HALT-006`, `DIS-007` |
| hart_selection | partial | partial | - | 1 | `HS-001`, `HS-002` |
| reset_ctrl | pass | pass | 11/11 | 0 | `RST-010`, `RST-011`, `RST-060`, `RST-062` |
| halt_on_reset | pass | pass | 6/6 | 0 | `RST-053`, `HALT-013` |
| gpr_write | pass | pass | 4/4 | 0 | `AC-001`, `AC-002`, `RAP-025` |
| csr_access | fail | fail | 3/4 | 1 | `AC-004`, `RAP-020`, `RAP-023` |
| cmderr | pass | pass | 14/14 | 0 | `AC-005`, `AC-006`, `AC-007`, `AC-008` |
| program_buffer | pass | pass | 6/6 | 0 | `PB-001`, `PB-002`, `PB-004`, `AC-010` |
| sw_breakpoint_progbuf | pass | pass | 3/3 | 0 | `PB-005`, `DM-001`, `DM-003` |
| single_step | pass | pass | 9/9 | 0 | `SSTEP-001`, `SSTEP-012`, `SSTEP-013` |
| step_stall | pass | pass | 9/9 | 0 | `SSTEP-004`, `RTL-001` |
| step_classes | pass | pass | 9/9 | 0 | `SSTEP-014-V`, `SSTEP-019`, `SSTEP-015` |
| priv_irq | fail | fail | 6/10 | 1 | `DM-011-V`, `SSTEP-006`, `SSTEP-007`, `SSTEP-018-V` |
| trigger | pass | pass | 13/13 | 0 | `TRIG-001`, `TRIG-002`, `TRIG-006` |
| external_trigger | pass | pass | 3/3 | 0 | `HG-003`, `RST-041` |
| sba | pass | pass | 10/10 | 0 | `SBA-001`, `SBA-002` |
| mem_scan | pass | pass | 18/18 | 0 | `PB-002`, `PB-003` |
| cmd_busy | pass | pass | 11/11 | 0 | `AC-020`, `AC-021`, `AC-022`, `AC-023` |
| dmi_error | fail | fail | 10/11 | 1 | `DTM-002`, `DTM-010`, `DTM-011`, `DTM-012` |
| dm_corners | fail | fail | 9/12 | 1 | `DMC-001`, `DMC-002`, `DMC-003`, `DMC-004` |
| debug_entry | pass | pass | 13/13 | 0 | `DCSR-010`, `DCSR-011`, `DCSR-012`, `DCSR-013` |
| step_matrix | fail | fail | 12/13 | 1 | `SSTEP-006`, `SSTEP-007`, `SSTEP-008`, `SSTEP-009` |

## Functional coverage

Per-run maxima across the suite — a **lower bound** on merged
coverage, because two runs hitting different bins of one
coverpoint credit only the higher. A true merge needs `imc`.
A run that fails stops at the UVM quit count before printing these per-run
figures, so `step_matrix` (the run that fills `cg_step_external`) is absent
here; its database is still written, and the `imc` merge above counts it.

| Coverpoint | Best |
|---|---:|
| `cg_abstract_cmd` | 83.33% |
| `cg_debug_entry` | 75.33% |
| `cg_hart_mode` | 100.00% |
| `cg_sba` | 25.00% |
| `cg_step_external` | 51.49% |
| `cp_cause` | 75.00% |
| `cp_cmderr` | 83.33% |
| `cp_consecutive` | 100.00% |
| `cp_dpc_origin` | 75.00% |
| `cp_haltreq_guard` | 100.00% |
| `cp_mode_transition` | 100.00% |
| `cp_prv` | 100.00% |
| `cp_prv_at_step` | 66.67% |
| `cp_sbaccess` | 33.33% |
| `cp_sberror` | 16.67% |
| `cp_stepie_irq` | 25.00% |
| `cp_stepped_class` | 87.50% |
| `x_cause_x_dpc` | 60.00% |
| `x_cause_x_prv` | 66.67% |
| `x_class_x_consecutive` | 62.50% |
| `x_class_x_prv` | 31.25% |
| `x_class_x_stepie` | 20.83% |
