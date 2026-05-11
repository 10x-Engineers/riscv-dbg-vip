# RISCV Debug Compliance - OpenOCD Integration Fixes

## Problem Summary
The OpenOCD + simulation integration was failing with:
- **Timeout errors**: `TimeoutError: timed out` in OpenOCD transport
- **Broken pipe errors**: `Connection reset by peer` and `Broken pipe`
- **Socket errors**: `couldn't bind gdb to socket on port 3333: Address already in use`
- **Root cause**: Simulation finished at 100ms before OpenOCD could complete JTAG communication

## Root Causes Identified

### 1. Simulation Timeout Too Short (100ms)
- **File**: `tb/tb_top.sv`
- **Issue**: UVM watchdog set to 100ms for OpenOCD scenario
- **Why critical**: OpenOCD needs time to:
  - Initialize remote bitbang server
  - Connect to the simulation
  - Negotiate JTAG handshake
  - Execute read/write transactions
  - All of this easily takes 5-30 seconds with bitbang

### 2. Python Socket Timeout (10s)
- **File**: `debug_lib/openocd_transport.py`
- **Issue**: OpenOCD transport socket timeout set to 10 seconds
- **Problem**: With slow bitbang communication, responses can take 5-15 seconds per transaction
- **Race condition**: Simulation dies at 100ms while Python waits 10 seconds

### 3. No Graceful Simulation Shutdown
- **File**: `tb/tb_top.sv`
- **Issue**: Simulation used hard watchdog timeout instead of waiting for bb_quit signal
- **Problem**: Simulation could end mid-transaction, leaving sockets in broken state

### 4. Process Cleanup Issues
- **File**: `sim/run_openocd_sim.sh`
- **Issue**: Leftover OpenOCD/vsim processes from failed runs held ports 3333 and 6666
- **Problem**: Subsequent runs failed immediately with "Address already in use"

### 5. Poor Error Handling in Run Script
- **File**: `sim/run_openocd_sim.sh`
- **Issue**: Script didn't verify processes started successfully
- **Problem**: Silent failures made debugging difficult

## Fixes Applied

### Fix 1: Extended Simulation Timeout (tb/tb_top.sv)
```systemverilog
// BEFORE: 100ms for OpenOCD (too short!)
initial begin
    if (jtag_use_openocd)
        #100_000_000;  // 100 ms
    else
        #10_000_000;   // 10 ms
    `uvm_fatal("TIMEOUT", "Simulation watchdog expired")
end

// AFTER: 60 seconds for OpenOCD
initial begin
    if (jtag_use_openocd)
        #60_000_000_000;  // 60 seconds (plenty of time for JTAG scans)
    else
        #10_000_000;   // 10 ms for UVM
    `uvm_fatal("TIMEOUT", "Simulation watchdog expired")
end
```

**Impact**: Simulation now runs long enough for OpenOCD transactions to complete.

### Fix 2: Wait for Bitbang Quit Signal (tb/tb_top.sv)
```systemverilog
// NEW: Gracefully exit when Python finishes
initial begin
    if (jtag_use_openocd) begin
        @(posedge bb_quit);  // Wait for OpenOCD remote_bitbang to signal done
        uvm_config_db #(int)::set(null, "*", "bb_quit", 1);
        #1_000_000;  // 1 ms for Python cleanup
        $finish;     // Clean simulation exit
    end
end
```

**Impact**: 
- Prevents mid-transaction simulation termination
- Signals Python when to shut down gracefully
- Prevents socket corruption

### Fix 3: Increased OpenOCD Socket Timeout (debug_lib/openocd_transport.py)
```python
# BEFORE
OPENOCD_TIMEOUT = 10.0

# AFTER
OPENOCD_TIMEOUT = 30.0  # Increased to allow slow bitbang simulation communication
```

**Impact**: Allows Python to wait for slow bitbang responses without timing out.

### Fix 4: Robust Cleanup & Error Handling (sim/run_openocd_sim.sh)

**Pre-cleanup**:
```bash
# Kill any lingering processes from previous runs
pkill -f "vsim.*tb_top" 2>/dev/null || true
pkill -f "openocd" 2>/dev/null || true
sleep 0.5
```

**Better startup verification**:
```bash
# Wait for bitbang server with error checking
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
    if ss -tln 2>/dev/null | grep -q ":$BB_PORT "; then
        echo "Bitbang server ready on port $BB_PORT."
        break
    fi
    if ! kill -0 $VSIM_PID 2>/dev/null; then
        echo "ERROR: vsim exited prematurely. Check simulation for errors."
        exit 1  # Fail fast if process dies
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo "ERROR: Bitbang server failed to start after ${MAX_WAIT}s"
        exit 1
    fi
    sleep 1
done
```

**Impact**:
- Cleans up leftover processes that would block ports
- Verifies each component starts successfully
- Clear error messages when things fail
- Prevents cascading failures

## Testing the Fixes

### 1. Quick verification of changes:
```bash
cd pydebug/sim
# Check changes are in place
grep "60_000_000_000" ../tb/tb_top.sv
grep "OPENOCD_TIMEOUT = 30.0" ../debug_lib/openocd_transport.py
grep "pkill.*vsim" run_openocd_sim.sh
```

### 2. Run the test with improved diagnostics:
```bash
cd pydebug/sim
chmod +x run_openocd_sim.sh
./run_openocd_sim.sh read_dmstatus 2>&1 | tee test_output.log
```

Expected behavior:
1. Pre-cleanup kills any leftover processes
2. Bitbang server starts on port 9824 (~1-5 seconds)
3. OpenOCD starts and connects to bitbang (~2-5 seconds)
4. Python test executes JTAG commands (~5-15 seconds)
5. Clean shutdown with no errors
6. Total runtime: typically 15-40 seconds depending on simulation speed

### 3. Success indicators:
- No "Address already in use" errors
- No timeout errors from Python
- OpenOCD completes DMSTATUS read successfully
- All processes terminate cleanly
- Exit code 0 (success)

## Performance Expectations

With these fixes:
- **Bitbang server startup**: 1-2 seconds
- **OpenOCD initialization**: 2-5 seconds  
- **Per JTAG transaction**: 1-3 seconds (depending on scan complexity)
- **Total test time**: 15-40 seconds for simple tests

Note: Bitbang is inherently slow (socket-based JTAG over TCP). For faster tests, use UVMTransport directly. For real hardware, use native OpenOCD with actual JTAG adapters.

## Future Improvements

1. **Configurable timeouts**: Make simulation timeout a parameter
2. **Heartbeat mechanism**: Add periodic keep-alive messages
3. **Progress reporting**: Real-time status in run script
4. **Parallel test execution**: Multiple tests without restart
5. **Timeout warnings**: Alert when near watchdog limit

## Files Modified

1. **tb/tb_top.sv**
   - Line ~240-260: Updated watchdog timeout and bb_quit handling

2. **debug_lib/openocd_transport.py**
   - Line ~31: Updated OPENOCD_TIMEOUT constant

3. **sim/run_openocd_sim.sh**
   - Lines throughout: Added pre-cleanup, error checking, improved timing

## References

- RISC-V Debug Specification: Remote Bitbang protocol
- OpenOCD Documentation: TCL server and bitbang mode
- UVM 1.1 Specification: Simulation timeout handling
