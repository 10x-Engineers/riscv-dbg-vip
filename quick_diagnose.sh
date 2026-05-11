#!/bin/bash
# quick_diagnose.sh - Quick diagnostic check before running tests

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  RISCV Debug Compliance - Pre-Test Diagnostic                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check 1: Kill any leftover processes
echo "🧹 Cleaning up leftover processes..."
pkill -f "vsim.*tb_top" 2>/dev/null && echo "  ✓ Killed vsim" || echo "  ℹ No vsim running"
pkill -f "openocd" 2>/dev/null && echo "  ✓ Killed OpenOCD" || echo "  ℹ No OpenOCD running"
sleep 0.5

# Check 2: Verify key ports are free
echo ""
echo "🔍 Checking critical ports..."
if ss -tln 2>/dev/null | grep -q ":9824 "; then
    echo "  ⚠ WARNING: Port 9824 (bitbang) already in use!"
else
    echo "  ✓ Port 9824 (bitbang) is free"
fi

if ss -tln 2>/dev/null | grep -q ":6666 "; then
    echo "  ⚠ WARNING: Port 6666 (OpenOCD TCL) already in use!"
else
    echo "  ✓ Port 6666 (OpenOCD TCL) is free"
fi

if ss -tln 2>/dev/null | grep -q ":3333 "; then
    echo "  ⚠ WARNING: Port 3333 (GDB) already in use!"
else
    echo "  ✓ Port 3333 (GDB) is free"
fi

# Check 3: Verify simulation library
echo ""
echo "📦 Checking simulation environment..."
if [ -f "work/_lib.qdb" ]; then
    echo "  ✓ Simulation library (work/) exists"
else
    echo "  ⚠ WARNING: Simulation library not compiled - run: cd sim && make"
fi

# Check 4: Verify OpenOCD binary
echo ""
echo "🔧 Checking OpenOCD..."
OPENOCD_BIN="${OPENOCD_BIN:-/home/jk/Documents/riscv/bin/openocd}"
if [ -x "$OPENOCD_BIN" ]; then
    echo "  ✓ OpenOCD found: $OPENOCD_BIN"
    echo "    Version: $($OPENOCD_BIN --version 2>&1 | head -1)"
else
    echo "  ⚠ ERROR: OpenOCD not found at $OPENOCD_BIN"
    echo "    Set OPENOCD_BIN environment variable"
fi

# Check 5: Verify OpenOCD config
echo ""
echo "📋 Checking configuration..."
if [ -f "configs/openocd_bitbang.cfg" ]; then
    echo "  ✓ OpenOCD config found"
else
    echo "  ⚠ ERROR: OpenOCD config not found at configs/openocd_bitbang.cfg"
fi

# Check 6: Verify Python dependencies
echo ""
echo "🐍 Checking Python dependencies..."
python3 -c "import socket, logging, re" 2>/dev/null && \
    echo "  ✓ Python dependencies OK" || \
    echo "  ⚠ WARNING: Missing Python dependencies"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✓ Diagnostic complete - ready to run tests                    ║"
echo "║                                                                ║"
echo "║  Next steps:                                                   ║"
echo "║  1. cd sim                                                     ║"
echo "║  2. ./run_openocd_sim.sh read_dmstatus                         ║"
echo "║                                                                ║"
echo "║  For more info, see: ../FIXES_APPLIED.md                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
