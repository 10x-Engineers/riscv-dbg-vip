"""
pydebug.api — Core debug transport and command library.

Public API:
    from pydebug.api import UVMTransport, OpenOCDTransport, RISCVDebug, DebugSession
"""

from .transport         import DebugTransport, TransportError
from .uvm_transport     import UVMTransport
from .openocd_transport import OpenOCDTransport
from .riscv_dm          import RISCVDebug, DebugError, DMI
from .session           import DebugSession, StepResult

__all__ = [
    "DebugTransport", "TransportError",
    "UVMTransport",
    "OpenOCDTransport",
    "RISCVDebug", "DebugError", "DMI",
    "DebugSession", "StepResult",
]
