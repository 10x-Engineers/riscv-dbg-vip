# ──────────────────────────────────────────────────────────────────────────────
# Makefile — pydebug <-> CVA6-fork SoC integration
#
# Deploys the pip-installed `pydebug` package against a freshly cloned
# 10x-Engineers/CVA6-fork checkout. Source paths for the shared C/SV kit are
# resolved via `pydebug sources --c/--sv` (installed package), not hardcoded —
# only the CVA6 RTL paths below are specific to this SoC.
#
#   make soc_compile   — compile CVA6 SoC + pydebug JTAG/DPI kit
#   make soc_test      — run halt/read-PC/resume session (UVM socket transport)
#   make soc_openocd    — run the same session over OpenOCD remote-bitbang
#   make soc_interactive — live, GDB-style interactive session (UVM socket)
#
# Runs on Questa or Xcelium; the tool invocation lives in ../mk/simulator.mk
# and is selected with SIM=questa | SIM=xcelium (auto-detected from PATH when
# unset). `make sim_info` prints what was resolved.
# ──────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

CVA6_REPO_DIR := $(abspath ../CVA6-fork)
SIM_OUTPUT_DIR = ./sim_outputs
TB_TOP         = tb_top_soc

# ── pydebug-provided sources (resolved via the installed CLI) ────────────────
PYDEBUG_C_DIR  := $(shell pydebug sources --c-dir)
PYDEBUG_SV_DIR := $(shell pydebug sources --sv-dir)

SRC_C_SOC = $(PYDEBUG_C_DIR)/uvm_bridge.c $(PYDEBUG_C_DIR)/remote_bitbang.c $(PYDEBUG_C_DIR)/elfloader.c

# Compile order matters: dm_defines_pkg -> jtag_if -> jtag_pkg (pulls in
# model/types + agents/jtag txn-driver-monitor-agent) -> debug_pkg (pulls in
# sequences/scoreboard/fcov/model/env/py_bridge/rv_dbg_base_test) ->
# jtag_bitbang -> our tb top.
SRC_SV_KIT = \
    $(PYDEBUG_SV_DIR)/model/dm_defines_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_if.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_pkg.sv \
    $(PYDEBUG_SV_DIR)/env/debug_pkg.sv \
    $(PYDEBUG_SV_DIR)/agents/jtag/jtag_bitbang.sv \
    tb_top_cva6.sv

# Questa-only run flags for this SoC (unused under SIM=xcelium): -novopt keeps
# the full hierarchy visible, and 12110 is the advisory about having done so.
VSIM_EXTRA = -novopt -suppress 12110

RUNNER   ?= pydebug run
CFG_FILE ?= configs/halt_uvm.json
# rv_dbg_base_test.sv launches this via `python3 -u <PYTHON_SEQ>`, so it must
# be a module/script arg (not a full shell command like `pydebug run ...`).
PYTHON_SEQ ?= -m pydebug.cli run --config $(CFG_FILE)

ELF ?= sw/halt_probe.elf
ELF_PLUSARGS = $(if $(ELF),+enable_boot "+elf_file=$(abspath $(ELF))",)

OPENOCD_SCENARIO ?= halt
OPENOCD_SOC_CFG  ?= configs/openocd_bitbang_soc.cfg

# ── Functional-coverage collection ────────────────────────────────────────────
# The per-tool details — Questa needing +cover=<spec> at vlog time and
# `onfinish stop` before `coverage save`, Xcelium needing its -covworkdir to
# already exist — live in ../mk/simulator.mk next to the commands they qualify.
COV_LIB        = work_cov
COV_DIR        = $(SIM_OUTPUT_DIR)/coverage
RESULTS_DIR    = ../testplans/results
COV_REPORT_TXT = $(RESULTS_DIR)/cva6_functional_coverage_merged.txt
UCDB_NAME      = $(basename $(notdir $(CFG_FILE)))
COV_CONFIGS    = $(wildcard configs/*_uvm.json)

# Selects Questa or Xcelium and defines every $(SIM_*) used below.
include ../mk/simulator.mk

# ── CVA6 RTL: flags and sources shared by the plain and coverage builds ───────
# One list, used twice. It was duplicated verbatim between soc_compile and
# soc_compile_cov, which is exactly how a coverage build ends up measuring a
# different set of files than the one under test.
CVA6_DEFINES = +define+RISCV_VIP_MODE +define+DUT_VERSION_1_0

CVA6_INCDIRS = \
    +incdir+$(CVA6_REPO_DIR)/corev_apu/register_interface/include \
    +incdir+$(CVA6_REPO_DIR)/corev_apu/instr_tracing/ITI/include \
    +incdir+$(CVA6_REPO_DIR)/corev_apu/fpga/src/apb/include \
    +incdir+$(CVA6_REPO_DIR)/core/include/ \
    +incdir+$(CVA6_REPO_DIR)/vendor/pulp-platform/axi/include

# NOTE: config_pkg.sv is deliberately absent — flist_soc.tmp already compiles
# it (the flattener emits it), and naming it again here compiles the package
# twice. Questa downgrades that to a "recompiling design unit" warning;
# Xcelium raises *E,DLCIRD "circular dependency" and stops.
CVA6_SRC_SOC = \
    $(CVA6_REPO_DIR)/corev_apu/instr_tracing/ITI/include/iti_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/fpga/src/apb/src/apb_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dm_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/ariane_soc_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/axi_intf.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/ariane_axi_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/ariane_axi_soc_pkg.sv \
    $(CVA6_REPO_DIR)/corev_apu/axi_mem_if/src/axi2mem.sv \
    $(CVA6_REPO_DIR)/corev_apu/clint/*.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/debug_rom/debug_rom.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dm_csrs.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dm_mem.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dm_sba.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dm_top.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dmi_cdc.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dmi_jtag.sv \
    $(CVA6_REPO_DIR)/corev_apu/riscv-dbg/src/dmi_jtag_tap.sv \
    $(CVA6_REPO_DIR)/corev_apu/rv_plic/rtl/rv_plic_target.sv \
    $(CVA6_REPO_DIR)/corev_apu/rv_plic/rtl/rv_plic_gateway.sv \
    $(CVA6_REPO_DIR)/corev_apu/rv_plic/rtl/plic_regmap.sv \
    $(CVA6_REPO_DIR)/corev_apu/rv_plic/rtl/plic_top.sv \
    $(CVA6_REPO_DIR)/corev_apu/fpga/src/axi2apb/src/*.sv \
    $(CVA6_REPO_DIR)/corev_apu/fpga/src/axi_slice/src/*.sv \
    $(CVA6_REPO_DIR)/corev_apu/register_interface/src/apb_to_reg.sv \
    $(CVA6_REPO_DIR)/corev_apu/register_interface/src/reg_intf.sv \
    $(CVA6_REPO_DIR)/corev_apu/fpga/src/apb_timer/*.sv \
    $(CVA6_REPO_DIR)/corev_apu/fpga/src/apb_uart/src/*.sv \
    $(CVA6_REPO_DIR)/corev_apu/bootrom/bootrom.sv \
    $(CVA6_REPO_DIR)/corev_apu/src/ariane.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi_riscv_atomics/src/*.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/rstgen_bypass.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/rstgen.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/addr_decode.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/stream_register.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_cut.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_join.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_delayer.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_to_axi_lite.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_id_prepend.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_atop_filter.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_err_slv.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_mux.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_demux.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/axi/src/axi_xbar.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/cdc_2phase.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/spill_register_flushable.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/spill_register.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/deprecated/fifo_v1.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/deprecated/fifo_v2.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/stream_delay.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/common_cells/src/lfsr_16bit.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/tech_cells_generic/src/deprecated/cluster_clk_cells.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/tech_cells_generic/src/deprecated/pulp_clk_cells.sv \
    $(CVA6_REPO_DIR)/vendor/pulp-platform/tech_cells_generic/src/rtl/tc_clk.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/common/uart.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/ariane_peripherals.sv \
    $(CVA6_REPO_DIR)/corev_apu/tb/ariane_testharness.sv

# CVA6's own flattener resolves Flist.cva6 (which needs these three env vars)
# into a plain file list the simulator can consume.
define cva6_flatten
	export CVA6_REPO_DIR=$(CVA6_REPO_DIR); \
	export TARGET_CFG=cv64a6_imafdc_sv39; \
	export HPDCACHE_DIR=$(CVA6_REPO_DIR)/core/cache_subsystem/hpdcache; \
	python3 $(CVA6_REPO_DIR)/util/flist_flattener.py --print_incdir --print_newline \
	    $(CVA6_REPO_DIR)/core/Flist.cva6 > flist_soc.tmp
endef

uvm_bridge_soc.so: $(SRC_C_SOC)
	gcc -shared -fPIC -std=c11 \
	    -I"$(PYDEBUG_C_DIR)" \
	    -I/usr/include/x86_64-linux-gnu \
	    -I"$(DPI_INC)" \
	    $(SRC_C_SOC) -o uvm_bridge_soc.so -lpthread

soc_compile: uvm_bridge_soc.so sw/$(notdir $(ELF))
	$(SIM_PRE_COMPILE)
	@$(cva6_flatten)
	$(SIM_COMPILE) $(CVA6_DEFINES) $(CVA6_INCDIRS) \
	    -f flist_soc.tmp \
	    $(CVA6_SRC_SOC) \
	    $(SRC_SV_KIT) \
	    $(SIM_COMPILE_POST)
	@rm -f flist_soc.tmp

sw/$(notdir $(ELF)):
	$(MAKE) -C sw

soc_compile_cov: uvm_bridge_soc.so sw/$(notdir $(ELF))
	$(SIM_PRE_COMPILE_COV)
	@$(cva6_flatten)
	$(SIM_COMPILE_COV) $(CVA6_DEFINES) $(CVA6_INCDIRS) \
	    -f flist_soc.tmp \
	    $(CVA6_SRC_SOC) \
	    $(SRC_SV_KIT) \
	    $(SIM_COMPILE_COV_POST)
	@rm -f flist_soc.tmp

soc_test_cov: soc_compile_cov
	@mkdir -p $(COV_DIR)
	$(SIM_RUN_COV) \
	     +UVM_TESTNAME=debug_test \
	     +PYTHON_SEQ="$(PYTHON_SEQ)" \
	     $(ELF_PLUSARGS) \
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

soc_test: soc_compile
	@mkdir -p $(SIM_OUTPUT_DIR); \
	 TEST_NUM=$$(ls -1 $(SIM_OUTPUT_DIR)/soc_test_*.log 2>/dev/null | wc -l); \
	 OUTPUT_FILE=$(SIM_OUTPUT_DIR)/soc_test_$$TEST_NUM.log; \
	 echo "Logging output to: $$OUTPUT_FILE"; \
	 $(SIM_RUN) \
	      +UVM_TESTNAME=debug_test \
	      +PYTHON_SEQ="$(PYTHON_SEQ)" \
	      $(ELF_PLUSARGS) \
	      +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee $$OUTPUT_FILE

soc_openocd: soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "Starting $(SIM) (full CVA6 SoC) with JTAG bitbang server..."
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
	$(RUNNER) --transport openocd --scenario $(OPENOCD_SCENARIO) --mode batch --openocd-config $(OPENOCD_SOC_CFG) --log-level DEBUG

# Live, GDB-style interactive session: the sim runs in the background with
# the UVM bridge active but no auto-launched Python client (+JTAG_MASTER=
# external, see rv_dbg_base_test.sv), then `pydebug interactive` connects
# from this same foreground terminal -- `pydebug interactive`'s own
# connect_transport() already polls for the bridge socket to appear, so no
# extra wait-loop is needed here (unlike soc_openocd's RBB-port grep).
soc_interactive: soc_compile
	@rm -f sim.log
	@mkdir -p $(SIM_OUTPUT_DIR)
	@echo "Starting $(SIM) (full CVA6 SoC) with UVM bridge active, no auto-launched client..."
	$(SIM_RUN) \
	     +UVM_TESTNAME=debug_test \
	     "+PYTHON_SEQ=unused" \
	     +JTAG_MASTER=external \
	     $(ELF_PLUSARGS) \
	     +UVM_VERBOSITY=UVM_MEDIUM 2>&1 | tee sim.log &
	pydebug interactive --transport uvm --log-level WARNING

clean:
	rm -rf $(SIM_CLEAN_ARTIFACTS) uvm_bridge_soc.so flist_soc.tmp sim.log
	rm -f sw/*.o sw/*.elf

.PHONY: soc_compile soc_test soc_openocd soc_interactive soc_compile_cov soc_test_cov coverage_regress coverage_merge clean
