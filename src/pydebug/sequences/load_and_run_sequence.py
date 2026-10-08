"""
sequences/load_and_run_sequence.py — download a program and run it, the way a
debugger brings up a board with nothing in memory.

The flow every bring-up uses: write the program into RAM over System Bus
Access, make the hart's instruction fetch see it (`fence.i`, since SBA
bypasses the hart's caches), point `dpc` at it, resume, and wait for it to
come back through an `ebreak` with `dcsr.ebreakm` set. Then read its result
both ways: the register it computed into (an abstract command) and the word
it stored (over SBA, after a `fence` writes the hart's dirty lines back).

No other scenario does this end to end. cmd_outcome writes code into RAM over
SBA but enters it from the Program Buffer, and the native_* tests run code the
testbench preloaded.

The second download overwrites the first program in place with one that
computes something else. A hart that ran the old program again -- stale
I-cache, or a `fence.i` that did nothing -- stores the first result, so the
two downloads are told apart.

Traces to: TC-LR-001 (download and run), TC-LR-002 (re-download over the
same address) -- testplan RES-011.
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI
from pydebug.sequences.hart_control import (
    CAUSE_EBREAK, DCSR, DCSR_EBREAKM, DCSR_STEP, DPC, PRV_M,
    cause_of, ensure_halted, modify_dcsr,
)

SBDATA1 = 0x3D

# Assembled with riscv64-unknown-elf-as -march=rv64i_zifencei, .option norvc.
FENCE   = 0x0FF0000F   # fence
FENCE_I = 0x0000100F   # fence.i
EBREAK  = 0x00100073   # ebreak
NOP     = 0x00000013   # nop

#: auipc t0,0; li a0,<k>; addi a0,a0,<j>; sd a0,0x100(t0); ebreak; nop.
#: The result lands 0x100 past the program, in its own cache line.
PROGRAM_A = (0x00000297, 0x12300513, 0x11150513, 0x10A2B023, EBREAK, NOP)   # a0 = 0x234
PROGRAM_B = (0x00000297, 0x45600513, 0x22250513, 0x10A2B023, EBREAK, NOP)   # a0 = 0x678
RESULT_A, RESULT_B = 0x234, 0x678
EBREAK_OFFSET = 4 * PROGRAM_A.index(EBREAK)
RESULT_OFFSET = 0x100

#: DRAM, clear of halt_probe.elf and of the RAM cmd_outcome (0x80180000),
#: abstractauto (0x801A0000), priv_state (0x801B0000) and dm_corners use.
PROG_ADDR = 0x801C0000

A0_REGNO, T0_REGNO = 0x100A, 0x1005


def build_load_and_run_sequence(dm: RISCVDebug, mode: str = "batch") -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    saved = {}

    def sba_write64(addr: int, value: int) -> None:
        dm.t.write(DMI.SBCS, 3 << 17)                     # 64-bit, no read-on-addr
        dm.t.write(DMI.SBADDRESS0, addr)
        dm.t.write(SBDATA1, value >> 32)
        dm.t.write(DMI.SBDATA0, value & 0xFFFFFFFF)       # starts the write
        dm._wait_sbus()

    def sba_read64(addr: int) -> int:
        dm.t.write(DMI.SBCS, (1 << 20) | (3 << 17))       # read on address
        dm.t.write(DMI.SBADDRESS0, addr)
        dm._wait_sbus()
        return (dm.t.read(SBDATA1) << 32) | dm.t.read(DMI.SBDATA0)

    def run_progbuf(*words) -> None:
        for i, w in enumerate(words):
            dm.write_progbuf(i, w)
        dm.execute_progbuf()

    def download(words) -> bool:
        """Write `words` at PROG_ADDR over SBA and read them back."""
        pairs = [(words[i + 1] << 32) | words[i] for i in range(0, len(words), 2)]
        for i, w in enumerate(pairs):
            sba_write64(PROG_ADDR + 8 * i, w)
        return [sba_read64(PROG_ADDR + 8 * i) for i in range(len(pairs))] == pairs

    def load_and_run(tc: str, words, want: int) -> StepResult:
        if not ensure_halted(dm):
            return StepResult(ok=False, msg=f"{tc}: hart would not halt")
        loaded = download(words)
        run_progbuf(FENCE_I, EBREAK)                       # fetch must see the new code
        modify_dcsr(dm, set_bits=DCSR_EBREAKM, clear_bits=DCSR_STEP, prv=PRV_M)
        dm.write_reg64(DPC, PROG_ADDR)
        dm.resume_no_wait()
        returned = any(dm.is_halted() for _ in range(400))
        if not returned:
            ensure_halted(dm)
        cause = cause_of(dm.read_gpr(DCSR))
        dpc = dm.read_reg64(DPC)
        a0 = dm.read_reg64(A0_REGNO)
        run_progbuf(FENCE, EBREAK)                         # write the stored word back
        stored = sba_read64(PROG_ADDR + RESULT_OFFSET)
        ok = (loaded and returned and cause == CAUSE_EBREAK
              and dpc == PROG_ADDR + EBREAK_OFFSET and a0 == want and stored == want)
        if ok:
            verdict = "OK"
        elif a0 == RESULT_A and want == RESULT_B:
            verdict = "the previous program ran -- stale instruction fetch"
        else:
            verdict = "program did not run as downloaded"
        return StepResult(
            ok=ok,
            msg=f"{tc}: downloaded {len(words)} words at 0x{PROG_ADDR:x} (read-back ok={loaded}); "
                f"returned={returned} cause={cause} (expect {CAUSE_EBREAK}) "
                f"dpc=0x{dpc:x} (expect 0x{PROG_ADDR + EBREAK_OFFSET:x}); "
                f"a0=0x{a0:x}, stored=0x{stored:x} (expect 0x{want:x})  {verdict}")

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        for name, regno in (("dcsr", DCSR), ("dpc", DPC), ("a0", A0_REGNO), ("t0", T0_REGNO)):
            saved[name] = dm.read_reg64(regno)
        return StepResult(ok=True, msg="saved dcsr, dpc, a0, t0")
    session.add_step("Save the state the programs change", setup)

    session.add_step("TC-LR-001: download a program over SBA and run it",
                     lambda: load_and_run("TC-LR-001", PROGRAM_A, RESULT_A))
    session.add_step("TC-LR-002: download a different program over it and run that",
                     lambda: load_and_run("TC-LR-002", PROGRAM_B, RESULT_B))

    def restore():
        ensure_halted(dm)
        dm.write_gpr(DCSR, saved["dcsr"] & 0xFFFFFFFF)     # dcsr is 32 bits
        for name, regno in (("dpc", DPC), ("a0", A0_REGNO), ("t0", T0_REGNO)):
            dm.write_reg64(regno, saved[name])
        return StepResult(ok=True, msg="dcsr, dpc, a0, t0 restored; hart halted")
    session.add_step("Restore", restore)

    return session
