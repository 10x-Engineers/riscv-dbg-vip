// dbg_dmi_monitor.sv — passive DMI monitor.
//
// Pairs each accepted request with the response that follows it. The DM
// answers in order and one at a time, so a single outstanding slot is enough;
// anything deeper would be modelling a DM this VIP does not target.
class dbg_dmi_monitor extends uvm_monitor;

    virtual dbg_dmi_if vif;
    uvm_analysis_port #(dbg_dmi_txn) ap;

    `uvm_component_utils(dbg_dmi_monitor)

    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db #(virtual dbg_dmi_if)::get(this, "", "vif", vif))
            `uvm_fatal("DMI_MON", $sformatf("no virtual dbg_dmi_if for %s", get_full_name()))
    endfunction

    task run_phase(uvm_phase phase);
        dbg_dmi_txn pending;
        forever begin
            @(posedge vif.clk);
            if (!vif.rst_n) begin
                pending = null;
                continue;
            end

            // Request accepted
            if (vif.req_valid && vif.req_ready) begin
                pending        = dbg_dmi_txn::type_id::create("dmi");
                pending.addr   = vif.req_addr;
                pending.op     = vif.req_op;
                pending.wdata  = vif.req_data;
                pending.t_req  = $time;
                // A nop carries no response worth waiting for; emit it now so
                // it cannot block the slot.
                if (pending.op == 2'd0) begin
                    ap.write(pending);
                    pending = null;
                end
            end

            // Response accepted -- belongs to the outstanding request
            if (vif.resp_valid && vif.resp_ready && pending != null) begin
                pending.rdata    = vif.resp_data;
                pending.status   = vif.resp_status;
                pending.has_resp = 1'b1;
                pending.t_resp   = $time;
                ap.write(pending);
                pending = null;
            end
        end
    endtask

endclass
