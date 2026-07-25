# rbb_control.tcl — pure-TCL control sequence over Remote Bit-Bang, no Python.
#
# Demonstrates that the RBB simulation flow is independently controllable
# through OpenOCD's own scripting surface -- useful as a sanity check when
# bringing up RBB on a new DUT (isolate "is RBB/JTAG working at all" from
# "is pydebug's transport code working"), and as a minimal reference for
# anyone integrating a non-Python debugger frontend against this same
# simulation-only RBB flow.
#
# Usage (after rbb_launch.tcl / the canonical per-DUT .cfg has already run
# `init; halt`, i.e. as a second -c on the same openocd invocation, or
# piped to a running instance's tcl_port with `echo "..." | nc localhost 6666`):
#   openocd -f rbb_launch.tcl -c "set DUT ibex" -c "source rbb_control.tcl"
#
# Every command here is exactly what pydebug's OpenOCDTransport sends over
# the TCL port (src/pydebug/api/openocd_transport.py) -- this script is the
# same protocol, just issued directly instead of through Python sockets.

puts "==> rbb_control.tcl: reading dmstatus (DMI 0x11)"
set dmstatus [riscv dmi_read 0x11]
puts "    dmstatus = $dmstatus"

puts "==> rbb_control.tcl: activating DM (dmcontrol.dmactive=1, DMI 0x10)"
riscv dmi_write 0x10 0x00000001

puts "==> rbb_control.tcl: requesting halt (dmcontrol.haltreq=1)"
riscv dmi_write 0x10 0x80000001

# Poll dmstatus.allhalted (bit 9) -- same predicate RISCVDebug.halt() polls
# in src/pydebug/api/riscv_dm.py, just re-expressed as raw TCL here.
set halted 0
for {set i 0} {$i < 200} {incr i} {
    set s [riscv dmi_read 0x11]
    if {([expr {$s & 0x200}]) != 0} {
        set halted 1
        break
    }
}
if {$halted} {
    puts "==> rbb_control.tcl: hart halted (dmstatus.allhalted=1) after $i poll(s)"
} else {
    puts "==> rbb_control.tcl: WARNING -- hart did not report halted within 200 polls"
}

puts "==> rbb_control.tcl: clearing haltreq"
riscv dmi_write 0x10 0x00000001

puts "==> rbb_control.tcl: reading abstractcs (DMI 0x16)"
puts "    abstractcs = [riscv dmi_read 0x16]"

puts "==> rbb_control.tcl: done -- hart left halted, ready for further OpenOCD/GDB commands"
