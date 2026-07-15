// =============================================================================
// jtag_driver.sv — Full JTAG TAP Driver
// Included inside jtag_pkg
// Generates TCK, drives TMS/TDI, implements IEEE 1149.1 state machine
// Supports: configurable TCK frequency via config_db (tck_half_ns)
//           get_response() for sequence self-checking
// =============================================================================

class jtag_driver extends uvm_driver #(jtag_txn_c);
  `uvm_component_utils(jtag_driver)

  virtual jtag_if vif;

  // Local TAP state tracker
  tap_state_e tap_state;

  // TCK half-period — configurable via config_db key "tck_half_ns" (int unsigned)
  // Default = 10 ns => 50 MHz JTAG
  int unsigned tck_half_ns = 10;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual jtag_if)::get(this, "", "jtag_vif", vif))
      `uvm_fatal("JTAG_DRV", "Virtual jtag_if not found in config_db")
    // Optional: override TCK frequency
    void'(uvm_config_db #(int unsigned)::get(this, "", "tck_half_ns", tck_half_ns));
    `uvm_info("JTAG_DRV",
      $sformatf("TCK half-period = %0d ns  (JTAG ~%0d MHz)",
                tck_half_ns, 500/tck_half_ns), UVM_MEDIUM)
  endfunction

  task run_phase(uvm_phase phase);
    jtag_txn_c txn;
    // Initialise signals
    vif.tck   = 1'b0;
    vif.tdi   = 1'b0;
    vif.tms   = 1'b1;
    vif.trst_n = 1'b0;
    tap_state  = TAP_TEST_LOGIC_RESET;

    // Hold reset for 5 TCK cycles, then release
    repeat (5) drive_bit_notdo(1'b1, 1'b0);
    vif.trst_n = 1'b1;

    // Drive to Run-Test-Idle
    drive_bit_notdo(1'b0, 1'b0);
    tap_state = TAP_RUN_TEST_IDLE;

    forever begin
      seq_item_port.get_next_item(txn);
      drive_txn(txn);
      // Return filled-in response to sequence (dmi_rdata/dmi_status populated)
      seq_item_port.item_done(txn);
    end
  endtask

  // ---------------------------------------------------------------------------
  // Drive a single TCK bit.  TMS and TDI are set BEFORE the rising edge.
  // Returns TDO sampled on the falling edge.
  // ---------------------------------------------------------------------------
  task drive_bit(input logic tms_val, input logic tdi_val,
                 output logic tdo_val);
    vif.tms = tms_val;
    vif.tdi = tdi_val;
    #(tck_half_ns * 1ns);
    vif.tck = 1'b1;
    #(tck_half_ns * 1ns);
    tdo_val = vif.tdo;
    vif.tck = 1'b0;
    tap_state = tap_next_state(tap_state, tms_val);
  endtask

  // Convenience overload — no TDO capture needed
  task drive_bit_notdo(input logic tms_val, input logic tdi_val);
    logic tdo_dummy;
    drive_bit(tms_val, tdi_val, tdo_dummy);
  endtask

  // ---------------------------------------------------------------------------
  // Dispatch one transaction
  // ---------------------------------------------------------------------------
  task drive_txn(jtag_txn_c txn);
    case (txn.phase)
      jtag_txn_c::PH_IR_ONLY:    drive_ir(txn);
      jtag_txn_c::PH_DR_ONLY:    drive_dr(txn);
      jtag_txn_c::PH_IR_THEN_DR: begin drive_ir(txn); drive_dr(txn); end
      default: `uvm_error("JTAG_DRV", "Unknown txn phase")
    endcase
    `uvm_info("JTAG_DRV", txn.convert2string(), UVM_HIGH)
  endtask

  // ---------------------------------------------------------------------------
  // Shift IR — navigate RTI → Shift-IR, clock in ir_val LSB-first,
  //            then navigate back to RTI
  // ---------------------------------------------------------------------------
  task drive_ir(jtag_txn_c txn);
    `uvm_info("JTAG_DRV",
      $sformatf("IR shift: ir=%05b (%0d bits)", txn.ir_val, txn.ir_len),
      UVM_MEDIUM)
    drive_bit_notdo(1'b1, 1'b0);   // Select-DR-Scan
    drive_bit_notdo(1'b1, 1'b0);   // Select-IR-Scan
    drive_bit_notdo(1'b0, 1'b0);   // Capture-IR
    drive_bit_notdo(1'b0, 1'b0);   // Shift-IR (first shift with TMS=0)
    for (int i = 0; i < txn.ir_len; i++) begin
      logic tms_out = (i == txn.ir_len - 1) ? 1'b1 : 1'b0;
      drive_bit_notdo(tms_out, txn.ir_val[i]);
    end
    drive_bit_notdo(1'b1, 1'b0);   // Update-IR
    drive_bit_notdo(1'b0, 1'b0);   // RTI
  endtask

  // ---------------------------------------------------------------------------
  // Shift DR — navigate RTI → Shift-DR, clock dr_len bits in/out,
  //            then back to RTI.  Captured bits go to txn.dr_data_out.
  //            DMI response fields unpacked into txn.dmi_rdata / dmi_status.
  // ---------------------------------------------------------------------------
  task drive_dr(jtag_txn_c txn);
    logic tdo_bit;
    `uvm_info("JTAG_DRV",
      $sformatf("DR shift: data_in=0x%0h (%0d bits)", txn.dr_data_in, txn.dr_len),
      UVM_MEDIUM)

    txn.dr_data_out = '0;

    drive_bit_notdo(1'b1, 1'b0);   // Select-DR-Scan
    drive_bit_notdo(1'b0, 1'b0);   // Capture-DR
    drive_bit_notdo(1'b0, 1'b0);   // Shift-DR (first shift, TMS=0)

    for (int i = 0; i < txn.dr_len; i++) begin
      logic tms_out = (i == txn.dr_len - 1) ? 1'b1 : 1'b0;
      drive_bit(tms_out, txn.dr_data_in[i], tdo_bit);
      txn.dr_data_out[i] = tdo_bit;
    end

    drive_bit_notdo(1'b1, 1'b0);   // Update-DR
    drive_bit_notdo(1'b0, 1'b0);   // RTI

    // Always decode DMI fields from shift result
    txn.unpack_dmi();
  endtask

endclass : jtag_driver
