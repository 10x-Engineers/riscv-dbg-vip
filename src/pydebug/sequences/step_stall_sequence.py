"""
sequences/step_stall_sequence.py — single-step over a stalling instruction.

Sdext, "Step Bit In Dcsr":

    If the instruction being stepped over would normally stall the hart, then
    instead the instruction is treated as a `nop`. This includes `wfi`,
    `wrs.sto`, and `wrs.nto`.

A hart that ignores this deadlocks the debugger permanently: during a step
dcsr.stepie=0 masks the interrupts that would wake a wfi, and the debugger must
not assert haltreq, since re-halting unaided is the property under test. Nothing
is left that can recover the hart.

Regression test for the CVA6 defect where wfi_ctrl un-stalls only on a pending
enabled interrupt, an external debug_req_i, or irq_i[1], with no dcsr.step term.

The wfi's address is resolved from the ELF's symbol table at run time, not
hardcoded. A hardcoded address is a second source of truth for something the
program already defines: add an instruction ahead of the wfi and the constant
silently goes stale, and the test then reports "wfi not reached", which reads
like a DUT fault rather than a stale number. Edit the assembly, run `make -C sw`,
and this picks the new address up on its own.

Run with:
    make soc_test CFG_FILE=configs/step_stall_uvm.json ELF=sw/step_stall_probe.elf

Traces to: TC-SSTEP-002
"""

import logging
import subprocess
import time

from pydebug.api import RISCVDebug, DebugSession, StepResult
from pydebug.api.riscv_dm import (
    DMI, allhalted, anyhalted, allrunning, anyrunning, anyunavail,
)

log = logging.getLogger(__name__)

DCSR_CAUSE_STEP = 4

#: dcsr.cause encodings, spec #4.8 -- named so a wrong cause reports as
#: "3 (haltreq)" rather than a bare number.
CAUSE_NAMES = {
    1: "ebreak", 2: "trigger", 3: "haltreq", 4: "step",
    5: "resethaltreq", 6: "halt group", 7: "other",
}


def _cause_name(cause: int) -> str:
    return CAUSE_NAMES.get(cause, "reserved")


POLL_INTERVAL_S = 0.001
POLL_TIMEOUT_S = 2.0

#: How many times to sample dmstatus after the step before giving a verdict.
#: A single sample cannot tell "stalled forever" from "had not re-halted yet";
#: three spaced samples that all read allrunning settle it, and cost far less
#: than retrying an abstract command that aborts every time.
DMSTATUS_SAMPLES = 3

#: The loop is four instructions, so this covers several laps and then fails
#: loudly rather than stepping forever.
MAX_STEPS_TO_FIND = 24


def _symbol_addr(elf: str, symbol: str, nm: str = "riscv64-unknown-elf-nm") -> int:
    """
    Address of `symbol` in `elf`, from the symbol table.

    Raises rather than falling back to a default: a wrong address here produces
    a confusing failure much later, so it is better to stop at the cause.
    """
    out = subprocess.run([nm, elf], capture_output=True, text=True, check=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == symbol:
            return int(parts[0], 16)
    raise RuntimeError(f"symbol {symbol!r} not found in {elf} -- rebuild it with `make -C sw`")


def _dmstatus_state(dm: RISCVDebug) -> str:
    """
    Read dmstatus and render it as one line: raw value, the bits, and a verdict.

    dmstatus is a DM register, so the debugger reads it straight over DMI with
    no help from the hart. That makes it the only hart-state observable left
    once an abstract command starts aborting -- dcsr needs the hart parked, and
    a stalled hart is exactly the case worth reporting. It also distinguishes
    the two ways a step can fail: allrunning means the hart left Debug Mode and
    never came back, allhalted means it never left.
    """
    return _describe_dmstatus(dm.t.read(DMI.DMSTATUS))


def _describe_dmstatus(status: int) -> str:
    """Render one already-read dmstatus value."""
    if allrunning(status):
        state = "RUNNING -- hart is out of Debug Mode and has not returned"
    elif allhalted(status):
        state = "HALTED -- hart is parked and answering the DM"
    elif anyunavail(status):
        state = "UNAVAILABLE -- hart is not responding to the DM"
    else:
        state = "mixed/unknown"
    return (
        f"dmstatus=0x{status:08x} allhalted={int(allhalted(status))} "
        f"anyhalted={int(anyhalted(status))} allrunning={int(allrunning(status))} "
        f"anyrunning={int(anyrunning(status))} anyunavail={int(anyunavail(status))} "
        f"-> {state}"
    )


def _wait_halted(dm: RISCVDebug, timeout: float = POLL_TIMEOUT_S):
    """Poll dmstatus for allhalted and anyhalted. Never writes haltreq."""
    deadline = time.monotonic() + timeout
    status = 0
    while time.monotonic() < deadline:
        status = dm.t.read(DMI.DMSTATUS)
        if allhalted(status) and anyhalted(status):
            return True, status
        time.sleep(POLL_INTERVAL_S)
    status = dm.t.read(DMI.DMSTATUS)
    return (allhalted(status) and anyhalted(status)), status


def build_step_stall_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    elf: str = "sw/step_stall_probe.elf",
    symbol: str = "wfi_insn",
) -> DebugSession:
    session = DebugSession(mode=mode, stop_on_error=True)
    state = {}

    def resolve_symbol():
        addr = _symbol_addr(elf, symbol)
        state["wfi_addr"] = addr
        return StepResult(
            ok=True,
            msg=f"{symbol} = {addr:#010x} (from {elf}'s symbol table, not hardcoded)",
        )
    session.add_step(f"Resolve {symbol} from the ELF", resolve_symbol)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())

    def confirm_halted():
        halted, status = _wait_halted(dm)
        return StepResult(
            ok=halted,
            msg=f"dmstatus=0x{status:08x} allhalted={int(allhalted(status))} "
                f"anyhalted={int(anyhalted(status))}",
        )
    session.add_step("Confirm hart halted", confirm_halted)

    session.add_step("Set dcsr.step=1", lambda: dm.set_step(True))

    def advance_to_wfi():
        target = state["wfi_addr"]
        for i in range(MAX_STEPS_TO_FIND):
            pc = dm.get_pc()
            if pc == target:
                return StepResult(ok=True,
                                  msg=f"dpc={pc:#010x} is the wfi, after {i} step(s)")
            dm.resume_no_wait()
            halted, status = _wait_halted(dm)
            if not halted:
                return StepResult(
                    ok=False,
                    msg=f"hart did not re-halt after stepping a NON-stalling "
                        f"instruction at {pc:#010x} (dmstatus=0x{status:08x}) -- "
                        f"single-step is broken generally, not just for wfi",
                )
        return StepResult(
            ok=False,
            msg=f"wfi at {target:#010x} not reached in {MAX_STEPS_TO_FIND} steps "
                f"(last dpc={dm.get_pc():#010x})",
        )
    session.add_step("Step until dpc is the wfi", advance_to_wfi)

    def step_over_wfi():
        pc_before = dm.get_pc()
        dm.resume_no_wait()

        # Two questions, two observables. Whether the hart came back is
        # dmstatus's to answer: it is a DM register, read over DMI without the
        # hart's help, so it stays truthful while the hart is gone. Why it came
        # back is dcsr.cause's, and dcsr needs an abstract command, which needs
        # the hart parked -- so it is only worth asking once dmstatus says the
        # hart is there to ask.
        #
        # Sampling a few times rather than once distinguishes a hart that is
        # merely slow to re-halt from one that never will. Polling the abstract
        # command instead, as this used to, just retries a command that aborts
        # for the whole timeout and reports the abort rather than the state.
        samples = []
        halted = False
        for _ in range(DMSTATUS_SAMPLES):
            status = dm.t.read(DMI.DMSTATUS)
            samples.append(status)
            if allhalted(status) and anyhalted(status):
                halted = True
                break
            time.sleep(POLL_INTERVAL_S)

        if not halted:
            trace = "; ".join(
                f"#{i + 1} {_describe_dmstatus(v)}" for i, v in enumerate(samples)
            )
            return StepResult(
                ok=False,
                msg=f"TC-SSTEP-002: hart did not re-enter Debug Mode after stepping "
                    f"the wfi at {pc_before:#010x} -- dmstatus read "
                    f"{len(samples)} times, never halted. Sdext requires a stepped "
                    f"stalling instruction be treated as a nop; with dcsr.stepie=0 "
                    f"and no haltreq the hart cannot be recovered. {trace}",
            )

        # Hart is parked, so dcsr is readable and is the authority on the cause.
        try:
            cause = dm.get_dcsr_cause()
        except Exception as e:
            return StepResult(
                ok=False,
                msg=f"TC-SSTEP-002: hart re-halted after the wfi at {pc_before:#010x} "
                    f"but dcsr.cause could not be read ({e}). "
                    f"{_describe_dmstatus(samples[-1])}",
            )

        if cause != DCSR_CAUSE_STEP:
            return StepResult(
                ok=False,
                msg=f"TC-SSTEP-002: dcsr.cause is NOT correct -- got {cause} "
                    f"({_cause_name(cause)}), expected {DCSR_CAUSE_STEP}=step. "
                    f"The hart is in Debug Mode for some other reason, so the "
                    f"wfi at {pc_before:#010x} was not stepped. "
                    f"{_dmstatus_state(dm)}",
            )

        pc_after = dm.get_pc()
        return StepResult(
            ok=(pc_after != pc_before),
            msg=f"TC-SSTEP-002: dcsr.cause={cause} (step), wfi at {pc_before:#010x} "
                f"-> dpc={pc_after:#010x} (delta={pc_after - pc_before:+d})",
        )

    session.add_step("TC-SSTEP-002: single-step over wfi (spec: treated as a nop)",
                     step_over_wfi)

    session.add_step("Clear dcsr.step", lambda: dm.set_step(False))

    # ── Final hart state ──────────────────────────────────────────────────────
    # Only reached when every step passed; a failing step reports dmstatus in
    # its own message, because stop_on_error ends the session right there.
    session.add_step("Read dmstatus at end of test",
                     lambda: StepResult(ok=True, msg=_dmstatus_state(dm)))

    return session
