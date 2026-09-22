// =============================================================================
// jtag_txn.sv — JTAG sequence item
// Included inside jtag_pkg
// =============================================================================

class jtag_txn_c extends uvm_sequence_item;
  `uvm_object_utils(jtag_txn_c)

  // ---- IR fields -----------------------------------------------------------
  rand logic [4:0]  ir_val;      // 5-bit instruction register value
  int unsigned      ir_len = 5;  // always 5 for RISC-V DTM

  // ---- DR / DMI fields ------------------------------------------------------
  // Raw DR shift value (up to 64 bits; for DMI = 41 bits)
  rand logic [63:0] dr_data_in;  // data shifted in (written)
  logic      [63:0] dr_data_out; // data captured out (read back)
  int unsigned      dr_len;      // number of bits to shift

  // Decoded DMI fields (populated by driver before sending / by monitor on capture)
  rand logic [6:0]  dmi_addr;
  rand logic [31:0] dmi_wdata;
  rand logic [1:0]  dmi_op;     // dmi_op_e cast to logic
  logic      [31:0] dmi_rdata;
  logic      [1:0]  dmi_status;

  // Phase flag: IR_ONLY | DR_ONLY | IR_THEN_DR | TAP_RESET (TMS=1 x5, no shift)
  // | TMS_WALK (dr_len TMS bits from dr_data_in, LSB first, TDI held at 1)
  typedef enum { PH_IR_ONLY, PH_DR_ONLY, PH_IR_THEN_DR, PH_TAP_RESET, PH_TMS_WALK } txn_phase_e;
  rand txn_phase_e phase;

  // Route each shift through Pause and Exit2 (Exit1 -> Pause -> Exit2 ->
  // Update) instead of Exit1 -> Update. Only raw scans set it.
  bit pause = 0;

  constraint default_dr_len_c {
    // For DMI instruction, DR is 41 bits
    if (ir_val == 5'h11) dr_len == 41;
    else                 dr_len == 32;
  }

  function new(string name = "jtag_txn_c");
    super.new(name);
    ir_len = 5;
  endfunction

  // Pack DMI fields into dr_data_in: {addr[6:0], data[31:0], op[1:0]}
  //
  // The 41-bit length assumes `dtmcs.abits` == 7, which is what both DUTs'
  // DTMs implement and what `dmi_jtag_tap` defaults to. It is NOT a spec
  // constant: #6.1.4 makes abits implementation-defined and a debugger is
  // meant to read it out of dtmcs before its first DMI scan. On a DTM with a
  // different abits every scan here would be misaligned by the difference --
  // addresses and data shifted into the wrong fields, with no error anywhere,
  // which is the worst shape a bug can take.
  //
  // Deliberately not parameterised yet: the length is baked into the monitor's
  // field slices and the checker's correlation as well, so changing it is a
  // three-file change that wants its own regression rather than a drive-by.
  // Reviewed and recorded in #9; revisit when a third DTM appears.
  function void pack_dmi();
    dr_data_in = {26'h0, dmi_addr, dmi_wdata, dmi_op};
    dr_len      = 41;
    ir_val      = 5'h11; // JTAG_DMI
  endfunction

  // Unpack dr_data_out into DMI response fields
  function void unpack_dmi();
    dmi_status = dr_data_out[1:0];
    dmi_rdata  = dr_data_out[33:2];
  endfunction

  function void do_copy(uvm_object rhs);
    jtag_txn_c rhs_;

    if (!$cast(rhs_, rhs)) begin
      `uvm_fatal("JTAG_TXN", "do_copy rhs is not a jtag_txn_c")
    end

    super.do_copy(rhs);
    ir_val      = rhs_.ir_val;
    ir_len      = rhs_.ir_len;
    dr_data_in  = rhs_.dr_data_in;
    dr_data_out = rhs_.dr_data_out;
    dr_len      = rhs_.dr_len;
    dmi_addr    = rhs_.dmi_addr;
    dmi_wdata   = rhs_.dmi_wdata;
    dmi_op      = rhs_.dmi_op;
    dmi_rdata   = rhs_.dmi_rdata;
    dmi_status  = rhs_.dmi_status;
    phase       = rhs_.phase;
    pause       = rhs_.pause;
  endfunction

  function string convert2string();
    return $sformatf(
      "jtag_txn: ir=%05b ph=%s dmi_addr=0x%02h dmi_op=%02b dmi_wdata=0x%08h dmi_rdata=0x%08h stat=%02b",
      ir_val, phase.name(), dmi_addr, dmi_op, dmi_wdata, dmi_rdata, dmi_status);
  endfunction

endclass : jtag_txn_c
