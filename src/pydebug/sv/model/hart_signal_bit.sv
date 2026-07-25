// ══════════════════════════════════════════════════════════════════════════════
// hart_signal_bit.sv — One bit of DM state that is genuinely driven BY the
// hart, not the DM itself (spec #3.5: "The DM receives halted, running, and
// havereset signals from each hart"), and therefore reaches the DM through
// real, variable-latency hardware propagation an untimed model cannot
// predict synchronously (e.g. dm_mem.sv's halted_q, only set once the hart
// actually executes a debug-ROM entry write; a hart-side resumeack flip-flop
// cleared by dm_csrs.sv's clear_resumeack_o pulse and reasserted only after
// the hart genuinely resumes).
//
// set() is the model's own write-driven prediction of what the signal
// SHOULD eventually become -- used exactly like a plain bit everywhere
// dm_ref_model.sv's internal transition logic (apply_ndmreset,
// release_from_reset, apply_resumereq, ...) already computes one.
//
// observe() is what a real DMI read reports the DUT is showing RIGHT NOW.
// It unconditionally wins: rather than assert a prediction the DUT can
// legitimately still be catching up to for a real, variable number of
// cycles, this class just mirrors the latest real observation -- the same
// way a real debugger's own polling loop (dm.halt()/dm.resume()'s
// _poll_until) does, and the reason that stimulus never sees this as a
// functional bug even when the checker's own synchronous prediction would
// have. A genuine functional defect (the value never actually settling to
// what a write demanded) still surfaces through that same polling timeout,
// just not as a spurious single-read MODEL_MISMATCH.
//
// Not a UVM agent (driver/monitor/sequencer) in the traditional sense --
// "agent" here names its role (the one place responsible for this signal's
// current believed value), not the UVM component category.
// ══════════════════════════════════════════════════════════════════════════════
class hart_signal_bit;
    local bit value;

    function new(bit initial_value = 1'b0);
        value = initial_value;
    endfunction

    function bit get();
        return value;
    endfunction

    // The model's own write-driven prediction.
    function void set(bit v);
        value = v;
    endfunction

    // A real DMI read's observed value -- always wins, no comparison.
    function void observe(bit v);
        value = v;
    endfunction
endclass : hart_signal_bit
