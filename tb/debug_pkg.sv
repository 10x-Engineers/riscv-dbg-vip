/*
 * debug_pkg.sv — UVM debug package (JTAG VIP edition).
 *
 * The DMI-level debug_agent has been replaced by the JTAG VIP agent
 * (jtag_agent from jtag_pkg).  Python commands are translated into
 * jtag_txn_c items that drive the real dmi_jtag + dm_top RTL.
 *
 * Contains (in dependency order):
 *   jtag_dmi_write_seq  — single IR+DR shift for a DMI write
 *   jtag_dmi_read_seq   — two-phase IR+DR shifts for a DMI read
 *   jtag_tap_reset_seq  — navigate TAP back to Test-Logic-Reset
 *   debug_scoreboard    — checks DMI status from JTAG monitor
 *   debug_env           — environment (jtag_agent + scoreboard)
 *   python_bridge       — reusable DPI command loop (TB-agnostic)
 *   debug_test          — top-level test
 */

package debug_pkg;

    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import jtag_pkg::*;   // brings in jtag_txn_c, jtag_agent, etc.

// ══════════════════════════════════════════════════════════════════════════════
// DPI imports — implemented in uvm_bridge.c
// ══════════════════════════════════════════════════════════════════════════════
import "DPI-C" function int  uvm_bridge_start();
import "DPI-C" function void uvm_bridge_stop();
import "DPI-C" function int  dpi_bridge_get_req(output int op, output int addr, output int unsigned data);
import "DPI-C" function void dpi_bridge_put_rsp(int unsigned data);

// ══════════════════════════════════════════════════════════════════════════════
// JTAG DMI Write Sequence
// Performs one IR+DR shift: {addr, data, DMI_WRITE}
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_write_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_write_seq)

    logic [6:0]  addr;
    logic [31:0] data;

    function new(string name = "jtag_dmi_write_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn = new("dmi_wr");
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = data;
        txn.dmi_op    = 2'b10;  // DMI_WRITE
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);
    endtask
endclass

// ══════════════════════════════════════════════════════════════════════════════
// JTAG DMI Read Sequence
// Phase-1: IR+DR shift with op=READ → queues read in dmi_jtag FSM
// Phase-2: IR+DR shift with op=NOP  → captures the result; retries if BUSY
// ══════════════════════════════════════════════════════════════════════════════
class jtag_dmi_read_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_dmi_read_seq)

    logic [6:0]  addr;
    logic [31:0] rsp_data;

    function new(string name = "jtag_dmi_read_seq");
        super.new(name);
    endfunction

    task body();
        jtag_txn_c txn;

        // ── Phase 1: issue DMI READ ─────────────────────────────────────────
        txn = new("dmi_rd_req");
        txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
        txn.dmi_addr  = addr;
        txn.dmi_wdata = 32'h0;
        txn.dmi_op    = 2'b01;  // DMI_READ
        txn.pack_dmi();
        start_item(txn);
        finish_item(txn);

        // ── Phase 2: poll with NOP until result is captured ─────────────────
        do begin
            txn = new("dmi_rd_cap");
            txn.phase     = jtag_txn_c::PH_IR_THEN_DR;
            txn.dmi_addr  = 7'h0;
            txn.dmi_wdata = 32'h0;
            txn.dmi_op    = 2'b00;  // DMI_NOP
            txn.pack_dmi();
            start_item(txn);
            finish_item(txn);
            // txn.dmi_rdata / dmi_status populated by driver via unpack_dmi()
        end while (txn.dmi_status == 2'b11);  // retry while DMI_BUSY

        rsp_data = txn.dmi_rdata;
    endtask
endclass

// ══════════════════════════════════════════════════════════════════════════════
// JTAG TAP Reset Sequence
// Drives TMS=1 for 5 TCK cycles to force Test-Logic-Reset from any state.
// Implemented as an IR-only transaction with ir_val=5'h1f (BYPASS).
// ══════════════════════════════════════════════════════════════════════════════
class jtag_tap_reset_seq extends uvm_sequence #(jtag_txn_c);
    `uvm_object_utils(jtag_tap_reset_seq)

    function new(string name = "jtag_tap_reset_seq");
        super.new(name);
    endfunction

    task body();
        // Send BYPASS IR — the driver navigates via TMS=1 enough times
        // to pass through Test-Logic-Reset on the way to Shift-IR, which
        // effectively resets the TAP.
        jtag_txn_c txn = new("tap_rst");
        txn.phase  = jtag_txn_c::PH_IR_ONLY;
        txn.ir_val = 5'h1f;  // BYPASS
        txn.ir_len = 5;
        start_item(txn);
        finish_item(txn);
    endtask
endclass

// ══════════════════════════════════════════════════════════════════════════════
// Scoreboard — checks DMI status from the JTAG monitor's analysis port
// ══════════════════════════════════════════════════════════════════════════════
class debug_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(debug_scoreboard)

    uvm_analysis_imp #(jtag_txn_c, debug_scoreboard) analysis_export;
    int unsigned total_checked;
    int unsigned total_errors;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        analysis_export = new("analysis_export", this);
    endfunction

    function void write(jtag_txn_c item);
        total_checked++;
        if (item.dmi_status == 2'b10 || item.dmi_status == 2'b11) begin
            total_errors++;
            `uvm_error("SCB", $sformatf("DMI error status=%02b on %s",
                        item.dmi_status, item.convert2string()))
        end else begin
            `uvm_info("SCB", $sformatf("[tx#%0d] %s ✓", total_checked,
                       item.convert2string()), UVM_HIGH)
        end
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SCB", $sformatf("Checked=%0d Errors=%0d",
                  total_checked, total_errors), UVM_NONE)
    endfunction
endclass

// ══════════════════════════════════════════════════════════════════════════════
// Environment
// ══════════════════════════════════════════════════════════════════════════════
class debug_env extends uvm_env;
    `uvm_component_utils(debug_env)

    jtag_agent       m_agent;
    debug_scoreboard m_scoreboard;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_agent      = jtag_agent::type_id::create("m_agent", this);
        m_scoreboard = debug_scoreboard::type_id::create("m_scoreboard", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        m_agent.monitor.analysis_port.connect(m_scoreboard.analysis_export);
    endfunction
endclass

// ══════════════════════════════════════════════════════════════════════════════
// Python Bridge — REUSABLE component for third-party integration
//
// Usage in any test:
//   python_bridge m_bridge;
//   m_bridge = python_bridge::type_id::create("m_bridge", this);
//   ...
//   m_bridge.serve(my_jtag_agent.sequencer);
//
// op=1 → DMI read  (2-phase JTAG DR shift)
// op=2 → DMI write (1-phase JTAG DR shift)
// op=3 → TAP reset
// op=4 → shutdown
// ══════════════════════════════════════════════════════════════════════════════
class python_bridge extends uvm_component;
    `uvm_component_utils(python_bridge)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    task serve(uvm_sequencer #(jtag_txn_c) sqr);
        int rc;

        rc = uvm_bridge_start();
        if (rc != 0)
            `uvm_fatal("BRIDGE", "uvm_bridge_start() failed")
        `uvm_info("BRIDGE", "C bridge started — waiting for Python client", UVM_NONE)

        forever begin
            int op, addr;
            int unsigned data;

            if (dpi_bridge_get_req(op, addr, data)) begin
                case (op)
                    1: begin  // DMI Read
                        jtag_dmi_read_seq r_seq;
                        r_seq = jtag_dmi_read_seq::type_id::create("r_seq");
                        r_seq.addr = addr[6:0];
                        r_seq.start(sqr);
                        dpi_bridge_put_rsp(r_seq.rsp_data);
                        `uvm_info("BRIDGE", $sformatf(
                            "READ  addr=0x%02h → data=0x%08h", addr, r_seq.rsp_data),
                            UVM_MEDIUM)
                    end
                    2: begin  // DMI Write
                        jtag_dmi_write_seq w_seq;
                        w_seq = jtag_dmi_write_seq::type_id::create("w_seq");
                        w_seq.addr = addr[6:0];
                        w_seq.data = data;
                        w_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("BRIDGE", $sformatf(
                            "WRITE addr=0x%02h ← data=0x%08h", addr, data),
                            UVM_MEDIUM)
                    end
                    3: begin  // TAP Reset
                        jtag_tap_reset_seq rst_seq;
                        rst_seq = jtag_tap_reset_seq::type_id::create("rst_seq");
                        rst_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("BRIDGE", "TAP RESET", UVM_MEDIUM)
                    end
                    4: begin  // Shutdown
                        `uvm_info("BRIDGE",
                            "Shutdown requested by Python — exiting command loop",
                            UVM_NONE)
                        dpi_bridge_put_rsp(0);
                        uvm_bridge_stop();
                        return;
                    end
                    default: begin
                        `uvm_warning("BRIDGE",
                            $sformatf("Unknown op=%0d — ignoring", op))
                        dpi_bridge_put_rsp(0);
                    end
                endcase
            end else begin
                #1ns;
            end
        end
    endtask
endclass

// ══════════════════════════════════════════════════════════════════════════════
// Test
// ══════════════════════════════════════════════════════════════════════════════
class debug_test extends uvm_test;
    `uvm_component_utils(debug_test)

    debug_env     m_env;
    python_bridge m_bridge;
    bit bb_quit;

    string python_seq   = "../run.py --config ../configs/halt_uvm.json";
    string python_extra = "";
    string jtag_master  = "uvm";

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_env    = debug_env::type_id::create("m_env", this);
        m_bridge = python_bridge::type_id::create("m_bridge", this);

        void'($value$plusargs("PYTHON_SEQ=%s",   python_seq));
        void'($value$plusargs("PYTHON_EXTRA=%s", python_extra));
        void'($value$plusargs("JTAG_MASTER=%s",  jtag_master));

        uvm_config_db#(int)::get(null, "*", "bb_quit", bb_quit);  // initialize quit flag in config_db
    endfunction

    task run_phase(uvm_phase phase);
        string cmd;

        phase.raise_objection(this);

        if (jtag_master == "openocd") begin
            // In OpenOCD mode: sim just runs the bitbang server.
            // OpenOCD and Python are started externally by the Makefile.
            `uvm_info("TEST", "OpenOCD mode — bitbang server active, waiting for quit signal", UVM_NONE)
            forever begin
                int quit_flag;
                #100_000;  // check every 100us
                if (uvm_config_db#(int)::get(null, "*", "bb_quit", quit_flag) &&
                    quit_flag != 0) begin
                    `uvm_info("TEST", "Remote bitbang client disconnected — ending sim", UVM_NONE)
                    break;
                end
            end
        end else begin
            // UVM mode: launch Python and serve bridge requests
            cmd = $sformatf("python3 -u %s %s 2>&1 &", python_seq, python_extra);
            `uvm_info("TEST", $sformatf("Launching: %s", cmd), UVM_NONE)
            void'($system(cmd));
            m_bridge.serve(m_env.m_agent.sequencer);
        end

        `uvm_info("TEST", "Session complete — ending simulation", UVM_NONE)
        // wait(bb_quit==1);  // ensure bitbang server has time to print final messages
        // `uvm_info("TEST", "Session complete — ending simulation2", UVM_NONE)
        phase.drop_objection(this);
    endtask
endclass

endpackage
