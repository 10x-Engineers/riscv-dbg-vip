"""
sequences/priv_state_sequence.py — what Debug Mode must leave alone, and
`dcsr.mprven`.

An OS debugger halts a hart that may be part-way through handling a trap.
If entering Debug Mode, or running the Program Buffer, disturbed the trap
CSRs, resuming would return the OS to the wrong place or misreport why it
trapped. The spec is explicit about both halves:

- Halt (Sdext "Halt"): when a hart halts, dcsr.cause, dcsr.prv/v and dpc are
  updated -- that list is the whole of what changes.
- Program Buffer (Sdext, executing code in Debug Mode): "Traps don't take
  place. ... Because they do not trap to M-mode, they do not update registers
  such as `mepc`, `mcause`, `mtval`, `mtval2`, and `mtinst`. The same is true
  for the equivalent privileged registers that are updated when trapping to
  other modes."

So each entry path -- haltreq, ebreak and step, from M, S and U -- and each
kind of Program Buffer exception is checked against sentinels written into
mepc/mcause/mtval and sepc/scause/stval beforehand, and against mstatus with
MPP/MPIE/MIE preset so that a trap would visibly change them.

CVA6 fails the ebreak case: an ebreak that enters Debug Mode (ebreakm/s/u
set) also takes the breakpoint trap's CSR update -- csr_regfile.sv excludes
only DEBUG_REQUEST from it. Tracked upstream as openhwgroup/cva6#1980.

`dcsr.mprven` (WARL, "may be tied to either 0 or 1"): with it 0, mstatus.MPRV
is ignored in Debug Mode; with it 1, MPRV takes effect. The check makes the
difference observable: PMP entry 0 denies a 4 KiB page to U and S (M is not
bound by an unlocked entry), mstatus has MPRV=1 and MPP=U, and the Program
Buffer loads from that page. It must succeed with mprven=0 and fault
(cmderr=3) with mprven=1.

Traces to: TC-DCSR-020 (haltreq entry), TC-DCSR-021 (ebreak entry),
TC-DCSR-022 (step entry) -- testplan DM-012, DM-017; TC-DCSR-023 (Program
Buffer exceptions) -- PB-006, PB-015; TC-DCSR-024 (mprven) -- DCSR-016.
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI
from pydebug.sequences.hart_control import (
    CAUSE_EBREAK, CAUSE_HALTREQ, CAUSE_STEP,
    DCSR, DCSR_EBREAKM, DCSR_EBREAKS, DCSR_EBREAKU, DCSR_STEP, DPC,
    MSTATUS, PMPADDR0, PMPCFG0, PRV_M, PRV_S, PRV_U,
    cause_of, clear_cmderr, ensure_halted, modify_dcsr, open_pmp, place,
    run_until_halted, step_once, symbol_addr,
)

MEPC, MCAUSE, MTVAL = 0x341, 0x342, 0x343
SEPC, SCAUSE, STVAL = 0x141, 0x142, 0x143
PMPADDR1 = PMPADDR0 + 1

#: Written into each trap CSR before an entry; what reads back (they are
#: WARL/WLRL) is the value that must survive. Each is something no trap on
#: this program would produce.
SENTINELS = {
    "mepc": (MEPC, 0x80000ABC), "mcause": (MCAUSE, 0x0B), "mtval": (MTVAL, 0x12345678),
    "sepc": (SEPC, 0x80000DEC), "scause": (SCAUSE, 0x05), "stval": (STVAL, 0xCAFE),
}

DCSR_MPRVEN = 1 << 4
MSTATUS_MPRV = 1 << 17
MSTATUS_MPP = 0x3 << 11
MSTATUS_MPIE, MSTATUS_MIE = 1 << 7, 1 << 3
#: The mstatus fields a trap to M rewrites (MPP <- prv, MPIE <- MIE, MIE <- 0),
#: preset so that any trap changes them: MPP=S, MPIE=1, MIE=0.
MSTATUS_TRAP_FIELDS = MSTATUS_MPP | MSTATUS_MPIE | MSTATUS_MIE
MSTATUS_TRAP_PRESET = (1 << 11) | MSTATUS_MPIE

# Assembled with riscv64-unknown-elf-as -march=rv64i, .option norvc.
EBREAK      = 0x00100073   # ebreak
ILLEGAL     = 0x00000000   # all-zero word: illegal in every base ISA
ECALL       = 0x00000073   # ecall
LW_T0_0_T1  = 0x00032283   # lw t0, 0(t1)
T1_REGNO    = 0x1006

#: The page PMP entry 0 denies to S and U in TC-DCSR-024. DRAM, clear of the
#: ELF and of the RAM other scenarios write.
PROBE_PAGE = 0x801B0000

PRV_NAME = {PRV_U: "U", PRV_S: "S", PRV_M: "M"}
EBREAK_BIT = {PRV_M: DCSR_EBREAKM, PRV_S: DCSR_EBREAKS, PRV_U: DCSR_EBREAKU}
ALL_EBREAK = DCSR_EBREAKM | DCSR_EBREAKS | DCSR_EBREAKU


def build_priv_state_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_classes.elf",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)
    addrs: dict = {}
    sentinel: dict = {}
    saved: dict = {}

    def arm_sentinels() -> None:
        for name, (csr, value) in SENTINELS.items():
            dm.write_reg64(csr, value)
            sentinel[name] = dm.read_reg64(csr)
        # mstatus is not overwritten wholesale: only the fields a trap moves.
        dm.write_reg64(MSTATUS, (saved["mstatus"] & ~MSTATUS_TRAP_FIELDS) | MSTATUS_TRAP_PRESET)
        sentinel["mstatus"] = dm.read_reg64(MSTATUS)

    def disturbed() -> dict:
        """The trap CSRs that moved since arm_sentinels(), then re-arm them so
        one failure does not cascade into every later step."""
        moved = {}
        for name, csr in [(n, c) for n, (c, _) in SENTINELS.items()] + [("mstatus", MSTATUS)]:
            now = dm.read_reg64(csr)
            if now != sentinel[name]:
                moved[name] = f"0x{sentinel[name]:x}->0x{now:x}"
        if moved:
            arm_sentinels()
        return moved

    def report(tc: str, rows: list) -> StepResult:
        """rows: (label, entered-as-expected, detail, moved)."""
        ok = all(entered and not moved for _, entered, _, moved in rows)
        return StepResult(
            ok=ok,
            msg=f"{tc}: " + "; ".join(
                f"{label} {detail}" + (f" DISTURBED {moved}" if moved else " trap CSRs intact")
                for label, entered, detail, moved in rows)
                + ("  OK" if ok else "  FAIL"))

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def setup():
        for sym in ("cls_ebreak", "ebreak_park", "step_loop"):
            addrs[sym] = symbol_addr(elf, sym)
        for name, csr in (("mstatus", MSTATUS), ("pmpcfg0", PMPCFG0),
                          ("pmpaddr0", PMPADDR0), ("pmpaddr1", PMPADDR1),
                          ("dcsr", DCSR), ("dpc", DPC)):
            saved[name] = dm.read_reg64(csr)
        open_pmp(dm)
        arm_sentinels()
        return StepResult(
            ok=True,
            msg="sentinels " + ", ".join(f"{k}=0x{v:x}" for k, v in sentinel.items())
                + "; PMP entry 0 opened for S/U")
    session.add_step("Resolve entry points, open PMP, arm trap-CSR sentinels", setup)

    # ── TC-DCSR-020: haltreq entry ────────────────────────────────────────
    def tc_dcsr_020():
        rows = []
        for prv in (PRV_M, PRV_S, PRV_U):
            ensure_halted(dm)
            modify_dcsr(dm, clear_bits=ALL_EBREAK | DCSR_STEP)
            place(dm, addrs["ebreak_park"], prv)     # a one-instruction spin
            dm.resume()
            dm.halt()
            cause = cause_of(dm.read_gpr(DCSR))
            rows.append((f"haltreq in {PRV_NAME[prv]}", cause == CAUSE_HALTREQ,
                         f"cause={cause}", disturbed()))
        return report("TC-DCSR-020", rows)
    session.add_step("TC-DCSR-020: haltreq entry leaves the trap CSRs alone", tc_dcsr_020)

    # ── TC-DCSR-021: ebreak entry ─────────────────────────────────────────
    def tc_dcsr_021():
        rows = []
        for prv in (PRV_M, PRV_S, PRV_U):
            ensure_halted(dm)
            modify_dcsr(dm, set_bits=EBREAK_BIT[prv],
                        clear_bits=(ALL_EBREAK | DCSR_STEP) & ~EBREAK_BIT[prv])
            place(dm, addrs["cls_ebreak"], prv)
            entered = run_until_halted(dm)
            if not entered:
                ensure_halted(dm)
            cause = cause_of(dm.read_gpr(DCSR))
            rows.append((f"ebreak in {PRV_NAME[prv]}", entered and cause == CAUSE_EBREAK,
                         f"halted={entered} cause={cause}", disturbed()))
        modify_dcsr(dm, clear_bits=ALL_EBREAK)
        return report("TC-DCSR-021", rows)
    session.add_step("TC-DCSR-021: ebreak entry leaves the trap CSRs alone", tc_dcsr_021)

    # ── TC-DCSR-022: step entry ───────────────────────────────────────────
    def tc_dcsr_022():
        rows = []
        start = addrs["step_loop"] + 4               # `li t3, 1`: traps on nothing
        for prv in (PRV_M, PRV_S, PRV_U):
            ensure_halted(dm)
            modify_dcsr(dm, set_bits=DCSR_STEP, clear_bits=ALL_EBREAK)
            place(dm, start, prv)
            entered = step_once(dm)
            cause = cause_of(dm.read_gpr(DCSR))
            modify_dcsr(dm, clear_bits=DCSR_STEP)
            rows.append((f"step in {PRV_NAME[prv]}", entered and cause == CAUSE_STEP,
                         f"halted={entered} cause={cause}", disturbed()))
        return report("TC-DCSR-022", rows)
    session.add_step("TC-DCSR-022: step entry leaves the trap CSRs alone", tc_dcsr_022)

    # ── TC-DCSR-023: exceptions inside the Program Buffer ─────────────────
    # Each must end the buffer with cmderr=3 and update nothing -- not the
    # trap CSRs, and not dpc either: the hart never left Debug Mode.
    def tc_dcsr_023():
        ensure_halted(dm)
        modify_dcsr(dm, prv=PRV_M)
        dm.write_reg64(DPC, addrs["ebreak_park"])
        dpc_before = dm.read_reg64(DPC)
        rows = []
        for label, word in (("illegal instruction", ILLEGAL), ("ecall", ECALL)):
            dm.write_progbuf(0, word)
            dm.write_progbuf(1, EBREAK)
            clear_cmderr(dm)
            dm.t.write(DMI.COMMAND, (2 << 20) | (1 << 18))   # postexec only
            for _ in range(400):
                acs = dm.t.read(DMI.ABSTRACTCS)
                if not (acs >> 12) & 1:
                    break
            err = (acs >> 8) & 0x7
            clear_cmderr(dm)
            dpc = dm.read_reg64(DPC)
            moved = disturbed()
            if dpc != dpc_before:
                moved["dpc"] = f"0x{dpc_before:x}->0x{dpc:x}"
            rows.append((label, err == 3 and dm.is_halted(),
                         f"cmderr={err} (expect 3) halted={dm.is_halted()}", moved))
        return report("TC-DCSR-023", rows)
    session.add_step("TC-DCSR-023: Program Buffer exceptions update no trap CSR", tc_dcsr_023)

    # ── TC-DCSR-024: dcsr.mprven ──────────────────────────────────────────
    def tc_dcsr_024():
        ensure_halted(dm)
        settable = []
        for want in (0, 1):
            modify_dcsr(dm, set_bits=DCSR_MPRVEN if want else 0,
                        clear_bits=0 if want else DCSR_MPRVEN)
            got = (dm.read_gpr(DCSR) >> 4) & 1
            if got == want:
                settable.append(want)
        # PMP: entry 0 a 4 KiB NAPOT page with no permissions, entry 1 the rest
        # of the address space R/W/X. Neither is locked, so M ignores both.
        dm.write_reg64(PMPADDR0, (PROBE_PAGE >> 2) | 0x1FF)
        dm.write_reg64(PMPADDR1, (1 << 54) - 1)
        dm.write_reg64(PMPCFG0, (0x1F << 8) | 0x18)
        dm.write_reg64(T1_REGNO, PROBE_PAGE)
        dm.write_progbuf(0, LW_T0_0_T1)
        dm.write_progbuf(1, EBREAK)
        dm.write_reg64(MSTATUS, (saved["mstatus"] & ~MSTATUS_MPP) | MSTATUS_MPRV)  # MPP=U
        results = {}
        for mprven in settable:
            modify_dcsr(dm, set_bits=DCSR_MPRVEN if mprven else 0,
                        clear_bits=0 if mprven else DCSR_MPRVEN)
            clear_cmderr(dm)
            dm.t.write(DMI.COMMAND, (2 << 20) | (1 << 18))   # postexec only
            for _ in range(400):
                acs = dm.t.read(DMI.ABSTRACTCS)
                if not (acs >> 12) & 1:
                    break
            results[mprven] = (acs >> 8) & 0x7
            clear_cmderr(dm)
        # MPRV must be off again before anything else runs in M.
        dm.write_reg64(MSTATUS, saved["mstatus"])
        for name, csr in (("pmpaddr0", PMPADDR0), ("pmpaddr1", PMPADDR1), ("pmpcfg0", PMPCFG0)):
            dm.write_reg64(csr, saved[name])
        open_pmp(dm)
        modify_dcsr(dm, set_bits=saved["dcsr"] & DCSR_MPRVEN,
                    clear_bits=DCSR_MPRVEN & ~saved["dcsr"])
        want = {0: 0, 1: 3}
        bad = {m: e for m, e in results.items() if e != want[m]}
        ok = bool(settable) and not bad
        return StepResult(
            ok=ok,
            msg=f"TC-DCSR-024: mprven settable to {settable}; with MPRV=1, MPP=U, a "
                f"load from the U-denied page gives "
                + ", ".join(f"mprven={m} -> cmderr={e} (expect {want[m]})" for m, e in results.items())
                + ("  OK" if ok else f"  mprven not honoured: {bad}"))
    session.add_step("TC-DCSR-024: dcsr.mprven decides whether MPRV applies in Debug Mode", tc_dcsr_024)

    def restore():
        ensure_halted(dm)
        dm.write_reg64(MSTATUS, saved["mstatus"])
        dm.write_gpr(DCSR, saved["dcsr"] & 0xFFFFFFFF)   # dcsr is 32 bits
        dm.write_reg64(DPC, saved["dpc"])
        return StepResult(ok=True, msg="mstatus, dcsr, dpc restored; hart halted")
    session.add_step("Restore", restore)

    return session
