// dbg_axi_if.sv — passive AXI4 tap for the debug VIP.
//
// Deliberately a plain signal bundle rather than a reuse of the DUT's own AXI
// interface type: the kit is shared across SoCs that vendor different AXI
// packages (CVA6 has pulp-platform's AXI_BUS, another SoC will have its own),
// and a monitor that names those types cannot compile against both. The SoC's
// tb top assigns into this from whatever it has.
//
// Monitor-only: no modports with outputs, nothing here ever drives the bus.
interface dbg_axi_if #(
    parameter int unsigned ADDR_W = 64,
    parameter int unsigned DATA_W = 64,
    parameter int unsigned ID_W   = 4
) (
    input logic clk,
    input logic rst_n
);
    localparam int unsigned STRB_W = DATA_W / 8;

    // Write address channel
    logic [ID_W-1:0]   aw_id;
    logic [ADDR_W-1:0] aw_addr;
    logic [7:0]        aw_len;
    logic [2:0]        aw_size;
    logic [1:0]        aw_burst;
    logic              aw_valid;
    logic              aw_ready;

    // Write data channel
    logic [DATA_W-1:0] w_data;
    logic [STRB_W-1:0] w_strb;
    logic              w_last;
    logic              w_valid;
    logic              w_ready;

    // Write response channel
    logic [ID_W-1:0]   b_id;
    logic [1:0]        b_resp;
    logic              b_valid;
    logic              b_ready;

    // Read address channel
    logic [ID_W-1:0]   ar_id;
    logic [ADDR_W-1:0] ar_addr;
    logic [7:0]        ar_len;
    logic [2:0]        ar_size;
    logic [1:0]        ar_burst;
    logic              ar_valid;
    logic              ar_ready;

    // Read data channel
    logic [ID_W-1:0]   r_id;
    logic [DATA_W-1:0] r_data;
    logic [1:0]        r_resp;
    logic              r_last;
    logic              r_valid;
    logic              r_ready;
endinterface
