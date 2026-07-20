"""
sequences/dm_activation_sequence.py — DM Activation (dmactive).

Not a Ch.3-numbered operation in its own right — every other sequence in this
project depends on it — but a genuine gap: no other sequence ever writes
`dmcontrol.dmactive=0`, even though spec #3.14.2 prescribes a specific
known-state recovery procedure for it. Found by diffing this project's TC-IDs
against `pydebug.model.coverage.DebugCoverageModel`'s bin list, which is why
this sequence exists.

Traces to: TC-DMA-001, TC-DMA-002

Usage:
    from pydebug.sequences.dm_activation_sequence import build_dm_activation_sequence
    session = build_dm_activation_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import dmcontrol_dmactive, version


def build_dm_activation_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    **params,
) -> DebugSession:
    """
    Build and return a DebugSession exercising DM Activation (spec #3.14.2).
    The session is NOT run yet — call session.run() when ready.

    Traces to: TC-DMA-001, TC-DMA-002
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module (baseline)", lambda: dm.activate())

    # ── TC-DMA-001: deactivate resets DM to defaults ──────────────────────
    def tc_dma_001():
        # #3.14.2 dmactive=0: "The module's state, including authentication
        # mechanism, takes its reset values (the dmactive bit is the only bit
        # which can be written to something other than its reset value)."
        dm.write_dmcontrol(dmactive=False)
        readback = dm.read_dmcontrol()
        deactivated = not dmcontrol_dmactive(readback)
        # #3.14.2: "version might not return correct data" while inactive —
        # typically reads 0 ("no Debug Module present"); this is the one
        # documented reason dmstatus.version can legitimately be 0 elsewhere
        # in this project's coverage model.
        status = dm.read_dmstatus()
        return StepResult(
            ok=deactivated,
            msg=f"TC-DMA-001: dmactive written 0, read back dmactive="
                f"{dmcontrol_dmactive(readback)}, dmstatus.version={version(status)} "
                f"(may legitimately be 0 while inactive, #3.14.2)",
        )
    session.add_step(
        "TC-DMA-001: deactivate Debug Module (write dmcontrol.dmactive=0)",
        tc_dma_001,
    )

    # ── TC-DMA-002: known-state reset sequence ────────────────────────────
    def tc_dma_002():
        # Spec's own documented procedure (#3.14.2 dmactive): "write 0 to
        # dmactive, poll until dmactive is observed 0, write 1 to dmactive,
        # and poll until dmactive is observed 1." This project's dm.activate()
        # only ever writes 1 — this step is what actually exercises the full
        # round trip, and is reusable as a precondition fixture elsewhere.
        dm.write_dmcontrol(dmactive=False)
        deactivated = not dmcontrol_dmactive(dm.read_dmcontrol())
        dm.activate()
        reactivated = dmcontrol_dmactive(dm.read_dmcontrol())
        status = dm.read_dmstatus()
        v = version(status)
        return StepResult(
            ok=deactivated and reactivated and v != 0,
            msg=f"TC-DMA-002: 0->poll->1->poll round trip — deactivated="
                f"{deactivated}, reactivated={reactivated}, version after="
                f"{v} (DM functions normally again, #3.14.2)",
        )
    session.add_step(
        "TC-DMA-002: known-state reset sequence (write0/poll/write1/poll, spec #3.14.2)",
        tc_dma_002,
    )

    return session
