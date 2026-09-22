# ──────────────────────────────────────────────────────────────────────────────
# Makefile — pydebug <-> the Debug Module, standalone, with more than one hart
#
# Mirrors cva6_sim/ and ibex_sim/, but there is no SoC here: tb_top_multihart.sv
# instantiates dm_top directly with NrHarts=2 and stands dbg_dummy_hart behind
# it, which is enough for the DM to believe in two harts (see that file, and
# src/pydebug/sv/agents/hart/dbg_dummy_hart.sv, for why that works).
#
#   make soc_compile   — compile the DM, the DTM and the pydebug JTAG kit
#   make soc_test      — run a scenario (CFG_FILE=configs/<name>.json)
#   make coverage_regress / coverage_merge — as the other two sims
#
# Runs on Questa or Xcelium; the tool invocation lives in ../mk/simulator.mk.
# ──────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

SIM_OUTPUT_DIR = ./sim_outputs
TB_TOP         = tb_top_multihart

PYDEBUG_C_DIR  := $(shell pydebug sources --c-dir)
PYDEBUG_SV_DIR := $(shell pydebug sources --sv-dir)

SRC_C_SOC = $(PYDEBUG_C_DIR)/uvm_bridge.c $(PYDEBUG_C_DIR)/remote_bitbang.c $(PYDEBUG_C_DIR)/elfloader.c

# Same order as the other two sims: defines, interfaces, packages, then the
# testbench. The hart stubs come before the top that instantiates them.
SRC_SV_KIT = \
    $(PYDEBUG_SV_DIR)/model/dm_defines_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_if.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/axi/dbg_axi_if.sv \
    $(PYDEBUG_SV_DIR)/agents/axi/dbg_axi_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/backdoor/dbg_dm_backdoor_if.sv \
    $(PYDEBUG_SV_DIR)/agents/backdoor/dbg_hart_backdoor_if.sv \
    $(PYDEBUG_SV_DIR)/agents/dmi/dbg_dmi_if.sv \
    $(PYDEBUG_SV_DIR)/agents/dmi/dbg_dmi_pkg.sv \
    $(PYDEBUG_SV_DIR)/env/debug_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_bitbang.sv \
    $(PYDEBUG_SV_DIR)/agents/hart/dbg_dummy_hart.sv \
    $(PYDEBUG_SV_DIR)/agents/hart/dbg_hart_arbiter.sv \
    tb_top_multihart.sv

RUNNER   ?= pydebug run
CFG_FILE ?= configs/hart_array_uvm.json
PYTHON_SEQ ?= -m pydebug.cli run --config $(CFG_FILE)

# No ELF: there is no memory and no processor to load one into. The other two
# sims pass +elf_file; this one deliberately does not.
PLUSARGS ?=

# ── Functional-coverage collection ────────────────────────────────────────────
COV_LIB        = work_cov
COV_DIR        = $(SIM_OUTPUT_DIR)/coverage
RESULTS_DIR    = ../testplans/results
COV_REPORT_TXT = $(RESULTS_DIR)/multihart_functional_coverage_merged.txt
UCDB_NAME      = $(basename $(notdir $(CFG_FILE)))
COV_CONFIGS    = $(wildcard configs/*_uvm.json)

include ../mk/simulator.mk

uvm_bridge_soc.so: $(SRC_C_SOC)
	gcc -shared -fPIC -std=c11 \
	    -I"$(PYDEBUG_C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I"$(DPI_INC)" \
	    $(SRC_C_SOC) -o uvm_bridge_soc.so -lpthread

soc_compile: uvm_bridge_soc.so
	$(SIM_PRE_COMPILE)
	$(SIM_COMPILE) -f flist_multihart.f $(SRC_SV_KIT) $(SIM_COMPILE_POST)

soc_test: soc_compile
	@mkdir -p $(RESULT_DIR); \
	 echo "Logging output to: $(RESULT_DIR)/run.log"; \
	 $(SIM_RUN) \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $(RESULT_DIR)/run.log
	@$(collect_results)

soc_compile_cov: uvm_bridge_soc.so
	$(SIM_PRE_COMPILE_COV)
	$(SIM_COMPILE_COV) -f flist_multihart.f $(SRC_SV_KIT) $(SIM_COMPILE_COV_POST)

soc_test_cov: soc_compile_cov
	@mkdir -p $(COV_DIR)
	$(SIM_RUN_COV) \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(PYTHON_SEQ)" \
	     $(PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $(COV_DIR)/$(UCDB_NAME).log

coverage_regress: soc_compile_cov
	@mkdir -p $(COV_DIR)
	@for cfg in $(COV_CONFIGS); do \
		echo "=== coverage run: $$cfg ==="; \
		$(MAKE) --no-print-directory soc_test_cov CFG_FILE=$$cfg || \
			echo "!!! scenario $$cfg failed, continuing !!!"; \
	done

coverage_merge:
	@mkdir -p $(RESULTS_DIR)
	$(SIM_COV_MERGE_REPORT)

clean:
	rm -rf $(SIM_CLEAN_ARTIFACTS) uvm_bridge_soc.so sim.log

.PHONY: soc_compile soc_test soc_compile_cov soc_test_cov coverage_regress coverage_merge clean
