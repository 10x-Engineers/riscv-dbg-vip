`timescale 1ns/1ps

// ──────────────────────────────────────────────────────────────────────────────
// tb_top_ibex.sv
//
// Testbench top connecting:
//   jtag_agent (JTAG VIP) / OpenOCD Bitbang  →  Ibex Demo System SoC
//
// Supports preloading any RISC-V ELF into the SoC SRAM via +elf_file=<path>.
// The Ibex core boots from MEM_START (0x00100000) + 0x80.
// ──────────────────────────────────────────────────────────────────────────────

// ── Hierarchical access to the behavioural dual-port SRAM ───────────────────
// Path: ibex_demo_system → ram_2p (u_ram) → prim_ram_2p (u_ram) →
//       prim_generic_ram_2p → mem[]
// Each element is 32 bits wide; addresses are word-aligned.
`define IBEX_MEM(P) dut.u_ram.u_ram.gen_generic.u_impl_generic.mem[(``P``)]

// ── DPI-C imports for ELF loading ───────────────────────────────────────────
`ifndef READ_ELF_T
`define READ_ELF_T
import "DPI-C" function void read_elf(input string filename);
import "DPI-C" function byte get_section(output longint address, output longint len);
import "DPI-C" context function void read_section_sv(input longint address, inout byte buffer[]);
`endif

module tb_top_ibex;

    import uvm_pkg::*;
    `include "uvm_macros.svh"
    import dm::*;
    import debug_pkg::*;

    // ── Parameters matching ibex_demo_system defaults ─────────────────────
    localparam int ClockFrequency = 50_000_000;
    localparam int BaudRate       = 115_200;

    // Memory map constants (must match ibex_demo_system.sv)
    localparam logic [31:0] MEM_START = 32'h00100000;
    localparam logic [31:0] MEM_SIZE  = 128 * 1024;  // 128 KiB

    // ── System clock & reset ─────────────────────────────────────────────
    logic clk;
    logic rst_n;

    initial clk = 1'b0;
    always  #10 clk = ~clk;  // 50 MHz (matches ClockFrequency default)

    initial begin
        rst_n = 1'b0;
        repeat (10) @(posedge clk);
        rst_n = 1'b1;
    end

    // ── JTAG interface ───────────────────────────────────────────────────
    jtag_if jtag_vif (.clk(clk), .rst_n(rst_n));

    // ── OpenOCD Remote Bitbang ───────────────────────────────────────────
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

    // ── JTAG Mux ─────────────────────────────────────────────────────────
    logic muxed_tck, muxed_tms, muxed_tdi, muxed_trstn;
    assign muxed_tck   = jtag_use_openocd ? bb_tck   : jtag_vif.tck;
    assign muxed_tms   = jtag_use_openocd ? bb_tms   : jtag_vif.tms;
    assign muxed_tdi   = jtag_use_openocd ? bb_tdi   : jtag_vif.tdi;
    assign muxed_trstn = jtag_use_openocd ? bb_trstn : jtag_vif.trst_n;

    // ── DUT: Ibex Demo System ────────────────────────────────────────────
    // JTAG TD_O connects back through the VIF for both UVM and OpenOCD paths
    logic ibex_tdo;

    ibex_demo_system #(
        .GpiWidth       ( 8                   ),
        .GpoWidth       ( 16                  ),
        .PwmWidth       ( 12                  ),
        .ClockFrequency ( ClockFrequency      ),
        .BaudRate       ( BaudRate            ),
        .RegFile        ( ibex_pkg::RegFileFF )
    ) dut (
        .clk_sys_i  (clk),
        .rst_sys_ni (rst_n),

        // JTAG — directly wired from the mux
        .tck_i      (muxed_tck),
        .tms_i      (muxed_tms),
        .trst_ni    (muxed_trstn),
        .td_i       (muxed_tdi),
        .td_o       (ibex_tdo),

        // Peripherals — unused, tie off
        .gp_i       (8'b0),
        .gp_o       (),
        .pwm_o      (),
        .uart_rx_i  (1'b1),     // idle high
        .uart_tx_o  (),
        .spi_rx_i   (1'b0),
        .spi_tx_o   (),
        .spi_sck_o  ()
    );

    // Feed TDO back to the JTAG VIF (used by both UVM agent and bitbang)
    assign jtag_vif.tdo = ibex_tdo;

    // ── Push JTAG virtual interface into UVM config DB ────────────────────
    initial begin
        uvm_config_db #(virtual jtag_if)::set(
            null, "uvm_test_top.*", "jtag_vif", jtag_vif);
    end

    // ── Tell dm_checker which declared DUT config to load (#117) ───────────
    // Ibex's vendored riscv-dbg is untouched PULP v0.13. Path is relative to
    // ibex_sim/ (vsim's CWD when this runs); explicit here even though it
    // matches dm_checker's own default, so the mapping isn't implicit.
    initial begin
        uvm_config_db #(string)::set(null, "*", "dut_config_path",
            "../src/pydebug/dut_configs/ibex.json");
    end

    // ── Waveform dump (opt-in via +dump_waves) ─────────────────────────────
    // Scoped to the Debug Module (dut.gen_dm_top.u_dm_top — it sits inside a
    // generate-if block, not directly under dut) plus the JTAG VIP interface
    // — see cva6_sim/tb_top_cva6.sv's equivalent block for why the dump is
    // scoped rather than whole-SoC.
    //
    // ibex_sim's soc_test runs fully optimized: vopt silently strips the
    // internal DM signals this dumpvars call targets even though elaboration
    // doesn't error, so a debug run here needs extra visibility. Prefer
    // recompiling with `+acc` added to the vlog invocation (no vsim flag
    // needed) over `-novopt` at vsim time — `-novopt` reliably trips
    // Questa's own combinational-loop abort (vsim-3601, "Iteration limit
    // 10000000 reached") within the first ~15-20us of any scenario on this
    // design, before ever reaching the event under investigation, whereas
    // `+acc` preserves almost all internal visibility without disabling
    // optimization. (`+acc` still won't show pure pass-through nets with no
    // intervening logic — that's a vopt optimization, not a dump bug.)
    initial begin
        string wave_file;
        if ($test$plusargs("dump_waves")) begin
            wave_file = "sim_outputs/waves.vcd";
            void'($value$plusargs("wave_file=%s", wave_file));
            $dumpfile(wave_file);
            $dumpvars(0, dut.gen_dm_top.u_dm_top);
            $dumpvars(0, jtag_vif);
            `uvm_info("TB_IBEX", $sformatf("Waveform dump enabled: %s", wave_file), UVM_LOW)
        end
    end

    // ── Monitor bb_quit and signal via config_db ─────────────────────────
    initial begin
        if (jtag_use_openocd) begin
            @(posedge bb_quit);
            uvm_config_db #(int)::set(null, "*", "bb_quit", 1);
        end
    end

    // ── ELF preloading ───────────────────────────────────────────────────
    // Ibex demo system uses 32-bit wide RAM (ram_2p → prim_generic_ram_2p).
    // Words are addressed as byte_addr[Aw-1+2:2], i.e. word-aligned index.
    // MEM_START = 0x00100000, so ELF addresses relative to MEM_START are
    // converted to word indices: idx = (addr - MEM_START) >> 2
    initial begin
        automatic string binary = "";
        longint address, len;
        byte buffer[];

        // ── Zero-Initialize SRAM ──────────────────────────────────────────
        // Speculative fetches into uninitialized memory regions return 'X',
        // which triggers Ibex assertions (e.g., IbexInstrRPayloadX). 
        // We zero-initialize the entire memory to prevent this.
        for (int i = 0; i < (MEM_SIZE / 4); i++) begin
            `IBEX_MEM(i) = 32'h0;
        end

        void'($value$plusargs("elf_file=%s", binary));

        if (binary != "") begin
            `uvm_info("TB_IBEX", $sformatf("Preloading ELF: %s", binary), UVM_LOW)

            read_elf(binary);
            // Wait for clock to start before preloading
            wait(clk);

            while (get_section(address, len)) begin
                automatic int num_words = (len + 3) / 4;  // 32-bit words
                `uvm_info("TB_IBEX", $sformatf(
                    "Loading section: addr=0x%08x  len=0x%x (%0d bytes)",
                    address[31:0], len, len), UVM_LOW)
                buffer = new [num_words * 4];
                read_section_sv(address, buffer);

                for (int i = 0; i < num_words; i++) begin
                    automatic logic [31:0] word;
                    automatic logic [31:0] byte_addr;
                    automatic int word_idx;

                    // Assemble 32-bit word (little-endian)
                    word = {buffer[i*4+3], buffer[i*4+2],
                            buffer[i*4+1], buffer[i*4+0]};

                    byte_addr = address[31:0] + (i * 4);

                    // ── Address Translation Hack ─────────────────────────
                    // CVA6 ELFs are linked at 0x80000000. Ibex Demo System
                    // boots from MEM_START + 0x80 (0x00100080). Translate the
                    // load address to ensure the core fetches valid code.
                    if (byte_addr >= 32'h80000000) begin
                        byte_addr = (byte_addr - 32'h80000000) + MEM_START + 32'h80;
                    end

                    // Only load into SRAM region
                    if (byte_addr >= MEM_START &&
                        byte_addr < (MEM_START + MEM_SIZE)) begin
                        word_idx = (byte_addr - MEM_START) >> 2;
                        `IBEX_MEM(word_idx) = word;
                    end
                end
            end
            `uvm_info("TB_IBEX", "ELF preloading complete", UVM_LOW)
            $display("DEBUG: IBEX_MEM(0) after load = %h", `IBEX_MEM(0));
            $display("DEBUG: IBEX_MEM(1) after load = %h", `IBEX_MEM(1));
            
            // Wait for reset to finish
            @(posedge rst_n);
            $display("DEBUG: IBEX_MEM(0) after rst_n = %h", `IBEX_MEM(0));
        end else begin
            `uvm_info("TB_IBEX",
                "No +elf_file specified — core will execute uninitialized SRAM",
                UVM_LOW)
        end
    end

    // ── UVM start ────────────────────────────────────────────────────────
    initial run_test("debug_test");

endmodule
