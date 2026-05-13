// ══════════════════════════════════════════════════════════════════════════════
// Test
// ══════════════════════════════════════════════════════════════════════════════
class debug_test extends uvm_test;
    `uvm_component_utils(debug_test)

    debug_env     m_env;
    python_bridge m_bridge;
    bit bb_quit;

    string python_seq   = "../lib/python/run.py --config ../configs/halt_uvm.json";
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
