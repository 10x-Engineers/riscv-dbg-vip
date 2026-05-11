#!/bin/bash
set -e

echo "Step 1: Pre-cleanup"
pkill -f "vsim.*tb_top" 2>/dev/null || true
pkill -f "openocd" 2>/dev/null || true
sleep 0.5

echo "Step 2: Starting vsim"
VSIM_PID=""
vsim -c -do "run -all; quit -f" \
     -dpioutoftheblue 1 -sv_lib uvm_bridge work.tb_top \
     +UVM_TESTNAME=debug_test \
     "+PYTHON_SEQ=unused" \
     +JTAG_MASTER=openocd \
     +UVM_VERBOSITY=UVM_MEDIUM &
VSIM_PID=$!

echo "vsim PID: $VSIM_PID"
echo "Step 3: Waiting for bitbang"
sleep 2

echo "Step 4: Checking if vsim is still running"
if kill -0 $VSIM_PID 2>/dev/null; then
    echo "vsim is running"
    kill $VSIM_PID
else
    echo "vsim exited"
fi
