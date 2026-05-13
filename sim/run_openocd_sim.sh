#!/bin/bash
SCENARIO="${1:-read_dmstatus}"
OPENOCD_BIN="/home/jk/Documents/riscv/bin/openocd"  
OPENOCD_CFG="../configs/openocd_bitbang.cfg"
BB_PORT=9824
TCL_PORT=6666

VSIM_PID=""
OPENOCD_PID=""

cleanup() {
    echo "Cleaning up..."
    [ -n "$VSIM_PID" ] && kill $VSIM_PID 2>/dev/null
    [ -n "$OPENOCD_PID" ] && kill $OPENOCD_PID 2>/dev/null
}
trap cleanup EXIT

echo "Starting vsim..."
vsim -c -do "run -all; quit -f" -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top +UVM_TESTNAME=debug_test "+PYTHON_SEQ=unused" +JTAG_MASTER=openocd +UVM_VERBOSITY=UVM_MEDIUM > vsim.log 2>&1 &
VSIM_PID=$!

# Double-check
pgrep -l vsim

# Or
ps aux | grep -E "vsim|questa" | grep -v grep
ps aux | grep vsim

echo "Waiting for bitbang..."
for i in {1..30}; do ss -tln 2>/dev/null | grep -q ":9824 " && break; sleep 1; done

echo "Starting OpenOCD..."
$OPENOCD_BIN -f "$OPENOCD_CFG" > openocd.log 2>&1 &
OPENOCD_PID=$!

echo "Waiting for OpenOCD..."
for i in {1..60}; do ss -tln 2>/dev/null | grep -q ":6666 " && break; sleep 1; done
sleep 2

# Double-check
pgrep -l vsim

# Or
ps aux | grep -E "vsim|questa" | grep -v grep
ps aux | grep vsim

echo "Running test..."
python3 -u ../lib/python/run.py --transport openocd --scenario "$SCENARIO" --mode batch --log-level DEBUG
exit $?
