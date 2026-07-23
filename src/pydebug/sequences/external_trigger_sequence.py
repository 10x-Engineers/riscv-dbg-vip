"""
sequences/external_trigger_sequence.py — Halt-group support discovery via
dmcs2 (spec #3.6, #3.14.3, Ch.3 op 12/13/14).

This is the gate row for the whole HG cluster: `TC-HG-002` onward all need
TWO harts (assign different harts to the same/different groups and confirm
propagation/isolation), which is out of scope for a single-hart basic pass.
TC-HG-001 itself only needs one hart -- read/write dmcs2 and report whether
the fields stick.

No DMI 0x32 register exists at all pre-v1.0 -- only meaningful when run
against a v1.0-compliant DM (the CVA6 v1.0 fork, currently). Confirmed from
that fork's own dm_pkg.sv `dmcs2_t` struct: on this specific target, every
dmcs2 field is architecturally tied to the "not implemented" value (halt/
resume groups are absent), so a real run against it is *expected* to report
"does not implement halt groups" -- this sequence exists to make that a
directly observed, logged fact rather than an assumption, and to be reusable
unchanged against any other DUT that does implement dmcs2.

Traces to: TC-HG-001

Usage:
    from pydebug.sequences.external_trigger_sequence import build_external_trigger_sequence
    session = build_external_trigger_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import dmcs2_group, dmcs2_hgselect


def build_external_trigger_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build and return a DebugSession exercising dmcs2 halt-group support
    discovery (spec #3.6, TC-HG-001).

    Traces to: TC-HG-001
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())

    # ── TC-HG-001: does hgselect/group actually stick? ────────────────────
    def tc_hg_001():
        written = dm.write_dmcs2(hgselect=True, group=0x5)
        readback = dm.read_dmcs2()

        hgselect_stuck = dmcs2_hgselect(readback)
        group_stuck = dmcs2_group(readback)
        implements_halt_groups = hgselect_stuck or (group_stuck != 0)

        return StepResult(
            ok=True,  # discovery row: either answer is a pass, per TC-HG-001's own wording
            msg=f"TC-HG-001: wrote dmcs2=0x{written:08x} "
                f"(hgselect=1, group=5), read back 0x{readback:08x} "
                f"(hgselect={hgselect_stuck}, group={group_stuck}) -- "
                f"{'implements' if implements_halt_groups else 'does NOT implement'} "
                f"halt groups on this DUT. Gate for TC-HG-002 onward "
                f"(multi-hart, out of scope for this single-hart pass).",
        )
    session.add_step("TC-HG-001: dmcs2 halt-group support discovery", tc_hg_001)

    return session
