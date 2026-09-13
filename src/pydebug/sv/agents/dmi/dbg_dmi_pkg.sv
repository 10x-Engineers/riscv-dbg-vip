// dbg_dmi_pkg.sv — passive monitoring of the Debug Module Interface.
//
// The DMI sits between the DTM (dmi_jtag) and the DM. Tapping it is what lets
// the checker verify the DTM itself: every DMI request the debugger shifts in
// over JTAG must appear here with the same addr/op/data, and the response must
// come back matching what JTAG shifts out.
package dbg_dmi_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    `include "dbg_dmi_txn.sv"
    `include "dbg_dmi_monitor.sv"
    `include "dbg_dmi_agent.sv"

    typedef virtual dbg_dmi_if dbg_dmi_vif_t;
endpackage
