// ══════════════════════════════════════════════════════════════════════════════
// dtmcs_seq.sv — access the DTM's own control/status register (dtmcs, IR 0x10)
//
// dtmcs lives in the DTM, not the DM, so it is not reachable through the DMI
// address space every other sequence uses. Without this, `dtmcs.dmireset` and
// `dmihardreset` cannot be driven at all, and the DTM's sticky-error recovery
// paths -- the whole reason those bits exist -- are untestable.
//
// Spec #6.1.4 (dtmcs):
//   [17] dmihardreset  W1 -- cancel outstanding DMI transactions and reset DTM
//   [16] dmireset      W1 -- clear the sticky error state, keep the transaction
//   [14:12] idle, [11:10] dmistat, [9:4] abits, [3:0] version   (all R)
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dtmcs_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dtmcs_seq)

    //: Value to shift in. 0 is a pure read -- both control bits are W1, so
    //: shifting zeros has no side effect and simply captures the status.
    logic [31:0] wdata = 32'h0;
    //: Captured dtmcs, valid after the sequence completes.
    logic [31:0] rdata;

    function new(string name = "jtag_dtmcs_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("dtmcs");
        uvm_sequence_item rsp_item;
        txn.phase      = jtag_txn_c::PH_IR_THEN_DR;
        txn.ir_val     = dm_defines_pkg::JTAG_DTMCS;
        txn.ir_len     = 5;
        txn.dr_len     = 32;            // dtmcs is 32 bits, not the DMI's 41
        txn.dr_data_in = {32'h0, wdata};
        start_item(txn);
        finish_item(txn);
        get_response(rsp_item);
        $cast(txn, rsp_item);
        rdata = txn.dr_data_out[31:0];
    endtask
endclass
