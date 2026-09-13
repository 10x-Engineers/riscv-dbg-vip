// dbg_axi_pkg.sv — passive AXI monitoring for the debug VIP.
//
// Named dbg_axi_* throughout rather than axi_*: CVA6 vendors pulp-platform's
// `axi_pkg`, and a second `axi_pkg` in one compilation would collide.
//
// Widths are parameters, so a SoC instantiates the tap to match its own bus:
//
//   dbg_axi_agent #(.ADDR_W(32), .DATA_W(32), .ID_W(4)) agent;
//
// and per-run behaviour comes from dbg_axi_cfg through the config_db.
// Bus widths default to a 64-bit SoC and are overridden at compile time for
// anything else, e.g. `+define+DBG_AXI_DATA_W=32` for a 32-bit core. Defines
// rather than UVM parameters so the env and tb agree on one specialisation
// without threading widths through every component.
`ifndef DBG_AXI_ADDR_W
  `define DBG_AXI_ADDR_W 64
`endif
`ifndef DBG_AXI_DATA_W
  `define DBG_AXI_DATA_W 64
`endif
`ifndef DBG_AXI_ID_W
  `define DBG_AXI_ID_W 8
`endif

package dbg_axi_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    `include "dbg_axi_cfg.sv"
    `include "dbg_axi_cfg_reader.sv"
    `include "dbg_axi_txn.sv"
    `include "dbg_axi_monitor.sv"
    `include "dbg_axi_agent.sv"

    // The specialisation this build uses. Everything outside the package --
    // env, tb, config_db keys -- refers to these, so changing a width define
    // moves the whole kit together.
    typedef dbg_axi_txn   #(`DBG_AXI_ADDR_W, `DBG_AXI_DATA_W, `DBG_AXI_ID_W) dbg_axi_txn_t;
    typedef dbg_axi_agent #(`DBG_AXI_ADDR_W, `DBG_AXI_DATA_W, `DBG_AXI_ID_W) dbg_axi_agent_t;

    // Virtual-interface type used as the config_db key. Must live inside the
    // package: a package may not reference compilation-unit scope, so a $unit
    // typedef here is rejected (*E,PKGDOCU).
    typedef virtual dbg_axi_if #(`DBG_AXI_ADDR_W, `DBG_AXI_DATA_W, `DBG_AXI_ID_W) dbg_axi_vif_t;
endpackage
