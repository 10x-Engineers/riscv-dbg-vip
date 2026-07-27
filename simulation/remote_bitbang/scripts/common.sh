#!/usr/bin/env bash
# common.sh — shared DUT parameters for the remote_bitbang benchmark scripts.
#
# Sourced, not executed. Every launch script does:
#   source "$(dirname "$0")/common.sh"
#   resolve_dut "$1"
# then uses the DUT_* variables it sets.
#
# Deliberately does NOT duplicate any Questa flags, include paths, or DPI
# library recipes that already live in cva6_sim/Makefile and
# ibex_sim/Makefile — those stay the single source of truth for how to
# *compile* each SoC. This module only adds a new way to *run* an
# already-compiled simulation (see launch_uvm_benchmark.sh /
# launch_rbb_benchmark.sh), the same way `soc_test`/`soc_openocd` already do,
# so it always shells out to `make -C <dut>_sim soc_compile` rather than
# re-deriving the vlog invocation here.

set -euo pipefail

# Root of the pydebug checkout (three levels up from this file).
RBB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RBB_MODULE_DIR="$RBB_ROOT/simulation/remote_bitbang"

resolve_dut() {
    local dut="$1"
    case "$dut" in
        ibex)
            DUT_SIM_DIR="$RBB_ROOT/ibex_sim"
            DUT_TB_TOP="work.tb_top_ibex"
            DUT_OPENOCD_CFG="$DUT_SIM_DIR/configs/openocd_bitbang_ibex.cfg"
            DUT_VSIM_EXTRA_FLAGS=""
            ;;
        cva6)
            DUT_SIM_DIR="$RBB_ROOT/cva6_sim"
            DUT_TB_TOP="work.tb_top_soc"
            DUT_OPENOCD_CFG="$DUT_SIM_DIR/configs/openocd_bitbang_soc.cfg"
            DUT_VSIM_EXTRA_FLAGS="-novopt -suppress 12110"
            ;;
        *)
            echo "error: unknown DUT '$dut' (expected: ibex | cva6)" >&2
            exit 1
            ;;
    esac
    DUT_NAME="$dut"
    DUT_RESULTS_DIR="$RBB_MODULE_DIR/python/results"
    mkdir -p "$DUT_RESULTS_DIR"
}

# Ensure the DUT's `work` library exists before driving vsim directly.
# Skips recompilation if `work/` is already present -- pass --recompile to
# any launch script to force a fresh `make soc_compile` (needed after any
# RTL/SV env change).
ensure_compiled() {
    if [[ ! -d "$DUT_SIM_DIR/work" || "${RBB_FORCE_RECOMPILE:-0}" == "1" ]]; then
        echo "[common.sh] compiling $DUT_NAME (make -C $DUT_SIM_DIR soc_compile)..."
        make -C "$DUT_SIM_DIR" soc_compile
    else
        echo "[common.sh] reusing existing $DUT_SIM_DIR/work (pass --recompile to force a rebuild)"
    fi
}

VSIM_BATCH="${VSIM_BATCH:-env -u DISPLAY vsim -batch}"
