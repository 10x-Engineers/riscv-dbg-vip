// ══════════════════════════════════════════════════════════════════════════════
// JTAG TAP Reset Sequence
// Drives TMS=1 for 5 TCK cycles to force Test-Logic-Reset from any state, then
// returns to Run-Test/Idle.
//
// This used to be an IR scan of BYPASS, on the belief that the driver passed
// through Test-Logic-Reset on its way to Shift-IR. It does not (RTI ->
// Select-DR -> Select-IR -> Capture-IR), so no "TAP reset" ever reset the TAP,
// and dmi_jtag's test_logic_reset arm stayed uncovered while TC-DTM-014 passed.
// ══════════════════════════════════════════════════════════════════════════════
class jtag_tap_reset_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_tap_reset_seq)

    function new(string name = "jtag_tap_reset_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("tap_rst");
        uvm_sequence_item rsp_item;
        txn.phase = jtag_txn_c::PH_TAP_RESET;
        start_item(txn);
        finish_item(txn);
        // The driver returns every item; drain it (see dmi_read_seq.sv).
        get_response(rsp_item);
    endtask
endclass
