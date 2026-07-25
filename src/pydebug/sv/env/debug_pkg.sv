// =============================================================================
// debug_pkg.sv - RISC-V debug UVM environment package
// =============================================================================

package debug_pkg;

  import uvm_pkg::*;
  import jtag_pkg::*;
  `include "uvm_macros.svh"

  `include "../sequences/dmi_read_seq.sv"
  `include "../sequences/dmi_write_seq.sv"
  `include "../sequences/reset_tap_seq.sv"
  `include "scoreboard.sv"
  // Must precede covergroups.sv AND dm_checker.sv: both instantiate
  // dut_config_reader directly (`new()`, not just a handle), which needs the
  // full class definition, not just a forward declaration.
  `include "../model/dut_config_reader.sv"
  // Must precede env.sv: env instantiates debug_coverage.
  `include "../fcov/covergroups.sv"
  // Must precede dm_ref_model.sv: hart_state_s's halted/running/resume_ack
  // fields are hart_signal_bit handles, constructed by dm_ref_model.sv.
  `include "../model/hart_signal_bit.sv"
  // Must precede dm_checker.sv: the checker instantiates dm_ref_model.
  `include "../model/dm_ref_model.sv"
  // Must precede env.sv: env instantiates dm_checker.
  `include "dm_checker.sv"
  `include "env.sv"
  `include "py_bridge.sv"
  `include "rv_dbg_base_test.sv"

endpackage : debug_pkg
