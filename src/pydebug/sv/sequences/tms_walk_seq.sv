// ══════════════════════════════════════════════════════════════════════════════
// tms_walk_seq.sv — drive an arbitrary TMS sequence (TDI held at 1)
//
// `bits` holds `count` TMS values, LSB first. The sequence must begin and end
// in Run-Test/Idle; the driver flags it otherwise. Select an instruction whose
// Update-DR is harmless (BYPASS) first: a walk through Update-DR with DMI
// selected would issue a DMI request from whatever the register held.
// ══════════════════════════════════════════════════════════════════════════════
class jtag_tms_walk_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_tms_walk_seq)

    int unsigned count;
    logic [31:0] bits;

    function new(string name = "jtag_tms_walk_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("tms_walk");
        uvm_sequence_item rsp_item;
        txn.phase      = jtag_txn_c::PH_TMS_WALK;
        txn.dr_len     = count;
        txn.dr_data_in = {32'h0, bits};
        start_item(txn);
        finish_item(txn);
        get_response(rsp_item);
    endtask
endclass
