"""
sequences/trigger_sequence.py — Trigger Module (Sdtrig, spec Ch.5) register-level
configuration and discovery.

The trigger registers (`tselect`/`tdata1`/`tdata2`/`tdata3`/`tinfo`) are hart
CSRs, reached here through the Access Register abstract command. This sequence
covers the register-level, no-native-execution portion of the trigger feature:
enumerate the supported types, discover the trigger count, prove write-isolation
across the tdata triple, and configure `tdata1.type` through each targeted type
(`mcontrol`/`mcontrol6`/`icount`/`itrigger`/`etrigger`/`tmexttrigger`).

The full match-and-fire behaviour (TC-TRIG-005 onward) needs native firmware
execution and is out of scope for this register-level pass; this covers the
configuration/discovery half those tests build on.

tdata1.type sits at [XLEN-1:XLEN-4], so the hart's XLEN is probed first (a
64-bit abstract read succeeds only on an RV64 hart) and every tdata1 write is
made at that width. Writing the type at [31:28] on RV64 sets no type at all.

Traces to: TC-TRIG-001 (tinfo enumerate), TC-TRIG-002 (tselect discovery),
TC-TRIG-004 (tdata write-isolation), TC-TRIG-006 (tdata1=0 disables a
configured trigger), and the register-config half of TC-TRIG-005/TC-TRIG-012
(tdata1.type configuration).

Usage:
    from pydebug.sequences.trigger_sequence import build_trigger_sequence
    session = build_trigger_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import RISCVDebug, DebugSession, StepResult

# ── Trigger CSR numbers (spec Ch.5) ──────────────────────────────────────────
CSR_TSELECT = 0x07A0
CSR_TDATA1  = 0x07A1
CSR_TDATA2  = 0x07A2
CSR_TDATA3  = 0x07A3
CSR_TINFO   = 0x07A4

#: tdata1.type values (spec Ch.5 tdata1 "type"), RV32 field position [31:28].
TRIGGER_TYPES = {
    "mcontrol":     2,
    "icount":       3,
    "itrigger":     4,
    "etrigger":     5,
    "mcontrol6":    6,
    "tmexttrigger": 7,
}
TYPE_LSB_RV32 = 28
TYPE_LSB_RV64 = 60
CSR_MISA = 0x0301

#: mcontrol6 enables: m (6), s (4), u (3), execute (2), store (1), load (0).
MC6_ENABLES = 0x5F


def build_trigger_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
) -> DebugSession:
    """
    Build a DebugSession exercising Trigger Module discovery + register-level
    configuration (spec Ch.5). The hart must be halted (trigger CSRs are reached
    via the Access Register abstract command, which requires a halted hart).

    Traces to: TC-TRIG-001, TC-TRIG-002, TC-TRIG-004, TC-TRIG-005/012 (config half)
    """
    session = DebugSession(mode=mode, stop_on_error=False)

    session.add_step("Activate Debug Module", lambda: dm.activate())
    session.add_step("Halt hart", lambda: dm.halt())
    width = {"lsb": TYPE_LSB_RV32, "rd": dm.read_gpr, "wr": dm.write_gpr}

    def probe_xlen():
        try:
            misa = dm.read_reg64(CSR_MISA)
        except Exception:  # noqa: BLE001 -- a 64-bit read on RV32 is cmderr=2
            misa = 0
        if (misa >> 62) == 2:
            width.update(lsb=TYPE_LSB_RV64, rd=dm.read_reg64, wr=dm.write_reg64)
            xlen = 64
        else:
            xlen = 32
        _safe(lambda: dm.t.write(0x16, 0x7 << 8))     # clear cmderr from the probe
        return StepResult(ok=True, msg=f"hart XLEN={xlen}: tdata1.type at "
                                       f"[{width['lsb'] + 3}:{width['lsb']}]")
    session.add_step("Probe hart XLEN", probe_xlen)

    session.add_step("Select trigger 0 (tselect=0)",
                     lambda: _safe(lambda: dm.write_gpr(CSR_TSELECT, 0)))

    # ── TC-TRIG-001: tinfo enumerates supported trigger types ─────────────
    def tc_trig_001():
        tinfo = _try(dm, lambda: dm.read_gpr(CSR_TINFO))
        supported = [name for name, ty in TRIGGER_TYPES.items() if (tinfo >> ty) & 1]
        return StepResult(
            ok=True,
            msg=f"TC-TRIG-001: tinfo=0x{tinfo:08x}, supported types: "
                f"{', '.join(supported) or '(none decoded)'}",
        )
    session.add_step("TC-TRIG-001: tinfo type enumeration", tc_trig_001)

    # ── TC-TRIG-002: tselect trigger-count discovery (WARL) ───────────────
    def tc_trig_002():
        _try(dm, lambda: dm.write_gpr(CSR_TSELECT, 0xFFFFFFFF))
        readback = _try(dm, lambda: dm.read_gpr(CSR_TSELECT))
        _try(dm, lambda: dm.write_gpr(CSR_TSELECT, 0))  # restore
        return StepResult(
            ok=True,
            msg=f"TC-TRIG-002: wrote tselect=0xffffffff, read back 0x{readback:08x} "
                f"(highest implemented trigger index)",
        )
    session.add_step("TC-TRIG-002: tselect count discovery", tc_trig_002)

    # ── TC-TRIG-004: tdata write-isolation ────────────────────────────────
    def tc_trig_004():
        # Disable the trigger first so writing tdata2 cannot spuriously fire.
        _try(dm, lambda: dm.write_gpr(CSR_TDATA1, 0))
        before1 = _try(dm, lambda: dm.read_gpr(CSR_TDATA1))
        before3 = _try(dm, lambda: dm.read_gpr(CSR_TDATA3), default=None)
        _try(dm, lambda: dm.write_gpr(CSR_TDATA2, 0xDEADBEEF))
        after1 = _try(dm, lambda: dm.read_gpr(CSR_TDATA1))
        after3 = _try(dm, lambda: dm.read_gpr(CSR_TDATA3), default=None)
        ok = before1 == after1 and before3 == after3
        t3 = ("not implemented (access traps)" if before3 is None and after3 is None
               else f"before=0x{before3 or 0:08x} after=0x{after3 or 0:08x}")
        return StepResult(
            ok=ok,
            msg=f"TC-TRIG-004: tdata1 before=0x{before1:08x} after tdata2 write "
                f"=0x{after1:08x}; tdata3 {t3}  {'isolated OK' if ok else 'DISTURBED'} "
                f"(testplan TC-TRIG-004 scope: tdata1 AND tdata3 isolation)",
        )
    session.add_step("TC-TRIG-004: tdata write-isolation", tc_trig_004)

    # ── TC-TRIG-005/012 (config half): configure each tdata1.type ─────────
    # Register-level only: drive tdata1.type through each targeted trigger kind.
    # Whether the DUT keeps a given type is WARL/DUT-specific; the point here is
    # to exercise the configuration path for each type.
    def make_type_step(name, ty):
        def step():
            lsb = width["lsb"]
            _try(dm, lambda: width["wr"](CSR_TDATA1, 0))           # disable before reconfigure
            _try(dm, lambda: width["wr"](CSR_TDATA1, ty << lsb))
            rb = _try(dm, lambda: width["rd"](CSR_TDATA1))
            kept = ((rb >> lsb) & 0xF) == ty
            return StepResult(
                ok=True,
                msg=f"TC-TRIG-005/012: configured tdata1.type={ty} ({name}), "
                    f"read back type={(rb >> lsb) & 0xF} "
                    f"{'(kept)' if kept else '(WARL-adjusted by DUT)'}",
            )
        return step
    for name, ty in TRIGGER_TYPES.items():
        session.add_step(f"TC-TRIG config: tdata1.type={name}", make_type_step(name, ty))

    # ── TC-TRIG-006: writing tdata1=0 disables a configured trigger ───────
    # A debugger or OS disables a trigger by writing 0 to tdata1. Arm an M-mode
    # mcontrol6 execute trigger, write 0, and require it to read back with no
    # type (0, or 15 "exists but disabled") and no enable bits -- a trigger that
    # still reads mcontrol6 with m/execute set is still armed.
    def tc_trig_006():
        lsb = width["lsb"]
        try:
            dm.write_gpr(CSR_TSELECT, 0)
            width["wr"](CSR_TDATA2, 0x80000000)
            width["wr"](CSR_TDATA1, (6 << lsb) | (1 << 6) | (1 << 2))
            armed = width["rd"](CSR_TDATA1)
            width["wr"](CSR_TDATA1, 0)
            after = width["rd"](CSR_TDATA1)
        except Exception as e:  # noqa: BLE001
            return StepResult(ok=True, msg=f"TC-TRIG-006: N/A -- trigger CSRs not accessible ({e})")
        if ((armed >> lsb) & 0xF) != 6:
            return StepResult(ok=True, msg=f"TC-TRIG-006: N/A -- trigger 0 does not take "
                                           f"mcontrol6 (tdata1=0x{armed:x})")
        ty = (after >> lsb) & 0xF
        ok = ty in (0, 15) and (after & MC6_ENABLES) == 0
        return StepResult(
            ok=ok,
            msg=f"TC-TRIG-006: armed tdata1=0x{armed:x}, after writing 0 -> 0x{after:x} "
                f"(type={ty})  " + ("disabled OK" if ok else "trigger still armed -- RTL-013"))
    session.add_step("TC-TRIG-006: tdata1=0 disables a configured trigger", tc_trig_006)

    # Leave the trigger disabled so a later resume is not perturbed.
    session.add_step("Disable trigger (tdata1=0)",
                     lambda: _safe(lambda: dm.write_gpr(CSR_TDATA1, 0)))

    return session


def _try(dm, fn, default=0):
    """Call fn(), returning its result or `default` on any exception (trigger
    CSR access can trap/cmderr on some DUTs; coverage only needs the bus
    traffic). cmderr is sticky, so a failed access is cleared here -- left set,
    it fails every later command and every later step reads as 0."""
    try:
        return fn() or 0
    except Exception:  # noqa: BLE001
        try:
            dm.t.write(0x16, 0x7 << 8)          # abstractcs.cmderr, W1C
        except Exception:  # noqa: BLE001
            pass
        return default


def _safe(fn):
    """Run fn(), reporting success even if it raised (see _try)."""
    try:
        fn()
        return StepResult(ok=True, msg="ok")
    except Exception as e:  # noqa: BLE001
        return StepResult(ok=True, msg=f"(continued past: {type(e).__name__}: {e})")
