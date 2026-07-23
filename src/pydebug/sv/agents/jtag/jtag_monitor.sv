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
    tap_state_e state       = TAP_TEST_LOGIC_RESET;
    logic [4:0] ir_reg      = '0;   // captured IR value
    logic [4:0] curr_ir     = '0;   // IR latched at Update-IR
    int         ir_bit      = 0;

    logic [63:0] dr_reg     = '0;   // captured DR shift register (TDI = request)
    logic [63:0] dr_out_reg = '0;   // captured DR shift register (TDO = response)
    int          dr_bit     = 0;

    forever begin
      // ---- Wait for rising TCK edge (TAP samples TMS/TDI here) -------------
      @(posedge vif.tck);

      if (!vif.trst_n) begin
        state      = TAP_TEST_LOGIC_RESET;
        ir_reg     = '0;
        curr_ir    = '0;
        dr_reg     = '0;
        dr_out_reg = '0;
        ir_bit     = 0;
        dr_bit     = 0;
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

        // Shift DR: sample TDI into dr_reg (request bits, LSB-first). TDO is
        // sampled separately below, at the same simulation instant the driver
        // itself samples it (posedge + half-period, i.e. at the falling edge)
        // — the passive monitor cannot know tck_half_ns, so it waits for the
        // actual negedge instead, which is where the driver's own drive_bit()
        // task reads vif.tdo (jtag_driver.sv). TMS is stable across this wait
        // (driven once, well before this posedge, until the next drive_bit
        // call after this cycle's negedge), so reading it later at the bottom
        // of this loop iteration is still the same value used to select the
        // next TAP state — no timing hazard introduced by the extra wait.
        TAP_SHIFT_DR: begin
          logic tdo_sample;
          dr_reg = {vif.tdi, dr_reg[63:1]};
          @(negedge vif.tck);
          tdo_sample = vif.tdo;
          dr_out_reg = {tdo_sample, dr_out_reg[63:1]};
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
            emit_dmi_txn(dr_reg, dr_out_reg, dr_bit);
          end
          dr_reg     = '0;
          dr_out_reg = '0;
          dr_bit     = 0;
        end
        default: ;
      endcase

      // ---- Advance TAP state ------------------------------------------------
      state = tap_next_state(state, vif.tms);
    end
  endtask

  // ---------------------------------------------------------------------------
  // Build and broadcast a jtag_txn_c from a completed DR shift.
  // dr_raw/dr_out_raw are LSB-aligned: bit[0] = first bit shifted in/out.
  // DMI DR format: [1:0]=op  [33:2]=data  [40:34]=addr  (request, from TDI)
  //                [1:0]=status [33:2]=rdata            (response, from TDO)
  //
  // Per spec #6.1.5 the DMI request/response pair is pipelined one shift deep:
  // this transaction's dmi_rdata/dmi_status are the result of the *previous*
  // DMI op (dr_data_in/dmi_addr/dmi_op above are the *current*, newly-issued
  // request). Correlating response-to-request across that one-deep pipeline
  // is the checker's job (dm_checker.sv), not this monitor's — the monitor
  // only needs to report both halves of what it observed on this shift,
  // faithfully and without trying to interpret them.
  // ---------------------------------------------------------------------------
  function void emit_dmi_txn(logic [63:0] dr_raw, logic [63:0] dr_out_raw, int n_bits);
    jtag_txn_c txn;
    txn = jtag_txn_c::type_id::create("mon_txn");

    // Both shift registers were filled the same way (right-shift per bit, so
    // bit[63] holds the FIRST bit shifted and bit[63-n_bits+1] the last) —
    // right-align both identically before slicing out fields.
    txn.dr_data_in  = dr_raw     >> (64 - n_bits);
    txn.dr_data_out = dr_out_raw >> (64 - n_bits);
    txn.dr_len      = n_bits;
    txn.ir_val      = 5'h11;
    txn.phase       = jtag_txn_c::PH_DR_ONLY;

    // Decode DMI request fields (this shift's own op/addr/wdata)
    txn.dmi_op    = txn.dr_data_in[1:0];
    txn.dmi_wdata = txn.dr_data_in[33:2];
    txn.dmi_addr  = txn.dr_data_in[40:34];

    // Decode DMI response fields (result of the *previous* shift, per #6.1.5)
    txn.unpack_dmi();

    `uvm_info("JTAG_MON",
      $sformatf("DMI txn: addr=0x%02h op=%02b wdata=0x%08h  (prev-op result: status=%02b rdata=0x%08h)",
                txn.dmi_addr, txn.dmi_op, txn.dmi_wdata, txn.dmi_status, txn.dmi_rdata), UVM_MEDIUM)

    analysis_port.write(txn);
  endfunction

endclass : jtag_monitor
