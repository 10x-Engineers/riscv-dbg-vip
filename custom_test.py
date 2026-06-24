#!/usr/bin/env python3
from lib.python.rv_dbg_python_api import OpenOCDTransport, RISCVDebug

print("Connecting to OpenOCD TCL port...")
# Connect to the running OpenOCD server
with OpenOCDTransport(host="127.0.0.1", port=6666) as transport:
    dm = RISCVDebug(transport)
    
    print("Activating Debug Module...")
    dm.activate()
    
    print("Halting the core...")
    dm.halt()
    
    # Read the Program Counter
    pc = dm.get_pc()
    print(f"Current PC: {hex(pc)}")
    
    import time
    print("Blinking LEDs from Python...")
    for i in range(10):
        dm.write_mem32(0x8000_0000, 0xF0) # All ON
        time.sleep(0.2)
        dm.write_mem32(0x8000_0000, 0x00) # All OFF
        time.sleep(0.2)
    
    print("Reading back from GPIO...")
    val = dm.read_mem32(0x8000_0000)
    print(f"Read back from GPIO: {hex(val)}")
    
    print("Resuming core...")
    dm.resume()
    
    print("Done!")
