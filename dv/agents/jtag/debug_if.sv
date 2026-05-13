/*
 * debug_if.sv — DMI (Debug Module Interface) SystemVerilog interface.
 *
 * Connects the DPI shim (which receives commands from Python via C)
 * to the UVM driver and ultimately to the RTL DM under test.
 *
 * Signal widths follow the RISC-V Debug Spec v1.0:
 *   addr  : 7-bit DMI address
 *   data  : 32-bit data
 *   op    : 2-bit operation (0=NOP, 1=read, 2=write, 3=reserved)
 */
interface debug_dmi_if (input logic clk);

    logic        rst_n;

    /* DMI request (driven by driver) */
    logic [6:0]  req_addr;
    logic [31:0] req_data;
    logic [1:0]  req_op;     // 1=read, 2=write
    logic        req_valid;

    /* DMI response (driven by DUT/monitor) */
    logic [31:0] rsp_data;
    logic [1:0]  rsp_op;     // 0=ok, 2=fail, 3=busy
    logic        rsp_valid;

    /* Driver clocking block */
    clocking driver_cb @(posedge clk);
        default input #1 output #1;
        output req_addr, req_data, req_op, req_valid, rst_n;
        input  rsp_data, rsp_op, rsp_valid;
    endclocking

    /* Monitor clocking block */
    clocking monitor_cb @(posedge clk);
        default input #1;
        input req_addr, req_data, req_op, req_valid;
        input rsp_data, rsp_op, rsp_valid;
        input rst_n;
    endclocking

    modport driver_mp  (clocking driver_cb,  input clk);
    modport monitor_mp (clocking monitor_cb, input clk);

endinterface
