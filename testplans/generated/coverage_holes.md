# Coverage holes — proposed testplan items

Generated from `testplans/generated/coverage_model.yaml` against `testplans/riscv_debug_testplan.md`.

Each row is a bin the coverage model says matters and no testplan
item claims. Each needs a testplan item and a test, or a
documented exclusion.

| Covergroup | Coverpoint | Bin | Spec | Why it matters |
|---|---|---|---|---|
| `cg_dtm_dmi` | `cp_idle_cycles` | `above_advertised` | dtm.html#dtmcs | Generous idling — the baseline every other test runs at. |
| `cg_dtm_dmi` | `x_op_x_result` | `x_op_x_result` | — | no testplan item claims this bin |
| `cg_hart_selection` | `cp_hartsel_class` | `last_existing` | debug_module.html#dmcontrol | The highest implemented index — the boundary the DM must still decode. |
| `cg_hart_selection` | `cp_all_vs_any` | `neither` | debug_module.html#dmstatus | No selected hart in this state. |
| `cg_reset` | `cp_activity_at_reset` | `idle` | debug_module.html#reset | Baseline. |
| `cg_run_control` | `cp_halt_latency` | `immediate` | debug_module.html#dmcontrol | The common case on a hart executing ordinary instructions. |
| `cg_step_external` | `cp_stepped_class` | `not_taken_branch` | Sdext.html#stepbit | Falls through: dpc is the sequential next address. |
| `cg_step_external` | `cp_consecutive_steps` | `across_loop_backedge` | Sdext.html#stepbit | Stepping past a backward branch, where dpc must follow the branch. |
| `cg_step_external` | `x_class_x_privilege` | `x_class_x_privilege` | — | no testplan item claims this bin |
| `cg_abstract_command` | `cp_cmdtype` | `reserved_cmdtype` | debug_module.html#abstractcs | Undefined type; must not hang the DM. |
| `cg_abstract_command` | `cp_aarsize` | `reserved_size` | debug_module.html#access-register | Undefined encodings must be rejected. |
| `cg_abstract_command` | `cp_cmderr` | `other` | debug_module.html#abstractcs | Catch-all; reaching it means the DM could not classify its own failure. |
| `cg_program_buffer` | `cp_progbuf_fill` | `partial` | debug_module.html#abstractcs | Ordinary use. |
| `cg_program_buffer` | `cp_progbuf_operation` | `memory_write` | debug_module.html#program-buffer | Store from the hart's point of view. |
| `cg_system_bus_access` | `cp_sberror` | `timeout` | debug_module.html#sbcs | The bus did not respond. |
| `cg_system_bus_access` | `cp_sberror` | `other` | debug_module.html#sbcs | Catch-all. |
| `cg_system_bus_access` | `cp_sb_trigger_mode` | `manual` | debug_module.html#sbcs | Explicit address then explicit data access. |
| `cg_system_bus_access` | `cp_sb_address_region` | `ram_body` | debug_module.html#sbcs | Ordinary mapped memory. |
| `cg_system_bus_access` | `cp_sb_address_region` | `ram_top` | debug_module.html#sbcs | Last mapped address — the boundary before the decode fails. |
| `cg_system_bus_access` | `x_size_x_alignment` | `x_size_x_alignment` | — | no testplan item claims this bin |
| `cg_triggers` | `cp_match_event` | `load_and_store` | Sdtrig.html#mcontrol6 | Both set — a watchpoint on any access. |
| `cg_triggers` | `cp_trigger_privilege` | `all_privileges` | Sdtrig.html#mcontrol6 | Fires anywhere. |
| `cg_triggers` | `x_match_x_privilege` | `x_match_x_privilege` | — | no testplan item claims this bin |
| `cg_register_access` | `x_interface_x_register` | `x_interface_x_register` | — | no testplan item claims this bin |
