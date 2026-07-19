"""
mock_transport.py — A DebugTransport backed by the golden-reference predictor.

This is the sim-less, hardware-less backend for the Python test suite. Unlike the
ad-hoc mock in `tests/test_riscv_dm.py` (which hard-codes canned dmstatus words
and models only a single `halted` flag), every modeled register read here is
computed by `DMPredictor` from spec-traced semantics. That means run-control
tests written against it are meaningful rather than tautological: they exercise
resume-ack, havereset stickiness, ndmresetpending, halt-on-reset, and hart
selection, none of which the ad-hoc mock can represent.

    from pydebug.model.mock_transport import ModelBackedMockTransport

    t = ModelBackedMockTransport()
    t.connect()
    dm = RISCVDebug(t)
    dm.activate(); dm.halt()
    assert t.predictor.harts[0].halted

The legacy `MockTransport` in the test file is deliberately left alone: existing
tests assert against its specific (and in places incorrect) bit encodings, and
this class is an addition rather than a migration.

Addresses outside the modeled set fall back to canned values matching the legacy
mock, so this class is a drop-in superset for the existing sequences (which read
abstractcs/data0/sbcs/sbdata0 while exercising halt).
"""

import logging
from typing import List, Optional, Tuple

from ..api.riscv_dm import DMI
from ..api.transport import DebugTransport
from .predictor import DMPredictor
from .registers import register_at

log = logging.getLogger(__name__)


class ModelBackedMockTransport(DebugTransport):
    """In-memory transport whose modeled registers are driven by DMPredictor."""

    def __init__(self, predictor: Optional[DMPredictor] = None, **predictor_kwargs):
        """
        Args:
            predictor: An existing DMPredictor to back this transport. Pass one
                when a test wants to inspect or preconfigure model state.
            **predictor_kwargs: Forwarded to DMPredictor() when `predictor` is
                None (e.g. num_harts=2, hasresethaltreq=False).
        """
        super().__init__(name="ModelBackedMockTransport")
        self.predictor = predictor if predictor is not None else DMPredictor(**predictor_kwargs)
        self.regfile = {}
        self.log: List[Tuple[str, int, Optional[int]]] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    # ── Core ops ──────────────────────────────────────────────────────────────

    def write(self, addr: int, data: int) -> None:
        self.log.append(("write", addr, data))
        self.regfile[addr] = data
        self.predictor.on_write(addr, data)

    def read(self, addr: int) -> int:
        if register_at(addr) is not None:
            value = self.predictor.expect(addr)
        else:
            value = self._canned(addr)
        self.log.append(("read", addr, value))
        return value

    # ── Unmodeled-register fallbacks ──────────────────────────────────────────

    def _canned(self, addr: int) -> int:
        """Canned values for registers outside the run-control model.

        These exist only so sequences that incidentally touch the abstract-command
        and system-bus paths keep running against this transport. They are NOT a
        model of those registers — when the Abstract Commands / SBA slices are
        built, those addresses move into `registers.py` + `predictor.py` and stop
        being answered from here.
        """
        if addr == DMI.ABSTRACTCS:
            return 0x0100_0000  # busy=0, cmderr=0, progbufsize=1
        if addr == DMI.DATA0:
            return self.regfile.get(DMI.DATA0, 0xDEAD_BEEF)
        if addr == DMI.SBCS:
            return 0x2004_0000  # sbbusy=0, sbversion=1, sbaccess32=1
        if addr == DMI.SBDATA0:
            return self.regfile.get(DMI.SBDATA0, 0xCAFE_0000)
        return self.regfile.get(addr, 0)

    # ── Test helpers ──────────────────────────────────────────────────────────

    def ops(self) -> List[Tuple[str, int]]:
        """The (op, addr) transaction trace, for asserting on protocol shape."""
        return [(op, addr) for op, addr, _ in self.log]

    def writes_to(self, addr: int) -> List[int]:
        """Every value written to `addr`, in order."""
        return [data for op, a, data in self.log if op == "write" and a == addr]

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ModelBackedMockTransport {self.predictor!r} ops={len(self.log)}>"
