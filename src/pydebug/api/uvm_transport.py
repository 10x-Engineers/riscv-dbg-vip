"""
uvm_transport.py — Connects Python to the UVM C bridge via a Unix socket.

Protocol (newline-delimited JSON):

  Python → C:
    {"id": 1, "op": "read",  "addr": 17}
    {"id": 2, "op": "write", "addr": 16, "data": 2147483649}
    {"id": 3, "op": "reset"}

  C → Python:
    {"id": 1, "status": "ok", "data": 3}
    {"id": 2, "status": "ok"}
    {"id": 3, "status": "ok"}
    {"id": X, "status": "err", "msg": "timeout waiting for UVM response"}

The C bridge runs inside the simulator process as a DPI server.
The socket path must match UVM_BRIDGE_SOCK in uvm_bridge.c (default /tmp/uvm_bridge.sock).
"""

import json
import socket
import threading
import logging
from .transport import DebugTransport, TransportError

log = logging.getLogger(__name__)

DEFAULT_SOCK = "/tmp/uvm_bridge.sock"
DEFAULT_TIMEOUT = 300.0   # seconds per transaction


class UVMTransport(DebugTransport):
    """
    Transport that talks to a running UVM simulation via the C bridge.
    Uses a Unix domain socket for low-latency IPC.
    Can be swapped for a TCP socket trivially (change _open_socket).
    """

    def __init__(
        self,
        socket_path: str = DEFAULT_SOCK,
        timeout: float = DEFAULT_TIMEOUT,
        use_tcp: bool = False,
        tcp_host: str = "127.0.0.1",
        tcp_port: int = 5555,
    ):
        super().__init__(name="UVMTransport")
        self._socket_path = socket_path
        self._timeout     = timeout
        self._use_tcp     = use_tcp
        self._tcp_host    = tcp_host
        self._tcp_port    = tcp_port
        self._sock        = None
        self._file        = None          # buffered reader on the socket
        self._id_counter  = 0
        self._lock        = threading.Lock()  # one transaction at a time

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        if self._connected:
            return
        try:
            if self._use_tcp:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self._tcp_host, self._tcp_port))
                log.info("[UVMTransport] connected via TCP %s:%d", self._tcp_host, self._tcp_port)
            else:
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._sock.connect(self._socket_path)
                log.info("[UVMTransport] connected via Unix socket %s", self._socket_path)

            self._sock.settimeout(self._timeout)
            self._file = self._sock.makefile("r")
            self._connected = True
        except (FileNotFoundError, ConnectionRefusedError, OSError) as e:
            raise TransportError(f"UVMTransport: cannot connect — {e}") from e

    def disconnect(self) -> None:
        if not self._connected:
            return
        try:
            # Tell UVM to exit its command loop gracefully
            self._send_shutdown()
        except Exception:
            pass
        try:
            if self._file:
                self._file.close()
            if self._sock:
                self._sock.close()
        except OSError:
            pass
        self._connected = False
        log.info("[UVMTransport] disconnected")

    def set_session_result(self, failed_steps: int) -> None:
        """
        Record how many steps failed, so shutdown can tell the simulator.

        Without this the two halves disagree about the verdict: the client
        exits non-zero, while the UVM side sees an ordinary shutdown and
        reports UVM_ERROR: 0. A scenario that failed then looks green in the
        simulation log, which is the one place people check.
        """
        self._failed_steps = failed_steps

    def _send_shutdown(self) -> None:
        """Send shutdown command so UVM drops its objection and simulation ends."""
        try:
            tx_id = self._next_id()
            msg = json.dumps({"id": tx_id, "op": "shutdown",
                              "data": getattr(self, "_failed_steps", 0)}) + "\n"
            self._sock.sendall(msg.encode())
            raw = self._file.readline()
            if raw:
                resp = json.loads(raw.strip())
                log.debug("[UVMTransport] shutdown ack: %s", resp)
        except Exception as e:
            log.debug("[UVMTransport] shutdown send failed (ok if sim already stopped): %s", e)

    # ── Log forwarding ────────────────────────────────────────────────────────

    def emit_log(self, text: str, verbosity: int = 200) -> None:
        """
        Send one line to the simulator, which prints it via `uvm_info`.

        Printed by UVM rather than by this process so that it carries the
        simulator's own $time and is ordered against the DMI traffic around it.
        Python and the simulator are separate processes sharing one stdout, so
        anything printed here races with UVM's own output and can be torn in
        half mid-line; routing it through the bridge makes the simulator the
        single writer.

        Only UVMTransport does this. OpenOCDTransport keeps printing to stdout,
        because on real hardware there is no simulator and no $time to align to.
        Sequences are untouched either way -- they never print, they return
        StepResults -- so the same scenario runs unchanged in both.

        verbosity is a UVM verbosity level (UVM_MEDIUM = 200).
        """
        if not self._connected:
            return
        for chunk in text.splitlines() or [""]:
            try:
                self._transact({"op": "log", "text": chunk, "data": verbosity})
            except Exception:
                # Never let logging break a run: a debug session that dies
                # because a log line could not be delivered is worse than one
                # that loses the line.
                return

    # ── Core ops ──────────────────────────────────────────────────────────────

    def read(self, addr: int) -> int:
        resp = self._transact({"op": "read", "addr": addr})
        if "data" not in resp:
            raise TransportError(f"UVMTransport read: no data in response: {resp}")
        val = resp["data"]
        log.debug("[UVMTransport] read  addr=0x%02x -> 0x%08x", addr, val)
        return val

    def write(self, addr: int, data: int) -> None:
        self._transact({"op": "write", "addr": addr, "data": data})
        log.debug("[UVMTransport] write addr=0x%02x <- 0x%08x", addr, data)

    def reset(self) -> None:
        self._transact({"op": "reset"})
        log.info("[UVMTransport] reset issued")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _transact(self, payload: dict) -> dict:
        """Send one command, wait for the matching response (by id)."""
        if not self._connected:
            raise TransportError("UVMTransport: not connected")
        with self._lock:
            tx_id = self._next_id()
            payload["id"] = tx_id
            msg = json.dumps(payload) + "\n"
            try:
                self._sock.sendall(msg.encode())
                raw = self._file.readline()
                if not raw:
                    raise TransportError("UVMTransport: socket closed by remote")
                resp = json.loads(raw.strip())
            except (OSError, json.JSONDecodeError, socket.timeout) as e:
                raise TransportError(f"UVMTransport transact: {e}") from e

            if resp.get("id") != tx_id:
                raise TransportError(
                    f"UVMTransport: id mismatch — sent {tx_id}, got {resp.get('id')}"
                )
            if resp.get("status") != "ok":
                raise TransportError(f"UVMTransport: remote error — {resp.get('msg', resp)}")
            return resp
