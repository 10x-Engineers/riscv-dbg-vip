// dbg_axi_agent.sv — passive-only AXI agent, parameterised to match the RTL.
//
// No driver and no sequencer, deliberately: this taps buses the DUT already
// drives, and passive-only removes any way to drive a live bus from a test.
class dbg_axi_agent #(
    parameter int unsigned ADDR_W = 64,
    parameter int unsigned DATA_W = 64,
    parameter int unsigned ID_W   = 4
) extends uvm_agent;

    typedef dbg_axi_txn     #(ADDR_W, DATA_W, ID_W) txn_t;
    typedef dbg_axi_monitor #(ADDR_W, DATA_W, ID_W) mon_t;

    mon_t                      m_monitor;
    uvm_analysis_port #(txn_t) ap;

    `uvm_component_param_utils(dbg_axi_agent #(ADDR_W, DATA_W, ID_W))

    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        is_active = UVM_PASSIVE;
        m_monitor = mon_t::type_id::create("m_monitor", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        m_monitor.ap.connect(ap);
    endfunction

endclass
