// ══════════════════════════════════════════════════════════════════════════════
// Environment
// ══════════════════════════════════════════════════════════════════════════════
class debug_env extends uvm_env;
    `uvm_component_utils(debug_env)

    jtag_agent       m_agent;
    debug_scoreboard m_scoreboard;
    debug_coverage   m_coverage;
    dm_checker       m_model_checker;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        m_agent         = jtag_agent::type_id::create("m_agent", this);
        m_scoreboard    = debug_scoreboard::type_id::create("m_scoreboard", this);
        m_coverage      = debug_coverage::type_id::create("m_coverage", this);
        m_model_checker = dm_checker::type_id::create("m_model_checker", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        // All three subscribe to the same monitor stream: the scoreboard checks
        // DMI protocol status, the coverage model records which architectural
        // bins were reached, and the model checker predicts/checks register
        // *values* (dm_ref_model) -- three independent concerns over one
        // observed transaction stream, per VERIFICATION_STRATEGY.md.
        m_agent.monitor.analysis_port.connect(m_scoreboard.analysis_export);
        m_agent.monitor.analysis_port.connect(m_coverage.analysis_export);
        m_agent.monitor.analysis_port.connect(m_model_checker.dmi_export);
    endfunction
endclass