// =============================================================================
// dmi_assertions.sv — Protocol-tier SVA for the JTAG DTM's DMI register.
//
// Tier: PROTOCOL. This file ships with the VIP kit. It knows only about the JTAG
// DTM as the spec defines it (Ch.6 / dtm.adoc, and xml/jtag_registers.xml for the
// dmi and dtmcs register layouts) and nothing whatsoever about any DUT's internals.
// Bind it to `jtag_if` on any RISC-V target and it is meaningful. The DUT-specific
// register-tier assertions live in the integration directory, deliberately NOT here.
//
// Bind — NOT `bind jtag_if`, and not with `.*`
// -------------------------------------------
// The obvious line, `bind jtag_if dmi_assertions u_dmi_assertions (.*);`, does not
// work. Questa rejects it outright:
//     ** Error (vopt-3843): Can't instantiate a module (dmi_assertions) within an
//                           interface.
// So this checker is bound into the TESTBENCH module's scope with the interface's
// nets connected explicitly. In tb_top_cva6.sv (module tb_top_soc), which already
// declares `jtag_if jtag_vif` and the OpenOCD/UVM pin mux, the line is:
//
//     bind tb_top_soc dmi_assertions u_dmi_assertions (
//         .tck    (muxed_tck),
//         .tdi    (muxed_tdi),
//         .tms    (muxed_tms),
//         .trst_n (muxed_trstn),
//         .tdo    (jtag_vif.tdo)
//     );
//
// Connect the MUXED pins, not jtag_vif.tck/tms/tdi. tb_top_cva6.sv:85-88 muxes the
// UVM driver against the OpenOCD remote-bitbang adapter, and the muxed nets are what
// actually reach the DUT. Binding to jtag_vif directly would silently check nothing
// whenever +JTAG_MASTER=openocd is used — i.e. exactly the runs where a
// non-conformant TAP walk is most likely. TDO is the DUT's output and is driven onto
// jtag_vif.tdo (tb_top_cva6.sv:114) on both paths, so it is taken from there.
//
// Why pin level, and why a TAP FSM in here
// ----------------------------------------
// `jtag_if` carries only tck/tdi/tdo/tms/trst_n — there is no `dmi_op` signal to
// assert on, because at this boundary the DMI does not exist yet: it is a protocol
// layered on top of a DR shift. So this module reconstructs it, exactly the way
// `jtag_monitor.sv` does, from the TAP state machine. `tap_state_e` and
// `tap_next_state()` are imported from jtag_pkg rather than re-declared, so this
// checker's idea of the TAP can never drift from the driver's and monitor's.
//
// That reconstruction is the point: an assertion on a decoded transaction object
// can only ever catch what the monitor already decoded correctly. An assertion on
// the pins catches a DMI scan that is malformed *as pins* — a wrong-length scan, an
// abandoned scan, a reserved op — which is precisely the class of bug a transaction
// monitor silently normalises away.
//
// Sampling conventions (both match jtag_driver.sv / jtag_monitor.sv):
//   • TMS and TDI are sampled by the TAP on the rising edge of TCK.
//   • TDO is driven from the falling edge and is stable across the high phase, so
//     sampling it on the rising edge reads the bit belonging to that shift cycle —
//     the same bit jtag_driver.drive_bit() captures.
//
// Spec references (RISC-V Debug Specification, Ch.6 Debug Transport Module):
//   #6.1.4  dtmcs   — dmireset (bit 16), dtmhardreset (bit 17)
//   #6.1.5  dmi     — op/data/address layout, and the sticky busy/error rules
// =============================================================================

module dmi_assertions (
  input logic tck,
  input logic tdi,
  input logic tdo,
  input logic tms,
  input logic trst_n
);

  import dm_defines_pkg::*;   // jtag_instr_e, dmi_op_e, dmi_stat_e, DMI_DR_WIDTH
  import jtag_pkg::*;         // tap_state_e, tap_next_state()

  // ───────────────────────────────────────────────────────────────────────────
  // Reserved encodings the enums in dm_defines_pkg deliberately do not name.
  //
  // dm_defines_pkg::dmi_op_e enumerates nop/read/write and dmi_stat_e enumerates
  // success/failed/busy — the reserved encodings are absent from both by design, so
  // there is no named constant to reuse and none is invented here. The literals
  // below are the spec's own "Reserved" rows in xml/jtag_registers.xml:
  //   dmi.op   v=3 → "Reserved."
  //   dmi.op   v=1 → "Reserved." (when READ back as status)
  // ───────────────────────────────────────────────────────────────────────────
  localparam logic [1:0] DMI_OP_RESERVED   = 2'b11;  // #6.1.5 dmi.op, write meaning
  localparam logic [1:0] DMI_STAT_RESERVED = 2'b01;  // #6.1.5 dmi.op, read meaning

  // dtmcs bit positions (#6.1.4). Taken from the spec's machine-readable register
  // definition; dm_defines_pkg carries only DTMCS_RESET_VAL, not the field offsets.
  localparam int DTMCS_DMIRESET_BIT     = 16;  // "clears the sticky error state"
  localparam int DTMCS_DTMHARDRESET_BIT = 17;  // "returning all registers and
                                               //  internal state to their reset value"

  // ───────────────────────────────────────────────────────────────────────────
  // TAP reconstruction
  // ───────────────────────────────────────────────────────────────────────────

  tap_state_e  state;
  logic [4:0]  ir_shift;
  logic [4:0]  curr_ir;

  logic [DMI_DR_WIDTH-1:0] dr_in;    // shifted in  on TDI, LSB first
  logic [DMI_DR_WIDTH-1:0] dr_out;   // shifted out on TDO, LSB first
  int unsigned             dr_bits;  // how many bits this scan has shifted

  // True from the first Shift-DR bit of a DMI scan until its Update-DR. This is the
  // "in-flight" window the overlap assertion below polices.
  logic dmi_scan_open;

  // Modeled sticky status (#6.1.5): once the DTM reports failed or busy, that status
  // must persist until dmireset/dtmhardreset. Tracking it here is what lets the
  // checker distinguish "the DTM is still reporting the old error" (correct) from
  // "the DTM quietly forgot the error" (the bug — and a nasty one, because the whole
  // reason the status is sticky is to let debuggers batch scans and check once at the
  // end; a non-sticky DTM makes a batch of scans silently lose a failure).
  logic       sticky_valid;
  logic [1:0] sticky_status;

  wire is_dmi_ir   = (curr_ir == JTAG_DMI);
  wire is_dtmcs_ir = (curr_ir == JTAG_DTMCS);

  // Right-aligned view of the current scan, valid at Update-DR.
  wire [1:0] dmi_op_in      = dr_in[1:0];
  wire [1:0] dmi_status_out = dr_out[1:0];

  wire at_update_dr  = (state == TAP_UPDATE_DR);
  wire at_capture_dr = (state == TAP_CAPTURE_DR);
  wire at_shift_dr   = (state == TAP_SHIFT_DR);

  wire dmi_update  = at_update_dr  && is_dmi_ir && (dr_bits != 0);
  wire dtmcs_update = at_update_dr && is_dtmcs_ir && (dr_bits != 0);

  always_ff @(posedge tck or negedge trst_n) begin
    if (!trst_n) begin
      // #6.1 / IEEE 1149.1: nTRST "initializes the JTAG DTM asynchronously".
      state         <= TAP_TEST_LOGIC_RESET;
      ir_shift      <= '0;
      curr_ir       <= 5'h01;   // IDCODE — "When the TAP is reset, IR must default
                                // to 00001, selecting the IDCODE instruction."
      dr_in         <= '0;
      dr_out        <= '0;
      dr_bits       <= 0;
      dmi_scan_open <= 1'b0;
      sticky_valid  <= 1'b0;
      sticky_status <= '0;
    end else begin
      case (state)
        TAP_TEST_LOGIC_RESET: curr_ir <= 5'h01;

        TAP_CAPTURE_IR: ir_shift <= '0;
        TAP_SHIFT_IR:   ir_shift <= {tdi, ir_shift[4:1]};
        TAP_UPDATE_IR:  curr_ir  <= ir_shift;

        TAP_CAPTURE_DR: begin
          dr_in   <= '0;
          dr_out  <= '0;
          dr_bits <= 0;
        end

        TAP_SHIFT_DR: begin
          // LSB-first, right-shifting: bit 0 of the register is the first bit in.
          dr_in         <= {tdi, dr_in [DMI_DR_WIDTH-1:1]};
          dr_out        <= {tdo, dr_out[DMI_DR_WIDTH-1:1]};
          dr_bits       <= dr_bits + 1;
          dmi_scan_open <= dmi_scan_open | is_dmi_ir;
        end

        TAP_UPDATE_DR: begin
          dmi_scan_open <= 1'b0;

          // #6.1.5 dmi.op read meaning: "A previous operation failed ... This status
          // is sticky" / "A DMI operation was attempted while a prior DMI operation
          // was still in progress ... This status is sticky".
          if (is_dmi_ir && (dr_bits != 0)) begin
            if ((dmi_status_out == DMI_STAT_FAILED) ||
                (dmi_status_out == DMI_STAT_BUSY)) begin
              sticky_valid  <= 1'b1;
              sticky_status <= dmi_status_out;
            end
          end

          // #6.1.4 dmireset: "Writing 1 to this bit clears the sticky error state".
          // #6.1.4 dtmhardreset: "returning all registers and internal state to their
          // reset value" — which necessarily includes the sticky status.
          if (is_dtmcs_ir && (dr_bits != 0)) begin
            if (dr_in[DTMCS_DMIRESET_BIT] || dr_in[DTMCS_DTMHARDRESET_BIT]) begin
              sticky_valid  <= 1'b0;
              sticky_status <= '0;
            end
          end
        end

        default: ;
      endcase

      state <= tap_next_state(state, tms);
    end
  end

  // ───────────────────────────────────────────────────────────────────────────
  // Properties
  //
  // All are clocked on posedge TCK and disabled under nTRST, since nTRST puts the
  // DTM in a state where none of these statements are claims about anything.
  // ───────────────────────────────────────────────────────────────────────────

  default clocking cb @(posedge tck); endclocking
  default disable iff (!trst_n);

  // ── 1. Legal dmi_op encodings ──────────────────────────────────────────────
  //
  // #6.1.5 dmi.op, write meaning: 0=nop, 1=read, 2=write, 3="Reserved."
  // A debugger writing the reserved encoding is asking the DTM to do something the
  // spec does not define, so this is a stimulus-legality property: it protects the
  // suite from writing tests whose expected result cannot exist. It is the SVA
  // counterpart of invariants.py's INV-STIM-* checks.

  property p_dmi_op_legal;
    dmi_update |-> (dmi_op_in != DMI_OP_RESERVED);
  endproperty

  a_dmi_op_legal: assert property (p_dmi_op_legal)
    else $error("[DMI-SVA] Update-DR started DMI op=2'b11 (reserved) -- spec #6.1.5 dmi.op");

  // #6.1.5 dmi.op, read meaning: 0=success, 1="Reserved.", 2=failed, 3=busy.
  // Unlike the above this IS a DUT property: the DTM must never report the reserved
  // status.
  property p_dmi_status_legal;
    dmi_update |-> (dmi_status_out != DMI_STAT_RESERVED);
  endproperty

  a_dmi_status_legal: assert property (p_dmi_status_legal)
    else $error("[DMI-SVA] DTM reported dmi.op status=2'b01 (reserved) -- spec #6.1.5 dmi.op");

  // No X/Z on the op field of a scan the DTM is about to act on.
  property p_dmi_op_known;
    dmi_update |-> !$isunknown(dmi_op_in);
  endproperty

  a_dmi_op_known: assert property (p_dmi_op_known)
    else $error("[DMI-SVA] DMI op field contains X/Z at Update-DR");

  // ── 2. Sticky busy / error behaviour (#6.1.5) ──────────────────────────────
  //
  // "This status is sticky and can be cleared by writing dmireset in dtmcs."
  // The NOTE in #6.1.5 explains why this one matters more than it looks: "The
  // still-in-progress status is sticky to accommodate debuggers that batch together
  // a number of scans, which must all be executed or stop as soon as there's a
  // problem. For instance a series of scans may write a Debug Program and execute
  // it. If one of the writes fails but the execution continues, then the Debug
  // Program may hang or have other unexpected side effects."
  //
  // So a DTM that drops a sticky status does not merely misreport — it lets a
  // corrupted batch run to completion. Hence: once sticky, every subsequent DMI
  // Capture must keep reporting that same status until an explicit clear.

  property p_sticky_status_persists;
    (dmi_update && sticky_valid) |-> (dmi_status_out == sticky_status);
  endproperty

  a_sticky_status_persists: assert property (p_sticky_status_persists)
    else $error("[DMI-SVA] sticky DMI status %02b was not preserved (now %02b); only dtmcs.dmireset/dtmhardreset may clear it -- spec #6.1.5",
                sticky_status, dmi_status_out);

  // The converse half of the same sentence — "can be cleared by writing dmireset" —
  // is deliberately a COVER, not an assert. The tempting property is "after a
  // dtmcs.dmireset write, the next DMI scan must not report failed/busy", and it
  // would be wrong: a *new* DMI operation issued straight after the clear may
  // legitimately go busy on its own merits (#6.1.5 busy: "A DMI operation was
  // attempted while a prior DMI operation was still in progress"). Distinguishing a
  // stale sticky status from a freshly-earned one needs knowledge of what was in
  // flight, which lives in the sequence, not at the pins. So the honest pin-level
  // statement is: prove the clear path was exercised.
  c_dmireset_clears_sticky: cover property (
    dtmcs_update && (dr_in[DTMCS_DMIRESET_BIT] || dr_in[DTMCS_DTMHARDRESET_BIT]) && sticky_valid
  );

  // ── 3. No overlapping in-flight DR shift ───────────────────────────────────
  //
  // A DMI scan is atomic between Capture-DR and Update-DR: #6.1.5 starts the
  // operation "In Update-DR" and presents its result "In Capture-DR". A TAP that
  // re-enters Capture-DR while a scan is still open has abandoned a half-shifted
  // operation, and the debugger and the DM now disagree about what was requested.
  //
  // REACHABILITY — read before "fixing" this as dead code:
  // Trace the DR column in types.sv's tap_next_state(). EVERY exit from it funnels
  // through Update-DR: Exit1-DR(tms=1)→Update-DR, Exit1-DR(tms=0)→Pause-DR(tms=1)→
  // Exit2-DR, and Exit2-DR(tms=1)→Update-DR / (tms=0)→Shift-DR. There is no path from
  // Shift-DR back to Capture-DR that skips Update-DR, and Update-DR clears
  // dmi_scan_open. So against a CONFORMANT TAP this property is unreachable and
  // therefore vacuously true — it cannot be provoked by legal stimulus, and the
  // demonstration that it is live has to force dmi_scan_open directly.
  //
  // It is kept deliberately, and it is not decoration: `state` here is reconstructed
  // from the pins, so this fires if the DUT's TAP (or a bit-banged adapter such as
  // the OpenOCD path in tb_top_cva6.sv, which drives TMS from a socket and is under
  // no obligation to be conformant) ever produces a pin sequence that is not a legal
  // 1149.1 walk. That is a real class of bring-up bug and nothing else catches it.
  property p_no_overlapping_dr_scan;
    at_capture_dr |-> !dmi_scan_open;
  endproperty

  a_no_overlapping_dr_scan: assert property (p_no_overlapping_dr_scan)
    else $error("[DMI-SVA] Capture-DR entered while a DMI DR scan was still in flight (%0d bits shifted, no Update-DR) -- spec #6.1.5", dr_bits);

  // The reachable sibling of the above, and the one that earns its keep: nTRST
  // asserted part-way through a DMI scan. This IS provokable by legal-looking
  // stimulus — trst_n is a physical pin any adapter can drop at any moment — and it
  // desynchronises the debugger from the DTM exactly like an abandoned scan, because
  // the shifted bits are discarded without ever reaching Update-DR.
  //
  // Written as an IMMEDIATE assertion in an always block rather than a concurrent
  // `assert property`, for two reasons that both bit during bring-up of this file:
  //
  //  1. A concurrent property inherits this module's `default disable iff (!trst_n)`,
  //     which makes it self-defeating — the one event it exists to catch is trst_n
  //     going low, which is exactly the condition the default treats as "don't
  //     check". (Verified: with the default in force it never fires on a mid-scan
  //     nTRST. An explicit `disable iff` override did not suppress the time-0 sample
  //     either.)
  //  2. Concurrent properties sample in the preponed region, where dmi_scan_open is
  //     still X at the power-on X→0 transition of trst_n, and Questa reported a
  //     failure at 0 ns on every run. A standing false positive at time 0 is worse
  //     than no check: it trains everyone to ignore the log.
  //
  // The `!== 1'b1` (rather than `!`) is what makes it immune to the time-0 X: only a
  // definite 1 is a violation.
  always @(negedge trst_n) begin
    a_dmi_scan_not_aborted_by_trst: assert (dmi_scan_open !== 1'b1)
      else $error("[DMI-SVA] nTRST asserted mid-DMI-scan (%0d bits shifted, no Update-DR); the operation is silently discarded -- spec #6.1.5", dr_bits);
  end

  // A DMI scan that reaches Update-DR must be exactly abits+34 bits wide (#6.1.5
  // field layout: address[abits+33:34], data[33:2], op[1:0]). A short scan silently
  // misaligns every field, which is the single most common bring-up bug on a new DTM
  // and produces symptoms (wrong register touched) that look nothing like its cause.
  property p_dmi_scan_length;
    dmi_update |-> (dr_bits == DMI_DR_WIDTH);
  endproperty

  a_dmi_scan_length: assert property (p_dmi_scan_length)
    else $error("[DMI-SVA] DMI scan shifted %0d bits, expected %0d (abits=%0d) -- spec #6.1.5",
                dr_bits, DMI_DR_WIDTH, DMI_ABITS);

  // Shifting DR while the IR selects DMI but never reaching Update-DR is the same
  // hazard seen from the other side; covering it proves the negative test that
  // provokes it actually ran.
  c_dmi_scan_abandoned: cover property (at_capture_dr && dmi_scan_open);

  // ── 4. Coverage of the legal op encodings ──────────────────────────────────
  //
  // Not checks — evidence that the protocol tier was actually exercised. A green
  // assertion run over stimulus that never issued a read proves nothing.
  c_dmi_op_nop:   cover property (dmi_update && (dmi_op_in == DMI_NOP));
  c_dmi_op_read:  cover property (dmi_update && (dmi_op_in == DMI_READ));
  c_dmi_op_write: cover property (dmi_update && (dmi_op_in == DMI_WRITE));
  c_dmi_busy:     cover property (dmi_update && (dmi_status_out == DMI_STAT_BUSY));
  c_dmi_failed:   cover property (dmi_update && (dmi_status_out == DMI_STAT_FAILED));

endmodule : dmi_assertions
