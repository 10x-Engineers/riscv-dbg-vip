// dbg_dm_backdoor_if.sv — backdoor view of the Debug Module's register state.
//
// Front-door checking only sees what a scenario happens to read back: if a
// write to one register corrupted another that nothing reads, no check would
// fire. This carries the DM's own register state so every register can be
// compared after every access -- expected from dm_ref_model, actual from here.
//
// The one place in the VIP that reaches into RTL internals, so it is kept to
// this file plus the per-SoC assigns in the tb. Signal names follow dm_csrs;
// a DM refactor breaks the backdoor, which is inherent to backdoor access.
//
// dmstatus and abstractcs are taken from dm_csrs' assembled values rather than
// from stored state: both are computed combinationally, and it is the assembled
// word a DMI read returns, which is what the model predicts.
interface dbg_dm_backdoor_if (
    input logic clk,
    input logic rst_n
);
    logic [31:0] dmcontrol;      // dmcontrol_q
    logic [31:0] dmstatus;       // assembled
    logic [31:0] abstractcs;     // assembled
    logic [31:0] abstractauto;   // abstractauto_q
    logic [31:0] command;        // command_q
    logic [31:0] sbcs;           // sbcs_q
    logic [31:0] data0;          // data_q[0]
    logic [31:0] data1;          // data_q[1]
endinterface
