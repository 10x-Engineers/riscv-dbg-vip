// =============================================================================
// jtag_agent.sv — JTAG Agent
// Included inside jtag_pkg
// =============================================================================

class jtag_agent extends uvm_agent;
  `uvm_component_utils(jtag_agent)

  jtag_driver    driver;
  jtag_monitor   monitor;
  uvm_sequencer#(jtag_txn_c) sequencer;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    string jtag_master;
    super.build_phase(phase);

    // Default to ACTIVE unless JTAG_MASTER is set to openocd
    if ($value$plusargs("JTAG_MASTER=%s", jtag_master)) begin
      if (jtag_master == "openocd") begin
        is_active = UVM_PASSIVE;
      end
    end

    monitor = jtag_monitor::type_id::create("monitor", this);

    if (get_is_active() == UVM_ACTIVE) begin
      sequencer = uvm_sequencer#(jtag_txn_c)::type_id::create("sequencer", this);
      driver    = jtag_driver::type_id::create("driver", this);
    end
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE)
      driver.seq_item_port.connect(sequencer.seq_item_export);
  endfunction

endclass : jtag_agent