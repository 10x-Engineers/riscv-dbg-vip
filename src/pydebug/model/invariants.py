"""
invariants.py — Architectural invariants of the dmcontrol/dmstatus run-control slice.

An invariant here is a statement the RISC-V Debug Specification makes about *every*
legal implementation. If one is violated, either the DUT is wrong, the stimulus is
illegal, or `predictor.py` is wrong — never "the DUT is just different". That is the
whole point of the split from `predictor.py`: the predictor says what this model
*predicts*, and where the spec allows latitude it exposes that latitude as a
constructor knob. This module only says what the spec *mandates*, so a violation is
always a real finding.

Scope: dmcontrol (0x10) / dmstatus (0x11) run control only — spec #3.5 Run Control,
#3.2 Reset, #3.14.1 dmstatus, #3.14.2 dmcontrol. Abstract commands, the Program
Buffer, SBA, triggers and authentication are deliberately out of scope; nothing here
asserts on them.


Calling convention
------------------
`check_all()` is designed to be driven from `ObservingTransport`, whose callback is
`callback(op, addr, data, readback)` and fires *after* the operation has completed.
The predictor has therefore already absorbed the write by the time an observer runs,
so the observer must have captured the *pre*-transaction state itself:

    from pydebug.api.observer import ObservingTransport
    from pydebug.model.invariants import check_all

    t = ObservingTransport(ModelBackedMockTransport())
    predictor = t.delegate.predictor
    pending = {}

    def before(op, addr):                     # call right before each transport op
        pending["prev"] = predictor.snapshot()

    def observe(op, addr, data, readback):    # ObservingTransport callback
        for v in check_all(pending["prev"], op, addr, data, readback, predictor):
            log.error("%s", v)                # caller decides severity

    t.add_observer(observe)

`prev_state` is a `predictor.snapshot()` dict taken before the transaction; the
`predictor` argument is the live model, already updated, i.e. the *post* state. Both
are needed: every "X is ignored when Y" rule in #3.5 is a statement about a
transition, not about a state, and cannot be checked from either end alone.

`check_all()` returns a list of `Violation` and **never raises**. Severity is the
caller's decision: a UVM test may want `uvm_error`, a bring-up script may want a
warning, and the negative tests (TC-HOR-005) deliberately provoke a violation and
must be able to observe it as data rather than as an exception.


Two kinds of check
------------------
Most invariants are *DUT* checks: the implementation must behave this way.
A few are *stimulus-legality* checks: the spec constrains what a debugger may do,
so a violation means our own stimulus is illegal, not that the DUT is broken. Those
are marked `stimulus_legality=True` on the Violation so a scoreboard can route them
differently (and so TC-HOR-005, which is *built* on violating one, can assert that it
fired rather than treating it as a failure).


Deliberately NOT asserted (spec-sanctioned latitude)
----------------------------------------------------
See `UNSPECIFIED_BEHAVIOURS` at the bottom of this module. Asserting on any of them
would manufacture failures against perfectly conformant implementations. Each entry
names the spec sentence that grants the latitude. This list is part of the
deliverable: "we chose not to check this, and here is the spec's permission" is a
verification result, not an omission.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .registers import (
    ACCESS_READS_ZERO,
    DMCONTROL,
    DMCONTROL_MUTEX_BITS,
    DMSTATUS,
    DMSTATUS_ALL_ANY_PAIRS,
    DMSTATUS_VERSION_NONE,
)

log = logging.getLogger(__name__)


# ── Violation ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Violation:
    """One architectural rule, broken, with everything needed to triage it.

    `rule` is a stable identifier (INV-*) so a regression can be grepped for and a
    waiver can name it. `tc_ids` closes the loop back to the test plan: every
    invariant exists because some TC-ID's "Expected Result / Check" column demands
    it, and every violation therefore names the test cases it invalidates.
    """

    rule: str
    message: str
    #: Test-plan TC-IDs whose Expected Result/Check clause this invariant backs.
    tc_ids: Tuple[str, ...]
    #: Spec citation — the sentence that makes this a rule rather than a preference.
    spec: str
    observed: Any = None
    expected: Any = None
    #: Which hart the violation is about, where that is meaningful.
    hart: Optional[int] = None
    #: True when the violation means *our stimulus* was illegal, not that the DUT
    #: misbehaved. See "Two kinds of check" in the module docstring.
    stimulus_legality: bool = False

    def __str__(self) -> str:
        where = "" if self.hart is None else f" [hart {self.hart}]"
        kind = "stimulus-legality" if self.stimulus_legality else "DUT"
        detail = ""
        if self.observed is not None or self.expected is not None:
            detail = f" (observed={self.observed!r}, expected={self.expected!r})"
        return (
            f"{self.rule}{where} [{kind}] {self.message}{detail} "
            f"— spec {self.spec}; backs {', '.join(self.tc_ids)}"
        )


# ── Small helpers over snapshot dicts ─────────────────────────────────────────
#
# `predictor.snapshot()` is deliberately plain data (no HartState references), so a
# snapshot taken before a transaction stays frozen while the model moves on. These
# helpers read that shape without duplicating knowledge of it.


def _hart(state: Optional[Dict[str, Any]], index: int) -> Optional[Dict[str, Any]]:
    """The per-hart sub-dict of a snapshot, or None if unavailable.

    `state` may legitimately be None: a caller that starts observing partway
    through a session has no prior snapshot for its first transaction. Returning
    None there makes the edge invariants (the "#3.5 X is ignored when Y" family)
    skip that one transaction rather than crash, which keeps check_all's "never
    raises" contract honest for a caller that cannot supply a prior state.
    """
    harts = (state or {}).get("harts") or []
    if 0 <= index < len(harts):
        return harts[index]
    return None


def _in_reset(hart: Dict[str, Any]) -> bool:
    """A hart held in reset reports neither halted nor running.

    #3.2: "While the reset is on-going, harts are either in the running state ... or
    in the unavailable state". The observable consequence modeled here (and in
    `predictor._settle_reset_state`) is that halted and running are both deasserted.
    This is the reason the halted/running check below is a mutual exclusion and NOT
    an XOR: `halted ^ running` is 0 for a hart in reset, so an XOR assertion would
    fire on every single reset — a false failure on conformant hardware.
    """
    return not hart["halted"] and not hart["running"]


def _is_reset_write(fields: Dict[str, int], predictor) -> bool:
    """Whether this dmcontrol write asserts or deasserts any reset.

    Transition rules of the form "a halted hart that sees haltreq stays halted" are
    stated by #3.5 about harts observing request bits, not about harts being yanked
    through reset in the same access. When a write also moves ndmreset or hartreset,
    the hart's halted/running state is governed by #3.2's reset rules instead, so
    the run-control transition invariants must stand down rather than false-fire.
    """
    return (
        bool(fields["ndmreset"])
        or bool(predictor.ndmreset)
        or bool(fields["hartreset"])
        or bool(predictor._hartreset_level)
    )


# ── The invariants ────────────────────────────────────────────────────────────
#
# Each `_inv_*` appends to `out`. They are separate functions rather than one big
# body so that each one's spec citation sits directly above the code it justifies,
# and so a failing invariant can be read in isolation during triage.


def _inv_halted_running_mutex(out: List[Violation], predictor) -> None:
    """A hart is never simultaneously halted and running.

    #3.5: "When a running hart ... sees its halt request bit high, it responds by
    halting, deasserting its running signal, and asserting its halted signal." The
    two signals are each other's complement *during normal operation* — but #3.2
    describes harts in reset as being in neither state, and #3.14.1 reports halted
    and running as independent bits precisely because a third state exists.

    So this is mutual exclusion, NOT exclusive-or. `halted ^ running` would be the
    tempting one-liner and it would be wrong: it fires on every hart in reset.
    """
    for i, h in enumerate(predictor.snapshot()["harts"]):
        if h["halted"] and h["running"]:
            out.append(
                Violation(
                    rule="INV-HALT-RUN-MUTEX",
                    message="hart reports halted and running simultaneously",
                    tc_ids=("TC-RC-001", "TC-RC-002", "TC-RC-003", "TC-RC-004",
                            "TC-RC-005", "TC-RST-001", "TC-RST-002", "TC-RST-003",
                            "TC-HOR-002", "TC-HOR-003", "TC-HOR-004"),
                    spec="#3.5 Run Control",
                    observed={"halted": True, "running": True},
                    expected="at most one of halted/running asserted",
                    hart=i,
                )
            )


def _check_dmstatus_word(out: List[Violation], word: int, predictor, source: str) -> None:
    """Invariants readable from a single dmstatus word.

    `source` distinguishes a real DUT read-back from this model's own prediction, so
    a violation report says whether the DUT or the model produced the bad word.
    """
    f = DMSTATUS.decode(word)

    # #3.14.1: all* is "1 when all currently selected harts are X"; any* is "1 when
    # any currently selected hart is X". For any non-empty selection, all implies
    # any — this is definitional and holds on every implementation, single- or
    # multi-hart. With an empty selection the predicate is vacuous (all=1, any=0 is
    # legal), so the check is gated on there being a selected hart at all.
    if predictor.selected_indices():
        for all_name, any_name in DMSTATUS_ALL_ANY_PAIRS:
            if f[all_name] and not f[any_name]:
                out.append(
                    Violation(
                        rule="INV-ALL-IMPLIES-ANY",
                        message=f"{all_name}=1 but {any_name}=0 ({source})",
                        tc_ids=("TC-RC-001", "TC-RC-003", "TC-RST-003", "TC-RST-004"),
                        spec=f"#3.14.1 {all_name}/{any_name}",
                        observed={all_name: 1, any_name: 0},
                        expected=f"{all_name}=1 implies {any_name}=1",
                    )
                )

    # #3.14.1 version: 0 means "No debug module present, or the debug module cannot
    # be accessed". A DM that is active and out of ndmreset is by definition present
    # and accessible, so version must be non-zero. #3.13 Version Detection makes this
    # load-bearing: it is the very first thing a debugger reads to decide the DM
    # exists at all.
    if predictor.dmactive and not predictor.ndmreset:
        if f["version"] == DMSTATUS_VERSION_NONE:
            out.append(
                Violation(
                    rule="INV-VERSION-NONZERO",
                    message=f"dmstatus.version=0 while dmactive=1 and ndmreset=0 ({source})",
                    tc_ids=("TC-RST-001", "TC-RST-005", "TC-HOR-001"),
                    spec="#3.14.1 version / #3.13 Version Detection",
                    observed=0,
                    expected="non-zero",
                )
            )

    # #3.14.1 ndmresetpending: "This field is 1 when either the debugger or the hart
    # has requested an ndmreset that has not yet completed." The DM's own ndmreset
    # request is the part this slice controls, so at minimum the bit must be set
    # whenever the debugger holds ndmreset asserted. The converse (bit set with
    # ndmreset deasserted) is legal — the reset may still be draining, and #3.2 warns
    # "the reset itself may also take an arbitrarily long time" — so only the
    # implication ndmreset -> ndmresetpending is asserted.
    if predictor.ndmreset and not f["ndmresetpending"]:
        out.append(
            Violation(
                rule="INV-NDMRESETPENDING",
                message=f"ndmreset asserted but dmstatus.ndmresetpending=0 ({source})",
                tc_ids=("TC-RST-001", "TC-RST-005"),
                spec="#3.14.1 ndmresetpending / #3.2 Reset",
                observed=0,
                expected=1,
            )
        )


def _inv_dmcontrol_reads_zero(out: List[Violation], readback: int) -> None:
    """Every W1/WARZ dmcontrol field reads back 0.

    #3.14 register-table conventions: W1 fields act on a write of 1 and are not
    meaningful to read; WARZ fields "Write Any, Read Zero". #3.14.2 marks haltreq
    WARZ and resumereq/ackhavereset/ackunavail/set*/clr* W1. This is an architectural
    property of the register, not a behavioural prediction, so it is checkable on any
    dmcontrol read without knowing anything about what came before.

    The field set is taken from `registers.ACCESS_READS_ZERO` rather than a hardcoded
    list, so adding a field to the register definition automatically extends this
    check.
    """
    for fld in DMCONTROL.fields:
        if fld.access not in ACCESS_READS_ZERO:
            continue
        value = fld.extract(readback)
        if value != 0:
            out.append(
                Violation(
                    rule="INV-DMCONTROL-READS-ZERO",
                    message=f"dmcontrol.{fld.name} ({fld.access}) read back non-zero",
                    tc_ids=("TC-RC-001", "TC-RC-002", "TC-RC-005", "TC-RST-004",
                            "TC-HOR-002", "TC-HOR-003", "TC-HOR-005"),
                    spec=fld.spec,
                    observed=value,
                    expected=0,
                )
            )


def _inv_mutex_bits(out: List[Violation], fields: Dict[str, int]) -> None:
    """At most one of the mutually-exclusive dmcontrol action bits per write.

    #3.14.2: "On any given write, a debugger may only write 1 to at most one of the
    following bits: resumereq, hartreset, ackhavereset, setresethaltreq,
    clrresethaltreq. The others must be written 0."

    This constrains the *debugger*, not the DM: the spec says nothing about what a DM
    does if the rule is broken, so there is no DUT behaviour to assert. It is
    therefore a stimulus-legality check. TC-HOR-005 exists precisely to break it and
    observe the DUT's (undefined but hopefully non-corrupting) handling, so it must
    be reportable as data rather than raised.
    """
    asserted = [name for name in DMCONTROL_MUTEX_BITS if fields.get(name)]
    if len(asserted) > 1:
        out.append(
            Violation(
                rule="INV-STIM-DMCONTROL-MUTEX",
                message="more than one mutually-exclusive dmcontrol bit written 1 in one access",
                tc_ids=("TC-HOR-005",),
                spec="#3.14.2 dmcontrol",
                observed=asserted,
                expected="at most one of " + ", ".join(DMCONTROL_MUTEX_BITS),
                stimulus_legality=True,
            )
        )


def _inv_dmi_access_during_ndmreset(
    out: List[Violation], addr: int, predictor
) -> None:
    """Only dmcontrol and ndmresetpending may be accessed while ndmreset is asserted.

    #3.2: "While ndmreset or any external reset is asserted, the only supported DM
    operations are reading/writing dmcontrol and reading ndmresetpending. The
    behavior of other accesses is undefined."

    ndmresetpending lives in dmstatus, so a dmstatus read is a supported operation and
    is not flagged. Anything else is the debugger walking into undefined territory —
    again a stimulus-legality matter, since "undefined" means no DUT behaviour can be
    wrong. TC-RST-005 deliberately does this and checks only that the DM does not hang
    or corrupt, which is exactly what the remaining invariants continue to police.
    """
    if not predictor.ndmreset:
        return
    if addr in (DMCONTROL.address, DMSTATUS.address):
        return
    out.append(
        Violation(
            rule="INV-STIM-DMI-DURING-NDMRESET",
            message=f"DMI access to 0x{addr:02x} while ndmreset asserted; behaviour is UNSPECIFIED",
            tc_ids=("TC-RST-005",),
            spec="#3.2 Reset",
            observed=f"0x{addr:02x}",
            expected="dmcontrol read/write or dmstatus (ndmresetpending) read only",
            stimulus_legality=True,
        )
    )


def _inv_resumereq_ignored_when_haltreq(
    out: List[Violation], prev: Dict[str, Any], fields: Dict[str, int], predictor
) -> None:
    """resumereq has no effect when haltreq is set in the same write.

    #3.14.2 resumereq: "resumereq is ignored if haltreq is set."

    Observable consequence: a hart that was halted before such a write must still be
    halted after it, and must not have acquired a resume ack from this write.
    """
    if not (fields["haltreq"] and fields["resumereq"]):
        return
    if not fields["dmactive"] or _is_reset_write(fields, predictor):
        return
    post = predictor.snapshot()
    for i in predictor.selected_indices():
        was, now = _hart(prev, i), _hart(post, i)
        if was is None or now is None or was["nonexistent"] or was["unavail"]:
            continue
        if was["halted"] and not now["halted"]:
            out.append(
                Violation(
                    rule="INV-RESUMEREQ-IGNORED-WHEN-HALTREQ",
                    message="halted hart resumed on a write with both haltreq=1 and resumereq=1",
                    tc_ids=("TC-RC-005",),
                    spec="#3.14.2 resumereq",
                    observed={"halted": now["halted"], "running": now["running"]},
                    expected={"halted": True, "running": False},
                    hart=i,
                )
            )


def _inv_halted_ignores_haltreq(
    out: List[Violation], prev: Dict[str, Any], fields: Dict[str, int], predictor
) -> None:
    """Halted harts ignore their halt request bit.

    #3.5: "Halted harts ignore their halt request bit."

    So writing haltreq=1 at an already-halted hart is a no-op on its observable run
    state: it stays halted, and — crucially — it does not silently reacquire or lose
    a resume ack, which is what distinguishes "ignored" from "re-halted".
    """
    if not fields["haltreq"] or not fields["dmactive"]:
        return
    if _is_reset_write(fields, predictor):
        return
    post = predictor.snapshot()
    for i in predictor.selected_indices():
        was, now = _hart(prev, i), _hart(post, i)
        if was is None or now is None or was["nonexistent"] or was["unavail"]:
            continue
        if not was["halted"]:
            continue
        if not now["halted"] or now["running"]:
            out.append(
                Violation(
                    rule="INV-HALTED-IGNORES-HALTREQ",
                    message="already-halted hart changed run state on a haltreq=1 write",
                    tc_ids=("TC-RC-002",),
                    spec="#3.5 Run Control",
                    observed={"halted": now["halted"], "running": now["running"]},
                    expected={"halted": True, "running": False},
                    hart=i,
                )
            )
        if now["resume_ack"] != was["resume_ack"]:
            out.append(
                Violation(
                    rule="INV-HALTED-IGNORES-HALTREQ",
                    message="already-halted hart's resume ack changed on a haltreq=1 write",
                    tc_ids=("TC-RC-002",),
                    spec="#3.5 Run Control",
                    observed=now["resume_ack"],
                    expected=was["resume_ack"],
                    hart=i,
                )
            )


def _inv_resumereq(
    out: List[Violation], prev: Dict[str, Any], fields: Dict[str, int], predictor
) -> None:
    """The three halves of #3.5's resumereq sentence. (Yes, three.)

    #3.5: "When a debugger writes 1 to resumereq, each selected hart's resume ack bit
    is cleared and each selected, halted hart is sent a resume request. Harts respond
    by resuming, clearing their halted signal, and asserting their running signal. At
    the end of this process the resume ack bit is set. ... Resume requests are ignored
    by running harts."

    Read that carefully, because the asymmetry is the whole trap:
      1. resume ack is cleared for EVERY selected hart — running ones included;
      2. only SELECTED, HALTED harts are sent the request, so only they resume and
         only they set resume ack again;
      3. therefore a hart that was already running when resumereq was written ends up
         with resume_ack=0 and stays running. That is not a bug and must not be
         asserted away — it is the literal reading of the sentence, and it is why
         "resumereq is idempotent" is a false intuition.

    The model deliberately does not settle resume timing: #3.5 allows "less than one
    second" for the response, which is a cycle-domain property and belongs to the SVA
    tier, not here.
    """
    if not fields["resumereq"] or not fields["dmactive"]:
        return
    if fields["haltreq"]:
        return  # ignored — policed by INV-RESUMEREQ-IGNORED-WHEN-HALTREQ instead
    if _is_reset_write(fields, predictor):
        return
    post = predictor.snapshot()
    for i in predictor.selected_indices():
        was, now = _hart(prev, i), _hart(post, i)
        if was is None or now is None or was["nonexistent"] or was["unavail"]:
            continue

        if was["halted"]:
            # (2) selected + halted -> resumed, running, resume ack set.
            if now["halted"] or not now["running"]:
                out.append(
                    Violation(
                        rule="INV-RESUMEREQ-RESUMES-HALTED",
                        message="selected halted hart did not resume on resumereq=1",
                        tc_ids=("TC-RC-003",),
                        spec="#3.5 Run Control",
                        observed={"halted": now["halted"], "running": now["running"]},
                        expected={"halted": False, "running": True},
                        hart=i,
                    )
                )
            elif not now["resume_ack"]:
                out.append(
                    Violation(
                        rule="INV-RESUMEREQ-RESUMES-HALTED",
                        message="hart resumed but resume ack was not set",
                        tc_ids=("TC-RC-003",),
                        spec="#3.5 Run Control",
                        observed=False,
                        expected=True,
                        hart=i,
                    )
                )
        elif was["running"]:
            # (3) "Resume requests are ignored by running harts": run state unchanged,
            # and resume ack cleared per (1) with nothing to re-set it.
            if now["halted"] or not now["running"]:
                out.append(
                    Violation(
                        rule="INV-RUNNING-IGNORES-RESUMEREQ",
                        message="running hart changed run state on resumereq=1",
                        tc_ids=("TC-RC-004",),
                        spec="#3.5 Run Control",
                        observed={"halted": now["halted"], "running": now["running"]},
                        expected={"halted": False, "running": True},
                        hart=i,
                    )
                )
            if now["resume_ack"]:
                out.append(
                    Violation(
                        rule="INV-RESUMEREQ-CLEARS-ACK",
                        message=(
                            "resume ack still set on a running hart after resumereq=1; "
                            "#3.5 clears ack for every selected hart and only halted "
                            "harts re-set it"
                        ),
                        tc_ids=("TC-RC-004",),
                        spec="#3.5 Run Control",
                        observed=True,
                        expected=False,
                        hart=i,
                    )
                )


def _inv_havereset_sticky(
    out: List[Violation],
    prev: Dict[str, Any],
    op: str,
    addr: int,
    fields: Optional[Dict[str, int]],
    predictor,
) -> None:
    """havereset is sticky: only ackhavereset (or a DM reset) may clear it.

    #3.2: "When harts have been reset, they must set a sticky havereset state bit ...
    These bits must be set regardless of the cause of the reset. The havereset bits
    for the selected harts can be cleared by writing 1 to ackhavereset."
    #3.14.2 ackhavereset: "Writing 1 to this bit clears havereset for any selected
    harts."

    Two clearing routes are legal and only two:
      - a dmcontrol write with ackhavereset=1, and only for SELECTED harts;
      - dmactive going low. #3.2 is explicit that this one is optional: "The havereset
        bits might or might not be cleared when dmactive is low." Since both outcomes
        conform, a dmactive=0 write is exempted rather than asserted either way.

    Any other 1->0 transition is a stickiness bug — the failure mode this catches is a
    DM that clears havereset on the next dmcontrol write of any kind, which would make
    TC-RST-003's "regardless of cause" check pass by accident on a broken DUT.
    """
    post = predictor.snapshot()
    is_dmcontrol_write = op == "write" and addr == DMCONTROL.address and fields is not None

    # dmactive low: spec-sanctioned latitude, nothing to check.
    if is_dmcontrol_write and not fields["dmactive"]:
        return

    acked = set()
    if is_dmcontrol_write and fields["ackhavereset"]:
        acked = set(predictor.selected_indices())

    for i, now in enumerate(post["harts"]):
        was = _hart(prev, i)
        if was is None:
            continue
        if was["havereset"] and not now["havereset"] and i not in acked:
            out.append(
                Violation(
                    rule="INV-HAVERESET-STICKY",
                    message="havereset cleared without an ackhavereset naming this hart",
                    tc_ids=("TC-RST-003", "TC-RST-004"),
                    spec="#3.2 Reset / #3.14.2 ackhavereset",
                    observed=False,
                    expected=True,
                    hart=i,
                )
            )

    # The positive half of #3.14.2 ackhavereset: for the harts it names, it must work.
    for i in acked:
        now = _hart(post, i)
        if now is not None and now["havereset"]:
            out.append(
                Violation(
                    rule="INV-ACKHAVERESET-CLEARS",
                    message="ackhavereset=1 did not clear havereset for a selected hart",
                    tc_ids=("TC-RST-004",),
                    spec="#3.14.2 ackhavereset",
                    observed=True,
                    expected=False,
                    hart=i,
                )
            )


def _inv_reset_release(
    out: List[Violation], prev: Dict[str, Any], fields: Dict[str, int], predictor
) -> None:
    """What must be true the moment a hart is released from reset.

    #3.2: "Once a hart's reset is complete, havereset becomes set. When a hart comes
    out of reset and haltreq or resethaltreq are set, the hart will immediately enter
    Debug Mode (halted state)."
    #3.5: "When a hart's halt-on-reset request bit is set, the hart will immediately
    enter debug mode on the next deassertion of its reset. This is true regardless of
    the reset's cause."

    Detected as a transition: a hart that was in reset (neither halted nor running)
    and now is not. Note the model releases reset synchronously with the deasserting
    write, whereas #3.2 explicitly allows an arbitrarily long delay ("the reset itself
    may also take an arbitrarily long time"). The *ordering* asserted here holds
    either way; the timing is deliberately not asserted (see UNSPECIFIED_BEHAVIOURS).
    """
    if not fields["dmactive"]:
        return
    post = predictor.snapshot()
    for i, now in enumerate(post["harts"]):
        was = _hart(prev, i)
        if was is None or now["nonexistent"]:
            continue
        if not (_in_reset(was) and not _in_reset(now)):
            continue  # not a release-from-reset edge

        # #3.2: havereset must be set, whatever caused the reset.
        if not now["havereset"]:
            out.append(
                Violation(
                    rule="INV-HAVERESET-SET-ON-RESET",
                    message="hart came out of reset without havereset being set",
                    tc_ids=("TC-RST-001", "TC-RST-002", "TC-RST-003"),
                    spec="#3.2 Reset",
                    observed=False,
                    expected=True,
                    hart=i,
                )
            )

        # #3.5 / #3.2: halt-on-reset request or a standing halt request means the hart
        # must come out of reset already halted, not run a single instruction.
        wants_halt = was["reset_haltreq"] or now["reset_haltreq"] or now["halt_request"]
        if wants_halt and not now["halted"]:
            out.append(
                Violation(
                    rule="INV-HALT-ON-RESET",
                    message=(
                        "hart released from reset with halt-on-reset (or haltreq) set "
                        "but did not enter Debug Mode"
                    ),
                    tc_ids=("TC-HOR-002", "TC-HOR-004"),
                    spec="#3.5 Run Control / #3.2 Reset",
                    observed={"halted": now["halted"], "running": now["running"]},
                    expected={"halted": True, "running": False},
                    hart=i,
                )
            )
        if not wants_halt and now["halted"]:
            # #3.2: "if the hart was initially running it will execute normally". A
            # hart with no halt request of any kind must not halt on reset — this is
            # the check that makes TC-HOR-003 (clrresethaltreq) mean something.
            # NB: #3.2 also says a hart that was *initially halted* "should now be
            # running but may be halted" — but a hart that was halted before an
            # ndmreset is not in the reset state this branch triggers on, and
            # predictor._release_from_reset does not resurrect its halted bit, so that
            # latitude is not silently asserted away here.
            out.append(
                Violation(
                    rule="INV-NO-HALT-WITHOUT-REQUEST",
                    message="hart halted out of reset with no halt-on-reset or halt request set",
                    tc_ids=("TC-HOR-003",),
                    spec="#3.5 Run Control / #3.2 Reset",
                    observed={"halted": True},
                    expected={"halted": False},
                    hart=i,
                )
            )


def _inv_resethaltreq_per_hart(
    out: List[Violation], prev: Dict[str, Any], fields: Dict[str, int], predictor
) -> None:
    """set/clrresethaltreq touch only the selected harts.

    #3.5: "Writing 1 to setresethaltreq sets the halt-on-reset request bit for each
    selected hart ... The hart's halt-on-reset request bit remains set until cleared
    by the debugger writing 1 to clrresethaltreq while the hart is selected, or by DM
    reset."

    The test plan's own Design Rationale note spells out why this matters: the bits are
    split into two write-only bits "specifically so per-hart halt-on-reset config can
    change without disturbing other selected harts". A DM that applied the request to
    all harts would pass a single-hart test and fail silently in a multi-hart system,
    which is exactly the bug TC-HOR-004 is written to catch.
    """
    if not fields["dmactive"]:
        return
    if not (fields["setresethaltreq"] or fields["clrresethaltreq"]):
        return
    post = predictor.snapshot()
    selected = set(predictor.selected_indices())
    for i, now in enumerate(post["harts"]):
        was = _hart(prev, i)
        if was is None or i in selected:
            continue
        if now["reset_haltreq"] != was["reset_haltreq"]:
            out.append(
                Violation(
                    rule="INV-RESETHALTREQ-PER-HART",
                    message="set/clrresethaltreq changed the halt-on-reset bit of an unselected hart",
                    tc_ids=("TC-HOR-004",),
                    spec="#3.5 Run Control / #3.14.2 setresethaltreq",
                    observed=now["reset_haltreq"],
                    expected=was["reset_haltreq"],
                    hart=i,
                )
            )


def _inv_dm_reset_state(out: List[Violation], fields: Dict[str, int], predictor) -> None:
    """dmactive=0 takes DM state to its reset values.

    #3.14.2 dmactive: "0: The module's state, including authentication mechanism,
    takes its reset values (the dmactive bit is the only bit which can be written to
    something other than its reset value)."

    So after a write clearing dmactive, every reset-valued dmcontrol field must be at
    its reset value. The field's own declared `reset` in registers.py is the authority
    — fields the spec leaves as Preset/implementation-defined carry reset=None and are
    skipped rather than guessed at.

    This is what makes TC-RST-005's "does not corrupt DM state" clause checkable: the
    DM must land in a known state, not a scrambled one.
    """
    if fields["dmactive"]:
        return
    for fld in DMCONTROL.fields:
        if fld.name == "dmactive" or fld.reset is None or fld.reads_zero:
            continue
        actual = fld.extract(predictor.expect(DMCONTROL.address))
        if actual != fld.reset:
            out.append(
                Violation(
                    rule="INV-DM-RESET-STATE",
                    message=f"dmcontrol.{fld.name} not at its reset value after dmactive=0",
                    tc_ids=("TC-RST-005", "TC-HOR-003"),
                    spec=f"#3.14.2 dmactive / {fld.spec}",
                    observed=actual,
                    expected=fld.reset,
                )
            )
    for i, h in enumerate(predictor.snapshot()["harts"]):
        # #3.5: the DM's 4 conceptual per-hart bits "reset to 0, except for resume ack,
        # which may reset to either 0 or 1". resume_ack is therefore NOT checked here
        # — see UNSPECIFIED_BEHAVIOURS.
        for bit in ("halt_request", "reset_haltreq"):
            if h[bit]:
                out.append(
                    Violation(
                        rule="INV-DM-RESET-STATE",
                        message=f"per-hart {bit} not cleared by DM reset (dmactive=0)",
                        tc_ids=("TC-RST-005", "TC-HOR-003"),
                        spec="#3.5 Run Control / #3.14.2 dmactive",
                        observed=True,
                        expected=False,
                        hart=i,
                    )
                )


# ── Entry point ───────────────────────────────────────────────────────────────


def check_all(
    prev_state: Dict[str, Any],
    op: str,
    addr: int,
    data: Optional[int],
    readback: Optional[int],
    predictor,
) -> List[Violation]:
    """Check every architectural invariant of the run-control slice for one DMI op.

    Args:
        prev_state: `predictor.snapshot()` captured *before* this transaction. The
            transition invariants (#3.5's "X is ignored when Y" family) are statements
            about edges and cannot be evaluated without it.
        op: "read" or "write" (`observer.OP_READ` / `OP_WRITE`).
        addr: DMI address.
        data: the value written (writes only; None on reads).
        readback: the value read (reads only; None on writes).
        predictor: the live `DMPredictor`, already updated with this transaction —
            i.e. the post state.

    Returns:
        A list of `Violation`, empty when nothing is broken. Never raises: severity is
        the caller's call, and the negative tests need violations as data.
    """
    out: List[Violation] = []

    # Addresses outside this slice are not modeled here; the only thing to say about
    # them is whether touching them was legal at this moment (#3.2 reset window).
    _inv_dmi_access_during_ndmreset(out, addr, predictor)

    fields: Optional[Dict[str, int]] = None
    if op == "write" and addr == DMCONTROL.address and data is not None:
        fields = DMCONTROL.decode(data)

    # ── State invariants: true of every state, checked on every transaction ────
    _inv_halted_running_mutex(out, predictor)

    if op == "read" and addr == DMSTATUS.address and readback is not None:
        # Prefer the DUT's actual word: that is the thing under test.
        _check_dmstatus_word(out, readback, predictor, source="dmstatus read-back")
    else:
        # No DUT word this cycle — check the model's own predicted dmstatus so a model
        # bug cannot hide between reads and then be believed when a read finally comes.
        _check_dmstatus_word(
            out, predictor.expect(DMSTATUS.address), predictor, source="predicted"
        )

    if op == "read" and addr == DMCONTROL.address and readback is not None:
        _inv_dmcontrol_reads_zero(out, readback)

    # ── havereset stickiness spans reads and writes alike: nothing but an ack may
    #    clear it, including nothing at all happening. ─────────────────────────
    _inv_havereset_sticky(out, prev_state, op, addr, fields, predictor)

    # ── Transition invariants: only meaningful on a dmcontrol write ────────────
    if fields is not None:
        _inv_mutex_bits(out, fields)
        _inv_dm_reset_state(out, fields, predictor)
        _inv_resumereq_ignored_when_haltreq(out, prev_state, fields, predictor)
        _inv_halted_ignores_haltreq(out, prev_state, fields, predictor)
        _inv_resumereq(out, prev_state, fields, predictor)
        _inv_reset_release(out, prev_state, fields, predictor)
        _inv_resethaltreq_per_hart(out, prev_state, fields, predictor)

    return out


# ── Deliberately unasserted: spec-sanctioned latitude ─────────────────────────
#
# Every entry is a place where a plausible-looking assertion would be WRONG, with the
# spec sentence that makes it wrong. This list is a deliverable in its own right: it
# is the difference between "we verified the spec" and "we verified our reading of the
# spec". If a future reader wonders why there is no check for one of these, the answer
# is here rather than in a git blame.


@dataclass(frozen=True)
class Unspecified:
    topic: str
    spec: str
    quote: str
    why_not_asserted: str


UNSPECIFIED_BEHAVIOURS: Tuple[Unspecified, ...] = (
    Unspecified(
        topic="resume ack reset value",
        spec="#3.5 Run Control",
        quote=(
            "These 4 bits reset to 0, except for resume ack, which may reset to "
            "either 0 or 1."
        ),
        why_not_asserted=(
            "Both values conform. Asserting resume_ack==0 after DM reset would fail "
            "every implementation that chose 1. Exposed instead as "
            "DMPredictor(resumeack_reset=...) so a DUT difference is declared, not "
            "discovered as a bug. INV-DM-RESET-STATE checks the other three bits and "
            "skips this one."
        ),
    ),
    Unspecified(
        topic="whether a halted hart resumes when the DM is reset",
        spec="#3.5 Run Control",
        quote=(
            "If the DM is reset while a hart is halted, it is UNSPECIFIED whether "
            "that hart resumes."
        ),
        why_not_asserted=(
            "Both outcomes conform, so no invariant may constrain a hart's halted/"
            "running state across a dmactive=0 write. INV-DM-RESET-STATE checks only "
            "DM-side state; the hart run-state invariants stand down on dmactive=0 "
            "writes."
        ),
    ),
    Unspecified(
        topic="hartreset may reset more harts than are selected",
        spec="#3.2 Reset",
        quote=(
            "In this case an implementation may reset more harts than just the ones "
            "that are selected. The debugger can discover which other harts are reset "
            "(if any) by selecting them and checking anyhavereset and allhavereset."
        ),
        why_not_asserted=(
            "TC-RST-002's check is discovery, not a rule: an unselected hart getting "
            "reset is legal. Only the positive half is asserted (selected harts DO "
            "reset -> INV-HAVERESET-SET-ON-RESET); no invariant forbids collateral "
            "resets."
        ),
    ),
    Unspecified(
        topic="reset timing / latency",
        spec="#3.2 Reset",
        quote=(
            "The actual reset may start as soon as the bit is asserted, but may start "
            "an arbitrarily long time after the bit is deasserted. The reset itself "
            "may also take an arbitrarily long time. ... There is no general, reliable "
            "way for the debugger to know when reset has actually begun."
        ),
        why_not_asserted=(
            "No cycle bound exists to assert against, and the test plan's own Design "
            "Rationale forbids reset-start latency tests. Only orderings are asserted, "
            "never delays."
        ),
    ),
    Unspecified(
        topic="hart run state while reset is on-going",
        spec="#3.2 Reset",
        quote=(
            "While the reset is on-going, harts are either in the running state ... or "
            "in the unavailable state."
        ),
        why_not_asserted=(
            "The spec permits either, so no invariant pins halted/running during "
            "reset. This is the direct reason INV-HALT-RUN-MUTEX is a mutual exclusion "
            "and not `halted ^ running`."
        ),
    ),
    Unspecified(
        topic="DMI accesses other than dmcontrol/ndmresetpending during reset",
        spec="#3.2 Reset",
        quote=(
            "While ndmreset or any external reset is asserted, the only supported DM "
            "operations are reading/writing dmcontrol and reading ndmresetpending. The "
            "behavior of other accesses is undefined."
        ),
        why_not_asserted=(
            "'Undefined' means no return value can be wrong, so TC-RST-005 checks only "
            "that the DM does not hang or corrupt state. Flagged as a stimulus-legality "
            "matter (INV-STIM-DMI-DURING-NDMRESET), never as a DUT failure."
        ),
    ),
    Unspecified(
        topic="havereset across dmactive=0",
        spec="#3.2 Reset",
        quote=(
            "The havereset bits might or might not be cleared when dmactive is low."
        ),
        why_not_asserted=(
            "Explicitly optional in both directions. INV-HAVERESET-STICKY therefore "
            "exempts dmactive=0 writes rather than asserting either outcome."
        ),
    ),
    Unspecified(
        topic="DM behaviour when the dmcontrol mutex rule is broken",
        spec="#3.14.2 dmcontrol",
        quote=(
            "On any given write, a debugger may only write 1 to at most one of the "
            "following bits ... The others must be written 0."
        ),
        why_not_asserted=(
            "The spec constrains the debugger and says nothing about the DM's "
            "response, so there is no DUT behaviour to assert (TC-HOR-005 must "
            "'confirm the DUT's documented/defined handling' per-DUT). Reported as a "
            "stimulus-legality violation instead."
        ),
    ),
    Unspecified(
        topic="hart response latency to halt/resume",
        spec="#3.5 Run Control",
        quote=(
            "When halt or resume is requested, a hart must respond in less than one "
            "second, unless it is unavailable. (How this is implemented is not further "
            "specified. A few clock cycles will be a more typical latency)."
        ),
        why_not_asserted=(
            "A one-second bound is a cycle-domain property with no meaning in an "
            "untimed transaction model. TC-RC-006 belongs to the SVA tier, not here."
        ),
    ),
    Unspecified(
        topic="a hart that was halted before ndmreset",
        spec="#3.2 Reset",
        quote=(
            "if the hart was initially halted it should now be running but may be "
            "halted."
        ),
        why_not_asserted=(
            "'Should ... but may' is not a rule. INV-NO-HALT-WITHOUT-REQUEST only "
            "fires on the release-from-reset edge for harts with no halt request of "
            "any kind, so this latitude is preserved."
        ),
    ),
)


def unspecified_report() -> str:  # pragma: no cover - documentation aid
    """Render UNSPECIFIED_BEHAVIOURS for a test report or review."""
    lines = ["Spec-sanctioned latitude — deliberately NOT asserted:"]
    for u in UNSPECIFIED_BEHAVIOURS:
        lines.append(f"  • {u.topic} ({u.spec})")
        lines.append(f'      spec: "{u.quote}"')
        lines.append(f"      why:  {u.why_not_asserted}")
    return "\n".join(lines)
