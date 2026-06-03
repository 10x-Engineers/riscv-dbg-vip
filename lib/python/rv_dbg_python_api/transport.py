"""
transport.py — Abstract transport base class.

Every concrete transport (UVM socket, OpenOCD TCL, etc.) must implement:
    connect()           → open the channel
    disconnect()        → close cleanly
    read(addr)          → int  (32-bit data)
    write(addr, data)   → None
    reset()             → trigger a debug reset (optional, transport may no-op)

That's the only surface the command library ever touches.
Swap the transport, keep every sequence unchanged.
"""

from abc import ABC, abstractmethod
import logging

log = logging.getLogger(__name__)


class DebugTransport(ABC):
    """
    Abstract base for all debug transports.
    Concrete subclasses: UVMTransport, OpenOCDTransport
    """

    def __init__(self, name: str = "transport"):
        self.name = name
        self._connected = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> None:
        """Open the channel. Raises TransportError on failure."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the channel cleanly."""

    # ── Core ops ──────────────────────────────────────────────────────────────

    @abstractmethod
    def read(self, addr: int) -> int:
        """
        Read a 32-bit word at DMI address `addr`.
        Returns the data as an int. Raises TransportError on failure.
        """

    @abstractmethod
    def write(self, addr: int, data: int) -> None:
        """
        Write 32-bit `data` to DMI address `addr`.
        Raises TransportError on failure.
        """

    def reset(self) -> None:
        """
        Optional: trigger a debug module reset.
        Default implementation is a no-op — transports that support it override.
        """
        log.debug("[%s] reset() not implemented for this transport (no-op)", self.name)

    # ── Context manager support ───────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    @property
    def connected(self) -> bool:
        return self._connected

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r} connected={self._connected}>"


class TransportError(RuntimeError):
    """Raised when a transport operation fails (timeout, NAK, socket error, etc.)."""
    pass
