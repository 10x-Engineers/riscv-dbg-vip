"""
interactive_shell.py — GDB-style live REPL on top of RISCVDebug.

Every command here is a thin wrapper around a real `RISCVDebug` method
(`src/pydebug/api/riscv_dm.py`) or a raw `DebugTransport` read/write — no
new debug logic lives in this file. The point is real-time, one-command-
at-a-time control against a *running* target (simulation or hardware),
the same way a debugger's own prompt works, rather than a pre-scripted
batch sequence that runs start-to-finish unattended.

Usage: `pydebug interactive --transport uvm` (see cli.py). Standalone:

    from pydebug.api import RISCVDebug, UVMTransport
    from pydebug.api.interactive_shell import RiscvDebugShell
    with UVMTransport() as t:
        RiscvDebugShell(RISCVDebug(t)).cmdloop()
"""

import cmd
import shlex

from .riscv_dm import RISCVDebug, DebugError, allhalted, allrunning, allresumeack, \
    allhavereset, anyunavail, hasresethaltreq, ndmresetpending, version
from .transport import TransportError

# ABI register names -> x-number, per the RISC-V calling convention.
_ABI_NAMES = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}


def _parse_int(s: str) -> int:
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def _parse_gpr(s: str) -> int:
    """Accept 'x5', 't0', 'a0', or a bare/hex regno -- return the abstract-
    command regno (0x1000 + x-number for GPRs)."""
    s = s.strip().lower()
    if s.startswith("x") and s[1:].isdigit():
        return 0x1000 | int(s[1:])
    if s in _ABI_NAMES:
        return 0x1000 | _ABI_NAMES[s]
    return _parse_int(s)  # already a raw regno (e.g. a CSR number)


class RiscvDebugShell(cmd.Cmd):
    intro = (
        "pydebug interactive shell -- type `help` for commands, `quit` to end.\n"
        "Every command below is a real, immediate operation against the live target."
    )
    prompt = "(pydebug) "

    def __init__(self, dm: RISCVDebug):
        super().__init__()
        self.dm = dm

    # ── error handling: never let a bad command kill the whole shell ────────

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except (DebugError, TransportError) as e:
            print(f"error: {e}")
            return False
        except ValueError as e:
            print(f"bad argument: {e}")
            return False

    # ── activation / lifecycle ───────────────────────────────────────────

    def do_activate(self, arg):
        "activate -- write dmcontrol.dmactive=1, verify DM version"
        self.dm.activate()
        print("DM activated")

    def do_deactivate(self, arg):
        "deactivate -- write dmcontrol.dmactive=0 (resets the DM)"
        self.dm.deactivate()
        print("DM deactivated")

    # ── run control ───────────────────────────────────────────────────────

    def do_halt(self, arg):
        "halt -- request halt, poll dmstatus.allhalted"
        self.dm.halt()
        print(f"halted, PC = 0x{self.dm.get_pc():08x}")

    def do_resume(self, arg):
        "resume -- request resume, poll dmstatus.allrunning"
        self.dm.resume()
        print("running")

    def do_step(self, arg):
        "step -- single-step one instruction (dcsr.step), then report the new PC"
        self.dm.set_step(True)
        self.dm.resume_no_wait()
        self.dm._poll_until(
            lambda s: allhalted(s), register=0x11, msg="allhalted (post-step)", timeout=2.0,
        )
        self.dm.set_step(False)
        cause = self.dm.get_dcsr_cause()
        print(f"stepped, PC = 0x{self.dm.get_pc():08x}  dcsr.cause={cause}")

    def do_select_hart(self, arg):
        "select_hart <n> -- select hart n for every subsequent dmcontrol write"
        self.dm.select_hart(_parse_int(arg))
        print(f"hartsel = {_parse_int(arg)}")

    def do_ndmreset(self, arg):
        "ndmreset [assert|deassert] -- platform reset (default: assert)"
        assert_reset = arg.strip() != "deassert"
        self.dm.ndmreset(assert_reset)
        print(f"ndmreset {'asserted' if assert_reset else 'deasserted'}")

    def do_hartreset(self, arg):
        "hartreset [assert|deassert] -- hart-only reset (default: assert)"
        assert_reset = arg.strip() != "deassert"
        self.dm.hartreset(assert_reset)
        print(f"hartreset {'asserted' if assert_reset else 'deasserted'}")

    # ── registers ─────────────────────────────────────────────────────────

    def do_read_gpr(self, arg):
        "read_gpr <x5|t0|a0|regno> -- read a GPR/CSR via abstract command"
        regno = _parse_gpr(arg)
        val = self.dm.read_gpr(regno)
        print(f"{arg.strip()} = 0x{val:08x}")

    def do_write_gpr(self, arg):
        "write_gpr <x5|t0|a0|regno> <value> -- write a GPR/CSR via abstract command"
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("usage: write_gpr <reg> <value>")
            return
        regno = _parse_gpr(parts[0])
        val = _parse_int(parts[1])
        self.dm.write_gpr(regno, val)
        print(f"{parts[0]} <- 0x{val:08x}")

    def do_pc(self, arg):
        "pc -- read the current PC (dpc CSR via abstract command)"
        print(f"PC = 0x{self.dm.get_pc():08x}")

    # ── memory (system bus access) ───────────────────────────────────────

    def do_read_mem(self, arg):
        "read_mem <addr> [count] -- read count (default 1) 32-bit words starting at addr"
        parts = shlex.split(arg)
        if not parts:
            print("usage: read_mem <addr> [count]")
            return
        addr = _parse_int(parts[0])
        count = _parse_int(parts[1]) if len(parts) > 1 else 1
        for i in range(count):
            a = addr + 4 * i
            print(f"0x{a:08x}: 0x{self.dm.read_mem32(a):08x}")

    def do_write_mem(self, arg):
        "write_mem <addr> <value> -- write one 32-bit word via System Bus Access"
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("usage: write_mem <addr> <value>")
            return
        addr, val = _parse_int(parts[0]), _parse_int(parts[1])
        self.dm.write_mem32(addr, val)
        print(f"0x{addr:08x} <- 0x{val:08x}")

    # ── raw DMI escape hatch ──────────────────────────────────────────────

    def do_read_dmi(self, arg):
        "read_dmi <addr> -- raw DMI register read (bypasses RISCVDebug helpers)"
        addr = _parse_int(arg)
        print(f"DMI[0x{addr:02x}] = 0x{self.dm.t.read(addr):08x}")

    def do_write_dmi(self, arg):
        "write_dmi <addr> <value> -- raw DMI register write"
        parts = shlex.split(arg)
        if len(parts) != 2:
            print("usage: write_dmi <addr> <value>")
            return
        addr, val = _parse_int(parts[0]), _parse_int(parts[1])
        self.dm.t.write(addr, val)
        print(f"DMI[0x{addr:02x}] <- 0x{val:08x}")

    # ── status ────────────────────────────────────────────────────────────

    def do_status(self, arg):
        "status -- decoded dmstatus snapshot"
        s = self.dm.read_dmstatus()
        print(f"dmstatus = 0x{s:08x}")
        print(f"  version           = {version(s)}")
        print(f"  allhalted         = {allhalted(s)}")
        print(f"  allrunning        = {allrunning(s)}")
        print(f"  allresumeack      = {allresumeack(s)}")
        print(f"  allhavereset      = {allhavereset(s)}")
        print(f"  anyunavail        = {anyunavail(s)}")
        print(f"  hasresethaltreq   = {hasresethaltreq(s)}")
        print(f"  ndmresetpending   = {ndmresetpending(s)}")

    def do_dmcontrol(self, arg):
        "dmcontrol -- raw dmcontrol read-back"
        print(f"dmcontrol = 0x{self.dm.read_dmcontrol():08x}")

    # ── shell control ─────────────────────────────────────────────────────

    def do_quit(self, arg):
        "quit -- disconnect (sends the transport shutdown, ends the sim) and exit"
        return True

    do_exit = do_quit
    do_EOF = do_quit

    def emptyline(self):
        pass  # don't repeat the last command on a bare Enter (cmd.Cmd's default)
