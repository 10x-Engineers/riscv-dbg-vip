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
VIP_DIR   = $(TB_DIR)/jtag_vip
RTL_DIR   = ../riscv-dbg/src
C_DIR     = ../c_bridge
SEQ_DIR   = ../sequences
CFG_DIR   = ../configs

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
    $(VIP_DIR)/dm_defines_pkg.sv \
    $(VIP_DIR)/jtag_if.sv       \
    $(VIP_DIR)/jtag_pkg.sv      \
    $(TB_DIR)/debug_pkg.sv      \
    $(TB_DIR)/jtag_bitbang.sv   \
    $(TB_DIR)/tb_top.sv

# C sources for the DPI bridges (UVM bridge and Remote Bitbang server)
SRC_C   = $(C_DIR)/uvm_bridge.c $(C_DIR)/remote_bitbang.c

# +incdir so that jtag_pkg's `include "types.sv" etc. resolve correctly
INCDIRS = +incdir+$(VIP_DIR) +incdir+$(TB_DIR)

# Default Python runner and config
RUNNER   = ../run.py
CFG_FILE = $(CFG_DIR)/halt_uvm.json

# Default command-line to run the Python sequencer
PYTHON_SEQ ?= $(RUNNER) --config $(CFG_FILE)

# ══════════════════════════════════════════════════════════════════════════════
# Questa
# ══════════════════════════════════════════════════════════════════════════════
QUESTA_FLAGS = -sv -timescale 1ns/1ps $(INCDIRS)

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
	vsim -c -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(PYTHON_SEQ)" \
	     +UVM_VERBOSITY=UVM_MEDIUM

# Run in interactive mode (GUI usually, or just interactive terminal)
questa_interactive: questa_compile
	vsim -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(RUNNER) --config $(CFG_FILE) --mode interactive" \
	     +PYTHON_MODE=interactive \
	     +UVM_VERBOSITY=UVM_MEDIUM

# Target for running a specific memory scan sequence
questa_mem_scan: questa_compile
	vsim -c -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ=$(SEQ_DIR)/mem_scan_sequence.py \
	     +PYTHON_MODE=batch \
	     +PYTHON_EXTRA="--base 0x80000000 --count 8" \
	     +UVM_VERBOSITY=UVM_MEDIUM

# Target for reading the DMSTATUS register specifically
questa_read_dmstatus: questa_compile
	vsim -c -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=$(RUNNER) --config $(CFG_DIR)/read_dmstatus_uvm.json" \
	     +UVM_VERBOSITY=UVM_MEDIUM

questa_openocd_cleanup:
	@echo "🔄 Cleaning up any existing Questa/OpenOCD processes..."
	@kill -9 -f "vsim" 2>/dev/null || true
	@kill -9 -f "openocd" 2>/dev/null || true
	@sleep 1
# Target to run OpenOCD alongside the simulator using an orchestration script
questa_openocd: questa_compile
	@echo "🚀 Starting vsim..."
	vsim -c -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=$(RUNNER) --transport openocd --scenario read_dmstatus --mode batch --log-level DEBUG" \
	     +JTAG_MASTER=openocd \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 &

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
	python3 -m pytest ../tests/ -v

# Remove all generated files (compiled libs, logs, wave files)
clean:
	rm -rf simv simv.daidir csrc xcelium.d work uvm_bridge.so \
	       *.log *.vcd *.vpd ucli.key novas* verdiLog* transcript

.PHONY: vcs_compile vcs_batch vcs_interactive \
        xrun_batch xrun_interactive \
        questa_compile questa_batch questa_interactive questa_mem_scan \
        openocd_batch openocd_interactive \
        python_test clean
