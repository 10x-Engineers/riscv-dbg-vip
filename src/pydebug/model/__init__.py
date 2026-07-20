"""
pydebug.model — Project-agnostic golden reference model of the RISC-V Debug Module.

This subpackage *predicts* what a compliant Debug Module must do; `pydebug.api`
*drives* a real one. Keeping the two apart is what lets stimulus self-check
against an authority rather than against hardcoded constants, and what lets the
same check run unchanged against the mock, a UVM simulation, or real silicon.

Layers:
    registers.py      Spec-traced register/field definitions (pure data).
    predictor.py      Executable state model: write -> predicted state/read-back.
    invariants.py     Architectural rules that must never be violated.
    coverage.py       Functional coverage model: which architectural bins were hit.
    mock_transport.py A DebugTransport backed by the predictor (no sim needed).

Current scope: dmcontrol/dmstatus run control (halt, resume, reset, halt-on-reset).
Other spec areas are added slice by slice; see pydebug/testplans/.

Public API:
    from pydebug.model import DMPredictor, ModelBackedMockTransport
"""

from .coverage import CoverageIncomplete, DebugCoverageModel
from .mock_transport import ModelBackedMockTransport
from .predictor import DMPredictor, HartState
from .registers import (
    DMCONTROL,
    DMCONTROL_MUTEX_BITS,
    DMSTATUS,
    DMSTATUS_ALL_ANY_PAIRS,
    Field,
    Register,
    hartsel_of,
    register_at,
    with_hartsel,
)

__all__ = [
    "CoverageIncomplete",
    "DebugCoverageModel",
    "DMPredictor",
    "HartState",
    "ModelBackedMockTransport",
    "DMCONTROL",
    "DMSTATUS",
    "DMCONTROL_MUTEX_BITS",
    "DMSTATUS_ALL_ANY_PAIRS",
    "Field",
    "Register",
    "hartsel_of",
    "with_hartsel",
    "register_at",
]
