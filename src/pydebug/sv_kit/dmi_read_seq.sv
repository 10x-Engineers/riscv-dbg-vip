// ══════════════════════════════════════════════════════════════════════════════
// JTAG DMI Read Sequence
// Phase-1: IR+DR shift with op=READ → queues read in dmi_jtag FSM
// Phase-2: IR+DR shift with op=NOP  → captures the result; retries if BUSY
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_read_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_read_seq)

    logic [6:0]  addr;
    logic [31:0] rsp_data;

    function new(string name = "jtag_dmi_read_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn;

        // ── Phase 1: issue DMI READ ─────────────────────────────────────────
        txn = new("dmi_rd_req");
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = 32'h0;
        txn.dmi_op    = 2'b01;  // DMI_READ
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);

        // ── Phase 2: poll with NOP until result is captured ─────────────────
        do begin
            txn = new("dmi_rd_cap");
            txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
            txn.dmi_addr  = 7'h0;
            txn.dmi_wdata = 32'h0;
            txn.dmi_op    = 2'b00;  // DMI_NOP
            txn.pack_dmi();
            start_item(txn);
            finish_item(txn);
            // txn.dmi_rdata / dmi_status populated by driver via unpack_dmi()
        end while (txn.dmi_status == 2'b11);  // retry while DMI_BUSY

        rsp_data = txn.dmi_rdata;
    endtask
endclass
