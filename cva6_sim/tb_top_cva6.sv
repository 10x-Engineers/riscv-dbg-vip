`timescale 1ns/1ps

// ──────────────────────────────────────────────────────────────────────────────
// tb_top_soc.sv
//
// Testbench top connecting:
//   jtag_agent (JTAG VIP) / OpenOCD Bitbang  →  Full CVA6 SoC (ariane_testharness)
//
// Supports preloading any RISC-V ELF into the SoC SRAM via +elf_file=<path>.
// When +elf_file is provided, also pass +enable_boot so the bootrom jumps
// to DRAM instead of spinning.
// ──────────────────────────────────────────────────────────────────────────────

// ── Hierarchical access to SoC SRAM for ELF preloading ──────────────────────
// Write directly to the behavioural sram[] array (not the init_val[] shadow).
// init_val[] is only copied into sram[] during reset, so post-reset writes
// must target sram[] to actually appear in memory.
`define MAIN_MEM(P) dut.i_sram.gen_cut[0].i_tc_sram_wrapper.i_tc_sram.sram[(``P``)]

// ── DPI-C imports for ELF loading (same functions used by ariane_tb.sv) ─────
`ifndef READ_ELF_T
`define READ_ELF_T
import "DPI-C" function void read_elf(input string filename);
import "DPI-C" function byte get_section(output longint address, output longint len);
import "DPI-C" context function void read_section_sv(input longint address, inout byte buffer[]);
`endif

module tb_top_soc;

    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import dm::*;
    import debug_pkg::*;
    import dbg_axi_pkg::*;
    import dbg_dmi_pkg::*;

    // ── System clock & reset ───────────────────────────────────────────────
    logic clk;
    logic rtc;
    logic rst_n;

    initial clk = 1'b0;
    always  #5 clk = ~clk;  // 100 MHz

    initial rtc = 1'b0;
    always #100 rtc = ~rtc; // slower RTC clock

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

    // ── Boot Control ───────────────────────────────────────────────────────
    logic enable_boot;
    initial begin
        // User request: "disable that signal to avoid boot so that only the external path can be used."
        enable_boot = 1'b0;
        if ($test$plusargs("enable_boot")) begin
            enable_boot = 1'b1;
        end
    end

    // ── DUT: Full CVA6 SoC (ariane_testharness) ────────────────────────────
    ariane_testharness #(
        .InclSimDTM (1'b0)
    ) dut (
        .clk_i           (clk),
        .rtc_i           (rtc),
        .rst_ni          (rst_n),
        .exit_o          (),
`ifdef RISCV_VIP_MODE
        .enable_boot_i   (enable_boot),
        .jtag_TCK_i      (muxed_tck),
        .jtag_TMS_i      (muxed_tms),
        .jtag_TDI_i      (muxed_tdi),
        .jtag_TRSTn_i    (muxed_trstn),
        .jtag_TDO_data_o (jtag_vif.tdo)
`endif
    );

    // ── AXI taps ───────────────────────────────────────────────────────────
    // Two buses matter for debug:
    //   dm_sba   -- dut.slave[1], the Debug Module's System Bus Access master
    //   dm_slave -- dut.master[ariane_soc::Debug], the hart's accesses to the
    //               DM: debug-ROM fetches, the halted/going/resuming flag
    //               writes, and the data0 result store
    // The second is the one that makes an abstract command legible end to end.
    dbg_axi_if #(`DBG_AXI_ADDR_W, `DBG_AXI_DATA_W, `DBG_AXI_ID_W)
        dm_sba_if   (.clk(clk), .rst_n(rst_n));
    dbg_axi_if #(`DBG_AXI_ADDR_W, `DBG_AXI_DATA_W, `DBG_AXI_ID_W)
        dm_slave_if (.clk(clk), .rst_n(rst_n));

    // IDs are zero-extended: the crossbar's slave side carries IdWidthSlave
    // (IdWidth + $clog2(NrSlaves)) bits, narrower than the tap's default 8.
    `define DBG_AXI_TAP(TAP, BUS)                                              \
        assign TAP``.aw_id    = BUS``.aw_id;                                   \
        assign TAP``.aw_addr  = BUS``.aw_addr;                                 \
        assign TAP``.aw_len   = BUS``.aw_len;                                  \
        assign TAP``.aw_size  = BUS``.aw_size;                                 \
        assign TAP``.aw_burst = BUS``.aw_burst;                                \
        assign TAP``.aw_valid = BUS``.aw_valid;                                \
        assign TAP``.aw_ready = BUS``.aw_ready;                                \
        assign TAP``.w_data   = BUS``.w_data;                                  \
        assign TAP``.w_strb   = BUS``.w_strb;                                  \
        assign TAP``.w_last   = BUS``.w_last;                                  \
        assign TAP``.w_valid  = BUS``.w_valid;                                 \
        assign TAP``.w_ready  = BUS``.w_ready;                                 \
        assign TAP``.b_id     = BUS``.b_id;                                    \
        assign TAP``.b_resp   = BUS``.b_resp;                                  \
        assign TAP``.b_valid  = BUS``.b_valid;                                 \
        assign TAP``.b_ready  = BUS``.b_ready;                                 \
        assign TAP``.ar_id    = BUS``.ar_id;                                   \
        assign TAP``.ar_addr  = BUS``.ar_addr;                                 \
        assign TAP``.ar_len   = BUS``.ar_len;                                  \
        assign TAP``.ar_size  = BUS``.ar_size;                                 \
        assign TAP``.ar_burst = BUS``.ar_burst;                                \
        assign TAP``.ar_valid = BUS``.ar_valid;                                \
        assign TAP``.ar_ready = BUS``.ar_ready;                                \
        assign TAP``.r_id     = BUS``.r_id;                                    \
        assign TAP``.r_data   = BUS``.r_data;                                  \
        assign TAP``.r_resp   = BUS``.r_resp;                                  \
        assign TAP``.r_last   = BUS``.r_last;                                  \
        assign TAP``.r_valid  = BUS``.r_valid;                                 \
        assign TAP``.r_ready  = BUS``.r_ready;

    `DBG_AXI_TAP(dm_sba_if,   dut.slave[1])
    `DBG_AXI_TAP(dm_slave_if, dut.master[ariane_soc::Debug])

    // ── Push JTAG virtual interface into UVM config DB ─────────────────────
    initial begin
        uvm_config_db #(virtual jtag_if)::set(
            null, "uvm_test_top.*", "jtag_vif", jtag_vif);
    end

    // ── DMI bus tap ────────────────────────────────────────────────────────
    // The DMI is not AXI: it is the DM's own valid/ready request-response bus,
    // dm::dmi_req_t/dmi_resp_t between dmi_jtag and dm_top. Tapping it lets the
    // checker verify the DTM -- every request shifted in over JTAG must appear
    // here unchanged.
    dbg_dmi_if dmi_bus_if (.clk(clk), .rst_n(rst_n));

    assign dmi_bus_if.req_valid   = dut.debug_req_valid;
    assign dmi_bus_if.req_ready   = dut.debug_req_ready;
    assign dmi_bus_if.req_addr    = dut.debug_req.addr;
    assign dmi_bus_if.req_op      = dut.debug_req.op;
    assign dmi_bus_if.req_data    = dut.debug_req.data;
    assign dmi_bus_if.resp_valid  = dut.debug_resp_valid;
    assign dmi_bus_if.resp_ready  = dut.debug_resp_ready;
    assign dmi_bus_if.resp_data   = dut.debug_resp.data;
    assign dmi_bus_if.resp_status = dut.debug_resp.resp;

    initial begin
        uvm_config_db #(dbg_dmi_pkg::dbg_dmi_vif_t)::set(
            null, "uvm_test_top.m_env", "dmi_vif", dmi_bus_if);
    end

    // ── Publish the AXI taps ───────────────────────────────────────────────
    // Interfaces only. Every setting -- which taps are enabled, their names,
    // address windows, region annotation and verbosity -- lives in
    // axi_configs/cva6_axi.json so DV behaviour is never driven from the
    // design side. Path is relative to cva6_sim/ (the simulator's CWD).
    initial begin
        uvm_config_db #(dbg_axi_vif_t)::set(
            null, "uvm_test_top.m_env", "axi_vif_dm_sba", dm_sba_if);
        uvm_config_db #(dbg_axi_vif_t)::set(
            null, "uvm_test_top.m_env", "axi_vif_dm_slave", dm_slave_if);

        uvm_config_db #(string)::set(
            null, "uvm_test_top.m_env", "axi_config_path",
            "../src/pydebug/axi_configs/cva6_axi.json");
    end

    // ── Tell dm_checker which declared DUT config to load (#104, #117) ─────
    // CVA6-fork's nested corev_apu/riscv-dbg is pinned to
    // 10x-Engineers/riscv-dbg@features/riscv-debug-update; Ibex's tb_top
    // sets nothing and gets dm_checker's ibex.json default. Path is relative
    // to cva6_sim/ (vsim's CWD when this runs).
    initial begin
        uvm_config_db #(string)::set(null, "*", "dut_config_path",
            "../src/pydebug/dut_configs/cva6.json");
    end

    // ── Waveform dump (opt-in via +dump_waves) ─────────────────────────────
    // Scoped to the Debug Module (dut.i_dm_top, which nests dm_csrs/dm_mem/
    // dm_sba/dmi_jtag) plus the JTAG VIP interface, rather than the whole SoC
    // — keeps the VCD small enough to script against for issue debugging.
    initial begin
        string wave_file;
        if ($test$plusargs("dump_waves")) begin
            wave_file = "sim_outputs/waves.vcd";
            void'($value$plusargs("wave_file=%s", wave_file));
            $dumpfile(wave_file);
            $dumpvars(0, dut.i_dm_top);
            $dumpvars(0, jtag_vif);
            $dumpvars(0, dut.i_ariane.i_cva6.csr_regfile_i);
            $dumpvars(0, dut.i_ariane.i_cva6.commit_stage_i);
            `uvm_info("TB_SOC", $sformatf("Waveform dump enabled: %s", wave_file), UVM_LOW)
        end
    end

    // ── Monitor bb_quit and signal via config_db ──────────────────────────
    initial begin
        if (jtag_use_openocd) begin
            @(posedge bb_quit);
            uvm_config_db #(int)::set(null, "*", "bb_quit", 1);
        end
    end

    // ── ELF preloading ─────────────────────────────────────────────────────
    // Mirrors ariane_tb.sv preloading logic.
    // Usage: +elf_file=path/to/test.elf (also needs +enable_boot)
    initial begin
        automatic string binary = "";
        automatic logic [7:0][7:0] mem_row;
        longint address, load_address, last_load_address, len;
        byte buffer[];

        void'($value$plusargs("elf_file=%s", binary));

        if (binary != "") begin
            `uvm_info("TB_SOC", $sformatf("Preloading ELF: %s", binary), UVM_LOW)

            read_elf(binary);
            // Wait for clock to start before preloading (avoids race with SIM_INIT)
            wait(clk);

            last_load_address = 'hFFFFFFFF;
            // Iterate over all ELF sections
            while (get_section(address, len)) begin
                automatic int num_words = (len+7)/8;
                `uvm_info("TB_SOC", $sformatf("Loading section: addr=0x%016x  len=0x%x (%0d bytes)",
                    address, len, len), UVM_LOW)
                buffer = new [num_words*8];
                read_section_sv(address, buffer);

                // Preload into SRAM — 64-bit words
                for (int i = 0; i < num_words; i++) begin
                    mem_row = '0;
                    for (int j = 0; j < 8; j++) begin
                        mem_row[j] = buffer[i*8 + j];
                    end
                    load_address = (address[23:0] >> 3) + i;
                    if (load_address != last_load_address) begin
                        if (address[31:0] < 'h84000000) begin
                            `MAIN_MEM(load_address) = mem_row;
                        end
                        last_load_address = load_address;
                    end
                end
            end
            `uvm_info("TB_SOC", "ELF preloading complete", UVM_LOW)
        end else begin
            `uvm_info("TB_SOC",
                "No +elf_file specified — core will execute bootrom only", UVM_LOW)
        end
    end

    // ── UVM start ──────────────────────────────────────────────────────────
    initial run_test("debug_test");

endmodule
