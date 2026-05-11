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

  // Phase flag: IR_ONLY | DR_ONLY | IR_THEN_DR
  typedef enum { PH_IR_ONLY, PH_DR_ONLY, PH_IR_THEN_DR } txn_phase_e;
  rand txn_phase_e phase;

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
  endfunction

  function string convert2string();
    return $sformatf(
      "jtag_txn: ir=%05b ph=%s dmi_addr=0x%02h dmi_op=%02b dmi_wdata=0x%08h dmi_rdata=0x%08h stat=%02b",
      ir_val, phase.name(), dmi_addr, dmi_op, dmi_wdata, dmi_rdata, dmi_status);
  endfunction

endclass : jtag_txn_c
