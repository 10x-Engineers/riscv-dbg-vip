// =============================================================================
// jtag_monitor.sv — JTAG Monitor
// Tracks TAP state, captures IR and DR shift registers,
// emits jtag_txn_c on every Update-DR when instruction == JTAG_DMI
// =============================================================================

class jtag_monitor extends uvm_monitor;
  `uvm_component_utils(jtag_monitor)

  virtual jtag_if vif;
  uvm_analysis_port #(jtag_txn_c) analysis_port;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    analysis_port = new("analysis_port", this);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual jtag_if)::get(this, "", "jtag_vif", vif))
      `uvm_fatal("JTAG_MON", "Virtual jtag_if not found in config_db")
  endfunction

  task run_phase(uvm_phase phase);
    monitor_tap();
  endtask

  // ---------------------------------------------------------------------------
  // TAP state tracker — runs forever, watches posedge TCK
  // ---------------------------------------------------------------------------
  task monitor_tap();
    tap_state_e state     = TAP_TEST_LOGIC_RESET;
    logic [4:0] ir_reg    = '0;   // captured IR value
    logic [4:0] curr_ir   = '0;   // IR latched at Update-IR
    int         ir_bit    = 0;

    logic [63:0] dr_reg   = '0;   // captured DR shift register
    int          dr_bit   = 0;

    forever begin
      // ---- Wait for rising TCK edge (TAP samples TMS/TDI here) -------------
      @(posedge vif.tck);

      if (!vif.trst_n) begin
        state   = TAP_TEST_LOGIC_RESET;
        ir_reg  = '0;
        curr_ir = '0;
        dr_reg  = '0;
        ir_bit  = 0;
        dr_bit  = 0;
        continue;
      end

      // ---- Capture phase actions (before next-state update) -----------------
      case (state)
        TAP_CAPTURE_IR: ir_bit = 0;
        TAP_CAPTURE_DR: dr_bit = 0;

        // Shift IR: sample TDI into ir_reg shift register (LSB-first)
        TAP_SHIFT_IR: begin
          ir_reg = {vif.tdi, ir_reg[4:1]};
          ir_bit++;
        end

        // Shift DR: sample TDI into dr_reg shift register (LSB-first)
        TAP_SHIFT_DR: begin
          dr_reg = {vif.tdi, dr_reg[63:1]};
          // Shift right so MSB arrives last; bits fill from position (dr_bit)
          dr_bit++;
        end

        // Update-IR: latch the new instruction
        TAP_UPDATE_IR: begin
          curr_ir = ir_reg;
          `uvm_info("JTAG_MON",
            $sformatf("IR updated to 5'b%05b", curr_ir), UVM_HIGH)
        end

        // Update-DR: emit transaction if we were shifting DMI
        TAP_UPDATE_DR: begin
          if (curr_ir == 5'h11) begin  // JTAG_DMI
            emit_dmi_txn(dr_reg, dr_bit);
          end
          dr_reg  = '0;
          dr_bit  = 0;
        end
        default: ;
      endcase

      // ---- Advance TAP state ------------------------------------------------
      state = tap_next_state(state, vif.tms);
    end
  endtask

  // ---------------------------------------------------------------------------
  // Build and broadcast a jtag_txn_c from a completed DR shift
  // dr_raw is LSB-aligned: dr_raw[0] = first bit shifted in
  // DMI DR format: [1:0]=op  [33:2]=data  [40:34]=addr
  // ---------------------------------------------------------------------------
  function void emit_dmi_txn(logic [63:0] dr_raw, int n_bits);
    jtag_txn_c txn;
    txn = jtag_txn_c::type_id::create("mon_txn");

    // The shift register was filled MSB-first (TDI sampled MSB→bit0 in our
    // right-shift loop), so we need to reverse to get LSB-first alignment.
    // Actually we shifted right so dr_reg[63] has the FIRST bit shifted in
    // and dr_reg[63-n_bits+1] has the last bit.  Right-align:
    txn.dr_data_in  = dr_raw >> (64 - n_bits);
    txn.dr_data_out = '0;
    txn.dr_len      = n_bits;
    txn.ir_val      = 5'h11;
    txn.phase       = jtag_txn_c::PH_DR_ONLY;

    // Decode DMI fields from right-aligned DR
    txn.dmi_op    = txn.dr_data_in[1:0];
    txn.dmi_wdata = txn.dr_data_in[33:2];
    txn.dmi_addr  = txn.dr_data_in[40:34];

    `uvm_info("JTAG_MON",
      $sformatf("DMI txn: addr=0x%02h op=%02b data=0x%08h",
                txn.dmi_addr, txn.dmi_op, txn.dmi_wdata), UVM_MEDIUM)

    analysis_port.write(txn);
  endfunction

endclass : jtag_monitor
