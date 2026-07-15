"""
openocd_transport.py — Connects to a running OpenOCD instance via its TCL port.

OpenOCD exposes a TCL command server on port 6666 by default.
We send raw TCL commands and parse the response.

The DMI register read/write surface is identical to UVMTransport —
sequences and the command library are completely unaware of the swap.

OpenOCD setup (in your openocd.cfg):
    tcl_port 6666

Then:
    openocd -f interface/ftdi/olimex-arm-usb-ocd-h.cfg \
            -f target/riscv.cfg

API difference from UVMTransport:
    - socket_path / tcp_host replaced by host:port (always TCP)
    - reset() sends "reset halt" via TCL
    - read/write translate to: riscv dmi_read / riscv dmi_write
"""

import socket
import logging
import re
import time
from .transport import DebugTransport, TransportError

log = logging.getLogger(__name__)

OPENOCD_HOST    = "127.0.0.1"
OPENOCD_PORT    = 6666
OPENOCD_TIMEOUT = 30.0  # Increased to allow slow bitbang simulation communication

# OpenOCD appends \x1a (EOF / ctrl-Z) as an end-of-response marker
_EOF_MARKER = b"\x1a"


class OpenOCDTransport(DebugTransport):
    """
    Transport targeting a real board or FPGA through OpenOCD.
    Implements exactly the same read/write/reset surface as UVMTransport.

    Usage:
        transport = OpenOCDTransport(host="127.0.0.1", port=6666)
        # ... everything else is identical to UVMTransport usage
    """

    def __init__(
        self,
        host: str = OPENOCD_HOST,
        port: int = OPENOCD_PORT,
        timeout: float = OPENOCD_TIMEOUT,
    ):
        super().__init__(name="OpenOCDTransport")
        self._host    = host
        self._port    = port
        self._timeout = timeout
        self._sock    = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        if self._connected:
            return
        for _ in range(30):
            try:
                self._sock = socket.create_connection((self._host, self._port), timeout=self._timeout)
                
                self._connected = True
                
                log.info("[OpenOCDTransport] connected to %s:%d", self._host, self._port)

                return
            
            except (ConnectionRefusedError, OSError) as e:
                last_error = e
                time.sleep(0.5)
        raise TransportError(f"OpenOCDTransport: cannot connect — {last_error}")

    def disconnect(self) -> None:
        if not self._connected:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        self._connected = False
        log.info("[OpenOCDTransport] disconnected")

    # ── Core ops ──────────────────────────────────────────────────────────────

    def read(self, addr: int) -> int:
        """
        DMI read via OpenOCD's high-level riscv dmi_read command.
        Returns the 32-bit data value.
        """
        tcl = f"riscv dmi_read {addr:#x}"
        resp = self._send_tcl(tcl)
        data = self._parse_int(resp, context=f"read addr=0x{addr:02x}")
        log.debug("[OpenOCDTransport] read addr=0x%02x → 0x%08x", addr, data)
        return data

    def write(self, addr: int, data: int) -> None:
        """
        Translate a DMI write:
            riscv dmi_write <addr> <data>
        """
        tcl = f"riscv dmi_write {addr:#x} {data:#010x}"
        self._send_tcl(tcl)
        log.debug("[OpenOCDTransport] write addr=0x%02x ← 0x%08x", addr, data)

    def reset(self) -> None:
        """Issue a halt+reset through OpenOCD."""
        self._send_tcl("reset halt")
        log.info("[OpenOCDTransport] reset halt issued")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _send_tcl(self, cmd: str) -> str:
        """
        Send a TCL command string, read until the 0x1a EOF marker.
        Returns the response as a stripped string.
        """
        if not self._connected:
            raise TransportError("OpenOCDTransport: not connected")
        try:
            log.debug("[OpenOCDTransport] >>> sending: %r", cmd)
            self._sock.sendall((cmd + "\x1a").encode())
            resp = self._recv_until_eof()
            log.debug("[OpenOCDTransport] <<< response: %r", resp)
            return resp
        except (OSError, socket.timeout) as e:
            raise TransportError(f"OpenOCDTransport: {e}") from e

    def _recv_until_eof(self) -> str:
        buf = b""
        while True:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise TransportError("OpenOCDTransport: connection closed")
            buf += chunk
            if _EOF_MARKER in buf:
                buf = buf.split(_EOF_MARKER)[0]
                break
        return buf.decode(errors="replace").strip()

    def _drain_banner(self) -> None:
        """Read and discard OpenOCD's connect banner (if any)."""
        try:
            self._sock.settimeout(0.3)
            while True:
                data = self._sock.recv(1024)
                if not data or _EOF_MARKER in data:
                    break
        except socket.timeout:
            pass
        finally:
            self._sock.settimeout(self._timeout)

    @staticmethod
    def _parse_int(s: str, context: str = "") -> int:
        """Parse a hex (0x...) or decimal integer from an OpenOCD response string."""
        s = s.strip()
        # Try to find a hex value first
        m = re.search(r"0x([0-9a-fA-F]+)", s)
        if m:
            return int(m.group(1), 16)
        # Try plain decimal
        m = re.search(r"\b(\d+)\b", s)
        if m:
            return int(m.group(1))
        raise TransportError(
            f"OpenOCDTransport: cannot parse int from {s!r} (context: {context})"
        )
