// JTAG Interface
// Defines the JTAG bus signals for communication with Debug Module

interface jtag_if (
  input logic clk,
  input logic rst_n
);

  logic tck;       // Test Clock
  logic tdi;       // Test Data Input
  logic tdo;       // Test Data Output
  logic tms;       // Test Mode Select
  logic trst_n;    // Test Reset (active low)

  // Driver modport
  modport driver (
    output tck, tdi, tms, trst_n,
    input tdo
  );

  // Monitor modport
  modport monitor (
    input tck, tdi, tdo, tms, trst_n
  );

  // DUT modport
  modport dut (
    input tck, tdi, tms, trst_n,
    output tdo
  );

endinterface : jtag_if
