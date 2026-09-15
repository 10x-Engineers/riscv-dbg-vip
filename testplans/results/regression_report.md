# cva6-debug-vip — regression report

Generated 2026-09-15.

| Test | Result | Expected | Steps | UVM errors | Covers |
|---|---|---|---:|---:|---|
| discovery | pass | pass | 2/2 | 0 | `DIS-001`, `DIS-002`, `RST-025` |
| dm_activation | pass | pass | 3/3 | 0 | `ACT-001`, `ACT-002`, `ACT-003`, `RAP-040` |
| read_dmstatus | pass | pass | 1/1 | 0 | `RST-031`, `DIS-001` |
| halt | partial | partial | - | 1 | `HALT-001`, `HALT-002`, `RC-001` |
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
| priv_irq | fail | fail | 7/10 | 1 | `DM-011-V`, `SSTEP-006`, `SSTEP-007`, `SSTEP-018-V` |
| trigger | pass | pass | 13/13 | 0 | `TRIG-001`, `TRIG-002`, `TRIG-006` |
| external_trigger | pass | pass | 3/3 | 0 | `HG-003`, `RST-041` |
| sba | partial | partial | - | 1 | `SBA-001`, `SBA-002` |
| mem_scan | partial ⚠ | pass | - | 1 | `PB-002`, `PB-003` |

## Functional coverage

Per-run maxima across the suite — a **lower bound** on merged
coverage, because two runs hitting different bins of one
coverpoint credit only the higher. A true merge needs `imc`.

| Coverpoint | Best |
|---|---:|
| `cg_abstract_cmd` | 83.33% |
| `cg_debug_entry` | 32.67% |
| `cg_hart_mode` | 87.50% |
| `cg_sba` | 25.00% |
| `cg_step_external` | 41.96% |
| `cp_cause` | 50.00% |
| `cp_cmderr` | 83.33% |
| `cp_consecutive` | 100.00% |
| `cp_dpc_origin` | 50.00% |
| `cp_haltreq_guard` | 100.00% |
| `cp_mode_transition` | 75.00% |
| `cp_prv` | 33.33% |
| `cp_prv_at_step` | 33.33% |
| `cp_sbaccess` | 33.33% |
| `cp_sberror` | 16.67% |
| `cp_stepie_irq` | 25.00% |
| `cp_stepped_class` | 62.50% |
| `x_cause_x_dpc` | 13.33% |
| `x_cause_x_prv` | 16.67% |
| `x_class_x_consecutive` | 43.75% |
| `x_class_x_prv` | 16.67% |
| `x_class_x_stepie` | 12.50% |
