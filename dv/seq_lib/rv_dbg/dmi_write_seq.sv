// ══════════════════════════════════════════════════════════════════════════════
// JTAG DMI Write Sequence
// Performs one IR+DR shift: {addr, data, DMI_WRITE}
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_write_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_write_seq)

    logic [6:0]  addr;
    logic [31:0] data;

    function new(string name = "jtag_dmi_write_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("dmi_wr");
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = data;
        txn.dmi_op    = 2'b10;  // DMI_WRITE
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);
    endtask
endclass
