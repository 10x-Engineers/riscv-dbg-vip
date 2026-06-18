#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# fpga.sh — Ibex Demo System FPGA Automation Script
#
# End-to-end automation for the Arty A7-100T:
#   build-sw   → Cross-compile ibex demo software (cmake + make)
#   synth      → Synthesize FPGA bitstream (FuseSoC + Vivado)
#   program    → Program the FPGA with the bitstream
#   load       → Load an ELF onto the running FPGA via OpenOCD
#   debug      → Run a pydebug scenario against the FPGA
#   uart       → Open UART serial console
#   check      → Verify all required tools are installed
#   all        → Full pipeline: build-sw → synth → program → load → debug
#
# Usage:
#   ./fpga.sh check
#   ./fpga.sh build-sw
#   ./fpga.sh synth
#   ./fpga.sh program
#   ./fpga.sh load ./my_test.elf [run|halt]
#   ./fpga.sh debug [scenario] [elf_file]
#   ./fpga.sh uart
#   ./fpga.sh all ./my_test.elf
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Resolve project root (directory containing this script) ──────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYDEBUG_ROOT="$SCRIPT_DIR"
IBEX_DIR="$PYDEBUG_ROOT/ibex-demo-system"
CONFIGS_DIR="$PYDEBUG_ROOT/configs"
PYTHON_DIR="$PYDEBUG_ROOT/lib/python"

# ── Configurable paths (override via environment) ────────────────────────────
VIVADO_SETTINGS="${VIVADO_SETTINGS:-/tools/Xilinx/Vivado/2022.2/settings64.sh}"
OPENOCD_BIN="${OPENOCD_BIN:-openocd}"
OPENOCD_CFG="${OPENOCD_CFG:-$CONFIGS_DIR/openocd_arty_a7_100t.cfg}"
RISCV32_PREFIX="${RISCV32_PREFIX:-riscv32-unknown-elf-}"
UART_DEV="${UART_DEV:-/dev/ttyUSB1}"
UART_BAUD="${UART_BAUD:-115200}"

# ── FPGA target constants ────────────────────────────────────────────────────
FPGA_PART="xc7a100tcsg324-1"
JTAG_IDCODE="0x13631093"  # Arty A7-100T
FUSESOC_TARGET="synth"
BITSTREAM_PATH="$IBEX_DIR/build/lowrisc_ibex_demo_system_0/synth-vivado/lowrisc_ibex_demo_system_0.bit"
SW_BUILD_DIR="$IBEX_DIR/sw/c/build"
LOAD_SCRIPT="$IBEX_DIR/util/load_demo_system.sh"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "${RED}❌${NC} $*" >&2; }
header(){ echo -e "\n${BOLD}═══ $* ═══${NC}"; }

# ══════════════════════════════════════════════════════════════════════════════
# check — Verify all required tools
# ══════════════════════════════════════════════════════════════════════════════
cmd_check() {
    header "Checking Prerequisites"
    local all_ok=true

    # Required tools
    local -A tools=(
        ["${RISCV32_PREFIX}gcc"]="RISC-V RV32 GCC (cross-compiler)"
        ["cmake"]="CMake (build system)"
        ["python3"]="Python 3"
        ["$OPENOCD_BIN"]="OpenOCD (JTAG debug bridge)"
    )

    for cmd in "${!tools[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            ok "${tools[$cmd]}: $(command -v "$cmd")"
        else
            err "${tools[$cmd]}: NOT FOUND ($cmd)"
            all_ok=false
        fi
    done

    # Optional tools
    if command -v fusesoc &>/dev/null; then
        ok "FuseSoC: $(command -v fusesoc)"
    else
        warn "FuseSoC: not found (needed for 'synth' command — install with: pip install fusesoc)"
    fi

    if command -v vivado &>/dev/null; then
        ok "Vivado: $(command -v vivado)"
    elif [[ -f "$VIVADO_SETTINGS" ]]; then
        warn "Vivado: not in PATH but settings found at $VIVADO_SETTINGS"
        info "  → Run: source $VIVADO_SETTINGS"
    else
        warn "Vivado: not found (needed for 'synth' and 'program' commands)"
    fi

    if command -v screen &>/dev/null; then
        ok "screen: $(command -v screen)"
    else
        warn "screen: not found (needed for 'uart' command)"
    fi

    # Check ibex-demo-system submodule
    if [[ -f "$IBEX_DIR/ibex_demo_system.core" ]]; then
        ok "ibex-demo-system submodule: present"
    else
        err "ibex-demo-system submodule: NOT FOUND at $IBEX_DIR"
        all_ok=false
    fi

    # Check OpenOCD config
    if [[ -f "$OPENOCD_CFG" ]]; then
        ok "OpenOCD config: $OPENOCD_CFG"
        if grep -q "$JTAG_IDCODE" "$OPENOCD_CFG"; then
            ok "  JTAG IDCODE: $JTAG_IDCODE (A7-100T) ✓"
        else
            warn "  JTAG IDCODE mismatch — expected $JTAG_IDCODE for A7-100T"
        fi
    else
        err "OpenOCD config not found: $OPENOCD_CFG"
        all_ok=false
    fi

    # Check UART device
    if [[ -e "$UART_DEV" ]]; then
        ok "UART device: $UART_DEV"
    else
        warn "UART device $UART_DEV not found (board may not be connected)"
    fi

    echo ""
    if $all_ok; then
        ok "All required tools present"
    else
        err "Some required tools are missing — see above"
        return 1
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# build-sw — Cross-compile the ibex demo software
# ══════════════════════════════════════════════════════════════════════════════
cmd_build_sw() {
    header "Building Ibex Demo Software"
    mkdir -p "$SW_BUILD_DIR"
    info "Running cmake..."
    (cd "$SW_BUILD_DIR" && cmake ..)
    info "Running make..."
    (cd "$SW_BUILD_DIR" && make -j"$(nproc)")
    ok "Software build complete"
    info "Binaries at: $SW_BUILD_DIR/demo/"
    echo ""
    info "Available ELFs:"
    find "$SW_BUILD_DIR" -name "*.elf" -o -type f -executable | \
        grep -v CMake | grep -v '.dir' | head -20 || \
    find "$SW_BUILD_DIR/demo" -mindepth 2 -maxdepth 2 -type f ! -name "*.o" ! -name "*.d" 2>/dev/null | head -20
}

# ══════════════════════════════════════════════════════════════════════════════
# synth — Synthesize FPGA bitstream
# ══════════════════════════════════════════════════════════════════════════════
cmd_synth() {
    header "Synthesizing FPGA Bitstream (target: $FPGA_PART)"

    # Source Vivado if not already in PATH
    if ! command -v vivado &>/dev/null; then
        if [[ -f "$VIVADO_SETTINGS" ]]; then
            info "Sourcing Vivado: $VIVADO_SETTINGS"
            source "$VIVADO_SETTINGS"
        else
            err "Vivado not found. Set VIVADO_SETTINGS or add vivado to PATH."
            return 1
        fi
    fi

    if ! command -v fusesoc &>/dev/null; then
        err "FuseSoC not found. Install with: pip install fusesoc"
        return 1
    fi

    # Ensure SW is built (bitstream embeds blank.vmem)
    if [[ ! -f "$SW_BUILD_DIR/blank/blank.vmem" ]]; then
        warn "blank.vmem not found — building software first..."
        cmd_build_sw
    fi

    info "Starting FuseSoC synthesis (this may take 15–30 minutes)..."
    (cd "$IBEX_DIR" && fusesoc --cores-root=. run \
        --target="$FUSESOC_TARGET" --setup --build \
        lowrisc:ibex:demo_system)

    if [[ -f "$BITSTREAM_PATH" ]]; then
        ok "Bitstream generated: $BITSTREAM_PATH"
        ls -lh "$BITSTREAM_PATH"
    else
        err "Bitstream not found at expected path: $BITSTREAM_PATH"
        return 1
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# program — Program the FPGA
# ══════════════════════════════════════════════════════════════════════════════
cmd_program() {
    header "Programming FPGA"

    if [[ ! -f "$BITSTREAM_PATH" ]]; then
        err "No bitstream found. Run './fpga.sh synth' first."
        return 1
    fi

    # Try openFPGALoader first (fastest)
    if command -v openFPGALoader &>/dev/null; then
        info "Using openFPGALoader..."
        openFPGALoader -b arty_a7_100t "$BITSTREAM_PATH"
        ok "FPGA programmed via openFPGALoader"
        return 0
    fi

    # Fall back to FuseSoC/Vivado
    if ! command -v vivado &>/dev/null; then
        if [[ -f "$VIVADO_SETTINGS" ]]; then
            source "$VIVADO_SETTINGS"
        else
            err "Neither openFPGALoader nor Vivado found."
            return 1
        fi
    fi

    info "Using Vivado programmer..."
    (cd "$IBEX_DIR" && fusesoc --cores-root=. run \
        --target="$FUSESOC_TARGET" --run \
        lowrisc:ibex:demo_system) || \
    (cd "$IBEX_DIR/build/lowrisc_ibex_demo_system_0/synth-vivado/" && make pgm)

    ok "FPGA programmed via Vivado"
}

# ══════════════════════════════════════════════════════════════════════════════
# load — Load an ELF binary onto the FPGA via OpenOCD
# ══════════════════════════════════════════════════════════════════════════════
cmd_load() {
    local elf_file="${1:-}"
    local mode="${2:-halt}"  # 'run' or 'halt'

    if [[ -z "$elf_file" ]]; then
        # Default to hello_world demo
        elf_file="$SW_BUILD_DIR/demo/hello_world/demo"
        warn "No ELF specified, using default: $elf_file"
    fi

    # Resolve relative path
    if [[ ! "$elf_file" = /* ]]; then
        elf_file="$(pwd)/$elf_file"
    fi

    if [[ ! -f "$elf_file" ]]; then
        err "ELF file not found: $elf_file"
        return 1
    fi

    header "Loading ELF onto FPGA (mode: $mode)"
    info "ELF: $elf_file"

    if [[ -x "$LOAD_SCRIPT" ]]; then
        # Use the ibex-demo-system's built-in loader
        # It needs a TCL config that does init+halt
        "$LOAD_SCRIPT" "$mode" "$elf_file" "$OPENOCD_CFG"
    else
        # Manual OpenOCD load
        local exit_cmd=""
        [[ "$mode" == "run" ]] && exit_cmd='-c "exit"'

        $OPENOCD_BIN -f "$OPENOCD_CFG" \
            -c "load_image $elf_file 0x0" \
            -c "verify_image $elf_file 0x0" \
            -c "echo \"Reset $mode\"" \
            -c "reset $mode" \
            $exit_cmd
    fi

    ok "ELF loaded and core is ${mode}ed"
}

# ══════════════════════════════════════════════════════════════════════════════
# debug — Run a pydebug scenario against the hardware
# ══════════════════════════════════════════════════════════════════════════════
cmd_debug() {
    local scenario="${1:-halt}"
    local elf_file="${2:-}"
    local config="${3:-}"
    local log_level="${LOG_LEVEL:-INFO}"

    header "Running pydebug Debug Scenario: $scenario"

    # Pick the right JSON config
    if [[ -z "$config" ]]; then
        local hw_config="$CONFIGS_DIR/halt_hw.json"
        if [[ -f "$hw_config" ]]; then
            config="$hw_config"
        else
            err "No config found. Create $hw_config or pass --config."
            return 1
        fi
    fi

    # If an ELF is provided, load it first (halted)
    if [[ -n "$elf_file" ]]; then
        info "Loading ELF before debug: $elf_file"
        cmd_load "$elf_file" halt
        # Give OpenOCD a moment to settle, then kill it
        # (pydebug will spawn its own OpenOCD)
        sleep 1
        pkill -f "openocd.*arty" 2>/dev/null || true
        sleep 0.5
    fi

    info "Config: $config"
    info "Scenario: $scenario"
    info "Log level: $log_level"

    python3 "$PYTHON_DIR/run.py" \
        --config "$config" \
        --scenario "$scenario" \
        --transport openocd \
        --log-level "$log_level"
}

# ══════════════════════════════════════════════════════════════════════════════
# uart — Open UART serial console
# ══════════════════════════════════════════════════════════════════════════════
cmd_uart() {
    header "Opening UART Console"

    if [[ ! -e "$UART_DEV" ]]; then
        err "UART device not found: $UART_DEV"
        info "Available ttyUSB devices:"
        ls -la /dev/ttyUSB* 2>/dev/null || echo "  (none)"
        info "Set UART_DEV=/dev/ttyUSBx to override"
        return 1
    fi

    info "Device: $UART_DEV @ ${UART_BAUD} baud"
    info "Exit: Ctrl-A then K, then Y"
    echo ""
    screen "$UART_DEV" "$UART_BAUD"
}

# ══════════════════════════════════════════════════════════════════════════════
# all — Full pipeline
# ══════════════════════════════════════════════════════════════════════════════
cmd_all() {
    local elf_file="${1:-}"

    header "Full FPGA Pipeline"
    cmd_check
    cmd_build_sw
    cmd_synth
    cmd_program

    if [[ -n "$elf_file" ]]; then
        cmd_load "$elf_file" halt
        # Kill the OpenOCD from load before debug spawns its own
        sleep 1
        pkill -f "openocd.*arty" 2>/dev/null || true
        sleep 0.5
        cmd_debug halt "$elf_file"
    else
        info "No ELF specified — FPGA programmed with default blank.vmem"
        info "Next: ./fpga.sh load ./my_test.elf"
    fi

    ok "Pipeline complete!"
}

# ══════════════════════════════════════════════════════════════════════════════
# Main dispatcher
# ══════════════════════════════════════════════════════════════════════════════
usage() {
    cat <<'EOF'
Usage: ./fpga.sh <command> [args...]

Commands:
  check                      Verify all tools are installed
  build-sw                   Cross-compile ibex demo software
  synth                      Synthesize FPGA bitstream (~20 min)
  program                    Program FPGA with bitstream
  load <elf> [run|halt]      Load ELF onto FPGA via OpenOCD
  debug [scenario] [elf]     Run pydebug scenario (halt|read_dmstatus|mem_scan)
  uart                       Open UART serial console
  all [elf]                  Full pipeline: build → synth → program → load → debug

Environment variables:
  VIVADO_SETTINGS   Path to Vivado settings64.sh
  OPENOCD_BIN       Path to OpenOCD binary
  OPENOCD_CFG       Path to OpenOCD TCL config
  RISCV32_PREFIX    Cross-compiler prefix (default: riscv32-unknown-elf-)
  UART_DEV          UART device (default: /dev/ttyUSB1)
  LOG_LEVEL         Python log level (default: INFO)

Examples:
  ./fpga.sh check
  ./fpga.sh build-sw
  ./fpga.sh synth
  ./fpga.sh program
  ./fpga.sh load ./sw/c/build/demo/hello_world/demo run
  ./fpga.sh load ./my_test.elf halt
  ./fpga.sh debug halt
  ./fpga.sh debug halt ./my_test.elf
  ./fpga.sh uart
  ./fpga.sh all ./my_test.elf
EOF
}

case "${1:-}" in
    check)     cmd_check ;;
    build-sw)  cmd_build_sw ;;
    synth)     cmd_synth ;;
    program)   cmd_program ;;
    load)      shift; cmd_load "$@" ;;
    debug)     shift; cmd_debug "$@" ;;
    uart)      cmd_uart ;;
    all)       shift; cmd_all "$@" ;;
    -h|--help|help) usage ;;
    *)
        if [[ -n "${1:-}" ]]; then
            err "Unknown command: $1"
        fi
        usage
        exit 1
        ;;
esac
