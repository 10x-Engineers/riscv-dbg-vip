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
        uvm_sequence_item rsp_item;

        // ── Phase 1: issue DMI READ ─────────────────────────────────────────
        txn = new("dmi_rd_req");
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = 32'h0;
        txn.dmi_op    = 2'b01;  // DMI_READ
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);
        // The driver calls item_done(txn) for every transaction it processes,
        // unconditionally -- that response MUST be drained here even though
        // this phase's own result is never used, or it sits in the
        // sequencer's response queue and corrupts every later get_response()
        // in this sequence with an off-by-one, permanently stale response.
        // (Root cause of a real regression found this session: every read
        // came back 0 once this drain was missing -- see the retrospective
        // note at the end of this file before ever removing this again.)
        get_response(rsp_item);

        // ── Phase 2: poll with NOP until result is captured ─────────────────
        do begin
            uvm_sequence_item rsp_item;
            txn = new("dmi_rd_cap");
            txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
            txn.dmi_addr  = 7'h0;
            txn.dmi_wdata = 32'h0;
            txn.dmi_op    = 2'b00;  // DMI_NOP
            txn.pack_dmi();
            start_item(txn);
            finish_item(txn);
            // Explicit self-checking pull: the driver captures TDO and decodes
            // dmi_rdata/dmi_status (jtag_driver.sv, jtag_txn_c::unpack_dmi())
            // before handing this same item back as its own response via
            // item_done(txn) -- get_response() is the sequence's half of that
            // same handoff, rather than reading the mutation off `txn` directly.
            get_response(rsp_item);
            $cast(txn, rsp_item);
        end while (txn.dmi_status == 2'b11);  // retry while DMI_BUSY

        rsp_data = txn.dmi_rdata;
    endtask
endclass
