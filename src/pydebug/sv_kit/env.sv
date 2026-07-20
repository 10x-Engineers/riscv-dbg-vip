// ══════════════════════════════════════════════════════════════════════════════
// Environment
// ══════════════════════════════════════════════════════════════════════════════
class debug_env extends uvm_env;
    `uvm_component_utils(debug_env)

    jtag_agent       m_agent;
    debug_scoreboard m_scoreboard;
    debug_coverage   m_coverage;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_agent      = jtag_agent::type_id::create("m_agent", this);
        m_scoreboard = debug_scoreboard::type_id::create("m_scoreboard", this);
        m_coverage   = debug_coverage::type_id::create("m_coverage", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        // Both subscribe to the same monitor stream: the scoreboard checks, the
        // coverage model records which architectural bins were reached.
        m_agent.monitor.analysis_port.connect(m_scoreboard.analysis_export);
        m_agent.monitor.analysis_port.connect(m_coverage.analysis_export);
    endfunction
endclass