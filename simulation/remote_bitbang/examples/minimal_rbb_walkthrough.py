#!/usr/bin/env python3
"""
minimal_rbb_walkthrough.py — the smallest possible RBB example.

Not the benchmark harness (see python/run_benchmark.py for that) -- this is
a plain walkthrough for someone reading the code to understand the RBB path,
with no timing/statistics logic in the way. Same three lines of setup as
UVMTransport would need; only the transport class differs (that's the whole
point of `pydebug.api`'s DebugTransport abstraction -- see
src/pydebug/api/transport.py).

Precondition: a Questa simulation compiled with `+JTAG_MASTER=openocd` is
already running and its RBB server is listening on port 9824. Easiest way
to get there:

    ../scripts/launch_rbb_benchmark.sh ibex 1   # spins one up, runs a
                                                 # 1-iteration benchmark,
                                                 # then tears down -- kill it
                                                 # after "RBB server ready"
                                                 # prints and run this
                                                 # script instead, or adapt
                                                 # the script to skip the
                                                 # benchmark call.

Or, manually, in one terminal:
    cd ../../../ibex_sim && make soc_compile   # once
    vsim -batch -do "run -all; quit -f" -dpioutoftheblue 1 \\
         -sv_lib uvm_bridge_soc work.tb_top_ibex +UVM_TESTNAME=debug_test \\
         "+PYTHON_SEQ=unused" +JTAG_MASTER=openocd \\
         "+elf_file=$(pwd)/sw/halt_probe.elf" +UVM_VERBOSITY=UVM_MEDIUM
and in a second terminal, run this script.
"""

from pydebug.api import OpenOCDTransport, RISCVDebug

OPENOCD_CONFIG = "../../../ibex_sim/configs/openocd_bitbang_ibex.cfg"


def main():
    # OpenOCDTransport expects an OpenOCD instance already running with its
    # TCL port open (tcl_port 6666 in the .cfg above) -- unlike
    # run_benchmark.py, this walkthrough does not spawn openocd itself, to
    # keep the example minimal. Start it yourself first:
    #   openocd -f ../tcl/rbb_launch.tcl -c "set DUT ibex"
    with OpenOCDTransport(host="127.0.0.1", port=6666) as transport:
        dm = RISCVDebug(transport)

        dm.activate()
        print(f"dmstatus = 0x{dm.read_dmstatus():08x}")

        dm.halt()
        print(f"halted, PC = 0x{dm.get_pc():08x}")

        ra = dm.read_gpr(0x1001)  # x1 / ra
        print(f"ra (x1) = 0x{ra:08x}")

        mem_val = dm.read_mem32(0x8000_0000)
        print(f"mem[0x80000000] = 0x{mem_val:08x}")

        dm.resume()
        print(f"running = {dm.is_running()}")


if __name__ == "__main__":
    main()
