"""
sequences/reset_values_sequence.py — every DM register's value after a DM reset.

The spec gives a reset value for each field of each register (the "Reset" column
of #3.14's register tables). Nothing checked them: the suite activated the DM
and started working, so a field that came up wrong was only ever noticed if a
later test happened to trip over it. This reads the whole DMI map immediately
after `dmactive` 0→1, before anything else touches it, and compares field by
field.

Two kinds of expectation, kept apart on purpose:

- **Architectural.** `busy=0`, `cmderr=0`, `command`=0, `abstractauto`=0,
  `haltsum*`=0 with no hart halted. The spec fixes these for every DM, so a
  mismatch is a defect.
- **Preset.** `progbufsize`, `datacount`, `hartinfo`, `sbcs.sbasize` and the
  rest are implementation-defined. They are compared against the DUT's own
  declared configuration (`pydebug/dut_configs/<dut>.json`, the same file the
  reference model is built from), so this checks that the RTL implements the
  parameters it was configured with — not that it matches some other DM.

`sbcs` matters here more than the others: RST-038 exists because every `sbcs`
value recorded by the suite so far carried `sbreadonaddr=1`, whose reset is 0 —
none of them was a post-reset read, so the reset value had never actually been
observed. The read below is the first thing the sequence does to the SBA.

Traces to: RST-030, RST-032, RST-033, RST-034, RST-035, RST-036, RST-037,
RST-038, RST-039, RST-040, RST-042, RST-043

Usage:
    from pydebug.sequences.reset_values_sequence import build_reset_values_sequence
    session = build_reset_values_sequence(dm, mode="batch")
    session.run()
"""

from pydebug.api import DebugSession, RISCVDebug, StepResult
from pydebug.api.riscv_dm import dmcontrol
from pydebug.model.dut_config import load_dut_config
from pydebug.model.registers import (
    ABSTRACTAUTO,
    ABSTRACTCS,
    AUTHDATA,
    COMMAND,
    CONFSTRPTR0,
    DMCONTROL,
    HALTSUM_LEVELS,
    HARTINFO,
    NEXTDM,
    data_address,
    progbuf_address,
)

#: sbcs (DMI 0x38) field positions, spec #3.14.13. Not in registers.py: the SBA
#: slice models sbcs in predictor.py, and this sequence only needs to name the
#: fields it reports.
SBCS_FIELDS = (
    ("sbversion", 29, 3),
    ("sbbusyerror", 22, 1),
    ("sbbusy", 21, 1),
    ("sbreadonaddr", 20, 1),
    ("sbaccess", 17, 3),
    ("sbautoincrement", 16, 1),
    ("sbreadondata", 15, 1),
    ("sberror", 12, 3),
    ("sbasize", 5, 7),
    ("sbaccess128", 4, 1),
    ("sbaccess64", 3, 1),
    ("sbaccess32", 2, 1),
    ("sbaccess16", 1, 1),
    ("sbaccess8", 0, 1),
)

#: dtmcs (JTAG, no DMI address) field positions, spec #6.1.4.
DTMCS_FIELDS = (("dmihardreset", 17, 1), ("dmireset", 16, 1),
                ("idle", 12, 3), ("dmistat", 10, 2),
                ("abits", 4, 6), ("version", 0, 4))

#: DMI addresses of the system-bus registers (#3.14.13-#3.14.17).
SBCS, SBADDRESS0, SBADDRESS3, SBDATA0, SBDATA3 = 0x38, 0x39, 0x37, 0x3C, 0x3F


def _diff(expected: dict, word: int, fields) -> list:
    """Field-by-field mismatches of `word` against `expected`.

    `fields` is a sequence of (name, lsb, width). Only fields named in
    `expected` are checked — an unlisted field is one the spec leaves
    implementation-defined and this sequence does not claim to know.
    """
    bad = []
    for name, lsb, width in fields:
        if name not in expected:
            continue
        got = (word >> lsb) & ((1 << width) - 1)
        if got != expected[name]:
            bad.append(f"{name}={got} (expect {expected[name]})")
    return bad


def _register_fields(reg):
    return tuple((f.name, f.lsb, f.width) for f in reg.fields)


def build_reset_values_sequence(
    dm: RISCVDebug,
    mode: str = "batch",
    dut: str = "cva6",
) -> DebugSession:
    """Build a DebugSession that resets the DM and checks every register's
    post-reset value against the spec's reset column and the DUT's declared
    presets.

    Traces to: RST-030, RST-032 … RST-043
    """
    session = DebugSession(mode=mode, stop_on_error=False)
    cfg = load_dut_config(dut).raw

    def _reg(addr):
        return dm.t.read(addr)

    # ── The reset itself ──────────────────────────────────────────────────────
    # dmactive=0 resets the DM (spec #3.14.2: "the DM ... is reset when
    # dmactive is 0"), and nothing else may be written before the checks, or
    # what they read is the write, not the reset value.
    def dm_reset():
        dm.t.write(DMCONTROL.address, dmcontrol(dmactive=False))
        dm.t.write(DMCONTROL.address, dmcontrol(dmactive=True))
        return StepResult(ok=True, msg="DM reset: dmactive 0 -> 1, nothing else written")
    session.add_step("Reset the Debug Module", dm_reset)

    # ── RST-030: dmcontrol ────────────────────────────────────────────────────
    def rst_030():
        word = _reg(DMCONTROL.address)
        expected = {f.name: (1 if f.name == "dmactive" else f.reset)
                    for f in DMCONTROL.fields if f.reset is not None or f.name == "dmactive"}
        # The W1 bits read 0 whatever was written (#3.14.2), so they are part
        # of the expectation even though the spec gives them no reset value.
        expected.update({f.name: 0 for f in DMCONTROL.fields if f.reads_zero})
        bad = _diff(expected, word, _register_fields(DMCONTROL))
        return StepResult(
            ok=not bad,
            msg=f"RST-030-C: dmcontrol=0x{word:08x} after reset  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-030-C: dmcontrol reset value", rst_030)

    # ── RST-032: hartinfo (all preset) ────────────────────────────────────────
    def rst_032():
        word = _reg(HARTINFO.address)
        expected = {"nscratch": cfg["nscratch"], "dataaccess": int(cfg["dataaccess"]),
                    "datasize": cfg["datasize"], "dataaddr": int(cfg["dataaddr"], 16)}
        bad = _diff(expected, word, _register_fields(HARTINFO))
        return StepResult(
            ok=not bad,
            msg=f"RST-032-C: hartinfo=0x{word:08x} vs declared presets  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-032-C: hartinfo presets", rst_032)

    # ── RST-033: abstractcs ───────────────────────────────────────────────────
    def rst_033():
        word = _reg(ABSTRACTCS.address)
        expected = {"busy": 0, "cmderr": 0,               # architectural
                    "progbufsize": cfg["progbufsize"],    # preset
                    "datacount": cfg["datacount"],
                    "relaxedpriv": int(cfg["relaxedpriv_reset"])}
        bad = _diff(expected, word, _register_fields(ABSTRACTCS))
        return StepResult(
            ok=not bad,
            msg=f"RST-033-C: abstractcs=0x{word:08x}  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-033-C: abstractcs reset value", rst_033)

    # ── RST-034 / RST-035: command, abstractauto ──────────────────────────────
    def rst_034():
        word = _reg(COMMAND.address)
        return StepResult(
            ok=word == 0,
            msg=f"RST-034-C: command=0x{word:08x} (WARZ, reads 0)  "
                + ("OK" if word == 0 else "MISMATCH"))
    session.add_step("RST-034-C: command reads zero", rst_034)

    def rst_035():
        word = _reg(ABSTRACTAUTO.address)
        return StepResult(
            ok=word == 0,
            msg=f"RST-035-C: abstractauto=0x{word:08x}  "
                + ("OK" if word == 0 else "MISMATCH, expect 0"))
    session.add_step("RST-035-C: abstractauto reset value", rst_035)

    # ── RST-036 / RST-037: data and progbuf ───────────────────────────────────
    # The spec does not fix these (they are scratch), so what is checked is the
    # weaker, still meaningful claim: after a DM reset they are not stale, i.e.
    # the DM does not carry a previous session's operands into this one.
    def rst_036():
        vals = [_reg(data_address(i)) for i in range(cfg["datacount"])]
        bad = [f"data{i}=0x{v:08x}" for i, v in enumerate(vals) if v != 0]
        return StepResult(
            ok=not bad,
            msg=f"RST-036-C: data0..{cfg['datacount'] - 1} after reset  "
                + ("all zero" if not bad else "non-zero: " + ", ".join(bad)))
    session.add_step("RST-036-C: data registers after reset", rst_036)

    def rst_037():
        vals = [_reg(progbuf_address(i)) for i in range(cfg["progbufsize"])]
        bad = [f"progbuf{i}=0x{v:08x}" for i, v in enumerate(vals) if v != 0]
        return StepResult(
            ok=not bad,
            msg=f"RST-037-C: progbuf0..{cfg['progbufsize'] - 1} after reset  "
                + ("all zero" if not bad else "non-zero: " + ", ".join(bad)))
    session.add_step("RST-037-C: program buffer after reset", rst_037)

    # ── RST-038: sbcs, the first SBA access of the run ────────────────────────
    def rst_038():
        word = _reg(SBCS)
        expected = {"sbversion": cfg["sbversion"], "sbbusy": 0, "sbbusyerror": 0,
                    "sberror": 0, "sbreadonaddr": 0, "sbreadondata": 0,
                    "sbautoincrement": 0, "sbasize": cfg["sbasize"],
                    "sbaccess": cfg["sbaccess_reset"],
                    "sbaccess128": int(cfg["sbaccess128"]),
                    "sbaccess64": int(cfg["sbaccess64"]),
                    "sbaccess32": int(cfg["sbaccess32"]),
                    "sbaccess16": int(cfg["sbaccess16"]),
                    "sbaccess8": int(cfg["sbaccess8"])}
        bad = _diff(expected, word, SBCS_FIELDS)
        return StepResult(
            ok=not bad,
            msg=f"RST-038-C: sbcs=0x{word:08x}, first SBA access after reset  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-038-C: sbcs reset value", rst_038)

    # ── RST-039: sbaddress0..3, sbdata0..3 ────────────────────────────────────
    def rst_039():
        bad = []
        for addr, name in ([(SBADDRESS0 + i, f"sbaddress{i}") for i in range(3)]
                           + [(SBADDRESS3, "sbaddress3")]
                           + [(SBDATA0 + i, f"sbdata{i}") for i in range(4)]):
            word = _reg(addr)
            if word != 0:
                bad.append(f"{name}=0x{word:08x}")
        return StepResult(
            ok=not bad,
            msg="RST-039-C: sbaddress0..3 / sbdata0..3 after reset  "
                + ("all zero" if not bad else "non-zero: " + ", ".join(bad)))
    session.add_step("RST-039-C: SBA address/data after reset", rst_039)

    # ── RST-040: haltsum0..3 with no hart halted ──────────────────────────────
    def rst_040():
        bad = []
        for level, reg in enumerate(HALTSUM_LEVELS):
            word = _reg(reg.address)
            if word != 0:
                bad.append(f"haltsum{level}=0x{word:08x}")
        return StepResult(
            ok=not bad,
            msg="RST-040-C: haltsum0..3 with no hart halted  "
                + ("all zero" if not bad
                   else "non-zero: " + ", ".join(bad) + " (see RTL-007)"))
    session.add_step("RST-040-C: halt summaries with nothing halted", rst_040)

    # ── RST-042: nextdm, confstrptr0..3, authdata ─────────────────────────────
    def rst_042():
        bad = []
        word = _reg(NEXTDM)
        if word != int(cfg["nextdm"], 16):
            bad.append(f"nextdm=0x{word:08x} (expect {cfg['nextdm']})")
        for i in range(4):
            word = _reg(CONFSTRPTR0 + i)
            # confstrptr is only meaningful when dmstatus.confstrptrvalid is
            # set; this DUT does not set it, so the registers must read 0.
            if word != 0:
                bad.append(f"confstrptr{i}=0x{word:08x}")
        word = _reg(AUTHDATA)
        if word != 0 and not cfg["authentication_enable"]:
            bad.append(f"authdata=0x{word:08x} with authentication not implemented")
        return StepResult(
            ok=not bad,
            msg="RST-042-C: nextdm / confstrptr0..3 / authdata  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-042-C: nextdm and confstrptr", rst_042)

    # ── RST-043: dtmcs (the DTM, not the DM) ──────────────────────────────────
    # dtmcs has no DMI address: it is a JTAG register, and only a transport that
    # speaks JTAG can read it. A transport that cannot says so rather than
    # silently passing.
    def rst_043():
        if not hasattr(dm.t, "dtmcs"):
            return StepResult(
                ok=True,
                msg="RST-043-C: N/A -- this transport has no dtmcs access")
        word = dm.t.dtmcs()
        bad = _diff({"dmistat": 0, "dmireset": 0, "dmihardreset": 0},
                    word, DTMCS_FIELDS)
        decoded = " ".join(f"{n}={(word >> l) & ((1 << w) - 1)}"
                           for n, l, w in DTMCS_FIELDS)
        return StepResult(
            ok=not bad,
            msg=f"RST-043-C: dtmcs=0x{word:08x} ({decoded})  "
                + ("OK" if not bad else "MISMATCH: " + ", ".join(bad)))
    session.add_step("RST-043-C: dtmcs reset value", rst_043)

    return session
