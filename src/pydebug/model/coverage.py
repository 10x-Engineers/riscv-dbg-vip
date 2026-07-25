"""
coverage.py — Architectural functional coverage of the dmcontrol/dmstatus run-control slice.

This model answers one question: *which architectural situations described by the
spec has our stimulus actually created?* It is deliberately built on the DMI
transaction stream alone — `(op, addr, data, readback)` — and never reaches into
`DMPredictor`. That constraint is the whole point: a coverage model that peeked at
the golden model's internal state would measure what the *model* did, not what the
*DUT* was actually asked to do. Reading only what a real debugger can read means
this same object produces meaningful numbers against the mock, a UVM simulation,
and real silicon over OpenOCD, unchanged.

    from pydebug.api.observer import ObservingTransport
    from pydebug.model.coverage import DebugCoverageModel

    cov = DebugCoverageModel(num_harts=2)
    t = ObservingTransport(ModelBackedMockTransport(num_harts=2))
    t.add_observer(cov.sample)
    ...
    cov.assert_slice_complete()

Bin names are derived from `registers.py`, never hand-typed, so a field that moves
or gains a bit cannot leave a stale bin behind claiming coverage of something that
no longer exists.

Three populations, always reported separately (see `report()`):

    hit       bins the stimulus created at least once
    unhit     bins that are architecturally reachable but nothing has driven yet
    excluded  bins that CANNOT be reached in this configuration, each carrying a
              spec-cited reason

The excluded registry is the honesty mechanism. A bin that is unreachable is not
quietly deleted — deleting it would silently shrink the denominator and inflate the
percentage. It is named, reasoned about in the spec's own terms, and reported
apart from "covered". If an excluded bin ever *is* hit, that is a bug in the
exclusion reason (the configuration assumption was false), and `report()` and
`assert_slice_complete()` both surface it loudly rather than treating it as a bonus.

Scope: dmcontrol (0x10) / dmstatus (0x11) run control only — spec #3.5 Run Control,
#3.2 Reset Control, #3.14.1 dmstatus, #3.14.2 dmcontrol. Abstract commands, Program
Buffer, SBA, triggers and authentication are later slices and are not binned here.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..api.observer import OP_READ, OP_WRITE
from .registers import (
    DMCONTROL,
    DMCONTROL_MUTEX_BITS,
    DMSTATUS,
    DMSTATUS_ALL_ANY_PAIRS,
    DMSTATUS_VERSION_0_11,
    DMSTATUS_VERSION_0_13,
    DMSTATUS_VERSION_1_0,
    DMSTATUS_VERSION_CUSTOM,
    DMSTATUS_VERSION_NONE,
    HARTSEL_MAX_WIDTH,
    hartsel_of,
)

log = logging.getLogger(__name__)


# ── Observed hart state ───────────────────────────────────────────────────────
#
# What a debugger can infer about the selected hart from one dmstatus read. This
# is an *observation*, not the DM's internal state: spec #3.5 is explicit that of
# the 4 conceptual per-hart bits, "the state of the other bits cannot be observed
# directly" — only halted/running/havereset/resumeack are visible.

ST_UNKNOWN = "unknown"  # no dmstatus read yet; nothing may be inferred
ST_HALTED = "halted"
ST_RUNNING = "running"
ST_IN_RESET = "in_reset"  # neither halted nor running (#3.2, reset in progress)
ST_UNAVAIL = "unavailable"
ST_NONEXISTENT = "nonexistent"


@dataclass(frozen=True)
class Bin:
    """One architectural situation worth knowing we created.

    `tc` names the test case from `testplans/riscv_debug_testplan.md` expected to
    hit this bin. A bin whose `tc` is None is a bin the test plan does not cover —
    that is a finding about the *test plan*, and keeping it visible here is how the
    gap stays visible instead of being rationalised away.
    """

    group: str
    name: str
    spec: str
    why: str
    tc: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.group}.{self.name}"


@dataclass(frozen=True)
class ExcludedBin:
    """A bin that cannot be reached in this configuration, and precisely why.

    `reason` must cite the spec or a declared DUT/model configuration choice. An
    exclusion without a traceable reason is indistinguishable from hiding a hole.
    """

    group: str
    name: str
    reason: str

    @property
    def key(self) -> str:
        return f"{self.group}.{self.name}"


class CoverageIncomplete(AssertionError):
    """Raised by `assert_slice_complete()` when the slice is not closed."""

    def __init__(self, unhit: List[Bin], excluded_hits: List[str]):
        self.unhit = unhit
        self.excluded_hits = excluded_hits
        lines = []
        if unhit:
            lines.append(f"{len(unhit)} un-hit bin(s):")
            for b in unhit:
                tc = b.tc or "NO TC-ID COVERS THIS — test-plan gap"
                lines.append(f"  - {b.key:<52} [{tc}] {b.why}")
        if excluded_hits:
            lines.append(
                f"{len(excluded_hits)} EXCLUDED bin(s) were actually hit — the "
                f"exclusion reason is wrong:"
            )
            for k in excluded_hits:
                lines.append(f"  - {k}")
        super().__init__("\n".join(lines))


class DebugCoverageModel:
    """Functional coverage of dmcontrol/dmstatus run control, sampled off the DMI bus."""

    def __init__(
        self,
        num_harts: int = 1,
        hartsellen: int = HARTSEL_MAX_WIDTH,
        supports_hasel: bool = False,
        supports_stickyunavail: bool = False,
    ):
        """
        Args:
            num_harts: Implemented hart count. Needed to name the "max-implemented"
                and "nonexistent" hartsel bins — a coverage model cannot know from
                the bus alone where the implemented range ends. This must match the
                DUT/predictor configuration; it is a declared input, not a guess.
            hartsellen: The DUT's implemented hartsel width (#3.14.2 hartsel:
                "The actual width of hartsel is called HARTSELLEN. It must be at
                least 0 and at most 20"). Used only to name the all-ones discovery
                write bin.
            supports_hasel: Whether the hart array mask register exists. When False
                (#3.14.2 hasel: "An implementation which does not implement the hart
                array mask register must tie this field to 0"), hasel=1 and every
                all*!=any* bin become unreachable and are moved to the excluded
                registry with that reason.
            supports_stickyunavail: Whether the DM reports dmstatus.stickyunavail=1
                (#3.14.1 stickyunavail is Preset). When False, its 1 bin is excluded.
        """
        self.num_harts = num_harts
        self.hartsellen = hartsellen
        self.supports_hasel = supports_hasel
        self.supports_stickyunavail = supports_stickyunavail

        self._bins: Dict[str, Bin] = {}
        self._counts: Dict[str, int] = {}
        self._excluded: Dict[str, ExcludedBin] = {}
        self._excluded_hits: Dict[str, int] = {}

        # ── Inferred state, rebuilt from the bus exactly as a debugger would ──
        #: Selected-hart state as of the last dmstatus read.
        self._state: str = ST_UNKNOWN
        #: hartsel in force when `_state` was observed, so that a *selection*
        #: change is never mistaken for a hart *state* transition.
        self._state_hartsel: Optional[int] = None
        #: hartsel from the last dmcontrol write (#3.14.2: hartsel resets to 0).
        self._hartsel: int = 0
        #: anyhavereset as of the last dmstatus read.
        self._havereset: Optional[bool] = None
        #: Shadow of the per-hart halt-on-reset request bit, keyed by hartsel.
        #: Spec #3.14.2 resethaltreq: "an optional internal bit of per-hart state
        #: that cannot be read, but can be written with setresethaltreq and
        #: clrresethaltreq" — so the only way to know it is to track what we wrote.
        self._reset_haltreq: Dict[int, bool] = {}
        #: Level of dmcontrol.ndmreset as last written (#3.14.2: it is a level —
        #: "the debugger writes 1, and then writes 0 to deassert the reset").
        self._ndmreset: bool = False

        self._build_bins()

    # ── Bin construction (derived from registers.py, never hand-typed) ─────────

    def _add(self, group: str, name: str, spec: str, why: str, tc: Optional[str] = None) -> None:
        b = Bin(group=group, name=name, spec=spec, why=why, tc=tc)
        self._bins[b.key] = b
        self._counts[b.key] = 0

    def _exclude(self, group: str, name: str, reason: str) -> None:
        e = ExcludedBin(group=group, name=name, reason=reason)
        self._excluded[e.key] = e
        self._excluded_hits[e.key] = 0

    def _build_bins(self) -> None:
        self._build_dmi_access_bins()
        self._build_dmcontrol_field_bins()
        self._build_hartsel_bins()
        self._build_dmstatus_field_bins()
        self._build_all_any_bins()
        self._build_cross_bins()

    def _build_dmi_access_bins(self) -> None:
        """Which registers we touched, and in which direction."""
        g = "dmi_access"
        self._add(g, "read:dmcontrol", "#3.14.2", "dmcontrol read-back (WARL discovery)", "TC-RST-002")
        self._add(g, "write:dmcontrol", "#3.14.2", "dmcontrol write", "TC-RC-001")
        self._add(g, "read:dmstatus", "#3.14.1", "dmstatus read", "TC-RC-001")
        self._exclude(
            g,
            "write:dmstatus",
            "Every dmstatus field is R (#3.14.1), so a write has no spec-defined "
            "behaviour — there is no architectural situation here to cover, which is "
            "why this is an exclusion rather than an un-hit bin. It is registered "
            "instead of dropped so that the excluded-hit mechanism flags it: if "
            "stimulus ever writes dmstatus, that is a bug in the stimulus, and it "
            "should surface as a loud error rather than as silent unbinned traffic.",
        )

    def _build_dmcontrol_field_bins(self) -> None:
        """Both values of every 1-bit dmcontrol field, sampled on writes.

        dmcontrol bins are sampled from the *written* word rather than a read-back
        because most of these fields are W1/WARZ and read back as 0 by definition
        (registers.ACCESS_READS_ZERO) — a read-back-sampled model could never hit
        their 1 bins at all, and would report a comfortable, meaningless 100%.
        """
        #: The TC-ID whose stimulus is expected to drive each field to 1.
        tc_for_one = {
            "haltreq": "TC-RC-001",
            "resumereq": "TC-RC-003",
            "hartreset": "TC-RST-002",
            "ackhavereset": "TC-RST-004",
            "ackunavail": None,  # test-plan gap: no TC-ID exercises ackunavail
            "hasel": None,  # test-plan gap: no TC-ID does the hasel discovery write
            "setkeepalive": None,  # test-plan gap: no TC-ID exercises keepalive
            "clrkeepalive": None,  # test-plan gap: no TC-ID exercises keepalive
            "setresethaltreq": "TC-HOR-002",
            "clrresethaltreq": "TC-HOR-003",
            "ndmreset": "TC-RST-001",
            "dmactive": "TC-RC-001",
        }
        why_one = {
            "hasel": "#3.14.2 hasel: \"A debugger which wishes to use the hart array "
            "mask register feature should set this bit and read back to see if the "
            "functionality is supported.\" Note this bin is reachable even where the "
            "mask register is absent — it records the debugger's discovery *write*, "
            "not whether multiple harts actually got selected. What an absent mask "
            "register makes unreachable is the all*!=any* aggregate, which is "
            "excluded there rather than here.",
            "ackunavail": "#3.14.2 ackunavail=1 clears unavail for selected harts "
            "that are currently available",
            "setkeepalive": "#3.14.2 keepalive: optional per-hart hint to keep the "
            "hart available (e.g. out of a low-power state)",
            "clrkeepalive": "#3.14.2 clrkeepalive clears the keepalive hint",
        }
        #: The TC-ID expected to drive each field to 0. Almost every dmcontrol
        #: write in the slice leaves most of these at 0, so TC-RC-001 covers them
        #: incidentally — dmactive is the exception, and a pointed one: writing
        #: dmactive=0 is the DM reset (#3.14.2 dmactive=0), and no RC/RST/HOR
        #: TC-ID performs it.
        tc_for_zero = {
            "dmactive": None,  # test-plan gap: no TC-ID resets the DM
        }
        for f in DMCONTROL.fields:
            if f.width != 1:
                continue  # hartsello/hartselhi are covered as composite hartsel
            g = f"dmcontrol.{f.name}"
            why_zero = (
                "dmactive=0 resets the DM: \"The module's state ... takes its reset "
                "values\" (#3.14.2 dmactive=0)"
                if f.name == "dmactive"
                else f"{f.name} written 0"
            )
            self._add(g, "0", f.spec, why_zero, tc_for_zero.get(f.name, "TC-RC-001"))
            self._add(
                g,
                "1",
                f.spec,
                why_one.get(f.name, f"{f.name} written 1"),
                tc_for_one[f.name],
            )

    def _build_hartsel_bins(self) -> None:
        """hartsel — the 20-bit index assembled from two disjoint fields.

        Binning hartsel as a value rather than as two independent fields is the
        point: hartselhi only ever matters *because* it is the high half of one
        logical index, and a per-field bin would happily report hartselhi covered
        by a write that never actually selected a hart above 1023.
        """
        g = "dmcontrol.hartsel"
        self._add(g, "zero", "#3.14.2 hartsel", "hart 0 selected (the reset value)", "TC-RC-001")
        self._add(
            g,
            "nonzero",
            "#3.14.2 hartsel",
            "a hart other than 0 selected — proves the field is decoded at all",
            "TC-HOR-004",  # the only TC-ID that selects a hart other than 0
        )
        self._add(
            g,
            "max_implemented",
            "#3.14.2 hartsel",
            f"the highest implemented hart index ({self.num_harts - 1}) selected",
            "TC-HOR-004",
        )
        self._add(
            g,
            "nonexistent",
            "#3.14.1 anynonexistent",
            f"hartsel >= num_harts ({self.num_harts}) — selects a nonexistent hart",
            None,  # test-plan gap
        )
        self._add(
            g,
            "hartselhi_nonzero",
            "#3.14.2 hartselhi",
            "hartsel > 1023, i.e. the high half of the index is nonzero",
            None,  # test-plan gap: HARTSELLEN discovery has no TC-ID
        )
        self._add(
            g,
            "all_ones",
            "#3.14.2 hartsel",
            "the HARTSELLEN discovery write — spec: \"A debugger should discover "
            "HARTSELLEN by writing all ones to hartsel ... and reading back the "
            "value to see which bits were actually set\"",
            None,  # test-plan gap: HARTSELLEN discovery has no TC-ID
        )

    def _build_dmstatus_field_bins(self) -> None:
        """Both values of every 1-bit dmstatus field, sampled on reads.

        The all*/any* fields get their bins here as individual fields *and* again
        as pairs in `_build_all_any_bins` — the pair bins are what carry the
        aggregate-selection semantics, which no single-field bin can express.
        """
        tc_for_one = {
            "ndmresetpending": "TC-RST-001",
            "stickyunavail": None,
            "impebreak": None,
            "allhavereset": "TC-RST-003",
            "anyhavereset": "TC-RST-003",
            "allresumeack": "TC-RC-003",
            "anyresumeack": "TC-RC-003",
            "allnonexistent": "TC-HS-002",
            "anynonexistent": "TC-HS-002",
            "allunavail": None,  # test-plan gap
            "anyunavail": None,  # test-plan gap
            "allrunning": "TC-RC-003",
            "anyrunning": "TC-RC-003",
            "allhalted": "TC-RC-001",
            "anyhalted": "TC-RC-001",
            "authenticated": "TC-RC-001",
            "authbusy": None,
            "hasresethaltreq": "TC-HOR-001",
            "confstrptrvalid": None,
        }
        tc_for_zero = {
            "allhavereset": "TC-RST-004",
            "anyhavereset": "TC-RST-004",
            "allrunning": "TC-RC-001",
            "anyrunning": "TC-RC-001",
            "allhalted": "TC-RC-003",
            "anyhalted": "TC-RC-003",
            "allresumeack": "TC-RC-004",
            "anyresumeack": "TC-RC-004",
            "hasresethaltreq": "TC-HOR-001",  # the gate case: feature absent
            "ndmresetpending": "TC-RST-001",
        }

        #: Fields whose 1 (or 0) bin belongs to a slice we are explicitly not
        #: covering yet, or which the DM reports as a fixed Preset. Each carries
        #: the spec citation that makes it unreachable *here* — not unreachable
        #: in general, which is why the reason names the owning slice.
        out_of_slice = {
            ("impebreak", "1"): "#3.14.1 impebreak reports whether an implicit "
            "ebreak follows the Program Buffer. It is a Program Buffer property; "
            "the Program Buffer is a later slice and no run-control stimulus can "
            "or should set it.",
            ("authenticated", "0"): "#3.14.1 authenticated=0 means the DM is "
            "locked and \"most registers will not be accessible\". Authentication "
            "(#3.12) is a later slice; both project DUTs report authenticated=1 "
            "with no authentication required.",
            ("authbusy", "1"): "#3.14.1 authbusy \"only becomes set in immediate "
            "response to an access to authdata\". authdata is in the authentication "
            "slice, which run-control stimulus never touches.",
            ("confstrptrvalid", "1"): "#3.14.1 confstrptrvalid=1 means "
            "confstrptr0-3 hold the configuration string pointer. That is the "
            "\"Discover DM/implementation info\" feature row, a later slice.",
            ("allunavail", "1"): "#3.2: harts become unavailable for reasons "
            "outside debugger control (being reset, powered down, unplugged) "
            "-- not something a debugger's own DMI stimulus can cause. "
            "Confirmed structurally unreachable on both project SoC "
            "integrations, not just unimplemented: CVA6's ariane_testharness.sv "
            "and Ibex's ibex_demo_system.sv both hardwire the DM's "
            "unavailable_i input to constant 0, so no hart can ever report "
            "unavailable regardless of stimulus.",
            ("anyunavail", "1"): "Same reason as allunavail=1 above.",
        }
        for f in DMSTATUS.fields:
            if f.width != 1:
                continue  # version is enumerated separately
            g = f"dmstatus.{f.name}"
            for val in ("0", "1"):
                reason = out_of_slice.get((f.name, val))
                if reason is not None:
                    self._exclude(g, val, reason)
                    continue
                if f.name == "stickyunavail" and val == "1" and not self.supports_stickyunavail:
                    self._exclude(
                        g,
                        "1",
                        "dmstatus.stickyunavail is Preset (#3.14.1) and this DM is "
                        "configured to report 0, so no stimulus can raise it. With "
                        "stickyunavail=0, unavail is not sticky and clears without "
                        "ackunavail.",
                    )
                    continue
                tc = tc_for_one.get(f.name) if val == "1" else tc_for_zero.get(f.name, "TC-RC-001")
                self._add(g, val, f.spec, f"dmstatus.{f.name} observed {val}", tc)

        # dmstatus.version — an enumeration, not a bit (#3.14.1 version).
        g = "dmstatus.version"
        self._exclude(
            g,
            "none",
            "version=0 means either \"no DM present\" (unreachable -- this model "
            "always represents an implemented DM) or dmactive=0, where #3.14.2 "
            "PERMITS (\"might not return correct data\") but does not require "
            "returning an incorrect version. Confirmed against both DUTs' RTL "
            "(dm_csrs.sv): dmstatus.version is assigned unconditionally, not "
            "gated by dmactive -- neither project DUT exercises this allowance "
            "(riscv-dbg-vip#117).",
        )
        self._add(g, "v0_13", "#3.14.1 version", "version=2: DM conforms to 0.13", "TC-RC-001")
        self._add(g, "v1_0", "#3.14.1 version", "version=3: DM conforms to 1.0", "TC-RC-001")
        self._exclude(
            g,
            "v0_11",
            "version=1 (conforms to 0.11) predates the dmcontrol/dmstatus field "
            "layout this model encodes (#3.14.1 version). A 0.11 DM would not have "
            "these registers at these bits, so binning it here would be incoherent; "
            "neither project DUT reports it.",
        )
        self._exclude(
            g,
            "custom",
            "version=15 means \"not conforming to any available standard\" "
            "(#3.14.1 version). By definition no spec-derived stimulus can require "
            "a DUT to report it, and neither project DUT does.",
        )

    def _build_all_any_bins(self) -> None:
        """The (all*, any*) pairs — the aggregate semantics of hart selection.

        #3.14.1: all* is 1 when *every* currently selected hart is in the state,
        any* is 1 when at least one is. Two of the four combinations are not
        reachable, for two entirely different reasons, and conflating them would
        lose the distinction between "our config can't do this" and "the
        architecture forbids this":

          all=0,any=1  needs a *split* selection — some selected harts in the
                       state, some not. Impossible with one selected hart.
          all=1,any=0  violates all=>any. Not a configuration limit at all; it is
                       architecturally impossible for any non-empty selection, and
                       invariants.py is what proves a DUT never does it.
        """
        #: (TC-ID for all0_any0, TC-ID for all1_any1), per pair. "unavail"'s
        #: all1_any1 entry here is unused (excluded below instead, not a
        #: reachable bin) -- both project SoC integrations hardwire the DM's
        #: unavailable_i input to 0. "nonexistent"'s all1_any1 IS reachable,
        #: via TC-HS-002's deliberately-out-of-range hartsel selection.
        tc_by_pair = {
            "halted": ("TC-RC-003", "TC-RC-001"),
            "running": ("TC-RC-001", "TC-RC-003"),
            "havereset": ("TC-RST-004", "TC-RST-003"),
            "resumeack": ("TC-RC-004", "TC-RC-003"),
            "nonexistent": ("TC-RC-001", "TC-HS-002"),
            "unavail": ("TC-RC-001", None),  # unused, see comment above
        }
        for all_name, any_name in DMSTATUS_ALL_ANY_PAIRS:
            state = all_name.removeprefix("all")
            g = f"dmstatus.all_any.{state}"
            tc_none, tc_all = tc_by_pair[state]
            self._add(
                g,
                "all0_any0",
                "#3.14.1",
                f"no selected hart is in the {state} state",
                tc_none,
            )
            if state == "unavail":
                # Structurally unreachable, not just a test-plan gap: both
                # project SoC integrations (CVA6's ariane_testharness.sv,
                # Ibex's ibex_demo_system.sv) hardwire the DM's
                # unavailable_i input to constant 0, so no hart can ever
                # report unavailable regardless of stimulus -- same reason
                # as the dmstatus.allunavail/anyunavail=1 exclusions above.
                self._exclude(
                    g,
                    "all1_any1",
                    "every selected hart unavailable (#3.14.1) -- both "
                    "project SoC integrations hardwire the DM's "
                    "unavailable_i input to constant 0.",
                )
            else:
                self._add(
                    g,
                    "all1_any1",
                    "#3.14.1",
                    f"every selected hart is in the {state} state",
                    tc_all,
                )
            self._exclude(
                g,
                "all0_any1",
                f"{all_name}=0 with {any_name}=1 requires a selection in which some "
                f"harts are in the state and some are not (#3.14.1). With hasel tied "
                f"to 0 there is exactly one currently selected hart (#3.14.2 hasel "
                f"value 0: \"There is a single currently selected hart\"), so all* "
                f"and any* are computed over one hart and are always equal. "
                f"Reachable only once the hart array mask (hasel/hawindow, Ch.3 op 9) "
                f"is implemented and covered.",
            )
            self._exclude(
                g,
                "all1_any0",
                f"{all_name}=1 with {any_name}=0 is architecturally impossible: "
                f"all* implies any* for any non-empty selection (#3.14.1). This is "
                f"not a coverage hole but an invariant — invariants.py asserts a DUT "
                f"never produces it. Binning it as coverable would make a DUT bug "
                f"look like progress.",
            )

    def _build_cross_bins(self) -> None:
        """Crosses that carry architectural meaning a single field cannot."""

        # ── haltreq x resumereq (#3.14.2 resumereq: "ignored if haltreq is set") ──
        g = "cross.haltreq_x_resumereq"
        self._add(g, "h0_r0", "#3.14.2", "neither requested", "TC-RC-001")
        self._add(g, "h1_r0", "#3.14.2", "halt requested alone", "TC-RC-001")
        self._add(g, "h0_r1", "#3.14.2", "resume requested alone", "TC-RC-003")
        self._add(
            g,
            "h1_r1",
            "#3.14.2 resumereq",
            "both set in one write — spec: \"resumereq is ignored if haltreq is "
            "set\". The bin exists because this rule is only testable by creating "
            "exactly this combination.",
            "TC-RC-005",
        )

        # ── Hart state transitions (#3.5, #3.2) ───────────────────────────────
        #
        # A run-control slice that binned only "we saw halted" and "we saw running"
        # would be satisfied by a DUT stuck in one state that happened to be read
        # after a reset. The transitions are the behaviour; the levels are not.
        g = "cross.hart_state_transition"
        self._add(g, "running_to_halted", "#3.5", "a running hart saw haltreq and halted", "TC-RC-001")
        self._add(g, "halted_to_running", "#3.5", "a halted hart saw resumereq and resumed", "TC-RC-003")
        self._add(
            g,
            "running_to_in_reset",
            "#3.2",
            "reset asserted on a running hart",
            "TC-RST-001",
        )
        self._exclude(
            g,
            "halted_to_in_reset",
            "reset asserted on a halted hart (#3.2). Unreachable via any "
            "stimulus on either project DUT: not via hartreset (WARL-tied "
            "to 0, confirmed via TC-RST-002's own discovery check), and not "
            "via ndmreset either -- both DUTs' dm_mem.sv only resets "
            "halted_q on !rst_ni (the DM's own reset), and ndmreset "
            "deliberately does not touch the DM's own registers, so a "
            "hart already halted stays reported halted throughout an "
            "ndmreset cycle, unaffected by it.",
        )
        self._add(
            g,
            "in_reset_to_running",
            "#3.2",
            "reset deasserted with no halt-on-reset request: \"if the hart was "
            "initially running it will execute normally\"",
            "TC-RST-001",
        )
        self._add(
            g,
            "in_reset_to_halted",
            "#3.5",
            "reset deasserted with haltreq or resethaltreq set: \"the hart will "
            "immediately enter debug mode on the next deassertion of its reset\". "
            "Produced via haltreq, not resethaltreq (TC-HOR-002's own "
            "mechanism) -- resethaltreq is WARL-tied to 0 on both project "
            "DUTs, same family as hartreset, so it can never actually "
            "produce this transition; TC-RST-001's own persistent haltreq "
            "reaches the identical release_from_reset() code path.",
            "TC-RST-001",
        )

        # ── havereset x ackhavereset (#3.2, #3.14.2 ackhavereset) ─────────────
        g = "cross.havereset_x_ackhavereset"
        self._add(
            g,
            "ack_when_set",
            "#3.14.2 ackhavereset",
            "the meaningful ack: havereset was set and is acknowledged",
            "TC-RST-004",
        )
        self._add(
            g,
            "ack_when_clear",
            "#3.14.2 ackhavereset",
            "ack written with havereset already clear — must be a harmless no-op",
            "TC-RC-001",
        )
        self._add(
            g,
            "noack_when_set",
            "#3.2",
            "havereset observed set across a write that does NOT ack — proves the "
            "bit is sticky: \"they must set a sticky havereset state bit\"",
            "TC-RST-003",
        )

        # ── ndmreset x resethaltreq (#3.5 halt-on-reset, #3.2) ────────────────
        #
        # This cross is halt-on-reset itself. The resethaltreq shadow is what makes
        # it possible: the bit "cannot be read" (#3.14.2 resethaltreq), so only the
        # debugger's own write history knows its value.
        # NOTE: self._reset_haltreq (unlike DMPredictor's own reset_haltreq
        # shadow in predictor.py) is a raw debugger-write tracker, not gated
        # by DUT capability -- it answers "did the debugger write
        # setresethaltreq, then hit an ndmreset edge", regardless of whether
        # the DUT actually honors that write. That combination is real,
        # useful stimulus to have covered even on a DUT that WARL-ties
        # resethaltreq to 0 (confirms the probe doesn't break anything),
        # so these bins stay real (not excluded) -- see
        # halt_on_reset_sequence.py's TC-HOR-002/003 for why the write now
        # always happens, gate or no gate.
        g = "cross.ndmreset_x_reset_haltreq"
        self._add(g, "assert_rhr0", "#3.2", "reset asserted, no halt-on-reset request", "TC-RST-001")
        self._add(g, "assert_rhr1", "#3.5", "reset asserted with halt-on-reset request", "TC-HOR-002")
        self._add(
            g,
            "deassert_rhr0",
            "#3.2",
            "reset released with no halt-on-reset request — hart must run, and this "
            "is also the bin that proves clrresethaltreq worked",
            "TC-HOR-003",
        )
        self._add(
            g,
            "deassert_rhr1",
            "#3.5",
            "reset released with halt-on-reset request — hart must halt out of reset "
            "if the DUT implements it, or stays running/N/A if it doesn't "
            "(spec Optional, #3.5) -- either way the write+edge combination "
            "is the thing being covered here, not a specific DUT behavior",
            "TC-HOR-002",
        )

        # ── resumereq x prior hart state (#3.5's asymmetry) ───────────────────
        #
        # #3.5: "each selected hart's resume ack bit is cleared and each selected,
        # halted hart is sent a resume request ... Resume requests are ignored by
        # running harts." The ack is cleared for EVERY selected hart but only halted
        # harts re-set it, so resumereq on a running hart leaves resume_ack=0 with
        # no way to re-set it until that hart halts and resumes. That asymmetry is
        # invisible unless resumereq is sampled against the hart's prior state.
        g = "cross.resumereq_x_prior_state"
        self._add(
            g,
            "resumereq_when_halted",
            "#3.5",
            "resumereq on a halted hart — resumes and re-sets resume ack",
            "TC-RC-003",
        )
        self._add(
            g,
            "resumereq_when_running",
            "#3.5",
            "resumereq on a running hart — request ignored, but resume ack is still "
            "cleared and never re-set",
            "TC-RC-004",
        )
        self._add(
            g,
            "resumereq_when_in_reset",
            "#3.2",
            "resumereq while the hart is in reset — neither halted nor running",
            None,  # test-plan gap: no TC-ID combines resumereq with reset
        )

        # ── dmcontrol mutually-exclusive action bits (#3.14.2) ────────────────
        #
        # "On any given write, a debugger may only write 1 to at most one of the
        # following bits ... The others must be written 0." Counting them turns a
        # protocol rule into something measurable: `multiple` is a rule violation,
        # and the only TC-ID that may legitimately hit it is the negative test.
        g = "cross.dmcontrol_mutex_bits"
        self._add(g, "none", "#3.14.2", f"no bit of {DMCONTROL_MUTEX_BITS} written 1", "TC-RC-001")
        self._add(g, "one", "#3.14.2", "exactly one mutex bit written 1 — the legal case", "TC-RC-003")
        self._add(
            g,
            "multiple",
            "#3.14.2",
            "more than one mutex bit written 1 — a protocol violation the DUT must "
            "survive without corrupting DM state",
            "TC-HOR-005",
        )

    # ── Sampling (the observer callback) ──────────────────────────────────────

    def sample(
        self,
        op: str,
        addr: int,
        data: Optional[int],
        readback: Optional[int],
    ) -> None:
        """Observer callback — matches `ObservingTransport`'s contract exactly.

        Signature is (op, addr, data, readback) so this registers directly:
            ObservingTransport(...).add_observer(cov.sample)

        Addresses outside the run-control slice are ignored rather than binned:
        this model has no business claiming to measure abstractcs or sbcs.
        """
        if op == OP_WRITE and addr == DMCONTROL.address:
            self._hit("dmi_access", "write:dmcontrol")
            self._sample_dmcontrol_write(data or 0)
        elif op == OP_READ and addr == DMCONTROL.address:
            self._hit("dmi_access", "read:dmcontrol")
        elif op == OP_READ and addr == DMSTATUS.address:
            self._hit("dmi_access", "read:dmstatus")
            self._sample_dmstatus_read(readback or 0)
        elif op == OP_WRITE and addr == DMSTATUS.address:
            self._hit("dmi_access", "write:dmstatus")

    def _sample_dmcontrol_write(self, word: int) -> None:
        f = DMCONTROL.decode(word)

        for name, val in f.items():
            field = DMCONTROL.field(name)
            if field.width != 1:
                continue
            self._hit(f"dmcontrol.{name}", str(val))

        # ── hartsel ───────────────────────────────────────────────────────────
        hartsel = hartsel_of(word)
        g = "dmcontrol.hartsel"
        if hartsel == 0:
            self._hit(g, "zero")
        else:
            self._hit(g, "nonzero")
        if hartsel == self.num_harts - 1:
            self._hit(g, "max_implemented")
        if hartsel >= self.num_harts:
            self._hit(g, "nonexistent")
        if hartsel > 0x3FF:
            self._hit(g, "hartselhi_nonzero")
        if hartsel == (1 << HARTSEL_MAX_WIDTH) - 1:
            self._hit(g, "all_ones")

        # ── cross: haltreq x resumereq ────────────────────────────────────────
        self._hit(
            "cross.haltreq_x_resumereq",
            f"h{f['haltreq']}_r{f['resumereq']}",
        )

        # ── cross: dmcontrol mutex bits ───────────────────────────────────────
        n_mutex = sum(f[name] for name in DMCONTROL_MUTEX_BITS)
        self._hit(
            "cross.dmcontrol_mutex_bits",
            "none" if n_mutex == 0 else "one" if n_mutex == 1 else "multiple",
        )

        # Selection updates before the action bits are evaluated. #3.14.2 states
        # it per action bit: "Writes apply to the new value of hartsel and hasel."
        selection_changed = hartsel != self._hartsel
        self._hartsel = hartsel

        # ── cross: resumereq x prior state ────────────────────────────────────
        #
        # Only sampled when this write does not move hartsel: if it does, our
        # last-known state belongs to the previously selected hart while the
        # resumereq applies to the newly selected one, and crossing the two would
        # be a fabricated observation.
        if f["resumereq"] and not selection_changed:
            if self._state == ST_HALTED:
                self._hit("cross.resumereq_x_prior_state", "resumereq_when_halted")
            elif self._state == ST_RUNNING:
                self._hit("cross.resumereq_x_prior_state", "resumereq_when_running")
            elif self._state == ST_IN_RESET:
                self._hit("cross.resumereq_x_prior_state", "resumereq_when_in_reset")

        # ── cross: havereset x ackhavereset ───────────────────────────────────
        if self._havereset is not None and not selection_changed:
            if f["ackhavereset"]:
                self._hit(
                    "cross.havereset_x_ackhavereset",
                    "ack_when_set" if self._havereset else "ack_when_clear",
                )
            elif self._havereset:
                self._hit("cross.havereset_x_ackhavereset", "noack_when_set")
            if f["ackhavereset"]:
                # The debugger now expects it cleared; the next dmstatus read is
                # what actually confirms it (#3.14.2 ackhavereset).
                self._havereset = False

        # ── resethaltreq shadow (#3.14.2: the bit cannot be read) ─────────────
        #
        # clr wins over a simultaneous set, mirroring the documented
        # set/clrkeepalive precedence: setresethaltreq applies "unless
        # clrresethaltreq is simultaneously set to 1" (#3.14.2 setresethaltreq).
        if f["clrresethaltreq"]:
            self._reset_haltreq[hartsel] = False
        elif f["setresethaltreq"]:
            self._reset_haltreq[hartsel] = True
        if not f["dmactive"]:
            # #3.5: the halt-on-reset request bit "remains set until cleared by the
            # debugger writing 1 to clrresethaltreq while the hart is selected, or
            # by DM reset". dmactive=0 is that DM reset (#3.14.2 dmactive=0).
            self._reset_haltreq.clear()
            self._ndmreset = False
            self._state = ST_UNKNOWN
            self._havereset = None
            return

        # ── cross: ndmreset x resethaltreq ────────────────────────────────────
        #
        # ndmreset is a level, so only its *edges* are reset events (#3.14.2
        # ndmreset: "the debugger writes 1, and then writes 0 to deassert"). Every
        # subsequent dmcontrol write while it stays high is not another reset, and
        # binning it as one would let a test that never released reset look done.
        ndmreset = bool(f["ndmreset"])
        rhr = int(self._reset_haltreq.get(hartsel, False))
        if ndmreset and not self._ndmreset:
            self._hit("cross.ndmreset_x_reset_haltreq", f"assert_rhr{rhr}")
        elif not ndmreset and self._ndmreset:
            self._hit("cross.ndmreset_x_reset_haltreq", f"deassert_rhr{rhr}")
        self._ndmreset = ndmreset

    def _sample_dmstatus_read(self, word: int) -> None:
        f = DMSTATUS.decode(word)

        for name, val in f.items():
            field = DMSTATUS.field(name)
            if field.width != 1:
                continue
            self._hit(f"dmstatus.{name}", str(val))

        # ── version (#3.14.1 version) ─────────────────────────────────────────
        version_bin = {
            DMSTATUS_VERSION_NONE: "none",
            DMSTATUS_VERSION_0_11: "v0_11",
            DMSTATUS_VERSION_0_13: "v0_13",
            DMSTATUS_VERSION_1_0: "v1_0",
            DMSTATUS_VERSION_CUSTOM: "custom",
        }.get(f["version"])
        if version_bin is not None:
            self._hit("dmstatus.version", version_bin)

        # ── all*/any* pairs ───────────────────────────────────────────────────
        for all_name, any_name in DMSTATUS_ALL_ANY_PAIRS:
            g = f"dmstatus.all_any.{all_name.removeprefix('all')}"
            self._hit(g, f"all{f[all_name]}_any{f[any_name]}")

        self._havereset = bool(f["anyhavereset"])

        # ── Observed hart state, and the transition into it ───────────────────
        state = self._state_from_dmstatus(f, self._ndmreset)
        prev, prev_hartsel = self._state, self._state_hartsel
        self._state, self._state_hartsel = state, self._hartsel

        # A transition is only a hart *state* change if the same hart is on both
        # sides of it. Reading dmstatus, reselecting, and reading again observes
        # two harts, not one hart moving — crossing those would invent a
        # transition that never happened.
        if prev_hartsel != self._hartsel:
            return
        if prev in (ST_UNKNOWN, ST_UNAVAIL, ST_NONEXISTENT) or state in (
            ST_UNKNOWN,
            ST_UNAVAIL,
            ST_NONEXISTENT,
        ):
            return
        if prev != state:
            self._hit("cross.hart_state_transition", f"{prev}_to_{state}")

    @staticmethod
    def _state_from_dmstatus(f: Dict[str, int], ndmreset: bool) -> str:
        """Infer the selected hart's state from one dmstatus word.

        Order matters. A nonexistent hart reports neither halted nor running and
        would otherwise be indistinguishable from a hart held in reset — #3.14.1
        anynonexistent is the only thing that tells them apart, so it is checked
        first. Likewise unavailable (#3.2: "While the reset is on-going, harts are
        either in the running state ... or in the unavailable state").

        A hart held in ndmreset reads anyrunning=1 on both project DUTs --
        dm_csrs.sv computes allrunning/anyrunning combinationally as
        ~halted & ~unavailable, with no separate "in reset" encoding, so it
        is NOT distinguishable from a genuinely running hart via dmstatus
        bits alone (confirmed against real RTL, riscv-dbg-vip investigation,
        2026-07-25). ndmreset itself IS separately observable though (the
        dmcontrol write that asserted it, tracked in self._ndmreset) --
        consult that instead of trying to infer "in reset" from a read that
        cannot actually carry it.
        """
        if f["anynonexistent"]:
            return ST_NONEXISTENT
        if f["anyunavail"]:
            return ST_UNAVAIL
        if f["anyhalted"]:
            return ST_HALTED
        if f["anyrunning"] and ndmreset:
            return ST_IN_RESET
        if f["anyrunning"]:
            return ST_RUNNING
        return ST_IN_RESET

    # ── Hit accounting ────────────────────────────────────────────────────────

    def _hit(self, group: str, name: str) -> None:
        key = f"{group}.{name}"
        if key in self._counts:
            self._counts[key] += 1
        elif key in self._excluded_hits:
            # An excluded bin was reached, so the exclusion reason is false. Record
            # it rather than counting it as coverage: this is a defect in the model's
            # own assumptions and must be loud, not absorbed.
            self._excluded_hits[key] += 1
            log.warning(
                "coverage: EXCLUDED bin %s was hit — exclusion reason is wrong: %s",
                key,
                self._excluded[key].reason,
            )
        else:
            raise KeyError(f"coverage: no bin or exclusion declared for {key!r}")

    # ── Reporting ─────────────────────────────────────────────────────────────

    def report(self) -> Dict[str, object]:
        """Per-bin hit counts, plus the un-hit and excluded populations.

        Structure:
            counts        {bin_key: hit_count} for every declared bin
            hit           {bin_key: hit_count} for bins with count > 0
            unhit         [{bin, spec, why, tc}] — reachable but not yet driven
            excluded      [{bin, reason}] — unreachable, never counted as covered
            excluded_hits [bin_key] — exclusions proven wrong (should be empty)
            summary       counts and the coverage percentage
        """
        hit = {k: v for k, v in self._counts.items() if v > 0}
        unhit = [
            {"bin": b.key, "spec": b.spec, "why": b.why, "tc": b.tc}
            for k, b in sorted(self._bins.items())
            if self._counts[k] == 0
        ]
        excluded = [
            {"bin": e.key, "reason": e.reason} for _, e in sorted(self._excluded.items())
        ]
        excluded_hits = [k for k, v in sorted(self._excluded_hits.items()) if v > 0]
        total = len(self._bins)
        return {
            "counts": dict(sorted(self._counts.items())),
            "hit": dict(sorted(hit.items())),
            "unhit": unhit,
            "excluded": excluded,
            "excluded_hits": excluded_hits,
            "summary": {
                "bins": total,
                "hit": len(hit),
                "unhit": len(unhit),
                "excluded": len(excluded),
                # The denominator is the reachable bins only. Excluded bins are not
                # in it — and, critically, not in the numerator either. Adding them
                # to both is the arithmetic by which unreachable states get reported
                # as verified.
                "percent": round(100.0 * len(hit) / total, 2) if total else 100.0,
            },
        }

    def unhit_bins(self) -> List[Bin]:
        """Every bin no stimulus has reached, as structured `Bin`s."""
        return [b for k, b in sorted(self._bins.items()) if self._counts[k] == 0]

    def assert_slice_complete(self, raise_on_incomplete: bool = True) -> List[Bin]:
        """Check the run-control slice is closed.

        Returns the un-hit bins, and by default raises `CoverageIncomplete` naming
        every one of them together with the TC-ID that should have hit it. Also
        fails if any *excluded* bin was hit, because that means an exclusion reason
        is wrong — which is worse than an un-hit bin: an un-hit bin is a known hole,
        a false exclusion is a hole the model claims does not exist.
        """
        unhit = self.unhit_bins()
        excluded_hits = [k for k, v in sorted(self._excluded_hits.items()) if v > 0]
        if raise_on_incomplete and (unhit or excluded_hits):
            raise CoverageIncomplete(unhit, excluded_hits)
        return unhit

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        s = self.report()["summary"]
        return (
            f"<DebugCoverageModel {s['hit']}/{s['bins']} bins "
            f"({s['percent']}%) excluded={s['excluded']}>"
        )
