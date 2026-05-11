"""
sequences/read_dmstatus_sequence.py — Simple sequence to read dmstatus.

This sequence:
    1. Reads dmstatus

Usage (batch, UVM):
    python run.py --scenario read_dmstatus --mode batch --transport uvm
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from debug_lib import RISCVDebug, DebugSession, StepResult
from debug_lib.riscv_dm import DMI

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
