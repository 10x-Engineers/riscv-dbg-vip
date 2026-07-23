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
        uvm_sequence_item rsp_item;
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = data;
        txn.dmi_op    = 2'b10;  // DMI_WRITE
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);
        // Same explicit pull as jtag_dmi_read_seq.sv, for consistency -- NOTE
        // this does NOT retry on dmi_status==BUSY the way the read sequence
        // does. That is a pre-existing gap, not something this change fixes:
        // a write that comes back busy is silently treated as done today, and
        // no caller inspects txn.dmi_status afterward. Flagged, not resolved
        // here -- ask before changing write's retry semantics, since that is
        // a behavioral change, not a plumbing one.
        get_response(rsp_item);
        $cast(txn, rsp_item);
    endtask
endclass
