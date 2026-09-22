"""
sequences/dm_corners_sequence.py — Debug Module arms no ordinary debugger flow reaches.

Each step targets code that code coverage showed was never executed, and that
is reachable on this DUT once you know how. Three routes, none of them exotic:

* **The hart polls its flags while another hart is selected** (#3.14.2).
  dm_mem answers a hart's flag read only if that hart is the selected one.
  With one hart that comparison is always true, unless the debugger selects
  a hart that does not exist while hart 0 sits in the park loop.

* **The Debug Module's own memory is on the system bus.** The testharness
  maps dm_mem at 0x0 on the same crossbar SBA uses, so SBA reaches decode arms
  that only the hart normally touches: a write to an address with no flag
  behind it, a read of `whereto` while no command is pending, and a read of
  another hart's flag word.

* **A system bus access can be held busy** (#3.10). Every other scenario's
  transfer finishes in a few clock cycles, while one JTAG scan takes about
  ninety, so no DMI access ever arrived while `sbbusy` was set, and all of
  dm_csrs's `sbbusy` arms except the ones reached through `sbbusyerror` were
  dead. `ndmreset` holds the crossbar in reset while the DM's bus master
  stays out of it, so a transfer started under `ndmreset` stays busy for as
  long as the debugger likes.

* **Toggle coverage** named whole fields no scenario ever set: WARL-masked
  and reserved register bits, and the upper half of every 64-bit bus.

Traces to: TC-DMC-001 (flag poll with a nonexistent hart selected),
TC-DMC-002 (SBA into the DM's own memory), TC-DMC-003 (DMI access while
sbbusy), TC-DMC-004 (DM consistent after release), TC-DMC-005 (every
writable register bit), TC-DMC-006 (64-bit bus and data-path halves),
TC-DMC-007 (sbcs reserved bits read 0), TC-DMC-008 (haltsum1-3 read 0),
TC-DMC-009 (another hart's state slots), TC-DMC-010 (abstract-command
program walk).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI, allnonexistent

SBADDRESS1 = 0x3A
SBDATA1    = 0x3D

SB_BUSYERROR  = 22
SB_BUSY       = 21
SB_READONADDR = 20
SB_ACCESS_LSB = 17
SB_ERROR_LSB  = 12

#: dm_mem's address map (dm_mem.sv): whereto, the flag words, and a hole.
DM_WHERETO   = 0x300
DM_FLAGS     = 0x400
DM_UNDECODED = 0x000

#: DRAM, away from the program image, and never written by this model, so
#: the value the stalled read eventually returns is not predicted.
STALL_ADDR = 0x80001000

DMC_RESUMEREQ = 30
DMC_DMACTIVE  = 0

#: DRAM for the 64-bit patterns, chosen with bits [27:13] set: no other
#: address in the suite has them, so the address buses never toggled there.
#: The RISCV_VIP_MODE memory is 2 MB and decodes addr[20:3], so this aliases
#: to 0x801FE000 -- well clear of halt_probe.elf, a few words at 0x80000000.
#: Written before it is read: unwritten memory reads X.
#: Overridable per DUT: on Ibex this address decodes to nothing, the demo
#: system's bus leaves the read data X, and the DM's response FIFO trips
#: lowRISC's own `DataKnown_A` assertion (prim_fifo_sync.sv:151) -- which ends
#: the simulation before the scenario reaches anything else.
SCRATCH_ADDR = 0x8FFFE000

#: All offsets from the DM's own base address, which is where the SoC maps
#: dm_mem: 0 on CVA6, 0x1a110000 on the Ibex demo system (DEBUG_START). An
#: absolute address here reaches nothing on a SoC that maps it elsewhere, and
#: the read comes back X rather than as a bus error.
#:
#: dm_mem regions, as 64-bit words (dm_mem.sv / debug_rom.sv): the debug ROM
#: (19 words at HaltAddress), the abstract-command slots, the Program Buffer
#: and the data registers.
ROM_WORDS      = [0x800 + 8 * i for i in range(19)]
ABSTRACT_WORDS = [0x338 + 8 * i for i in range(5)]
PROGBUF_WORDS  = [0x360 + 8 * i for i in range(4)]
DATA_WORDS     = [0x380]

#: debug_rom.sv, as dm_mem serves it: mem[0] (the last word listed there)
#: at 0x800. Checked word for word by TC-DMC-006.
DEBUG_ROM = [
    0x07c0006f_00c0006f, 0x0ff0000f_04c0006f, 0x7b351073_7b241073,
    0x00c55513_00000517, 0xf1402473_00c51513, 0x00a40433_10852023,
    0x00147413_40044403, 0xf1402473_02041c63, 0x40044403_00a40433,
    0xfa041ce3_00247413, 0x00000517_fd5ff06f, 0x00c51513_00c55513,
    0x7b302573_10052623, 0x00100073_7b202473, 0x7b302573_10052223,
    0xa85ff06f_7b202473, 0x10852423_f1402473, 0x7b202473_7b302573,
    0x00000000_7b200073,
]

#: whereto while a resume is requested: jal x0, ResumeAddress - WhereTo
#: (0x804 - 0x300), zero-extended to the 64-bit word.
WHERETO_RESUME = 0x5040006f

#: dm_mem's per-hart state words (dm_mem.sv): a hart writes its id here.
DM_HALTED   = 0x100
DM_RESUMING = 0x108

ABSTRACTAUTO = 0x18
HALTSUM1, HALTSUM2, HALTSUM3 = 0x13, 0x34, 0x35
EBREAK = 0x00100073
X5_REGNO = 0x1005
ONES = 0xFFFFFFFF

#: sbcs reserved field [28:23], which the spec defines as reading 0.
SBCS_ZERO0 = 0x1F800000


def _sbcs_read_on_addr() -> int:
    return (1 << SB_READONADDR) | (2 << SB_ACCESS_LSB)


def build_dm_corners_sequence(dm: RISCVDebug, mode: str = "batch",
                              scratch_addr: int = SCRATCH_ADDR,
                              dm_base: int = 0) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    # ── TC-DMC-001: flag poll while a nonexistent hart is selected ────────
    def tc_dmc_001():
        # With hartsel=1 dmstatus indexes a one-hart vector out of range and
        # reads X (RTL-008). The reads are recorded rather than raised, and
        # hart 0 is always reselected: a step that left hartsel=1 behind made
        # every later step fail with cmderr=4 against a hart that does not
        # exist, hiding what those steps were testing.
        status, errors = [], []
        dm.select_hart(1)
        try:
            # A few DMI round-trips: the parked hart reads its flag word every
            # few cycles, and each read must now miss.
            for _ in range(3):
                try:
                    status.append(dm.t.read(DMI.DMSTATUS))
                except Exception as e:       # noqa: BLE001 - X is the finding
                    errors.append(str(e))
        finally:
            dm.select_hart(0)
        still_halted = dm.is_halted()
        nonexist = bool(status) and all(allnonexistent(v) for v in status)
        ok = not errors and nonexist and still_halted
        return StepResult(
            ok=ok,
            msg=f"TC-DMC-001: hartsel=1 -> allnonexistent={nonexist}"
                + (f", dmstatus unreadable: {errors[0]}" if errors else "")
                + f"; back on hart 0 it is still halted={still_halted}  "
                + ("OK" if ok else
                   "dmstatus reads X for a nonexistent hart -- RTL-008" if errors else
                   "hart 0 released, or hart 1 reported present"),
        )

    # ── TC-DMC-002: SBA into the DM's own memory ──────────────────────────
    def tc_dmc_002():
        # A write to a hole in dm_mem's decode must be ignored. Zero, so the
        # bus's write-data register holds 0 for the reads below: dm_mem
        # indexes a per-hart array with the low bit of that register.
        dm.write_mem32(DM_UNDECODED, 0)
        flags_mine  = dm.read_mem32(dm_base + DM_FLAGS)
        flags_other = dm.read_mem32(dm_base + DM_FLAGS + 8)
        # whereto with no command pending, and again while a resume request
        # is outstanding: resumereq stays up because the hart is running and
        # so never acknowledges it.
        idle_whereto = dm.read_mem32(DM_WHERETO)
        dm.resume()
        dm.t.write(DMI.DMCONTROL, (1 << DMC_RESUMEREQ) | (1 << DMC_DMACTIVE))
        resume_whereto = dm.read_mem32(DM_WHERETO)
        dm.t.write(DMI.DMCONTROL, 1 << DMC_DMACTIVE)
        dm.halt()
        # With nothing pending the hart must not be told to go or resume, and
        # a pending resume must send it to the resume entry. (An idle whereto
        # returns whatever dm_mem last read -- rdata_d = rdata_q -- which the
        # DM does not define, so it is reported, not checked.)
        ok = flags_mine == 0 and flags_other == 0 and resume_whereto == WHERETO_RESUME
        return StepResult(
            ok=ok,
            msg=f"TC-DMC-002: flags(hart0)=0x{flags_mine:08x} flags(+8)="
                f"0x{flags_other:08x} (expect 0), whereto idle=0x{idle_whereto:08x}, "
                f"whereto with resumereq=0x{resume_whereto:08x}  "
                + ("OK" if ok else f"a flag was raised with nothing pending, or whereto "
                                   f"is not jal ResumeAddress (0x{WHERETO_RESUME:08x})"),
        )
    session.add_step("TC-DMC-002: SBA into the Debug Module's own memory", tc_dmc_002)

    def _sba_read64(addr: int) -> int:
        dm.t.write(DMI.SBADDRESS0, addr)     # sbreadonaddr is set by the caller
        dm._wait_sbus()
        return (dm.t.read(SBDATA1) << 32) | dm.t.read(DMI.SBDATA0)

    def _abstract(control: int) -> int:
        dm.t.write(DMI.COMMAND, control)
        dm._poll_until(lambda v: not (v >> 12) & 1, DMI.ABSTRACTCS,
                       "abstractcs.busy=0", dm.DEFAULT_TIMEOUT)
        err = (dm.t.read(DMI.ABSTRACTCS) >> 8) & 0x7
        dm.t.write(DMI.ABSTRACTCS, 0x7 << 8)
        return err

    # ── TC-DMC-005: every writable register bit, both ways ────────────────
    # Toggle coverage showed whole fields that no scenario ever set: the WARL
    # masks of abstractauto, relaxedpriv, the reserved and unused bits of
    # command, and every bit of sbcs a debugger may write. Each is written
    # all-ones and then restored. abstractauto is read back in between, which
    # also checks its WARL masking against progbufsize/datacount.
    def tc_dmc_005():
        problems = []
        dm.t.write(DMI.ABSTRACTCS, ONES)             # relaxedpriv=1, cmderr W1C
        relaxed = (dm.t.read(DMI.ABSTRACTCS) >> 11) & 1
        dm.t.write(DMI.ABSTRACTCS, 0)
        dm.t.write(ABSTRACTAUTO, ONES)
        auto = dm.t.read(ABSTRACTAUTO)
        dm.t.write(ABSTRACTAUTO, 0)                  # disarm before any data/progbuf access
        if auto != 0x00FF0003:
            problems.append(f"abstractauto=0x{auto:08x}, expected 0x00ff0003")
        # Reserved bit 23, aarpostincrement and regno[13], with no transfer
        # and no postexec: nothing to execute, so the only question is that
        # the DM comes back usable.
        cmd_err = _abstract((1 << 23) | (2 << 20) | (1 << 19) | (1 << 13))
        return StepResult(
            ok=not problems,
            msg=f"TC-DMC-005: relaxedpriv reads {relaxed} after writing 1; "
                f"abstractauto all-ones -> 0x{auto:08x}; odd command -> cmderr={cmd_err}  "
                + ("OK" if not problems else "; ".join(problems)),
        )
    session.add_step("TC-DMC-005: every writable register bit, both ways", tc_dmc_005)

    # ── TC-DMC-007: sbcs reserved bits read 0 ─────────────────────────────
    # Its own step so a failure names exactly one thing. The reference model
    # masks sbcs to the fields it predicts, so without this explicit check the
    # reserved bits are compared by nobody. Fails today: RTL-006.
    def tc_dmc_007():
        dm.t.write(DMI.SBCS, ONES)
        sbcs = dm.t.read(DMI.SBCS)
        dm.t.write(DMI.SBCS, _sbcs_read_on_addr())
        reserved = (sbcs & SBCS_ZERO0) >> 23
        return StepResult(
            ok=reserved == 0,
            msg=f"TC-DMC-007: sbcs after writing all-ones = 0x{sbcs:08x}, reserved "
                f"[28:23] = 0x{reserved:02x} (expect 0)  "
                + ("OK" if reserved == 0 else "reserved bits hold the written value -- RTL-006"),
        )
    session.add_step("TC-DMC-007: sbcs reserved bits read 0", tc_dmc_007)

    # ── TC-DMC-008: haltsum1-3 read 0 on a single-hart DM ─────────────────
    # They summarise groups of 32 harts, so with one hart every bit is 0; the
    # decode answers them regardless. Each is read on its own so one X does
    # not hide the others. Fails today: RTL-007 (bit 0 reads X).
    def tc_dmc_008():
        seen = {}
        for name, addr in (("haltsum1", HALTSUM1), ("haltsum2", HALTSUM2),
                           ("haltsum3", HALTSUM3)):
            try:
                seen[name] = f"0x{dm.t.read(addr):08x}"
            except Exception as e:           # noqa: BLE001 - X is reported, not raised
                seen[name] = f"unknown ({e})"
        ok = all(v == "0x00000000" for v in seen.values())
        return StepResult(
            ok=ok,
            msg="TC-DMC-008: " + "; ".join(f"{k}={v}" for k, v in seen.items())
                + ("  OK" if ok else "  expected 0 -- RTL-007"),
        )
    session.add_step("TC-DMC-008: haltsum1-3 read 0", tc_dmc_008)

    # ── TC-DMC-006: the 64-bit halves of the system bus and the data path ─
    # sbasize is 64, so sbaddress1 and sbdata1 exist and the bus carries
    # 64-bit words; every scenario so far used 32-bit values, leaving the upper
    # half of each bus untoggled. Likewise every abstract command used
    # aarsize=2, so the hart never wrote the upper half of the data window.
    def tc_dmc_006():
        # The whole step is about the 64-bit halves: sbdata1/sbaddress1 and
        # 64-bit reads of dm_mem. A DM whose system bus is 32 bits wide
        # advertises no sbaccess64 and answers a 64-bit access with
        # sberror=3 -- which `_wait_sbus()` raises, killing the session. Gate
        # on what sbcs says rather than assuming CVA6's bus width.
        if not (dm.t.read(DMI.SBCS) >> 3) & 1:
            return StepResult(
                ok=True,
                msg="TC-DMC-006: N/A -- sbcs advertises no 64-bit access, so "
                    "there are no sbdata1/sbaddress1 halves to exercise")
        problems = []
        dm.t.write(DMI.SBCS, 2 << SB_ACCESS_LSB)      # no read-on-address
        dm.t.write(SBADDRESS1, ONES)
        dm.t.write(SBADDRESS1, 0)
        dm.t.write(DMI.SBADDRESS0, scratch_addr)
        readback = {}
        for pattern in (ONES, 0):
            dm.t.write(DMI.SBCS, 2 << SB_ACCESS_LSB)
            dm.t.write(DMI.SBADDRESS0, scratch_addr)
            dm.t.write(SBDATA1, pattern)
            dm.t.write(DMI.SBDATA0, pattern)          # starts the 64-bit write
            dm._wait_sbus()
            dm.t.write(DMI.SBCS, _sbcs_read_on_addr())
            readback[pattern] = _sba_read64(scratch_addr)
            if readback[pattern] != (pattern << 32) | pattern:
                problems.append(f"SBA 64-bit 0x{pattern:08x}{pattern:08x} read back "
                                f"0x{readback[pattern]:016x}")
        # An address with its low two bits set: the byte-enable index.
        _sba_read64(dm_base + DM_FLAGS + 3)
        # 64-bit reads of every dm_mem region, with the Program Buffer holding
        # all-ones and then all-zeros so its read path toggles both ways. Each
        # word is checked against what dm_mem should serve, except the
        # abstract-command slots, whose content is the last command's program.
        for fill in (ONES, 0):
            for i in range(8):
                dm.write_progbuf(i, fill)
            for addr in [dm_base + w for w in PROGBUF_WORDS]:
                got = _sba_read64(addr)
                if got != (fill << 32) | fill:
                    problems.append(f"progbuf word 0x{addr:03x}=0x{got:016x}")
        for i in range(8):
            dm.write_progbuf(i, EBREAK)
        for addr, want in zip([dm_base + w for w in ROM_WORDS], DEBUG_ROM):
            got = _sba_read64(addr)
            if got != want:
                problems.append(f"ROM 0x{addr:03x}=0x{got:016x}, expected 0x{want:016x}")
        for addr in [dm_base + w for w in ABSTRACT_WORDS]:
            _sba_read64(addr)
        data_now = (dm.t.read(DMI.DATA1) << 32) | dm.t.read(DMI.DATA0)
        got = _sba_read64(DATA_WORDS[0])
        if got != data_now:
            problems.append(f"data word 0x{got:016x}, data1:data0 0x{data_now:016x}")
        # 64-bit register round-trip: aarsize=3 moves data0 and data1 together.
        gpr = {}
        for pattern in (ONES, 0):
            dm.t.write(DMI.DATA0, pattern)
            dm.t.write(DMI.DATA1, pattern)
            werr = _abstract((3 << 20) | (1 << 17) | (1 << 16) | X5_REGNO)
            rerr = _abstract((3 << 20) | (1 << 17) | X5_REGNO)
            gpr[pattern] = (dm.t.read(DMI.DATA1) << 32) | dm.t.read(DMI.DATA0)
            if werr or rerr or gpr[pattern] != (pattern << 32) | pattern:
                problems.append(f"x5 64-bit 0x{pattern:08x}{pattern:08x}: cmderr "
                                f"{werr}/{rerr}, read 0x{gpr[pattern]:016x}")
        return StepResult(
            ok=not problems,
            msg=f"TC-DMC-006: SBA 64-bit round-trips "
                f"0x{readback[ONES]:016x}/0x{readback[0]:016x}; x5 64-bit round-trips "
                f"0x{gpr[ONES]:016x}/0x{gpr[0]:016x}; read "
                f"{len(ROM_WORDS + ABSTRACT_WORDS + PROGBUF_WORDS + DATA_WORDS)} dm_mem words  "
                + ("OK" if not problems else "; ".join(problems)),
        )
    session.add_step("TC-DMC-006: 64-bit bus and data-path halves", tc_dmc_006)

    # ── TC-DMC-009: another hart's state slots in dm_mem ──────────────────
    # dm_mem keeps halted/resuming per hart, padded to two slots with one
    # hart, and indexes them with the hart id a hart writes. Over SBA the id
    # can be 1: halted then resuming for hart 1, then a resume request
    # selected on hart 1 clears its resuming flag. None of it may touch hart
    # 0. dmstatus is not read while hart 1 is selected (RTL-008).
    def tc_dmc_009():
        dm.t.write(SBDATA1, 0)                   # 64-bit bus: keep the upper half 0
        dm.write_mem32(DM_HALTED, 1)
        dm.write_mem32(DM_RESUMING, 1)
        dm.t.write(DMI.DMCONTROL, (1 << 16) | 1)                       # hartsel=1
        dm.t.write(DMI.DMCONTROL, (1 << DMC_RESUMEREQ) | (1 << 16) | 1)
        dm.t.write(DMI.DMCONTROL, (1 << 16) | 1)
        dm.select_hart(0)
        halted = dm.is_halted()
        return StepResult(
            ok=halted,
            msg=f"TC-DMC-009: hart-1 halted/resuming slots driven over SBA; "
                f"hart 0 still halted={halted}  "
                + ("OK" if halted else "hart 0 disturbed by another hart's state"),
        )

    # ── TC-DMC-010: abstract-command program walk ─────────────────────────
    # dm_mem builds each command's program from regno and aarsize, and toggle
    # coverage on that program showed which operand bits no command ever
    # set. This walks every regno bit in the CSR, GPR and FPR spaces, both
    # sizes, reads and writes, plus an unsupported size and transfer with
    # postexec. Writes put back the value just read (so the hart is
    # unchanged) and are attempted even where the read failed, only at
    # aarsize=3: a 32-bit write sign-extends into a 64-bit
    # register, which would corrupt sp. The 32-bit write program differs only
    # in its size field, which other steps already vary. A register that does
    # not exist answers cmderr=3, which is fine here -- the program is built
    # either way.
    WALK_REGNOS = ([1 << k for k in range(12)] + [0xFFF]
                   + [0x1000 | (1 << k) for k in range(5)] + [0x101F]
                   + [0x1020 | (1 << k) for k in range(5)] + [0x103F])

    def tc_dmc_010():
        errors = {}
        for size in (2, 3):
            for regno in WALK_REGNOS:
                base = (size << 20) | (1 << 17) | regno
                rerr = _abstract(base)
                # A register the read could not reach will refuse the write
                # too, so the attempt is harmless -- and its program still
                # carries the regno bits (CSR 0x004/0x040/0x800 exist only
                # there).
                werr = _abstract(base | (1 << 16)) if size == 3 else None
                errors[(size, regno)] = (rerr, werr)
        odd_size = _abstract((4 << 20) | (1 << 17) | 0x1005)     # 128-bit: unsupported
        dm.write_progbuf(0, EBREAK)
        postexec = _abstract((3 << 20) | (1 << 18) | (1 << 17) | 0x1005)
        gpr_ok = all(errors[(s, r)] == (0, 0 if s == 3 else None) for s in (2, 3)
                     for r in WALK_REGNOS if 0x1000 < r <= 0x101F)
        ok = gpr_ok and odd_size == 2 and postexec == 0 and dm.is_halted()
        failed = sum(1 for e in errors.values() if e[0])
        return StepResult(
            ok=ok,
            msg=f"TC-DMC-010: {2 * len(WALK_REGNOS)} regno/size reads (+ write-backs); "
                f"{failed} answered cmderr (nonexistent CSR/FPR -- expected); every "
                f"GPR round-tripped={gpr_ok}; aarsize=4 -> cmderr={odd_size} (expect 2); "
                f"transfer+postexec -> cmderr={postexec} (expect 0)  "
                + ("OK" if ok else "unexpected command result"),
        )
    session.add_step("TC-DMC-010: abstract-command program walk", tc_dmc_010)

    # ── TC-DMC-003: DMI access while a system bus access is busy ──────────
    # Spec #3.10: sbbusyerror is set when the debugger "attempts to read data
    # while a read is in progress, or ... starts a new access while one is
    # already in progress", and while it is set further sbaddress/sbdata
    # accesses are ignored. Every refused access below is written with the
    # value the register already holds, so a refusal is invisible to the
    # reference model, which does not model sbbusy.
    def tc_dmc_003():
        dm.resume()                       # a halted hart stays "halted" through ndmreset
        dm.t.write(DMI.SBCS, _sbcs_read_on_addr())
        dm.ndmreset(True)
        dm.t.write(DMI.SBADDRESS0, STALL_ADDR)      # starts a read the bus cannot answer
        busy = dm.t.read(DMI.SBCS)
        dm.t.write(DMI.SBCS, _sbcs_read_on_addr())  # sbcs write while busy
        dm.t.read(SBDATA1)                          # sbdata1 read while busy
        dm.t.write(SBADDRESS1, 0)                   # sbaddress1 write while busy
        dm.t.write(SBDATA1, 0)                      # sbdata1 write while busy
        after = dm.t.read(DMI.SBCS)
        was_busy = bool((busy >> SB_BUSY) & 1)
        flagged  = bool((after >> SB_BUSYERROR) & 1)
        ok = was_busy and flagged
        return StepResult(
            ok=ok,
            msg=f"TC-DMC-003: under ndmreset sbcs=0x{busy:08x} (sbbusy={int(was_busy)}), "
                f"after four accesses sbcs=0x{after:08x} (sbbusyerror={int(flagged)})  "
                + ("OK" if ok else "transfer did not stall, or busy access not flagged"),
        )
    session.add_step("TC-DMC-003: DMI access while sbbusy", tc_dmc_003)

    # ── TC-DMC-004: the DM stays consistent once ndmreset is released ─────
    # The stalled transfer does not complete. The crossbar is reset by
    # ndmreset_n and the DM's AXI master by power-on reset only
    # (ariane_testharness.sv), so the request made during ndmreset is lost and
    # the master waits for a response that never comes. That is a property of
    # this testharness, not of the DM, and it leaves SBA busy until power-on
    # reset -- which is why this scenario runs it last.
    #
    # What the DM still owes: sbcs must tell the truth about it. While sbbusy
    # is set, a W1C of sbbusyerror is itself an access during a busy transfer
    # and must be refused (#3.10); once sbbusy clears the same write must
    # clear it. And run control, which does not use the bus, must still work.
    def tc_dmc_004():
        dm.ndmreset(False)
        dm.ackhavereset()
        busy_now = bool((dm.t.read(DMI.SBCS) >> SB_BUSY) & 1)
        dm.t.write(DMI.SBCS, (1 << SB_BUSYERROR) | (0x7 << SB_ERROR_LSB)
                   | _sbcs_read_on_addr())
        after = dm.t.read(DMI.SBCS)
        busyerr = bool((after >> SB_BUSYERROR) & 1)
        consistent = busyerr == busy_now
        # dmactive=0 resets the DM's own state (#3.14.2), sbcs included, so
        # it is the debugger's way out of a sticky sbbusyerror it cannot W1C.
        dm.deactivate()
        dm.activate()
        reset_err = (dm.t.read(DMI.SBCS) >> SB_BUSYERROR) & 1
        dm.halt()
        ok = consistent and not reset_err and dm.is_halted()
        return StepResult(
            ok=ok,
            msg=f"TC-DMC-004: after release sbbusy={int(busy_now)} "
                f"({'transfer lost with the crossbar reset' if busy_now else 'transfer completed'}); "
                f"W1C of sbbusyerror {'refused' if busyerr else 'applied'} (sbcs=0x{after:08x}); "
                f"after dmactive cycle sbbusyerror={reset_err}; hart halts={dm.is_halted()}  "
                + ("OK" if ok else "sbcs inconsistent, not reset by dmactive, or run control lost"),
        )
    session.add_step("TC-DMC-004: DM consistent after ndmreset release", tc_dmc_004)

    # ── The nonexistent-hart steps, last ───────────────────────────────────
    # Both select a hartsel with no hart behind it, which is RTL-003: the DM
    # reports allnonexistent=1 AND allrunning=1, the model reports the hart as
    # not running, and the checker's UVM_ERROR ends the run (quit count 1).
    # Run first, as they used to be, they aborted the scenario at its second
    # step and every corner below this line went unexercised -- on Ibex that
    # alone accounted for the haltsum1-3 and sbbusy blocks showing as
    # uncovered. A known defect should cost its own steps, not the whole
    # scenario.
    session.add_step("TC-DMC-001: flag poll with a nonexistent hart selected", tc_dmc_001)
    session.add_step("TC-DMC-009: another hart's state slots", tc_dmc_009)

    return session
