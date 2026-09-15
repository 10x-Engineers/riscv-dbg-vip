// ============================================================================
// Functional coverage -- GENERATED from coverage_model.yaml
//
// Do not edit. The model is the source of truth; regenerate with
//   python3 emit_sv.py coverage_model.yaml --out <this file>
//
// Spec version : 1.0
// DUT profile  : cva6-10x-fork
// Scope: The complete external-debug feature set of Debug Specification v1.0:
// DTM and DMI transport, Debug Module control and status, hart selection and
// availability, reset, halt and resume, abstract commands, Program Buffer,
// System Bus Access, Debug Mode and the core debug registers, external
// single-step, native single-step via icount, triggers (Sdtrig), halt and
// resume groups, and authentication. Excluded and NOT counted in any closure
// figure: the E-Trace/Nexus trace specifications, which are separate
// documents.
// ============================================================================

  // ========================================================================
  // The transport carries every operation and reports every outcome, so a
  // debugger can distinguish success from busy from a sticky error and
  // recover without losing Debug Module state.
  // spec: dtm.html#dtmcs
  // spec: dtm.html#dmi
  // observable via: JTAG DR capture of the dmi register
  // ========================================================================
  covergroup cg_dtm_dmi;
    option.per_instance = 1;
    // sampled on: every DMI transaction, on the response

    // The three request encodings exercise different DM paths; the reserved
    // encoding must not wedge the DTM.
    cp_dmi_op: coverpoint t.dmi_op {
      // A no-op request must leave DM state untouched.
      // spec: dtm.html#dmi
      // testplan: DTM-006-S
      bins nop = {0};

      // Basic read path.
      // spec: dtm.html#dmi
      // testplan: DTM-003-S
      bins read = {1};

      // Basic write path.
      // spec: dtm.html#dmi
      // testplan: DTM-003-S
      bins write = {2};

      // Reserved in a request; must not hang the DTM.
      // spec: dtm.html#dmi
      // testplan: DTM-006-S
      bins reserved = {3};
    }

    // The response encoding is how a debugger decides whether to retry. All
    // three reachable outcomes must occur or the retry logic is untested.
    cp_dmi_result: coverpoint t.dmi_status {
      // Normal completion.
      // spec: dtm.html#dmi
      // testplan: DTM-003-C
      bins success = {0};

      // Sticky failure; further accesses keep failing until dmireset.
      // spec: dtm.html#dmi
      // testplan: DTM-005-C
      bins failed = {2};

      // DM could not keep up; the debugger must back off, idle and retry.
      // spec: dtm.html#dmi
      // testplan: DTM-004-C
      // needs directed stimulus; constrained-random will not reach it
      bins busy = {3};

      // 1 is not a defined response encoding.
      // spec: dtm.html#dmi
      illegal_bins reserved_result = {1};
    }

    // The sticky status a debugger polls to decide whether a reset is needed.
    cp_dtmcs_dmistat: coverpoint dtmcs_rdata[11:10] {
      // Clean state.
      // spec: dtm.html#dtmcs
      // testplan: RST-043-C
      bins no_error = {0};

      // Set by a failed operation and sticky until dmireset.
      // spec: dtm.html#dtmcs
      // testplan: RST-020-C
      bins op_failed = {2};

      // Set when an operation was attempted while busy.
      // spec: dtm.html#dtmcs
      // testplan: DTM-004-C
      bins op_busy = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // run_test_idle_cycles_between_accesses

    // Reads and writes fail differently: a failed read returns stale data, a
    // failed write may partially apply. Both need their failure and busy
    // cells, which neither coverpoint alone proves.
    x_op_x_result: cross cp_dmi_op, cp_dmi_result {
      // A nop does no DM work, so it has no path to a busy response.
      ignore_bins ig = binsof(cp_dmi_op.nop && cp_dmi_result.busy);
    }

    // NOT EMITTED -- cross x_idle_x_result needs unbound coverpoint(s):
    // cp_idle_cycles

  endgroup : cg_dtm_dmi

  // ========================================================================
  // The DM comes out of reset on request and is then genuinely alive —
  // meaning registers other than dmstatus.version read plausible values.
  // spec: debug_module.html#dmcontrol
  // spec: debug_module.html#reset
  // observable via: DMI
  // ========================================================================
  covergroup cg_dm_activation;
    option.per_instance = 1;
    // sampled on: every dmcontrol write and the dmstatus read that follows

    // The 0->1 edge is activation; 1->0 is the DM reset that must return
    // every register to its reset value. The idempotent cases are where a
    // spurious state change would show.
    // transition coverage
    cp_dmactive_transition: coverpoint dm_vif.dmcontrol[0] {
      // Bring the DM out of reset.
      // spec: debug_module.html#dmcontrol
      // testplan: ACT-001-S
      bins activate = (0 => 1);

      // Reset the DM; all state returns to reset values.
      // spec: debug_module.html#reset
      // testplan: ACT-003-S
      bins deactivate = (1 => 0);

      // Full cycle: the state must be clean, not merely re-enabled.
      // spec: debug_module.html#reset
      // testplan: ACT-003-C
      bins reactivate = (1 => 0 => 1);

      // Writing 1 when already active must change nothing.
      // spec: debug_module.html#dmcontrol
      // testplan: ACT-004-S
      bins idempotent_set = (1 => 1);
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // register_read_after_activation

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // operation_attempted_with_dmactive_0

    // NOT EMITTED -- cross x_transition_x_post_read needs unbound
    // coverpoint(s): cp_post_activation_read

  endgroup : cg_dm_activation

  // ========================================================================
  // The DM addresses the hart the debugger selected, and reports truthfully
  // about harts that do not exist or cannot respond.
  // spec: debug_module.html#dmcontrol
  // spec: debug_module.html#dmstatus
  // observable via: DMI
  // ========================================================================
  covergroup cg_hart_selection;
    option.per_instance = 1;
    // sampled on: dmstatus read after any hartsel write

    // NOT EMITTED -- no binding for this DUT. Model samples: hartsel_class

    // The five states dmstatus can report. Each drives different debugger
    // behaviour, and the nonexistent and unavailable states are the ones
    // implementations get wrong.
    cp_hart_reported_state: coverpoint decode_hart_state(dm_vif.dmstatus) {
      // allrunning/anyrunning set.
      // spec: debug_module.html#dmstatus
      // testplan: RES-001-C
      bins running = {0};

      // allhalted/anyhalted set.
      // spec: debug_module.html#dmstatus
      // testplan: HALT-001-C
      bins halted = {1};

      // Hart powered down or held in reset.
      // spec: debug_module.html#dmstatus
      // testplan: HS-004-C
      bins unavailable = {2};

      // No hart at this index.
      // spec: debug_module.html#dmstatus
      // testplan: HS-002-C
      bins nonexistent = {3};

      // ndmreset or hartreset asserted.
      // spec: debug_module.html#dmstatus
      // testplan: RST-010-C
      bins in_reset = {4};
    }

    // A hart that does not exist is not running. This coverpoint exists
    // solely because both project DUTs get it wrong — it is a live defect
    // with a bin of its own so a fix is measurable.
    cp_nonexistent_runstate: coverpoint {dm_vif.dmstatus[DMS_ALLRUNNING], dm_vif.dmstatus[DMS_ANYRUNNING]} {
      // The spec-conformant reading.
      // spec: debug_module.html#dmstatus
      // testplan: HS-002-C2
      bins correctly_not_running = {0};

      // allrunning/anyrunning asserted for a nonexistent hart. Observed on
      // both DUTs — issue #130.
      // spec: debug_module.html#dmstatus
      illegal_bins wrongly_running = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {all_bit,
    // any_bit}

    // NOT EMITTED -- cross x_hartsel_x_state needs unbound coverpoint(s):
    // cp_hartsel_class

    // NOT EMITTED -- cross x_hartsel_x_all_any needs unbound coverpoint(s):
    // cp_hartsel_class, cp_all_vs_any

  endgroup : cg_hart_selection

  // ========================================================================
  // Each reset has the scope the spec defines, resets are survivable mid-
  // operation, and havereset tracks every cause until acknowledged.
  // spec: debug_module.html#reset
  // spec: debug_module.html#dmcontrol
  // observable via: DMI; dmstatus.ndmresetpending and the havereset bits
  // ========================================================================
  covergroup cg_reset;
    option.per_instance = 1;
    // sampled on: every reset assertion and the dmstatus read after release

    // NOT EMITTED -- no binding for this DUT. Model samples: reset_source

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // dm_activity_when_reset_asserted

    // havereset is sticky and cleared only by an explicit acknowledge. The
    // transitions prove stickiness and acknowledgement separately; a single
    // value coverpoint proves neither.
    // transition coverage
    cp_havereset_lifecycle: coverpoint dm_vif.dmstatus[DMS_ANYHAVERESET] {
      // Any reset sets it.
      // spec: debug_module.html#dmstatus
      // testplan: RST-060-C
      bins set_by_reset = (CLEAR => SET);

      // Survives unrelated reads and writes — stickiness.
      // spec: debug_module.html#dmstatus
      // testplan: RST-061-C
      bins stays_set = (SET => SET);

      // ackhavereset clears it.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-062-C
      bins cleared_by_ack = (SET => CLEAR);

      // Clearing without an ackhavereset write, except across dmactive=0
      // where the spec permits either behaviour.
      // spec: debug_module.html#dmstatus
      illegal_bins cleared_without_ack = SET => CLEAR;
    }

    // The only DMI-visible indication that ndmreset is still asserted.
    cp_reset_pending: coverpoint dm_vif.dmstatus[DMS_NDMRESETPENDING] {
      // Set while ndmreset is asserted.
      // spec: debug_module.html#dmstatus
      // testplan: RST-010-C
      bins pending = {1};

      // Clear once the reset completes.
      // spec: debug_module.html#dmstatus
      // testplan: RST-010-C
      bins not_pending = {0};
    }

    // NOT EMITTED -- cross x_source_x_activity needs unbound coverpoint(s):
    // cp_reset_source, cp_activity_at_reset

    // NOT EMITTED -- cross x_source_x_havereset needs unbound coverpoint(s):
    // cp_reset_source

  endgroup : cg_reset

  // ========================================================================
  // Halt and resume move the hart between running and Debug Mode, ignore
  // requests that do not apply, and report the handshake truthfully.
  // spec: debug_module.html#dmcontrol
  // spec: debug_module.html#dmstatus
  // observable via: DMI
  // ========================================================================
  covergroup cg_run_control;
    option.per_instance = 1;
    // sampled on: every dmcontrol write carrying haltreq or resumereq

    // Both bits in one write is an explicitly specified precedence case
    // (haltreq wins), reachable only by writing both together.
    cp_haltreq_x_resumereq: coverpoint {dm_vif.dmcontrol[DMC_HALTREQ], dm_vif.dmcontrol[DMC_RESUMEREQ]} {
      // A dmcontrol write for some other purpose.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-007-V
      bins neither = {0};

      // Ordinary halt.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-001-S
      bins halt_only = {2};

      // Ordinary resume.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-001-S
      bins resume_only = {1};

      // haltreq takes precedence; resumereq has no effect.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-003-S
      // needs directed stimulus; constrained-random will not reach it
      bins both = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {request_type,
    // hart_state_before}

    // Steady states are reached by any test. The transitions carry the
    // behaviour, and the reset-adjacent ones are the ones nobody drives by
    // accident.
    // transition coverage
    cp_hart_transition: coverpoint cur_hart_state {
      // Halt.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-001-C
      bins running_to_halted = (RUNNING => HALTED);

      // Resume.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-001-C
      bins halted_to_running = (HALTED => RUNNING);

      // Reset a running hart.
      // spec: debug_module.html#reset
      // testplan: RST-010-S
      bins running_to_in_reset = (RUNNING => IN_RESET);

      // Normal reset release.
      // spec: debug_module.html#reset
      // testplan: RST-010-C
      bins in_reset_to_running = (IN_RESET => RUNNING);

      // Pending haltreq takes effect on reset release — the portable halt-on-
      // reset substitute.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-053-C
      bins in_reset_to_halted = (IN_RESET => HALTED);

      // Confirmed unreachable on both DUTs 2026-07-25: no stimulus drives a
      // reset while the hart reports halted without passing through RUNNING.
      // Kept so a DUT that can do it is measured.
      ignore_bins halted_to_in_reset = HALTED => IN_RESET;
    }

    // The handshake proving the hart actually resumed rather than merely
    // being asked to.
    cp_resumeack: coverpoint {dm_vif.dmstatus[DMS_ALLRESUMEACK], dm_vif.dmstatus[DMS_ANYRESUMEACK]} {
      // Resume completed.
      // spec: debug_module.html#dmstatus
      // testplan: RES-001-C2
      bins acked = {3};

      // Cleared by a resumereq that was ignored.
      // spec: debug_module.html#dmstatus
      // testplan: RES-002-C
      bins cleared = {0};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // cycles_from_haltreq_to_allhalted

    // resumeack must accompany a real HALTED => RUNNING transition and must
    // be cleared by a resumereq that caused no transition. The §3.5 asymmetry
    // is only visible as the pairing of the two.
    x_transition_x_resumeack: cross cp_hart_transition, cp_resumeack {
      // A hart that genuinely resumed must acknowledge it; a transition with
      // the ack cleared means the handshake is lost.
      illegal_bins il = binsof(cp_hart_transition.halted_to_running && cp_resumeack.cleared);
    }

    // NOT EMITTED -- cross x_request_x_latency needs unbound coverpoint(s):
    // cp_request_x_prior_state, cp_halt_latency

  endgroup : cg_run_control

  // ========================================================================
  // A hart enters Debug Mode for exactly one reason at a time and records
  // which, so a debugger can tell an external halt from a breakpoint, a
  // trigger or a completed step.
  // spec: Sdext.html#csr-dcsr
  // spec: debug_module.html#dmcontrol
  // observable via: dcsr via Access Register; dmstatus over DMI
  // ========================================================================
  covergroup cg_debug_entry;
    option.per_instance = 1;
    // sampled on: abstract read of dcsr after dmstatus.allhalted rises

    // Each cause drives different debugger behaviour. This coverpoint is what
    // proves every entry path was actually taken, and the implemented
    // testbench has no equivalent today.
    cp_cause: coverpoint hart_vif.cause() {
      // ebreak with the matching ebreak* bit set.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-001-C
      bins ebreak = {1};

      // A trigger firing.
      // spec: Sdtrig.html
      // testplan: TRIG-003-C
      // needs directed stimulus; constrained-random will not reach it
      bins trigger = {2};

      // External halt request.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-001-C2
      bins haltreq = {3};

      // Re-entry after a completed single step.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-001-C2
      bins step = {4};

      // Halt-on-reset entry at the first instruction.
      // spec: debug_module.html#dmcontrol
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins resethaltreq = {5};

      // The spec enumerates causes 1-5. Sampling 0 or 6-7 means the DUT
      // reported an undefined cause.
      // spec: Sdext.html#csr-dcsr
      illegal_bins undefined_causes = {0, 6, 7};
    }

    // Records the privilege the hart was in; ebreak gating is per-privilege.
    cp_prv: coverpoint hart_vif.prv() {
      // Entry from user mode.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-011-V
      bins U = {0};

      // Entry from supervisor mode.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-011-V
      bins S = {1};

      // Entry from machine mode.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-011-V
      bins M = {3};

      // Privilege 2 is reserved.
      // spec: Sdext.html#csr-dcsr
      illegal_bins reserved_prv = {2};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {ebreakm,
    // ebreaks, ebreaku} vs executing privilege

    // dpc means different things per cause: the interrupted PC for haltreq,
    // the ebreak's own address, the handler entry for a stepped trap. A
    // single "dpc is plausible" check hides all three.
    cp_dpc_origin: coverpoint classify_dpc_origin(hart_vif.cause()) {
      // haltreq: the instruction that would have executed next.
      // spec: Sdext.html#csr-dpc
      // testplan: HALT-001-C3
      bins interrupted_pc = {0};

      // ebreak: the address of the ebreak itself.
      // spec: Sdext.html#csr-dpc
      // testplan: DM-001-C
      bins ebreak_address = {1};

      // step: advanced by the stepped instruction's length.
      // spec: Sdext.html#csr-dpc
      // testplan: SSTEP-001-C3
      bins next_after_step = {2};

      // A stepped instruction that trapped: the handler's first instruction.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-008-C
      bins trap_handler_entry = {3};
    }

    // ebreak entry is gated per privilege by ebreakm/s/u, so this cross is
    // where a wrongly-gated ebreak shows up. The other causes do not vary by
    // privilege, but recording prv on each catches it being reported wrong.
    x_cause_x_prv: cross cp_cause, cp_prv {
      // Reset-halt entry always reports the post-reset privilege, which is M
      // by definition. The U and S cells are unreachable, not untested.
      ignore_bins ig = binsof(cp_cause.resethaltreq && !cp_prv.M);
    }

    // dpc means something different per cause -- the interrupted PC for
    // haltreq, the ebreak's own address, the next instruction after a step,
    // the handler entry for a stepped trap. A DM can get dpc right for one
    // cause and wrong for another, and only this cross separates them.
    x_cause_x_dpc: cross cp_cause, cp_dpc_origin {
      // ebreak entry must report the ebreak's own address, not the following
      // instruction; reporting the next address would silently skip an
      // instruction on resume.
      illegal_bins il = binsof(cp_cause.ebreak && cp_dpc_origin.next_after_step);
    }

  endgroup : cg_debug_entry

  // ========================================================================
  // Debug Mode suspends the things the spec says it suspends, and dret
  // returns the hart exactly where it came from.
  // spec: Sdext.html#debugmode
  // spec: Sdext.html#dret
  // observable via: dcsr/dpc via abstract command; mcycle and time via
  // program buffer
  // ========================================================================
  covergroup cg_debug_mode;
    option.per_instance = 1;
    // sampled on: entry to and exit from Debug Mode

    // Both settings matter: the suspend and the non-suspend are separate
    // behaviours.
    cp_stopcount: coverpoint {hart_vif.stopcount(), counters_advanced} {
      // stopcount=1: mcycle must not advance while halted.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-006-C
      bins stopped = {2};

      // stopcount=0: counters continue.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-006-S
      bins free_running = {1};

      // stopcount=1 with counters advancing is a conformance failure.
      // spec: Sdext.html#csr-dcsr
      illegal_bins stopped_but_advanced = {3};
    }

    // Same structure as stopcount, on a different timer.
    cp_stoptime: coverpoint {hart_vif.stoptime(), time_advanced} {
      // stoptime=1: time must not update while halted.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-007-C
      bins stopped = {2};

      // stoptime=0: time continues.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-007-S
      bins free_running = {1};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // interrupt_asserted_while_in_debug_mode

    // dret outside Debug Mode is an illegal instruction — the negative case
    // needs its own bin.
    cp_dret_context: coverpoint dret_executed_in_debug {
      // Legal: returns to dpc at dcsr.prv.
      // spec: Sdext.html#dret
      // testplan: DM-003-C
      bins in_debug_mode = {0};

      // Illegal instruction trap.
      // spec: Sdext.html#dret
      // testplan: DM-004-C
      bins outside_debug_mode = {1};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // debug_csr_read_from_privilege

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // debug_rom_flag_written

    // dcsr.stopcount and dcsr.stoptime are independent controls over two
    // different timebases, and an implementation that wires them together
    // passes both coverpoints separately while being wrong. All four
    // combinations are architecturally legal.
    x_stopcount_x_stoptime: cross cp_stopcount, cp_stoptime;

    // NOT EMITTED -- cross x_dret_x_csr_access needs unbound coverpoint(s):
    // cp_debug_csr_access_context

  endgroup : cg_debug_mode

  // ========================================================================
  // A single step retires exactly one instruction and returns to Debug Mode
  // unaided, for every class of instruction — including those that would
  // otherwise never complete.
  // spec: Sdext.html#stepbit
  // observable via: dpc delta and dcsr.cause via Access Register; commit
  // trace
  // ========================================================================
  covergroup cg_step_external;
    option.per_instance = 1;
    // sampled on: dcsr read after the post-step re-halt

    // The instruction class is what makes a step interesting. Ordinary
    // instructions are hit by any test; the stalling and control-transfer
    // classes must be asked for.
    cp_stepped_class: coverpoint hart_vif.commit_iclass {
      // dpc advances by the instruction length.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-001-C3
      bins ordinary = {0};

      // dpc advances by 2 rather than 4.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-002-C
      bins compressed = {1};

      // A stalling instruction stepped over must be treated as a nop. This is
      // the bin that represents the CVA6 deadlock.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-004-C2
      bins wfi = {2};

      // dpc must be the branch target, not the sequential next address.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-003-C
      bins taken_branch = {3};

      // Falls through: dpc is the sequential next address.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-019-C
      bins not_taken_branch = {4};

      // Debug Mode re-entered at the handler's first instruction.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-008-C
      bins trapping = {5};

      // ecall/mret/sret: dcsr.prv must reflect the privilege after the
      // transition.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-009-C
      bins privilege_changing = {6};

      // The access must complete before Debug Mode is re-entered.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-015-C
      bins load_store = {7};

      // Zawrs absent on this DUT; wrs.sto/wrs.nto decode as illegal and would
      // test the trap handler rather than the step rule.
      ignore_bins wrs = {8};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {dcsr.stepie,
    // interrupt_pending}

    // The step is a D->M->D round trip; the return leg is the property under
    // test.
    // transition coverage
    cp_step_transition: coverpoint hart_vif.hart_mode() {
      // A completed step.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-001-C
      bins complete_step = (DEBUG => RUNNING => DEBUG);

      // Two consecutive samples in RUNNING after a step means the hart never
      // re-entered Debug Mode — exactly the CVA6 wfi deadlock.
      // spec: Sdext.html#stepbit
      illegal_bins stuck_running = DEBUG => RUNNING [* 2];
    }

    // If haltreq is still asserted the hart re-halts for the original request
    // and the step proves nothing. This bin guards the whole covergroup's
    // validity.
    cp_haltreq_during_step: coverpoint dm_vif.dmcontrol[DMC_HALTREQ] {
      // The only valid configuration for a step test.
      // spec: debug_module.html#dmcontrol
      // testplan: SSTEP-001-C0
      bins deasserted = {0};

      // A step measured with haltreq asserted is not a step measurement.
      // spec: Sdext.html#stepbit
      illegal_bins still_asserted = {1};
    }

    // The privilege the stepped instruction executed at. Needed in its own
    // right, and as the second leg of x_class_x_privilege.
    cp_prv_at_step: coverpoint hart_vif.prv() {
      // Stepping user code.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-018-V
      bins U = {0};

      // Stepping supervisor code.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-018-V
      bins S = {1};

      // Stepping machine code.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-018-V
      bins M = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // consecutive_steps_without_resume

    // Privilege changes what an instruction class does: a trapping
    // instruction from U enters the M-mode handler, from M stays in M.
    // Stepping the stalling and trapping classes from each privilege is where
    // the interaction lives. The ordinary and compressed classes do not vary
    // by privilege and are ignored here to avoid an empty product.
    x_class_x_privilege: cross cp_stepped_class, cp_prv_at_step {
      // These classes behave identically at every privilege; the cross adds
      // cells without adding information. Privilege for them is covered by
      // cp_prv alone.
      ignore_bins ig = binsof(cp_stepped_class.ordinary || cp_stepped_class.compressed);
    }

    // NOT EMITTED -- cross x_class_x_stepie needs unbound coverpoint(s):
    // cp_stepie_x_irq

    // NOT EMITTED -- cross x_class_x_consecutive needs unbound coverpoint(s):
    // cp_consecutive_steps

  endgroup : cg_step_external

  // ========================================================================
  // Native single-step via an icount trigger steps one instruction of a less-
  // privileged program — with none of the guarantees dcsr.step provides.
  // spec: Sdext.html#stepicount
  // spec: debugger_implementation.html#nativestep
  // observable via: trap into the M-mode stub; mepc; tdata1
  // ========================================================================
  covergroup cg_step_native;
    option.per_instance = 1;
    // sampled on: icount trigger fire

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // native_step_observed_behaviour

    // NOT EMITTED -- no binding for this DUT. Model samples: {stub_privilege,
    // target_privilege}

    // NOT EMITTED -- cross x_guarantee_x_privilege needs unbound
    // coverpoint(s): cp_native_step_guarantees, cp_native_step_privilege

  endgroup : cg_step_native

  // ========================================================================
  // Abstract commands read and write hart state without the hart executing
  // anything the debugger supplied, and report every failure mode distinctly
  // enough for a debugger to react correctly.
  // spec: debug_module.html#access-register
  // spec: debug_module.html#abstractcs
  // observable via: DMI
  // ========================================================================
  covergroup cg_abstract_command;
    option.per_instance = 1;
    // sampled on: every command write and the abstractcs read that follows

    // Unsupported command types must be rejected cleanly, not ignored.
    cp_cmdtype: coverpoint dm_vif.command[CMD_CMDTYPE_LSB +: 8] {
      // The only type this DUT implements.
      // spec: debug_module.html#access-register
      // testplan: AC-001-S
      bins access_register = {0};

      // Must return cmderr=2 when unimplemented.
      // spec: debug_module.html#quick-access
      // testplan: AC-013-S
      bins quick_access = {1};

      // Must return cmderr=2 when unimplemented.
      // spec: debug_module.html#access-memory
      // testplan: AC-013-S
      bins access_memory = {2};

      // Undefined type; must not hang the DM.
      // spec: debug_module.html#abstractcs
      // testplan: AC-018-C
      bins reserved_cmdtype = {3};
    }

    // The register number space has architecturally distinct regions, and the
    // unimplemented region is the one that must fail cleanly.
    cp_regno_class: coverpoint dm_vif.command[CMD_REGNO_LSB +: 16] {
      // 0x0000-0x0fff: CSRs including dcsr/dpc.
      // spec: debug_module.html#access-register
      // testplan: AC-004-S
      bins csr = {0};

      // 0x1000-0x101f: the integer registers.
      // spec: debug_module.html#access-register
      // testplan: AC-001-S
      bins gpr = {1};

      // x0 specifically: reads zero, writes discarded.
      // spec: debug_module.html#access-register
      // testplan: AC-003-C
      bins gpr_x0 = {2};

      // 0x1020-0x103f: present on this imafdc DUT.
      // spec: debug_module.html#access-register
      // testplan: AC-017-V
      bins fpr = {3};

      // Must produce cmderr 2 or 3, not silence.
      // spec: debug_module.html#access-register
      // testplan: AC-006-S
      bins unimplemented = {4};
    }

    // An unsupported size must be rejected rather than silently truncating.
    cp_aarsize: coverpoint dm_vif.command[CMD_AARSIZE_LSB +: 3] {
      // 32-bit access.
      // spec: debug_module.html#access-register
      // testplan: AC-017-V
      bins size32 = {2};

      // 64-bit access on this RV64 DUT.
      // spec: debug_module.html#access-register
      // testplan: AC-001-S
      bins size64 = {3};

      // Unsupported here: expect cmderr=2.
      // spec: debug_module.html#access-register
      // testplan: AC-005-S
      bins size128 = {4};

      // Undefined encodings must be rejected.
      // spec: debug_module.html#access-register
      // testplan: AC-019-C
      bins reserved_size = {0, 1, 5, 6, 7};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {transfer,
    // postexec, aarpostincrement, write}

    // Every error code drives different debugger recovery. A debugger that
    // cannot distinguish busy from halt/resume retries the wrong thing.
    cp_cmderr: coverpoint dm_vif.abstractcs[ABS_CMDERR_LSB +: 3] {
      // Success.
      // spec: debug_module.html#abstractcs
      // testplan: AC-001-C
      bins none = {0};

      // Command or data accessed while busy.
      // spec: debug_module.html#abstractcs
      // testplan: RAP-042-C
      bins busy = {1};

      // Unsupported command, size or register.
      // spec: debug_module.html#abstractcs
      // testplan: AC-005-C
      bins not_supported = {2};

      // The hart faulted executing the command or program buffer.
      // spec: debug_module.html#abstractcs
      // testplan: PB-005-C
      bins exception = {3};

      // Command issued while the hart was not halted.
      // spec: debug_module.html#abstractcs
      // testplan: AC-007-C
      bins halt_resume = {4};

      // Bus error during the command.
      // spec: debug_module.html#abstractcs
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins bus = {5};

      // Catch-all; reaching it means the DM could not classify its own
      // failure.
      // spec: debug_module.html#abstractcs
      // testplan: AC-020-C
      bins other = {7};

      // 6 is not a defined cmderr encoding.
      // spec: debug_module.html#abstractcs
      illegal_bins reserved_cmderr = {6};
    }

    // cmderr is sticky and W1C. A debugger that assumes a successful command
    // clears it misattributes the next failure — and only a transition
    // coverpoint proves stickiness.
    // transition coverage
    cp_cmderr_lifecycle: coverpoint cmderr_state {
      // A failing command sets it.
      // spec: debug_module.html#abstractcs
      // testplan: AC-008-S
      bins set_by_failure = (NONE => ERROR);

      // A subsequent VALID command must not clear it.
      // spec: debug_module.html#abstractcs
      // testplan: AC-008-C
      bins sticky_across_success = (ERROR => ERROR);

      // Only a write of 1s clears it.
      // spec: debug_module.html#abstractcs
      // testplan: AC-009-S
      bins cleared_by_w1c = (ERROR => NONE);

      // Clearing on a successful command instead of on W1C.
      // spec: debug_module.html#abstractcs
      illegal_bins cleared_by_success = ERROR => NONE;
    }

    // If busy is never observed set, the polling loop is untested and a slow
    // command would break a real debugger.
    cp_busy_observed: coverpoint dm_vif.abstractcs[ABS_BUSY] {
      // The debugger actually polled through a busy period.
      // spec: debug_module.html#abstractcs
      // testplan: AC-001-C
      bins busy_observed = {1};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // abstract_command_phase

    // Size legality depends on which register is addressed: a 64-bit access
    // to a 32-bit CSR must be rejected while the same size on a GPR succeeds.
    // This cross is where cmderr=2 for a size actually arises.
    x_regno_x_size: cross cp_regno_class, cp_aarsize {
      // An unimplemented regno fails on the register, not the size; the size
      // cells add nothing.
      ignore_bins ig = binsof(cp_regno_class.unimplemented);
    }

    // Each command type fails differently, and an unimplemented type must
    // give cmderr=2 rather than whatever the last command left behind.
    x_cmdtype_x_cmderr: cross cp_cmdtype, cp_cmderr {
      // Unimplemented on this DUT, so only the not_supported cell is
      // reachable; the others are excluded by construction rather than
      // untested.
      ignore_bins ig = binsof(cp_cmdtype.quick_access || cp_cmdtype.access_memory);
    }

    // NOT EMITTED -- cross x_flags_x_cmderr needs unbound coverpoint(s):
    // cp_command_flags

  endgroup : cg_abstract_command

  // ========================================================================
  // The program buffer executes arbitrary instructions on a halted hart and
  // returns control cleanly, including when the instructions fault.
  // spec: debug_module.html#program-buffer
  // spec: debug_module.html#abstractcs
  // observable via: cmderr; hart registers and memory via abstract command
  // ========================================================================
  covergroup cg_program_buffer;
    option.per_instance = 1;
    // sampled on: each postexec completion

    // Boundaries sit at one word and at exactly progbufsize — the last slot
    // is where an off-by-one in the buffer decode shows up.
    cp_progbuf_fill: coverpoint progbuf_words_written {
      // Minimum useful buffer.
      // spec: debug_module.html#program-buffer
      // testplan: PB-001-S
      bins single_word = {1};

      // Ordinary use.
      // spec: debug_module.html#abstractcs
      // testplan: PB-011-C
      bins partial = [2:7];

      // Exactly progbufsize — the boundary.
      // spec: debug_module.html#abstractcs
      // testplan: PB-003-S
      bins full = {8};

      // One past the end: must be ignored, not wrap onto progbuf0.
      // spec: debug_module.html#abstractcs
      // testplan: DIS-005-S
      bins overflow = {9};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // program_buffer_termination

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // what_the_buffer_did

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // progbuf_execution_count

    // NOT EMITTED -- cross x_outcome_x_operation needs unbound coverpoint(s):
    // cp_progbuf_outcome, cp_progbuf_operation

    // NOT EMITTED -- cross x_fill_x_outcome needs unbound coverpoint(s):
    // cp_progbuf_outcome

  endgroup : cg_program_buffer

  // ========================================================================
  // System Bus Access reaches memory independently of the hart, its MMU and
  // its PMP, and reports every error class distinctly.
  // spec: debug_module.html#sbcs
  // spec: debug_module.html#systembusaccess
  // observable via: DMI; sberror and sbbusy
  // ========================================================================
  covergroup cg_system_bus_access;
    option.per_instance = 1;
    // sampled on: every sbcs write and every sbdata access

    // sbaccess is declared R/W with a reset of constant 2. Every size, and an
    // unsupported one, must be writable — the unsupported case is how
    // sberror=4 is reached at all.
    cp_sbaccess_size: coverpoint dm_vif.sbcs[SBCS_SBACCESS_LSB +: 3] {
      // 8-bit access.
      // spec: debug_module.html#sbcs
      // testplan: SBA-011-V
      bins size8 = {0};

      // 16-bit access.
      // spec: debug_module.html#sbcs
      // testplan: SBA-011-V
      bins size16 = {1};

      // 32-bit; also the specified reset value.
      // spec: debug_module.html#sbcs
      // testplan: RST-038-C2
      bins size32 = {2};

      // 64-bit, the only size this DUT advertises.
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-S
      bins size64 = {3};

      // 128-bit.
      // spec: debug_module.html#sbcs
      // testplan: SBA-011-V
      bins size128 = {4};

      // Spec: an unsupported value at access time gives sberror=4. The field
      // must accept the write for that path to exist.
      // spec: debug_module.html#sbcs
      // testplan: RAP-007-C3
      bins unsupported_size_written = {7};
    }

    // Each error class means a different debugger response.
    cp_sberror: coverpoint dm_vif.sbcs[SBCS_SBERROR_LSB +: 3] {
      // Success.
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-C
      bins none = {0};

      // The bus did not respond.
      // spec: debug_module.html#sbcs
      // testplan: SBA-012-C
      bins timeout = {1};

      // Unmapped physical address.
      // spec: debug_module.html#sbcs
      // testplan: SBA-008-C
      bins bad_address = {2};

      // Misaligned for the selected size.
      // spec: debug_module.html#sbcs
      // testplan: SBA-007-C
      bins alignment = {3};

      // sbaccess named a size the DM does not support.
      // spec: debug_module.html#sbcs
      // testplan: SBA-006-C
      bins unsupported_size = {4};

      // Catch-all.
      // spec: debug_module.html#sbcs
      // testplan: SBA-013-C
      bins other = {7};
    }

    // These three compose into the block-transfer modes a debugger actually
    // uses. Autoincrement with readondata is how a memory dump works, and it
    // is a different path from a single addressed read.
    cp_sb_trigger_mode: coverpoint {dm_vif.sbcs[SBCS_SBREADONADDR], dm_vif.sbcs[SBCS_SBREADONDATA], dm_vif.sbcs[SBCS_SBAUTOINCREMENT]} {
      // Explicit address then explicit data access.
      // spec: debug_module.html#sbcs
      // testplan: SBA-014-C
      bins manual = {0};

      // Writing the address triggers the read.
      // spec: debug_module.html#sbcs
      // testplan: SBA-003-C
      bins read_on_addr = {4};

      // Reading data triggers the next read.
      // spec: debug_module.html#sbcs
      // testplan: SBA-004-C
      bins read_on_data = {2};

      // readondata + autoincrement: the memory-dump mode.
      // spec: debug_module.html#sbcs
      // testplan: SBA-005-C
      bins block_dump = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: sbaddress

    // NOT EMITTED -- no binding for this DUT. Model samples: sbaddress
    // alignment relative to sbaccess size

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // sba_while_hart_running

    // Accessing while busy must be reported, not silently dropped or applied.
    cp_sbbusyerror: coverpoint dm_vif.sbcs[SBCS_SBBUSYERROR] {
      // sbbusyerror set; the in-flight transfer unaffected.
      // spec: debug_module.html#sbcs
      // testplan: RAP-043-C
      bins flagged = {1};
    }

    // NOT EMITTED -- cross x_size_x_alignment needs unbound coverpoint(s):
    // cp_sb_alignment

    // An error mid-block-transfer is the interesting case: with autoincrement
    // the address has already advanced, so the debugger must be able to tell
    // which word failed. A single-access error does not have that problem.
    x_mode_x_error: cross cp_sb_trigger_mode, cp_sberror;

    // NOT EMITTED -- cross x_size_x_region needs unbound coverpoint(s):
    // cp_sb_address_region

  endgroup : cg_system_bus_access

  // ========================================================================
  // Triggers halt the hart on a condition rather than on a debugger request,
  // for each supported trigger type and privilege.
  // spec: Sdtrig.html
  // spec: Sdtrig.html#mcontrol6
  // observable via: tselect/tdata via abstract command; dcsr.cause
  // ========================================================================
  covergroup cg_triggers;
    option.per_instance = 1;
    // sampled on: every tdata write and every trigger fire

    // Each type matches on a different event and has its own configuration
    // path.
    cp_trigger_type: coverpoint last_tdata1[TRIG_TYPE_LSB_RV32 +: 4] {
      // Trigger slot exists but is unconfigured.
      // spec: Sdtrig.html
      // testplan: TRIG-006-C
      bins none = {0};

      // v0.13-era match control; encoding differs from mcontrol6.
      // spec: Sdtrig.html
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins mcontrol = {2};

      // Instruction count — the native single-step mechanism.
      // spec: Sdtrig.html#icount
      // testplan: TRIG-008-C
      bins icount = {3};

      // Interrupt trigger.
      // spec: Sdtrig.html#itrigger
      // testplan: TRIG-009-C
      bins itrigger = {4};

      // Exception trigger.
      // spec: Sdtrig.html#itrigger
      // testplan: TRIG-009-C
      bins etrigger = {5};

      // The v1.0 match control.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-003-S
      bins mcontrol6 = {6};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples: {execute, load,
    // store}

    // NOT EMITTED -- no binding for this DUT. Model samples: {m, s, u} enable
    // bits

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // tselect_write_vs_readback

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // tdata_written_while

    // NOT EMITTED -- cross x_match_x_privilege needs unbound coverpoint(s):
    // cp_match_event, cp_trigger_privilege

    // NOT EMITTED -- cross x_type_x_privilege needs unbound coverpoint(s):
    // cp_trigger_privilege

    // NOT EMITTED -- cross x_type_x_update_context needs unbound
    // coverpoint(s): cp_trigger_update_context

  endgroup : cg_triggers

  // ========================================================================
  // Halt and resume groups propagate a halt between harts and to external
  // trigger outputs.
  // spec: debug_module.html#dmcs2
  // spec: debug_module.html#halt-groups
  // observable via: DMI; external trigger pins
  // ========================================================================
  covergroup cg_halt_groups;
    option.per_instance = 1;
    // sampled on: every dmcs2 write and every group-propagated halt

    // Halt groups and resume groups are configured through the same field
    // pair.
    cp_group_config: coverpoint {dm_vif.dmcs2[DMCS2_GROUPTYPE], dm_vif.dmcs2[DMCS2_HGSELECT]} {
      // grouptype=0.
      // spec: debug_module.html#dmcs2
      // testplan: HG-001-S
      bins halt_group = {0};

      // grouptype=1.
      // spec: debug_module.html#dmcs2
      // testplan: HG-003-S
      bins resume_group = {1};

      // hgselect=1 selects the external trigger rather than a hart group.
      // spec: debug_module.html#dmcs2
      // testplan: HG-003-S
      bins external_trigger = {2};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // group_halt_propagated

    // NOT EMITTED -- cross x_config_x_propagation needs unbound
    // coverpoint(s): cp_group_propagation

  endgroup : cg_halt_groups

  // ========================================================================
  // An unauthenticated DM exposes only what the spec permits, and reports
  // itself already authenticated when it implements no authentication.
  // spec: debug_module.html#authdata
  // spec: debug_module.html#dmstatus
  // observable via: DMI
  // ========================================================================
  covergroup cg_authentication;
    option.per_instance = 1;
    // sampled on: dmstatus reads and any authdata access

    // A DM with no authentication must report authenticated=1 from reset, or
    // every debugger will refuse to proceed.
    cp_auth_state: coverpoint {dm_vif.dmstatus[DMS_AUTHENTICATED], dm_vif.dmstatus[DMS_AUTHBUSY]} {
      // authenticated=1 permanently. The only bin reachable on this DUT.
      // spec: debug_module.html#dmstatus
      // testplan: AUTH-001-C
      bins no_auth_implemented = {1};

      // Access restricted to dmstatus/dmcontrol/authdata.
      // spec: debug_module.html#authdata
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins unauthenticated = {0};

      // authbusy set during the exchange.
      // spec: debug_module.html#dmstatus
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins auth_in_progress = {2};

      // authbusy set while already authenticated is contradictory.
      // spec: debug_module.html#dmstatus
      illegal_bins busy_and_authenticated = {3};
    }

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // register_class_accessed_while_unauthenticated

    // NOT EMITTED -- cross x_auth_x_gated_access needs unbound coverpoint(s):
    // cp_auth_permitted_register

  endgroup : cg_authentication

  // ========================================================================
  // Every DM register honours its declared access type, from every interface
  // that can reach it. The same storage can be writable from one side and
  // read-only from another.
  // spec: debug_module.html
  // spec: introduction.html#1-1-3-3-register-definition-format
  // observable via: DMI; hart CSR reads via program buffer; SBA
  // ========================================================================
  covergroup cg_register_access;
    option.per_instance = 1;
    // sampled on: every register access, tagged with the originating
    // interface

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // field_access_type

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // originating_interface

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // register_class_being_accessed

    // NOT EMITTED -- no binding for this DUT. Model samples:
    // dm_gating_state_at_access

    // NOT EMITTED -- cross x_interface_x_register needs unbound
    // coverpoint(s): cp_interface, cp_register_class

    // NOT EMITTED -- cross x_interface_x_access_type needs unbound
    // coverpoint(s): cp_interface, cp_access_type

    // NOT EMITTED -- cross x_class_x_gating needs unbound coverpoint(s):
    // cp_register_class, cp_gating_state

  endgroup : cg_register_access

  // ------------------------------------------------------------------------
  // 35 coverpoint(s) in the model have no binding on this
  // DUT and were not emitted. This list is the distance between what
  // the specification asks for and what this testbench can observe.
  // ------------------------------------------------------------------------
  //   cg_dtm_dmi.cp_idle_cycles  [range]  model samples: run_test_idle_cycles_between_accesses
  //   cg_dm_activation.cp_post_activation_read  [event]  model samples: register_read_after_activation
  //   cg_dm_activation.cp_op_while_inactive  [event]  model samples: operation_attempted_with_dmactive_0
  //   cg_hart_selection.cp_hartsel_class  [value]  model samples: hartsel_class
  //   cg_hart_selection.cp_all_vs_any  [value]  model samples: {all_bit, any_bit}
  //   cg_reset.cp_reset_source  [value]  model samples: reset_source
  //   cg_reset.cp_activity_at_reset  [state]  model samples: dm_activity_when_reset_asserted
  //   cg_run_control.cp_request_x_prior_state  [value]  model samples: {request_type, hart_state_before}
  //   cg_run_control.cp_halt_latency  [range]  model samples: cycles_from_haltreq_to_allhalted
  //   cg_debug_entry.cp_ebreak_enable  [value]  model samples: {ebreakm, ebreaks, ebreaku} vs executing privi
  //   cg_debug_mode.cp_interrupts_in_debug  [event]  model samples: interrupt_asserted_while_in_debug_mode
  //   cg_debug_mode.cp_debug_csr_access_context  [value]  model samples: debug_csr_read_from_privilege
  //   cg_debug_mode.cp_debug_rom_flags  [event]  model samples: debug_rom_flag_written
  //   cg_step_external.cp_stepie_x_irq  [value]  model samples: {dcsr.stepie, interrupt_pending}
  //   cg_step_external.cp_consecutive_steps  [range]  model samples: consecutive_steps_without_resume
  //   cg_step_native.cp_native_step_guarantees  [value]  model samples: native_step_observed_behaviour
  //   cg_step_native.cp_native_step_privilege  [value]  model samples: {stub_privilege, target_privilege}
  //   cg_abstract_command.cp_command_flags  [value]  model samples: {transfer, postexec, aarpostincrement, write}
  //   cg_abstract_command.cp_command_sequence  [sequence]  model samples: abstract_command_phase
  //   cg_program_buffer.cp_progbuf_outcome  [value]  model samples: program_buffer_termination
  //   cg_program_buffer.cp_progbuf_operation  [value]  model samples: what_the_buffer_did
  //   cg_program_buffer.cp_progbuf_reuse  [transition]  model samples: progbuf_execution_count
  //   cg_system_bus_access.cp_sb_address_region  [range]  model samples: sbaddress
  //   cg_system_bus_access.cp_sb_alignment  [value]  model samples: sbaddress alignment relative to sbaccess size
  //   cg_system_bus_access.cp_sb_concurrency  [event]  model samples: sba_while_hart_running
  //   cg_triggers.cp_match_event  [value]  model samples: {execute, load, store}
  //   cg_triggers.cp_trigger_privilege  [value]  model samples: {m, s, u} enable bits
  //   cg_triggers.cp_tselect_probe  [value]  model samples: tselect_write_vs_readback
  //   cg_triggers.cp_trigger_update_context  [value]  model samples: tdata_written_while
  //   cg_halt_groups.cp_group_propagation  [event]  model samples: group_halt_propagated
  //   cg_authentication.cp_auth_permitted_register  [value]  model samples: register_class_accessed_while_unauthenticated
  //   cg_register_access.cp_access_type  [value]  model samples: field_access_type
  //   cg_register_access.cp_interface  [value]  model samples: originating_interface
  //   cg_register_access.cp_register_class  [value]  model samples: register_class_being_accessed
  //   cg_register_access.cp_gating_state  [state]  model samples: dm_gating_state_at_access

  // ------------------------------------------------------------------------
  // Assertion candidates -- NOT functional coverage.
  // A property being proven says nothing about whether the
  // interesting scenarios were exercised.
  // ------------------------------------------------------------------------
  // a_one_retire_per_step: Between dret and the next Debug Mode entry with dcsr.cause==4, exactly one instruction retires.
  //   spec: Sdext.html#stepbit
  // a_halt_within_bound: allhalted rises within one second of haltreq being asserted on an available hart.
  //   spec: debug_module.html#dmcontrol
  // a_cmderr_sticky: cmderr never transitions from non-zero to zero except on a write of 1s to that field.
  //   spec: debug_module.html#abstractcs
  // a_busy_before_result: abstractcs.busy is set for at least one cycle between a command write and cmderr updating.
  //   spec: debug_module.html#abstractcs
  // a_no_interrupt_in_debug: No trap is taken while debug_mode is asserted.
  //   spec: Sdext.html#debugmode
  // a_dm_regs_stable_across_ndmreset: DM register values are unchanged across an ndmreset assert/deassert.
  //   spec: debug_module.html#reset

