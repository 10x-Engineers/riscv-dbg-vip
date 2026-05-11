// =============================================================================
// types.sv  — JTAG VIP type definitions
// Included inside jtag_pkg; references dm_defines_pkg types
// =============================================================================

// ---------------------------------------------------------------------------
// TAP Controller States (IEEE 1149.1)
// ---------------------------------------------------------------------------
typedef enum logic [3:0] {
  TAP_TEST_LOGIC_RESET = 4'h0,
  TAP_RUN_TEST_IDLE    = 4'h1,
  TAP_SELECT_DR_SCAN   = 4'h2,
  TAP_CAPTURE_DR       = 4'h3,
  TAP_SHIFT_DR         = 4'h4,
  TAP_EXIT1_DR         = 4'h5,
  TAP_PAUSE_DR         = 4'h6,
  TAP_EXIT2_DR         = 4'h7,
  TAP_UPDATE_DR        = 4'h8,
  TAP_SELECT_IR_SCAN   = 4'h9,
  TAP_CAPTURE_IR       = 4'hA,
  TAP_SHIFT_IR         = 4'hB,
  TAP_EXIT1_IR         = 4'hC,
  TAP_PAUSE_IR         = 4'hD,
  TAP_EXIT2_IR         = 4'hE,
  TAP_UPDATE_IR        = 4'hF
} tap_state_e;

// ---------------------------------------------------------------------------
// TAP next-state function (pure combinatorial, used by driver & monitor)
// ---------------------------------------------------------------------------
function automatic tap_state_e tap_next_state(tap_state_e curr, logic tms);
  case (curr)
    TAP_TEST_LOGIC_RESET: return tms ? TAP_TEST_LOGIC_RESET : TAP_RUN_TEST_IDLE;
    TAP_RUN_TEST_IDLE   : return tms ? TAP_SELECT_DR_SCAN   : TAP_RUN_TEST_IDLE;
    TAP_SELECT_DR_SCAN  : return tms ? TAP_SELECT_IR_SCAN   : TAP_CAPTURE_DR;
    TAP_CAPTURE_DR      : return tms ? TAP_EXIT1_DR         : TAP_SHIFT_DR;
    TAP_SHIFT_DR        : return tms ? TAP_EXIT1_DR         : TAP_SHIFT_DR;
    TAP_EXIT1_DR        : return tms ? TAP_UPDATE_DR        : TAP_PAUSE_DR;
    TAP_PAUSE_DR        : return tms ? TAP_EXIT2_DR         : TAP_PAUSE_DR;
    TAP_EXIT2_DR        : return tms ? TAP_UPDATE_DR        : TAP_SHIFT_DR;
    TAP_UPDATE_DR       : return tms ? TAP_SELECT_DR_SCAN   : TAP_RUN_TEST_IDLE;
    TAP_SELECT_IR_SCAN  : return tms ? TAP_TEST_LOGIC_RESET : TAP_CAPTURE_IR;
    TAP_CAPTURE_IR      : return tms ? TAP_EXIT1_IR         : TAP_SHIFT_IR;
    TAP_SHIFT_IR        : return tms ? TAP_EXIT1_IR         : TAP_SHIFT_IR;
    TAP_EXIT1_IR        : return tms ? TAP_UPDATE_IR        : TAP_PAUSE_IR;
    TAP_PAUSE_IR        : return tms ? TAP_EXIT2_IR         : TAP_PAUSE_IR;
    TAP_EXIT2_IR        : return tms ? TAP_UPDATE_IR        : TAP_SHIFT_IR;
    TAP_UPDATE_IR       : return tms ? TAP_SELECT_DR_SCAN   : TAP_RUN_TEST_IDLE;
    default             : return TAP_TEST_LOGIC_RESET;
  endcase
endfunction
