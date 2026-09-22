"""
sequences/hart_array_sequence.py — halting and resuming more than one hart.

Everything here needs a DM with `NrHarts > 1`, which is why none of it has run
before: both SoCs in this project instantiate `dm_top` with one hart, so
`dmstatus`'s all\\*/any\\* pairs cannot differ, `haltsum0` has a single
interesting bit, and the hart array mask is tied off. `multihart_sim` exists for
exactly these rows — `dm_top` with two harts and `dbg_dummy_hart` behind it.

The interesting case throughout is **some but not all**: a debugger that selects
several harts must be able to tell "every selected hart is halted" from "at
least one is", and that distinction is what the `all`/`any` pairs are for. A
single-hart DM answers both the same way forever, so a test written against one
cannot fail in the way this is meant to catch.

Selection works two ways (#3.14.2). `hartsel` names one hart; setting `hasel`
adds every hart whose bit is set in the hart array mask, which is
`hawindow` for the window `hawindowsel` selects. This exercises both, and
checks that a DM which does not implement the mask says so through the
read-back rather than silently ignoring it.

Traces to: TC-HS-007, TC-HS-008, TC-HS-010-V, TC-HALT-010, TC-RES-010

Usage:
    from pydebug.sequences.hart_array_sequence import build_hart_array_sequence
    session = build_hart_array_sequence(dm, mode="batch", num_harts=2)
    session.run()
"""

from pydebug.api import DebugSession, DMI, RISCVDebug, StepResult
from pydebug.api.riscv_dm import (
    allhalted,
    allresumeack,
    allrunning,
    anyhalted,
    anyresumeack,
    anyrunning,
    dmcontrol,
    dmcontrol_hasel,
)
from pydebug.model.registers import HAWINDOW, HAWINDOWSEL, hawindow_of

#: DMI 0x40. Bit i is set iff hart i (in the low 32-hart window) is halted.
HALTSUM0 = 0x40


def _selected(dm, hartsel: int, hasel: bool, **bits) -> None:
    """Write dmcontrol with a selection, keeping dmactive set."""
    dm.t.write(DMI.DMCONTROL,
               dmcontrol(dmactive=True, hartsel=hartsel, hasel=hasel, **bits))


def build_hart_array_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    num_harts: int = 2,
) -> DebugSession:
    """Build a DebugSession exercising multi-hart halt, resume and the hart
    array mask (spec #3.5, #3.14.1, #3.14.2, #3.14.4, #3.14.5).

    Traces to: TC-HS-007, TC-HS-008, TC-HS-010-V, TC-HALT-010, TC-RES-010
    """
    session = DebugSession(mode=mode, stop_on_error=False)
    state = {"hasel": False}
    other = num_harts - 1           # the highest implemented hart index

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-HS-007: the highest implemented hart index exists ──────────────
    def tc_hs_007():
        _selected(dm, other, False)
        word = dm.read_dmstatus()
        nonexistent = bool((word >> 14) & 1)     # anynonexistent
        return StepResult(
            ok=not nonexistent,
            msg=f"TC-HS-007: hartsel={other} (the highest implemented index) -> "
                f"dmstatus=0x{word:08x}, anynonexistent={int(nonexistent)} "
                f"(expect 0: this hart exists)",
        )
    session.add_step(f"TC-HS-007: select hart {other}, the highest implemented",
                     tc_hs_007)

    # ── TC-HALT-010 part 1: halt ONE of several harts ─────────────────────
    # The state the all/any pairs exist to describe. Only reachable with more
    # than one hart, and the reason this sequence has a testbench of its own.
    def tc_halt_010_one():
        _selected(dm, other, False, haltreq=True)
        dm._poll_until(allhalted, DMI.DMSTATUS, "allhalted", dm.DEFAULT_TIMEOUT)
        _selected(dm, other, False)
        summ = dm.t.read(HALTSUM0)
        ok = ((summ >> other) & 1) == 1 and (summ & 1) == 0
        return StepResult(
            ok=ok,
            msg=f"TC-HALT-010: halted hart {other} alone -> haltsum0=0x{summ:08x} "
                f"(bit {other} set, bit 0 clear)  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step(f"TC-HALT-010: halt hart {other} alone", tc_halt_010_one)

    # ── TC-HS-003: the hart array mask, and whether it exists ─────────────
    def tc_hs_003_mask():
        window, bit = hawindow_of(0)             # hart 0 is in window 0, bit 0
        dm.t.write(HAWINDOWSEL.address, window)
        dm.t.write(HAWINDOW.address, 1 << bit)
        read_sel = dm.t.read(HAWINDOWSEL.address)
        read_win = dm.t.read(HAWINDOW.address)
        _selected(dm, other, True)
        state["hasel"] = dmcontrol_hasel(dm.read_dmcontrol())
        return StepResult(
            ok=True,     # discovery: the value is the finding
            msg=f"TC-HS-003: hawindowsel={read_sel} hawindow=0x{read_win:08x}, "
                f"hasel reads back {int(state['hasel'])} -- "
                + ("the mask is implemented, so hart 0 joins the selection"
                   if state["hasel"] and read_win & (1 << bit) else
                   "the hart array mask is NOT implemented on this DM; the "
                   "selection stays a single hart"),
        )
    session.add_step("TC-HS-003: hart array mask discovery", tc_hs_003_mask)

    # ── TC-HS-008 / TC-HS-010-V: some selected harts halted, not all ──────
    def tc_hs_008():
        if not state["hasel"]:
            return StepResult(ok=True, msg="TC-HS-008: N/A -- no hart array mask")
        word = dm.read_dmstatus()
        some_not_all = anyhalted(word) and not allhalted(word)
        running_too = anyrunning(word)
        return StepResult(
            ok=some_not_all and running_too,
            msg=f"TC-HS-008: hart {other} halted, hart 0 running, both selected -> "
                f"dmstatus=0x{word:08x} anyhalted={int(anyhalted(word))} "
                f"allhalted={int(allhalted(word))} anyrunning={int(running_too)} "
                f"allrunning={int(allrunning(word))}  "
                + ("OK -- the all/any pair distinguishes them"
                   if some_not_all and running_too else
                   "MISMATCH: the pair should differ with one hart in each state"),
        )
    session.add_step("TC-HS-008: some selected harts halted, not all", tc_hs_008)

    # ── TC-HALT-010 part 2: halt every selected hart ──────────────────────
    def tc_halt_010_all():
        if not state["hasel"]:
            return StepResult(ok=True, msg="TC-HALT-010: N/A -- no hart array mask")
        _selected(dm, other, True, haltreq=True)
        dm._poll_until(allhalted, DMI.DMSTATUS, "allhalted", dm.DEFAULT_TIMEOUT)
        _selected(dm, other, True)
        word = dm.read_dmstatus()
        summ = dm.t.read(HALTSUM0)
        want = (1 << num_harts) - 1
        ok = allhalted(word) and anyhalted(word) and not anyrunning(word) \
            and (summ & want) == want
        return StepResult(
            ok=ok,
            msg=f"TC-HALT-010: haltreq with both harts selected -> "
                f"allhalted={int(allhalted(word))} anyrunning={int(anyrunning(word))}, "
                f"haltsum0=0x{summ:08x} (expect the low {num_harts} bits set)  "
                + ("OK" if ok else "MISMATCH"),
        )
    session.add_step("TC-HALT-010: halt every selected hart", tc_halt_010_all)

    # ── TC-RES-010: resume every selected hart ────────────────────────────
    def tc_res_010():
        if not state["hasel"]:
            return StepResult(ok=True, msg="TC-RES-010: N/A -- no hart array mask")
        _selected(dm, other, True, resumereq=True)
        dm._poll_until(allrunning, DMI.DMSTATUS, "allrunning", dm.DEFAULT_TIMEOUT)
        _selected(dm, other, True)
        word = dm.read_dmstatus()
        summ = dm.t.read(HALTSUM0)
        ok = (allrunning(word) and allresumeack(word) and anyresumeack(word)
              and not anyhalted(word) and (summ & ((1 << num_harts) - 1)) == 0)
        return StepResult(
            ok=ok,
            msg=f"TC-RES-010: resumereq with both harts selected -> "
                f"allrunning={int(allrunning(word))} "
                f"allresumeack={int(allresumeack(word))} "
                f"anyhalted={int(anyhalted(word))}, haltsum0=0x{summ:08x}  "
                + ("OK" if ok else "MISMATCH"),
        )
    session.add_step("TC-RES-010: resume every selected hart", tc_res_010)

    # ── TC-HALT-010 without the mask: halt each hart in turn ─────────────
    # A debugger on a DM with no hart array mask halts several harts by
    # selecting each and requesting in turn. haltsum0 is then the only place
    # the whole picture appears at once, which is what it is for (#3.14.10).
    def tc_halt_010_each():
        for h in range(num_harts):
            _selected(dm, h, False, haltreq=True)
            dm._poll_until(allhalted, DMI.DMSTATUS, f"hart {h} allhalted",
                           dm.DEFAULT_TIMEOUT)
            _selected(dm, h, False)
        summ = dm.t.read(HALTSUM0)
        want = (1 << num_harts) - 1
        ok = (summ & want) == want
        return StepResult(
            ok=ok,
            msg=f"TC-HALT-010: halted all {num_harts} harts one at a time -> "
                f"haltsum0=0x{summ:08x} (expect the low {num_harts} bits set)  "
                + ("OK" if ok else "MISMATCH"),
        )
    session.add_step("TC-HALT-010: halt every hart, one selection at a time",
                     tc_halt_010_each)

    # ── TC-RES-010 without the mask: resume each hart in turn ────────────
    def tc_res_010_each():
        acks = []
        for h in range(num_harts):
            _selected(dm, h, False, resumereq=True)
            dm._poll_until(allrunning, DMI.DMSTATUS, f"hart {h} allrunning",
                           dm.DEFAULT_TIMEOUT)
            _selected(dm, h, False)
            acks.append(allresumeack(dm.read_dmstatus()))
        summ = dm.t.read(HALTSUM0)
        ok = all(acks) and (summ & ((1 << num_harts) - 1)) == 0
        return StepResult(
            ok=ok,
            msg=f"TC-RES-010: resumed all {num_harts} harts one at a time -> "
                f"resume acks {[int(a) for a in acks]}, haltsum0=0x{summ:08x}  "
                + ("OK" if ok else "MISMATCH"),
        )
    session.add_step("TC-RES-010: resume every hart, one selection at a time",
                     tc_res_010_each)

    # ── TC-HS-008 (the other half): no selected hart in a state ───────────
    # With both harts running, every halted bit must read 0 -- `all` as well as
    # `any`. A DM that computed `all` over an empty set would report 1 here.
    def tc_hs_008_neither():
        _selected(dm, 0, False)
        word = dm.read_dmstatus()
        ok = not anyhalted(word) and not allhalted(word)
        return StepResult(
            ok=ok,
            msg=f"TC-HS-008: with no selected hart halted, allhalted="
                f"{int(allhalted(word))} anyhalted={int(anyhalted(word))} "
                f"(both expect 0)  {'OK' if ok else 'MISMATCH'}",
        )
    session.add_step("TC-HS-008: neither all nor any, with nothing halted",
                     tc_hs_008_neither)

    return session
