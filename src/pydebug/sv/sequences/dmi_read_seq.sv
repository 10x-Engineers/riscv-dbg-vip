// ══════════════════════════════════════════════════════════════════════════════
// JTAG DMI Read Sequence
// Phase-1: IR+DR shift with op=READ → queues read in dmi_jtag FSM
// Phase-2: IR+DR shift with op=NOP  → captures the result; retries if BUSY
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_read_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_read_seq)

    logic [6:0]  addr;
    logic [31:0] rsp_data;

    //: NOP polls before concluding the DTM is stuck in sticky busy, and how
    //: many times to clear it and start over. Both are generous: a DM answers
    //: an ordinary read in one or two polls, and needing a reset at all means
    //: something kept the DM busy for longer than the link takes to ask.
    localparam int unsigned MaxBusyPolls  = 64;
    localparam int unsigned MaxBusyResets = 4;
    //: NOP scans between a dmireset and the re-issued read, to give the DM
    //: time to finish and to flush the DTM's stale result register.
    localparam int unsigned BusyDrainScans = 8;

    function new(string name = "jtag_dmi_read_seq");
        super.new(name);
    endfunction

    //: Phase 1, as its own task: the busy-recovery path has to re-issue it
    //: after a dmireset, because the reset discards the queued read.
    task issue_read(output jtag_txn_c txn);
        uvm_sequence_item rsp_item;
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
    endtask

    task body();
        jtag_txn_c txn;

        issue_read(txn);

        // ── Phase 2: poll with NOP until result is captured ─────────────────
        //
        // Busy is sticky (#6.1.5): once dtmcs.dmistat latches 3, EVERY later
        // DMI access returns busy until the debugger writes dtmcs.dmireset,
        // and the access that met it "did not happen". This loop used to be
        // `do ... while (status == busy)` with no reset in it, so a DM that
        // stayed busy long enough for the sticky bit to latch spun here for
        // the rest of the simulation -- 15,281 NOP scans and 17 seconds of
        // simulated time in the run that found this, on Ibex's cmderr
        // scenario. Nothing reported it, because the scoreboard used to abort
        // the run at the first busy it saw.
        //
        // So: poll a bounded number of times, then clear the sticky state and
        // re-issue the read, because the reset discards it.
        for (int unsigned attempt = 0; attempt < MaxBusyResets + 1; attempt++) begin
            bit captured = 1'b0;
            for (int unsigned poll = 0; poll < MaxBusyPolls; poll++) begin
                uvm_sequence_item rsp_item;
                txn = new("dmi_rd_cap");
                txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
                txn.dmi_addr  = 7'h0;
                txn.dmi_wdata = 32'h0;
                txn.dmi_op    = 2'b00;  // DMI_NOP
                txn.pack_dmi();
                start_item(txn);
                finish_item(txn);
                // Explicit self-checking pull: the driver captures TDO and
                // decodes dmi_rdata/dmi_status (jtag_driver.sv,
                // jtag_txn_c::unpack_dmi()) before handing this same item back
                // as its own response via item_done(txn) -- get_response() is
                // the sequence's half of that same handoff, rather than
                // reading the mutation off `txn` directly.
                get_response(rsp_item);
                $cast(txn, rsp_item);
                if (txn.dmi_status != 2'b11) begin
                    captured = 1'b1;
                    break;
                end
            end
            if (captured) break;

            if (attempt == MaxBusyResets) begin
                `uvm_error("DMI_RD", $sformatf(
                    "DMI still busy for addr 0x%02h after %0d dmireset(s) and %0d polls each",
                    addr, MaxBusyResets, MaxBusyPolls))
                break;
            end

            // Clear the sticky error, then re-issue: the read was discarded.
            // The dtmcs scan is built here rather than through jtag_dtmcs_seq
            // because that class is compiled after this one (debug_pkg.sv's
            // include order), and a read must not depend on which sequences
            // happen to have been declared before it.
            begin
                uvm_sequence_item rsp_item;
                jtag_txn_c rst_txn = new("dmi_rd_dmireset");
                rst_txn.phase      = jtag_txn_c::PH_IR_THEN_DR;
                rst_txn.ir_val     = dm_defines_pkg::JTAG_DTMCS;
                rst_txn.ir_len     = 5;
                rst_txn.dr_len     = 32;              // dtmcs is 32 bits
                rst_txn.dr_data_in = {32'h0, 32'h1 << 16};   // dmireset (W1)
                start_item(rst_txn);
                finish_item(rst_txn);
                get_response(rsp_item);
                `uvm_info("DMI_RD", $sformatf(
                    "DMI busy on addr 0x%02h; wrote dtmcs.dmireset and re-issuing",
                    addr), UVM_MEDIUM)
            end
            // Let the DM finish whatever kept it busy, and flush the DTM's
            // result register while doing it. Re-issuing straight after the
            // reset returns the PREVIOUS operation's data with status 0 --
            // the read was discarded by the reset, so the register still
            // holds what was shifted in before it, which is indistinguishable
            // from a fresh result by status alone. Observed as an abstractcs
            // read coming back with the command word in it.
            for (int unsigned drain = 0; drain < BusyDrainScans; drain++) begin
                uvm_sequence_item rsp_item;
                jtag_txn_c nop_txn = new("dmi_rd_drain");
                nop_txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
                nop_txn.dmi_addr  = 7'h0;
                nop_txn.dmi_wdata = 32'h0;
                nop_txn.dmi_op    = 2'b00;  // DMI_NOP
                nop_txn.pack_dmi();
                start_item(nop_txn);
                finish_item(nop_txn);
                get_response(rsp_item);
            end
            issue_read(txn);
        end

        rsp_data = txn.dmi_rdata;
    endtask
endclass
