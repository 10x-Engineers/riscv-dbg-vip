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
    cp_dmi_op: coverpoint dmi.op (request) {
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
    cp_dmi_result: coverpoint dmi.op (response) {
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
    cp_dtmcs_dmistat: coverpoint dtmcs.dmistat {
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

    // dtmcs.idle advertises how many idle cycles the DM needs. Under-running
    // it is the classic source of intermittent failures on a fast debugger,
    // so the boundary sits at the advertised value, not at a round number.
    cp_idle_cycles: coverpoint run_test_idle_cycles_between_accesses {
      // No idling at all — provokes busy if the DM needs any.
      // spec: dtm.html#dtmcs
      // testplan: DTM-004-S
      bins none = {0};

      // One short of dtmcs.idle. Range resolved at elaboration from the
      // advertised value.
      // spec: dtm.html#dtmcs
      // testplan: DIS-004-S
      bins below_advertised = [1:0];

      // Exactly dtmcs.idle — must always succeed.
      // spec: dtm.html#dtmcs
      // testplan: DIS-004-C
      bins exactly_advertised = [0:0];

      // Generous idling — the baseline every other test runs at.
      // spec: dtm.html#dtmcs
      bins above_advertised = {99};
    }

    // Reads and writes fail differently: a failed read returns stale data, a
    // failed write may partially apply. Both need their failure and busy
    // cells, which neither coverpoint alone proves.
    x_op_x_result: cross cp_dmi_op, cp_dmi_result {
      // A nop does no DM work, so it has no path to a busy response.
      ignore_bins ig = binsof(cp_dmi_op.nop && cp_dmi_result.busy);
    }

    // Under-running dtmcs.idle is the specified way to provoke a busy
    // response. This cross is the only place that causal link is measured:
    // idling correctly must never yield busy, and idling short must be able
    // to.
    x_idle_x_result: cross cp_idle_cycles, cp_dmi_result {
      // A DM that advertises N idle cycles and still reports busy after N has
      // mis-declared dtmcs.idle.
      illegal_bins il = binsof(cp_idle_cycles.exactly_advertised && cp_dmi_result.busy);
    }

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
    cp_dmactive_transition: coverpoint dmcontrol.dmactive {
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

    // dmstatus.version reads correctly even on a dead DM, so reading it
    // proves nothing. Coverage must record that registers BEYOND version were
    // read and were plausible.
    cp_post_activation_read: coverpoint register_read_after_activation {
      // nscratch/dataaccess consistent with the DUT.
      // spec: debug_module.html#hartinfo
      // testplan: ACT-002-C
      bins hartinfo = {0};

      // progbufsize/datacount non-zero and within legal range.
      // spec: debug_module.html#abstractcs
      // testplan: ACT-002-C
      bins abstractcs = {1};

      // Reads consistent with the hart's actual halt state.
      // spec: debug_module.html#haltsum0
      // testplan: ACT-002-S
      bins haltsum0 = {2};
    }

    // Operations issued before activation must be ignored, not queued.
    cp_op_while_inactive: coverpoint operation_attempted_with_dmactive_0 {
      // haltreq with dmactive=0 must not halt the hart.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-003-C
      bins haltreq_ignored = {0};

      // Reads return reset values while inactive.
      // spec: debug_module.html#dmcontrol
      // testplan: RAP-040-C
      bins other_register_read = {1};
    }

    // What a register should read depends on which transition preceded it.
    // After a full reactivate every register must read its reset value; after
    // an idempotent write they must be unchanged. Reading the same register
    // proves opposite things in the two cases, and neither coverpoint alone
    // distinguishes them.
    x_transition_x_post_read: cross cp_dmactive_transition, cp_post_activation_read {
      // With dmactive=0 only dmcontrol is meaningful, so the post-activation
      // reads are not defined for this cell; RAP-040-C owns the inactive
      // case.
      ignore_bins ig = binsof(cp_dmactive_transition.deactivate);
    }

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

    // What matters is the class of index, not its numeric value: existing,
    // just past the end, and all-ones (the width probe) behave differently.
    cp_hartsel_class: coverpoint hartsel_class {
      // Hart 0 always exists.
      // spec: debug_module.html#dmcontrol
      // testplan: HS-001-S
      bins first_existing = {0};

      // The highest implemented index — the boundary the DM must still
      // decode.
      // spec: debug_module.html#dmcontrol
      bins last_existing = {1};

      // One past the end: the DM must report nonexistent, not wrap.
      // spec: debug_module.html#dmstatus
      // testplan: HS-002-S
      bins first_nonexistent = {2};

      // The standard width-discovery probe: write all ones, read back the
      // implemented width.
      // spec: debug_module.html#dmcontrol
      // testplan: DIS-003-S
      bins all_ones = {3};
    }

    // The five states dmstatus can report. Each drives different debugger
    // behaviour, and the nonexistent and unavailable states are the ones
    // implementations get wrong.
    cp_hart_reported_state: coverpoint hart_state_from_dmstatus {
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
    cp_nonexistent_runstate: coverpoint {allrunning, anyrunning} when nonexistent {
      // The spec-conformant reading.
      // spec: debug_module.html#dmstatus
      // testplan: HS-002-C2
      bins correctly_not_running = {0};

      // allrunning/anyrunning asserted for a nonexistent hart. Observed on
      // both DUTs — issue #130.
      // spec: debug_module.html#dmstatus
      illegal_bins wrongly_running = {3};
    }

    // all/any pairs only differ in a multi-hart system, but the {0,1}
    // combination is architecturally impossible in any system and is worth an
    // illegal bin regardless of hart count.
    cp_all_vs_any: coverpoint {all_bit, any_bit} {
      // No selected hart in this state.
      // spec: debug_module.html#dmstatus
      bins neither = {0};

      // any set, all clear — only reachable with multiple harts selected.
      // spec: debug_module.html#dmstatus
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins some_not_all = {1};

      // Every selected hart in this state.
      // spec: debug_module.html#dmstatus
      // testplan: HALT-001-C
      bins all_and_any = {3};

      // all set with any clear is a contradiction in any hart count.
      // spec: debug_module.html#dmstatus
      illegal_bins all_without_any = {2};
    }

    // Selecting a nonexistent index must report nonexistent rather than the
    // previously selected hart's state -- a stale-mux bug looks exactly like
    // a correct read on either coverpoint alone.
    x_hartsel_x_state: cross cp_hartsel_class, cp_hart_reported_state {
      // A nonexistent hart reported as running or halted. Observed on both
      // DUTs -- issue #130.
      illegal_bins il = binsof(cp_hartsel_class.first_nonexistent && (cp_hart_reported_state.running || cp_hart_reported_state.halted));
    }

    // all/any only diverge with several harts selected, and which harts are
    // selected is what hartsel controls. On a multi-hart DUT this is where a
    // selection mask that reports the wrong aggregate shows up.
    x_hartsel_x_all_any: cross cp_hartsel_class, cp_all_vs_any {
      // Requires more than one hart selected. Unreachable on a single-hart
      // DUT; retained so a multi-hart DUT is measured here.
      ignore_bins ig = binsof(cp_all_vs_any.some_not_all);
    }

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

    // The sources have different scopes, and a DM that conflates them resets
    // things it should not. Each needs its own bin.
    cp_reset_source: coverpoint reset_source {
      // Cold start; the baseline every reset value is checked against.
      // spec: debug_module.html#reset
      // testplan: RST-030-C
      bins power_on = {0};

      // Resets the DM but must not reset the DTM.
      // spec: debug_module.html#reset
      // testplan: RST-001-S
      bins dmactive_low = {1};

      // Resets the platform but not the DM/DTM/DMI.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-010-S
      bins ndmreset = {2};

      // Resets only the selected harts.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-011-S
      bins hartreset = {3};

      // Clears a sticky DMI error without disturbing DM state.
      // spec: dtm.html#dtmcs
      // testplan: RST-020-S
      bins dtm_dmireset = {4};

      // Forcibly resets the DTM state machine.
      // spec: dtm.html#dtmcs
      // testplan: RST-021-S
      bins dtm_dmihardreset = {5};

      // A platform reset outside the DM's control must still set havereset.
      // spec: debug_module.html#dmstatus
      // testplan: RST-012-V
      bins external = {6};
    }

    // A reset landing mid-operation is where DMs wedge. These are the in-
    // flight states worth interrupting, and each leaves different internal
    // state to recover from.
    cp_activity_at_reset: coverpoint dm_activity_when_reset_asserted {
      // Baseline.
      // spec: debug_module.html#reset
      bins idle = {0};

      // The common case.
      // spec: debug_module.html#reset
      // testplan: RST-013-V
      bins hart_running = {1};

      // Reset from inside Debug Mode.
      // spec: debug_module.html#reset
      // testplan: RST-013-V
      bins hart_halted = {2};

      // Reset with abstractcs.busy=1 — classic hang source.
      // spec: debug_module.html#abstractcs
      // testplan: RST-050-S
      // needs directed stimulus; constrained-random will not reach it
      bins abstract_busy = {3};

      // Reset with sbcs.sbbusy=1.
      // spec: debug_module.html#sbcs
      // testplan: RST-051-S
      bins sb_busy = {4};

      // Reset between a DMI request and its response.
      // spec: dtm.html#dmi
      // testplan: RST-052-S
      bins dmi_in_flight = {5};

      // Reset while the hart is stalled in wfi.
      // spec: Sdext.html#4-1-3-wait-for-interrupt-instruction
      // testplan: RST-013-V
      bins hart_stalled_wfi = {6};
    }

    // havereset is sticky and cleared only by an explicit acknowledge. The
    // transitions prove stickiness and acknowledgement separately; a single
    // value coverpoint proves neither.
    // transition coverage
    cp_havereset_lifecycle: coverpoint havereset_state {
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
    cp_reset_pending: coverpoint dmstatus.ndmresetpending {
      // Set while ndmreset is asserted.
      // spec: debug_module.html#dmstatus
      // testplan: RST-010-C
      bins pending = {1};

      // Clear once the reset completes.
      // spec: debug_module.html#dmstatus
      // testplan: RST-010-C
      bins not_pending = {0};
    }

    // A reset landing mid-operation is where DMs wedge, and which reset it is
    // decides what should survive. ndmreset during an abstract command must
    // leave the DM usable; dmactive=0 during the same command may
    // legitimately discard it. Neither coverpoint alone distinguishes them.
    x_source_x_activity: cross cp_reset_source, cp_activity_at_reset {
      // The DTM resets act on the transport, not the DM, so hart-activity
      // cells carry no information for them.
      ignore_bins ig = binsof(cp_reset_source.dtm_dmireset || cp_reset_source.dtm_dmihardreset);
    }

    // The spec requires havereset to be set regardless of which cause reset
    // the hart. That is a per-source claim, so only the cross can show a DM
    // that tracks ndmreset but silently misses an external reset.
    x_source_x_havereset: cross cp_reset_source, cp_havereset_lifecycle {
      // The DTM resets do not reset any hart, so they have no havereset
      // semantics.
      ignore_bins ig = binsof(cp_reset_source.dtm_dmireset || cp_reset_source.dtm_dmihardreset);
    }

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
    cp_haltreq_x_resumereq: coverpoint {haltreq, resumereq} {
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

    // A request's effect depends entirely on the state it lands in, and the
    // spec defines an asymmetry: resumereq on a running hart is ignored but
    // still clears resumeack. That combination is only reachable here.
    cp_request_x_prior_state: coverpoint {request_type, hart_state_before} {
      // Takes effect.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-001-S
      bins halt_when_running = {0};

      // Ignored; no state change.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-002-S
      bins halt_when_halted = {1};

      // Pending; takes effect on reset release.
      // spec: debug_module.html#dmcontrol
      // testplan: RST-053-S
      bins halt_when_in_reset = {2};

      // Takes effect.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-001-S
      bins resume_when_halted = {3};

      // Ignored, but resumeack is still cleared — the §3.5 asymmetry.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-002-C
      bins resume_when_running = {4};

      // No transition; the hart is neither halted nor running.
      // spec: debug_module.html#dmcontrol
      // testplan: RES-006-S
      bins resume_when_in_reset = {5};
    }

    // Steady states are reached by any test. The transitions carry the
    // behaviour, and the reset-adjacent ones are the ones nobody drives by
    // accident.
    // transition coverage
    cp_hart_transition: coverpoint hart_state {
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
    cp_resumeack: coverpoint {allresumeack, anyresumeack} {
      // Resume completed.
      // spec: debug_module.html#dmstatus
      // testplan: RES-001-C2
      bins acked = {3};

      // Cleared by a resumereq that was ignored.
      // spec: debug_module.html#dmstatus
      // testplan: RES-002-C
      bins cleared = {0};
    }

    // The spec bounds halt response at one second. The interesting boundaries
    // are "immediate" and "longer than any test should wait", not an
    // arbitrary bucket split.
    cp_halt_latency: coverpoint cycles_from_haltreq_to_allhalted {
      // The common case on a hart executing ordinary instructions.
      // spec: debug_module.html#dmcontrol
      bins immediate = [0:10];

      // Hart was stalled or mid-instruction; still well within bound.
      // spec: debug_module.html#dmcontrol
      // testplan: HALT-003-S
      bins delayed = {100};

      // Beyond the spec's one-second bound — a conformance failure, not slow
      // hardware.
      // spec: debug_module.html#dmcontrol
      illegal_bins over_bound = [1000000000:2000000000];
    }

    // resumeack must accompany a real HALTED => RUNNING transition and must
    // be cleared by a resumereq that caused no transition. The §3.5 asymmetry
    // is only visible as the pairing of the two.
    x_transition_x_resumeack: cross cp_hart_transition, cp_resumeack {
      // A hart that genuinely resumed must acknowledge it; a transition with
      // the ack cleared means the handshake is lost.
      illegal_bins il = binsof(cp_hart_transition.halted_to_running && cp_resumeack.cleared);
    }

    // Latency is only meaningful for requests that take effect. A halt on a
    // running hart has a bound; a halt on an already-halted hart has no
    // latency at all, and conflating them hides a slow path behind the
    // ignored cases.
    x_request_x_latency: cross cp_request_x_prior_state, cp_halt_latency {
      // These requests are specified as ignored, so no transition occurs and
      // latency is undefined for them.
      ignore_bins ig = binsof(cp_request_x_prior_state.halt_when_halted || cp_request_x_prior_state.resume_when_running);
    }

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
    cp_cause: coverpoint dcsr.cause {
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
    cp_prv: coverpoint dcsr.prv {
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

    // The enable-clear case is the one that catches a stuck-enabled bit, and
    // it is invisible to a coverpoint that only samples successful entries.
    cp_ebreak_enable: coverpoint {ebreakm, ebreaks, ebreaku} vs executing privilege {
      // ebreak* set: ebreak enters Debug Mode.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-001-C
      bins enabled_entered_debug = {1};

      // ebreak* clear: ebreak takes an ordinary breakpoint trap, mcause=3.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-002-C
      bins disabled_took_trap = {0};
    }

    // dpc means different things per cause: the interrupted PC for haltreq,
    // the ebreak's own address, the handler entry for a stepped trap. A
    // single "dpc is plausible" check hides all three.
    cp_dpc_origin: coverpoint dpc_relationship_to_entry {
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
    cp_stopcount: coverpoint {dcsr.stopcount, counters_advanced} {
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
    cp_stoptime: coverpoint {dcsr.stoptime, time_advanced} {
      // stoptime=1: time must not update while halted.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-007-C
      bins stopped = {2};

      // stoptime=0: time continues.
      // spec: Sdext.html#csr-dcsr
      // testplan: DM-007-S
      bins free_running = {1};
    }

    // An interrupt taken in Debug Mode would corrupt the debugger's context.
    cp_interrupts_in_debug: coverpoint interrupt_asserted_while_in_debug_mode {
      // Interrupt pending and enabled but not taken while halted.
      // spec: Sdext.html#debugmode
      // testplan: DM-005-C
      bins masked_correctly = {0};

      // An interrupt serviced while in Debug Mode.
      // spec: Sdext.html#debugmode
      illegal_bins taken_in_debug = {1};
    }

    // dret outside Debug Mode is an illegal instruction — the negative case
    // needs its own bin.
    cp_dret_context: coverpoint dret_executed_in {
      // Legal: returns to dpc at dcsr.prv.
      // spec: Sdext.html#dret
      // testplan: DM-003-C
      bins in_debug_mode = {0};

      // Illegal instruction trap.
      // spec: Sdext.html#dret
      // testplan: DM-004-C
      bins outside_debug_mode = {1};
    }

    // dcsr/dpc/dscratch must be invisible outside Debug Mode.
    cp_debug_csr_access_context: coverpoint debug_csr_read_from_privilege {
      // Legal.
      // spec: Sdext.html#csr-dcsr
      // testplan: RAP-020-S
      bins from_debug_mode = {0};

      // Illegal instruction, even at machine privilege.
      // spec: Sdext.html#csr-dcsr
      // testplan: RAP-022-C
      bins from_m_mode = {1};
    }

    // The ROM/dm_mem flag addresses must agree. A stride mismatch here made
    // every abstract command hang, and no register-level coverpoint saw it.
    cp_debug_rom_flags: coverpoint debug_rom_flag_written {
      // Hart reports arrival in Debug Mode.
      // spec: debug_module.html
      // testplan: DM-008-C
      bins halted = {0};

      // Hart acknowledges a command. The flag whose stride was wrong.
      // spec: debug_module.html
      // testplan: DM-009-C
      bins going = {1};

      // Hart acknowledges a resume.
      // spec: debug_module.html
      // testplan: DM-009-C
      bins resuming = {2};

      // Hart reports a fault during program buffer execution.
      // spec: debug_module.html
      // testplan: PB-005-C
      bins exception = {3};
    }

    // dcsr.stopcount and dcsr.stoptime are independent controls over two
    // different timebases, and an implementation that wires them together
    // passes both coverpoints separately while being wrong. All four
    // combinations are architecturally legal.
    x_stopcount_x_stoptime: cross cp_stopcount, cp_stoptime;

    // Both measure what the hart may do outside Debug Mode. The cross
    // confirms the privilege check is on Debug Mode itself rather than on
    // machine privilege -- a hart in M-mode must be refused both.
    x_dret_x_csr_access: cross cp_dret_context, cp_debug_csr_access_context;

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
    cp_stepped_class: coverpoint stepped_instruction_class {
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

    // stepie decides whether an interrupt may fire during the step, and it
    // only matters with an interrupt actually pending. A 2x2 rather than two
    // independent points, because three of the four cells are trivial and one
    // is the whole question.
    cp_stepie_x_irq: coverpoint {dcsr.stepie, interrupt_pending} {
      // Baseline step.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-006-C
      bins masked_no_irq = {0};

      // stepie=0 must keep the interrupt from firing.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-006-C
      bins masked_irq_pending = {1};

      // stepie=1, nothing pending: behaves as a normal step.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-007-C
      bins unmasked_no_irq = {2};

      // The interrupt is taken; dpc is the handler entry.
      // spec: Sdext.html#csr-dcsr
      // testplan: SSTEP-007-C
      bins unmasked_irq_pending = {3};
    }

    // The step is a D->M->D round trip; the return leg is the property under
    // test.
    // transition coverage
    cp_step_transition: coverpoint hart_mode {
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
    cp_haltreq_during_step: coverpoint haltreq_asserted_during_step_window {
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
    cp_prv_at_step: coverpoint dcsr.prv at the step {
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

    // Single steps can drift: an off-by-one in dpc only shows after several.
    // Boundaries at one, a handful, and enough to cross a loop back-edge.
    cp_consecutive_steps: coverpoint consecutive_steps_without_resume {
      // The basic case.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-001-S
      bins single = {1};

      // Enough to expose drift; 14 observed clean.
      // spec: Sdext.html#stepbit
      // testplan: SSTEP-013-C
      bins several = [2:16];

      // Stepping past a backward branch, where dpc must follow the branch.
      // spec: Sdext.html#stepbit
      bins across_loop_backedge = {32};
    }

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

    // Interrupt masking interacts with instruction class, and the stalling
    // case is where it matters most: a wfi stepped with stepie=1 and an
    // interrupt pending may legitimately complete via the interrupt, while
    // the same wfi with stepie=0 must be treated as a nop. Testing the wfi
    // only at one stepie setting leaves the harder half unmeasured.
    x_class_x_stepie: cross cp_stepped_class, cp_stepie_x_irq {
      // Zawrs absent on this DUT; retained so a Zawrs DUT is measured across
      // both stepie settings.
      ignore_bins ig = binsof(cp_stepped_class.wrs);
    }

    // Drift accumulates differently per class. Stepping repeatedly across a
    // loop back-edge exercises taken branches many times, where an off-by-one
    // in dpc compounds rather than cancelling.
    x_class_x_consecutive: cross cp_stepped_class, cp_consecutive_steps {
      // One step cannot accumulate drift; the single case is owned by the
      // per-class bins directly.
      ignore_bins ig = binsof(cp_consecutive_steps.single);
    }

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

    // This mechanism INVERTS two of dcsr.step's guarantees, and conflating
    // the two is the mistake this covergroup exists to prevent.
    cp_native_step_guarantees: coverpoint native_step_observed_behaviour {
      // count=1 fires after exactly one instruction.
      // spec: Sdext.html#stepicount
      // testplan: NSTEP-001-C
      bins one_instruction_retired = {0};

      // icount gives NO interrupt masking — the opposite of dcsr.stepie.
      // spec: Sdext.html#stepicount
      // testplan: NSTEP-002-C
      bins interrupt_fired = {1};

      // The spec's prescribed workaround: the debugger edits mstatus itself.
      // spec: Sdext.html#stepicount
      // testplan: NSTEP-003-C
      bins interrupt_masked_via_mstatus = {2};

      // wfi is NOT treated specially here and may stall indefinitely — the
      // inverse of cg_step_external.cp_stepped_class.wfi.
      // spec: Sdext.html#stepicount
      // testplan: NSTEP-005-C
      bins wfi_stalled = {3};

      // The spec warns instructions reading mstatus need special handling;
      // this bin quantifies the exposure.
      // spec: Sdext.html#stepicount
      // testplan: NSTEP-004-C
      bins mstatus_read_observed_debugger_value = {4};
    }

    // Appendix A flags same-privilege stepping as materially harder than
    // stepping a less-privileged program.
    cp_native_step_privilege: coverpoint {stub_privilege, target_privilege} {
      // The straightforward case.
      // spec: debugger_implementation.html#nativestep
      // testplan: NSTEP-007-V
      bins m_stub_u_target = {0};

      // Spec calls this 'more complicated, depending on what other debug
      // features are implemented'.
      // spec: debugger_implementation.html#nativestep
      // testplan: NSTEP-006-C
      bins same_privilege = {1};
    }

    // The privilege relationship changes which limitations bite. Stepping a
    // less-privileged program lets the M-mode stub edit mstatus freely;
    // stepping code at the stub's own privilege makes that edit visible to
    // the program being debugged, which is precisely the case Appendix A
    // calls more complicated.
    x_guarantee_x_privilege: cross cp_native_step_guarantees, cp_native_step_privilege;

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
    cp_cmdtype: coverpoint command.cmdtype {
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
      bins reserved_cmdtype = {3};
    }

    // The register number space has architecturally distinct regions, and the
    // unimplemented region is the one that must fail cleanly.
    cp_regno_class: coverpoint regno_class {
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
    cp_aarsize: coverpoint command.aarsize {
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
      bins reserved_size = {0, 1, 5, 6, 7};
    }

    // These flags compose, and the combinations that matter are transfer with
    // and without postexec, and postexec with transfer=0 — the last is how a
    // debugger runs the program buffer without touching a register.
    cp_command_flags: coverpoint {transfer, postexec, aarpostincrement, write} {
      // Plain register read.
      // spec: debug_module.html#access-register
      // testplan: AC-001-S
      bins transfer_read = {8};

      // Plain register write.
      // spec: debug_module.html#access-register
      // testplan: AC-002-S
      bins transfer_write = {12};

      // Transfer then run the program buffer.
      // spec: debug_module.html#access-register
      // testplan: AC-010-S
      bins transfer_and_postexec = {10};

      // transfer=0: run the buffer with no register transfer.
      // spec: debug_module.html#access-register
      // testplan: AC-011-S
      bins postexec_only = {2};

      // regno advances after the access — how block register dumps work.
      // spec: debug_module.html#access-register
      // testplan: AC-012-S
      bins postincrement = {9};
    }

    // Every error code drives different debugger recovery. A debugger that
    // cannot distinguish busy from halt/resume retries the wrong thing.
    cp_cmderr: coverpoint abstractcs.cmderr {
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
    cp_busy_observed: coverpoint abstractcs.busy_seen_set {
      // The debugger actually polled through a busy period.
      // spec: debug_module.html#abstractcs
      // testplan: AC-001-C
      bins busy_observed = {1};
    }

    // The protocol is ordered: data, command, poll, result. Order violations
    // are a different defect class from wrong values.
    // sequence coverage
    cp_command_sequence: coverpoint abstract_command_phase {
      // The prescribed order.
      // spec: debug_module.html#abstract-commands
      // testplan: AC-002-S
      bins write_read_sequence = (WRITE_DATA => WRITE_CMD => POLL_BUSY => READ_DATA);

      // Error then recovery — proves the DM is usable after a failure.
      // spec: debug_module.html#abstractcs
      // testplan: AC-009-C
      bins recovery_sequence = (CMD_FAIL => CLEAR_CMDERR => CMD_OK);
    }

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

    // A command that both transfers and runs the program buffer can fail in
    // either phase, and the debugger must be able to tell which. postexec
    // with transfer=0 failing means the buffer faulted; a transfer failing
    // means the register access did. Same cmderr, different cause.
    x_flags_x_cmderr: cross cp_command_flags, cp_cmderr {
      // cmderr=5 requires abstract memory access, absent on this DUT;
      // retained so a DUT implementing cmdtype=2 is measured.
      ignore_bins ig = binsof(cp_cmderr.bus);
    }

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
    cp_progbuf_fill: coverpoint words_written_to_progbuf {
      // Minimum useful buffer.
      // spec: debug_module.html#program-buffer
      // testplan: PB-001-S
      bins single_word = {1};

      // Ordinary use.
      // spec: debug_module.html#abstractcs
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

    // How execution ended is the behaviour; each outcome leaves the DM in a
    // different state and the debugger must be able to continue from all.
    cp_progbuf_outcome: coverpoint program_buffer_termination {
      // The debugger's own ebreak returns control.
      // spec: debug_module.html#program-buffer
      // testplan: PB-001-C
      bins explicit_ebreak = {0};

      // impebreak=1: no explicit ebreak needed.
      // spec: debug_module.html#dmstatus
      // testplan: PB-004-C
      bins implicit_ebreak = {1};

      // A faulting instruction: cmderr=3, hart stays usable.
      // spec: debug_module.html#program-buffer
      // testplan: PB-005-C
      bins exception = {2};

      // An illegal encoding.
      // spec: debug_module.html#program-buffer
      // testplan: PB-006-C
      bins illegal_instruction = {3};

      // A jump beyond the buffer — the spec permits treating it as illegal;
      // record what this DUT does.
      // spec: debug_module.html#program-buffer
      // testplan: PB-007-C
      bins control_transfer_out = {4};
    }

    // The buffer exists to reach what abstract commands cannot; each use must
    // be exercised.
    cp_progbuf_operation: coverpoint what_the_buffer_did {
      // Reach a register with no abstract encoding.
      // spec: debug_module.html#program-buffer
      // testplan: PB-002-C
      bins register_access = {0};

      // Load from the hart's point of view, honouring its MMU and PMP.
      // spec: debug_module.html#program-buffer
      // testplan: PB-002-S
      bins memory_read = {1};

      // Store from the hart's point of view.
      // spec: debug_module.html#program-buffer
      bins memory_write = {2};

      // How dcsr is written during a step setup.
      // spec: debug_module.html#program-buffer
      // testplan: RAP-020-S
      bins csr_access = {3};
    }

    // Buffer contents must persist; a DM that clears on execute breaks
    // repeated use.
    // transition coverage
    cp_progbuf_reuse: coverpoint progbuf_execution_count {
      // Second run behaves identically.
      // spec: debug_module.html#program-buffer
      // testplan: PB-008-C
      bins rerun_without_rewrite = (EXECUTED => EXECUTED);
    }

    // An exception during a memory write leaves different state from one
    // during a register read -- a partially-completed store versus a clean
    // abort. The recovery path a debugger needs differs, so the outcome must
    // be measured per operation rather than in aggregate.
    x_outcome_x_operation: cross cp_progbuf_outcome, cp_progbuf_operation;

    // The last buffer slot is where off-by-one errors live. An exception
    // raised by the final word of a full buffer, and implicit ebreak on a
    // full buffer, are the two boundary interactions worth naming.
    x_fill_x_outcome: cross cp_progbuf_fill, cp_progbuf_outcome {
      // Writes past progbufsize are ignored, so no execution outcome follows;
      // DIS-005 owns the out-of-range write itself.
      ignore_bins ig = binsof(cp_progbuf_fill.overflow);
    }

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
    cp_sbaccess_size: coverpoint sbcs.sbaccess {
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
    cp_sberror: coverpoint sbcs.sberror {
      // Success.
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-C
      bins none = {0};

      // The bus did not respond.
      // spec: debug_module.html#sbcs
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
      bins other = {7};
    }

    // These three compose into the block-transfer modes a debugger actually
    // uses. Autoincrement with readondata is how a memory dump works, and it
    // is a different path from a single addressed read.
    cp_sb_trigger_mode: coverpoint {sbreadonaddr, sbreadondata, sbautoincrement} {
      // Explicit address then explicit data access.
      // spec: debug_module.html#sbcs
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

    // Regions are chosen by what the bus does with them, not by equal
    // division: mapped RAM, the boundary at the top of RAM, and an unmapped
    // address that must produce sberror=2.
    cp_sb_address_region: coverpoint sbaddress {
      // First byte of DRAM (0x8000_0000).
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-S
      bins ram_base = {2147483648};

      // Ordinary mapped memory.
      // spec: debug_module.html#sbcs
      bins ram_body = [2147483649:2415919103];

      // Last mapped address — the boundary before the decode fails.
      // spec: debug_module.html#sbcs
      bins ram_top = {2415919104};

      // Must produce sberror=2 rather than hanging the bus.
      // spec: debug_module.html#sbcs
      // testplan: SBA-008-S
      bins unmapped = {0};
    }

    // Alignment has no meaning on its own -- address 4 is aligned for 32-bit
    // and misaligned for 64-bit. Sampled as a relationship, not an address,
    // so the cross with size is expressible.
    cp_sb_alignment: coverpoint sbaddress alignment relative to sbaccess size {
      // Address is a multiple of the access size.
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-S
      bins aligned = {0};

      // One byte past an aligned address -- the first illegal offset.
      // spec: debug_module.html#sbcs
      // testplan: SBA-007-S
      bins misaligned_by_1 = {1};

      // Half the access size: legal for a narrower size, illegal for this
      // one.
      // spec: debug_module.html#sbcs
      // testplan: SBA-007-S
      bins misaligned_half = {2};
    }

    // Non-intrusive access is the main reason SBA exists; if it is only ever
    // exercised on a halted hart, that property is untested.
    cp_sb_concurrency: coverpoint sba_while_hart_running {
      // Hart must continue undisturbed throughout.
      // spec: debug_module.html#sbcs
      // testplan: SBA-010-C
      bins hart_running = {1};

      // The easy case.
      // spec: debug_module.html#sbcs
      // testplan: SBA-001-S
      bins hart_halted = {0};
    }

    // Accessing while busy must be reported, not silently dropped or applied.
    cp_sbbusyerror: coverpoint access_while_sbbusy {
      // sbbusyerror set; the in-flight transfer unaffected.
      // spec: debug_module.html#sbcs
      // testplan: RAP-043-C
      bins flagged = {1};
    }

    // Alignment is only meaningful relative to the access size: address 4 is
    // aligned for 32-bit and misaligned for 64-bit. Neither coverpoint alone
    // can express that, and this is where sberror=3 actually comes from.
    x_size_x_alignment: cross cp_sbaccess_size, cp_sb_alignment {
      // Every address is aligned for an 8-bit access; the cells carry no
      // information.
      ignore_bins ig = binsof(cp_sbaccess_size.size8);
    }

    // An error mid-block-transfer is the interesting case: with autoincrement
    // the address has already advanced, so the debugger must be able to tell
    // which word failed. A single-access error does not have that problem.
    x_mode_x_error: cross cp_sb_trigger_mode, cp_sberror;

    // A wide access near the top of mapped memory can straddle the boundary
    // while a narrow one at the same address does not. The ram_top cell is
    // only reachable as a size/region pair.
    x_size_x_region: cross cp_sbaccess_size, cp_sb_address_region;

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
    cp_trigger_type: coverpoint tdata1.type {
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

    // The three access classes take different paths through the core, and a
    // trigger that works on execute may not on store.
    cp_match_event: coverpoint {execute, load, store} {
      // Instruction fetch at an address.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-003-S
      bins execute = {4};

      // Data read at an address.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-004-S
      bins load = {1};

      // Data write at an address.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-005-S
      bins store = {2};

      // Both set — a watchpoint on any access.
      // spec: Sdtrig.html#mcontrol6
      bins load_and_store = {3};
    }

    // A trigger enabled only for U must not fire in M. The negative case is
    // the one that catches a mis-decoded enable.
    cp_trigger_privilege: coverpoint {m, s, u} enable bits {
      // Fires in M only.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-012-V
      bins m_only = {4};

      // Fires in S only.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-012-V
      bins s_only = {2};

      // Fires in U only.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-012-V
      bins u_only = {1};

      // Fires anywhere.
      // spec: Sdtrig.html#mcontrol6
      bins all_privileges = {7};

      // Configured but disabled: must never fire.
      // spec: Sdtrig.html#mcontrol6
      // testplan: TRIG-006-C
      bins none_enabled = {0};
    }

    // The spec requires a debugger to read back what it writes to tdata
    // registers; enumeration depends on the out-of-range behaviour.
    cp_tselect_probe: coverpoint tselect_write_vs_readback {
      // Reads back what was written.
      // spec: Sdtrig.html#enumeration
      // testplan: TRIG-001-C
      bins in_range = {0};

      // Reads back a legal index — how the count is discovered.
      // spec: Sdtrig.html
      // testplan: TRIG-002-C
      bins out_of_range = {1};
    }

    // The spec restricts trigger updates from a running hart; both contexts
    // must be exercised.
    cp_trigger_update_context: coverpoint tdata_written_while {
      // The normal configuration path.
      // spec: Sdtrig.html
      // testplan: TRIG-001-S
      bins hart_halted = {0};

      // Restricted; verify the DUT's behaviour matches.
      // spec: Sdtrig.html
      // testplan: TRIG-007-C
      bins hart_running = {1};
    }

    // The privilege filter is applied per access class, and a core can get it
    // right for execute and wrong for load. This cross is the whole point of
    // the trigger privilege bits.
    x_match_x_privilege: cross cp_match_event, cp_trigger_privilege {
      // A disabled trigger fires for no access class; the cells are
      // unreachable by construction, and TRIG-006-C owns the disabled case.
      ignore_bins ig = binsof(cp_trigger_privilege.none_enabled);
    }

    // Each trigger type applies the privilege filter through its own matching
    // logic, so a core can honour it for mcontrol6 and ignore it for icount
    // or etrigger. Per-type privilege filtering is not implied by getting it
    // right once.
    x_type_x_privilege: cross cp_trigger_type, cp_trigger_privilege {
      // An unconfigured trigger has no privilege fields in effect.
      ignore_bins ig = binsof(cp_trigger_type.none);
      // v0.13 encoding; this DUT reports v1.0 and implements mcontrol6.
      // Retained so a v0.13 DUT is measured.
      ignore_bins ig = binsof(cp_trigger_type.mcontrol);
    }

    // The spec restricts trigger updates from a running hart. Whether a DUT
    // enforces that can differ per trigger type, since each has a different
    // write path into tdata1.
    x_type_x_update_context: cross cp_trigger_type, cp_trigger_update_context;

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
    cp_group_config: coverpoint {dmcs2.grouptype, hgselect} {
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

    // Propagation is the feature; configuration without propagation proves
    // nothing.
    cp_group_propagation: coverpoint group_halt_propagated {
      // Halting one member halts the group.
      // spec: debug_module.html#halt-groups
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins hart_to_hart = {0};

      // An external trigger halts the group.
      // spec: debug_module.html#dmcs2
      // testplan: HG-003-C
      bins external_in = {1};

      // A group halt drives the outgoing trigger.
      // spec: debug_module.html#dmcs2
      // testplan: HG-004-C
      bins external_out = {2};
    }

    // Halt groups and resume groups propagate through separate logic, and the
    // external trigger is a third path. Configuring one and observing
    // propagation on another is the failure this cross catches.
    x_config_x_propagation: cross cp_group_config, cp_group_propagation {
      // Requires more than one hart. Unreachable on this DUT; retained so a
      // multi-hart DUT is measured, since this is the primary purpose of halt
      // groups.
      ignore_bins ig = binsof(cp_group_propagation.hart_to_hart);
    }

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
    cp_auth_state: coverpoint {authenticated, authbusy} {
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

    // The spec names exactly which registers stay reachable before
    // authentication. Both the permitted and the denied set must be
    // exercised, or the gate is only half tested.
    cp_auth_permitted_register: coverpoint register_class_accessed_while_unauthenticated {
      // Must remain readable -- it carries authenticated itself.
      // spec: debug_module.html#authdata
      // testplan: RAP-041-C
      bins dmstatus = {0};

      // Must remain accessible so the DM can be activated.
      // spec: debug_module.html#authdata
      bins dmcontrol = {1};

      // The challenge/response channel itself.
      // spec: debug_module.html#authdata
      bins authdata = {2};

      // Any other DM register: must be inaccessible until authenticated.
      // spec: debug_module.html#authdata
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins gated_register = {3};
    }

    // Authentication is a gate, so the behaviour is the pairing: which
    // registers remain reachable in which auth state. dmstatus, dmcontrol and
    // authdata must stay readable while unauthenticated; everything else must
    // not.
    x_auth_x_gated_access: cross cp_auth_state, cp_auth_permitted_register {
      // With no authentication implemented every register is reachable, so
      // the gating cells carry no information on this DUT. Retained so a DUT
      // implementing authentication is measured.
      ignore_bins ig = binsof(cp_auth_state.no_auth_implemented);
    }

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

    // Each access type has a distinct conformance rule, and the model must
    // record that every type was actually exercised rather than assumed.
    cp_access_type: coverpoint field_access_type {
      // Writes must not change it.
      // spec: introduction.html#1-1-3-3-register-definition-format
      // testplan: RAP-001-C
      bins read_only = {0};

      // Round-trips exactly.
      // spec: introduction.html#1-1-3-3-register-definition-format
      // testplan: RAP-002-C
      bins read_write = {1};

      // Illegal writes legalise deterministically.
      // spec: introduction.html#1-1-3-3-register-definition-format
      // testplan: RAP-003-C
      bins warl = {2};

      // Reads zero regardless of what was written — read-back only, not
      // storage.
      // spec: debug_module.html#command
      // testplan: RAP-004-C
      bins warz = {3};

      // Writing 1 acts, writing 0 does nothing, reads return 0.
      // spec: debug_module.html#dmcontrol
      // testplan: RAP-005-C
      bins w1 = {4};

      // Cleared only by writing 1s.
      // spec: debug_module.html#abstractcs
      // testplan: RAP-006-C
      bins w1c = {5};

      // Reads 0 always.
      // spec: debug_module.html
      // testplan: RAP-008-C
      bins reserved = {6};
    }

    // This is the dimension most coverage models omit entirely. A register's
    // permissions differ by who is asking, and a model that only samples DMI
    // cannot see it.
    cp_interface: coverpoint originating_interface {
      // The debugger's own path.
      // spec: dtm.html#dmi
      // testplan: RAP-001-S
      bins dmi = {0};

      // The hart reading/writing its own debug CSRs.
      // spec: Sdext.html#csr-dcsr
      // testplan: RAP-020-S
      bins hart_csr = {1};

      // The hart reaching the data window or Debug ROM as memory.
      // spec: debug_module.html#hartinfo
      // testplan: RAP-026-C
      bins hart_load_store = {2};

      // SBA, which bypasses hart privilege and translation.
      // spec: debug_module.html#sbcs
      // testplan: RAP-028-C
      bins system_bus = {3};

      // The hart executing debugger-supplied instructions.
      // spec: debug_module.html#program-buffer
      // testplan: RAP-024-S
      bins program_buffer = {4};
    }

    // Permissions differ by which class of storage is reached, and the class
    // determines which interfaces can reach it at all. The second leg of
    // x_interface_x_register.
    cp_register_class: coverpoint register_class_being_accessed {
      // dmcontrol, dmstatus, abstractcs and the rest -- DMI only.
      // spec: debug_module.html
      // testplan: RAP-001-S
      bins dm_register = {0};

      // dcsr/dpc/dscratch -- hart CSR instruction, or DMI via abstract
      // command.
      // spec: Sdext.html#csr-dcsr
      // testplan: RAP-020-S
      bins debug_csr = {1};

      // Writable over DMI, executable but not writable by the hart.
      // spec: debug_module.html#program-buffer
      // testplan: RAP-024-S
      bins progbuf = {2};

      // data0..N, reachable as memory by the hart when dataaccess=1.
      // spec: debug_module.html#hartinfo
      // testplan: RAP-026-C
      bins data_window = {3};

      // Reachable by SBA and by a hart load/store, with different
      // permissions.
      // spec: debug_module.html#sbcs
      // testplan: RAP-027-S
      bins system_memory = {4};

      // Executable by the hart, must not be writable.
      // spec: debug_module.html
      // testplan: RAP-030-S
      bins debug_rom = {5};
    }

    // Accessibility depends on DM state as well as on access type, and each
    // gating state rejects differently.
    cp_gating_state: coverpoint dm_gating_state_at_access {
      // Baseline.
      // spec: debug_module.html
      // testplan: RAP-002-S
      bins normal = {0};

      // dmactive=0: only dmcontrol is meaningful.
      // spec: debug_module.html#dmcontrol
      // testplan: RAP-040-C
      bins dm_inactive = {1};

      // Only dmcontrol R/W and ndmresetpending are supported; the rest is
      // UNSPECIFIED.
      // spec: debug_module.html#reset
      // testplan: RST-054-C
      bins in_ndmreset = {2};

      // cmderr=1 on command or data access.
      // spec: debug_module.html#abstractcs
      // testplan: RAP-042-C
      bins abstract_busy = {3};

      // sbbusyerror on sbaddress/sbdata access.
      // spec: debug_module.html#sbcs
      // testplan: RAP-043-C
      bins sb_busy = {4};

      // Most registers inaccessible.
      // spec: debug_module.html#authdata
      // NOT REACHABLE on this DUT -- kept so another DUT is measured
      bins unauthenticated = {5};
    }

    // The whole point of §2.2: the same register reached from two interfaces
    // must honour two different permissions. dcsr from the hart versus over
    // DMI, progbuf from DMI versus from the executing hart, and memory via
    // SBA versus via a hart load are the three that matter.
    x_interface_x_register: cross cp_interface, cp_register_class {
      // SBA reaches system memory, not DM registers; the combination does not
      // exist.
      ignore_bins ig = binsof(cp_interface.system_bus && cp_register_class.dm_register);
    }

    // An access type is declared per field, but enforced per interface. A
    // field that is R/W over DMI may be read-only to the hart, and a DM that
    // enforces the type only on its DMI decode passes cp_access_type while
    // being wrong everywhere else.
    x_interface_x_access_type: cross cp_interface, cp_access_type;

    // Gating applies unevenly by class: dmcontrol stays reachable with
    // dmactive=0 while other DM registers do not, and debug CSRs become
    // unreachable when the hart is not halted regardless of DM state.
    x_class_x_gating: cross cp_register_class, cp_gating_state;

  endgroup : cg_register_access

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

