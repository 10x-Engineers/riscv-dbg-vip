// ══════════════════════════════════════════════════════════════════════════════
// covergroups.sv — Functional coverage of the dmcontrol/dmstatus run-control slice
//
// The SystemVerilog twin of pydebug/model/coverage.py. Both subscribe to the same
// DMI transaction stream and define the same bins, for the same spec reasons:
// Python collects when the suite drives the mock or real hardware over OpenOCD, this
// collects when the suite drives RTL in simulation. Keeping the bin *names* aligned
// across the two is what lets a UVM run and a Python run be talked about as one
// coverage number rather than two unrelated ones.
//
// Spec references are to the RISC-V Debug Specification:
//   #3.2    Reset Control
//   #3.5    Run Control
//   #3.14.1 dmstatus  (DMI 0x11)
//   #3.14.2 dmcontrol (DMI 0x10)
//
// Scope: dmcontrol/dmstatus run control only — halt, resume, reset, halt-on-reset,
// hart selection. Abstract commands, Program Buffer, SBA, triggers and
// authentication are later slices and are deliberately not binned here.
//
// Register addresses come from dm_defines_pkg (fully qualified, so that this file
// needs no import line added to the shared debug_pkg.sv). Field bit positions are
// declared below because dm_defines_pkg carries addresses only — they are taken
// from the spec's own machine-readable register definitions
// (riscv/riscv-debug-spec, xml/dm_registers.xml) and match registers.py field for
// field, so the two models cannot silently disagree about where a bit lives.
// ══════════════════════════════════════════════════════════════════════════════
class debug_coverage extends uvm_subscriber #(jtag_txn_c);
    `uvm_component_utils(debug_coverage)

    // ── Register addresses (reused from dm_defines_pkg, not redefined) ────────
    localparam logic [6:0] ADDR_DMCONTROL = dm_defines_pkg::DM_ADDR_DMCONTROL;
    localparam logic [6:0] ADDR_DMSTATUS  = dm_defines_pkg::DM_ADDR_DMSTATUS;

    // ── dmcontrol field bit positions (#3.14.2) ───────────────────────────────
    localparam int DMC_HALTREQ         = 31;
    localparam int DMC_RESUMEREQ       = 30;
    localparam int DMC_HARTRESET       = 29;
    localparam int DMC_ACKHAVERESET    = 28;
    localparam int DMC_ACKUNAVAIL      = 27;
    localparam int DMC_HASEL           = 26;
    localparam int DMC_HARTSELLO_LSB   = 16;  // hartsello = bits 25:16
    localparam int DMC_HARTSELHI_LSB   = 6;   // hartselhi = bits 15:6
    localparam int DMC_SETKEEPALIVE    = 5;
    localparam int DMC_CLRKEEPALIVE    = 4;
    localparam int DMC_SETRESETHALTREQ = 3;
    localparam int DMC_CLRRESETHALTREQ = 2;
    localparam int DMC_NDMRESET        = 1;
    localparam int DMC_DMACTIVE        = 0;

    // ── dmstatus field bit positions (#3.14.1) ────────────────────────────────
    localparam int DMS_NDMRESETPENDING = 24;
    localparam int DMS_STICKYUNAVAIL   = 23;
    localparam int DMS_IMPEBREAK       = 22;
    localparam int DMS_ALLHAVERESET    = 19;
    localparam int DMS_ANYHAVERESET    = 18;
    localparam int DMS_ALLRESUMEACK    = 17;
    localparam int DMS_ANYRESUMEACK    = 16;
    localparam int DMS_ALLNONEXISTENT  = 15;
    localparam int DMS_ANYNONEXISTENT  = 14;
    localparam int DMS_ALLUNAVAIL      = 13;
    localparam int DMS_ANYUNAVAIL      = 12;
    localparam int DMS_ALLRUNNING      = 11;
    localparam int DMS_ANYRUNNING      = 10;
    localparam int DMS_ALLHALTED       = 9;
    localparam int DMS_ANYHALTED       = 8;
    localparam int DMS_AUTHENTICATED   = 7;
    localparam int DMS_AUTHBUSY        = 6;
    localparam int DMS_HASRESETHALTREQ = 5;
    localparam int DMS_CONFSTRPTRVALID = 4;
    // version = bits 3:0

    // dmstatus.version encodings (#3.14.1 version)
    localparam logic [3:0] VERSION_NONE   = 4'd0;
    localparam logic [3:0] VERSION_0_11   = 4'd1;
    localparam logic [3:0] VERSION_0_13   = 4'd2;
    localparam logic [3:0] VERSION_1_0    = 4'd3;
    localparam logic [3:0] VERSION_CUSTOM = 4'd15;

    // ── Computed sample values ────────────────────────────────────────────────
    //
    // These enums exist because several architectural situations are not any one
    // field of any one transaction: they are relations between a transaction and
    // what came before it. Computing them in write() and binning the result keeps
    // the covergroups declarative and, more importantly, keeps them identical in
    // meaning to the Python model's crosses.

    // Selected-hart state as observed through one dmstatus read (#3.5: of the DM's
    // 4 conceptual per-hart bits, "the state of the other bits cannot be observed
    // directly" — only these are visible).
    typedef enum {
        ST_HALTED,
        ST_RUNNING,
        ST_IN_RESET,     // neither halted nor running: reset in progress (#3.2)
        ST_UNAVAIL,
        ST_NONEXISTENT,
        ST_UNKNOWN       // no dmstatus read yet; nothing may be inferred
    } hart_state_e;

    // Hart state transitions. Binned as a computed enum rather than as covergroup
    // transition bins (`a => b`) on purpose: transition bins pair each sample with
    // the previous sample of that coverpoint, which would stitch a false transition
    // across a change of hartsel — two different harts observed in sequence would
    // look like one hart moving. Computing the transition lets us refuse to sample
    // at all when the selection moved.
    typedef enum {
        TR_RUNNING_TO_HALTED,
        TR_HALTED_TO_RUNNING,
        TR_RUNNING_TO_IN_RESET,
        TR_HALTED_TO_IN_RESET,
        TR_IN_RESET_TO_RUNNING,
        TR_IN_RESET_TO_HALTED
    } hart_transition_e;

    // hartsel classified against the implemented hart count, which no transaction
    // carries — it is DUT configuration, supplied via the config_db.
    typedef enum {
        HS_ZERO,          // hart 0: the reset value (#3.14.2 hartsello/hartselhi)
        HS_MAX_IMPL,      // the highest implemented hart index
        HS_NONEXISTENT,   // hartsel >= num_harts (#3.14.1 anynonexistent)
        HS_OTHER
    } hartsel_class_e;

    // resumereq crossed with the hart's state at the time of the write (#3.5).
    typedef enum {
        RQ_WHEN_HALTED,
        RQ_WHEN_RUNNING,
        RQ_WHEN_IN_RESET,
        RQ_NONE           // no resumereq in this write, or state not yet known
    } resumereq_ctx_e;

    // havereset crossed with ackhavereset (#3.2, #3.14.2 ackhavereset).
    typedef enum {
        HR_ACK_WHEN_SET,    // the meaningful ack
        HR_ACK_WHEN_CLEAR,  // ack with nothing to clear: must be a harmless no-op
        HR_NOACK_WHEN_SET,  // proves havereset is sticky (#3.2)
        HR_NONE
    } havereset_ctx_e;

    // ndmreset edges crossed with the halt-on-reset request shadow (#3.5, #3.2).
    typedef enum {
        ND_ASSERT_RHR0,
        ND_ASSERT_RHR1,
        ND_DEASSERT_RHR0,
        ND_DEASSERT_RHR1,
        ND_NO_EDGE          // ndmreset held at its previous level: not a reset event
    } ndmreset_ctx_e;

    // ── Sampled values (covergroups read these; write() sets them) ────────────
    hart_state_e      cur_state       = ST_UNKNOWN;
    hart_transition_e cur_transition;
    hartsel_class_e   cur_hartsel_cls;
    resumereq_ctx_e   cur_resumereq_ctx;
    havereset_ctx_e   cur_havereset_ctx;
    ndmreset_ctx_e    cur_ndmreset_ctx;
    int unsigned      cur_mutex_count;

    // ── Inferred state, rebuilt from the bus exactly as a debugger would ──────
    int unsigned num_harts       = 1;   // DUT config, from the config_db
    logic [19:0] hartsel         = '0;  // as last written (#3.14.2: resets to 0)
    logic [19:0] state_hartsel   = '0;  // hartsel in force when cur_state was read
    bit          state_valid     = 0;
    bit          havereset       = 0;   // anyhavereset as of the last dmstatus read
    bit          havereset_valid = 0;
    bit          ndmreset        = 0;   // dmcontrol.ndmreset as last written
    // Shadow of the per-hart halt-on-reset request bit, keyed by hartsel. Spec
    // #3.14.2 resethaltreq: "an optional internal bit of per-hart state that cannot
    // be read, but can be written with setresethaltreq and clrresethaltreq" — so
    // the only way to know its value is to remember what we wrote.
    bit reset_haltreq [logic [19:0]];

    // ══════════════════════════════════════════════════════════════════════════
    // Covergroup: DMI access shape
    // ══════════════════════════════════════════════════════════════════════════
    covergroup cg_dmi_access with function sample(
        logic [6:0] addr, logic [1:0] op, logic [1:0] status
    );
        option.per_instance = 1;
        option.comment = "Which run-control registers were accessed, how, and with what DMI status";

        cp_addr : coverpoint addr {
            bins dmcontrol = {ADDR_DMCONTROL};
            bins dmstatus  = {ADDR_DMSTATUS};
            // Addresses outside the slice are intentionally unbinned: this model has
            // no business claiming to measure abstractcs, sbcs or progbuf.
        }

        cp_op : coverpoint op {
            bins nop   = {dm_defines_pkg::DMI_NOP};
            bins read  = {dm_defines_pkg::DMI_READ};
            bins write = {dm_defines_pkg::DMI_WRITE};
        }

        cp_status : coverpoint status {
            bins success = {dm_defines_pkg::DMI_STAT_SUCCESS};
            bins failed  = {dm_defines_pkg::DMI_STAT_FAILED};
            bins busy    = {dm_defines_pkg::DMI_STAT_BUSY};
        }

        x_addr_op : cross cp_addr, cp_op {
            // Every dmstatus field is R (#3.14.1), so a write to it has no
            // spec-defined behaviour — there is no architectural situation to
            // cover. illegal_bins rather than ignore_bins: if stimulus ever does
            // this, it is a bug in the stimulus and should fail loudly rather than
            // pass as unbinned traffic. Mirrors the Python model's
            // `dmi_access.write:dmstatus` exclusion.
            illegal_bins dmstatus_write = binsof(cp_addr.dmstatus) && binsof(cp_op.write);
            // A NOP carries no address; crossing it with one would invent an access.
            ignore_bins nop_x_addr = binsof(cp_op.nop);
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    // Covergroup: dmcontrol writes (#3.14.2)
    //
    // dmcontrol is binned from the *written* word rather than a read-back because
    // most of its fields are W1/WARZ and read back as 0 by definition. A
    // read-back-sampled model could never hit their 1 bins at all, and would report
    // a comfortable, meaningless 100%.
    // ══════════════════════════════════════════════════════════════════════════
    covergroup cg_dmcontrol_write with function sample(logic [31:0] w);
        option.per_instance = 1;
        option.comment = "Decoded dmcontrol write data (#3.14.2)";

        cp_haltreq         : coverpoint w[DMC_HALTREQ]         { bins zero = {0}; bins one = {1}; }
        cp_resumereq       : coverpoint w[DMC_RESUMEREQ]       { bins zero = {0}; bins one = {1}; }
        cp_hartreset       : coverpoint w[DMC_HARTRESET]       { bins zero = {0}; bins one = {1}; }
        cp_ackhavereset    : coverpoint w[DMC_ACKHAVERESET]    { bins zero = {0}; bins one = {1}; }
        cp_ackunavail      : coverpoint w[DMC_ACKUNAVAIL]      { bins zero = {0}; bins one = {1}; }
        // hasel=1 is reachable even where the hart array mask register is absent:
        // it records the debugger's discovery write, not whether multiple harts
        // actually got selected (#3.14.2 hasel: "A debugger which wishes to use the
        // hart array mask register feature should set this bit and read back to see
        // if the functionality is supported"). What an absent mask register makes
        // unreachable is the all*!=any* aggregate, excluded in cg_dmstatus_read.
        cp_hasel           : coverpoint w[DMC_HASEL]           { bins zero = {0}; bins one = {1}; }
        cp_setkeepalive    : coverpoint w[DMC_SETKEEPALIVE]    { bins zero = {0}; bins one = {1}; }
        cp_clrkeepalive    : coverpoint w[DMC_CLRKEEPALIVE]    { bins zero = {0}; bins one = {1}; }
        cp_setresethaltreq : coverpoint w[DMC_SETRESETHALTREQ] { bins zero = {0}; bins one = {1}; }
        cp_clrresethaltreq : coverpoint w[DMC_CLRRESETHALTREQ] { bins zero = {0}; bins one = {1}; }
        cp_ndmreset        : coverpoint w[DMC_NDMRESET]        { bins zero = {0}; bins one = {1}; }
        // dmactive=0 is the DM reset: "The module's state ... takes its reset
        // values" (#3.14.2 dmactive=0). It is a distinct architectural event, not
        // merely the absence of activation.
        cp_dmactive        : coverpoint w[DMC_DMACTIVE]        { bins zero = {0}; bins one = {1}; }

        // hartsel is one logical 20-bit index assembled from two disjoint fields
        // (#3.14.2 hartsel). Binning the assembled value rather than the two fields
        // separately is the point: hartselhi only matters *because* it is the high
        // half, and a per-field bin would report it covered by a write that never
        // selected a hart above 1023.
        cp_hartsel : coverpoint {w[DMC_HARTSELHI_LSB +: 10], w[DMC_HARTSELLO_LSB +: 10]} {
            bins zero              = {20'h0};
            bins nonzero           = {[20'h1 : 20'hFFFFF]};
            bins hartselhi_nonzero = {[20'h400 : 20'hFFFFF]};
            // The HARTSELLEN discovery write. Spec: "A debugger should discover
            // HARTSELLEN by writing all ones to hartsel (assuming the maximum size)
            // and reading back the value to see which bits were actually set."
            bins all_ones          = {20'hFFFFF};
        }

        // hartsel against the implemented hart count (DUT config, not on the bus).
        cp_hartsel_cls : coverpoint cur_hartsel_cls {
            bins zero        = {HS_ZERO};
            bins max_impl    = {HS_MAX_IMPL};
            bins nonexistent = {HS_NONEXISTENT};
            bins other       = {HS_OTHER};
        }

        // #3.14.2 resumereq: "resumereq is ignored if haltreq is set." The rule is
        // only testable by creating exactly the h1_r1 combination.
        x_haltreq_resumereq : cross cp_haltreq, cp_resumereq;

        // #3.14.2: "On any given write, a debugger may only write 1 to at most one
        // of the following bits: resumereq, hartreset, ackhavereset,
        // setresethaltreq, and clrresethaltreq. The others must be written 0."
        // Counting them turns a protocol rule into something measurable. `multiple`
        // is a rule violation the DUT must survive without corrupting DM state, and
        // is reached only by the negative test (TC-HOR-005) — hence a plain bin
        // rather than illegal_bins.
        cp_mutex_count : coverpoint cur_mutex_count {
            bins none     = {0};
            bins one      = {1};
            bins multiple = {[2:5]};
        }

        // #3.5 halt-on-reset, crossed against the resethaltreq shadow. Only the
        // *edges* of ndmreset are reset events (#3.14.2 ndmreset: "the debugger
        // writes 1, and then writes 0 to deassert the reset"); binning every write
        // while it stays high as another reset would let a test that never released
        // reset look done.
        cp_ndmreset_ctx : coverpoint cur_ndmreset_ctx {
            bins assert_rhr0   = {ND_ASSERT_RHR0};
            bins assert_rhr1   = {ND_ASSERT_RHR1};
            bins deassert_rhr0 = {ND_DEASSERT_RHR0};
            bins deassert_rhr1 = {ND_DEASSERT_RHR1};
            ignore_bins no_edge = {ND_NO_EDGE};
        }

        // #3.5's asymmetry: "each selected hart's resume ack bit is cleared and
        // each selected, halted hart is sent a resume request ... Resume requests
        // are ignored by running harts." The ack is cleared for EVERY selected hart
        // but only halted harts re-set it, so resumereq on a running hart leaves
        // resume ack at 0 with no way to re-set it until that hart halts and
        // resumes. Invisible unless resumereq is sampled against the prior state.
        cp_resumereq_ctx : coverpoint cur_resumereq_ctx {
            bins when_halted   = {RQ_WHEN_HALTED};
            bins when_running  = {RQ_WHEN_RUNNING};
            bins when_in_reset = {RQ_WHEN_IN_RESET};
            ignore_bins none   = {RQ_NONE};
        }

        // #3.14.2 ackhavereset / #3.2 havereset stickiness.
        cp_havereset_ctx : coverpoint cur_havereset_ctx {
            bins ack_when_set   = {HR_ACK_WHEN_SET};
            bins ack_when_clear = {HR_ACK_WHEN_CLEAR};
            bins noack_when_set = {HR_NOACK_WHEN_SET};
            ignore_bins none    = {HR_NONE};
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    // Covergroup: dmstatus reads (#3.14.1)
    // ══════════════════════════════════════════════════════════════════════════
    covergroup cg_dmstatus_read with function sample(logic [31:0] r);
        option.per_instance = 1;
        option.comment = "Decoded dmstatus read data (#3.14.1)";

        cp_ndmresetpending : coverpoint r[DMS_NDMRESETPENDING] { bins zero = {0}; bins one = {1}; }
        cp_allhavereset    : coverpoint r[DMS_ALLHAVERESET]    { bins zero = {0}; bins one = {1}; }
        cp_anyhavereset    : coverpoint r[DMS_ANYHAVERESET]    { bins zero = {0}; bins one = {1}; }
        cp_allresumeack    : coverpoint r[DMS_ALLRESUMEACK]    { bins zero = {0}; bins one = {1}; }
        cp_anyresumeack    : coverpoint r[DMS_ANYRESUMEACK]    { bins zero = {0}; bins one = {1}; }
        cp_allnonexistent  : coverpoint r[DMS_ALLNONEXISTENT]  { bins zero = {0}; bins one = {1}; }
        cp_anynonexistent  : coverpoint r[DMS_ANYNONEXISTENT]  { bins zero = {0}; bins one = {1}; }
        cp_allunavail      : coverpoint r[DMS_ALLUNAVAIL]      { bins zero = {0}; bins one = {1}; }
        cp_anyunavail      : coverpoint r[DMS_ANYUNAVAIL]      { bins zero = {0}; bins one = {1}; }
        cp_allrunning      : coverpoint r[DMS_ALLRUNNING]      { bins zero = {0}; bins one = {1}; }
        cp_anyrunning      : coverpoint r[DMS_ANYRUNNING]      { bins zero = {0}; bins one = {1}; }
        cp_allhalted       : coverpoint r[DMS_ALLHALTED]       { bins zero = {0}; bins one = {1}; }
        cp_anyhalted       : coverpoint r[DMS_ANYHALTED]       { bins zero = {0}; bins one = {1}; }
        cp_hasresethaltreq : coverpoint r[DMS_HASRESETHALTREQ] { bins zero = {0}; bins one = {1}; }

        // ── Fields whose other value belongs to a slice we are not covering ────
        //
        // These are binned at their expected value only, with the opposite value
        // ignored and the reason named. They are NOT dropped: an ignore_bins with a
        // spec citation is a claim that can be checked and argued with, whereas a
        // missing coverpoint is invisible.

        // #3.14.1 authenticated=0 means the DM is locked and "most registers will
        // not be accessible". Authentication (#3.12) is a later slice.
        cp_authenticated : coverpoint r[DMS_AUTHENTICATED] {
            bins one = {1};
            ignore_bins locked_dm = {0};
        }
        // #3.14.1 authbusy "only becomes set in immediate response to an access to
        // authdata" — authentication slice; run control never touches authdata.
        cp_authbusy : coverpoint r[DMS_AUTHBUSY] {
            bins zero = {0};
            ignore_bins auth_slice = {1};
        }
        // #3.14.1 impebreak reports whether an implicit ebreak follows the Program
        // Buffer. Program Buffer is a later slice; no run-control stimulus sets it.
        cp_impebreak : coverpoint r[DMS_IMPEBREAK] {
            bins zero = {0};
            ignore_bins progbuf_slice = {1};
        }
        // #3.14.1 confstrptrvalid=1 means confstrptr0-3 hold the configuration
        // string pointer — the "Discover DM/implementation info" feature row.
        cp_confstrptrvalid : coverpoint r[DMS_CONFSTRPTRVALID] {
            bins zero = {0};
            ignore_bins discovery_slice = {1};
        }
        // #3.14.1 stickyunavail is Preset. Where the DM reports 0, unavail is not
        // sticky and clears without ackunavail, and no stimulus can raise this bit.
        cp_stickyunavail : coverpoint r[DMS_STICKYUNAVAIL] {
            bins zero = {0};
            ignore_bins preset_high = {1};
        }

        cp_version : coverpoint r[3:0] {
            // version=0: no DM present, or dmactive=0 so "version might not return
            // correct data" (#3.14.2 dmactive=0).
            bins none  = {VERSION_NONE};
            bins v0_13 = {VERSION_0_13};
            bins v1_0  = {VERSION_1_0};
            // version=1 (0.11) predates the dmcontrol/dmstatus field layout this
            // model decodes, so binning it here would be incoherent.
            ignore_bins v0_11 = {VERSION_0_11};
            // version=15 is "not conforming to any available standard" — by
            // definition no spec-derived stimulus can require a DUT to report it.
            ignore_bins custom = {VERSION_CUSTOM};
        }

        // ── The all*/any* pairs: the aggregate semantics of hart selection ─────
        //
        // #3.14.1: all* is 1 when *every* currently selected hart is in the state,
        // any* is 1 when at least one is. Two of the four combinations are
        // unreachable for entirely different reasons, and the covergroup keeps them
        // distinct rather than collapsing both into "not covered":
        //
        //   all=0,any=1  ignore_bins — needs a *split* selection, some selected
        //                harts in the state and some not. With hasel tied to 0 there
        //                is exactly one currently selected hart (#3.14.2 hasel=0:
        //                "There is a single currently selected hart"), so all* and
        //                any* are computed over one hart and are always equal.
        //                Reachable only once the hart array mask (Ch.3 op 9) is
        //                implemented and covered.
        //
        //   all=1,any=0  illegal_bins — all* implies any* for any non-empty
        //                selection (#3.14.1). Not a configuration limit but an
        //                architectural impossibility, so a DUT producing it is
        //                broken. Binning it as merely "coverable" would make a DUT
        //                bug look like coverage progress.
        x_halted : cross cp_allhalted, cp_anyhalted {
            ignore_bins  split      = binsof(cp_allhalted.zero) && binsof(cp_anyhalted.one);
            illegal_bins impossible = binsof(cp_allhalted.one)  && binsof(cp_anyhalted.zero);
        }
        x_running : cross cp_allrunning, cp_anyrunning {
            ignore_bins  split      = binsof(cp_allrunning.zero) && binsof(cp_anyrunning.one);
            illegal_bins impossible = binsof(cp_allrunning.one)  && binsof(cp_anyrunning.zero);
        }
        x_havereset : cross cp_allhavereset, cp_anyhavereset {
            ignore_bins  split      = binsof(cp_allhavereset.zero) && binsof(cp_anyhavereset.one);
            illegal_bins impossible = binsof(cp_allhavereset.one)  && binsof(cp_anyhavereset.zero);
        }
        x_resumeack : cross cp_allresumeack, cp_anyresumeack {
            ignore_bins  split      = binsof(cp_allresumeack.zero) && binsof(cp_anyresumeack.one);
            illegal_bins impossible = binsof(cp_allresumeack.one)  && binsof(cp_anyresumeack.zero);
        }
        x_nonexistent : cross cp_allnonexistent, cp_anynonexistent {
            ignore_bins  split      = binsof(cp_allnonexistent.zero) && binsof(cp_anynonexistent.one);
            illegal_bins impossible = binsof(cp_allnonexistent.one)  && binsof(cp_anynonexistent.zero);
        }
        x_unavail : cross cp_allunavail, cp_anyunavail {
            ignore_bins  split      = binsof(cp_allunavail.zero) && binsof(cp_anyunavail.one);
            illegal_bins impossible = binsof(cp_allunavail.one)  && binsof(cp_anyunavail.zero);
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    // Covergroup: hart state transitions (#3.5 Run Control, #3.2 Reset)
    //
    // A run-control slice binning only "we saw halted" and "we saw running" would
    // be satisfied by a DUT stuck in one state that happened to be read after a
    // reset. The transitions are the behaviour; the levels are not.
    // ══════════════════════════════════════════════════════════════════════════
    covergroup cg_hart_transition with function sample(hart_transition_e tr);
        option.per_instance = 1;
        option.comment = "Selected-hart run-control state transitions (#3.5, #3.2)";

        cp_transition : coverpoint tr {
            // #3.5: "When a running hart ... sees its halt request bit high, it
            // responds by halting, deasserting its running signal, and asserting
            // its halted signal."
            bins running_to_halted   = {TR_RUNNING_TO_HALTED};
            // #3.5: "each selected, halted hart is sent a resume request. Harts
            // respond by resuming, clearing their halted signal, and asserting
            // their running signal."
            bins halted_to_running   = {TR_HALTED_TO_RUNNING};
            // #3.2: while reset is on-going a hart reports neither halted nor
            // running.
            bins running_to_in_reset = {TR_RUNNING_TO_IN_RESET};
            bins halted_to_in_reset  = {TR_HALTED_TO_IN_RESET};
            // #3.2: "if the hart was initially running it will execute normally".
            bins in_reset_to_running = {TR_IN_RESET_TO_RUNNING};
            // #3.5: with haltreq or resethaltreq set, "the hart will immediately
            // enter debug mode on the next deassertion of its reset".
            bins in_reset_to_halted  = {TR_IN_RESET_TO_HALTED};
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    function new(string name, uvm_component parent);
        super.new(name, parent);
        cg_dmi_access      = new();
        cg_dmcontrol_write = new();
        cg_dmstatus_read   = new();
        cg_hart_transition = new();
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        // The implemented hart count is DUT configuration and appears nowhere on the
        // DMI bus, so it must be declared rather than inferred. Defaulting to 1 is
        // safe: it makes HS_MAX_IMPL coincide with HS_ZERO rather than silently
        // mis-classifying a multi-hart DUT's selection bins.
        if (!uvm_config_db #(int unsigned)::get(this, "", "num_harts", num_harts)) begin
            num_harts = 1;
            `uvm_info("DBG_COV",
                "num_harts not set in config_db; assuming a single-hart DM", UVM_MEDIUM)
        end
    endfunction

    // ══════════════════════════════════════════════════════════════════════════
    // The uvm_subscriber hook — one DMI transaction from the JTAG monitor.
    // ══════════════════════════════════════════════════════════════════════════
    function void write(jtag_txn_c t);
        cg_dmi_access.sample(t.dmi_addr, t.dmi_op, t.dmi_status);

        if (t.dmi_addr == ADDR_DMCONTROL && t.dmi_op == dm_defines_pkg::DMI_WRITE)
            sample_dmcontrol_write(t.dmi_wdata);
        else if (t.dmi_addr == ADDR_DMSTATUS && t.dmi_op == dm_defines_pkg::DMI_READ)
            sample_dmstatus_read(t.dmi_rdata);
        // Addresses outside the run-control slice are ignored rather than binned.
    endfunction

    // ── dmcontrol write ───────────────────────────────────────────────────────
    function void sample_dmcontrol_write(logic [31:0] w);
        logic [19:0] new_hartsel;
        bit          selection_changed;
        bit          rhr;
        bit          nd;

        new_hartsel = {w[DMC_HARTSELHI_LSB +: 10], w[DMC_HARTSELLO_LSB +: 10]};

        // Selection updates before the action bits are evaluated. #3.14.2 states it
        // per action bit: "Writes apply to the new value of hartsel and hasel."
        selection_changed = (new_hartsel != hartsel);

        // ── hartsel classified against the implemented hart count ─────────────
        if (new_hartsel == 0)
            cur_hartsel_cls = HS_ZERO;
        else if (new_hartsel >= num_harts)
            cur_hartsel_cls = HS_NONEXISTENT;
        else if (new_hartsel == num_harts - 1)
            cur_hartsel_cls = HS_MAX_IMPL;
        else
            cur_hartsel_cls = HS_OTHER;

        // ── mutually-exclusive action bits (#3.14.2) ─────────────────────────
        cur_mutex_count = w[DMC_RESUMEREQ]       + w[DMC_HARTRESET]
                        + w[DMC_ACKHAVERESET]    + w[DMC_SETRESETHALTREQ]
                        + w[DMC_CLRRESETHALTREQ];

        // ── resumereq x prior hart state (#3.5) ──────────────────────────────
        //
        // Only meaningful when this write does not move hartsel: if it does, the
        // last-known state belongs to the previously selected hart while the
        // resumereq applies to the newly selected one, and crossing the two would
        // be a fabricated observation.
        cur_resumereq_ctx = RQ_NONE;
        if (w[DMC_RESUMEREQ] && !selection_changed && state_valid) begin
            case (cur_state)
                ST_HALTED   : cur_resumereq_ctx = RQ_WHEN_HALTED;
                ST_RUNNING  : cur_resumereq_ctx = RQ_WHEN_RUNNING;
                ST_IN_RESET : cur_resumereq_ctx = RQ_WHEN_IN_RESET;
                default     : cur_resumereq_ctx = RQ_NONE;
            endcase
        end

        // ── havereset x ackhavereset (#3.2, #3.14.2 ackhavereset) ────────────
        cur_havereset_ctx = HR_NONE;
        if (havereset_valid && !selection_changed) begin
            if (w[DMC_ACKHAVERESET])
                cur_havereset_ctx = havereset ? HR_ACK_WHEN_SET : HR_ACK_WHEN_CLEAR;
            else if (havereset)
                // havereset observed set across a write that does NOT ack it —
                // proves the bit is sticky (#3.2: "they must set a sticky havereset
                // state bit").
                cur_havereset_ctx = HR_NOACK_WHEN_SET;
            if (w[DMC_ACKHAVERESET])
                // The debugger now expects it cleared; the next dmstatus read is
                // what actually confirms it.
                havereset = 0;
        end

        hartsel = new_hartsel;

        // ── DM reset (#3.14.2 dmactive=0) ────────────────────────────────────
        //
        // "The module's state ... takes its reset values (the dmactive bit is the
        // only bit which can be written to something other than its reset value) ...
        // When this value is written, the DM may ignore any other bits written to
        // dmcontrol in the same write." So no action bit in this write is evaluated,
        // and #3.5's "the halt-on-reset request bit remains set until cleared by the
        // debugger ... or by DM reset" makes this clear the shadow.
        if (!w[DMC_DMACTIVE]) begin
            reset_haltreq.delete();
            ndmreset        = 0;
            state_valid     = 0;
            cur_state       = ST_UNKNOWN;
            havereset_valid = 0;
            cur_ndmreset_ctx = ND_NO_EDGE;
            cg_dmcontrol_write.sample(w);
            return;
        end

        // ── resethaltreq shadow (#3.14.2: the bit cannot be read) ────────────
        //
        // clr wins over a simultaneous set: setresethaltreq applies "unless
        // clrresethaltreq is simultaneously set to 1" (#3.14.2 setresethaltreq).
        if (w[DMC_CLRRESETHALTREQ])
            reset_haltreq[hartsel] = 0;
        else if (w[DMC_SETRESETHALTREQ])
            reset_haltreq[hartsel] = 1;

        // ── ndmreset edges x resethaltreq (#3.2, #3.5 halt-on-reset) ─────────
        rhr = (reset_haltreq.exists(hartsel) != 0) ? reset_haltreq[hartsel] : 1'b0;
        nd  = w[DMC_NDMRESET];
        if (nd && !ndmreset)
            cur_ndmreset_ctx = rhr ? ND_ASSERT_RHR1 : ND_ASSERT_RHR0;
        else if (!nd && ndmreset)
            cur_ndmreset_ctx = rhr ? ND_DEASSERT_RHR1 : ND_DEASSERT_RHR0;
        else
            cur_ndmreset_ctx = ND_NO_EDGE;
        ndmreset = nd;

        cg_dmcontrol_write.sample(w);
    endfunction

    // ── dmstatus read ─────────────────────────────────────────────────────────
    function void sample_dmstatus_read(logic [31:0] r);
        hart_state_e prev_state;
        logic [19:0] prev_hartsel;
        bit          prev_valid;

        cg_dmstatus_read.sample(r);

        havereset       = r[DMS_ANYHAVERESET];
        havereset_valid = 1;

        prev_state   = cur_state;
        prev_hartsel = state_hartsel;
        prev_valid   = state_valid;

        cur_state     = decode_hart_state(r);
        state_hartsel = hartsel;
        state_valid   = 1;

        // A transition is only a hart *state* change if the same hart is on both
        // sides of it. Reading dmstatus, reselecting, and reading again observes two
        // harts, not one hart moving.
        if (!prev_valid || prev_hartsel != hartsel) return;
        if (prev_state == cur_state) return;

        if (prev_state == ST_RUNNING  && cur_state == ST_HALTED)
            cur_transition = TR_RUNNING_TO_HALTED;
        else if (prev_state == ST_HALTED   && cur_state == ST_RUNNING)
            cur_transition = TR_HALTED_TO_RUNNING;
        else if (prev_state == ST_RUNNING  && cur_state == ST_IN_RESET)
            cur_transition = TR_RUNNING_TO_IN_RESET;
        else if (prev_state == ST_HALTED   && cur_state == ST_IN_RESET)
            cur_transition = TR_HALTED_TO_IN_RESET;
        else if (prev_state == ST_IN_RESET && cur_state == ST_RUNNING)
            cur_transition = TR_IN_RESET_TO_RUNNING;
        else if (prev_state == ST_IN_RESET && cur_state == ST_HALTED)
            cur_transition = TR_IN_RESET_TO_HALTED;
        else
            // Transitions into or out of unavailable/nonexistent are not
            // run-control state changes: they are selection or availability
            // effects, and binning them as transitions would overstate what the
            // stimulus proved.
            return;

        cg_hart_transition.sample(cur_transition);
    endfunction

    // Infer the selected hart's state from one dmstatus word.
    //
    // Order matters. A nonexistent hart reports neither halted nor running and
    // would otherwise be indistinguishable from a hart held in reset — #3.14.1
    // anynonexistent is the only thing that tells them apart, so it is checked
    // first. Likewise unavailable (#3.2: "While the reset is on-going, harts are
    // either in the running state ... or in the unavailable state").
    function hart_state_e decode_hart_state(logic [31:0] r);
        if (r[DMS_ANYNONEXISTENT]) return ST_NONEXISTENT;
        if (r[DMS_ANYUNAVAIL])     return ST_UNAVAIL;
        if (r[DMS_ANYHALTED])      return ST_HALTED;
        if (r[DMS_ANYRUNNING])     return ST_RUNNING;
        return ST_IN_RESET;
    endfunction

    // ══════════════════════════════════════════════════════════════════════════
    function void report_phase(uvm_phase phase);
        `uvm_info("DBG_COV", $sformatf(
            "run-control coverage: dmi_access=%0.2f%% dmcontrol_write=%0.2f%% dmstatus_read=%0.2f%% hart_transition=%0.2f%%",
            cg_dmi_access.get_inst_coverage(),
            cg_dmcontrol_write.get_inst_coverage(),
            cg_dmstatus_read.get_inst_coverage(),
            cg_hart_transition.get_inst_coverage()), UVM_NONE)
    endfunction

endclass : debug_coverage
