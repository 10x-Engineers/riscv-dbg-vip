// flist_multihart.f -- the Debug Module and its DTM, standalone.
//
// No SoC: this testbench instantiates dm_top directly with NrHarts > 1 and
// stands dummy harts behind it (see tb_top_multihart.sv). The sources are
// CVA6's copy of riscv-dbg, so the DM measured here is the same RTL cva6_sim
// measures -- only the hart count differs.

// Common cells the DM and DTM instantiate.
+incdir+../CVA6-fork/vendor/pulp-platform/common_cells/include
../CVA6-fork/vendor/pulp-platform/common_cells/src/cdc_2phase.sv
../CVA6-fork/vendor/pulp-platform/common_cells/src/fifo_v3.sv
../CVA6-fork/vendor/pulp-platform/common_cells/src/deprecated/fifo_v2.sv
../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/rtl/tc_clk.sv
// dmi_jtag_tap instantiates these two by their deprecated names.
../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/deprecated/cluster_clk_cells.sv
../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/deprecated/pulp_clk_cells.sv

// The Debug Module itself.
../CVA6-fork/corev_apu/riscv-dbg/src/dm_pkg.sv
../CVA6-fork/corev_apu/riscv-dbg/debug_rom/debug_rom.sv
../CVA6-fork/corev_apu/riscv-dbg/debug_rom/debug_rom_one_scratch.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dm_csrs.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dm_mem.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dm_sba.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dm_top.sv

// The DTM.
../CVA6-fork/corev_apu/riscv-dbg/src/dmi_cdc.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dmi_jtag_tap.sv
../CVA6-fork/corev_apu/riscv-dbg/src/dmi_jtag.sv
