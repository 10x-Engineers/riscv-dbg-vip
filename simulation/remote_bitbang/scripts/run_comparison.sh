#!/usr/bin/env bash
# run_comparison.sh — full PyDebug-vs-OpenOCD+RBB benchmark + report, one DUT.
#
# Runs both launch_uvm_benchmark.sh and launch_rbb_benchmark.sh back-to-back
# on the same machine (so both share whatever load/noise is present at run
# time), then feeds both JSON results into compare_transports.py to produce
# documentation/performance_comparison_<dut>.md + a latency chart under
# documentation/figures/.
#
# Usage:
#   ./run_comparison.sh <ibex|cva6> [iterations] [--recompile]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

DUT="${1:?usage: run_comparison.sh <ibex|cva6> [iterations] [--recompile]}"
ITERATIONS="${2:-20}"
RECOMPILE_FLAG="${3:-}"

"$SCRIPT_DIR/launch_uvm_benchmark.sh" "$DUT" "$ITERATIONS" "$RECOMPILE_FLAG"
"$SCRIPT_DIR/launch_rbb_benchmark.sh" "$DUT" "$ITERATIONS"

resolve_dut "$DUT"
python3 "$RBB_MODULE_DIR/python/compare_transports.py" \
    --uvm "$DUT_RESULTS_DIR/${DUT_NAME}_uvm.json" \
    --openocd "$DUT_RESULTS_DIR/${DUT_NAME}_openocd.json" \
    --dut "$DUT_NAME" \
    --out-md "$RBB_MODULE_DIR/documentation/performance_comparison_${DUT_NAME}.md" \
    --out-svg-dir "$RBB_MODULE_DIR/documentation/figures"

echo "[run_comparison] report: $RBB_MODULE_DIR/documentation/performance_comparison_${DUT_NAME}.md"
