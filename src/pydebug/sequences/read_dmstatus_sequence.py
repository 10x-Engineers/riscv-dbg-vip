"""
sequences/read_dmstatus_sequence.py — Simple sequence to read dmstatus.

This sequence:
    1. Reads dmstatus

Usage:
    pydebug run --scenario read_dmstatus --mode batch --transport uvm
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult, DMI


def build_read_dmstatus_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=False)

    def read_dmstatus():
        val = dm.t.read(DMI.DMSTATUS)
        return StepResult(ok=True, msg=f"dmstatus = {val:#010x}")
        
    session.add_step("Read dmstatus", read_dmstatus)

    return session
