// ──────────────────────────────────────────────────────────────────────────────
// flist_ibex.f — Ibex Demo System file list for QuestaSim
//
// Manually curated from FuseSoC .core dependency tree.
// Compile order: packages → prim_generic → abstract shims → ibex core → demo system
//
// Abstract prim wrappers come from two sources:
//   1. DV shims: ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/
//   2. Custom shims: sim/prim_shims/ (for prims not in the DV shim set)
// ──────────────────────────────────────────────────────────────────────────────

// ── Include directories ─────────────────────────────────────────────────────
+incdir+../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl
+incdir+../ibex-demo-system/vendor/lowrisc_ibex/vendor/lowrisc_ip/dv/sv/dv_utils

// ── Packages (must be compiled first) ───────────────────────────────────────
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_util_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_mubi_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_count_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_cipher_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_1p_pkg.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_2p_pkg.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_pkg.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_tracer_pkg.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dm_pkg.sv
../ibex-demo-system/rtl/system/jtag_id_pkg.sv

// ── Prim assert (include file, compiled as SV for macro definitions) ────────
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_assert.sv

// ── Prim generic implementations (technology-independent) ───────────────────
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_flop.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_flop_en.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_buf.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_and2.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_xor2.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_xnor2.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_gating.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_inv.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_mux2.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_buf.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_clock_div.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_ram_1p.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_generic_ram_2p.sv

// ── Abstract prim wrappers (DV shims from ibex repo) ────────────────────────
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_clock_gating.sv
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_clock_mux2.sv
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_flop.sv
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_buf.sv
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_and2.sv
../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim/prim_ram_1p.sv

// ── Abstract prim wrappers (custom shims for prims missing from DV set) ─────
./prim_shims/prim_clock_inv.sv
./prim_shims/prim_ram_2p.sv

// ── Prim utilities used by Ibex ─────────────────────────────────────────────
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_count.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_sparse_fsm_flop.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_sec_anchor_buf.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_sec_anchor_flop.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_diff_decode.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_onehot_check.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_lfsr.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_fifo_sync_cnt.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_fifo_sync.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_sync_reqack.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_ram_1p_scr.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_inv_39_32_enc.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_inv_39_32_dec.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_enc.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_39_32_dec.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_cdc_rand_delay.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_flop_2sync.sv
../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl/prim_fifo_async_simple.sv

// ── PULP RISC-V Debug Module ────────────────────────────────────────────────
../ibex-demo-system/vendor/pulp_riscv_dbg/debug_rom/debug_rom.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/debug_rom/debug_rom_one_scratch.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dm_sba.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dm_csrs.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dm_mem.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dmi_cdc.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dmi_jtag.sv
../ibex-demo-system/vendor/pulp_riscv_dbg/src/dmi_jtag_tap.sv

// ── Ibex CPU Core ───────────────────────────────────────────────────────────
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_alu.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_branch_predict.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_compressed_decoder.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_controller.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_cs_registers.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_csr.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_counter.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_decoder.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_dummy_instr.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_ex_block.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_fetch_fifo.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_icache.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_id_stage.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_if_stage.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_load_store_unit.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_multdiv_fast.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_multdiv_slow.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_prefetch_buffer.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_pmp.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_wb_stage.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_core.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_register_file_ff.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_register_file_fpga.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_register_file_latch.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_lockstep.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_top.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_tracer.sv
../ibex-demo-system/vendor/lowrisc_ibex/rtl/ibex_top_tracing.sv

// ── Shared simulation RTL (bus, RAM wrappers, timer) ────────────────────────
../ibex-demo-system/vendor/lowrisc_ibex/shared/rtl/bus.sv
../ibex-demo-system/vendor/lowrisc_ibex/shared/rtl/ram_1p.sv
../ibex-demo-system/vendor/lowrisc_ibex/shared/rtl/ram_2p.sv
../ibex-demo-system/vendor/lowrisc_ibex/shared/rtl/timer.sv

// ── Ibex Demo System top-level RTL ──────────────────────────────────────────
../ibex-demo-system/rtl/system/debounce.sv
../ibex-demo-system/rtl/system/gpio.sv
../ibex-demo-system/rtl/system/pwm.sv
../ibex-demo-system/rtl/system/pwm_wrapper.sv
../ibex-demo-system/rtl/system/uart.sv
../ibex-demo-system/rtl/system/spi_host.sv
../ibex-demo-system/rtl/system/spi_top.sv
../ibex-demo-system/rtl/system/dm_top.sv
../ibex-demo-system/rtl/system/ibex_demo_system.sv
