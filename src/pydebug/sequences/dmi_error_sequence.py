"""
sequences/dmi_error_sequence.py — DTM sticky-error and reset recovery.

Spec #6.1.4: the DTM latches a sticky error in `dtmcs.dmistat`. Once set, every
subsequent DMI access returns the error and is otherwise ignored until the
debugger writes `dtmcs.dmireset`. `dmihardreset` additionally cancels any
outstanding transaction.

Nothing exercised the DTM's own registers, because `dtmcs` has no DMI address —
it is reached through JTAG IR 0x10, which the transport did not expose. Every
error-recovery path in `dmi_jtag.sv` was therefore dead: the `DMIBusy` arms, the
`dmi_reset` handler, request back-pressure, and `test_logic_reset`.

That is also the same hole as the unfilled `cp_dmi_result.failed` / `.busy`
functional bins — one test closes both.

TC-DTM-011 hammers the DMI through the normal read path, which cannot provoke
busy: every access scans the IR first, and that alone gives the DTM time to
finish. TC-DTM-015 uses a raw DR-only scan instead, so busy is provoked on
purpose and asserted rather than hoped for.

`idcode` is the implementation's IDCODE. The default is dmi_jtag's own
parameter default, which ariane_testharness does not override.

Traces to: TC-DTM-002 (IDCODE), TC-DTM-010 (dtmcs discovery), TC-DTM-011
(sticky error + dmireset), TC-DTM-012 (dmihardreset), TC-DTM-013
(unimplemented address), TC-DTM-014 (TAP reset recovery), TC-DTM-015
(provoked busy is sticky), TC-DTM-017 (BYPASS), TC-DTM-018 (dtmcs R/O bits),
TC-DTM-019 (every TAP transition).
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import DMI

#: dtmcs fields (spec #6.1.4).
DTMCS_DMIHARDRESET = 1 << 17
DTMCS_DMIRESET     = 1 << 16
DTMCS_IDLE_LSB     = 12
DTMCS_DMISTAT_LSB  = 10
DTMCS_ABITS_LSB    = 4
DTMCS_VERSION_MASK = 0xF

#: An address with no register behind it. Reading it exercises the DM's
#: `default:` decode arm, which nothing else reaches.
UNIMPLEMENTED_DMI_ADDR = 0x2F


def _decode(dtmcs: int) -> str:
    return (f"version={dtmcs & DTMCS_VERSION_MASK} "
            f"abits={(dtmcs >> DTMCS_ABITS_LSB) & 0x3F} "
            f"dmistat={(dtmcs >> DTMCS_DMISTAT_LSB) & 0x3} "
            f"idle={(dtmcs >> DTMCS_IDLE_LSB) & 0x7}")


def build_dmi_error_sequence(dm: RISCVDebug, mode: str = "batch",
                             idcode: int = 0x00000001) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)

    has_dtmcs = hasattr(dm.t, "dtmcs")

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-DTM-010: dtmcs discovery ───────────────────────────────────────
    def tc_dtm_010():
        if not has_dtmcs:
            return StepResult(ok=True, msg="TC-DTM-010: N/A -- transport has no dtmcs access")
        v = dm.t.dtmcs()
        # version 1 == spec 1.0; abits must cover the 7-bit DMI address space.
        ok = (v & DTMCS_VERSION_MASK) == 1 and ((v >> DTMCS_ABITS_LSB) & 0x3F) >= 7
        return StepResult(
            ok=ok, msg=f"TC-DTM-010: dtmcs=0x{v:08x} ({_decode(v)})  "
                       f"{'OK' if ok else 'unexpected version/abits'}")
    session.add_step("TC-DTM-010: dtmcs discovery", tc_dtm_010)

    # ── TC-DTM-011: sticky error, then dmireset clears it ─────────────────
    def tc_dtm_011():
        if not has_dtmcs:
            return StepResult(ok=True, msg="TC-DTM-011: N/A -- no dtmcs access")
        # Hammer the DMI with no idle cycles between accesses. Whether this
        # actually provokes busy depends on how fast the DM drains relative to
        # JTAG; a DM that keeps up is not wrong. What must hold is that
        # whatever state results is clearable and the DTM still works after.
        for _ in range(12):
            dm.t.read(DMI.DMSTATUS)
            dm.t.read(DMI.ABSTRACTCS)
        before = dm.t.dtmcs()
        stat_before = (before >> DTMCS_DMISTAT_LSB) & 0x3
        dm.t.dtmcs(DTMCS_DMIRESET)
        after = dm.t.dtmcs()
        stat_after = (after >> DTMCS_DMISTAT_LSB) & 0x3
        usable = dm.t.read(DMI.DMSTATUS) != 0
        ok = stat_after == 0 and usable
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-011: dmistat before={stat_before}, after dmireset="
                f"{stat_after}, DMI usable={usable}  "
                f"{'OK' if ok else 'dmireset did not restore the DTM'}")
    session.add_step("TC-DTM-011: sticky error cleared by dmireset", tc_dtm_011)

    has_scan = has_dtmcs and hasattr(dm.t, "dmi_scan")

    def _provoke_busy():
        """Queue a DMI read and scan again three TCK edges later (TC-DTM-015)."""
        dm.t.read(DMI.DMSTATUS)          # leaves the IR on DMI, the DTM idle
        return (dm.t.dmi_scan(dm.t.DMI_READ, DMI.DMSTATUS),
                dm.t.dmi_scan(dm.t.DMI_NOP),
                dm.t.dmi_scan(dm.t.DMI_NOP))

    def _dmistat():
        return (dm.t.dtmcs() >> DTMCS_DMISTAT_LSB) & 0x3

    # ── TC-DTM-012: dmihardreset clears a sticky error on its own ─────────
    # Spec #6.1.4: dmihardreset "does a hard reset of the DTM, causing the DTM
    # to forget about any outstanding DMI transactions, and returning all
    # registers and internal state to their reset value". An earlier version
    # wrote it with no error pending and checked dmistat=0, which a DTM that
    # ignores the bit also satisfies. Here a busy error is pending first, and
    # only dmihardreset is written. Fails today: RTL-009.
    def tc_dtm_012():
        if not has_scan:
            return StepResult(ok=True, msg="TC-DTM-012: N/A -- no raw DMI scan")
        scans = _provoke_busy()
        before = _dmistat()
        dm.t.dtmcs(DTMCS_DMIHARDRESET)
        after = _dmistat()
        dm.t.dtmcs(DTMCS_DMIRESET)       # recover either way, so later steps run
        dmcontrol = dm.t.read(DMI.DMCONTROL)
        dm_kept = (dmcontrol & 1) == 1
        ok = before == 3 and after == 0 and dm_kept
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-012: scans {scans[0]}/{scans[1]}/{scans[2]}, dmistat={before} "
                f"before dmihardreset, {after} after (expect 0); dmactive kept={dm_kept}  "
                + ("OK" if ok else
                   "dmihardreset did not clear the DTM -- RTL-009" if after else
                   "busy not provoked, or DM state lost"))
    session.add_step("TC-DTM-012: dmihardreset clears a pending error", tc_dtm_012)

    # ── TC-DTM-002: IDCODE ────────────────────────────────────────────────
    # Spec #6.1.2 / IEEE 1149.1: IDCODE is a 32-bit register with bit 0 set.
    # Its value is the implementation's; this build's is `idcode`. Read twice,
    # the second time through Pause-IR/Pause-DR, which no other scan visits.
    def tc_dtm_002():
        if not hasattr(dm.t, "jtag_scan"):
            return StepResult(ok=True, msg="TC-DTM-002: N/A -- transport has no raw JTAG scan")
        plain = dm.t.jtag_scan(dm.t.IR_IDCODE, 32)
        paused = dm.t.jtag_scan(dm.t.IR_IDCODE, 32, data=0xFFFFFFFF, pause=True)
        ok = plain == idcode and paused == idcode and plain & 1
        return StepResult(
            ok=bool(ok),
            msg=f"TC-DTM-002: IDCODE 0x{plain:08x}, through Pause 0x{paused:08x} "
                f"(expect 0x{idcode:08x}, bit 0 set)  " + ("OK" if ok else "IDCODE wrong"))
    session.add_step("TC-DTM-002: IDCODE, plain and through Pause", tc_dtm_002)

    # ── TC-DTM-017: BYPASS, both encodings ────────────────────────────────
    # IEEE 1149.1: BYPASS is one bit that captures 0, so the bits shifted out
    # are 0 followed by the bits shifted in, delayed by one. The spec reserves
    # 0x00 and 0x1f for it.
    def tc_dtm_017():
        if not hasattr(dm.t, "jtag_scan"):
            return StepResult(ok=True, msg="TC-DTM-017: N/A -- transport has no raw JTAG scan")
        pattern = 0xB4
        expect = (pattern << 1) & 0xFF
        got = {ir: dm.t.jtag_scan(ir, 8, data=pattern, pause=(ir == dm.t.IR_BYPASS0))
               for ir in (dm.t.IR_BYPASS0, dm.t.IR_BYPASS1)}
        ok = all(v == expect for v in got.values())
        return StepResult(
            ok=ok,
            msg="TC-DTM-017: " + ", ".join(f"IR 0x{ir:02x} -> 0x{v:02x}" for ir, v in got.items())
                + f" (expect 0x{expect:02x})  " + ("OK" if ok else "BYPASS is not a 1-bit delay"))
    session.add_step("TC-DTM-017: BYPASS through IR 0x00 and 0x1f", tc_dtm_017)

    # ── TC-DTM-019: every TAP transition ──────────────────────────────────
    # IEEE 1149.1 gives every TAP state two exits. Scans only ever take the
    # direct ones, so a DR/IR of zero length, a shift resumed from Exit2 and
    # Update going straight to Select-DR had never happened. One walk takes
    # all of them, with BYPASS selected so its Update-DRs are harmless, and
    # shifts five 1s through IR on the way so BYPASS is still selected after.
    TAP_WALK = (
        [1, 0, 1, 0, 1, 0, 1, 1]    # Select, Capture, Exit1, Pause, Exit2, Shift, Exit1, Update DR
        + [1]                       # Update-DR -> Select-DR
        + [1, 0, 1, 0, 1, 0]        # Select, Capture, Exit1, Pause, Exit2, Shift IR
        + [0, 0, 0, 0, 1]           # five IR shifts of TDI=1, out to Exit1-IR
        + [0, 1, 1]                 # Pause, Exit2, Update IR (IR = 0x1f, BYPASS)
        + [1]                       # Update-IR -> Select-DR
        + [0, 0, 1, 1]              # Capture, Shift, Exit1, Update DR
        + [0]                       # Run-Test/Idle
    )

    def tc_dtm_019():
        if not hasattr(dm.t, "tms_walk"):
            return StepResult(ok=True, msg="TC-DTM-019: N/A -- transport has no TMS walk")
        dm.t.jtag_scan(dm.t.IR_BYPASS1, 1)
        dm.t.tms_walk(TAP_WALK)
        # The driver tracks the TAP state itself (and flags a walk that does
        # not end in Run-Test/Idle). If the walk had left the TAP anywhere
        # else, this scan would shift garbage rather than a 1-bit delay.
        after = dm.t.jtag_scan(dm.t.IR_BYPASS1, 8, data=0xB4)
        usable = dm.t.read(DMI.DMSTATUS) != 0
        ok = after == 0x68 and usable
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-019: {len(TAP_WALK)}-clock TMS walk through every TAP arc; "
                f"BYPASS afterwards -> 0x{after:02x} (expect 0x68), DMI usable={usable}  "
                + ("OK" if ok else "TAP not where the walk should have left it"))
    session.add_step("TC-DTM-019: every TAP transition", tc_dtm_019)

    # ── TC-DTM-018: dtmcs reserved and read-only bits take any shift ──────
    # Writing 1s to dtmcs's reserved and read-only fields must change nothing:
    # the next capture reads the same value.
    def tc_dtm_018():
        if not has_dtmcs:
            return StepResult(ok=True, msg="TC-DTM-018: N/A -- no dtmcs access")
        before = dm.t.dtmcs()
        dm.t.dtmcs(0xFFFFFFFF & ~(DTMCS_DMIHARDRESET | DTMCS_DMIRESET))
        after = dm.t.dtmcs()
        ok = after == before
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-018: dtmcs 0x{before:08x} -> 0x{after:08x} after shifting "
                f"all-ones into its non-control bits  " + ("OK" if ok else "dtmcs changed"))
    session.add_step("TC-DTM-018: dtmcs ignores writes to R/O and reserved bits", tc_dtm_018)

    # ── TC-DTM-013: unimplemented DMI address ─────────────────────────────
    # The DM's `default:` decode arm. Spec: reads of an unimplemented address
    # return 0 rather than erroring.
    def tc_dtm_013():
        v = dm.t.read(UNIMPLEMENTED_DMI_ADDR)
        still_ok = dm.t.read(DMI.DMSTATUS) != 0
        return StepResult(
            ok=still_ok,
            msg=f"TC-DTM-013: read of unimplemented addr 0x{UNIMPLEMENTED_DMI_ADDR:02x} "
                f"= 0x{v:08x}, DMI still usable={still_ok}  "
                f"{'OK' if still_ok else 'DMI wedged'}")
    session.add_step("TC-DTM-013: unimplemented DMI address", tc_dtm_013)

    # ── TC-DTM-015: provoked busy is sticky until dmireset ────────────────
    # Spec #6.1.5: a scan that arrives before the previous request finished
    # returns dmistat=3, and the error sticks -- later scans return 3 and are
    # ignored -- until dmireset. A raw scan right behind a read is captured
    # three TCK edges later, too soon for the request to cross the CDC and back.
    def tc_dtm_015():
        if not (has_dtmcs and hasattr(dm.t, "dmi_scan")):
            return StepResult(ok=True, msg="TC-DTM-015: N/A -- transport has no raw DMI scan")
        dm.t.read(DMI.DMSTATUS)          # leaves the IR on DMI, the DTM idle
        first  = dm.t.dmi_scan(dm.t.DMI_READ, DMI.DMSTATUS)
        busy   = dm.t.dmi_scan(dm.t.DMI_NOP)
        sticky = dm.t.dmi_scan(dm.t.DMI_NOP)
        # While the error is sticky the DTM ignores every request, so a read
        # and a write here must also come back busy. Chosen so the ignored
        # requests cannot mislead the checker: the read repeats dmstatus (the
        # read that did complete), and the write targets an unmapped address.
        on_read  = dm.t.dmi_scan(dm.t.DMI_READ, DMI.DMSTATUS)
        on_write = dm.t.dmi_scan(dm.t.DMI_WRITE, UNIMPLEMENTED_DMI_ADDR, 0)
        stat   = (dm.t.dtmcs() >> DTMCS_DMISTAT_LSB) & 0x3
        dm.t.dtmcs(DTMCS_DMIRESET)
        after  = (dm.t.dtmcs() >> DTMCS_DMISTAT_LSB) & 0x3
        usable = dm.t.read(DMI.DMSTATUS) != 0
        ok = (first == 0 and busy == 3 and sticky == 3 and on_read == 3
              and on_write == 3 and stat == 3 and after == 0 and usable)
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-015: dmistat per scan {first}/{busy}/{sticky}/{on_read}/{on_write} "
                f"(expect 0/3/3/3/3 -- nop, nop, read, write), "
                f"dtmcs.dmistat={stat} (expect 3), after dmireset={after}, "
                f"DMI usable={usable}  "
                f"{'OK' if ok else 'busy not provoked, not sticky, or not cleared'}")
    session.add_step("TC-DTM-015: provoked busy is sticky until dmireset", tc_dtm_015)

    # ── TC-DTM-014: TAP reset and recover ─────────────────────────────────
    # Drives Test-Logic-Reset. The DTM must come back; dmactive must survive,
    # because a TAP reset is a transport event and the DM is not on the TAP.
    # Runs last: it leaves IDCODE in the IR.
    def tc_dtm_014():
        dm.t.reset()
        v = dm.t.dtmcs() if has_dtmcs else 0
        dmcontrol = dm.t.read(DMI.DMCONTROL)
        ok = (dmcontrol & 1) == 1
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-014: after TAP reset dtmcs=0x{v:08x}, "
                f"dmcontrol=0x{dmcontrol:08x}  "
                f"{'OK -- DM survived a transport reset' if ok else 'dmactive lost'}")
    session.add_step("TC-DTM-014: TAP reset, DM survives", tc_dtm_014)

    return session
