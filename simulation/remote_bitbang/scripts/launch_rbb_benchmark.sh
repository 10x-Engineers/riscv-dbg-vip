#!/usr/bin/env bash
# launch_rbb_benchmark.sh — run the transport benchmark over OpenOCD +
# Remote Bit-Bang (RBB), the simulation-only path this module is dedicated
# to (see documentation/architecture.md).
#
# Two processes, started in sequence, mirroring `soc_openocd` in
# cva6_sim/Makefile / ibex_sim/Makefile exactly:
#   1. vsim, compiled with `+JTAG_MASTER=openocd`, which runs ONLY the RBB
#      DPI server (jtag_bitbang.sv) -- no Python is launched from inside the
#      simulator in this mode.
#   2. python/run_benchmark.py --mode openocd, which spawns `openocd`
#      itself pointed at the DUT's RBB config, waits for JTAG examination,
#      then drives the identical benchmark body over OpenOCD's TCL port.
#
# Usage:
#   ./launch_rbb_benchmark.sh <ibex|cva6> [iterations] [--recompile]
#
# Output: python/results/<dut>_openocd.json

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

DUT="${1:?usage: launch_rbb_benchmark.sh <ibex|cva6> [iterations] [--recompile]}"
ITERATIONS="${2:-20}"
[[ "${3:-}" == "--recompile" || "${ITERATIONS}" == "--recompile" ]] && RBB_FORCE_RECOMPILE=1
[[ "${ITERATIONS}" == "--recompile" ]] && ITERATIONS=20
export RBB_FORCE_RECOMPILE="${RBB_FORCE_RECOMPILE:-0}"

resolve_dut "$DUT"
ensure_compiled
make -C "$DUT_SIM_DIR" uvm_bridge_soc.so

OUTPUT_JSON="$DUT_RESULTS_DIR/${DUT_NAME}_openocd.json"
ELF="$DUT_SIM_DIR/sw/halt_probe.elf"
if [[ "$DUT_NAME" == "cva6" ]]; then
    ELF_PLUSARGS=(+enable_boot "+elf_file=$ELF")
else
    ELF_PLUSARGS=("+elf_file=$ELF")
fi

SIM_LOG="$DUT_SIM_DIR/rbb_bench_sim.log"
rm -f "$SIM_LOG"

echo "[launch_rbb_benchmark] DUT=$DUT_NAME: starting vsim with RBB server..."
(
    cd "$DUT_SIM_DIR"
    # shellcheck disable=SC2086
    exec $VSIM_BATCH $DUT_VSIM_EXTRA_FLAGS -do "run -all; quit -f" \
        -dpioutoftheblue 1 -sv_lib uvm_bridge_soc "$DUT_TB_TOP" \
        +UVM_TESTNAME=debug_test \
        "+PYTHON_SEQ=unused" \
        +JTAG_MASTER=openocd \
        "${ELF_PLUSARGS[@]}" \
        +UVM_VERBOSITY=UVM_MEDIUM
) > "$SIM_LOG" 2>&1 &
SIM_PID=$!
trap 'kill "$SIM_PID" 2>/dev/null || true' EXIT

echo "[launch_rbb_benchmark] waiting for RBB server on port 9824..."
for i in $(seq 1 60); do
    if grep -q "Listening on port 9824" "$SIM_LOG" 2>/dev/null; then
        echo "[launch_rbb_benchmark] RBB server ready"
        break
    fi
    if ! kill -0 "$SIM_PID" 2>/dev/null; then
        echo "[launch_rbb_benchmark] ERROR: vsim exited before RBB server came up -- see $SIM_LOG" >&2
        exit 1
    fi
    if [[ "$i" -eq 60 ]]; then
        echo "[launch_rbb_benchmark] ERROR: timed out waiting for RBB server -- see $SIM_LOG" >&2
        exit 1
    fi
    sleep 1
done

echo "[launch_rbb_benchmark] launching OpenOCD + benchmark (iterations=$ITERATIONS)..."
python3 "$RBB_MODULE_DIR/python/run_benchmark.py" \
    --mode openocd \
    --iterations "$ITERATIONS" \
    --openocd-config "$DUT_OPENOCD_CFG" \
    --output "$OUTPUT_JSON"

echo "[launch_rbb_benchmark] done: $OUTPUT_JSON"
