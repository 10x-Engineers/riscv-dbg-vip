// ══════════════════════════════════════════════════════════════════════════════
// dmi_scan_seq.sv — one raw DMI DR scan: no IR scan, no busy retry
//
// jtag_dmi_read_seq / jtag_dmi_write_seq put an IR scan in front of every DR
// scan, which gives the DTM enough TCK edges to finish the previous request,
// and retry on busy. Neither can provoke a DMI busy, so the DTM's busy arms in
// dmi_jtag.sv were unreachable. This scan goes Update-DR -> RTI -> Select-DR ->
// Capture-DR, three TCK edges, which is fewer than a request needs to cross
// the CDC and back.
//
// The IR must already hold DMI (any earlier read/write leaves it there).
// `status` is the dmistat captured by THIS scan -- the result of the previous
// request (#6.1.5), and BUSY (3) if that request was still in flight.
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_scan_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_scan_seq)

    logic [1:0]  op;
    logic [6:0]  addr;
    logic [31:0] data;
    logic [1:0]  status;

    function new(string name = "jtag_dmi_scan_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("dmi_scan");
        uvm_sequence_item rsp_item;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = data;
        txn.dmi_op    = op;
        txn.pack_dmi();
        txn.phase     = jtag_txn_c::PH_DR_ONLY;
        start_item(txn);
        finish_item(txn);
        get_response(rsp_item);
        $cast(txn, rsp_item);
        status = txn.dmi_status;
    endtask
endclass
