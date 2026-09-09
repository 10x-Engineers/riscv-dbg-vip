"""
session.py — Session manager for interactive and non-interactive debug flows.

INTERACTIVE mode:
    Each step is presented to the user who chooses to execute, skip, or abort.
    After each step the response (register value, status) is printed and the
    user decides whether to continue. Useful for live debug / bring-up.

NON-INTERACTIVE mode:
    Steps are executed in sequence without user input.
    Any failure raises an exception (or can be configured to warn and continue).
    Useful for regression / CI.

A "step" is a callable (lambda or function) that takes no arguments and
returns a dict with at least {"ok": bool, "msg": str}.  Typically sequences
build these by calling riscv_dm helpers.

Usage (non-interactive):
    session = DebugSession(transport, mode="batch")
    session.add_step("activate DM",  lambda: dm.activate())
    session.add_step("halt hart",    lambda: dm.halt())
    session.add_step("read PC",      lambda: {"ok": True, "msg": f"PC = {dm.get_pc():#010x}"})
    session.run()

Usage (interactive):
    session = DebugSession(transport, mode="interactive")
    ... same add_step calls ...
    session.run()   # prompts at each step
"""

import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

MODES = ("interactive", "batch")



# ── Output sink ───────────────────────────────────────────────────────────────
# Step lines normally go to stdout. Under UVM simulation the sink is redirected
# so the simulator prints them instead (see UVMTransport.emit_log): Python and
# the simulator are separate processes sharing one stdout, so printing here
# races with UVM's output and can tear a line in half. Routing through the
# bridge makes the simulator the single writer, which also gives every line a
# $time and puts it in order against the DMI traffic it sits between.
#
# Sequences never print -- they return StepResults and this module renders them
# -- so redirecting here leaves every scenario unchanged, and identical between
# simulation and emulation.
_sink = None
_pending = ""


def set_output_sink(fn) -> None:
    """Route step output to `fn` (one call per completed line), or None for stdout."""
    global _sink, _pending
    _sink = fn
    _pending = ""


def _out(text: str = "", end: str = "\n", flush: bool = False) -> None:
    """_out() replacement that honours the sink, including partial lines."""
    global _pending
    if _sink is None:
        print(text, end=end, flush=flush)
        return
    _pending += text
    if end.endswith("\n"):
        for line in _pending.split("\n"):
            _sink(line)
        _pending = ""


class StepResult:
    def __init__(self, ok: bool, msg: str = "", data=None):
        self.ok   = ok
        self.msg  = msg
        self.data = data

    def __repr__(self):
        tag = "OK" if self.ok else "ERR"
        return f"[{tag}] {self.msg}"


class DebugSession:
    """
    Manages a sequence of debug steps in interactive or batch mode.
    The transport and RISCVDebug object are shared across all steps.
    """

    def __init__(
        self,
        mode: str = "batch",
        stop_on_error: bool = True,
    ):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        self.mode           = mode
        self.stop_on_error  = stop_on_error
        self._steps: list[tuple[str, Callable]] = []
        self._results: list[StepResult] = []

    # ── Build the sequence ────────────────────────────────────────────────────

    def add_step(self, name: str, fn: Callable) -> "DebugSession":
        """
        Add a step.  fn() must return:
            - None / any non-dict  → treated as ok=True, msg=""
            - dict with "ok" key  → used directly
            - StepResult          → used directly
            - raises exception    → treated as ok=False, msg=str(exception)
        """
        self._steps.append((name, fn))
        return self   # allows chaining

    # ── Execute ───────────────────────────────────────────────────────────────

    def run(self) -> list[StepResult]:
        """Execute all steps according to the configured mode."""
        self._results = []
        self._print_header()

        for idx, (name, fn) in enumerate(self._steps, start=1):
            if self.mode == "interactive":
                result = self._run_step_interactive(idx, name, fn)
            else:
                result = self._run_step_batch(idx, name, fn)

            self._results.append(result)

            if not result.ok and self.stop_on_error:
                _out(f"\n  [ABORT] Step {idx} failed - stopping session.\n")
                break

        self._print_summary()
        return self._results

    # ── Interactive step ──────────────────────────────────────────────────────

    def _run_step_interactive(self, idx: int, name: str, fn: Callable) -> StepResult:
        _out(f"\n{'-'*60}")
        _out(f"  Step {idx}/{len(self._steps)}: {name}")
        _out(f"{'-'*60}")

        while True:
            _out("  [e] Execute   [s] Skip   [q] Quit   [?] Help")
            try:
                choice = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "q"

            if choice in ("e", ""):
                result = self._invoke(fn)
                self._print_result(result)
                return result

            elif choice == "s":
                _out("  -> Skipped.")
                return StepResult(ok=True, msg="(skipped by user)")

            elif choice == "q":
                _out("  -> Quit requested.")
                raise KeyboardInterrupt("user quit")

            elif choice == "?":
                _out("  e / Enter - execute this step")
                _out("  s         - skip this step (mark ok, continue)")
                _out("  q         - abort the session")

            else:
                _out(f"  Unknown option: {choice!r}")

    # ── Batch step ────────────────────────────────────────────────────────────

    def _run_step_batch(self, idx: int, name: str, fn: Callable) -> StepResult:
        _out(f"  [{idx:02d}] {name} ...", end=" ", flush=True)
        result = self._invoke(fn)
        tag = "ok" if result.ok else "FAIL"
        _out(f"[{tag}]  {result.msg}")
        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _invoke(fn: Callable) -> StepResult:
        try:
            ret = fn()
        except Exception as exc:
            log.exception("Step raised exception")
            return StepResult(ok=False, msg=str(exc))

        if ret is None:
            return StepResult(ok=True, msg="")
        if isinstance(ret, StepResult):
            return ret
        if isinstance(ret, dict):
            return StepResult(
                ok=ret.get("ok", True),
                msg=ret.get("msg", ""),
                data=ret.get("data"),
            )
        return StepResult(ok=True, msg=str(ret))

    def _print_result(self, result: StepResult) -> None:
        tag = "OK" if result.ok else "ERR"
        _out(f"  {tag} {result.msg}")

    def _print_header(self) -> None:
        mode_str = "INTERACTIVE" if self.mode == "interactive" else "BATCH"
        _out(f"\n{'='*60}")
        _out(f"  Debug Session  [{mode_str}]  {len(self._steps)} step(s)")
        _out(f"{'='*60}")

    def _print_summary(self) -> None:
        total   = len(self._results)
        passed  = sum(1 for r in self._results if r.ok)
        failed  = total - passed
        _out(f"\n{'='*60}")
        _out(f"  Session complete - {passed}/{total} passed", end="")
        _out(f"  ({failed} failed)" if failed else "")
        _out(f"{'='*60}\n")

    @property
    def results(self) -> list[StepResult]:
        return self._results

    @property
    def all_passed(self) -> bool:
        return all(r.ok for r in self._results)
