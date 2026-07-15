// ══════════════════════════════════════════════════════════════════════════════
// JTAG TAP Reset Sequence
// Drives TMS=1 for 5 TCK cycles to force Test-Logic-Reset from any state.
// Implemented as an IR-only transaction with ir_val=5'h1f (BYPASS).
// ══════════════════════════════════════════════════════════════════════════════
class jtag_tap_reset_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_tap_reset_seq)

    function new(string name = "jtag_tap_reset_seq");
        super.new(name);
    endfunction

    task body();
        // Send BYPASS IR — the driver navigates via TMS=1 enough times
        // to pass through Test-Logic-Reset on the way to Shift-IR, which
        // effectively resets the TAP.
        jtag_txn_c txn = new("tap_rst");
        txn.phase  = jtag_txn_c::PH_IR_ONLY;
        txn.ir_val = 5'h1f;  // BYPASS
        txn.ir_len = 5;
        start_item(txn);
        finish_item(txn);
    endtask
endclass
