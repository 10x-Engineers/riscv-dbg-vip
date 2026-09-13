// dbg_dmi_agent.sv — passive-only DMI agent.
class dbg_dmi_agent extends uvm_agent;

    dbg_dmi_monitor m_monitor;
    uvm_analysis_port #(dbg_dmi_txn) ap;

    `uvm_component_utils(dbg_dmi_agent)

    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        is_active = UVM_PASSIVE;
        m_monitor = dbg_dmi_monitor::type_id::create("m_monitor", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        m_monitor.ap.connect(ap);
    endfunction

endclass
