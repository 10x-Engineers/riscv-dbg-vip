// dbg_axi_monitor.sv — passive, parameterised AXI4 monitor.
//
// Reassembles bursts from the five channels and reports one line per completed
// transaction, so the log shows what the bus carried rather than raw
// handshakes. Reads and writes run in parallel, since AXI lets them overlap.
//
// Widths come from the RTL via the parameters; per-run behaviour (naming,
// address window, annotation, verbosity) comes from dbg_axi_cfg.
class dbg_axi_monitor #(
    parameter int unsigned ADDR_W = 64,
    parameter int unsigned DATA_W = 64,
    parameter int unsigned ID_W   = 4
) extends uvm_monitor;

    typedef dbg_axi_txn #(ADDR_W, DATA_W, ID_W) txn_t;
    typedef virtual dbg_axi_if #(ADDR_W, DATA_W, ID_W) vif_t;

    vif_t                      vif;
    dbg_axi_cfg                cfg;
    uvm_analysis_port #(txn_t) ap;

    `uvm_component_param_utils(dbg_axi_monitor #(ADDR_W, DATA_W, ID_W))

    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db #(vif_t)::get(this, "", "vif", vif))
            `uvm_fatal("AXI_MON", $sformatf("no virtual dbg_axi_if for %s", get_full_name()))
        // A tap with no explicit config still works, on defaults.
        if (!uvm_config_db #(dbg_axi_cfg)::get(this, "", "cfg", cfg)) begin
            cfg = dbg_axi_cfg::type_id::create("cfg");
            `uvm_info("AXI_MON",
                $sformatf("%s: no dbg_axi_cfg given, using defaults", get_full_name()),
                UVM_HIGH)
        end
    endfunction

    function void start_of_simulation_phase(uvm_phase phase);
        super.start_of_simulation_phase(phase);
        `uvm_info("AXI_MON",
            $sformatf("tap '%s': %0d-bit addr, %0d-bit data, %0d-bit id%s",
                      cfg.bus_name, ADDR_W, DATA_W, ID_W,
                      (!cfg.monitor_writes) ? ", reads only" :
                      (!cfg.monitor_reads)  ? ", writes only" : ""),
            UVM_LOW)
    endfunction

    task run_phase(uvm_phase phase);
        fork
            if (cfg.monitor_writes) monitor_writes();
            if (cfg.monitor_reads)  monitor_reads();
        join
    endtask

    // Report only if the address is in the configured window; annotate it if
    // the config named that region.
    protected function void report_txn(txn_t txn);
        if (!cfg.in_window(txn.addr)) return;
        txn.region = cfg.annotate(txn.addr);
        `uvm_info($sformatf("AXI_MON:%s", cfg.bus_name), txn.convert2string(), cfg.log_level)
        ap.write(txn);
    endfunction

    // AW carries the address, W the data beats, B the response.
    task monitor_writes();
        txn_t txn;
        forever begin
            @(posedge vif.clk);
            if (!vif.rst_n) continue;

            if (vif.aw_valid && vif.aw_ready) begin
                txn = txn_t::type_id::create("wr");
                txn.dir     = txn_t::AXI_WRITE;
                txn.addr    = vif.aw_addr;
                txn.len     = vif.aw_len;
                txn.size    = vif.aw_size;
                txn.burst   = vif.aw_burst;
                txn.id      = vif.aw_id;
                txn.t_start = $time;

                do begin
                    @(posedge vif.clk);
                    if (vif.w_valid && vif.w_ready) begin
                        txn.data.push_back(vif.w_data);
                        txn.strb.push_back(vif.w_strb);
                    end
                end while (!(vif.w_valid && vif.w_ready && vif.w_last));

                do @(posedge vif.clk); while (!(vif.b_valid && vif.b_ready));
                txn.resp  = vif.b_resp;
                txn.t_end = $time;

                report_txn(txn);
            end
        end
    endtask

    task monitor_reads();
        txn_t txn;
        forever begin
            @(posedge vif.clk);
            if (!vif.rst_n) continue;

            if (vif.ar_valid && vif.ar_ready) begin
                txn = txn_t::type_id::create("rd");
                txn.dir     = txn_t::AXI_READ;
                txn.addr    = vif.ar_addr;
                txn.len     = vif.ar_len;
                txn.size    = vif.ar_size;
                txn.burst   = vif.ar_burst;
                txn.id      = vif.ar_id;
                txn.t_start = $time;

                do begin
                    @(posedge vif.clk);
                    if (vif.r_valid && vif.r_ready) begin
                        txn.data.push_back(vif.r_data);
                        txn.resp = vif.r_resp;   // last beat's response wins
                    end
                end while (!(vif.r_valid && vif.r_ready && vif.r_last));

                txn.t_end = $time;
                report_txn(txn);
            end
        end
    endtask

endclass
