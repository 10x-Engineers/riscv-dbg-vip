"""
debug_lib — Python debug framework for RISC-V targets.

Public API:
    from debug_lib import UVMTransport, OpenOCDTransport, RISCVDebug, DebugSession
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
