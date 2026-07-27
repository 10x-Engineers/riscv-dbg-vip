# rbb_launch.tcl — parameterized OpenOCD launch config for the simulation-only
# Remote Bit-Bang flow.
#
# Replaces having one near-duplicate .cfg file per DUT (the project already
# has ibex_sim/configs/openocd_bitbang_ibex.cfg and
# cva6_sim/configs/openocd_bitbang_soc.cfg, which differ only in the JTAG
# IDCODE they expect) with a single script driven by `-c "set DUT ..."`.
# Those two per-DUT files remain the canonical, tested launch path used by
# scripts/launch_rbb_benchmark.sh — this script is the tcl/-folder,
# hand-invokable equivalent for interactive use / a third DUT added later.
#
# Usage:
#   openocd -f rbb_launch.tcl -c "set DUT ibex"
#   openocd -f rbb_launch.tcl -c "set DUT cva6"
#   openocd -f rbb_launch.tcl -c "set DUT ibex" -c "set RBB_PORT 9824" -c "set TCL_PORT 6666"
#
# Preconditions (same as the canonical per-DUT .cfg files): a Questa
# simulation compiled with `+JTAG_MASTER=openocd` must already be running
# and its remote-bitbang server listening on RBB_PORT (see
# `jtag_bitbang.sv`'s `rbs_init(PORT)`, default 9824) *before* this is run —
# OpenOCD's remote_bitbang driver does not retry a refused connection.

if {![info exists DUT]} {
    error "rbb_launch.tcl: -c \"set DUT ibex\" (or cva6) is required"
}
if {![info exists RBB_PORT]} { set RBB_PORT 9824 }
if {![info exists TCL_PORT]} { set TCL_PORT 6666 }

# Per-DUT JTAG IDCODE, taken from each SoC's own dmi_jtag instantiation
# (see ibex_sim/configs/openocd_bitbang_ibex.cfg / cva6_sim/configs/
# openocd_bitbang_soc.cfg for where these were confirmed against the RTL).
array set IDCODE {
    ibex 0x11001cdf
    cva6 0x00000001
}
if {![info exists IDCODE($DUT)]} {
    error "rbb_launch.tcl: unknown DUT '$DUT' (expected: ibex | cva6)"
}

adapter driver remote_bitbang
remote_bitbang host localhost
remote_bitbang port $RBB_PORT

# TCL command server -- this is the port pydebug's OpenOCDTransport (and
# tcl/rbb_control.tcl below) actually talks to.
tcl_port $TCL_PORT

transport select jtag

set _CHIPNAME riscv
jtag newtap $_CHIPNAME cpu -irlen 5 -expected-id $IDCODE($DUT)

target create $_CHIPNAME.cpu riscv -chain-position $_CHIPNAME.cpu

init
halt
