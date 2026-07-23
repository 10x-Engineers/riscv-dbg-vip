`timescale 1ns/1ps

// ──────────────────────────────────────────────────────────────────────────────
// tb_top.sv
//
// Testbench top connecting:
//   jtag_agent (JTAG VIP)  →  dmi_jtag RTL  →  dm_top RTL
//
// The dm_top memory bus ports (slave / master) are tied off because
// no CPU or memory is connected in this VIP-only environment.
// ──────────────────────────────────────────────────────────────────────────────
module tb_top;

    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import dm::*;           // dm::dmi_req_t, dm::dmi_resp_t, dm::hartinfo_t
    import debug_pkg::*;

    // ── System clock & reset ───────────────────────────────────────────────
    logic clk;
    logic rst_n;

    initial clk = 1'b0;
    always  #5 clk = ~clk;  // 100 MHz

    initial begin
        rst_n = 1'b0;
        repeat (10) @(posedge clk);
        rst_n = 1'b1;
    end

    // ── JTAG interface ─────────────────────────────────────────────────────
    jtag_if jtag_vif (.clk(clk), .rst_n(rst_n));

    // ── OpenOCD Remote Bitbang ─────────────────────────────────────────────
    logic bb_tck, bb_tms, bb_tdi, bb_trstn, bb_quit;
    logic jtag_use_openocd;
    
    initial begin
        string jtag_master;
        jtag_use_openocd = 1'b0;
        if ($value$plusargs("JTAG_MASTER=%s", jtag_master)) begin
            if (jtag_master == "openocd") begin
                jtag_use_openocd = 1'b1;
            end
        end
    end

    jtag_bitbang #(
        .PORT(9824)
    ) i_jtag_bitbang (
        .clk_i(clk),
        .rst_ni(rst_n),
        .enable_i(jtag_use_openocd),
        .tck_o(bb_tck),
        .tms_o(bb_tms),
        .tdi_o(bb_tdi),
        .trstn_o(bb_trstn),
        .tdo_i(jtag_vif.tdo),
        .quit_o(bb_quit)
    );

    // ── JTAG Mux ───────────────────────────────────────────────────────────
    logic muxed_tck, muxed_tms, muxed_tdi, muxed_trstn;
    assign muxed_tck   = jtag_use_openocd ? bb_tck   : jtag_vif.tck;
    assign muxed_tms   = jtag_use_openocd ? bb_tms   : jtag_vif.tms;
    assign muxed_tdi   = jtag_use_openocd ? bb_tdi   : jtag_vif.tdi;
    assign muxed_trstn = jtag_use_openocd ? bb_trstn : jtag_vif.trst_n;

    // ── DMI wires (dmi_jtag → dm_top) ─────────────────────────────────────
    logic          dmi_rst_n;
    dm::dmi_req_t  dmi_req;
    logic          dmi_req_valid;
    logic          dmi_req_ready;
    dm::dmi_resp_t dmi_resp;
    logic          dmi_resp_valid;
    logic          dmi_resp_ready;

    // ── DUT: dmi_jtag (JTAG TAP + CDC) ────────────────────────────────────
    dmi_jtag #(
        .IdcodeValue(32'hDEAD_0001)
    ) u_dmi_jtag (
        .clk_i          (clk),
        .rst_ni         (rst_n),
        .testmode_i     (1'b0),
        // DMI output to dm_top
        .dmi_rst_no     (dmi_rst_n),
        .dmi_req_o      (dmi_req),
        .dmi_req_valid_o(dmi_req_valid),
        .dmi_req_ready_i(dmi_req_ready),
        .dmi_resp_i     (dmi_resp),
        .dmi_resp_ready_o(dmi_resp_ready),
        .dmi_resp_valid_i(dmi_resp_valid),
        // JTAG pins from the VIP interface
        .tck_i          (muxed_tck),
        .tms_i          (muxed_tms),
        .trst_ni        (muxed_trstn),
        .td_i           (muxed_tdi),
        .td_o           (jtag_vif.tdo),
        .tdo_oe_o       ()   // not needed in this TB
    );

    // ── DUT: dm_top (RISC-V Debug Module) ─────────────────────────────────
    //
    // Memory bus tie-offs:
    //   slave_*  — debug-module internal bus (program buffer / data regs)
    //              driven low; dm_top will never receive a bus request.
    //   master_* — system-bus access (SBA) outputs
    //              gnt and r_valid tied high/low so the SBA FSM stays idle.
    //
    // ── Dummy Core (simulates CPU interacting with DM memory bus) ──────────
    logic        slave_req;
    logic        slave_we;
    logic [31:0] slave_addr;
    logic [31:0] slave_wdata;
    logic [31:0] slave_rdata;
    logic [0:0]  debug_req_o;

    logic is_halted;
    initial begin
        slave_req = 1'b0;
        slave_we = 1'b0;
        slave_addr = 32'h0;
        slave_wdata = 32'h0;
        is_halted = 1'b0;

        forever begin
            @(posedge clk);
            if (rst_n) begin
                if (!is_halted && debug_req_o[0]) begin
                    // CPU receives halt request: jump to debug ROM and write HaltedAddr
                    repeat(5) @(posedge clk);
                    slave_req   <= 1'b1;
                    slave_we    <= 1'b1;
                    slave_addr  <= 32'h1100; // DmBaseAddress + HaltedAddr
                    slave_wdata <= 32'h0;
                    @(posedge clk);
                    slave_req   <= 1'b0;
                    is_halted   = 1'b1;
                end
                
                if (is_halted) begin
                    // Polling FlagsBaseAddr
                    slave_req  <= 1'b1;
                    slave_we   <= 1'b0;
                    slave_addr <= 32'h1400; // DmBaseAddress + FlagsBaseAddr
                    @(posedge clk);
                    slave_req  <= 1'b0;
                    @(posedge clk); // wait for rdata (SRAM latency is 1)
                    
                    if (slave_rdata[1]) begin // resume flag
                        slave_req   <= 1'b1;
                        slave_we    <= 1'b1;
                        slave_addr  <= 32'h1108; // DmBaseAddress + ResumingAddr
                        slave_wdata <= 32'h0;
                        @(posedge clk);
                        slave_req   <= 1'b0;
                        is_halted   = 1'b0;
                    end else if (slave_rdata[0]) begin // go flag
                        slave_req   <= 1'b1;
                        slave_we    <= 1'b1;
                        slave_addr  <= 32'h1104; // DmBaseAddress + GoingAddr
                        slave_wdata <= 32'h0;
                        @(posedge clk);
                        slave_req   <= 1'b0;
                        
                        // Simulate executing abstract command
                        repeat(5) @(posedge clk);
                        
                        // Re-halt
                        slave_req   <= 1'b1;
                        slave_we    <= 1'b1;
                        slave_addr  <= 32'h1100; // DmBaseAddress + HaltedAddr
                        slave_wdata <= 32'h0;
                        @(posedge clk);
                        slave_req   <= 1'b0;
                    end else begin
                        repeat(5) @(posedge clk); // wait before polling again
                    end
                end
            end
        end
    end

    dm_top #(
        .NrHarts       (1),
        .BusWidth      (32),
        .DmBaseAddress (32'h0000_1000)
    ) u_dm_top (
        .clk_i          (clk),
        .rst_ni         (rst_n),
        .testmode_i     (1'b0),

        // Status outputs (not checked in this TB)
        .ndmreset_o     (),
        .dmactive_o     (),
        .debug_req_o    (debug_req_o),

        // Hart info — single hart, all defaults
        .unavailable_i  (1'b0),
        .hartinfo_i     ('0),

        // ── Slave bus (driven by dummy core to simulate CPU interactions) 
        .slave_req_i    (slave_req),
        .slave_we_i     (slave_we),
        .slave_addr_i   (slave_addr),
        .slave_be_i     (4'hF),
        .slave_wdata_i  (slave_wdata),
        .slave_rdata_o  (slave_rdata),

        // ── Master bus (SBA — always grant, no read responses) ───────────
        .master_req_o   (),
        .master_add_o   (),
        .master_we_o    (),
        .master_wdata_o (),
        .master_be_o    (),
        .master_gnt_i   (1'b1),   // always grant so SBA FSM doesn't stall
        .master_r_valid_i(1'b0),  // no read data
        .master_r_rdata_i(32'h0),

        // ── DMI from dmi_jtag ─────────────────────────────────────────────
        .dmi_rst_ni     (dmi_rst_n),
        .dmi_req_valid_i(dmi_req_valid),
        .dmi_req_ready_o(dmi_req_ready),
        .dmi_req_i      (dmi_req),
        .dmi_resp_valid_o(dmi_resp_valid),
        .dmi_resp_ready_i(dmi_resp_ready),
        .dmi_resp_o     (dmi_resp)
    );

    // ── Push JTAG virtual interface into UVM config DB ─────────────────────
    initial begin
        uvm_config_db #(virtual jtag_if)::set(
            null, "uvm_test_top.*", "jtag_vif", jtag_vif);
    end

    // ── Monitor bb_quit and signal via config_db ──────────────────────────
    initial begin
        if (jtag_use_openocd) begin
            @(posedge bb_quit);
            uvm_config_db #(int)::set(null, "*", "bb_quit", 1);
        end
    end

    // ── Watchdog ───────────────────────────────────────────────────────────
    // initial begin
    //     if (jtag_use_openocd)
    //         #100_000_000;  // 100 ms for OpenOCD (bitbang is slow)
    //     else
    //         #10_000_000;   // 10 ms for UVM
    //     `uvm_fatal("TIMEOUT", "Simulation watchdog expired")
    // end

    // ── UVM start ──────────────────────────────────────────────────────────
    initial run_test("debug_test");

endmodule
