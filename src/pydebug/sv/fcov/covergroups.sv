// ══════════════════════════════════════════════════════════════════════════════
// covergroups.sv — Functional coverage of the external-debug feature set
//
// Collects functional coverage for the external-debug operations a debugger drives
// over DMI: run control (halt/resume/reset/halt-on-reset/hart-selection), abstract
// commands (Access Register — GPR/CSR read+write), the Program Buffer, System Bus
// Access, hart-grouping/external-trigger (dmcs2), halt-status summary (haltsum0),
// and DM/hart discovery (hartinfo, abstractcs capability fields). It subscribes to
// the same DMI transaction stream the checker and scoreboard do, one covergroup per
// register/feature, sampled from the decoded transaction in write().
//
// Spec references are to the RISC-V Debug Specification:
//   #3.2      Reset Control
//   #3.5      Run Control
//   #3.6      Hart groups                (dmcs2,      DMI 0x32)
//   #3.7.1.1  Access Register command    (command,    DMI 0x17)
//   #3.8      Program Buffer             (progbuf0-15, DMI 0x20-0x2f)
//   #3.10     System Bus Access          (sbcs,       DMI 0x38)
//   #3.14.1   dmstatus                   (DMI 0x11)
//   #3.14.2   dmcontrol                  (DMI 0x10)
//   #3.14.3   hartinfo                   (DMI 0x12)
//   #3.14.9   haltsum0                   (DMI 0x40)
//   #3.14.13  abstractcs                 (DMI 0x16)
//   #3.14.14  command                    (DMI 0x17)
//   #3.14.17  dmcs2                       (DMI 0x32)
//   #3.14.20  sbcs                        (DMI 0x38)
//
// Twin-model status (READ THIS before assuming parity): the run-control covergroups
// (cg_dmi_access/cg_dmcontrol_write/cg_dmstatus_read/cg_hart_transition) are a true
// twin of pydebug/model/coverage.py — same bins, same names, so a UVM run and a
// Python run report one number. The external-debug covergroups added below
// (abstractcs/command/progbuf/sbcs/dmcs2/hartinfo/haltsum0/data0) are, as of this
// pass, SV-ONLY: coverage.py and registers.py still model dmcontrol/dmstatus only
// (a gap that testplans/riscv_debug_testplan.md already states). Restoring full twin
// parity means extending those two Python files to match — tracked, not silently
// assumed. The bin names here are chosen to be portable to that later Python
// extension.
//
// Register addresses come from dm_defines_pkg (fully qualified, so that this file
// needs no import line added to the shared debug_pkg.sv). Field bit positions are
// declared below because dm_defines_pkg carries addresses only — they are taken
// from the spec's own machine-readable register definitions
// (riscv/riscv-debug-spec, xml/dm_registers.xml). The run-control positions match
// registers.py field-for-field; the abstractcs/command/sbcs/dmcs2 positions are the
// same ones the stimulus generator api/riscv_dm.py encodes and decodes with (e.g.
// abstractcs.busy=bit12/cmderr=[10:8], command.cmdtype=[31:24]/aarsize=[22:20],
// sbcs.sbaccess=[19:17]/sbbusy=bit21, dmcs2.group=[6:2]), so the model and the
// stimulus cannot silently disagree about where a bit lives.
// ══════════════════════════════════════════════════════════════════════════════
class debug_coverage extends uvm_subscriber #(jtag_txn_c);
    `uvm_component_utils(debug_coverage)

    // ── Register addresses (reused from dm_defines_pkg, not redefined) ────────
    localparam logic [6:0] ADDR_DMCONTROL  = dm_defines_pkg::DM_ADDR_DMCONTROL;
    localparam logic [6:0] ADDR_DMSTATUS   = dm_defines_pkg::DM_ADDR_DMSTATUS;
    localparam logic [6:0] ADDR_DATA0      = dm_defines_pkg::DM_ADDR_DATA0;
    localparam logic [6:0] ADDR_DATA11     = dm_defines_pkg::DM_ADDR_DATA11;
    localparam logic [6:0] ADDR_HARTINFO   = dm_defines_pkg::DM_ADDR_HARTINFO;
    localparam logic [6:0] ADDR_ABSTRACTCS = dm_defines_pkg::DM_ADDR_ABSTRACTCS;
    localparam logic [6:0] ADDR_COMMAND    = dm_defines_pkg::DM_ADDR_COMMAND;
    localparam logic [6:0] ADDR_PROGBUF0   = dm_defines_pkg::DM_ADDR_PROGBUF0;
    localparam logic [6:0] ADDR_PROGBUF15  = dm_defines_pkg::DM_ADDR_PROGBUF15;
    localparam logic [6:0] ADDR_DMCS2      = dm_defines_pkg::DM_ADDR_DMCS2;
    localparam logic [6:0] ADDR_SBCS       = dm_defines_pkg::DM_ADDR_SBCS;
    localparam logic [6:0] ADDR_SBADDRESS0 = dm_defines_pkg::DM_ADDR_SBADDRESS0;
    localparam logic [6:0] ADDR_SBDATA0    = dm_defines_pkg::DM_ADDR_SBDATA0;
    localparam logic [6:0] ADDR_HALTSUM0   = dm_defines_pkg::DM_ADDR_HALTSUM0;

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

    // ── abstractcs field bit positions (#3.14.13) ─────────────────────────────
    // busy=bit12 and cmderr=[10:8] match api/riscv_dm.py's _wait_abstract poll.
    localparam int ABS_PROGBUFSIZE_LSB = 24;  // [28:24]
    localparam int ABS_BUSY            = 12;
    localparam int ABS_RELAXEDPRIV     = 11;
    localparam int ABS_CMDERR_LSB      = 8;   // [10:8]
    localparam int ABS_DATACOUNT_LSB   = 0;   // [3:0]

    // abstractcs.cmderr encodings (#3.14.13 cmderr)
    localparam logic [2:0] CMDERR_NONE          = 3'd0;
    localparam logic [2:0] CMDERR_BUSY          = 3'd1;
    localparam logic [2:0] CMDERR_NOT_SUPPORTED = 3'd2;
    localparam logic [2:0] CMDERR_EXCEPTION     = 3'd3;
    localparam logic [2:0] CMDERR_HALT_RESUME   = 3'd4;
    localparam logic [2:0] CMDERR_BUS           = 3'd5;
    localparam logic [2:0] CMDERR_OTHER         = 3'd7;

    // ── command field bit positions (#3.14.14) ────────────────────────────────
    // cmdtype=[31:24], aarsize=[22:20], transfer=17, write=16, regno=[15:0] match
    // api/riscv_dm.py's read_gpr/write_gpr/execute_progbuf command encoders.
    localparam int CMD_CMDTYPE_LSB = 24;  // [31:24]
    localparam int CMD_AARSIZE_LSB = 20;  // [22:20]
    localparam int CMD_AARPOSTINC  = 19;
    localparam int CMD_POSTEXEC    = 18;
    localparam int CMD_TRANSFER    = 17;
    localparam int CMD_WRITE       = 16;
    localparam int CMD_REGNO_LSB   = 0;   // [15:0]

    // command.cmdtype encodings (#3.7.1: Access Register / Quick Access / Access Memory)
    localparam logic [7:0] CMDTYPE_ACCESS_REGISTER = 8'd0;
    localparam logic [7:0] CMDTYPE_QUICK_ACCESS    = 8'd1;
    localparam logic [7:0] CMDTYPE_ACCESS_MEMORY   = 8'd2;

    // command.aarsize encodings (#3.7.1.1 aarsize): 2=32-bit, 3=64-bit, 4=128-bit
    localparam logic [2:0] AARSIZE_32  = 3'd2;
    localparam logic [2:0] AARSIZE_64  = 3'd3;
    localparam logic [2:0] AARSIZE_128 = 3'd4;

    // Access Register regno ranges (#3.7.1.1 / Table "Abstract Register Numbers")
    localparam logic [15:0] REGNO_CSR_LO = 16'h0000;
    localparam logic [15:0] REGNO_CSR_HI = 16'h0FFF;
    localparam logic [15:0] REGNO_GPR_LO = 16'h1000;  // x0=0x1000 .. x31=0x101F
    localparam logic [15:0] REGNO_GPR_HI = 16'h101F;
    localparam logic [15:0] REGNO_FPR_LO = 16'h1020;  // f0=0x1020 .. f31=0x103F
    localparam logic [15:0] REGNO_FPR_HI = 16'h103F;

    // ── sbcs field bit positions (#3.14.20) ───────────────────────────────────
    // sbaccess=[19:17], sbreadonaddr=20, sbbusy=21, sberror=[14:12] match
    // api/riscv_dm.py's SBA read/write and _wait_sba poll.
    localparam int SBCS_SBVERSION_LSB     = 29;  // [31:29]
    localparam int SBCS_SBBUSYERROR       = 22;
    localparam int SBCS_SBBUSY            = 21;
    localparam int SBCS_SBREADONADDR      = 20;
    localparam int SBCS_SBACCESS_LSB      = 17;  // [19:17]
    localparam int SBCS_SBAUTOINCREMENT   = 16;
    localparam int SBCS_SBREADONDATA      = 15;
    localparam int SBCS_SBERROR_LSB       = 12;  // [14:12]
    localparam int SBCS_SBASIZE_LSB       = 5;   // [11:5]
    localparam int SBCS_SBACCESS128       = 4;
    localparam int SBCS_SBACCESS64        = 3;
    localparam int SBCS_SBACCESS32        = 2;
    localparam int SBCS_SBACCESS16        = 1;
    localparam int SBCS_SBACCESS8         = 0;

    // sbcs.sbaccess encodings (#3.14.20 sbaccess): 0=8b,1=16b,2=32b,3=64b,4=128b
    localparam logic [2:0] SBACCESS_8   = 3'd0;
    localparam logic [2:0] SBACCESS_16  = 3'd1;
    localparam logic [2:0] SBACCESS_32  = 3'd2;
    localparam logic [2:0] SBACCESS_64  = 3'd3;
    localparam logic [2:0] SBACCESS_128 = 3'd4;

    // sbcs.sberror encodings (#3.14.20 sberror)
    localparam logic [2:0] SBERROR_NONE      = 3'd0;
    localparam logic [2:0] SBERROR_TIMEOUT   = 3'd1;
    localparam logic [2:0] SBERROR_BADADDR   = 3'd2;
    localparam logic [2:0] SBERROR_ALIGNMENT = 3'd3;
    localparam logic [2:0] SBERROR_BADSIZE   = 3'd4;
    localparam logic [2:0] SBERROR_OTHER     = 3'd7;

    // ── dmcs2 field bit positions (#3.14.17) ──────────────────────────────────
    // All positions match api/riscv_dm.py's dmcs2() encoder / dmcs2_* decoders.
    localparam int DMCS2_GROUPTYPE        = 11;
    localparam int DMCS2_DMEXTTRIGGER_LSB = 7;   // [10:7]
    localparam int DMCS2_GROUP_LSB        = 2;   // [6:2]
    localparam int DMCS2_HGWRITE          = 1;
    localparam int DMCS2_HGSELECT         = 0;

    // ── hartinfo field bit positions (#3.14.3) ────────────────────────────────
    localparam int HI_NSCRATCH_LSB  = 20;  // [23:20]
    localparam int HI_DATAACCESS    = 16;
    localparam int HI_DATASIZE_LSB  = 12;  // [15:12]
    localparam int HI_DATAADDR_LSB  = 0;   // [11:0]

    // ── Trigger Module (Sdtrig, spec Ch.5) — accessed as hart CSRs via the ────
    // Access Register abstract command (regno = the CSR number). The debugger
    // selects a trigger with tselect, then reads/writes its tdata1/2/3.
    localparam logic [15:0] CSR_TSELECT = 16'h07A0;
    localparam logic [15:0] CSR_TDATA1  = 16'h07A1;
    localparam logic [15:0] CSR_TDATA2  = 16'h07A2;
    localparam logic [15:0] CSR_TDATA3  = 16'h07A3;
    localparam logic [15:0] CSR_TINFO   = 16'h07A4;

    // tdata1.type encodings (spec Ch.5, tdata1 "type" field). For RV32 the field is
    // tdata1[31:28]; on an RV64 DUT it is tdata1[63:60] (staged in data1, not data0)
    // — decoded here from the RV32 position, which is the exercised width. The named
    // types are the ones the trigger-module coverage plan targets.
    localparam logic [3:0] TRIG_NONE         = 4'd0;
    localparam logic [3:0] TRIG_LEGACY       = 4'd1;
    localparam logic [3:0] TRIG_MCONTROL     = 4'd2;
    localparam logic [3:0] TRIG_ICOUNT       = 4'd3;
    localparam logic [3:0] TRIG_ITRIGGER     = 4'd4;
    localparam logic [3:0] TRIG_ETRIGGER     = 4'd5;
    localparam logic [3:0] TRIG_MCONTROL6    = 4'd6;
    localparam logic [3:0] TRIG_TMEXTTRIGGER = 4'd7;
    localparam logic [3:0] TRIG_DISABLED     = 4'd15;
    localparam int         TRIG_TYPE_LSB_RV32 = 28;  // tdata1[31:28] on RV32

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

    // ── DUT configuration, read from dut_configs/<name>.json in build_phase
    // (dut_config_reader.sv, same mechanism/same file dm_checker.sv already
    // uses to construct dm_ref_model) -- generatable from config, not
    // hardcoded per-DUT assumptions. Populated BEFORE the covergroups below
    // are constructed, since a coverpoint bin's value set is evaluated once
    // at covergroup construction, not re-evaluated per sample.
    bit [3:0] dut_version           = VERSION_0_13;
    bit       dut_hasresethaltreq   = 1'b0;
    bit       dut_stickyunavail     = 1'b0;

    // ── Inferred state, rebuilt from the bus exactly as a debugger would ──────
    int unsigned num_harts       = 1;   // DUT config, from the config_db
    logic [19:0] hartsel         = '0;  // as last written (#3.14.2: resets to 0)
    logic [19:0] state_hartsel   = '0;  // hartsel in force when cur_state was read
    bit          state_valid     = 0;
    bit          havereset       = 0;   // anyhavereset as of the last dmstatus read
    bit          havereset_valid = 0;
    bit          ndmreset        = 0;   // dmcontrol.ndmreset as last written
    // Set on the write that deasserts ndmreset; cleared by the next write.
    // Real RTL's halt handshake (fetch resume -> observe debug_req -> debug
    // ROM entry -> halted_q) takes real cycles after release -- ndmreset
    // itself (and dmstatus.ndmresetpending, a direct combinational
    // passthrough of the same register, dm_csrs.sv) drops the instant the
    // write lands, well before that. Without this flag, decode_hart_state
    // reclassifies the still-settling hart as plain ST_RUNNING the moment
    // ndmreset's local write-tracking flips to 0, so a haltreq-during-reset
    // release (TC-RST-001 (cont'd)) samples a spurious
    // in_reset->running->halted pair instead of the real in_reset->halted
    // transition it actually is. Confirmed via CVA6 UVM: the transition bin
    // stayed at 0 hits even after the underlying stimulus bug was fixed and
    // the step started passing functionally, 2026-07-25.
    bit          ndmreset_release_pending = 0;
    // DMI is pipelined one transaction deep (spec #6.1.5): a shift's captured
    // dmi_rdata/dmi_status belong to the PREVIOUS request, never its own
    // (jtag_dmi_read_seq.sv issues the read request as one transaction,
    // dmi_addr=<reg>, then a SEPARATE dmi_addr=0/NOP transaction to actually
    // capture the result -- same one-deep correlation dm_checker.sv's own
    // pending_addr implements). Read-sampling covergroups below must defer to
    // the NEXT transaction's rdata, not the request transaction's own.
    bit          pending_read_valid = 0;
    logic [6:0]  pending_read_addr;
    // Shadow of the per-hart halt-on-reset request bit, keyed by hartsel. Spec
    // #3.14.2 resethaltreq: "an optional internal bit of per-hart state that cannot
    // be read, but can be written with setresethaltreq and clrresethaltreq" — so
    // the only way to know its value is to remember what we wrote.
    bit reset_haltreq [logic [19:0]];

    // Last value staged into data0. An abstract CSR write is two transactions —
    // data0 write (the operand), then command write (the trigger) — so decoding a
    // trigger's configured type needs the operand remembered from the prior write.
    logic [31:0] last_data0_wr = '0;

    // ══════════════════════════════════════════════════════════════════════════
    // Covergroup: DMI access shape
    // ══════════════════════════════════════════════════════════════════════════
    covergroup cg_dmi_access with function sample(
        logic [6:0] addr, logic [1:0] op, logic [1:0] status
    );
        option.per_instance = 1;
        option.comment = "Which run-control registers were accessed, how, and with what DMI status";

        cp_addr : coverpoint addr {
            bins dmcontrol  = {ADDR_DMCONTROL};
            bins dmstatus   = {ADDR_DMSTATUS};
            bins hartinfo   = {ADDR_HARTINFO};
            bins data0      = {ADDR_DATA0};
            bins abstractcs = {ADDR_ABSTRACTCS};
            bins command    = {ADDR_COMMAND};
            // The Program Buffer is one logical region; every implemented slot is
            // the same architectural access, so all 16 addresses share one bin
            // rather than reporting 15 empties on a DUT with progbufsize<16.
            bins progbuf    = {[ADDR_PROGBUF0 : ADDR_PROGBUF15]};
            bins dmcs2      = {ADDR_DMCS2};
            bins sbcs       = {ADDR_SBCS};
            bins sbaddress0 = {ADDR_SBADDRESS0};
            bins sbdata0    = {ADDR_SBDATA0};
            bins haltsum0   = {ADDR_HALTSUM0};
            // Any remaining DMI address (authdata, abstractauto, nextdm, the hart
            // array-mask window, sbaddress1-3/sbdata1-3) is a feature not exercised
            // by this project's stimulus yet; left unbinned rather than claimed.
        }

        cp_op : coverpoint op {
            bins nop   = {dm_defines_pkg::DMI_NOP};
            bins read  = {dm_defines_pkg::DMI_READ};
            bins write = {dm_defines_pkg::DMI_WRITE};
        }

        cp_status : coverpoint status {
            bins success = {dm_defines_pkg::DMI_STAT_SUCCESS};
            // failed/busy are DMI error/back-pressure conditions reached only by
            // error injection (unimplemented-address access, back-to-back scans
            // with insufficient idle) — corner cases with no stimulus in this pass.
            ignore_bins failed = {dm_defines_pkg::DMI_STAT_FAILED};
            ignore_bins busy   = {dm_defines_pkg::DMI_STAT_BUSY};
        }

        // The cross exists only to assert the one architecturally-illegal combo: a
        // write to read-only dmstatus (#3.14.1, every field R). The remaining
        // addr×op cells are either covered by cp_addr/cp_op individually or are
        // read-only/write-only registers whose opposite direction never occurs;
        // they carry no extra architectural obligation, so the cross is reduced to
        // its assertion (all coverable cells ignored, the illegal one kept — illegal
        // takes precedence over ignore).
        x_addr_op : cross cp_addr, cp_op {
            illegal_bins dmstatus_write = binsof(cp_addr.dmstatus) && binsof(cp_op.write);
            ignore_bins  all_other      = binsof(cp_op) || binsof(cp_addr);
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
        // On a single-hart DUT (both project DUTs) the highest implemented index IS
        // hart 0 — so HS_MAX_IMPL is caught as HS_ZERO first and never occurs, and
        // HS_OTHER (an index strictly between 0 and the max) has no room to exist.
        // Both are excluded here; a multi-hart DUT would make them reachable.
        cp_hartsel_cls : coverpoint cur_hartsel_cls {
            bins zero        = {HS_ZERO};
            bins nonexistent = {HS_NONEXISTENT};
            ignore_bins max_impl_single_hart = {HS_MAX_IMPL};
            ignore_bins other_single_hart    = {HS_OTHER};
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

        // ndmresetpending (#3.14.1) is a v1.0 addition; a v0.13 DUT's dm_pkg
        // dmstatus_t has no such field routed at all and reads it tied 0
        // unconditionally (confirmed against real Ibex RTL, 2026-07-25).
        // Unlike cp_version/cp_stickyunavail/cp_hasresethaltreq above, this
        // one can't be made config-driven with a runtime dut_version check:
        // those fields each have exactly one real, static, per-DUT value,
        // but ndmresetpending on a v1.0 DUT is a genuine live signal with
        // BOTH 0 and 1 independently meaningful -- there's no single
        // "declared value" to swap in, and a runtime value-set trick (e.g.
        // an unreachable sentinel like 1'bz for the "wrong" DUT) does not
        // work either: Questa still counts a `bins` entry toward the total
        // even when its value can provably never be sampled -- only the
        // `ignore_bins` *keyword* removes a bin from the denominator, and
        // that keyword is fixed at elaboration, not switchable at runtime.
        // This needs real compile-time conditional compilation instead:
        // DUT_VERSION_1_0 is defined via +define+ only for the CVA6 vlog
        // invocations (cva6_sim/Makefile), left undefined for Ibex's.
        cp_ndmresetpending : coverpoint r[DMS_NDMRESETPENDING] {
            bins zero = {1'b0};
`ifdef DUT_VERSION_1_0
            bins one = {1'b1};
`else
            ignore_bins one_pre_1_0 = {1'b1};
`endif
        }
        cp_allhavereset    : coverpoint r[DMS_ALLHAVERESET]    { bins zero = {0}; bins one = {1}; }
        cp_anyhavereset    : coverpoint r[DMS_ANYHAVERESET]    { bins zero = {0}; bins one = {1}; }
        cp_allresumeack    : coverpoint r[DMS_ALLRESUMEACK]    { bins zero = {0}; bins one = {1}; }
        cp_anyresumeack    : coverpoint r[DMS_ANYRESUMEACK]    { bins zero = {0}; bins one = {1}; }
        cp_allnonexistent  : coverpoint r[DMS_ALLNONEXISTENT]  { bins zero = {0}; bins one = {1}; }
        cp_anynonexistent  : coverpoint r[DMS_ANYNONEXISTENT]  { bins zero = {0}; bins one = {1}; }
        // #3.2/#3.14.1 allunavail/anyunavail=1: both current SoC integrations
        // (CVA6-fork/corev_apu/tb/ariane_testharness.sv,
        // ibex-demo-system/rtl/system/ibex_demo_system.sv) hardwire the DM's
        // unavailable_i input to constant 0 -- unavail is structurally
        // unreachable via any DMI stimulus on either DUT, not just
        // unimplemented (confirmed against RTL, 2026-07-25).
        cp_allunavail      : coverpoint r[DMS_ALLUNAVAIL]      {
            bins zero = {0};
            ignore_bins unavailable_i_tied_0 = {1};
        }
        cp_anyunavail      : coverpoint r[DMS_ANYUNAVAIL]      {
            bins zero = {0};
            ignore_bins unavailable_i_tied_0 = {1};
        }
        cp_allrunning      : coverpoint r[DMS_ALLRUNNING]      { bins zero = {0}; bins one = {1}; }
        cp_anyrunning      : coverpoint r[DMS_ANYRUNNING]      { bins zero = {0}; bins one = {1}; }
        cp_allhalted       : coverpoint r[DMS_ALLHALTED]       { bins zero = {0}; bins one = {1}; }
        cp_anyhalted       : coverpoint r[DMS_ANYHALTED]       { bins zero = {0}; bins one = {1}; }
        // #3.14.2 hasresethaltreq: an optional, declared DUT capability
        // (dut_configs/<name>.json "hasresethaltreq", read into
        // dut_hasresethaltreq in build_phase) -- both current DUTs declare
        // it false (dm_csrs.sv hardcodes `dmstatus.hasresethaltreq = 1'b0`
        // unconditionally), so the "true" value is presently always
        // ignore_bins in practice, but this is now generated from the same
        // config dm_ref_model.sv uses, not a hardcoded cross-DUT assumption
        // (2026-07-25) -- a future DUT declaring it true flips which value
        // is real without touching this file.
        cp_hasresethaltreq : coverpoint r[DMS_HASRESETHALTREQ] {
            bins declared          = {dut_hasresethaltreq};
            ignore_bins undeclared = {!dut_hasresethaltreq};
        }

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
        // #3.14.1 stickyunavail is Preset -- a declared, per-DUT static value
        // (dut_configs/<name>.json "stickyunavail", read into
        // dut_stickyunavail in build_phase), not a runtime-settable bit: no
        // stimulus can ever change which single value a given DUT reports.
        // Previously hardcoded to always-expect-0/ignore-1, which was
        // silently backwards for a DUT declaring stickyunavail=true (CVA6:
        // permanently 1, making "0" the actually-unreachable value on that
        // DUT) -- generated from config now, 2026-07-25.
        cp_stickyunavail : coverpoint r[DMS_STICKYUNAVAIL] {
            bins declared          = {dut_stickyunavail};
            ignore_bins undeclared = {!dut_stickyunavail};
        }

        cp_version : coverpoint r[3:0] {
            // version=0 ("no DM present") is NOT reachable via any real
            // stimulus: dm_csrs.sv assigns dmstatus.version unconditionally
            // (not gated by dmactive) on both DUTs, confirmed against RTL --
            // #3.14.2's "might not return correct data" pre-activation is
            // permissive, not a guarantee any real DUT actually zeroes it
            // (2026-07-25; mirrors the identical fix already applied on the
            // Python model side, model/coverage.py).
            ignore_bins none = {VERSION_NONE};
            // A DUT reports exactly one spec version, declared in
            // dut_configs/<name>.json and read into dut_version in
            // build_phase (same mechanism as dm_ref_model.sv's own
            // version_ constructor arg) -- v0_13/v1_0 are therefore
            // mutually exclusive per DUT, not two bins every DUT is
            // expected to hit. Generated from config, 2026-07-25: CVA6's
            // own report no longer carries a permanently-red v0_13 bin it
            // structurally can never reach, and vice versa for Ibex.
            bins declared = {dut_version};
            ignore_bins undeclared = {
                (dut_version == VERSION_0_13) ? VERSION_1_0 : VERSION_0_13
            };
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
        // No explicit split/impossible bins needed here (unlike the other
        // all/any crosses above): cp_allunavail/cp_anyunavail's own "one"
        // values are already ignore_bins (unavailable_i tied 0 on both
        // DUTs), and Questa does not allow binsof() to reference an
        // ignore_bins name in a cross expression ("Could not find
        // Coverpoint bin ... in local scope", confirmed by trying, 2026-07-
        // 25). With only "zero" addressable on each axis, the auto-
        // generated cross has exactly one legal combination, <zero,zero>.
        x_unavail : cross cp_allunavail, cp_anyunavail;
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
            // #3.2: reset asserted on a running hart. Both DUTs' dm_csrs.sv
            // compute allrunning combinationally as ~halted & ~unavailable,
            // so a resetting hart reads running=1 throughout, not "neither"
            // (spec #3.2 leaves this implementation dependent; confirmed
            // against real RTL, riscv-dbg-vip PR#131, 2026-07-25).
            bins running_to_in_reset = {TR_RUNNING_TO_IN_RESET};
            // #3.2: "if the hart was initially running it will execute normally".
            bins in_reset_to_running = {TR_IN_RESET_TO_RUNNING};
            // #3.5: with haltreq set (not resethaltreq -- WARL-tied to 0 on
            // both DUTs, same family as hartreset), "the hart will
            // immediately enter debug mode on the next deassertion of its
            // reset". Produced by asserting plain haltreq while already in
            // ndmreset -- release_from_reset() checks "was a halt requested
            // by any means", not specifically resethaltreq.
            bins in_reset_to_halted  = {TR_IN_RESET_TO_HALTED};
            // reset asserted on a halted hart (#3.2). Excluded, not a bin:
            // unreachable via any stimulus on either project DUT. Not via
            // hartreset (WARL-tied to 0). Not via ndmreset either -- both
            // DUTs' dm_mem.sv only resets halted_q on !rst_ni (the DM's own
            // reset), and ndmreset deliberately does not touch the DM's own
            // registers, so a hart already halted stays reported halted
            // throughout an ndmreset cycle, unaffected by it (confirmed
            // 2026-07-25, the hard way -- a first stimulus attempt assumed
            // otherwise and timed out waiting for a transition that RTL
            // structurally cannot produce).
            ignore_bins halted_to_in_reset = {TR_HALTED_TO_IN_RESET};
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    // External-debug feature covergroups — BASIC-feature scope
    //
    // Each covergroup below is deliberately scoped to whether the *basic* operation
    // of its feature was exercised, not the full corner-case space. Error-injection
    // paths (cmderr/sberror codes, sbbusyerror), optional acceleration modes
    // (aar/aam/sb auto-increment, sbreadondata streaming), optional command kinds
    // (Quick Access, Access Memory), and wider access sizes (64/128-bit, FPR) are
    // intentionally NOT binned yet — they are corner cases whose stimulus does not
    // exist, and binning them now would only manufacture permanent holes. They are
    // named in comments so the later corner-case pass has a checklist, not so this
    // pass reports a misleadingly low number.
    // ══════════════════════════════════════════════════════════════════════════

    // ── Abstract Command — Access Register (#3.7.1.1, #3.14.14) ───────────────
    // Basic features: GPR read, GPR write, CSR access, Program-Buffer execute
    // (postexec). Sampled from the written command word.
    covergroup cg_command_write with function sample(logic [31:0] w);
        option.per_instance = 1;
        option.comment = "Abstract-command basic operation (#3.14.14)";

        // read (transfer=1,write=0) vs write (transfer=1,write=1) — the basic
        // abstract-command directions. (Program-Buffer execution via postexec is a
        // functional group of its own, cg_progbuf below.)
        cp_write : coverpoint w[CMD_WRITE] { bins read = {0}; bins write = {1}; }

        // GPR vs CSR — the two register namespaces this project exercises. FPR
        // (needs F/D ext) and the 64/128-bit sizes are corner cases, left unbinned.
        cp_regno_class : coverpoint w[CMD_REGNO_LSB +: 16] {
            bins gpr = {[REGNO_GPR_LO : REGNO_GPR_HI]};
            bins csr = {[REGNO_CSR_LO : REGNO_CSR_HI]};
        }
    endgroup

    // ── abstractcs — command status + capability discovery (#3.14.13) ─────────
    // Basic: we observe busy during a poll, a clean (cmderr=none) completion, and
    // the progbufsize/datacount discovery fields (TC-AC-013). cmderr error codes
    // are corner cases (negative tests), left unbinned for now.
    covergroup cg_abstractcs_read with function sample(logic [31:0] r);
        option.per_instance = 1;
        option.comment = "abstractcs basic status/discovery (#3.14.13)";

        cp_busy : coverpoint r[ABS_BUSY] { bins idle = {0}; bins busy = {1}; }
        // A clean completion is the basic case. cmderr!=0 error codes are the
        // corner-case (negative) paths and are not binned in this pass.
        cp_cmderr_none : coverpoint (r[ABS_CMDERR_LSB +: 3] == CMDERR_NONE) {
            bins clean = {1};
            ignore_bins error = {0};
        }
        // Whether a Program Buffer exists at all (discovery). Its exact slot count
        // is not a basic-feature distinction. `none` is unreachable on any DUT that
        // implements a Program Buffer (both project DUTs do, progbufsize>0), so it
        // is excluded here rather than left as a permanent hole — a DUT with no
        // Program Buffer would flip which bin is reachable.
        cp_has_progbuf : coverpoint (r[ABS_PROGBUFSIZE_LSB +: 5] != 0) {
            bins present     = {1};
            ignore_bins none = {0};
        }
        // Whether an abstract-data path exists (datacount>0) — the precondition for
        // Access Register at all.
        cp_has_data : coverpoint (r[ABS_DATACOUNT_LSB +: 4] != 0) {
            bins present     = {1};
            ignore_bins none = {0};
        }
    endgroup

    // ── Program Buffer (#3.8) ─────────────────────────────────────────────────
    // Basic feature = the buffer was written AND executed (via command postexec).
    // Sampled from two sites with iff guards so each call records only its event:
    // a progbuf write records cp_written; a postexec command records cp_executed.
    covergroup cg_progbuf with function sample(bit wrote, bit executed);
        option.per_instance = 1;
        option.comment = "Program Buffer written + executed (#3.8, #3.7.1.1 postexec)";

        cp_written  : coverpoint wrote    iff (wrote)    { bins written  = {1}; }
        cp_executed : coverpoint executed iff (executed) { bins executed = {1}; }
    endgroup

    // ── System Bus Access — basic config + status (#3.10, #3.14.20) ───────────
    // Basic: a 32-bit access configured (the exercised width), the read-on-address
    // trigger mode, and observing sbbusy during a poll. Error codes, sbbusyerror,
    // streaming, wider widths and the sbaccessN/sbasize/sbversion discovery matrix
    // are corner cases left for the later pass.
    covergroup cg_sbcs with function sample(logic [31:0] w, bit is_write);
        option.per_instance = 1;
        option.comment = "sbcs basic configuration/status (#3.14.20)";

        // sbaccess only carries the debugger's choice on a write; on a read it
        // reflects current config. Either way, seeing the 32-bit selection is the
        // basic case.
        cp_access32 : coverpoint (w[SBCS_SBACCESS_LSB +: 3] == SBACCESS_32) {
            bins acc32 = {1};
        }
        cp_readonaddr : coverpoint w[SBCS_SBREADONADDR] { bins off = {0}; bins on = {1}; }
        // sbbusy is only meaningful on a status read; gate the sample so a config
        // write's (busy=0) word doesn't count as "saw idle" spuriously.
        //
        // busy=1 has never been observed in this project's SBA stimulus --
        // every single SBCS read in the sba_uvm coverage log shows busy=0
        // (`_wait_sbus()` in api/riscv_dm.py polls at DMI/JTAG speed, and
        // this DUT's SBA transaction completes faster than software polling
        // can catch a busy=1 moment). This is a stimulus/timing-granularity
        // limitation, not a functional gap -- ignored rather than forced
        // with an artificial slow-down (2026-07-25).
        cp_sbbusy : coverpoint w[SBCS_SBBUSY] iff (!is_write) {
            bins idle = {0};
            ignore_bins too_fast_to_observe = {1};
        }
    endgroup

    // ── System-bus address/data accesses (#3.10) ──────────────────────────────
    // Basic: the read flow (write sbaddress0 → read sbdata0) and the write flow
    // (write sbaddress0 → write sbdata0).
    covergroup cg_sb_access with function sample(logic [6:0] addr, logic [1:0] op);
        option.per_instance = 1;
        option.comment = "System-bus address/data accesses (#3.10)";

        // {addr==ADDR_SBDATA0, op==DMI_WRITE}: MSB is the address bit, LSB is
        // the op bit, so e.g. a SBDATA0 *read* is {1,0}=2'b10, not 2'b00 --
        // confirmed against a real transaction (addr=0x3c op=READ) that
        // should have hit "data_read" but was silently falling into the
        // ignored 2'b10 bin instead, riscv-dbg-vip investigation 2026-07-25.
        cp_access : coverpoint {addr == ADDR_SBDATA0, op == dm_defines_pkg::DMI_WRITE} {
            bins addr_write = {2'b01};  // write sbaddress0 (arm/address)
            bins data_write = {2'b11};  // write sbdata0    (bus write)
            bins data_read  = {2'b10};  // read  sbdata0    (bus read result)
            // {2'b00} = reading sbaddress0 back: legal but not a basic flow.
            ignore_bins addr_read = {2'b00};
        }
    endgroup

    // ── dmcs2 — hart groups / external triggers (#3.6, #3.14.17) ──────────────
    // Basic: the register was accessed and its select/type/membership fields driven.
    covergroup cg_dmcs2_write with function sample(logic [31:0] w);
        option.per_instance = 1;
        option.comment = "dmcs2 basic access (#3.14.17)";

        cp_hgselect  : coverpoint w[DMCS2_HGSELECT]  { bins halt_group = {0}; bins resume_group = {1}; }
        cp_grouptype : coverpoint w[DMCS2_GROUPTYPE] { bins halt = {0}; bins ext_trigger = {1}; }
        cp_group     : coverpoint (w[DMCS2_GROUP_LSB +: 5] != 0) { bins ungrouped = {0}; bins grouped = {1}; }
    endgroup

    // ── hartinfo discovery (#3.14.3) ──────────────────────────────────────────
    // Basic: read hartinfo and observe whether abstract data is register- or
    // memory-backed (the one field that changes how Program-Buffer flows behave).
    covergroup cg_hartinfo_read with function sample(logic [31:0] r);
        option.per_instance = 1;
        option.comment = "hartinfo dataaccess discovery (#3.14.3)";

        // dataaccess is a fixed per-DUT property (0=abstract-data registers are
        // CSRs, 1=memory-mapped) — only one value is ever observable on a given
        // DUT, so binning both would cap this coverpoint at 50% forever. The basic
        // feature is "hartinfo was read and its data configuration observed", so a
        // single bin covers whichever value this DUT reports.
        cp_dataaccess : coverpoint r[HI_DATAACCESS] { bins observed = {[0:1]}; }
    endgroup

    // ── haltsum0 (#3.14.9) ────────────────────────────────────────────────────
    // Basic: the halt-status summary was read and reflects at least one halted hart.
    covergroup cg_haltsum0_read with function sample(logic [31:0] r);
        option.per_instance = 1;
        option.comment = "haltsum0 read (#3.14.9)";

        cp_haltsum0 : coverpoint (r != 0) { bins none_halted = {0}; bins some_halted = {1}; }
    endgroup

    // ── data0 — abstract-command operand/result (#3.14.11) ────────────────────
    // Basic: data0 was both written (operand staged) and read (result retrieved).
    covergroup cg_data0_access with function sample(logic [1:0] op);
        option.per_instance = 1;
        option.comment = "data0 read/write (#3.14.11)";

        cp_op : coverpoint op {
            bins read  = {dm_defines_pkg::DMI_READ};
            bins write = {dm_defines_pkg::DMI_WRITE};
            ignore_bins nop = {dm_defines_pkg::DMI_NOP};
        }
    endgroup

    // ── Trigger Module (Sdtrig, spec Ch.5) ────────────────────────────────────
    // Basic: which trigger CSR was accessed via the abstract command, and — on a
    // tdata1 write — which trigger type (mcontrol6, icount, ...) was configured.
    // Sampled statefully in write() from the command's regno plus the data0 operand
    // staged just before it. No trigger-module stimulus exists yet, so this group
    // defines the coverage intent and reads 0% until a trigger sequence is added —
    // an honest, visible gap rather than a silent omission.
    covergroup cg_trigger with function sample(
        logic [15:0] regno, bit is_tdata1_write, logic [3:0] ttype
    );
        option.per_instance = 1;
        option.comment = "Trigger Module CSR access + configured type (Sdtrig, Ch.5)";

        cp_trigger_csr : coverpoint regno {
            bins tselect = {CSR_TSELECT};
            bins tdata1  = {CSR_TDATA1};
            bins tdata2  = {CSR_TDATA2};
            bins tdata3  = {CSR_TDATA3};
            bins tinfo   = {CSR_TINFO};
        }
        // The configured trigger type, sampled only when a tdata1 write is seen.
        cp_trigger_type : coverpoint ttype iff (is_tdata1_write) {
            bins mcontrol     = {TRIG_MCONTROL};
            bins icount       = {TRIG_ICOUNT};
            bins itrigger     = {TRIG_ITRIGGER};
            bins etrigger     = {TRIG_ETRIGGER};
            bins mcontrol6    = {TRIG_MCONTROL6};
            bins tmexttrigger = {TRIG_TMEXTTRIGGER};
            // none/legacy/disabled are teardown states, not a configured trigger.
            ignore_bins inactive = {TRIG_NONE, TRIG_LEGACY, TRIG_DISABLED};
        }
    endgroup

    // ══════════════════════════════════════════════════════════════════════════
    function new(string name, uvm_component parent);
        string dut_config_path;
        dut_config_reader cfg;
        super.new(name, parent);
        // An embedded covergroup (declared inside a class) can only be
        // constructed in that class's own new() -- Questa (vlog-60) rejects
        // `cg_foo = new()` from build_phase or anywhere else, so the DUT
        // config read that cp_version/cp_stickyunavail/cp_hasresethaltreq/
        // cp_ndmresetpending need has to happen here too, before those
        // covergroups are constructed below, rather than in build_phase
        // alongside num_harts. uvm_config_db::get() still resolves
        // correctly at this point: tb_top's initial block sets
        // "dut_config_path" via a plain (non-UVM-phased) `initial` block at
        // time 0, and this component's own new() is only ever invoked from
        // its parent's build_phase (via create()), which runs after that.
        //
        // Same dut_config_path key/mechanism dm_checker.sv already uses to
        // construct dm_ref_model (riscv-dbg-vip#117) -- the single declared
        // source of every implementation-defined field this covergroup also
        // needs to correctly classify as reachable/unreachable per DUT.
        if (!uvm_config_db#(string)::get(this, "", "dut_config_path", dut_config_path))
            dut_config_path = "../src/pydebug/dut_configs/ibex.json";
        cfg = new(dut_config_path);
        dut_version         = cfg.get_version();
        dut_hasresethaltreq = cfg.get_bool("hasresethaltreq");
        dut_stickyunavail   = cfg.get_bool("stickyunavail");

        cg_dmi_access      = new();
        cg_dmcontrol_write = new();
        cg_dmstatus_read   = new();
        cg_hart_transition = new();
        cg_command_write   = new();
        cg_abstractcs_read = new();
        cg_progbuf         = new();
        cg_sbcs            = new();
        cg_sb_access       = new();
        cg_dmcs2_write     = new();
        cg_hartinfo_read   = new();
        cg_haltsum0_read   = new();
        cg_data0_access    = new();
        cg_trigger         = new();
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
        bit          is_write;
        bit          is_read;
        logic [15:0] cmd_regno;
        is_write  = (t.dmi_op == dm_defines_pkg::DMI_WRITE);
        is_read   = (t.dmi_op == dm_defines_pkg::DMI_READ);
        cmd_regno = t.dmi_wdata[CMD_REGNO_LSB +: 16];

        cg_dmi_access.sample(t.dmi_addr, t.dmi_op, t.dmi_status);

        // ── Step 1: resolve the READ pending from the PREVIOUS transaction,
        // using THIS transaction's captured dmi_rdata/dmi_status (see
        // pending_read_valid's declaration for why). A BUSY status means the
        // read is still outstanding -- leave it pending and retry on the next
        // shift, exactly as jtag_dmi_read_seq.sv does from the driving side.
        if (pending_read_valid && t.dmi_status != dm_defines_pkg::DMI_STAT_BUSY) begin
            case (pending_read_addr)
                ADDR_DMSTATUS:   sample_dmstatus_read(t.dmi_rdata);
                ADDR_ABSTRACTCS: cg_abstractcs_read.sample(t.dmi_rdata);
                ADDR_HARTINFO:   cg_hartinfo_read.sample(t.dmi_rdata);
                ADDR_HALTSUM0:   cg_haltsum0_read.sample(t.dmi_rdata);
                ADDR_SBCS:       cg_sbcs.sample(t.dmi_rdata, 1'b0);
                default: ;
            endcase
            pending_read_valid = 1'b0;
        end

        // ── Step 2: process THIS transaction's own request. Writes are
        // committed at issue time (dmi_wdata is set by the debugger, not
        // deferred), so those still sample immediately, same as before; reads
        // only ever latch pending_read_addr/valid here -- Step 1 above (on
        // some LATER transaction) is what actually samples them.
        // ── Run-control slice (dmcontrol/dmstatus) ───────────────────────────
        if (t.dmi_addr == ADDR_DMCONTROL && is_write)
            sample_dmcontrol_write(t.dmi_wdata);
        else if (t.dmi_addr == ADDR_DMSTATUS && is_read) begin
            pending_read_addr  = ADDR_DMSTATUS;
            pending_read_valid = 1'b1;
        end

        // ── Abstract command (Access Register): direction + regno class, plus
        //    Program-Buffer execution (postexec) and Trigger-Module CSR access ──
        else if (t.dmi_addr == ADDR_COMMAND && is_write) begin
            cg_command_write.sample(t.dmi_wdata);
            if (t.dmi_wdata[CMD_POSTEXEC])
                cg_progbuf.sample(1'b0, 1'b1);              // execution event
            if (t.dmi_wdata[CMD_TRANSFER] &&
                cmd_regno inside {CSR_TSELECT, CSR_TDATA1, CSR_TDATA2, CSR_TDATA3, CSR_TINFO})
                cg_trigger.sample(
                    cmd_regno,
                    (cmd_regno == CSR_TDATA1) && t.dmi_wdata[CMD_WRITE],
                    last_data0_wr[TRIG_TYPE_LSB_RV32 +: 4]);
        end
        else if (t.dmi_addr == ADDR_ABSTRACTCS && is_read) begin
            pending_read_addr  = ADDR_ABSTRACTCS;
            pending_read_valid = 1'b1;
        end
        else if (t.dmi_addr == ADDR_HARTINFO && is_read) begin
            pending_read_addr  = ADDR_HARTINFO;
            pending_read_valid = 1'b1;
        end

        // ── Abstract data-register operand/result ────────────────────────────
        else if (t.dmi_addr inside {[ADDR_DATA0 : ADDR_DATA11]} && (is_read || is_write)) begin
            cg_data0_access.sample(t.dmi_op);
            if (t.dmi_addr == ADDR_DATA0 && is_write)
                last_data0_wr = t.dmi_wdata;               // stage operand for trigger decode
        end

        // ── Program Buffer write ─────────────────────────────────────────────
        else if (t.dmi_addr inside {[ADDR_PROGBUF0 : ADDR_PROGBUF15]} && is_write)
            cg_progbuf.sample(1'b1, 1'b0);                 // write event

        // ── System Bus Access ────────────────────────────────────────────────
        else if (t.dmi_addr == ADDR_SBCS && is_write)
            cg_sbcs.sample(t.dmi_wdata, 1'b1);
        else if (t.dmi_addr == ADDR_SBCS && is_read) begin
            pending_read_addr  = ADDR_SBCS;
            pending_read_valid = 1'b1;
        end
        else if ((t.dmi_addr == ADDR_SBADDRESS0 || t.dmi_addr == ADDR_SBDATA0)
                 && (is_read || is_write))
            cg_sb_access.sample(t.dmi_addr, t.dmi_op);

        // ── Hart groups / external triggers ──────────────────────────────────
        else if (t.dmi_addr == ADDR_DMCS2 && is_write)
            cg_dmcs2_write.sample(t.dmi_wdata);

        // ── Halt-status summary ──────────────────────────────────────────────
        else if (t.dmi_addr == ADDR_HALTSUM0 && is_read) begin
            pending_read_addr  = ADDR_HALTSUM0;
            pending_read_valid = 1'b1;
        end

        // Any other address/op is a feature not covered in this pass; ignored.
    endfunction

    // ── dmcontrol write ───────────────────────────────────────────────────────
    function void sample_dmcontrol_write(logic [31:0] w);
        logic [19:0] new_hartsel;
        bit          selection_changed;
        bit          rhr;
        bit          nd;

        new_hartsel = {w[DMC_HARTSELHI_LSB +: 10], w[DMC_HARTSELLO_LSB +: 10]};

        // Default-clear the reset-release grace window on every new write --
        // it only covers the reads between the release write and the next
        // write (see the field's own declaration comment); re-armed below if
        // THIS write happens to be the release itself.
        ndmreset_release_pending = 0;

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
        else if (!nd && ndmreset) begin
            cur_ndmreset_ctx = rhr ? ND_DEASSERT_RHR1 : ND_DEASSERT_RHR0;
            // Only arm the grace window when a halt is actually pending on
            // release (haltreq set in this same write) -- TC-RST-001's own
            // baseline release (no haltreq) also reads dmstatus while still
            // in reset beforehand, so a blanket "just released" flag would
            // also catch that case and wrongly keep tagging its very next,
            // already-fully-resolved-to-running read as ST_IN_RESET too.
            // haltreq is the correct discriminator: it is the one thing that
            // tells us a delayed halt-handshake resolution should actually
            // be expected, vs. a release that resolves to running with
            // nothing further to wait for (confirmed both ways via CVA6 UVM
            // regression, 2026-07-25).
            ndmreset_release_pending = w[DMC_HALTREQ];
        end else
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
    //
    // A hart held in ndmreset reads running=1 on both project DUTs --
    // dm_csrs.sv computes allrunning/anyrunning combinationally as
    // ~halted & ~unavailable, with no separate "in reset" encoding, so it is
    // NOT distinguishable from a genuinely running hart via dmstatus bits
    // alone (confirmed against real RTL, riscv-dbg-vip investigation,
    // 2026-07-25). ndmreset itself IS separately observable, though: this
    // subscriber already tracks it from the dmcontrol write that asserted
    // it (the `ndmreset` member below), same as dm_ref_model.sv/predictor.py
    // do for their own state tracking -- consult that instead of trying to
    // infer "in reset" from a read that cannot actually carry it.
    function hart_state_e decode_hart_state(logic [31:0] r);
        if (r[DMS_ANYNONEXISTENT]) return ST_NONEXISTENT;
        if (r[DMS_ANYUNAVAIL])     return ST_UNAVAIL;
        if (r[DMS_ANYHALTED])      return ST_HALTED;
        if (r[DMS_ANYRUNNING] && (ndmreset || ndmreset_release_pending)) return ST_IN_RESET;
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
        `uvm_info("DBG_COV", $sformatf(
            "external-debug coverage: abstract_cmd=%0.2f%% abstractcs=%0.2f%% data0=%0.2f%% progbuf=%0.2f%% sbcs=%0.2f%% sb_access=%0.2f%% dmcs2=%0.2f%% hartinfo=%0.2f%% haltsum0=%0.2f%% trigger=%0.2f%%",
            cg_command_write.get_inst_coverage(),
            cg_abstractcs_read.get_inst_coverage(),
            cg_data0_access.get_inst_coverage(),
            cg_progbuf.get_inst_coverage(),
            cg_sbcs.get_inst_coverage(),
            cg_sb_access.get_inst_coverage(),
            cg_dmcs2_write.get_inst_coverage(),
            cg_hartinfo_read.get_inst_coverage(),
            cg_haltsum0_read.get_inst_coverage(),
            cg_trigger.get_inst_coverage()), UVM_NONE)
    endfunction

endclass : debug_coverage
