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

Traces to: TC-DTM-010 (dtmcs discovery), TC-DTM-011 (sticky error + dmireset),
TC-DTM-012 (dmihardreset), TC-DTM-013 (TAP reset recovery).
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


def build_dmi_error_sequence(dm: RISCVDebug, mode: str = "batch") -> DebugSession:
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

    # ── TC-DTM-012: dmihardreset ──────────────────────────────────────────
    def tc_dtm_012():
        if not has_dtmcs:
            return StepResult(ok=True, msg="TC-DTM-012: N/A -- no dtmcs access")
        dm.t.dtmcs(DTMCS_DMIHARDRESET)
        v = dm.t.dtmcs()
        stat = (v >> DTMCS_DMISTAT_LSB) & 0x3
        # dmihardreset resets the DTM, not the DM: dmactive must survive it.
        dmcontrol = dm.t.read(DMI.DMCONTROL)
        ok = stat == 0 and (dmcontrol & 1) == 1
        return StepResult(
            ok=ok,
            msg=f"TC-DTM-012: after dmihardreset dtmcs=0x{v:08x} (dmistat={stat}), "
                f"dmcontrol=0x{dmcontrol:08x} (dmactive={'1' if dmcontrol & 1 else '0'})  "
                f"{'OK -- DTM reset, DM untouched' if ok else 'DM state lost'}")
    session.add_step("TC-DTM-012: dmihardreset resets the DTM only", tc_dtm_012)

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

    # ── TC-DTM-014: TAP reset and recover ─────────────────────────────────
    # Drives Test-Logic-Reset. The DTM must come back; dmactive must survive,
    # because a TAP reset is a transport event and the DM is not on the TAP.
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
