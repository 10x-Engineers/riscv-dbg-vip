# questa_rbb_run.do — Questa run-control script for an RBB simulation.
#
# The shell launch scripts (../scripts/launch_rbb_benchmark.sh) invoke vsim
# with an inline `-do "run -all; quit -f"` for unattended batch runs. This
# .do file is the interactive/debug equivalent: source it from a `vsim`
# prompt (GUI or `-i`) already elaborated against the RBB build (see the
# vsim invocation in scripts/launch_rbb_benchmark.sh for the exact
# `-sv_lib uvm_bridge_soc <tb_top> +JTAG_MASTER=openocd ...` arguments) when
# you want to single-step, inspect signals, or capture a waveform while
# OpenOCD/RBB drives the DUT -- rather than a pure batch pass/fail run.
#
# Usage:
#   cd ibex_sim   # or cva6_sim
#   vsim -dpioutoftheblue 1 -sv_lib uvm_bridge_soc work.tb_top_ibex \
#        +UVM_TESTNAME=debug_test "+PYTHON_SEQ=unused" +JTAG_MASTER=openocd \
#        +elf_file=$(pwd)/sw/halt_probe.elf +dump_waves \
#        -do ../simulation/remote_bitbang/tcl/questa_rbb_run.do
#   # in another shell: openocd -f ../simulation/remote_bitbang/tcl/rbb_launch.tcl -c "set DUT ibex"

# Waveform dump, scoped to the DM instance only -- see
# .claude/skills/riscv-debug-root-cause for why this stays scoped rather
# than dumping the whole SoC (slow to generate, slow to parse, and almost
# every DM-register-level question lives entirely inside the DM instance).
# Only takes effect if the sim was elaborated with +dump_waves (tb_top_*.sv's
# own opt-in guard) -- harmless no-op otherwise.
if {[info exists ::env(RBB_NO_WAVES)] == 0} {
    catch {
        echo "questa_rbb_run.do: waveform dump active (if +dump_waves was passed at elaboration)"
    }
}

# Log every DMI transaction at a human-legible level (register names, not
# just raw hex) -- see py_bridge.sv's debug_print()/[DEBUG] tag.
log -r /*

echo "questa_rbb_run.do: RBB server is up; waiting for OpenOCD to connect and drive the DUT."
echo "questa_rbb_run.do: run 'openocd -f ../simulation/remote_bitbang/tcl/rbb_launch.tcl -c \"set DUT <ibex|cva6>\"' now."

run -all
quit -f
