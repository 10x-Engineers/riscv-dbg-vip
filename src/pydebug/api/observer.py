"""
observer.py — A transparent transport wrapper that exposes every DMI transaction.

`RISCVDebug` only ever calls `transport.read(addr)` and `transport.write(addr, data)`.
That makes a delegating wrapper the one place where coverage sampling, invariant
checking, and golden-model cross-checks can observe *every* DMI transaction
without any sequence, command, or test knowing they are there — and, critically,
identically across the mock, a UVM simulation, and real hardware over OpenOCD.

    from pydebug.api.observer import ObservingTransport
    from pydebug.model.coverage import DebugCoverageModel

    cov = DebugCoverageModel()
    t = ObservingTransport(UVMTransport())
    t.add_observer(cov.sample)
    dm = RISCVDebug(t)          # unchanged; unaware it is being observed

Observer contract:
    callback(op, addr, data, readback) -> None

    op        "read" or "write"
    addr      DMI address
    data      the value written  (writes only; None on reads)
    readback  the value read     (reads only;  None on writes)

Observers are called *after* the underlying operation completes, in registration
order. They must not raise: an observer is a passive recorder, and a throwing
observer would masquerade as a DUT failure. Exceptions are therefore allowed to
propagate rather than be swallowed, so an observer bug fails loudly and early
instead of silently dropping coverage.
"""

import logging
from typing import Callable, List, Optional

from .transport import DebugTransport

log = logging.getLogger(__name__)

#: Observer callback type: (op, addr, data, readback) -> None
Observer = Callable[[str, int, Optional[int], Optional[int]], None]

OP_READ = "read"
OP_WRITE = "write"


class ObservingTransport(DebugTransport):
    """Wraps any DebugTransport, notifying observers of each read/write.

    Transparent by construction: every method delegates, so swapping a bare
    transport for a wrapped one changes no behaviour, only visibility.
    """

    def __init__(self, delegate: DebugTransport, name: Optional[str] = None):
        super().__init__(name=name or f"observing({delegate.name})")
        self._delegate = delegate
        self._observers: List[Observer] = []

    # ── Observer registration ─────────────────────────────────────────────────

    def add_observer(self, observer: Observer) -> "ObservingTransport":
        """Register a callback. Returns self, so registrations can be chained."""
        self._observers.append(observer)
        return self

    def remove_observer(self, observer: Observer) -> None:
        self._observers.remove(observer)

    @property
    def observers(self) -> List[Observer]:
        return list(self._observers)

    def _notify(self, op: str, addr: int, data: Optional[int], readback: Optional[int]) -> None:
        for observer in self._observers:
            observer(op, addr, data, readback)

    # ── Delegated lifecycle ───────────────────────────────────────────────────

    def connect(self) -> None:
        self._delegate.connect()
        self._connected = True

    def disconnect(self) -> None:
        self._delegate.disconnect()
        self._connected = False

    # ── Delegated core ops (the observation points) ───────────────────────────

    def read(self, addr: int) -> int:
        readback = self._delegate.read(addr)
        self._notify(OP_READ, addr, None, readback)
        return readback

    def write(self, addr: int, data: int) -> None:
        self._delegate.write(addr, data)
        self._notify(OP_WRITE, addr, data, None)

    def reset(self) -> None:
        self._delegate.reset()

    # ── Pass-through introspection ────────────────────────────────────────────

    @property
    def delegate(self) -> DebugTransport:
        """The wrapped transport, for tests that need the concrete backend."""
        return self._delegate

    @property
    def connected(self) -> bool:
        # Defer to the delegate: it is the one actually holding the channel, so
        # its view cannot drift from reality the way a local copy could.
        return self._delegate.connected

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"<ObservingTransport delegate={self._delegate.__class__.__name__} "
            f"observers={len(self._observers)}>"
        )
