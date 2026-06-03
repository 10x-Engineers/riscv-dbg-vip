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

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

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

# SoC-specific C sources (adds standalone ELF loader for preloading into SRAM)
SRC_C_SOC = $(SRC_C) $(C_DIR)/elfloader.c

# +incdir so that jtag_pkg's `include "types.sv" etc. resolve correctly
INCDIRS = +incdir+$(VIP_DIR) +incdir+$(RV_DBG_ENV_DIR) +incdir+$(SV_SEQ_DIR) +incdir+$(TB_TEST_DIR) +incdir+$(TB_DIR)

# Default Python runner and config
RUNNER   = $(PY_DIR)/run.py
CFG_FILE = $(CFG_DIR)/halt_uvm.json

# Default command-line to run the Python sequencer
PYTHON_SEQ ?= $(RUNNER) --config $(CFG_FILE)

# ── OpenOCD defaults ─────────────────────────────────────────────────────────
# Override on command-line:  make questa_openocd OPENOCD_SCENARIO=halt
OPENOCD_SCENARIO ?= read_dmstatus
OPENOCD_CFG      ?= $(CFG_DIR)/openocd_bitbang.cfg
OPENOCD_SOC_CFG  ?= $(CFG_DIR)/openocd_bitbang_soc.cfg
OPENOCD_BIN      ?= /home/jk/Documents/riscv/bin/openocd

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

# SoC variant — includes the standalone ELF loader for SRAM preloading
uvm_bridge_soc.so: $(SRC_C_SOC)
	gcc -shared -fPIC -std=c11 \
	    -I"$(C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I/home/jk/mentor/questasim/include \
	    $(SRC_C_SOC) -o uvm_bridge_soc.so -lpthread

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
	@-pkill -f vsim 2>/dev/null || true
	@-pkill -f openocd 2>/dev/null || true
	@sleep 1

# ── Standalone OpenOCD target (tb_top: dm_top + dmi_jtag + dummy core) ───────
# Usage:
#   make questa_openocd                                        # read_dmstatus (default)
#   make questa_openocd OPENOCD_SCENARIO=halt                  # halt + inspect
#   make questa_openocd_halt                                   # convenience shortcut
questa_openocd: questa_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "🚀 Starting vsim (standalone dm_top) with JTAG bitbang server..."
	$(VSIM_BATCH) -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=unused" \
	     +JTAG_MASTER=openocd \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	@echo "⏳ Waiting for JTAG bitbang server on port 9824..."
	@for i in $$(seq 1 60); do \
		if grep -q "Listening on port 9824" sim.log 2>/dev/null; then \
			echo "✅ Bitbang server ready"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then echo "❌ Timeout waiting for bitbang server"; exit 1; fi; \
		sleep 1; \
	done
	@echo "🚀 Starting OpenOCD + Python runner (scenario=$(OPENOCD_SCENARIO))..."
	python3 $(RUNNER) --transport openocd --scenario $(OPENOCD_SCENARIO) --mode batch --log-level DEBUG

# Convenience shortcuts for standalone OpenOCD
questa_openocd_halt: OPENOCD_SCENARIO = halt
questa_openocd_halt: questa_openocd

questa_openocd_read_dmstatus: OPENOCD_SCENARIO = read_dmstatus
questa_openocd_read_dmstatus: questa_openocd


# ── Questa SoC Integration targets ────────────────────────────────────────────

# Common vsim flags for SoC targets.  -novopt is required because vopt
# crashes on this design (Signal 11).  Suppress Questa's deprecation warning
# for -novopt, but leave iteration-limit errors visible so real combinational
# loops fail loudly.
VSIM_SOC_FLAGS = -novopt -suppress 12110
VSIM_SOC_DO    = "run -all; quit -f"

# ── ELF preloading plusargs (auto-derived from ELF variable) ──────────────────
# When ELF is set, also enables boot so the bootrom jumps to DRAM.
# Usage:  make questa_soc_test ELF=../sw/infinite_loop.elf
#         make questa_soc_test                              (no ELF, bootrom spin)
ELF ?=
ELF_PLUSARGS = $(if $(ELF),+enable_boot "+elf_file=$(abspath $(ELF))",)

questa_soc_compile: uvm_bridge_soc.so
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

# ── Generic SoC test target ──────────────────────────────────────────────────
# This is the main entry point for running any RISC-V test on the CVA6 SoC.
#
# Usage:
#   make questa_soc_test ELF=../sw/infinite_loop.elf                         # halt test
#   make questa_soc_test ELF=../sw/infinite_loop.elf CFG_FILE=../configs/read_dmstatus_uvm.json
#   make questa_soc_test                                                      # no ELF, bootrom spin
#   make questa_soc_halt_test                                                 # convenience shortcut
questa_soc_test: questa_soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_soc_test_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_soc_test_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) $(VSIM_SOC_FLAGS) -do $(VSIM_SOC_DO) \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_soc \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(ELF_PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

# Convenience shortcut: infinite_loop + halt sequence
questa_soc_halt_test: ELF = ../sw/infinite_loop.elf
questa_soc_halt_test: questa_soc_test

# Remove the vopt flag because the simulation is too slow. find a workaround
questa_soc_batch: questa_soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/questa_soc_batch_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/questa_soc_batch_$$TEST_NUM.log; \
	 echo "📝 Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) $(VSIM_SOC_FLAGS) -do $(VSIM_SOC_DO) \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_soc \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(ELF_PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

questa_soc_interactive: questa_soc_compile
	$(VSIM) $(VSIM_SOC_FLAGS) -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_soc \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	     +PYTHON_MODE=interactive \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM

# ── SoC OpenOCD target (tb_top_soc: full CVA6 SoC with real CPU) ─────────────
# Usage:
#   make questa_soc_openocd                                                  # read_dmstatus (no ELF)
#   make questa_soc_openocd OPENOCD_SCENARIO=halt ELF=../sw/infinite_loop.elf # halt running program
#   make questa_soc_openocd_halt                                             # convenience shortcut
questa_soc_openocd: questa_soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "🚀 Starting vsim (full CVA6 SoC) with JTAG bitbang server..."
	$(VSIM_BATCH) $(VSIM_SOC_FLAGS) -do $(VSIM_SOC_DO) \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_soc \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=unused" \
	     +JTAG_MASTER=openocd \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	@echo "⏳ Waiting for JTAG bitbang server on port 9824..."
	@for i in $$(seq 1 60); do \
		if grep -q "Listening on port 9824" sim.log 2>/dev/null; then \
			echo "✅ Bitbang server ready"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then echo "❌ Timeout waiting for bitbang server"; exit 1; fi; \
		sleep 1; \
	done
	@echo "🚀 Starting OpenOCD + Python runner (scenario=$(OPENOCD_SCENARIO))..."
	python3 $(RUNNER) --transport openocd --scenario $(OPENOCD_SCENARIO) --mode batch --log-level DEBUG

# Convenience: halt the infinite loop test on CVA6 SoC via OpenOCD
questa_soc_openocd_halt: OPENOCD_SCENARIO = halt
questa_soc_openocd_halt: ELF = ../sw/infinite_loop.elf
questa_soc_openocd_halt: questa_soc_openocd


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
	rm -rf simv simv.daidir csrc xcelium.d work uvm_bridge.so uvm_bridge_soc.so \
	       *.log *.vcd *.vpd ucli.key novas* verdiLog* transcript

.PHONY: vcs_compile vcs_batch vcs_interactive \
        xrun_batch xrun_interactive \
        questa_compile questa_batch questa_interactive questa_mem_scan \
        questa_openocd questa_openocd_halt questa_openocd_read_dmstatus questa_openocd_cleanup \
        questa_soc_compile questa_soc_batch questa_soc_interactive \
        questa_soc_openocd questa_soc_openocd_halt \
        questa_soc_test questa_soc_halt_test \
        openocd_batch openocd_interactive \
        python_test clean
