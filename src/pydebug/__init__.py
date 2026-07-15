"""
pydebug — RISC-V Debug Compliance Framework.

Portable across SoCs (Ibex, CVA6, ...) and platforms (UVM simulation, FPGA emulation).

Public API:
    from pydebug import UVMTransport, OpenOCDTransport, RISCVDebug, DebugSession
"""

__version__ = "0.1.0"

from .api import (
    DebugTransport,
    TransportError,
    UVMTransport,
    OpenOCDTransport,
    RISCVDebug,
    DebugError,
    DMI,
    DebugSession,
    StepResult,
)

__all__ = [
    "DebugTransport",
    "TransportError",
    "UVMTransport",
    "OpenOCDTransport",
    "RISCVDebug",
    "DebugError",
    "DMI",
    "DebugSession",
    "StepResult",
]
