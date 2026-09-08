# ──────────────────────────────────────────────────────────────────────────────
# Makefile — pydebug <-> ibex-demo-system SoC integration
#
# Mirrors ../../integration_with_cva6/cva6_sim/Makefile: deploys the
# pip-installed `pydebug` package (via `pydebug sources --c/--sv`) against
# our existing ibex-demo-system checkout. flist_ibex.f and prim_shims/ are
# generic RTL glue (not pydebug-specific) needed to compile ibex-demo-system
# standalone.
#
#   make soc_compile   — compile ibex-demo-system + pydebug JTAG/DPI kit
#   make soc_test      — run halt/read-PC/resume session (UVM socket transport)
#   make soc_openocd   — run the same session over OpenOCD remote-bitbang
#   make soc_interactive — live, GDB-style interactive session (UVM socket)
#
# Runs on Questa or Xcelium; the tool invocation lives in ../mk/simulator.mk
# and is selected with SIM=questa | SIM=xcelium (auto-detected from PATH when
# unset). `make sim_info` prints what was resolved.
# ──────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

SIM_OUTPUT_DIR = ./sim_outputs
TB_TOP         = tb_top_ibex

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

RUNNER   ?= pydebug run
CFG_FILE ?= configs/halt_uvm.json
PYTHON_SEQ ?= -m pydebug.cli run --config $(CFG_FILE)

ELF ?= sw/halt_probe.elf
ELF_PLUSARGS = $(if $(ELF),"+elf_file=$(abspath $(ELF))",)

OPENOCD_SCENARIO ?= halt
OPENOCD_IBEX_CFG ?= configs/openocd_bitbang_ibex.cfg

# ── Functional-coverage collection ────────────────────────────────────────────
# A separate library/snapshot, so day-to-day debug runs (`soc_test`) keep using
# the uninstrumented build. The per-tool details — Questa needing +cover=<spec>
# at vlog time and `onfinish stop` before `coverage save`, Xcelium needing its
# -covworkdir to already exist — live in ../mk/simulator.mk, next to the
# commands they qualify.
COV_LIB        = work_cov
COV_DIR        = $(SIM_OUTPUT_DIR)/coverage
RESULTS_DIR    = ../testplans/results
COV_REPORT_TXT = $(RESULTS_DIR)/ibex_functional_coverage_merged.txt
UCDB_NAME      = $(basename $(notdir $(CFG_FILE)))
# Every scenario config that drives real stimulus (excludes openocd/hw configs).
COV_CONFIGS    = $(wildcard configs/*_uvm.json)

# Selects Questa or Xcelium and defines every $(SIM_*) used below.
include ../mk/simulator.mk

IBEX_DEFINES = +define+PRIM_DEFAULT_IMPL=prim_pkg::ImplGeneric \
               +define+INC_ASSERT \
               +define+RVFI

uvm_bridge_soc.so: $(SRC_C_SOC)
	gcc -shared -fPIC -std=c11 \
	    -I"$(PYDEBUG_C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I"$(DPI_INC)" \
	    $(SRC_C_SOC) -o uvm_bridge_soc.so -lpthread

soc_compile: uvm_bridge_soc.so sw/$(notdir $(ELF))
	$(SIM_PRE_COMPILE)
	$(SIM_COMPILE) $(IBEX_INCDIRS) $(IBEX_DEFINES) \
	    -f flist_ibex.f \
	    $(SRC_SV_KIT) \
	    $(SIM_COMPILE_POST)

sw/$(notdir $(ELF)):
	$(MAKE) -C sw

soc_test: soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/soc_test_$(UCDB_NAME).log; \
	 echo "Logging output to: $$OUTPUT_FILE"; \
	 $(SIM_RUN) \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(ELF_PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

soc_openocd: soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "Starting $(SIM) (ibex-demo-system) with JTAG bitbang server..."
	$(SIM_RUN) \
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

# Live, GDB-style interactive session: the sim runs in the background with
# the UVM bridge active but no auto-launched Python client (+JTAG_MASTER=
# external, see rv_dbg_base_test.sv), then `pydebug interactive` connects
# from this same foreground terminal -- `pydebug interactive`'s own
# connect_transport() already polls for the bridge socket to appear, so no
# extra wait-loop is needed here (unlike soc_openocd's RBB-port grep).
soc_interactive: soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "Starting $(SIM) (ibex-demo-system) with UVM bridge active, no auto-launched client..."
	$(SIM_RUN) \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=unused" \
	     +JTAG_MASTER=external \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	pydebug interactive --transport uvm --log-level WARNING

soc_compile_cov: uvm_bridge_soc.so sw/$(notdir $(ELF))
	$(SIM_PRE_COMPILE_COV)
	$(SIM_COMPILE_COV) $(IBEX_INCDIRS) $(IBEX_DEFINES) \
	    -f flist_ibex.f \
	    $(SRC_SV_KIT) \
	    $(SIM_COMPILE_COV_POST)

# Run one scenario against the coverage-instrumented build, saving its own
# database named after the scenario config (re-running the same scenario
# refreshes it rather than accumulating duplicates).
soc_test_cov: soc_compile_cov
	@mkdir -p $(COV_DIR)
	$(SIM_RUN_COV) \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(PYTHON_SEQ)" \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $(COV_DIR)/$(UCDB_NAME).log

# Run every *_uvm.json scenario config against the coverage library, each
# producing its own UCDB under $(COV_DIR). Continues past a single scenario's
# failure (-) so one broken/unimplemented scenario doesn't block the rest.
coverage_regress: soc_compile_cov
	@mkdir -p $(COV_DIR)
	@for cfg in $(COV_CONFIGS); do \
		echo "=== coverage run: $$cfg ==="; \
		$(MAKE) --no-print-directory soc_test_cov CFG_FILE=$$cfg || \
			echo "!!! scenario $$cfg failed, continuing !!!"; \
	done

# Merge every scenario's coverage database into one aggregate and report the
# true combined functional-coverage percentage (bins hit in ANY run count as
# covered) — the number no single scenario log can show on its own.
coverage_merge:
	@mkdir -p $(RESULTS_DIR)
	$(SIM_COV_MERGE_REPORT)

clean:
	rm -rf $(SIM_CLEAN_ARTIFACTS) uvm_bridge_soc.so sim.log
	rm -f sw/*.o sw/*.elf

.PHONY: soc_compile soc_test soc_openocd soc_interactive soc_compile_cov soc_test_cov coverage_regress coverage_merge clean
