// ══════════════════════════════════════════════════════════════════════════════
// dm_checker.sv — Model-backed register-value checker.
//
// Plumbing: one uvm_analysis_export + TLM analysis FIFO for the DMI monitor
// stream, one forever task blocking on fifo.get() -- the blocking get() is the
// "event" that wakes the task per transaction. This is the standard UVM TLM
// idiom; the pattern (one export/FIFO/task per monitored interface) was
// confirmed against a reviewed external reference checker, but no code from
// it is reused here -- see VERIFICATION_STRATEGY.md
// "Checker implementation (SV register model)".
//
// Semantics: NO sequence or stimulus step calls a compare method. Every
// observed WRITE updates `dm_ref_model`; every observed READ is checked
// against it automatically, here, as a property of the monitored transaction
// stream. On a mismatch, this reports (`MODEL_MISMATCH`, distinct from
// debug_scoreboard's protocol-status errors) and does NOT attempt to resolve
// it -- whether the bug is in the RTL, the model, or is a declared/accepted
// difference is a decision for whoever reads the report, not this checker.
//
// DMI is pipelined one transaction deep (spec #6.1.5): a shift's response
// fields belong to the PREVIOUS request, never its own. `pending_*` below is
// that one-deep correlation register.
// ══════════════════════════════════════════════════════════════════════════════
class dm_checker extends uvm_component;
  `uvm_component_utils(dm_checker)

  uvm_analysis_export #(jtag_txn_c)          dmi_export;
  protected uvm_tlm_analysis_fifo #(jtag_txn_c) dmi_fifo;

  dm_ref_model model;

  // One-deep pending-request register (see file header).
  local bit        pending_valid;
  local bit [6:0]  pending_addr;
  local bit [1:0]  pending_op;

  int unsigned total_checked;
  int unsigned total_mismatches;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    dmi_export = new("dmi_export", this);
    dmi_fifo   = new("dmi_fifo", this);
    // Defaults: 1 hart, dmstatus.version=0.13 -- matches both current DUTs
    // (dm_defines_pkg.sv). Override via set_model() before run_phase for a
    // v1.0 target or multi-hart configuration.
    model = new();
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    dmi_export.connect(dmi_fifo.analysis_export);
  endfunction

  // Swap in a differently-configured model (e.g. version=3 for the v1.0
  // fork, or num_harts>1) before run_phase starts. Kept separate from
  // build_phase's default so a test can override without needing to touch
  // this component's own build_phase.
  function void set_model(dm_ref_model m);
    model = m;
  endfunction

  task run_phase(uvm_phase phase);
    jtag_txn_c txn;
    forever begin
      dmi_fifo.get(txn);
      handle_txn(txn);
    end
  endtask

  local task handle_txn(jtag_txn_c txn);
    // ── Step 1: the response half of THIS shift belongs to the PREVIOUS
    // request (#6.1.5) -- check it before touching `pending_*` again. A
    // BUSY status means the previous request is still outstanding; leave it
    // pending and try again next shift, exactly as jtag_dmi_read_seq.sv does
    // from the driving side.
    if (pending_valid && txn.dmi_status != dm_defines_pkg::DMI_STAT_BUSY) begin
      if (pending_op == dm_defines_pkg::DMI_READ) begin
        check_read_response(pending_addr, txn.dmi_rdata, txn.dmi_status);
      end
      pending_valid = 1'b0;
    end

    // ── Step 2: process THIS shift's own request.
    case (txn.dmi_op)
      dm_defines_pkg::DMI_WRITE: begin
        // Committed at issue time, not deferred to a confirmed-success
        // response: jtag_dmi_write_seq.sv itself never checks dmi_status or
        // retries on busy, so pydebug's own stimulus already assumes a
        // write takes effect unconditionally -- the model has to assume the
        // same thing to stay meaningfully comparable to what's actually
        // being driven, not a stricter protocol than the real debugger
        // implements.
        model.on_write(txn.dmi_addr, txn.dmi_wdata);
        pending_valid = 1'b1;
        pending_addr  = txn.dmi_addr;
        pending_op    = dm_defines_pkg::DMI_WRITE;
      end
      dm_defines_pkg::DMI_READ: begin
        pending_valid = 1'b1;
        pending_addr  = txn.dmi_addr;
        pending_op    = dm_defines_pkg::DMI_READ;
      end
      dm_defines_pkg::DMI_NOP: begin
        // A NOP retrieves an already-in-flight result; it does not start a
        // new request, so `pending_*` is left exactly as it was.
      end
      default: ; // reserved op (2'b11 as an *op*, distinct from BUSY as a
                 // *status* -- dm_defines_pkg's dmi_op_e has no reserved-op
                 // encoding today; kept for forward compatibility)
    endcase
  endtask

  local function void check_read_response(bit [6:0] addr, bit [31:0] actual, bit [1:0] status);
    // A real DMI-level failure is debug_scoreboard's concern (protocol
    // status), not a register-value question -- skip rather than double-report.
    if (status == dm_defines_pkg::DMI_STAT_FAILED) return;

    total_checked++;
    if (!model.has_model(addr)) return; // nothing checkable for this address

    if (actual !== model.predict(addr)) begin
      total_mismatches++;
      `uvm_error("MODEL_MISMATCH",
        $sformatf(
          "DMI addr=0x%02h: RTL returned 0x%08h, dm_ref_model expected 0x%08h -- reported only, not auto-resolved (author decides RTL vs model vs accepted difference; see VERIFICATION_STRATEGY.md)",
          addr, actual, model.predict(addr)))
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("MODEL_CHECK",
      $sformatf("Checked=%0d Mismatches=%0d", total_checked, total_mismatches), UVM_NONE)
  endfunction

endclass : dm_checker
