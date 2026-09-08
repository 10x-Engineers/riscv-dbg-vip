// ══════════════════════════════════════════════════════════════════════════════
// Environment
// ══════════════════════════════════════════════════════════════════════════════
class debug_env extends uvm_env;
    `uvm_component_utils(debug_env)

    jtag_agent       m_agent;

    // Optional AXI taps. Built only for the buses the SoC's tb actually
    // published a virtual interface for, so an SoC with no AXI (Ibex, which
    // is OBI) simply gets none and nothing here needs to know about it.
    dbg_axi_agent_t  m_axi_agents[$];
    string           m_axi_names[$];
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

        build_axi_taps();
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
    // Tap settings come from axi_configs/<dut>_axi.json, never from the tb:
    // naming, windowing, annotation and verbosity are DV decisions, and a
    // design-side file driving them could bias what the checkers see. The tb
    // contributes only the physical interfaces, published as axi_vif_<name>.
    //
    // A tap in the file with no published interface is skipped with a warning;
    // an interface with no entry in the file is not built. The file is the
    // enable switch.
    protected function void build_axi_taps();
        string              cfg_path;
        dbg_axi_cfg_reader  reader;
        dbg_axi_cfg         cfgs[$];
        dbg_axi_vif_t       vif;
        dbg_axi_agent_t     agent;

        if (!uvm_config_db #(string)::get(this, "", "axi_config_path", cfg_path)) begin
            `uvm_info("ENV", "no axi_config_path set -- no AXI taps built", UVM_HIGH)
            return;
        end

        reader = new(cfg_path);
        reader.get_taps(cfgs);

        foreach (cfgs[i]) begin
            string name = cfgs[i].bus_name;
            if (!uvm_config_db #(dbg_axi_vif_t)::get(
                    this, "", $sformatf("axi_vif_%s", name), vif)) begin
                `uvm_warning("ENV", $sformatf(
                    "%s lists tap '%s' but the tb published no interface for it -- skipped",
                    cfg_path, name))
                continue;
            end
            agent = dbg_axi_agent_t::type_id::create($sformatf("m_axi_%s", name), this);
            uvm_config_db #(dbg_axi_vif_t)::set(this, $sformatf("m_axi_%s.*", name), "vif", vif);
            uvm_config_db #(dbg_axi_cfg)::set(this, $sformatf("m_axi_%s.*", name), "cfg", cfgs[i]);
            m_axi_agents.push_back(agent);
            m_axi_names.push_back(name);
        end
    endfunction

endclass