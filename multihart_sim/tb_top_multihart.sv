`timescale 1ns/1ps

// ─────────────────────────────────────────────────────────────────────────────
// tb_top_multihart.sv — the Debug Module with more than one hart behind it.
//
// Every other testbench in this project wraps a real SoC, and both of them are
// single-hart: CVA6's testharness instantiates `dm_top` with `NrHarts(1)` and
// the Ibex demo system does the same. That makes a whole column of the spec
// unreachable -- `dmstatus`'s all*/any* pairs can never differ, `haltsum0` has
// one interesting bit, and the hart array mask (`hasel`, `hawindowsel`,
// `hawindow`) is tied off -- which is why HS/HG array-mask rows and the
// multi-hart halt/resume features have been sitting unverified.
//
// The Debug Module does not need a processor to believe a hart exists. A hart
// tells the DM what it is doing by executing the debug ROM, which comes down to
// three accesses on the DM's own memory slave (dm_mem.sv:77-83): write
// HaltedAddr, poll the flags word, write ResumingAddr. `dbg_dummy_hart` does
// exactly that and nothing else, so this testbench instantiates `dm_top` with
// `NrHarts` of them and the real DTM, and the DM is none the wiser.
//
// What this is NOT: a model of a processor. There is no register file, no
// abstract-command execution and no program buffer execution here, so the
// scenarios that need those belong on cva6_sim or ibex_sim. This one exists for
// the things that need several harts and nothing else.
//
//   make -C multihart_sim soc_test CFG_FILE=configs/hart_array_uvm.json
// ─────────────────────────────────────────────────────────────────────────────

module tb_top_multihart;

    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import dm::*;
    import debug_pkg::*;

    //: How many harts the DM is built with. Two is enough for every all*/any*
    //: distinction; the hart array's second window would need 33.
    localparam int unsigned NrHarts  = 2;
    localparam int unsigned BusWidth = 32;

    // ── Clock and reset ──────────────────────────────────────────────────
    logic clk, rst_n;
    initial clk = 1'b0;
    always #10 clk = ~clk;                 // 50 MHz, as both SoCs use

    initial begin
        rst_n = 1'b0;
        repeat (10) @(posedge clk);
        rst_n = 1'b1;
    end

    // ── JTAG ─────────────────────────────────────────────────────────────
    jtag_if jtag_vif (.clk(clk), .rst_n(rst_n));

    logic tdo, tdo_oe;
    assign jtag_vif.tdo = tdo;

    // ── DTM ──────────────────────────────────────────────────────────────
    dm::dmi_req_t  dmi_req;
    logic          dmi_req_valid, dmi_req_ready;
    dm::dmi_resp_t dmi_resp;
    logic          dmi_resp_valid, dmi_resp_ready;
    logic          dmi_rst_n;

    dmi_jtag #(
        .IdcodeValue (32'h00000001)
    ) i_dmi_jtag (
        .clk_i            (clk),
        .rst_ni           (rst_n),
        .testmode_i       (1'b0),
        .dmi_rst_no       (dmi_rst_n),
        .dmi_req_o        (dmi_req),
        .dmi_req_valid_o  (dmi_req_valid),
        .dmi_req_ready_i  (dmi_req_ready),
        .dmi_resp_i       (dmi_resp),
        .dmi_resp_ready_o (dmi_resp_ready),
        .dmi_resp_valid_i (dmi_resp_valid),
        .tck_i            (jtag_vif.tck),
        .tms_i            (jtag_vif.tms),
        .trst_ni          (jtag_vif.trst_n),
        .td_i             (jtag_vif.tdi),
        .td_o             (tdo),
        .tdo_oe_o         (tdo_oe)
    );

    // ── The Debug Module ─────────────────────────────────────────────────
    logic [NrHarts-1:0]   debug_req;
    logic                 ndmreset, dmactive;
    logic                 slave_req, slave_we;
    logic [BusWidth-1:0]  slave_addr, slave_wdata, slave_rdata;
    logic [BusWidth/8-1:0] slave_be;

    // The DM's system-bus master. Nothing to talk to in this testbench: SBA
    // has its own scenarios on the SoC testbenches, where there is memory to
    // read. Tied off so a request never hangs -- granted immediately and
    // answered with zero.
    logic                master_req, master_we;
    logic [BusWidth-1:0] master_add, master_wdata;
    logic [BusWidth/8-1:0] master_be;

    dm::hartinfo_t [NrHarts-1:0] hartinfo;
    always_comb begin
        for (int unsigned i = 0; i < NrHarts; i++) begin
            hartinfo[i] = '{zero1: '0, nscratch: 2, zero0: '0, dataaccess: 1'b1,
                            datasize: dm::DataCount, dataaddr: dm::DataAddr};
        end
    end

    dm_top #(
        .NrHarts         (NrHarts),
        .BusWidth        (BusWidth),
        .SelectableHarts ({NrHarts{1'b1}})
    ) i_dm_top (
        .clk_i           (clk),
        .rst_ni          (rst_n),
        .testmode_i      (1'b0),
        .ndmreset_o      (ndmreset),
        .dmactive_o      (dmactive),
        .debug_req_o     (debug_req),
        .unavailable_i   ('0),
        .hartinfo_i      (hartinfo),

        .slave_req_i     (slave_req),
        .slave_we_i      (slave_we),
        .slave_addr_i    (slave_addr),
        .slave_be_i      (slave_be),
        .slave_wdata_i   (slave_wdata),
        .slave_rdata_o   (slave_rdata),

        .master_req_o    (master_req),
        .master_add_o    (master_add),
        .master_we_o     (master_we),
        .master_wdata_o  (master_wdata),
        .master_be_o     (master_be),
        .master_gnt_i    (1'b1),
        .master_r_valid_i(master_req),
        .master_r_rdata_i('0),

        .dmi_rst_ni      (dmi_rst_n),
        .dmi_req_valid_i (dmi_req_valid),
        .dmi_req_ready_o (dmi_req_ready),
        .dmi_req_i       (dmi_req),
        .dmi_resp_valid_o(dmi_resp_valid),
        .dmi_resp_ready_i(dmi_resp_ready),
        .dmi_resp_o      (dmi_resp)
    );

    // ── The harts ────────────────────────────────────────────────────────
    logic [NrHarts-1:0]                   h_req, h_we, h_gnt, h_halted;
    logic [NrHarts-1:0][BusWidth-1:0]     h_addr, h_wdata, h_rdata;
    logic [NrHarts-1:0][BusWidth/8-1:0]   h_be;

    for (genvar i = 0; i < NrHarts; i++) begin : gen_harts
        dbg_dummy_hart #(
            .HartId   (i),
            .BusWidth (BusWidth)
        ) i_hart (
            .clk_i       (clk),
            // ndmreset resets the harts, not the DM: a hart held in reset
            // stops reporting halted, which is what dmstatus should show.
            .rst_ni      (rst_n && !ndmreset),
            .debug_req_i (debug_req[i]),
            .req_o       (h_req[i]),
            .we_o        (h_we[i]),
            .addr_o      (h_addr[i]),
            .wdata_o     (h_wdata[i]),
            .be_o        (h_be[i]),
            .gnt_i       (h_gnt[i]),
            .rdata_i     (h_rdata[i]),
            .halted_o    (h_halted[i])
        );
    end

    dbg_hart_arbiter #(
        .NrHarts  (NrHarts),
        .BusWidth (BusWidth)
    ) i_arbiter (
        .clk_i         (clk),
        .rst_ni        (rst_n),
        .req_i         (h_req),
        .we_i          (h_we),
        .addr_i        (h_addr),
        .wdata_i       (h_wdata),
        .be_i          (h_be),
        .gnt_o         (h_gnt),
        .rdata_o       (h_rdata),
        .slave_req_o   (slave_req),
        .slave_we_o    (slave_we),
        .slave_addr_o  (slave_addr),
        .slave_wdata_o (slave_wdata),
        .slave_be_o    (slave_be),
        .slave_rdata_i (slave_rdata)
    );

    // ── Backdoor into the DM, for the coverage that reads its registers ──
    dbg_dm_backdoor_if dm_backdoor_if (.clk(clk), .rst_n(rst_n));
    assign dm_backdoor_if.dmcontrol    = i_dm_top.i_dm_csrs.dmcontrol_q;
    assign dm_backdoor_if.dmstatus     = i_dm_top.i_dm_csrs.dmstatus;
    assign dm_backdoor_if.abstractcs   = i_dm_top.i_dm_csrs.abstractcs;
    assign dm_backdoor_if.abstractauto = i_dm_top.i_dm_csrs.abstractauto_q;
    assign dm_backdoor_if.command      = i_dm_top.i_dm_csrs.command_q;
    assign dm_backdoor_if.sbcs         = i_dm_top.i_dm_csrs.sbcs_q;
    assign dm_backdoor_if.data0        = i_dm_top.i_dm_csrs.data_q[0];
    assign dm_backdoor_if.data1        = i_dm_top.i_dm_csrs.data_q[1];

    // ── UVM plumbing ─────────────────────────────────────────────────────
    initial begin
        uvm_config_db #(virtual jtag_if)::set(
            null, "uvm_test_top.*", "jtag_vif", jtag_vif);
        uvm_config_db #(virtual dbg_dm_backdoor_if)::set(
            null, "*", "dm_backdoor_vif", dm_backdoor_if);
        // The covergroups size their hart-selection bins from this; left at
        // its default of 1 it would classify hart 1 as nonexistent.
        uvm_config_db #(int unsigned)::set(null, "*", "num_harts", NrHarts);
        uvm_config_db #(string)::set(null, "*", "dut_config_path",
            "../src/pydebug/dut_configs/multihart.json");
    end

    // ── Waves, opt-in ────────────────────────────────────────────────────
    initial begin
        string wave_file;
        if ($test$plusargs("dump_waves")) begin
            wave_file = "sim_outputs/waves.vcd";
            void'($value$plusargs("wave_file=%s", wave_file));
            $dumpfile(wave_file);
            $dumpvars(0, i_dm_top);
            $dumpvars(0, gen_harts[0].i_hart);
            $dumpvars(0, gen_harts[1].i_hart);
            $dumpvars(0, jtag_vif);
        end
    end

    initial begin
        run_test();
    end

endmodule
