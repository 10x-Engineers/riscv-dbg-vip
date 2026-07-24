// ══════════════════════════════════════════════════════════════════════════════
// dm_ref_model.sv — Executable SV golden-reference model of RISC-V Debug Module
// run control, plus self-consistency shadows for the abstract-command and
// System Bus Access data paths.
//
// This is the SV counterpart of `pydebug/src/pydebug/model/predictor.py`
// (`DMPredictor`) — ported field-for-field, not re-derived, so the two cannot
// silently drift apart in what they claim the spec requires. Per
// VERIFICATION_STRATEGY.md ("Checker implementation (SV register model)"),
// this is the model `dm_checker.sv` compares DUT reads against; the Python
// model is NOT run alongside it this pass (decided 2026-07-23) — the two are
// equivalent in intent but only one runs checking at a time.
//
// Scope, stated plainly (mirrors predictor.py's own documentation discipline):
//   - dmcontrol/dmstatus run control: full model, spec #3.5 Run Control,
//     #3.2 Reset, #3.14.1 dmstatus, #3.14.2 dmcontrol. Predicts every field on
//     every read, the same way predictor.py does.
//   - Abstract command (data0/command) and System Bus Access
//     (sbaddress0/sbdata0): SELF-CONSISTENCY shadows only. This model tracks
//     values *this same DMI traffic* wrote to a GPR/CSR or memory location and
//     checks they read back unchanged. It does NOT and cannot predict a DUT's
//     arbitrary initial hart-register or memory content — that would require
//     a full ISA/memory simulator, out of scope here. A register or address
//     never written by this traffic reports `has_model()==0` and is silently
//     not checked, not asserted against a guessed value.
//
// Bit positions for dmcontrol/command/sbcs/sbaddress0 are taken from
// `pydebug/src/pydebug/api/riscv_dm.py` — the actual stimulus generator that
// produces the real DMI traffic this model must agree with — not re-derived
// from the spec text a third time. dmstatus field positions match both
// riscv_dm.py and model/registers.py (cross-checked, identical).
// ══════════════════════════════════════════════════════════════════════════════

class dm_ref_model;

  // ── Per-hart state (spec #3.5: "For every hart, the Debug Module tracks 4
  // conceptual bits of state: halt request, resume ack, halt-on-reset request,
  // and hart reset. ... These 4 bits reset to 0, except for resume ack, which
  // may reset to either 0 or 1. The DM receives halted, running, and
  // havereset signals from each hart.") ─────────────────────────────────────
  typedef struct {
    bit halt_request;
    bit resume_ack;
    bit reset_haltreq;
    bit hart_reset;
    bit halted;
    bit running;
    bit havereset;       // sticky until ackhavereset
    bit available;
    bit unavail_sticky;  // sticky until ackunavail (spec #3.14.2)
    bit nonexistent;
  } hart_state_s;

  // ── Configuration (constructor args mirror predictor.py's DMPredictor) ────
  local int unsigned num_harts;
  local bit [3:0]    version;             // dmstatus.version encoding
  local bit          authenticated;
  local bit          impebreak;
  local bit          hasresethaltreq;
  local bit          supports_hartreset;
  local bit          supports_hasel;
  local bit          resumeack_reset;

  // ── DM-wide state ──────────────────────────────────────────────────────────
  hart_state_s harts[];
  bit                dmactive;
  bit                ndmreset;
  bit [19:0]         hartsel;
  bit                hasel;
  local bit          hartreset_level;

  // ── Abstract-command (data0/command) self-consistency shadow ─────────────
  local bit [31:0]   shadow_regs[bit [15:0]];   // regno -> last value WE wrote
  local bit [31:0]   staged_data0;              // last value written to data0
  local bit          data0_pending_valid;
  local bit [31:0]   data0_pending_value;
  // GPR x0 (regno 0x1000) is architecturally hardwired to 0 (base ISA), not a
  // DUT-specific fact — safe to assert on unconditionally, unlike any other
  // register we never wrote ourselves.
  local const bit [15:0] GPR_X0_REGNO = 16'h1000;

  // ── System Bus Access (sbaddress0/sbdata0) self-consistency shadow ────────
  local bit [31:0]   shadow_mem[bit [31:0]];    // addr -> last value WE wrote
  local bit [31:0]   sbaddress0_q;
  local bit          sbcs_read_on_addr_armed;   // last sbcs write's sbreadonaddr
  local bit          sbdata0_pending_valid;
  local bit [31:0]   sbdata0_pending_value;

  // ── Construction ───────────────────────────────────────────────────────────
  function new(
    int unsigned num_harts_        = 1,
    bit [3:0]    version_          = 4'd2,  // 0.13; both current DUTs (dm_defines_pkg.sv)
    bit          authenticated_    = 1'b1,
    bit          impebreak_        = 1'b0,
    bit          hasresethaltreq_  = 1'b1,
    bit          supports_hartreset_ = 1'b1,
    bit          supports_hasel_   = 1'b0,
    bit          resumeack_reset_  = 1'b0
  );
    num_harts          = num_harts_;
    version            = version_;
    authenticated      = authenticated_;
    impebreak          = impebreak_;
    hasresethaltreq    = hasresethaltreq_;
    supports_hartreset = supports_hartreset_;
    supports_hasel     = supports_hasel_;
    resumeack_reset    = resumeack_reset_;
    reset_dm(1'b1);
  endfunction

  // ── Reset (spec #3.14.2 dmactive=0) ───────────────────────────────────────
  // "The module's state ... takes its reset values (dmactive is the only bit
  // which can be written to something other than its reset value)." The
  // harts' own halted/running/havereset state is NOT reset here on a plain DM
  // reset (only on power_on) — spec #3.5: "If the DM is reset while a hart is
  // halted, it is UNSPECIFIED whether that hart resumes," so this model keeps
  // the hart where it was, same as predictor.py's reset_dm().
  function void reset_dm(bit power_on = 1'b0);
    hart_state_s prev[];
    prev = harts;

    dmactive        = 1'b0;
    ndmreset        = 1'b0;
    hartsel         = '0;
    hasel           = 1'b0;
    hartreset_level = 1'b0;

    harts = new[(num_harts > 0) ? num_harts : 1];
    foreach (harts[i]) begin
      harts[i] = '{default: 0};
      harts[i].resume_ack = resumeack_reset;
      // predictor.py's HartState.available defaults True ("powered and
      // clocked" -- #3.2); the struct-fill above zeroes it, so it must be
      // set explicitly here to match, same as the other per-hart fields.
      harts[i].available  = 1'b1;
      if (power_on || i >= prev.size()) begin
        harts[i].halted    = 1'b0;
        harts[i].running   = 1'b1;
        harts[i].havereset = 1'b0;
      end else begin
        harts[i].halted    = prev[i].halted;
        harts[i].running   = prev[i].running;
        harts[i].havereset = prev[i].havereset;
      end
    end
  endfunction

  // ── Hart selection (spec #3.14.2 hasel: "An implementation which does not
  // implement the hart array mask register must tie this field to 0" — with
  // hasel=0 there is exactly one selected hart, chosen by hartsel). ─────────
  local function int selected_index();
    return int'(hartsel);
  endfunction

  local function bit hart_exists(int idx);
    return (idx >= 0) && (idx < harts.size());
  endfunction

  local function bit is_nonexistent(int idx);
    return idx >= num_harts;
  endfunction

  // ── Write dispatch ─────────────────────────────────────────────────────────
  function void on_write(bit [6:0] addr, bit [31:0] value);
    case (addr)
      dm_defines_pkg::DM_ADDR_DMCONTROL:  write_dmcontrol(value);
      dm_defines_pkg::DM_ADDR_DATA0:      staged_data0 = value;
      dm_defines_pkg::DM_ADDR_COMMAND:    write_command(value);
      dm_defines_pkg::DM_ADDR_SBCS:       write_sbcs(value);
      dm_defines_pkg::DM_ADDR_SBADDRESS0: write_sbaddress0(value);
      dm_defines_pkg::DM_ADDR_SBDATA0:    write_sbdata0(value);
      default: ; // unmodeled address -- ignored, not an error
    endcase
  endfunction

  // ── dmcontrol write (spec #3.14.2; bit layout from riscv_dm.py dmcontrol())
  local function void write_dmcontrol(bit [31:0] value);
    bit        dmactive_f        = value[0];
    bit        ndmreset_f        = value[1];
    bit        clrresethaltreq_f = value[2];
    bit        setresethaltreq_f = value[3];
    bit [9:0]  hartselhi_f       = value[15:6];
    bit [9:0]  hartsello_f       = value[25:16];
    bit        hasel_f           = value[26];
    bit        ackunavail_f      = value[27];
    bit        ackhavereset_f    = value[28];
    bit        hartreset_f       = value[29];
    bit        resumereq_f       = value[30];
    bit        haltreq_f         = value[31];
    int        sel;

    // dmactive=0 resets the DM; spec permits dropping every other bit in the
    // same write, same as predictor.py.
    if (!dmactive_f) begin
      reset_dm(1'b0);
      return;
    end
    dmactive = 1'b1;

    // Selection updates first (#3.14.2: "Writes apply to the new value of
    // hartsel and hasel").
    hartsel = {hartselhi_f, hartsello_f};
    hasel   = supports_hasel ? hasel_f : 1'b0;
    foreach (harts[i]) harts[i].nonexistent = is_nonexistent(i);

    apply_ndmreset(ndmreset_f);
    apply_hartreset(hartreset_f && supports_hartreset);

    sel = selected_index();
    if (hasresethaltreq && hart_exists(sel)) begin
      // clr wins over a simultaneous set (mirrors the documented
      // set/clrkeepalive precedence in #3.14.2).
      if (clrresethaltreq_f)
        harts[sel].reset_haltreq = 1'b0;
      else if (setresethaltreq_f)
        harts[sel].reset_haltreq = 1'b1;
    end

    if (hart_exists(sel)) begin
      if (ackhavereset_f)
        harts[sel].havereset = 1'b0;
      if (ackunavail_f && harts[sel].available)
        harts[sel].unavail_sticky = 1'b0;

      // Halt request is a persistent per-hart bit; writing 0 clears it
      // (#3.5, #3.14.2).
      harts[sel].halt_request = haltreq_f;
      if (haltreq_f && !harts[sel].nonexistent &&
          !(harts[sel].unavail_sticky || !harts[sel].available)) begin
        if (harts[sel].running && !harts[sel].halted) begin
          harts[sel].halted  = 1'b1;
          harts[sel].running = 1'b0;
        end
      end

      // #3.14.2 resumereq: "resumereq is ignored if haltreq is set."
      if (resumereq_f && !haltreq_f)
        apply_resumereq(sel);
    end

    settle_reset_state();
  endfunction

  // resumereq (spec #3.5): "the resume ack bit is cleared and each selected,
  // halted hart is sent a resume request ... At the end of this process the
  // resume ack bit is set." Asymmetry: resume_ack clears for the selected
  // hart regardless, but only sets again if it was actually halted.
  local function void apply_resumereq(int sel);
    if (!hart_exists(sel) || harts[sel].nonexistent ||
        harts[sel].unavail_sticky || !harts[sel].available) return;
    harts[sel].resume_ack = 1'b0;
    if (harts[sel].halted) begin
      harts[sel].halted     = 1'b0;
      harts[sel].running    = 1'b1;
      harts[sel].resume_ack = 1'b1;
    end
  endfunction

  // ndmreset resets every hart and the rest of the platform (#3.2).
  local function void apply_ndmreset(bit asserted);
    if (asserted && !ndmreset) begin
      ndmreset = 1'b1;
      foreach (harts[i]) begin
        harts[i].halted  = 1'b0;
        harts[i].running = 1'b0; // in reset: neither halted nor running
      end
    end else if (!asserted && ndmreset) begin
      ndmreset = 1'b0;
      foreach (harts[i]) release_from_reset(i);
    end
  endfunction

  // hartreset resets only the currently selected hart (#3.14.2).
  local function void apply_hartreset(bit asserted);
    int sel = selected_index();
    if (!hart_exists(sel)) return;
    if (asserted && !hartreset_level) begin
      hartreset_level        = 1'b1;
      harts[sel].hart_reset  = 1'b1;
      harts[sel].halted      = 1'b0;
      harts[sel].running     = 1'b0;
    end else if (!asserted && hartreset_level) begin
      hartreset_level       = 1'b0;
      harts[sel].hart_reset = 1'b0;
      release_from_reset(sel);
    end
  endfunction

  // A hart coming out of reset (#3.2: "havereset becomes set"; #3.5: a hart
  // whose reset_haltreq or halt_request is set halts immediately instead of
  // running, "regardless of the reset's cause").
  local function void release_from_reset(int idx);
    if (!hart_exists(idx) || harts[idx].nonexistent) return;
    harts[idx].havereset = 1'b1;
    if (harts[idx].reset_haltreq || harts[idx].halt_request) begin
      harts[idx].halted  = 1'b1;
      harts[idx].running = 1'b0;
    end else begin
      harts[idx].halted  = 1'b0;
      harts[idx].running = 1'b1;
    end
  endfunction

  // Harts held in reset report neither halted nor running.
  local function void settle_reset_state();
    foreach (harts[i]) begin
      if (ndmreset || (harts[i].hart_reset && !harts[i].nonexistent)) begin
        harts[i].halted  = 1'b0;
        harts[i].running = 1'b0;
      end
    end
  endfunction

  // ── Abstract command (spec #3.7.1.1; bit layout from riscv_dm.py
  // read_gpr()/write_gpr()/execute_progbuf(): cmd[18]=postexec,
  // cmd[17]=transfer, cmd[16]=write, cmd[15:0]=regno)
  local function void write_command(bit [31:0] value);
    bit        postexec = value[18];
    bit        transfer = value[17];
    bit        wr       = value[16];
    bit [15:0] regno    = value[15:0];

    if (transfer) begin
      if (wr) begin
        // GPR/CSR WRITE: commit the staged data0 value into the shadow regfile.
        shadow_regs[regno] = staged_data0;
      end else begin
        // GPR/CSR READ: arm the expectation for the DATA0 read that follows.
        // Spec #3.7.1.1: transfer happens before postexec, so this stays
        // correct for the read that immediately follows even when postexec
        // is also set on this same command.
        if (regno == GPR_X0_REGNO) begin
          // x0 is hardwired to 0 by the base ISA -- always safe to assert,
          // independent of anything this traffic has written.
          data0_pending_valid = 1'b1;
          data0_pending_value = 32'h0;
        end else if (shadow_regs.exists(regno)) begin
          data0_pending_valid = 1'b1;
          data0_pending_value = shadow_regs[regno];
        end else begin
          // Never written by this traffic -- no known-good value to check.
          data0_pending_valid = 1'b0;
        end
      end
    end

    if (postexec) begin
      // Program Buffer content is arbitrary code (#3.7.1.1); it may modify
      // any GPR/CSR architecturally in ways this self-consistency shadow
      // cannot simulate (would need a full ISA model -- out of scope, see
      // file header). Drop every previously-shadowed value so a later read
      // without an intervening write reports has_model()==0 rather than
      // asserting a now-stale pre-execution value (#110).
      shadow_regs.delete();
    end
  endfunction

  // ── System Bus Access (spec #3.10; bit layout from riscv_dm.py
  // read_mem32()/write_mem32(): sbcs[20]=sbreadonaddr)
  local function void write_sbcs(bit [31:0] value);
    sbcs_read_on_addr_armed = value[20];
  endfunction

  local function void write_sbaddress0(bit [31:0] value);
    sbaddress0_q = value;
    // #3.10: writing sbaddress0 while sbreadonaddr=1 triggers a read.
    if (sbcs_read_on_addr_armed) begin
      if (shadow_mem.exists(value)) begin
        sbdata0_pending_valid = 1'b1;
        sbdata0_pending_value = shadow_mem[value];
      end else begin
        sbdata0_pending_valid = 1'b0;
      end
    end
  endfunction

  local function void write_sbdata0(bit [31:0] value);
    shadow_mem[sbaddress0_q] = value;
  endfunction

  // ── Read prediction ────────────────────────────────────────────────────────

  // Whether this model has a checkable expectation for `addr` right now.
  // Callers (dm_checker.sv) MUST check this before calling predict() — an
  // unmodeled/not-yet-armed address returning 0 from predict() would look like
  // a real (and wrong) prediction otherwise.
  function bit has_model(bit [6:0] addr);
    case (addr)
      dm_defines_pkg::DM_ADDR_DMCONTROL: return 1'b1;
      dm_defines_pkg::DM_ADDR_DMSTATUS:  return 1'b1;
      dm_defines_pkg::DM_ADDR_DATA0:     return data0_pending_valid;
      dm_defines_pkg::DM_ADDR_SBDATA0:   return sbdata0_pending_valid;
      default:                           return 1'b0;
    endcase
  endfunction

  function bit [31:0] predict(bit [6:0] addr);
    case (addr)
      dm_defines_pkg::DM_ADDR_DMCONTROL: return expect_dmcontrol();
      dm_defines_pkg::DM_ADDR_DMSTATUS:  return expect_dmstatus();
      dm_defines_pkg::DM_ADDR_DATA0:     return data0_pending_value;
      dm_defines_pkg::DM_ADDR_SBDATA0:   return sbdata0_pending_value;
      default:                           return 32'h0; // caller must check has_model()
    endcase
  endfunction

  // dmstatus read-back (spec #3.14.1). Field positions match both
  // riscv_dm.py's accessor functions and model/registers.py's DMSTATUS table.
  local function bit [31:0] expect_dmstatus();
    int  sel = selected_index();
    bit  halted, running, havereset, resumeack, nonexist, unavail;
    bit [31:0] word;

    if (hart_exists(sel)) begin
      halted    = harts[sel].halted;
      running   = harts[sel].running;
      havereset = harts[sel].havereset;
      resumeack = harts[sel].resume_ack;
      nonexist  = harts[sel].nonexistent;
      unavail   = harts[sel].unavail_sticky || !harts[sel].available;
    end else begin
      // Selected index outside the modeled hart array: report nonexistent,
      // matching predictor.py's is_nonexistent() for hartsel >= num_harts.
      nonexist = 1'b1;
    end

    word = '0;
    word[24]   = ndmreset;              // ndmresetpending
    word[23]   = 1'b0;                  // stickyunavail (predictor.py always 0)
    word[22]   = impebreak;
    word[19]   = havereset;             // allhavereset (single selected hart: all==any)
    word[18]   = havereset;             // anyhavereset
    word[17]   = resumeack;             // allresumeack
    word[16]   = resumeack;             // anyresumeack
    word[15]   = nonexist;              // allnonexistent
    word[14]   = nonexist;              // anynonexistent
    word[13]   = unavail;               // allunavail
    word[12]   = unavail;               // anyunavail
    word[11]   = running;               // allrunning
    word[10]   = running;               // anyrunning
    word[9]    = halted;                // allhalted
    word[8]    = halted;                // anyhalted
    word[7]    = authenticated;
    word[6]    = 1'b0;                  // authbusy (predictor.py always 0)
    word[5]    = hasresethaltreq;
    word[4]    = 1'b0;                  // confstrptrvalid (predictor.py always 0)
    word[3:0]  = dmactive ? version : 4'h0;
    return word;
  endfunction

  // dmcontrol read-back: only R/W and WARL fields read back; every W1/WARZ
  // field reads 0 by definition (spec's own access-type convention), same as
  // predictor.py's _expect_dmcontrol().
  local function bit [31:0] expect_dmcontrol();
    bit [31:0] word = '0;
    word[0]     = dmactive;
    word[1]     = ndmreset;
    word[26]    = hasel;
    word[29]    = hartreset_level && supports_hartreset;
    word[15:6]  = hartsel[19:10]; // hartselhi
    word[25:16] = hartsel[9:0];   // hartsello
    return word;
  endfunction

endclass : dm_ref_model
