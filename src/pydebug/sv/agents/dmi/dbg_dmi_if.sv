// dbg_dmi_if.sv — passive tap on the Debug Module Interface.
//
// The DMI is not AXI. It is the DM's own valid/ready request-response bus,
// carried between the DTM (dmi_jtag) and dm_top as dm::dmi_req_t/dmi_resp_t.
// Flattened to plain signals here so the VIP does not depend on the DUT's
// package types -- another SoC's DM may spell the structs differently.
//
// Monitor-only: nothing here ever drives.
interface dbg_dmi_if (
    input logic clk,
    input logic rst_n
);
    // Request channel (DTM -> DM)
    logic        req_valid;
    logic        req_ready;
    logic [6:0]  req_addr;
    logic [1:0]  req_op;      // 0 = nop, 1 = read, 2 = write
    logic [31:0] req_data;

    // Response channel (DM -> DTM)
    logic        resp_valid;
    logic        resp_ready;
    logic [31:0] resp_data;
    logic [1:0]  resp_status; // 0 = success
endinterface
