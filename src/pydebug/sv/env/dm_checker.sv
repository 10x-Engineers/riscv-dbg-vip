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

  // Second monitored interface: the DM's System Bus Access master. Same
  // export/FIFO/task shape as the DMI stream above.
  uvm_analysis_export #(dbg_axi_pkg::dbg_axi_txn_t)          axi_export;
  protected uvm_tlm_analysis_fifo #(dbg_axi_pkg::dbg_axi_txn_t) axi_fifo;

  // Third monitored interface: the DMI bus itself, between the DTM and the DM.
  // Tapping it is what lets compare_dtm_dmi() verify the DTM's serial-to-
  // parallel translation rather than trusting it.
  uvm_analysis_export #(dbg_dmi_pkg::dbg_dmi_txn)          dmi_bus_export;
  protected uvm_tlm_analysis_fifo #(dbg_dmi_pkg::dbg_dmi_txn) dmi_bus_fifo;

  dm_ref_model model;

  // Streams recorded for compare_dtm_dmi(). Bounded so a long run cannot grow
  // them without limit: the correlation only ever looks at recent traffic.
  localparam int unsigned CORR_DEPTH = 64;

  typedef struct {
    bit [63:0] addr;
    bit [63:0] data;
    bit        is_write;
    time       t;
  } sba_evt_t;

  protected sba_evt_t dmi_sba_q[$];   // what the DTM asked the DM to do
  protected sba_evt_t axi_sba_q[$];   // what the DM actually put on the bus

  int unsigned sba_matched;
  int unsigned sba_unmatched;

  // DTM <-> DMI bridge correlation. jtag_q holds requests seen shifted in over
  // JTAG; bus_q holds what actually appeared on the DMI bus.
  protected dbg_dmi_pkg::dbg_dmi_txn bus_q[$];
  typedef struct {
    bit [6:0]  addr;
    bit [1:0]  op;
    bit [31:0] data;
    time       t;
  } jtag_evt_t;
  protected jtag_evt_t jtag_q[$];

  int unsigned dtm_matched;
  int unsigned dtm_mismatched;

  // Backdoor view of the DM's registers. Optional: an SoC that does not expose
  // it simply runs without the model-vs-RTL comparison.
  virtual dbg_dm_backdoor_if backdoor_vif;
  bit                     backdoor_en;
  event                   dmi_settled;

  int unsigned bd_checked;
  int unsigned bd_mismatched;

  // Latched sbaddress0, so a later sbdata0 access can be attributed to it.
  local bit [31:0] sbaddress0;

  // One-deep pending-request register (see file header).
  local bit        pending_valid;
  local bit [6:0]  pending_addr;
  local bit [1:0]  pending_op;

  int unsigned total_checked;
  int unsigned total_mismatches;

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Build the declared configuration from dut_configs/<dut>.json. Every field
  // is required: a Preset the model has to guess is a Preset that can turn a
  // missing config line into a false failure.
  protected function dm_defines_pkg::dm_cfg_t read_cfg(dut_config_reader r, int unsigned nharts);
    dm_defines_pkg::dm_cfg_t c;
    c.num_harts          = nharts;
    c.version            = r.get_version();
    c.authenticated      = r.get_bool("authenticated");
    c.impebreak          = r.get_bool("impebreak");
    c.hasresethaltreq    = r.get_bool("hasresethaltreq");
    c.stickyunavail      = r.get_bool("stickyunavail");
    c.havereset_poweron  = r.get_bool("havereset_poweron");
    c.supports_hartreset = r.get_bool("supports_hartreset");
    c.supports_hasel     = r.get_bool("supports_hasel");
    c.resumeack_reset    = r.get_bool("resumeack_reset");
    c.sba_enable            = r.get_bool("sba_enable");
    c.abstractauto_enable   = r.get_bool("abstractauto_enable");
    c.hartarray_enable      = r.get_bool("hartarray_enable");
    c.authentication_enable = r.get_bool("authentication_enable");
    c.haltgroups_enable     = r.get_bool("haltgroups_enable");
    c.progbufsize        = r.get_int("progbufsize");
    c.datacount          = r.get_int("datacount");
    c.relaxedpriv_reset  = r.get_bool("relaxedpriv_reset");
    c.nscratch           = r.get_int("nscratch");
    c.dataaccess         = r.get_bool("dataaccess");
    c.datasize           = r.get_int("datasize");
    c.dataaddr           = r.get_int("dataaddr");
    c.sbversion          = r.get_int("sbversion");
    c.sbasize            = r.get_int("sbasize");
    c.sbaccess128        = r.get_bool("sbaccess128");
    c.sbaccess64         = r.get_bool("sbaccess64");
    c.sbaccess32         = r.get_bool("sbaccess32");
    c.sbaccess16         = r.get_bool("sbaccess16");
    c.sbaccess8          = r.get_bool("sbaccess8");
    c.nextdm             = r.get_int("nextdm");
    return c;
  endfunction

  function void build_phase(uvm_phase phase);
    string dut_config_path;
    dut_config_reader cfg;
    super.build_phase(phase);
    dmi_export = new("dmi_export", this);
    dmi_fifo   = new("dmi_fifo", this);
    axi_export = new("axi_export", this);
    axi_fifo   = new("axi_fifo", this);
    dmi_bus_export = new("dmi_bus_export", this);
    dmi_bus_fifo   = new("dmi_bus_fifo", this);
    backdoor_en = uvm_config_db #(virtual dbg_dm_backdoor_if)::get(
                   this, "", "dm_backdoor_vif", backdoor_vif);
    if (!backdoor_en)
      `uvm_info("BACKDOOR", "no dm_backdoor_vif -- model-vs-RTL comparison disabled", UVM_HIGH)
    // dut_config_path points at dut_configs/<name>.json (#117) -- the single
    // declared source of every implementation-defined/Preset field this
    // model needs (version, stickyunavail, hasresethaltreq, ...), shared
    // with the Python side's model/dut_config.py. Set via uvm_config_db from
    // the target's tb_top; Ibex's tb_top sets nothing and gets the 0.13
    // default (matches its untouched vendored riscv-dbg). Override via
    // set_model() before run_phase for any further per-target divergence
    // (e.g. multi-hart configuration) beyond what the config file covers.
    if (!uvm_config_db#(string)::get(this, "", "dut_config_path", dut_config_path))
      dut_config_path = "../src/pydebug/dut_configs/ibex.json";
    cfg   = new(dut_config_path);
    model = new();
    // One call carrying the whole declared configuration, rather than a
    // positional list that stopped being reviewable around its tenth entry.
    model.set_config(read_cfg(cfg, 1));
  endfunction

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    dmi_export.connect(dmi_fifo.analysis_export);
    axi_export.connect(axi_fifo.analysis_export);
    dmi_bus_export.connect(dmi_bus_fifo.analysis_export);
  endfunction

  // Swap in a differently-configured model (e.g. version=3 for the v1.0
  // fork, or num_harts>1) before run_phase starts. Kept separate from
  // build_phase's default so a test can override without needing to touch
  // this component's own build_phase.
  function void set_model(dm_ref_model m);
    model = m;
  endfunction

  // One task per monitored interface, plus the correlator. Kept separate
  // rather than folded into one loop because the two FIFOs fill independently
  // -- a blocking get() on either must not stall the other.
  task run_phase(uvm_phase phase);
    fork
      get_dtm_txns();
      get_axi_txns();
      get_dmi_bus_txns();
      compare_dtm_dmi();
      compare_dmi_sba();
      compare_model_vs_rtl();
    join
  endtask

  // ── DTM side: DMI transactions seen on JTAG ─────────────────────────────
  task get_dtm_txns();
    jtag_txn_c txn;
    forever begin
      dmi_fifo.get(txn);
      `uvm_info("JTAG_DTM", $sformatf(
          "DTM  (JTAG shift) addr=0x%02h op=%0d wdata=0x%08h  (prev: status=%0d rdata=0x%08h)",
          txn.dmi_addr, txn.dmi_op, txn.dmi_wdata, txn.dmi_status, txn.dmi_rdata),
          UVM_HIGH)
      record_dmi_sba(txn);
      // Only real accesses cross the DTM; a nop shift produces no bus request.
      if (txn.dmi_op inside {2'd1, 2'd2}) begin
        jtag_q.push_back('{addr: txn.dmi_addr, op: txn.dmi_op,
                           data: txn.dmi_wdata, t: $time});
        if (jtag_q.size() > CORR_DEPTH) void'(jtag_q.pop_front());
      end
      handle_txn(txn);
    end
  endtask

  // ── DM side: what the System Bus Access master actually drove ───────────
  task get_axi_txns();
    dbg_axi_pkg::dbg_axi_txn_t txn;
    forever begin
      axi_fifo.get(txn);
      `uvm_info("AXI_TXN", {"AXI  ", txn.convert2string()}, UVM_HIGH)
      axi_sba_q.push_back('{addr:     txn.addr,
                            data:     (txn.data.size() > 0) ? txn.data[0] : 64'h0,
                            is_write: (txn.dir == dbg_axi_pkg::dbg_axi_txn_t::AXI_WRITE),
                            t:        $time});
      if (axi_sba_q.size() > CORR_DEPTH) void'(axi_sba_q.pop_front());
    end
  endtask

  // A DMI access to the SBA registers is a request for a bus transaction.
  // sbaddress0 is latched; sbcs.sbreadonaddr makes the address write itself
  // trigger a read, and an sbdata0 write is a bus write.
  protected function void record_dmi_sba(jtag_txn_c txn);
    if (txn.dmi_op != 2) return;                       // writes only
    case (txn.dmi_addr)
      7'h39: sbaddress0 = txn.dmi_wdata;               // sbaddress0
      7'h3C: begin                                     // sbdata0 -> bus write
        dmi_sba_q.push_back('{addr: sbaddress0, data: txn.dmi_wdata,
                              is_write: 1'b1, t: $time});
        if (dmi_sba_q.size() > CORR_DEPTH) void'(dmi_sba_q.pop_front());
      end
      default: ;
    endcase
  endfunction

  // ── DMI bus side ────────────────────────────────────────────────────────
  task get_dmi_bus_txns();
    dbg_dmi_pkg::dbg_dmi_txn txn;
    forever begin
      dmi_bus_fifo.get(txn);
      `uvm_info("DMI_BUS", {"DMI  (bus) ", txn.convert2string()}, UVM_HIGH)
      bus_q.push_back(txn);
      if (bus_q.size() > CORR_DEPTH) void'(bus_q.pop_front());
      -> dmi_settled;   // wakes the backdoor comparison
    end
  endtask

  // ── DTM correlator ──────────────────────────────────────────────────────
  // Verifies the Debug Transport Module: every DMI access shifted in over JTAG
  // must appear on the DMI bus with the same addr/op/data. A mismatch here
  // means the DTM's serial-to-parallel translation is wrong, which no
  // DMI-only check could catch -- both sides would agree with each other and
  // be wrong together.
  task compare_dtm_dmi();
    forever begin
      #1us;
      while (jtag_q.size() > 0 && bus_q.size() > 0) begin
        jtag_evt_t want = jtag_q[0];
        int        hit  = -1;
        foreach (bus_q[i]) begin
          if (bus_q[i].t_req >= want.t && bus_q[i].addr == want.addr &&
              bus_q[i].op == want.op) begin
            hit = i;
            break;
          end
        end
        if (hit < 0) break;   // not on the bus yet

        if (want.op == 2'd2 && bus_q[hit].wdata !== want.data) begin
          `uvm_error("DTM_CHECK", $sformatf(
              "DTM corrupted a write: JTAG shifted addr=0x%02h data=0x%08h, DMI bus carried 0x%08h",
              want.addr, want.data, bus_q[hit].wdata))
          dtm_mismatched++;
        end else begin
          `uvm_info("DTM_MATCH", $sformatf(
              "DTM  ok: %s addr=0x%02h matched on the DMI bus",
              (want.op == 2'd2) ? "write" : "read", want.addr), UVM_HIGH)
          dtm_matched++;
        end
        bus_q.delete(hit);
        void'(jtag_q.pop_front());
      end
    end
  endtask

  // ── SBA correlator ──────────────────────────────────────────────────────
  // Verifies the DM's bus bridge: a System Bus Access requested over DMI must
  // appear on the SBA master with the same address. Runs on a poll rather than
  // per-transaction because the two sides are inherently skewed -- the DM
  // issues the bus cycle some cycles after the DMI write that asked for it.
  task compare_dmi_sba();
    forever begin
      #1us;
      while (dmi_sba_q.size() > 0) begin
        sba_evt_t want = dmi_sba_q[0];
        int       hit  = -1;
        foreach (axi_sba_q[i]) begin
          if (axi_sba_q[i].addr == want.addr &&
              axi_sba_q[i].is_write == want.is_write &&
              axi_sba_q[i].t >= want.t) begin
            hit = i;
            break;
          end
        end
        if (hit < 0) break;   // not on the bus yet; look again next poll
        `uvm_info("SBA_MATCH", $sformatf(
            "SBA  matched DMI-requested %s at 0x%0h with bus transaction at %0t",
            want.is_write ? "write" : "read", want.addr, axi_sba_q[hit].t), UVM_MEDIUM)
        sba_matched++;
        axi_sba_q.delete(hit);
        void'(dmi_sba_q.pop_front());
      end
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

    // Sync the hart-driven dmstatus fields (halted/running/resume_ack) to
    // what the DUT just reported BEFORE comparing -- they reach the DM
    // through real, variable-latency hart-side hardware this model cannot
    // predict synchronously (see dm_ref_model.sv's sync_observed_hart_
    // signals / hart_signal_bit.sv). Every other dmstatus field is
    // unaffected and still compared normally below.
    if (addr == dm_defines_pkg::DM_ADDR_DMSTATUS)
      model.sync_observed_hart_signals(actual);

    // Compare only the bits the model claims to predict. predict_mask()
    // excludes genuinely dynamic state -- abstractcs.busy is set while an
    // abstract command is in flight, and an untimed model cannot know when
    // that is. Masking here rather than in the caller keeps the front door and
    // the backdoor honest about the same set of bits.
    if ((actual & model.predict_mask(addr)) !== (model.predict(addr) & model.predict_mask(addr))) begin
      total_mismatches++;
      `uvm_error("MODEL_MISMATCH",
        $sformatf(
          "DMI addr=0x%02h: RTL returned 0x%08h, dm_ref_model expected 0x%08h (compared over 0x%08h) -- reported only, not auto-resolved (author decides RTL vs model vs accepted difference; see VERIFICATION_STRATEGY.md)",
          addr, actual, model.predict(addr), model.predict_mask(addr)))
    end
  endfunction

  // ── Model vs RTL, by backdoor ───────────────────────────────────────────
  // Expected from dm_ref_model.predict(), actual from the DM's own state.
  // Runs after each DMI access settles; mid-access the two may legitimately
  // disagree.
  //
  // Scope is limited by the model, deliberately, and the limits are worth
  // stating because they bound what this check is worth:
  //
  //   * has_model() gates the address. predict() returns 0 for anything it
  //     does not implement -- today abstractcs, sbcs, command, abstractauto --
  //     so comparing those would report the model's own silence as a DUT bug.
  //   * Within an address, only the bits the model computes are compared.
  //     expect_dmcontrol() models dmactive/ndmreset/hasel/hartreset/hartsel
  //     and not haltreq or resumereq, so an unmasked compare would fail on
  //     every halt request.
  //   * dmstatus is excluded entirely. Its halted/running/resumeack bits reach
  //     the DM through hart-side hardware this untimed model cannot predict --
  //     the front-door path calls sync_observed_hart_signals() first for
  //     exactly that reason. Syncing from the RTL and then comparing against
  //     the RTL would be circular, so the front door keeps that check.
  //
  // Widening this is a matter of teaching dm_ref_model more registers, not of
  // adding backdoor signals: the backdoor already carries more than the model can
  // predict.
  localparam bit [31:0] DMCONTROL_MODELLED = 32'h27FF_FFC3;

  task compare_model_vs_rtl();
    if (!backdoor_en) return;
    forever begin
      @(dmi_settled);
      // Let the write land: dm_csrs commits on the clock edge after the DMI
      // request is accepted, so an immediate sample reads the old value.
      repeat (3) @(posedge backdoor_vif.clk);

      bd_try("dmcontrol",    dm_defines_pkg::DM_ADDR_DMCONTROL,
             backdoor_vif.dmcontrol,    DMCONTROL_MODELLED);
      bd_try("abstractcs",   dm_defines_pkg::DM_ADDR_ABSTRACTCS,
             backdoor_vif.abstractcs,   32'hFFFF_FFFF);
      bd_try("abstractauto", dm_defines_pkg::DM_ADDR_ABSTRACTAUTO,
             backdoor_vif.abstractauto, 32'hFFFF_FFFF);
      bd_try("command",      dm_defines_pkg::DM_ADDR_COMMAND,
             backdoor_vif.command,      32'hFFFF_FFFF);
      bd_try("sbcs",         dm_defines_pkg::DM_ADDR_SBCS,
             backdoor_vif.sbcs,         32'hFFFF_FFFF);
    end
  endtask

  // Compare only if the model claims the address, and only over the bits it
  // claims to predict -- predict_mask() excludes the dynamic ones.
  protected function void bd_try(string name, bit [6:0] addr,
                                 bit [31:0] actual, bit [31:0] extra_mask);
    if (!model.has_model(addr)) return;
    bd_check(name, addr, actual, model.predict_mask(addr) & extra_mask);
  endfunction

  protected function void bd_check(string name, bit [6:0] addr,
                                   bit [31:0] actual, bit [31:0] mask);
    bit [31:0] expected = model.predict(addr) & mask;
    bit [31:0] got      = actual & mask;
    bd_checked++;
    if (expected !== got) begin
      bd_mismatched++;
      `uvm_error("BACKDOOR", $sformatf(
          "%s mismatch: model expected 0x%08h, RTL holds 0x%08h (differing modelled bits 0x%08h)%s",
          name, expected, got, expected ^ got,
          dm_defines_pkg::dm_field_table(addr, actual)))
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("MODEL_CHECK",
      $sformatf("Checked=%0d Mismatches=%0d", total_checked, total_mismatches), UVM_NONE)
    // Reported unconditionally, including the zero case: "no SBA traffic was
    // correlated" is itself worth seeing, since silence would otherwise look
    // the same as a correlator that never ran.
    `uvm_info("DTM_CHECK",
      $sformatf("JTAG<->DMI bus: matched=%0d mismatched=%0d unmatched=%0d",
                dtm_matched, dtm_mismatched, jtag_q.size()), UVM_NONE)
    if (backdoor_en)
      `uvm_info("BACKDOOR",
        $sformatf("model vs RTL: checked=%0d mismatched=%0d", bd_checked, bd_mismatched),
        UVM_NONE)
    `uvm_info("SBA_CHECK",
      $sformatf("DMI<->SBA master: matched=%0d unmatched=%0d",
                sba_matched, dmi_sba_q.size()), UVM_NONE)
  endfunction

endclass : dm_checker
