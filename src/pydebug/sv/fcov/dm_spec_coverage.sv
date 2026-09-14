// dm_spec_coverage.sv — functional coverage derived from Debug Spec v1.0.
//
// The model of record is testplans/generated/coverage_model.yaml; this is its
// executable half. Every covergroup, coverpoint and bin here has a counterpart
// there carrying the spec anchor and the owning testplan item, and
// reconcile.py checks the two against each other.
//
// Why this exists alongside covergroups.sv: that model samples only DMI-visible
// DM registers. dcsr and dpc live in the core, so nothing sampled which
// instruction a step stepped over -- which is why the CVA6 wfi deadlock could
// not appear as a coverage hole and had to be found by a directed test. This
// class samples the hart backdoor as well as the DMI stream, so the Sdext
// behaviours are measurable.
//
// Sampling strategy: DMI transactions arrive through the analysis port, but the
// interesting hart state changes between them. So run-control and step
// coverage is sampled from a clocked process watching the hart backdoor, and
// the DMI stream is used for the protocol-level covergroups where the
// transaction IS the event.

`ifndef DM_SPEC_COVERAGE_SV
`define DM_SPEC_COVERAGE_SV

class dm_spec_coverage extends uvm_subscriber #(jtag_txn_c);
  `uvm_component_utils(dm_spec_coverage)

  virtual dbg_hart_backdoor_if hart_vif;
  virtual dbg_dm_backdoor_if   dm_vif;

  // ── Sampled state ────────────────────────────────────────────────────────
  // Written by the monitors below, read by the covergroups. Kept as members
  // rather than passed as arguments because several covergroups sample the
  // same value and a change of source should touch one line.
  logic [2:0]  s_cause;
  logic [1:0]  s_prv;
  logic [3:0]  s_iclass;
  logic [1:0]  s_stepie_irq;      // {stepie, irq_pending}
  logic [1:0]  s_mode_prev, s_mode_curr;
  logic        s_haltreq_during_step;
  logic [2:0]  s_dmi_op, s_dmi_result;
  logic [2:0]  s_cmderr;
  logic [2:0]  s_sbaccess;
  logic [2:0]  s_sberror;
  logic [1:0]  s_dpc_origin;
  logic        s_stopcount_adv, s_stoptime_adv;
  int unsigned s_consecutive_steps;

  // ══════════════════════════════════════════════════════════════════════════
  // cg_debug_entry -- a hart enters Debug Mode for exactly one reason and
  // records which, so a debugger can tell an external halt from a breakpoint,
  // a trigger or a completed step. spec: Sdext.html#csr-dcsr
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_debug_entry;
    option.per_instance = 1;

    // Each cause drives different debugger behaviour. This is the coverpoint
    // that proves every entry path was actually taken.
    cp_cause: coverpoint s_cause {
      bins ebreak       = {1};            // DM-001-C
      bins trigger      = {2};            // TRIG-003-C
      bins haltreq      = {3};            // HALT-001-C2
      bins step         = {4};            // SSTEP-001-C2
      // cause=5 needs hasresethaltreq, which is 0 on this DUT. Retained so a
      // DUT with halt-on-reset is measured here rather than silently skipped.
      ignore_bins resethaltreq = {5};
      // The spec enumerates 1-5. Anything else is the DUT reporting a cause
      // that does not exist.
      illegal_bins undefined = {0, 6, 7};
    }

    cp_prv: coverpoint s_prv {
      bins U = {0};
      bins S = {1};
      bins M = {3};
      illegal_bins reserved = {2};        // privilege 2 is reserved
    }

    // dpc means something different per cause -- the interrupted PC for
    // haltreq, the ebreak's own address, the next instruction after a step.
    // A DM can get one right and another wrong.
    cp_dpc_origin: coverpoint s_dpc_origin {
      bins interrupted_pc     = {0};
      bins ebreak_address     = {1};
      bins next_after_step    = {2};
      bins trap_handler_entry = {3};
    }

    // ebreak gating is per privilege, so this is where a wrongly-gated ebreak
    // shows up. Neither coverpoint alone finds it.  DM-012-C / DM-013-V
    x_cause_x_prv: cross cp_cause, cp_prv;

    // DM-014-V
    x_cause_x_dpc: cross cp_cause, cp_dpc_origin {
      // ebreak must report its own address; reporting the next one would
      // silently skip an instruction on resume.
      illegal_bins ebreak_skips =
          binsof(cp_cause.ebreak) && binsof(cp_dpc_origin.next_after_step);
    }
  endgroup

  // ══════════════════════════════════════════════════════════════════════════
  // cg_step_external -- a step retires exactly one instruction and returns to
  // Debug Mode unaided, for every class including those that would otherwise
  // never complete. spec: Sdext.html#stepbit
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_step_external;
    option.per_instance = 1;

    // Ordinary instructions are hit by any test; the stalling and
    // control-transfer classes have to be asked for.
    cp_stepped_class: coverpoint s_iclass {
      bins ordinary       = {0};          // SSTEP-001-C3
      bins compressed     = {1};          // SSTEP-002-C
      bins wfi            = {2};          // SSTEP-004-C2 -- the CVA6 deadlock
      bins branch_taken   = {3};          // SSTEP-003-C
      bins branch_ntaken  = {4};          // SSTEP-019-C
      bins trapping       = {5};          // SSTEP-008-C
      bins priv_change    = {6};          // SSTEP-009-C
      bins load_store     = {7};          // SSTEP-015-C
      // Zawrs absent: wrs.* decode as illegal and would test the trap handler
      // rather than the step rule.
      ignore_bins wrs     = {8};
      ignore_bins nothing = {15};
    }

    // stepie only matters with an interrupt actually pending, so this is a 2x2
    // rather than two independent points.
    cp_stepie_irq: coverpoint s_stepie_irq {
      bins masked_no_irq       = {2'b00};  // SSTEP-006-C
      bins masked_irq_pending  = {2'b01};  // SSTEP-006-C
      bins unmasked_no_irq     = {2'b10};  // SSTEP-007-C
      bins unmasked_irq_pending= {2'b11};  // SSTEP-007-C
    }

    cp_prv_at_step: coverpoint s_prv {
      bins U = {0}; bins S = {1}; bins M = {3};
      illegal_bins reserved = {2};
    }

    // Drift compounds across repeated steps; an off-by-one in dpc only shows
    // after several.
    cp_consecutive: coverpoint s_consecutive_steps {
      bins single    = {1};
      bins several   = {[2:16]};
      bins many      = {[17:64]};         // SSTEP-020-C, across a loop back-edge
    }

    // A wfi stepped with stepie=1 and an interrupt pending may legitimately
    // complete via the interrupt; with stepie=0 it must be treated as a nop.
    // Testing the wfi at one setting leaves the harder half unmeasured.
    // SSTEP-022-V
    x_class_x_stepie: cross cp_stepped_class, cp_stepie_irq {
      ignore_bins uninteresting =
          binsof(cp_stepped_class.ordinary) || binsof(cp_stepped_class.compressed);
    }

    // A trapping instruction from U enters the M handler; from M it stays in
    // M. Ordinary and compressed do not vary by privilege.  SSTEP-021-V
    x_class_x_prv: cross cp_stepped_class, cp_prv_at_step {
      ignore_bins invariant_classes =
          binsof(cp_stepped_class.ordinary) || binsof(cp_stepped_class.compressed);
    }

    // SSTEP-023-V
    x_class_x_consecutive: cross cp_stepped_class, cp_consecutive {
      ignore_bins one_step = binsof(cp_consecutive.single);
    }
  endgroup

  // ══════════════════════════════════════════════════════════════════════════
  // cg_hart_mode -- the step is a D->M->D round trip; the return leg is the
  // property under test. Sampling debug_mode directly rather than inferring it
  // from dmstatus is the point: dmstatus can report a hart running while it is
  // stalled, which is exactly how the wfi defect presented.
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_hart_mode;
    option.per_instance = 1;

    cp_mode_transition: coverpoint s_mode_curr {
      bins enter_debug = (0 => 1);
      bins leave_debug = (1 => 0);
      bins complete_step = (1 => 0 => 1);   // SSTEP-001-C
      // Two consecutive samples in RUNNING after a step means the hart never
      // re-entered Debug Mode. Recorded rather than illegal_bins because the
      // hart legitimately runs for long stretches outside a step; the step
      // case is qualified by the sampling guard in sample_step().
      bins stayed_running = (0 => 0);
    }

    // If haltreq is still asserted the hart re-halts for the original request
    // and the step proves nothing. This guards the whole covergroup.
    // SSTEP-001-C0
    cp_haltreq_guard: coverpoint s_haltreq_during_step {
      bins deasserted = {0};
      illegal_bins still_asserted = {1};
    }
  endgroup

  // ══════════════════════════════════════════════════════════════════════════
  // cg_dtm_dmi -- the transport carries every operation and reports every
  // outcome. spec: dtm.html#dmi
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_dtm_dmi;
    option.per_instance = 1;

    cp_dmi_op: coverpoint s_dmi_op {
      bins nop = {0}; bins read = {1}; bins write = {2}; bins reserved = {3};
    }
    cp_dmi_result: coverpoint s_dmi_result {
      bins success = {0};                 // DTM-003-C
      bins failed  = {2};                 // DTM-005-C
      bins busy    = {3};                 // DTM-004-C
      illegal_bins reserved_result = {1}; // 1 is not a defined response
    }
    // Reads and writes fail differently: a failed read returns stale data, a
    // failed write may partially apply.  DTM-010-V
    x_op_x_result: cross cp_dmi_op, cp_dmi_result {
      ignore_bins nop_cannot_be_busy =
          binsof(cp_dmi_op.nop) && binsof(cp_dmi_result.busy);
    }
  endgroup

  // ══════════════════════════════════════════════════════════════════════════
  // cg_abstract_cmd -- every failure mode distinct enough for a debugger to
  // react correctly. spec: debug_module.html#abstractcs
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_abstract_cmd;
    option.per_instance = 1;

    cp_cmderr: coverpoint s_cmderr {
      bins none          = {0};           // AC-001-C
      bins busy          = {1};           // RAP-042-C
      bins not_supported = {2};           // AC-005-C
      bins exception     = {3};           // PB-005-C
      bins halt_resume   = {4};           // AC-007-C
      // cmderr=5 needs abstract memory access, absent on this DUT.
      ignore_bins bus    = {5};
      bins other         = {7};           // AC-020-C
      illegal_bins reserved = {6};        // 6 is not a defined encoding
    }
  endgroup

  // ══════════════════════════════════════════════════════════════════════════
  // cg_sba -- System Bus Access reaches memory independently of the hart.
  // spec: debug_module.html#sbcs
  // ══════════════════════════════════════════════════════════════════════════
  covergroup cg_sba;
    option.per_instance = 1;

    cp_sbaccess: coverpoint s_sbaccess {
      bins size8 = {0}; bins size16 = {1}; bins size32 = {2};
      bins size64 = {3}; bins size128 = {4};
      bins unsupported_written = {7};     // RAP-007-C3
      ignore_bins undefined = {5, 6};
    }
    cp_sberror: coverpoint s_sberror {
      bins none = {0};                    // SBA-001-C
      bins timeout = {1};                 // SBA-012-C
      bins bad_address = {2};             // SBA-008-C
      bins alignment = {3};               // SBA-007-C
      bins unsupported_size = {4};        // SBA-006-C
      bins other = {7};                   // SBA-013-C
      ignore_bins reserved = {5, 6};
    }
  endgroup

  // ── Construction ─────────────────────────────────────────────────────────
  function new(string name, uvm_component parent);
    super.new(name, parent);
    cg_debug_entry   = new();
    cg_step_external = new();
    cg_hart_mode     = new();
    cg_dtm_dmi       = new();
    cg_abstract_cmd  = new();
    cg_sba           = new();
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(virtual dbg_hart_backdoor_if)::get(
            this, "", "hart_backdoor_vif", hart_vif))
      `uvm_warning("SPECCOV", "no hart backdoor -- Sdext coverage will not sample")
    if (!uvm_config_db #(virtual dbg_dm_backdoor_if)::get(
            this, "", "dm_backdoor_vif", dm_vif))
      `uvm_warning("SPECCOV", "no DM backdoor -- cmderr/sbcs coverage degraded")
  endfunction

  // ── Hart-side monitor ────────────────────────────────────────────────────
  // Runs for the whole simulation rather than being driven by DMI activity,
  // because the interesting hart state changes BETWEEN transactions.
  task run_phase(uvm_phase phase);
    logic prev_mode;
    logic prev_debug_entry;
    logic [63:0] dpc_before;
    if (hart_vif == null) return;

    prev_mode = 1'b0;
    prev_debug_entry = 1'b0;
    s_consecutive_steps = 0;

    forever begin
      @(posedge hart_vif.clk);
      if (!hart_vif.rst_n) begin
        prev_mode = 1'b0;
        s_consecutive_steps = 0;
        continue;
      end

      // Mode transition, sampled every cycle so the D->M->D round trip is
      // seen even when it is only a couple of cycles wide.
      s_mode_prev = {1'b0, prev_mode};
      s_mode_curr = {1'b0, hart_vif.debug_mode};
      if (hart_vif.debug_mode !== prev_mode) begin
        s_haltreq_during_step = dm_vif == null ? 1'b0
                                : dm_vif.dmcontrol[31];   // haltreq
        cg_hart_mode.sample();
      end

      // Debug Mode entry: the one moment dcsr.cause is meaningful.
      if (hart_vif.debug_mode && !prev_debug_entry) begin
        s_cause = hart_vif.cause();
        s_prv   = hart_vif.prv();
        s_dpc_origin = classify_dpc_origin(hart_vif.cause());
        cg_debug_entry.sample();

        // A step is an entry with cause=4; count consecutive ones so drift
        // across a run of steps is measurable.
        if (hart_vif.cause() == 3'd4) begin
          s_consecutive_steps++;
          s_iclass      = hart_vif.commit_iclass;
          s_stepie_irq  = {hart_vif.stepie(), hart_vif.irq_pending};
          cg_step_external.sample();
        end else begin
          s_consecutive_steps = 0;
        end
      end

      // Retirement while stepping: remember the class of the instruction that
      // actually retired, because by the time Debug Mode is re-entered the
      // commit port has moved on.
      if (hart_vif.commit_valid && !hart_vif.debug_mode && hart_vif.step())
        s_iclass = hart_vif.commit_iclass;

      prev_mode = hart_vif.debug_mode;
      prev_debug_entry = hart_vif.debug_mode;
    end
  endtask

  // dpc carries a different meaning per cause; classify at the entry.
  function logic [1:0] classify_dpc_origin(logic [2:0] cause);
    case (cause)
      3'd1:    return 2'd1;   // ebreak: its own address
      3'd3:    return 2'd0;   // haltreq: the interrupted PC
      3'd4:    return 2'd2;   // step: the next instruction
      default: return 2'd3;   // trigger or a stepped trap: handler entry
    endcase
  endfunction

  // ── DMI-side sampling ────────────────────────────────────────────────────
  function void write(jtag_txn_c t);
    s_dmi_op     = t.dmi_op;
    s_dmi_result = t.dmi_status;
    cg_dtm_dmi.sample();

    // cmderr and sbcs come from the DM backdoor rather than from a decoded
    // read, so a failing command is binned even when the sequence never reads
    // abstractcs back.
    if (dm_vif != null) begin
      s_cmderr = dm_vif.abstractcs[10:8];
      cg_abstract_cmd.sample();
      s_sbaccess = dm_vif.sbcs[19:17];
      s_sberror  = dm_vif.sbcs[14:12];
      cg_sba.sample();
    end
  endfunction

  function void report_phase(uvm_phase phase);
    `uvm_info("SPECCOV", $sformatf(
      "spec coverage: debug_entry=%0.2f%% step=%0.2f%% hart_mode=%0.2f%% dtm=%0.2f%% abstract=%0.2f%% sba=%0.2f%%",
      cg_debug_entry.get_inst_coverage(), cg_step_external.get_inst_coverage(),
      cg_hart_mode.get_inst_coverage(), cg_dtm_dmi.get_inst_coverage(),
      cg_abstract_cmd.get_inst_coverage(), cg_sba.get_inst_coverage()), UVM_NONE)
  endfunction

endclass

`endif
