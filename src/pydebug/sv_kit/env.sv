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