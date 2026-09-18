"""
native_trigger.py — what a trigger with `action=0` does, per Sdtrig.

Native (self-hosted) debug is the case with no debugger attached: triggers are
configured with `action=0`, and when one fires the hart takes an ordinary
breakpoint exception that its own trap handler deals with. This module models
that decision — does this trigger fire on this event, and what does the trap
look like — so a test can state its expectation once and have it checked
against the spec rather than against whatever the DUT happened to do.

What it models, and the rule each part comes from:

- **Which mode enables a trigger.** `m`/`s`/`u` name the privilege the trigger
  is enabled in. For `itrigger`/`etrigger` they name the mode the trap was
  taken *from*, not the mode it is handled in (Sdtrig 5.7.14/5.7.15).
- **Where the breakpoint lands.** `mcontrol6` with an execute match fires
  before the matched instruction, so `xepc` is that instruction and `xtval` is
  its address. `icount` fires before the next instruction in an enabled mode,
  with `xtval` written 0. `itrigger`/`etrigger` fire "after the trap occurs,
  just before the first instruction of the trap handler is executed", so
  `xepc` is the handler's entry and `xtval` is 0.
- **Counting.** `icount.count` decrements only for instructions retired in a
  mode the trigger is enabled in (Sdtrig 5.7.13). CVA6 gets this wrong
  (RTL-014).
- **Re-entrancy.** A hart with `action=0` triggers *should* either suppress
  them in M-mode while `mstatus.MIE`=0, or implement `tcontrol`
  (Sdtrig "Native Triggers"). Which of the two a DUT does is a parameter here,
  because the spec allows either; `NONE` says the DUT does neither, which is
  what CVA6 does (RTL-017).

This is a model of the specification, not of CVA6: where the two disagree the
model follows the spec, and the RTL finding is recorded in
`testplans/results/rtl_findings.md`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from .registers import (
    ETRIGGER,
    ICOUNT,
    ITRIGGER,
    MCONTROL6,
    TRIGGER_ACTION_BREAKPOINT,
    TRIGGER_TYPE_ETRIGGER,
    TRIGGER_TYPE_ICOUNT,
    TRIGGER_TYPE_ITRIGGER,
    TRIGGER_TYPE_MCONTROL6,
    tdata1_type,
)

#: mcause for a breakpoint exception (Privileged spec, table "Machine cause").
CAUSE_BREAKPOINT = 3

PRV_U, PRV_S, PRV_M = 0, 1, 3


class Reentrancy(Enum):
    """How the hart keeps an `action=0` trigger out of its own trap handler."""

    MIE_GATE = "mie"          # option 1: no match or fire in M while MIE=0
    TCONTROL = "tcontrol"     # option 2: tcontrol.mte/mpte
    NONE = "none"             # neither -- a SHOULD the DUT does not meet


class Event(Enum):
    """The kinds of event a native trigger can fire on."""

    EXECUTE = "execute"       # an instruction is about to execute
    LOAD = "load"
    STORE = "store"
    RETIRE = "retire"         # an instruction retired (icount counts these)
    EXCEPTION = "exception"   # a trap was taken (etrigger)
    INTERRUPT = "interrupt"   # an interrupt was taken (itrigger)


@dataclass
class Trigger:
    """One trigger: its tdata1 word and tdata2, decoded on demand."""

    tdata1: int
    tdata2: int = 0
    xlen: int = 64

    @property
    def type(self) -> int:
        return tdata1_type(self.tdata1, self.xlen)

    @property
    def fields(self) -> Dict[str, int]:
        layout = {TRIGGER_TYPE_MCONTROL6: MCONTROL6, TRIGGER_TYPE_ICOUNT: ICOUNT,
                  TRIGGER_TYPE_ITRIGGER: ITRIGGER,
                  TRIGGER_TYPE_ETRIGGER: ETRIGGER}.get(self.type)
        return layout.decode(self.tdata1) if layout else {}

    def enabled_in(self, prv: int) -> bool:
        f = self.fields
        return bool(f.get({PRV_M: "m", PRV_S: "s", PRV_U: "u"}[prv], 0))


@dataclass
class Fire:
    """What a firing trigger does to the hart, as a trap handler would see it."""

    trigger: int                  # which trigger index fired
    cause: int = CAUSE_BREAKPOINT
    epc: int = 0                  # xepc the handler will see
    tval: int = 0                 # xtval the handler will see
    why: str = ""

    def __bool__(self) -> bool:   # a Fire is truthy; None means "did not fire"
        return True


@dataclass
class NativeTriggerModel:
    """The trigger module's native (`action=0`) behaviour for one hart.

    Usage: configure triggers, then call `event()` for each thing the hart does
    and act on the returned `Fire` (or `None`).
    """

    reentrancy: Reentrancy = Reentrancy.MIE_GATE
    triggers: Dict[int, Trigger] = field(default_factory=dict)
    #: Set by the model when an icount trigger's count reaches 0.
    pending: Dict[int, bool] = field(default_factory=dict)

    def configure(self, index: int, tdata1: int, tdata2: int = 0, xlen: int = 64) -> None:
        self.triggers[index] = Trigger(tdata1, tdata2, xlen)
        self.pending[index] = False

    # ── the rule the whole thing turns on ────────────────────────────────────
    def _suppressed(self, prv: int, mie: bool, mte: bool) -> bool:
        """Is an action=0 trigger kept out of the trap handler right now?

        Sdtrig "Native Triggers": a hart should implement one of two
        protections. Both of them stop a trigger firing inside the handler that
        its own breakpoint would re-enter.
        """
        if self.reentrancy is Reentrancy.MIE_GATE:
            return prv == PRV_M and not mie
        if self.reentrancy is Reentrancy.TCONTROL:
            return not mte
        return False

    def event(
        self,
        kind: Event,
        prv: int,
        *,
        pc: int = 0,
        address: int = 0,
        cause: int = 0,
        handler: int = 0,
        next_pc: int = 0,
        mie: bool = True,
        mte: bool = True,
    ) -> Optional[Fire]:
        """The first trigger that fires on this event, or None.

        `pc` is the instruction being executed, `address` the data address of a
        load/store, `cause` the exception/interrupt code, `handler` the trap
        vector an itrigger/etrigger's breakpoint will report, and `next_pc` the
        instruction an icount fires before.
        """
        if self._suppressed(prv, mie, mte):
            return None
        for index in sorted(self.triggers):
            fire = self._one(index, kind, prv, pc, address, cause, handler, next_pc)
            if fire:
                return fire
        return None

    def _one(self, index, kind, prv, pc, address, cause, handler, next_pc):
        t = self.triggers[index]
        f = t.fields
        if f.get("action", TRIGGER_ACTION_BREAKPOINT) != TRIGGER_ACTION_BREAKPOINT:
            return None                      # action=1 is Debug Mode, not native

        if t.type == TRIGGER_TYPE_MCONTROL6:
            want = {Event.EXECUTE: "execute", Event.LOAD: "load",
                    Event.STORE: "store"}.get(kind)
            if not want or not f.get(want) or not t.enabled_in(prv):
                return None
            value = pc if kind is Event.EXECUTE else address
            if value != t.tdata2:
                return None
            # An address match fires before the instruction, so the handler
            # sees the matched instruction in xepc and its address in xtval.
            return Fire(index, epc=pc, tval=value,
                        why=f"mcontrol6 {want} match on 0x{value:x}")

        if t.type == TRIGGER_TYPE_ICOUNT:
            if kind is not Event.RETIRE:
                return None
            if not t.enabled_in(prv):
                return None                  # counts only in enabled modes
            count = f.get("count", 0)
            if count > 0:
                count -= 1
                t.tdata1 = ICOUNT.field("count").insert(
                    t.tdata1 & ~ICOUNT.field("count").mask, count)
                # pending is set when count decrements FROM 1 TO 0, and count
                # then "stays at 0 until explicitly written" (Sdtrig 5.7.13):
                # once fired, the trigger does not re-arm itself.
                if count == 0:
                    self.pending[index] = True
            if not self.pending[index]:
                return None
            self.pending[index] = False
            # Fires just before the next instruction in an enabled mode, and
            # writes zero to tval (Sdtrig 5.7.13).
            return Fire(index, epc=next_pc, tval=0,
                        why="icount reached 0")

        if t.type in (TRIGGER_TYPE_ITRIGGER, TRIGGER_TYPE_ETRIGGER):
            want = (Event.INTERRUPT if t.type == TRIGGER_TYPE_ITRIGGER
                    else Event.EXCEPTION)
            if kind is not want or not t.enabled_in(prv):
                return None                  # prv is the mode the trap came FROM
            if not (t.tdata2 >> cause) & 1:
                return None
            # Fires after the trap is taken, before the handler's first
            # instruction, with zero written to tval.
            return Fire(index, epc=handler, tval=0,
                        why=f"{'itrigger' if want is Event.INTERRUPT else 'etrigger'}"
                            f" on cause {cause}")
        return None
