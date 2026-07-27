#!/usr/bin/env bash
# launch_uvm_benchmark.sh — run the transport benchmark over PyDebug's direct
# UVM-socket path (no OpenOCD, no bit-banging).
#
# This is the "PyDebug" side of the PyDebug-vs-OpenOCD+RBB comparison: the
# Python benchmark body (python/run_benchmark.py --mode uvm) is launched BY
# the simulator itself, the same way `rv_dbg_base_test.sv` launches every
# other PYTHON_SEQ (see cva6_sim/Makefile's / ibex_sim/Makefile's `soc_test`
# target, which this mirrors) -- it connects over a Unix domain socket to the
# C DPI bridge (`uvm_bridge.c`) compiled into the simulator, one process hop,
# no TCP, no JTAG bit-banging.
#
# Usage:
#   ./launch_uvm_benchmark.sh <ibex|cva6> [iterations] [--recompile]
#
# Output: python/results/<dut>_uvm.json

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

DUT="${1:?usage: launch_uvm_benchmark.sh <ibex|cva6> [iterations] [--recompile]}"
ITERATIONS="${2:-20}"
[[ "${3:-}" == "--recompile" || "${ITERATIONS}" == "--recompile" ]] && RBB_FORCE_RECOMPILE=1
[[ "${ITERATIONS}" == "--recompile" ]] && ITERATIONS=20
export RBB_FORCE_RECOMPILE="${RBB_FORCE_RECOMPILE:-0}"

resolve_dut "$DUT"
ensure_compiled
make -C "$DUT_SIM_DIR" uvm_bridge_soc.so   # cheap: real file-based staleness check

OUTPUT_JSON="$DUT_RESULTS_DIR/${DUT_NAME}_uvm.json"
ELF="$DUT_SIM_DIR/sw/halt_probe.elf"
if [[ "$DUT_NAME" == "cva6" ]]; then
    ELF_PLUSARGS=(+enable_boot "+elf_file=$ELF")
else
    ELF_PLUSARGS=("+elf_file=$ELF")
fi

PYTHON_SEQ="$RBB_MODULE_DIR/python/run_benchmark.py --mode uvm --iterations $ITERATIONS --output $OUTPUT_JSON"

echo "[launch_uvm_benchmark] DUT=$DUT_NAME iterations=$ITERATIONS -> $OUTPUT_JSON"
cd "$DUT_SIM_DIR"
# shellcheck disable=SC2086
$VSIM_BATCH $DUT_VSIM_EXTRA_FLAGS -do "run -all; quit -f" \
    -dpioutoftheblue 1 -sv_lib uvm_bridge_soc "$DUT_TB_TOP" \
    +UVM_TESTNAME=debug_test \
    +PYTHON_SEQ="$PYTHON_SEQ" \
    "${ELF_PLUSARGS[@]}" \
    +UVM_VERBOSITY=UVM_MEDIUM

if [[ -f "$OUTPUT_JSON" ]]; then
    echo "[launch_uvm_benchmark] done: $OUTPUT_JSON"
else
    echo "[launch_uvm_benchmark] ERROR: $OUTPUT_JSON was not produced -- check the vsim log above" >&2
    exit 1
fi
