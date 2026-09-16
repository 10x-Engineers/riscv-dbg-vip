// ══════════════════════════════════════════════════════════════════════════════
// jtag_scan_seq.sv — one arbitrary IR + DR scan, optionally through Pause
//
// Every other sequence selects DMI or dtmcs. This one selects any instruction,
// so a scenario can scan IDCODE and BYPASS -- the TAP's own registers, which
// nothing else ever read -- and can route the shifts through Pause-IR/DR and
// Exit2-IR/DR, states the driver otherwise never enters.
//
// `rdata` is the first 32 captured bits. Selecting an instruction other than
// DMI leaves it selected; the next DMI read/write scans IR again anyway.
// ══════════════════════════════════════════════════════════════════════════════
class jtag_scan_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_scan_seq)

    logic [4:0]  ir;
    int unsigned dr_len;
    logic [31:0] wdata;
    bit          pause;
    logic [31:0] rdata;

    function new(string name = "jtag_scan_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("jtag_scan");
        uvm_sequence_item rsp_item;
        txn.phase      = jtag_txn_c::PH_IR_THEN_DR;
        txn.ir_val     = ir;
        txn.ir_len     = 5;
        txn.dr_len     = dr_len;
        txn.dr_data_in = {32'h0, wdata};
        txn.pause      = pause;
        start_item(txn);
        finish_item(txn);
        get_response(rsp_item);
        $cast(txn, rsp_item);
        rdata = txn.dr_data_out[31:0];
    endtask
endclass
