// =============================================================================
// jtag_pkg.sv — JTAG VIP Package
// =============================================================================

package jtag_pkg;

  import uvm_pkg::*;
  import dm_defines_pkg::*;   // jtag_instr_e, dmi_op_e, DMI_ABITS etc.
  `include "uvm_macros.svh"

  // Order matters: types first, then classes that use them
  `include "types.sv"         // tap_state_e, tap_next_state()
  `include "jtag_txn.sv"
  `include "jtag_driver.sv"
  `include "jtag_monitor.sv"
  `include "jtag_agent.sv"

endpackage : jtag_pkg
