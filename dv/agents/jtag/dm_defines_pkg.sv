// =============================================================================
// dm_defines_pkg.sv
// Consolidated constants for the RISC-V Debug Module VIP
// Based on RISC-V Debug Specification 1.0
// =============================================================================

package dm_defines_pkg;

  // ---------------------------------------------------------------------------
  // JTAG DTM parameters
  // ---------------------------------------------------------------------------
  parameter int unsigned JTAG_IR_WIDTH = 5;   // 5-bit IR per RISC-V DTM spec
  parameter int unsigned DMI_ABITS     = 7;   // address bits (DTMCS.abits)
  parameter int unsigned DMI_DR_WIDTH  = DMI_ABITS + 34; // 41 bits total

  // ---------------------------------------------------------------------------
  // JTAG Instructions (5-bit IR)
  // ---------------------------------------------------------------------------
  typedef enum logic [4:0] {
    JTAG_BYPASS  = 5'h1f,
    JTAG_IDCODE  = 5'h01,
    JTAG_DTMCS   = 5'h10,  // Debug Transport Module Control/Status
    JTAG_DMI     = 5'h11   // Debug Module Interface
  } jtag_instr_e;

  // ---------------------------------------------------------------------------
  // DMI Operation Codes
  // ---------------------------------------------------------------------------
  typedef enum logic [1:0] {
    DMI_NOP   = 2'b00,
    DMI_READ  = 2'b01,
    DMI_WRITE = 2'b10
  } dmi_op_e;

  // ---------------------------------------------------------------------------
  // DMI Status Codes (returned in op field of response)
  // ---------------------------------------------------------------------------
  typedef enum logic [1:0] {
    DMI_STAT_SUCCESS = 2'b00,
    DMI_STAT_FAILED  = 2'b10,
    DMI_STAT_BUSY    = 2'b11
  } dmi_stat_e;

  // ---------------------------------------------------------------------------
  // Debug Module Register Addresses (7-bit)
  // From RISC-V Debug Spec 1.0, Table 3.1
  // ---------------------------------------------------------------------------
  parameter logic [6:0] DM_ADDR_DATA0       = 7'h04;
  parameter logic [6:0] DM_ADDR_DATA11      = 7'h0f;
  parameter logic [6:0] DM_ADDR_DMCONTROL   = 7'h10;
  parameter logic [6:0] DM_ADDR_DMSTATUS    = 7'h11;
  parameter logic [6:0] DM_ADDR_HARTINFO    = 7'h12;
  parameter logic [6:0] DM_ADDR_HAWINDOWSEL = 7'h14;
  parameter logic [6:0] DM_ADDR_HAWINDOW    = 7'h15;
  parameter logic [6:0] DM_ADDR_ABSTRACTCS  = 7'h16;
  parameter logic [6:0] DM_ADDR_COMMAND     = 7'h17;
  parameter logic [6:0] DM_ADDR_ABSTRACTAUTO= 7'h18;
  parameter logic [6:0] DM_ADDR_NEXTDM      = 7'h1d;
  parameter logic [6:0] DM_ADDR_PROGBUF0    = 7'h20;
  parameter logic [6:0] DM_ADDR_PROGBUF15   = 7'h2f;
  parameter logic [6:0] DM_ADDR_AUTHDATA    = 7'h30;
  parameter logic [6:0] DM_ADDR_DMCS2       = 7'h32;
  parameter logic [6:0] DM_ADDR_SBCS        = 7'h38;
  parameter logic [6:0] DM_ADDR_SBADDRESS0  = 7'h39;
  parameter logic [6:0] DM_ADDR_SBDATA0     = 7'h3c;
  parameter logic [6:0] DM_ADDR_HALTSUM0    = 7'h40;

  // ---------------------------------------------------------------------------
  // DMSTATUS reset value
  // version=2 (CVA6 dm_top implements RISC-V Debug Spec 0.13),
  // authenticated=1, allrunning=1, anyrunning=1
  // bits: [3:0]=version, [7]=authenticated, [24]=allrunning, [25]=anyrunning
  // ---------------------------------------------------------------------------
  parameter logic [31:0] DMSTATUS_RESET_VAL = 32'h0300_0082;
  //   [3:0]  = 4'h2  (version = 0.13)
  //   [7]    = 1     (authenticated)
  //   [25]   = 1     (anyrunning)
  //   [24]   = 1     (allrunning)

  // ---------------------------------------------------------------------------
  // DTMCS reset value (version=1 for spec 1.0, abits=7)
  // ---------------------------------------------------------------------------
  parameter logic [31:0] DTMCS_RESET_VAL = 32'h00000171;
  //   [3:0]  version = 1
  //   [9:4]  abits   = 7
  //   [11:10] dmistat = 0

endpackage : dm_defines_pkg
