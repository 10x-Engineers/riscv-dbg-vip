# ──────────────────────────────────────────────────────────────────────────────
# Makefile — RISC-V debug framework (JTAG VIP edition)
#
#  make questa_batch       — Questa batch run (halt sequence, UVM)
#  make questa_interactive — Questa interactive run
#  make questa_mem_scan    — Questa memory-scan sequence
#
#  make vcs_batch          — VCS equivalent
#  make xrun_batch         — Xcelium equivalent
#
#  make openocd_batch      — run against real HW via OpenOCD (no sim)
#
# This Makefile manages the compilation and execution of the RISC-V Debug
# verification environment across different simulators (Questa, VCS, Xcelium).
# It also handles the compilation of the C-DPI bridge used for Python integration.
# ──────────────────────────────────────────────────────────────────────────────

# Path definitions for different project components
TB_DIR    = ../tb
TB_TEST_DIR = $(TB_DIR)/tests
VIP_DIR   = ../dv/agents/jtag
ENV_DIR   = ../dv/env
RV_DBG_ENV_DIR = $(ENV_DIR)/rv_dbg
SV_SEQ_DIR = ../dv/seq_lib/rv_dbg
RTL_DIR   = ../riscv-dbg/src
C_DIR     = ../lib/C/py_uvm_bridge
CFG_DIR   = ../configs
PY_DIR    = ../lib/python

# ── RTL source list (dependency order) ────────────────────────────────────────
# SRC_RTL lists all SystemVerilog files required for the simulation.
# Note: dm_pkg must be first — defines the dm:: namespace used by all RTL files.
SRC_RTL = \
    $(RTL_DIR)/dm_pkg.sv                        \
    $(RTL_DIR)/tb_stubs.sv                      \
    ../riscv-dbg/debug_rom/debug_rom.sv         \
    ../riscv-dbg/debug_rom/debug_rom_one_scratch.sv \
    $(RTL_DIR)/dmi_jtag_tap.sv                  \
    $(RTL_DIR)/dmi_cdc.sv                       \
    $(RTL_DIR)/dmi_jtag.sv                      \
    $(RTL_DIR)/dm_csrs.sv                       \
    $(RTL_DIR)/dm_sba.sv                        \
    $(RTL_DIR)/dm_mem.sv                        \
    $(RTL_DIR)/dm_top.sv                        \
    $(VIP_DIR)/dm_defines_pkg.sv                 \
    $(VIP_DIR)/jtag_if.sv                        \
    $(VIP_DIR)/jtag_pkg.sv                       \
    $(ENV_DIR)/debug_pkg.sv                      \
    $(VIP_DIR)/jtag_bitbang.sv                   \
    $(TB_DIR)/tb_top.sv

# C sources for the DPI bridges (UVM bridge and Remote Bitbang server)
SRC_C   = $(C_DIR)/uvm_bridge.c $(C_DIR)/remote_bitbang.c

# +incdir so that jtag_pkg's `include "types.sv" etc. resolve correctly
INCDIRS = +incdir+$(VIP_DIR) +incdir+$(RV_DBG_ENV_DIR) +incdir+$(SV_SEQ_DIR) +incdir+$(TB_TEST_DIR) +incdir+$(TB_DIR)

# Default Python runner and config
RUNNER   = $(PY_DIR)/run.py
CFG_FILE = $(CFG_DIR)/halt_uvm.json

# Default command-line to run the Python sequencer
PYTHON_SEQ ?= $(RUNNER) --config $(CFG_FILE)

# ── Simulation output directory ──────────────────────────────────────────────
# Simulation outputs are logged to numbered files in the output directory
SIM_OUTPUT_DIR = ./sim_outputs

# ══════════════════════════════════════════════════════════════════════════════
# Questa
# ══════════════════════════════════════════════════════════════════════════════
QUESTA_FLAGS = -sv -timescale 1ns/1ps $(INCDIRS)
VSIM ?= env -u DISPLAY vsim
VSIM_BATCH ?= env -u DISPLAY vsim -batch

# Compile the C sources into a shared object library (.so) for Questa's DPI
uvm_bridge.so: $(SRC_C)
	gcc -shared -fPIC -std=c11 \
	    -I"$(C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I/home/jk/mentor/questasim/include \
	    $(SRC_C) -o uvm_bridge.so -lpthread

# Create work library and compile all SV RTL/TB files
questa_compile: uvm_bridge.so
	vlib work
	vlog $(QUESTA_FLAGS) $(SRC_RTL)

# Run a standard batch simulation (non-interactive)
questa_batch: questa_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_batch_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_batch_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) -do "run -all; quit -f" \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

# Run in interactive mode (GUI usually, or just interactive terminal)
questa_interactive: questa_compile
	$(VSIM)  -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	     +PYTHON_MODE=interactive \
	     +UVM_VERBOSITY=UVM_MEDIUM

# Target for running a specific memory scan sequence
questa_mem_scan: questa_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_mem_scan_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_mem_scan_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) -do "run -all; quit -f" \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(RUNNER) --scenario mem_scan --transport uvm --mode batch" \
	      +PYTHON_MODE=batch \
	      +PYTHON_EXTRA="--base 0x80000000 --count 8" \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

# Target for reading the DMSTATUS register specifically
questa_read_dmstatus: questa_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_read_dmstatus_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_read_dmstatus_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) -do "run -all; quit -f" \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	      +UVM_TESTNAME=debug_test \
	      "+PYTHON_SEQ=$(RUNNER) --config $(CFG_DIR)/read_dmstatus_uvm.json" \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

questa_openocd_cleanup:
	@echo "🔄 Cleaning up any existing Questa/OpenOCD processes..."
	@kill -9 -f "vsim" 2>/dev/null || true
	@kill -9 -f "openocd" 2>/dev/null || true
	@sleep 1
# Target to run OpenOCD alongside the simulator using an orchestration script
questa_openocd: questa_compile
	@rm -f sim.log
	$(VSIM_BATCH) -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=$(RUNNER) --transport openocd --scenario read_dmstatus --mode batch --log-level DEBUG" \
	     +JTAG_MASTER=openocd \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &

# Wait for bitbang server to be ready
	@echo "⏳ Waiting for JTAG bitbang server to start..."
	@for i in $$(seq 1 40); do \
		if grep -q "Listening on port 9824" sim.log 2>/dev/null; then \
			echo "✅ Bitbang server ready on port 9824"; \
			break; \
		fi; \
		sleep 1; \
	done

# run.py launches OpenOCD itself, waits for "Examination succeed", then connects
	@echo "🚀 Starting Python runner (manages OpenOCD lifecycle)..."
	python3 $(RUNNER) --transport openocd --scenario read_dmstatus --mode batch --log-level DEBUG

# # this list contains the standalone components
# src :=  $(if $(spike-tandem),verif/tb/core/uvma_core_cntrl_pkg.sv)                   \
#         $(if $(spike-tandem),verif/tb/core/uvma_cva6pkg_utils_pkg.sv)                \
#         $(if $(spike-tandem),verif/tb/core/uvma_rvfi_pkg.sv)                         \
#         $(if $(spike-tandem),verif/tb/core/uvmc_rvfi_reference_model_pkg.sv)         \
#         $(if $(spike-tandem),verif/tb/core/uvmc_rvfi_scoreboard_pkg.sv)              \
#         $(if $(spike-tandem),corev_apu/tb/common/spike.sv)                           \
#         core/cva6_rvfi.sv                                                            \
#         corev_apu/src/ariane.sv                                                      \
#         $(wildcard corev_apu/bootrom/*.sv)                                           \
#         $(wildcard corev_apu/clint/*.sv)                                             \
#         $(wildcard corev_apu/fpga/src/axi2apb/src/*.sv)                              \
#         $(wildcard corev_apu/fpga/src/apb_timer/*.sv)                                \
#         $(wildcard corev_apu/fpga/src/axi_slice/src/*.sv)                            \
#         $(wildcard vendor/pulp-platform/axi_riscv_atomics/src/*.sv)                  \
#         $(wildcard corev_apu/axi_mem_if/src/*.sv)                                    \
#         $(wildcard corev_apu/riscv-dbg/src/*.sv)                                     \
#         corev_apu/rv_plic/rtl/rv_plic_target.sv                                      \
#         corev_apu/rv_plic/rtl/rv_plic_gateway.sv                                     \
#         corev_apu/rv_plic/rtl/plic_regmap.sv                                         \
#         corev_apu/rv_plic/rtl/plic_top.sv                                            \
#         corev_apu/riscv-dbg/debug_rom/debug_rom.sv                                   \
#         corev_apu/register_interface/src/apb_to_reg.sv                               \
#         vendor/pulp-platform/axi/src/axi_multicut.sv                                 \
#         vendor/pulp-platform/common_cells/src/rstgen_bypass.sv                       \
#         vendor/pulp-platform/common_cells/src/rstgen.sv                              \
#         vendor/pulp-platform/common_cells/src/addr_decode.sv                         \
#         vendor/pulp-platform/common_cells/src/stream_register.sv                     \
#         vendor/pulp-platform/axi/src/axi_cut.sv                                      \
#         vendor/pulp-platform/axi/src/axi_join.sv                                     \
#         vendor/pulp-platform/axi/src/axi_delayer.sv                                  \
#         vendor/pulp-platform/axi/src/axi_to_axi_lite.sv                              \
#         vendor/pulp-platform/axi/src/axi_id_prepend.sv                               \
#         vendor/pulp-platform/axi/src/axi_atop_filter.sv                              \
#         vendor/pulp-platform/axi/src/axi_err_slv.sv                                  \
#         vendor/pulp-platform/axi/src/axi_mux.sv                                      \
#         vendor/pulp-platform/axi/src/axi_demux.sv                                    \
#         vendor/pulp-platform/axi/src/axi_xbar.sv                                     \
#         vendor/pulp-platform/common_cells/src/cdc_2phase.sv                          \
#         vendor/pulp-platform/common_cells/src/spill_register_flushable.sv            \
#         vendor/pulp-platform/common_cells/src/spill_register.sv                      \
#         vendor/pulp-platform/common_cells/src/deprecated/fifo_v1.sv                  \
#         vendor/pulp-platform/common_cells/src/deprecated/fifo_v2.sv                  \
#         vendor/pulp-platform/common_cells/src/stream_delay.sv                        \
#         vendor/pulp-platform/common_cells/src/lfsr_16bit.sv                          \
#         vendor/pulp-platform/tech_cells_generic/src/deprecated/cluster_clk_cells.sv  \
#         vendor/pulp-platform/tech_cells_generic/src/deprecated/pulp_clk_cells.sv     \
#         vendor/pulp-platform/tech_cells_generic/src/rtl/tc_clk.sv                    \
#         corev_apu/instr_tracing/ITI/include/iti_pkg.sv                               \
#         corev_apu/instr_tracing/rv_tracer-main/include/te_pkg.sv                     \
#         corev_apu/instr_tracing/rv_encapsulator-main/src/include/encap_pkg.sv        \
#         corev_apu/tb/ariane_testharness.sv                                           \
#         corev_apu/tb/ariane_peripherals.sv                                           \
#         corev_apu/tb/rvfi_tracer.sv                                                  \
#         corev_apu/tb/common/uart.sv                                                  \
#         corev_apu/tb/common/SimDTM.sv                                                \
#         corev_apu/tb/common/SimJTAG.sv                                               \
#         corev_apu/instr_tracing/ITI/cva6_iti/iti.sv                                  \
#         corev_apu/instr_tracing/ITI/cva6_iti/block_retirement.sv                     \
#         corev_apu/instr_tracing/ITI/cva6_iti/single_retirement.sv                    \
#         corev_apu/instr_tracing/ITI/cva6_iti/itype_detector.sv                       \
#         vendor/pulp-platform/common_cells/src/counter.sv                             \
#         vendor/pulp-platform/common_cells/src/sync.sv                                \
#         vendor/pulp-platform/common_cells/src/sync_wedge.sv                          \
#         vendor/pulp-platform/common_cells/src/edge_detect.sv                         \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/lzc.sv                            \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_branch_map.sv                  \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_filter.sv                      \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_packet_emitter.sv              \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_priority.sv                    \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_reg.sv                         \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/te_resync_counter.sv              \
#         corev_apu/instr_tracing/rv_tracer-main/rtl/rv_tracer.sv                      \
#         vendor/pulp-platform/common_cells/src/fifo_v3.sv                             \
#         corev_apu/instr_tracing/DPTI/slicer_DPTI.sv                                  \
#         corev_apu/instr_tracing/rv_encapsulator-main/src/rtl/encapsulator.sv
# src := $(addprefix $(root-dir), $(src))

# CVA6_INCDIR :=+incdir+$(CVA6_HOME)/core/include 			\
# 	+incdir+$(CVA6_HOME)/vendor/pulp-platform/axi/include/		\
# 	+incdir+$(CVA6_HOME)/corev_apu/register_interface/include

# # Sources
# # Package files -> compile first
# ariane_pkg := \
#               corev_apu/tb/ariane_axi_pkg.sv                         \
#               corev_apu/tb/axi_intf.sv                               \
#               corev_apu/register_interface/src/reg_intf.sv           \
#               corev_apu/tb/ariane_soc_pkg.sv                         \
#               corev_apu/riscv-dbg/src/dm_pkg.sv                      \
#               corev_apu/tb/ariane_axi_soc_pkg.sv
# ariane_pkg := $(addprefix $(root-dir), $(ariane_pkg))

# uart_src := $(wildcard corev_apu/fpga/src/apb_uart/src/vhdl_orig/*.vhd)

# ── Questa SoC Integration targets ────────────────────────────────────────────
questa_soc_compile: uvm_bridge.so
	vlib work
	@echo "Creating absolute flist for CVA6 core using native flist_flattener..."
	@export CVA6_REPO_DIR=../CVA6-fork; \
	 export TARGET_CFG=cv64a6_imafdc_sv39; \
	 export HPDCACHE_DIR=../CVA6-fork/core/cache_subsystem/hpdcache; \
	 python3 ../CVA6-fork/util/flist_flattener.py --print_incdir --print_newline ../CVA6-fork/core/Flist.cva6 > flist_soc.tmp
	vlog $(QUESTA_FLAGS) +define+RISCV_VIP_MODE \
	    +incdir+../CVA6-fork/corev_apu/register_interface/include \
	    +incdir+../CVA6-fork/corev_apu/instr_tracing/ITI/include \
	    +incdir+../CVA6-fork/corev_apu/fpga/src/apb/include \
	    +incdir+../CVA6-fork/core/include/ \
	    +incdir+../CVA6-fork/vendor/pulp-platform/axi/include \
	    -f flist_soc.tmp \
			../CVA6-fork/core/include/config_pkg.sv \
	    ../CVA6-fork/corev_apu/instr_tracing/ITI/include/iti_pkg.sv \
			../CVA6-fork/corev_apu/fpga/src/apb/src/apb_pkg.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dm_pkg.sv \
	    ../CVA6-fork/corev_apu/tb/ariane_soc_pkg.sv \
	    ../CVA6-fork/corev_apu/tb/axi_intf.sv \
	    ../CVA6-fork/corev_apu/tb/ariane_axi_pkg.sv \
	    ../CVA6-fork/corev_apu/tb/ariane_axi_soc_pkg.sv \
	    ../CVA6-fork/corev_apu/axi_mem_if/src/axi2mem.sv \
	    ../CVA6-fork/corev_apu/clint/*.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/debug_rom/debug_rom.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dm_csrs.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dm_mem.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dm_sba.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dm_top.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dmi_cdc.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dmi_jtag.sv \
	    ../CVA6-fork/corev_apu/riscv-dbg/src/dmi_jtag_tap.sv \
	    ../CVA6-fork/corev_apu/rv_plic/rtl/rv_plic_target.sv \
	    ../CVA6-fork/corev_apu/rv_plic/rtl/rv_plic_gateway.sv \
	    ../CVA6-fork/corev_apu/rv_plic/rtl/plic_regmap.sv \
	    ../CVA6-fork/corev_apu/rv_plic/rtl/plic_top.sv \
	    ../CVA6-fork/corev_apu/fpga/src/axi2apb/src/*.sv \
	    ../CVA6-fork/corev_apu/fpga/src/axi_slice/src/*.sv \
	    ../CVA6-fork/corev_apu/register_interface/src/apb_to_reg.sv \
	    ../CVA6-fork/corev_apu/register_interface/src/reg_intf.sv \
	    ../CVA6-fork/corev_apu/fpga/src/apb_timer/*.sv \
	    ../CVA6-fork/corev_apu/fpga/src/apb_uart/src/*.sv \
	    ../CVA6-fork/corev_apu/bootrom/bootrom.sv \
	    ../CVA6-fork/corev_apu/src/ariane.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi_riscv_atomics/src/*.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/rstgen_bypass.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/rstgen.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/addr_decode.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/stream_register.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_cut.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_join.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_delayer.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_to_axi_lite.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_id_prepend.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_atop_filter.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_err_slv.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_mux.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_demux.sv \
	    ../CVA6-fork/vendor/pulp-platform/axi/src/axi_xbar.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/cdc_2phase.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/spill_register_flushable.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/spill_register.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/deprecated/fifo_v1.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/deprecated/fifo_v2.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/stream_delay.sv \
	    ../CVA6-fork/vendor/pulp-platform/common_cells/src/lfsr_16bit.sv \
	    ../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/deprecated/cluster_clk_cells.sv \
	    ../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/deprecated/pulp_clk_cells.sv \
	    ../CVA6-fork/vendor/pulp-platform/tech_cells_generic/src/rtl/tc_clk.sv \
	    ../CVA6-fork/corev_apu/tb/common/uart.sv \
	    ../CVA6-fork/corev_apu/tb/ariane_peripherals.sv \
	    ../CVA6-fork/corev_apu/tb/ariane_testharness.sv \
	    $(VIP_DIR)/dm_defines_pkg.sv \
	    $(VIP_DIR)/jtag_if.sv \
	    $(VIP_DIR)/jtag_pkg.sv \
	    $(ENV_DIR)/debug_pkg.sv \
	    $(VIP_DIR)/jtag_bitbang.sv \
	    $(TB_DIR)/tb_top_soc.sv
	@rm -f flist_soc.tmp

# Remove the vopt flag because the simulation is too slow. find a workaround
questa_soc_batch: questa_soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_soc_batch_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_soc_batch_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) -novopt -suppress 12110 -do "run -all; quit -f" \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top_soc \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

questa_soc_interactive: questa_soc_compile
	$(VSIM) -novopt -suppress 12110 -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top_soc \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	     +PYTHON_MODE=interactive \
	     +UVM_VERBOSITY=UVM_MEDIUM

questa_soc_openocd: questa_soc_compile
	@rm -f sim.log
	@echo "🚀 Starting vsim SoC..."
	$(VSIM_BATCH) -novopt -suppress 12110 -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top_soc \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=$(RUNNER) --transport openocd --scenario read_dmstatus --mode batch --log-level DEBUG" \
	     +JTAG_MASTER=openocd \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	@echo "⏳ Waiting for JTAG bitbang server to start..."
	@for i in $$(seq 1 40); do \
		if grep -q "Listening on port 9824" sim.log 2>/dev/null; then \
			echo "✅ Bitbang server ready on port 9824"; \
			break; \
		fi; \
		sleep 1; \
	done
	@echo "🚀 Starting Python runner (manages OpenOCD lifecycle)..."
	python3 $(RUNNER) --transport openocd --scenario read_dmstatus --mode batch --log-level DEBUG


# ══════════════════════════════════════════════════════════════════════════════
# VCS
# ══════════════════════════════════════════════════════════════════════════════
VCS_FLAGS = -sverilog -timescale=1ns/1ps \
            -ntb_opts uvm-1.2 \
            $(INCDIRS) \
            -CFLAGS "-std=c11 -I$(C_DIR)" \
            $(SRC_C) $(SRC_RTL)

# Compile for VCS and create the simv executable
vcs_compile:
	vcs $(VCS_FLAGS) -o simv -debug_access+all

# Run VCS simulation in batch mode
vcs_batch: vcs_compile
	./simv +UVM_TESTNAME=debug_test \
	       +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE)" \
	       +UVM_VERBOSITY=UVM_MEDIUM

# Run VCS simulation in interactive mode
vcs_interactive: vcs_compile
	./simv +UVM_TESTNAME=debug_test \
	       +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	       +PYTHON_MODE=interactive \
	       +UVM_VERBOSITY=UVM_MEDIUM

# ══════════════════════════════════════════════════════════════════════════════
# Xcelium
# ══════════════════════════════════════════════════════════════════════════════
XRUN_FLAGS = -sv -uvm -uvmhome CDNS-1.2 \
             -timescale 1ns/1ps \
             $(INCDIRS) \
             -ccargs "-std=c11 -I$(C_DIR)" \
             $(SRC_C) $(SRC_RTL)

# Run Xcelium simulation in batch mode (xrun handles compile/run in one step)
xrun_batch:
	xrun $(XRUN_FLAGS) \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE)"

# Run Xcelium simulation in interactive mode
xrun_interactive:
	xrun $(XRUN_FLAGS) \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	     +PYTHON_MODE=interactive

# ══════════════════════════════════════════════════════════════════════════════
# OpenOCD — no simulator, runs against real hardware
# ══════════════════════════════════════════════════════════════════════════════
openocd_batch:
	python3 $(RUNNER) --config $(CFG_DIR)/halt_openocd.json

openocd_interactive:
	python3 $(RUNNER) --config $(CFG_DIR)/halt_openocd.json --mode interactive

# ══════════════════════════════════════════════════════════════════════════════
# Standalone Python test (mock transport)
# ══════════════════════════════════════════════════════════════════════════════
python_test:
	python3 -m pytest ../lib/python/tests/ -v

# Remove all generated files (compiled libs, logs, wave files)
clean:
	rm -rf simv simv.daidir csrc xcelium.d work uvm_bridge.so \
	       *.log *.vcd *.vpd ucli.key novas* verdiLog* transcript

.PHONY: vcs_compile vcs_batch vcs_interactive \
        xrun_batch xrun_interactive \
        questa_compile questa_batch questa_interactive questa_mem_scan \
        questa_soc_compile questa_soc_batch questa_soc_interactive questa_soc_openocd \
        openocd_batch openocd_interactive \
        python_test clean
