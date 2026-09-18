"""
test_native_trigger_model.py — the native-trigger model against the spec.

Each test states the same expectation the corresponding firmware program
(`cva6_sim/sw/native_*.S`) checks on real hardware, so the two cannot drift:
the program says what the DUT did, this says what Sdtrig requires. Where CVA6
disagrees, the RTL finding is named in the test's docstring — the model follows
the spec, not the DUT.
"""

import pytest

from pydebug.model.native_trigger import (
    CAUSE_BREAKPOINT,
    Event,
    NativeTriggerModel,
    PRV_M,
    PRV_S,
    PRV_U,
    Reentrancy,
)
from pydebug.model.registers import (
    ETRIGGER,
    ICOUNT,
    ITRIGGER,
    MCONTROL6,
    TRIGGER_TYPE_ETRIGGER,
    TRIGGER_TYPE_ICOUNT,
    TRIGGER_TYPE_ITRIGGER,
    TRIGGER_TYPE_MCONTROL6,
)

pytestmark = pytest.mark.feature("coverage_model")

TYPE64 = 60


def mcontrol6(**f) -> int:
    return (TRIGGER_TYPE_MCONTROL6 << TYPE64) | MCONTROL6.encode(**f)


def icount(**f) -> int:
    return (TRIGGER_TYPE_ICOUNT << TYPE64) | ICOUNT.encode(**f)


def itrigger(**f) -> int:
    return (TRIGGER_TYPE_ITRIGGER << TYPE64) | ITRIGGER.encode(**f)


def etrigger(**f) -> int:
    return (TRIGGER_TYPE_ETRIGGER << TYPE64) | ETRIGGER.encode(**f)


@pytest.mark.smoke
def test_execute_trigger_fires_before_the_matched_instruction():
    """mcontrol6 execute: xepc is the matched instruction, xtval its address.

    Mirrors `native_hit.S`, which also checks that only the trigger that fired
    has its hit bits set.
    """
    m = NativeTriggerModel()
    m.configure(0, mcontrol6(u=1, execute=1), 0x8000_0100)
    fire = m.event(Event.EXECUTE, PRV_U, pc=0x8000_0100)
    assert fire and fire.cause == CAUSE_BREAKPOINT
    assert fire.epc == 0x8000_0100 and fire.tval == 0x8000_0100
    assert m.event(Event.EXECUTE, PRV_U, pc=0x8000_0104) is None


def test_a_trigger_is_enabled_per_privilege():
    """The m/s/u bits gate matching; a U-only trigger ignores M-mode."""
    m = NativeTriggerModel()
    m.configure(0, mcontrol6(u=1, execute=1), 0x8000_0100)
    assert m.event(Event.EXECUTE, PRV_M, pc=0x8000_0100) is None
    assert m.event(Event.EXECUTE, PRV_S, pc=0x8000_0100) is None
    assert m.event(Event.EXECUTE, PRV_U, pc=0x8000_0100)


def test_store_trigger_matches_the_data_address():
    m = NativeTriggerModel()
    m.configure(0, mcontrol6(m=1, store=1), 0x8000_c000)
    assert m.event(Event.STORE, PRV_M, address=0x8000_c000, pc=0x40)
    assert m.event(Event.LOAD, PRV_M, address=0x8000_c000, pc=0x40) is None


def test_icount_counts_only_in_enabled_modes():
    """Sdtrig 5.7.13: the count decrements for instructions retired in a mode
    the trigger is enabled in. CVA6 counts every retirement (RTL-014, #163),
    which is why `native_icount.S` fails on hardware and this does not."""
    m = NativeTriggerModel()
    m.configure(0, icount(u=1, count=2), 0)
    for _ in range(5):                              # M-mode work: not counted
        assert m.event(Event.RETIRE, PRV_M) is None
    assert m.event(Event.RETIRE, PRV_U) is None     # count 2 -> 1
    fire = m.event(Event.RETIRE, PRV_U, next_pc=0x8000_0208)   # 1 -> 0, fires
    assert fire and fire.epc == 0x8000_0208
    assert fire.tval == 0, "Sdtrig 5.7.13: icount writes zero to tval"


def test_icount_fires_once_and_clears_pending():
    m = NativeTriggerModel()
    m.configure(0, icount(u=1, count=1), 0)
    assert m.event(Event.RETIRE, PRV_U, next_pc=0x10)
    assert m.event(Event.RETIRE, PRV_U, next_pc=0x14) is None


def test_etrigger_fires_at_the_handler_entry():
    """Sdtrig 5.7.15: it fires after the trap occurs, just before the first
    instruction of the handler, with zero in tval. The m/s/u bits name the mode
    the exception was taken FROM. CVA6 never matches in S without textra
    (RTL-015, #164)."""
    m = NativeTriggerModel()
    m.configure(0, etrigger(s=1), 1 << 2)           # illegal instruction
    fire = m.event(Event.EXCEPTION, PRV_S, cause=2, handler=0x8000_0300)
    assert fire and fire.epc == 0x8000_0300 and fire.tval == 0
    assert m.event(Event.EXCEPTION, PRV_U, cause=2, handler=0x8000_0300) is None
    assert m.event(Event.EXCEPTION, PRV_S, cause=5, handler=0x8000_0300) is None


def test_itrigger_fires_at_the_handler_entry():
    """As etrigger, for interrupts. CVA6 fires only when the handler returns
    (RTL-016, #165)."""
    m = NativeTriggerModel()
    m.configure(0, itrigger(u=1), 1 << 1)           # supervisor software interrupt
    fire = m.event(Event.INTERRUPT, PRV_U, cause=1, handler=0x8000_0300)
    assert fire and fire.epc == 0x8000_0300 and fire.tval == 0
    assert m.event(Event.INTERRUPT, PRV_S, cause=1, handler=0x8000_0300) is None


def test_action_1_is_not_a_native_trigger():
    """action=1 enters Debug Mode; this model is the native (action=0) path."""
    m = NativeTriggerModel()
    m.configure(0, mcontrol6(m=1, execute=1, action=1), 0x8000_0100)
    assert m.event(Event.EXECUTE, PRV_M, pc=0x8000_0100) is None


@pytest.mark.parametrize(
    "mode, mie, mte, fires",
    [
        (Reentrancy.MIE_GATE, False, True, False),   # in the handler: suppressed
        (Reentrancy.MIE_GATE, True, True, True),
        (Reentrancy.TCONTROL, False, False, False),  # tcontrol.mte clear
        (Reentrancy.TCONTROL, False, True, True),
        (Reentrancy.NONE, False, True, True),        # neither protection: CVA6
    ],
)
def test_reentrancy_protection(mode, mie, mte, fires):
    """Sdtrig "Native Triggers": a hart supporting action=0 should implement one
    of the two protections. CVA6 implements neither (RTL-017, #166), which the
    NONE row states rather than hides."""
    m = NativeTriggerModel(reentrancy=mode)
    m.configure(0, mcontrol6(m=1, execute=1), 0x8000_0100)
    got = m.event(Event.EXECUTE, PRV_M, pc=0x8000_0100, mie=mie, mte=mte)
    assert bool(got) is fires
