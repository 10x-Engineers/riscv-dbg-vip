// dbg_hart_backdoor_if.sv — hart-side observability for Debug coverage.
//
// The DM backdoor (dbg_dm_backdoor_if) exposes DM registers, which is enough to
// cover the DMI-visible feature set. It is not enough for Sdext: dcsr, dpc and
// the hart's privilege live in the core, reachable over DMI only through an
// abstract command, and a coverage model that samples only DMI cannot see them
// at all. That is why the wfi single-step defect could never have shown up as a
// coverage hole -- no bin represented "a step over a stalling instruction",
// because nothing sampled which instruction was stepped.
//
// Everything here is observation only. Nothing drives the DUT, and the tb-side
// assigns that fill these signals are the single place RTL hierarchy is
// referenced, so a port rename breaks one file rather than the coverage model.
//
// Signal names follow CVA6's csr_regfile/commit_stage. A different core needs a
// different set of assigns in its tb, not a different interface.

`ifndef DBG_HART_BACKDOOR_IF_SV
`define DBG_HART_BACKDOOR_IF_SV

interface dbg_hart_backdoor_if (
    input logic clk,
    input logic rst_n
);

  // ── Core debug registers (Sdext ch.4) ───────────────────────────────────
  logic [31:0] dcsr;          // csr_regfile_i.dcsr_q, packed
  logic [63:0] dpc;           // csr_regfile_i.dpc_q
  logic [63:0] dscratch0;
  logic [63:0] dscratch1;

  // ── Hart mode and privilege ─────────────────────────────────────────────
  logic        debug_mode;    // csr_regfile_i.debug_mode_q
  logic [1:0]  priv_lvl;      // current privilege, 0=U 1=S 3=M
  logic        wfi_stalled;   // csr_regfile_i.wfi_q -- the stall that deadlocked

  // ── Retirement, for instruction-class coverage ──────────────────────────
  // Classified from CVA6's OWN decode (fu/op from the scoreboard entry) rather
  // than by re-decoding raw bits. The scoreboard entry carries no encoding
  // field, and re-deriving one from the fetch stream would mean maintaining a
  // second decoder that can disagree with the core's.
  logic        commit_valid;         // an instruction retired, or trapped, this cycle
  logic [63:0] commit_pc;

  // ── Interrupt state, for stepie crosses ─────────────────────────────────
  logic        irq_pending;   // any enabled interrupt pending (mip & mie)

  // ── Derived: dcsr field accessors ───────────────────────────────────────
  // Decoded here rather than at each sampling site, so a field-position change
  // is fixed once. Positions are from Sdext "Debug Control and Status".
  function automatic logic [2:0] cause();      return dcsr[8:6];  endfunction
  function automatic logic [1:0] prv();        return dcsr[1:0];  endfunction
  function automatic logic       step();       return dcsr[2];    endfunction
  function automatic logic       stepie();     return dcsr[11];   endfunction
  function automatic logic       stopcount();  return dcsr[10];   endfunction
  function automatic logic       stoptime();   return dcsr[9];    endfunction

  // ── Instruction class of the retiring instruction ───────────────────────
  // The class is what makes a step interesting, and it cannot be recovered
  // from DMI: the debugger sees dpc move but not what sat there.
  //
  // Classified in the TB, not here, and driven in as an already-decoded value.
  // The alternative -- carrying fu/op across and comparing against ordinals --
  // hardcodes ariane_pkg's enum positions into the VIP, where a reordered enum
  // would silently reclassify every instruction instead of failing to compile.
  typedef enum logic [3:0] {
    ICLASS_ORDINARY      = 0,
    ICLASS_COMPRESSED    = 1,
    ICLASS_WFI           = 2,
    ICLASS_BRANCH_TAKEN  = 3,
    ICLASS_BRANCH_NTAKEN = 4,
    ICLASS_TRAPPING      = 5,
    ICLASS_PRIV_CHANGE   = 6,
    ICLASS_LOAD_STORE    = 7,
    ICLASS_WRS           = 8,
    ICLASS_NONE          = 15
  } iclass_e;

  logic [3:0]  commit_iclass;        // an iclass_e, driven by the TB

  function automatic iclass_e instr_class();
    return commit_valid ? iclass_e'(commit_iclass) : ICLASS_NONE;
  endfunction

  // ── Derived: hart mode, for transition coverage ─────────────────────────
  // RUNNING vs DEBUG is what a step round-trips through. Sampling debug_mode
  // directly rather than inferring it from dmstatus is the point: dmstatus can
  // report a hart running while it is in fact stalled inside Debug Mode, which
  // is exactly how the wfi defect presented.
  typedef enum logic [1:0] {HMODE_RUNNING = 0, HMODE_DEBUG = 1} hmode_e;
  function automatic hmode_e hart_mode();
    return debug_mode ? HMODE_DEBUG : HMODE_RUNNING;
  endfunction

endinterface

`endif
