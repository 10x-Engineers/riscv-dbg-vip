# ──────────────────────────────────────────────────────────────────────────────
# mk/simulator.mk — simulator abstraction shared by cva6_sim/ and ibex_sim/
#
#   make SIM=questa  ...   Siemens Questa  (vlib/vlog/vsim, UCDB, vcover)
#   make SIM=xcelium ...   Cadence Xcelium (xrun -elaborate / -R, .ucd, imc)
#
# With no SIM= given, whichever simulator is actually on PATH is used, Questa
# first — so a machine that has Questa keeps behaving exactly as before, and a
# machine that has only Xcelium works without an override. `make sim_info`
# prints the resolved choice.
#
# A per-SoC Makefile sets TB_TOP, SIM_OUTPUT_DIR, PYDEBUG_SV_DIR and
# COV_REPORT_TXT, includes this file, and then builds its recipes from:
#
#   $(SIM_PRE_COMPILE)      library/directory creation the tool needs first
#   $(SIM_COMPILE)          compile+elaborate command, before flags and files
#   $(SIM_COMPILE_POST)     trailing args (Xcelium wants -top after the files)
#   $(SIM_RUN)              run the built snapshot, before plusargs
#   $(SIM_RUN_COV)          same, recording coverage under $(UCDB_NAME)
#   $(SIM_COV_MERGE_REPORT) merge every scenario's coverage and report it
#   $(DPI_INC)              the tool's DPI header directory, for the .so build
#   $(SIM_CLEAN_ARTIFACTS)  tool droppings for `make clean`
#
# The *_COV variants build into a separate library/snapshot in both tools, so
# day-to-day debug runs stay uninstrumented and fast.
# ──────────────────────────────────────────────────────────────────────────────

# ── Which simulator ───────────────────────────────────────────────────────────
# Questa first, so results published against it stay reproducible by default on
# a machine that has both.
# $(strip) is load-bearing: the line continuation below otherwise leaves a
# leading space in the value, and ' xcelium' matches no ifeq branch.
SIM_DETECTED := $(strip $(if $(shell command -v vsim 2>/dev/null),questa,\
                  $(if $(shell command -v xrun 2>/dev/null),xcelium,none)))
SIM ?= $(if $(filter none,$(SIM_DETECTED)),questa,$(SIM_DETECTED))

TB_TOP         ?= $(error TB_TOP must be set before including mk/simulator.mk)
SIM_OUTPUT_DIR ?= ./sim_outputs
COV_LIB        ?= work_cov
COV_DIR        ?= $(SIM_OUTPUT_DIR)/coverage
DPI_LIB_NAME   ?= uvm_bridge_soc

# Every package in the pydebug kit `include`s its siblings by bare name
# ("jtag_txn.sv") or by a path relative to its own directory
# ("../model/types.sv"). Questa's vlog searches the including file's own
# directory and finds them; Xcelium searches only +incdir+ and the cwd, and
# without these two entries fails with 17 *E,COFILX "cannot open include file".
# Passed to both tools: harmless for Questa, and it stops the search depending
# on a vendor default.
SIM_KIT_INCDIRS = +incdir+$(PYDEBUG_SV_DIR)/agents/jtag +incdir+$(PYDEBUG_SV_DIR)/agents/axi +incdir+$(PYDEBUG_SV_DIR)/agents/dmi \
                  +incdir+$(PYDEBUG_SV_DIR)/model +incdir+$(PYDEBUG_SV_DIR)/env

# ══════════════════════════════════════════════════════════════════════════════
ifeq ($(SIM),questa)
# ══════════════════════════════════════════════════════════════════════════════

# Questa ships svdpi.h inside the install. $(MODEL_TECH) is set by Questa's own
# setup and points at the tool binaries; otherwise derive the root from wherever
# vsim is on PATH. Never a hardcoded install path — that only works on one
# machine.
QUESTA_BIN  := $(shell command -v vsim 2>/dev/null)
QUESTA_HOME ?= $(if $(MODEL_TECH),$(abspath $(MODEL_TECH)/..),\
                 $(if $(QUESTA_BIN),$(abspath $(dir $(QUESTA_BIN))/..)))
# Left empty rather than guessed when Questa is absent, so sim_info reports the
# header as MISSING instead of printing a nonsense path like '//include'.
DPI_INC     ?= $(if $(QUESTA_HOME),$(QUESTA_HOME)/include)

VSIM_BATCH ?= env -u DISPLAY vsim -batch
VSIM_EXTRA ?=

SIM_PRE_COMPILE      = vlib work
SIM_COMPILE          = vlog -sv -timescale 1ns/1ps $(SIM_KIT_INCDIRS)
SIM_COMPILE_POST     =

SIM_PRE_COMPILE_COV  = vlib $(COV_LIB)
# +cover=<spec> must be given at vlog time: a runtime-only -coverage against an
# uninstrumented library silently produces no UCDB (vsim-8634).
SIM_COMPILE_COV      = vlog -sv -timescale 1ns/1ps +cover=sbceft -work $(COV_LIB) $(SIM_KIT_INCDIRS)
SIM_COMPILE_COV_POST =

SIM_RUN = $(VSIM_BATCH) $(VSIM_EXTRA) -do "run -all; quit -f" \
          -dpioutoftheblue 1 -sv_lib $(DPI_LIB_NAME) work.$(TB_TOP)

# `onfinish stop` before `run -all` is required: the UVM $finish otherwise exits
# the batch process before the trailing `coverage save` ever runs.
SIM_RUN_COV = $(VSIM_BATCH) $(VSIM_EXTRA) -coverage \
          -do "onfinish stop; run -all; coverage save $(COV_DIR)/$(UCDB_NAME).ucdb; quit -f" \
          -dpioutoftheblue 1 -sv_lib $(DPI_LIB_NAME) $(COV_LIB).$(TB_TOP)

SIM_COV_MERGE_REPORT = \
	vcover merge $(COV_DIR)/merged.ucdb \
	    $(filter-out $(COV_DIR)/merged.ucdb,$(wildcard $(COV_DIR)/*.ucdb)) && \
	vcover report -cvg -details $(COV_DIR)/merged.ucdb | tee $(COV_REPORT_TXT)

# ══════════════════════════════════════════════════════════════════════════════
else ifeq ($(SIM),xcelium)
# ══════════════════════════════════════════════════════════════════════════════

XCELIUM_HOME ?= $(XCELIUM)
DPI_INC      ?= $(XCELIUM_HOME)/tools/include

# Questa links UVM in automatically; Xcelium needs the library named. CDNS-1.2
# matches the UVM the kit is written against.
XRUN_UVM_HOME ?= $(XCELIUM_HOME)/tools/methodology/UVM/CDNS-1.2

XRUN         ?= xrun
XRUN_FLAGS   ?= -64bit
XRUN_LIB     ?= ./xcelium.d
XRUN_LIB_COV ?= ./xcelium_cov.d

# imc ships with vManager, not Xcelium, so it is often neither on PATH nor
# licensed on a machine that can happily run xrun. Point IMC at it if so.
IMC ?= imc

XRUN_COMMON = $(XRUN) $(XRUN_FLAGS) -sv -timescale 1ns/1ps \
              -uvmhome $(XRUN_UVM_HOME) $(SIM_KIT_INCDIRS)

# -elaborate builds the snapshot only; each `soc_test` then reruns it with -R
# and fresh plusargs, which is the two-phase shape the Questa flow already has.
SIM_PRE_COMPILE      = @mkdir -p $(SIM_OUTPUT_DIR)
SIM_COMPILE          = $(XRUN_COMMON) -elaborate -xmlibdirname $(XRUN_LIB)
SIM_COMPILE_POST     = -top $(TB_TOP) -sv_lib $(DPI_LIB_NAME).so

SIM_PRE_COMPILE_COV  = @mkdir -p $(COV_DIR)
SIM_COMPILE_COV      = $(XRUN_COMMON) -elaborate -xmlibdirname $(XRUN_LIB_COV) \
                       -coverage all -covoverwrite
SIM_COMPILE_COV_POST = -top $(TB_TOP) -sv_lib $(DPI_LIB_NAME).so

SIM_RUN = $(XRUN) $(XRUN_FLAGS) -R -xmlibdirname $(XRUN_LIB) -sv_lib $(DPI_LIB_NAME).so

# xrun refuses to create the coverage directory itself (*E,CNDIR) and then
# silently falls back to ./cov_work, so mkdir it here rather than losing the
# run's data somewhere else.
SIM_RUN_COV = mkdir -p $(COV_DIR) && \
          $(XRUN) $(XRUN_FLAGS) -R -xmlibdirname $(XRUN_LIB_COV) -sv_lib $(DPI_LIB_NAME).so \
          -covworkdir $(COV_DIR) -covtest $(UCDB_NAME) -covoverwrite

SIM_COV_MERGE_REPORT = IMC="$(IMC)" $(dir $(lastword $(MAKEFILE_LIST)))xcelium_cov_report.sh \
                       $(COV_DIR) $(COV_REPORT_TXT)

# ══════════════════════════════════════════════════════════════════════════════
else
$(error unknown SIM='$(SIM)' -- expected 'questa' or 'xcelium')
endif
# ══════════════════════════════════════════════════════════════════════════════

# Both tools' droppings, deliberately not conditioned on $(SIM): a tree built
# under Questa and then cleaned with SIM=xcelium (or the reverse) should still
# come out clean, and `rm -rf` on a path that was never created costs nothing.
SIM_CLEAN_ARTIFACTS = \
    work $(COV_LIB) transcript vsim.wlf vsim_stacktrace.vstf \
    xcelium.d xcelium_cov.d cov_work xrun.log xrun.history xmsc.d \
    .simvision waves.shm INCA_libs

## sim_info — print which simulator these targets will use, and where its
## DPI headers were found. Run this first when a build fails oddly.
sim_info:
	@echo "SIM          = $(SIM)$(if $(filter $(SIM),$(SIM_DETECTED)), (auto-detected), (explicit; auto-detected was '$(SIM_DETECTED)'))"
	@echo "TB_TOP       = $(TB_TOP)"
	@echo "DPI_INC      = $(DPI_INC)"
	@echo "  svdpi.h    : $(if $(wildcard $(DPI_INC)/svdpi.h),found,MISSING -- set DPI_INC or the tool's home variable)"
ifeq ($(SIM),xcelium)
	@echo "XCELIUM_HOME = $(XCELIUM_HOME)"
	@echo "UVM          = $(XRUN_UVM_HOME)$(if $(wildcard $(XRUN_UVM_HOME)),, -- MISSING)"
	@echo "snapshot dir = $(XRUN_LIB) (coverage: $(XRUN_LIB_COV))"
	@echo "imc          = $(IMC)$(if $(shell command -v $(IMC) 2>/dev/null),, -- not on PATH; coverage_merge will fail)"
else
	@echo "QUESTA_HOME  = $(QUESTA_HOME)"
endif

.PHONY: sim_info
