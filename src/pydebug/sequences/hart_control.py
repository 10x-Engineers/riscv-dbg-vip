"""
sequences/hart_control.py — putting a halted hart where a scenario needs it.

Several scenarios need the hart to execute one known instruction, at a chosen
privilege level, and come back: an ebreak or a single step in S or U, a halt
request that interrupts U-mode code. The Debug Module gives the debugger
exactly that lever -- write `dpc` and `dcsr.prv`, then resume or step -- and
these helpers wrap it.

Two things are easy to get wrong, and both have cost a test its meaning:

- `dpc` and other addresses must be written 64-bit. A 32-bit abstract write
  of 0x80000050 lands as 0xFFFFFFFF80000050 (the high bits of a short write
  are UNSPECIFIED, and the DM loads with a sign-extending `lw`), the hart
  faults at an address that does not exist, and a 32-bit read-back hides it.
- S- and U-mode code cannot run until PMP allows it. With PMP entries
  implemented and none matching, every S/U access faults (Priv. spec 3.7).
"""

import subprocess

from pydebug.api.riscv_dm import DMI

DCSR = 0x07B0
DPC = 0x07B1
MSTATUS = 0x0300
MIE = 0x0304
MCAUSE = 0x0342
MEPC = 0x0341
PMPCFG0 = 0x03A0
PMPADDR0 = 0x03B0

#: dcsr fields (Sdext 4.9.1).
DCSR_EBREAKM = 1 << 15
DCSR_EBREAKS = 1 << 13
DCSR_EBREAKU = 1 << 12
DCSR_STEPIE = 1 << 11
DCSR_STEP = 1 << 2
DCSR_PRV_MASK = 0x3
DCSR_CAUSE_LSB = 6

PRV_U, PRV_S, PRV_M = 0, 1, 3
CAUSE_EBREAK, CAUSE_TRIGGER, CAUSE_HALTREQ, CAUSE_STEP = 1, 2, 3, 4

MSTATUS_MIE = 1 << 3
MIE_MTIE = 1 << 7

ABSTRACTCS_CMDERR_W1C = 0x7 << 8


def symbol_addr(elf: str, symbol: str, nm: str = "riscv64-unknown-elf-nm") -> int:
    out = subprocess.run([nm, elf], capture_output=True, text=True, check=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == symbol:
            return int(parts[0], 16)
    raise RuntimeError(f"symbol {symbol!r} not found in {elf} -- rebuild with `make -C sw`")


def cause_of(dcsr: int) -> int:
    return (dcsr >> DCSR_CAUSE_LSB) & 0x7


def clear_cmderr(dm) -> None:
    dm.t.write(DMI.ABSTRACTCS, ABSTRACTCS_CMDERR_W1C)


def ensure_halted(dm, limit: int = 200) -> bool:
    """Halt the hart if it is not already, clearing a sticky cmderr first.

    cmderr is sticky: one command sent to a running hart (cmderr=4) makes
    every later command fail with the same error, so it is cleared before
    anything else.
    """
    clear_cmderr(dm)
    if dm.is_halted():
        return True
    dm.halt()
    return any(dm.is_halted() for _ in range(limit))


def open_pmp(dm) -> None:
    """One NAPOT entry covering the address space with R/W/X, so S and U code
    and data are reachable. Written 64-bit: pmpaddr is wider than 32 bits."""
    dm.write_reg64(PMPADDR0, (1 << 54) - 1)
    dm.write_reg64(PMPCFG0, 0x1F)          # entry 0: R, W, X, A=NAPOT


def modify_dcsr(dm, set_bits: int = 0, clear_bits: int = 0, prv: int = None) -> int:
    dcsr = dm.read_gpr(DCSR)                # dcsr is 32 bits (Sdext 4.9.1)
    dcsr = (dcsr | set_bits) & ~clear_bits
    if prv is not None:
        dcsr = (dcsr & ~DCSR_PRV_MASK) | prv
    dm.write_gpr(DCSR, dcsr)
    return dcsr


def place(dm, pc: int, prv: int) -> None:
    """Make the next resume start at `pc` in privilege `prv`."""
    modify_dcsr(dm, prv=prv)
    dm.write_reg64(DPC, pc)


def wait_halted(dm, limit: int = 400) -> bool:
    return any(dm.is_halted() for _ in range(limit))


def step_once(dm, limit: int = 400) -> bool:
    """With dcsr.step set, run one instruction and wait for the re-halt."""
    dm.resume_no_wait()
    return wait_halted(dm, limit)


def run_until_halted(dm, limit: int = 400) -> bool:
    """Resume (dcsr.step clear) and wait for the hart to halt on its own."""
    dm.resume_no_wait()
    return wait_halted(dm, limit)
