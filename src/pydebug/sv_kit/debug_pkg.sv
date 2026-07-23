// =============================================================================
// debug_pkg.sv - RISC-V debug UVM environment package
// =============================================================================

package debug_pkg;

  import uvm_pkg::*;
  import jtag_pkg::*;
  `include "uvm_macros.svh"

  `include "dmi_read_seq.sv"
  `include "dmi_write_seq.sv"
  `include "reset_tap_seq.sv"
  `include "scoreboard.sv"
  // Must precede env.sv: env instantiates debug_coverage.
  `include "covergroups.sv"
  // Must precede dm_checker.sv: the checker instantiates dm_ref_model.
  `include "dm_ref_model.sv"
  // Must precede env.sv: env instantiates dm_checker.
  `include "dm_checker.sv"
  `include "env.sv"
  `include "py_bridge.sv"
  `include "rv_dbg_base_test.sv"

endpackage : debug_pkg
