// =============================================================================
// jtag_sequencer.sv — JTAG Sequencer
// Included inside jtag_pkg
// =============================================================================

class jtag_sequencer extends uvm_sequencer #(jtag_txn_c);
  `uvm_component_utils(jtag_sequencer)

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

endclass : jtag_sequencer
