# ──────────────────────────────────────────────────────────────────────────────
# Makefile — pydebug <-> ibex-demo-system SoC integration (Questa)
#
# Mirrors ../../integration_with_cva6/cva6_sim/Makefile: deploys the
# pip-installed `pydebug` package (via `pydebug sources --c/--sv`) against
# our existing ibex-demo-system checkout. flist_ibex.f and prim_shims/ are
# generic RTL glue (not pydebug-specific) needed to compile ibex-demo-system
# standalone in Questa.
#
#   make soc_compile   — compile ibex-demo-system + pydebug JTAG/DPI kit
#   make soc_test      — run halt/read-PC/resume session (UVM socket transport)
#   make soc_openocd   — run the same session over OpenOCD remote-bitbang
# ──────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

SIM_OUTPUT_DIR = ./sim_outputs

PYDEBUG_C_DIR  := $(shell pydebug sources --c-dir)
PYDEBUG_SV_DIR := $(shell pydebug sources --sv-dir)

SRC_C_SOC = $(PYDEBUG_C_DIR)/uvm_bridge.c $(PYDEBUG_C_DIR)/remote_bitbang.c $(PYDEBUG_C_DIR)/elfloader.c

# Compile order matters: dm_defines_pkg -> jtag_if -> jtag_pkg (pulls in
# model/types + agents/txn-driver-monitor-agent) -> debug_pkg (pulls in
# sequences/scoreboard/fcov/model/env/py_bridge/rv_dbg_base_test) ->
# jtag_bitbang -> our tb top.
SRC_SV_KIT = \
    $(PYDEBUG_SV_DIR)/model/dm_defines_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_if.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_pkg.sv \
    $(PYDEBUG_SV_DIR)/env/debug_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_bitbang.sv \
    tb_top_ibex.sv

IBEX_INCDIRS = +incdir+../ibex-demo-system/vendor/lowrisc_ip/ip/prim/rtl \
               +incdir+../ibex-demo-system/vendor/lowrisc_ibex/vendor/lowrisc_ip/dv/sv/dv_utils \
               +incdir+../ibex-demo-system/vendor/lowrisc_ibex/dv/uvm/core_ibex/common/prim \
               +incdir+./prim_shims

QUESTA_FLAGS = -sv -timescale 1ns/1ps
VSIM       ?= env -u DISPLAY vsim
VSIM_BATCH ?= env -u DISPLAY vsim -batch

RUNNER   ?= pydebug run
CFG_FILE ?= configs/halt_uvm.json
PYTHON_SEQ ?= -m pydebug.cli run --config $(CFG_FILE)

ELF ?= sw/halt_probe.elf
ELF_PLUSARGS = $(if $(ELF),"+elf_file=$(abspath $(ELF))",)

OPENOCD_SCENARIO ?= halt
OPENOCD_IBEX_CFG ?= configs/openocd_bitbang_ibex.cfg

uvm_bridge_soc.so: $(SRC_C_SOC)
	gcc -shared -fPIC -std=c11 \
	    -I"$(PYDEBUG_C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I/home/jk/mentor/questasim/include \
	    $(SRC_C_SOC) -o uvm_bridge_soc.so -lpthread

soc_compile: uvm_bridge_soc.so sw/$(notdir $(ELF))
	vlib work
	vlog $(QUESTA_FLAGS) $(IBEX_INCDIRS) \
	    +define+PRIM_DEFAULT_IMPL=prim_pkg::ImplGeneric \
	    +define+INC_ASSERT \
	    +define+RVFI \
	    -f flist_ibex.f \
	    $(SRC_SV_KIT)

sw/$(notdir $(ELF)):
	$(MAKE) -C sw

soc_test: soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/soc_test_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/soc_test_$$TEST_NUM.log; \
	 echo "Logging output to: $$OUTPUT_FILE"; \
	 $(VSIM_BATCH) -do "run -all; quit -f" \
	      -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_ibex \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(ELF_PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

soc_openocd: soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "Starting vsim (ibex-demo-system) with JTAG bitbang server..."
	$(VSIM_BATCH) -do "run -all; quit -f" \
	     -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_ibex \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=unused" \
	     +JTAG_MASTER=openocd \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	@echo "Waiting for JTAG bitbang server on port 9824..."
	@for i in $$(seq 1 60); do \
		if grep -q "Listening on port 9824" sim.log 2>/dev/null; then \
			echo "Bitbang server ready"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then echo "Timeout waiting for bitbang server"; exit 1; fi; \
		sleep 1; \
	done
	@echo "Starting OpenOCD + pydebug (scenario=$(OPENOCD_SCENARIO))..."
	$(RUNNER) --transport openocd --scenario $(OPENOCD_SCENARIO) --mode batch --openocd-config $(OPENOCD_IBEX_CFG) --log-level DEBUG

clean:
	rm -rf work uvm_bridge_soc.so sim.log transcript vsim.wlf
	rm -f sw/*.o sw/*.elf

.PHONY: soc_compile soc_test soc_openocd clean
