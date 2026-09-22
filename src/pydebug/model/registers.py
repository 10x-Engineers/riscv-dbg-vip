"""
registers.py — Spec-traced register and field definitions for the RISC-V Debug Module.

This module is pure data plus encode/decode helpers: no transport, no I/O, no
behavioural prediction. `predictor.py` consumes these definitions to model DM
behaviour; `coverage.py` uses them to name bins; `invariants.py` uses them to
name architectural checks.

Bit positions and access types are taken verbatim from the ratified spec's own
machine-readable register definitions (riscv/riscv-debug-spec, xml/dm_registers.xml)
rather than transcribed by hand, so they cannot drift from the spec text.

Spec references are to the RISC-V Debug Specification:
    #3.14.1  dmstatus     (Debug Module Status,  DMI 0x11)
    #3.14.2  dmcontrol    (Debug Module Control, DMI 0x10)
    #3.14.3  dmcs2        (halt/resume groups and external triggers, DMI 0x32)
    #3.14.4  hawindowsel  (hart array window,    DMI 0x14)
    #3.14.5  hawindow     (hart array mask,      DMI 0x15)
    #3.14.6  abstractcs   (abstract control/status, DMI 0x16)
    #3.14.7  command      (abstract command,     DMI 0x17)
    #3.14.8  abstractauto (autoexec,             DMI 0x18)
    #3.14.9  data/progbuf (DMI 0x04-0x0f, 0x20-0x2f)
    #3.14.10 haltsum0-3   (DMI 0x40, 0x13, 0x34, 0x35)
    #3.14.11 hartinfo     (DMI 0x12)
and to Sdext (chapter 4) and Sdtrig (chapter 5) for the hart-side CSRs.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# ── Access types (spec #3.14 register-table conventions) ──────────────────────
#
# R     — read-only.
# R/W   — read/write; reads return the last written value.
# W1    — write-1-to-act. Writing 1 performs an action; writing 0 is a no-op.
#         Reads are not meaningful (this model returns 0).
# WARL  — Write Any, Read Legal. Writes of unsupported values are not required
#         to stick; read back to discover what the implementation supports.
# WARZ  — Write Any, Read Zero. Writes act; reads always return 0.
# W1C   — write-1-to-clear. Writing ones clears the field; writing zeros leaves
#         it alone. abstractcs.cmderr is the one of these, and it is sticky
#         until cleared, so forgetting to clear it makes every later command
#         fail with the first command's error.

ACCESS_R = "R"
ACCESS_RW = "R/W"
ACCESS_W1 = "W1"
ACCESS_W1C = "W1C"
ACCESS_WARL = "WARL"
ACCESS_WARZ = "WARZ"

#: Access types whose read-back value is architecturally always 0, regardless of
#: what was last written. Used by invariants.py to check read-back behaviour and
#: by predictor.py to build dmcontrol read-back values.
ACCESS_READS_ZERO = (ACCESS_W1, ACCESS_WARZ)


@dataclass(frozen=True)
class Field:
    """One named bit-field of a DMI register, with its spec citation."""

    name: str
    lsb: int
    width: int
    access: str
    spec: str
    #: Architectural reset value, or None where the spec leaves it
    #: implementation-defined / "Preset" / unspecified.
    reset: Optional[int] = None

    @property
    def msb(self) -> int:
        return self.lsb + self.width - 1

    @property
    def value_mask(self) -> int:
        """Mask of the field's value, right-aligned at bit 0."""
        return (1 << self.width) - 1

    @property
    def mask(self) -> int:
        """Mask of the field in its register position."""
        return self.value_mask << self.lsb

    @property
    def reads_zero(self) -> bool:
        return self.access in ACCESS_READS_ZERO

    def extract(self, word: int) -> int:
        """Pull this field's value out of a full register word."""
        return (word >> self.lsb) & self.value_mask

    def insert(self, word: int, value: int) -> int:
        """Return `word` with this field replaced by `value`."""
        return (word & ~self.mask) | ((value & self.value_mask) << self.lsb)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        bits = f"{self.msb}:{self.lsb}" if self.width > 1 else str(self.lsb)
        return f"<Field {self.name} bits={bits} access={self.access}>"


@dataclass(frozen=True)
class Register:
    """A DMI register: an address plus a set of named fields."""

    name: str
    address: int
    spec: str
    fields: Tuple[Field, ...]

    def field(self, name: str) -> Field:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(f"{self.name} has no field {name!r}")

    def has_field(self, name: str) -> bool:
        return any(f.name == name for f in self.fields)

    def decode(self, word: int) -> Dict[str, int]:
        """Split a register word into {field_name: value}."""
        return {f.name: f.extract(word) for f in self.fields}

    def encode(self, **values: int) -> int:
        """Build a register word from field values. Unnamed fields are 0."""
        word = 0
        for name, value in values.items():
            word = self.field(name).insert(word, value)
        return word

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Register {self.name} @0x{self.address:02x} ({len(self.fields)} fields)>"


# ── dmcontrol — Debug Module Control, DMI 0x10 (spec #3.14.2) ─────────────────
#
# Note the hartsel split: `hartsel` is hartselhi:hartsello, i.e. a 20-bit index
# assembled from two disjoint 10-bit fields. An implementation may implement
# fewer bits (HARTSELLEN, 0..20); a debugger discovers the width by writing all
# ones and reading back which bits stuck.

DMCONTROL = Register(
    name="dmcontrol",
    address=0x10,
    spec="#3.14.2",
    fields=(
        Field("haltreq", 31, 1, ACCESS_WARZ, "#3.14.2 haltreq"),
        Field("resumereq", 30, 1, ACCESS_W1, "#3.14.2 resumereq"),
        Field("hartreset", 29, 1, ACCESS_WARL, "#3.14.2 hartreset", reset=0),
        Field("ackhavereset", 28, 1, ACCESS_W1, "#3.14.2 ackhavereset"),
        Field("ackunavail", 27, 1, ACCESS_W1, "#3.14.2 ackunavail"),
        Field("hasel", 26, 1, ACCESS_WARL, "#3.14.2 hasel", reset=0),
        Field("hartsello", 16, 10, ACCESS_WARL, "#3.14.2 hartsello", reset=0),
        Field("hartselhi", 6, 10, ACCESS_WARL, "#3.14.2 hartselhi", reset=0),
        Field("setkeepalive", 5, 1, ACCESS_W1, "#3.14.2 setkeepalive"),
        Field("clrkeepalive", 4, 1, ACCESS_W1, "#3.14.2 clrkeepalive"),
        Field("setresethaltreq", 3, 1, ACCESS_W1, "#3.14.2 setresethaltreq"),
        Field("clrresethaltreq", 2, 1, ACCESS_W1, "#3.14.2 clrresethaltreq"),
        Field("ndmreset", 1, 1, ACCESS_RW, "#3.14.2 ndmreset", reset=0),
        Field("dmactive", 0, 1, ACCESS_RW, "#3.14.2 dmactive", reset=0),
    ),
)

#: dmcontrol bits a debugger may write 1 to only ONE of, per any single write
#: (spec #3.14.2: "On any given write, a debugger may only write 1 to at most one
#: of the following bits ... The others must be written 0."). Writing more than
#: one is a protocol violation; invariants.py checks stimulus never does it, and
#: the negative tests deliberately violate it to observe DUT handling.
DMCONTROL_MUTEX_BITS = (
    "resumereq",
    "hartreset",
    "ackhavereset",
    "setresethaltreq",
    "clrresethaltreq",
)


# ── dmstatus — Debug Module Status, DMI 0x11 (spec #3.14.1) ───────────────────
#
# Every field is read-only. The all*/any* pairs report the aggregate state of the
# *currently selected* harts: all* is 1 when every selected hart is in the state,
# any* is 1 when at least one is. On a single-hart selection all* == any* always
# — which is why the all!=any bins are unhittable without multi-hart selection.

DMSTATUS = Register(
    name="dmstatus",
    address=0x11,
    spec="#3.14.1",
    fields=(
        Field("ndmresetpending", 24, 1, ACCESS_R, "#3.14.1 ndmresetpending"),
        Field("stickyunavail", 23, 1, ACCESS_R, "#3.14.1 stickyunavail"),
        Field("impebreak", 22, 1, ACCESS_R, "#3.14.1 impebreak"),
        Field("allhavereset", 19, 1, ACCESS_R, "#3.14.1 allhavereset"),
        Field("anyhavereset", 18, 1, ACCESS_R, "#3.14.1 anyhavereset"),
        Field("allresumeack", 17, 1, ACCESS_R, "#3.14.1 allresumeack"),
        Field("anyresumeack", 16, 1, ACCESS_R, "#3.14.1 anyresumeack"),
        Field("allnonexistent", 15, 1, ACCESS_R, "#3.14.1 allnonexistent"),
        Field("anynonexistent", 14, 1, ACCESS_R, "#3.14.1 anynonexistent"),
        Field("allunavail", 13, 1, ACCESS_R, "#3.14.1 allunavail"),
        Field("anyunavail", 12, 1, ACCESS_R, "#3.14.1 anyunavail"),
        Field("allrunning", 11, 1, ACCESS_R, "#3.14.1 allrunning"),
        Field("anyrunning", 10, 1, ACCESS_R, "#3.14.1 anyrunning"),
        Field("allhalted", 9, 1, ACCESS_R, "#3.14.1 allhalted"),
        Field("anyhalted", 8, 1, ACCESS_R, "#3.14.1 anyhalted"),
        Field("authenticated", 7, 1, ACCESS_R, "#3.14.1 authenticated"),
        Field("authbusy", 6, 1, ACCESS_R, "#3.14.1 authbusy"),
        Field("hasresethaltreq", 5, 1, ACCESS_R, "#3.14.1 hasresethaltreq"),
        Field("confstrptrvalid", 4, 1, ACCESS_R, "#3.14.1 confstrptrvalid"),
        Field("version", 0, 4, ACCESS_R, "#3.14.1 version", reset=3),
    ),
)

#: dmstatus.version encodings (spec #3.14.1 version).
DMSTATUS_VERSION_NONE = 0  # No Debug Module present.
DMSTATUS_VERSION_0_11 = 1  # Conforms to 0.11.
DMSTATUS_VERSION_0_13 = 2  # Conforms to 0.13.
DMSTATUS_VERSION_1_0 = 3  # Conforms to 1.0.
DMSTATUS_VERSION_CUSTOM = 15  # Not conforming to any available standard.

#: The (all*, any*) field-name pairs. Every one carries the architectural
#: invariant `all_x implies any_x`, which holds for any non-empty selection.
DMSTATUS_ALL_ANY_PAIRS = (
    ("allhavereset", "anyhavereset"),
    ("allresumeack", "anyresumeack"),
    ("allnonexistent", "anynonexistent"),
    ("allunavail", "anyunavail"),
    ("allrunning", "anyrunning"),
    ("allhalted", "anyhalted"),
)


# ── hartsel helpers (spec #3.14.2, "hartsel" definition) ──────────────────────

#: Maximum architectural width of hartsel. An implementation's actual width is
#: HARTSELLEN, discoverable by writing all ones and reading back.
HARTSEL_MAX_WIDTH = 20


def hartsel_of(dmcontrol_word: int) -> int:
    """Assemble the 20-bit hartsel from its two disjoint dmcontrol fields."""
    hi = DMCONTROL.field("hartselhi").extract(dmcontrol_word)
    lo = DMCONTROL.field("hartsello").extract(dmcontrol_word)
    return (hi << 10) | lo


def with_hartsel(dmcontrol_word: int, hartsel: int) -> int:
    """Return `dmcontrol_word` with hartsel split across hartselhi/hartsello."""
    word = DMCONTROL.field("hartsello").insert(dmcontrol_word, hartsel & 0x3FF)
    return DMCONTROL.field("hartselhi").insert(word, (hartsel >> 10) & 0x3FF)


# ══════════════════════════════════════════════════════════════════════════════
# The abstract-command, program-buffer, hart-array and halt-group registers
#
# dmcontrol/dmstatus above are the run-control core. These are the rest of the
# DMI map the testplan exercises: the abstract-command engine (#3.14.6-#3.14.8),
# the program buffer (#3.14.9), the hart array mask (#3.14.4-#3.14.5), the halt
# summaries (#3.14.10) and dmcs2 (#3.14.3), which carries both halt/resume
# groups and the external-trigger selection.
#
# Bit positions are the spec's, cross-checked field for field against the DUT's
# own `dm_pkg.sv` packed structs (abstractcs_t, command_t, abstractauto_t,
# ac_ar_cmd_t, hartinfo_t) so that a disagreement between spec and RTL shows up
# here as a review question rather than as a silent mismatch at run time.
# ══════════════════════════════════════════════════════════════════════════════

# ── hartinfo — DMI 0x12 (#3.14.11) ────────────────────────────────────────────
#
# Read-only, and entirely implementation-defined: it tells a debugger where the
# selected hart keeps its `data` registers and how many dscratch registers it
# may borrow. Every field is "Preset", so none has an architectural reset value.

HARTINFO = Register(
    name="hartinfo",
    address=0x12,
    spec="#3.14.11",
    fields=(
        Field("nscratch", 20, 4, ACCESS_R, "#3.14.11 nscratch"),
        Field("dataaccess", 16, 1, ACCESS_R, "#3.14.11 dataaccess"),
        Field("datasize", 12, 4, ACCESS_R, "#3.14.11 datasize"),
        Field("dataaddr", 0, 12, ACCESS_R, "#3.14.11 dataaddr"),
    ),
)


# ── hawindowsel / hawindow — DMI 0x14, 0x15 (#3.14.4, #3.14.5) ────────────────
#
# The hart array mask, in 32-hart windows: hawindowsel picks the window,
# hawindow is that window's bitmask. Together with dmcontrol.hasel they select
# more than one hart at a time, which is what makes dmstatus's all*/any* pairs
# differ. A single-hart DM implements neither, so a debugger discovers them by
# writing and reading back.

HAWINDOWSEL = Register(
    name="hawindowsel",
    address=0x14,
    spec="#3.14.4",
    fields=(Field("hawindowsel", 0, 15, ACCESS_WARL, "#3.14.4 hawindowsel", reset=0),),
)

HAWINDOW = Register(
    name="hawindow",
    address=0x15,
    spec="#3.14.5",
    fields=(Field("maskdata", 0, 32, ACCESS_WARL, "#3.14.5 maskdata", reset=0),),
)

#: Harts per hawindow window (#3.14.5: hawindow is 32 bits wide).
HARTS_PER_HAWINDOW = 32


def hawindow_of(hart: int) -> Tuple[int, int]:
    """The (hawindowsel, bit index) that select `hart` in the hart array."""
    return divmod(hart, HARTS_PER_HAWINDOW)


# ── abstractcs — DMI 0x16 (#3.14.6) ───────────────────────────────────────────
#
# cmderr is W1C: a debugger clears it by writing all ones to the field, not by
# writing zero. It is also sticky -- until it is cleared, every further command
# is refused with the SAME error, which is why a sequence that forgets to clear
# it sees every later read return stale data (see trigger_sequence's `_try`).

ABSTRACTCS = Register(
    name="abstractcs",
    address=0x16,
    spec="#3.14.6",
    fields=(
        Field("progbufsize", 24, 5, ACCESS_R, "#3.14.6 progbufsize"),
        Field("busy", 12, 1, ACCESS_R, "#3.14.6 busy", reset=0),
        Field("relaxedpriv", 11, 1, ACCESS_WARL, "#3.14.6 relaxedpriv"),
        Field("cmderr", 8, 3, ACCESS_W1C, "#3.14.6 cmderr", reset=0),
        Field("datacount", 0, 4, ACCESS_R, "#3.14.6 datacount"),
    ),
)

#: abstractcs.cmderr encodings (#3.14.6 cmderr). `none` is the only value that
#: lets a further command start.
CMDERR_NONE = 0
CMDERR_BUSY = 1          # a command was written while another was running
CMDERR_NOT_SUPPORTED = 2  # the command, or its arguments, are unsupported
CMDERR_EXCEPTION = 3      # the command's own instructions took an exception
CMDERR_HALT_RESUME = 4    # the hart was not halted, or was resuming
CMDERR_BUS = 5            # a bus error while executing the command
CMDERR_OTHER = 7

#: The value a debugger writes to abstractcs.cmderr to clear it (W1C).
CMDERR_CLEAR = 7


# ── command — DMI 0x17 (#3.14.7) ──────────────────────────────────────────────
#
# One register with three meanings: cmdtype selects which, and `control` is
# decoded per type. Writing it starts the command; the DM reports the outcome
# in abstractcs.cmderr.

COMMAND = Register(
    name="command",
    address=0x17,
    spec="#3.14.7",
    fields=(
        Field("cmdtype", 24, 8, ACCESS_WARL, "#3.14.7 cmdtype"),
        Field("control", 0, 24, ACCESS_WARL, "#3.14.7 control"),
    ),
)

#: command.cmdtype encodings (#3.14.7 cmdtype).
CMDTYPE_ACCESS_REGISTER = 0
CMDTYPE_QUICK_ACCESS = 1
CMDTYPE_ACCESS_MEMORY = 2

#: Access Register (#3.14.7.1). `control` decoded as a register in its own
#: right, so a caller can encode/decode a command word field by field rather
#: than with shift arithmetic. Its bits are the full 32-bit command word's, so
#: COMMAND.encode(cmdtype=...) | ACCESS_REGISTER.encode(...) is one word.
ACCESS_REGISTER = Register(
    name="command.access_register",
    address=0x17,
    spec="#3.14.7.1",
    fields=(
        Field("aarsize", 20, 3, ACCESS_WARL, "#3.14.7.1 aarsize"),
        Field("aarpostincrement", 19, 1, ACCESS_WARL, "#3.14.7.1 aarpostincrement"),
        Field("postexec", 18, 1, ACCESS_WARL, "#3.14.7.1 postexec"),
        Field("transfer", 17, 1, ACCESS_WARL, "#3.14.7.1 transfer"),
        Field("write", 16, 1, ACCESS_WARL, "#3.14.7.1 write"),
        Field("regno", 0, 16, ACCESS_WARL, "#3.14.7.1 regno"),
    ),
)

#: Access Memory (#3.14.7.3). The address and data travel in the `data`
#: registers, not in the command word.
ACCESS_MEMORY = Register(
    name="command.access_memory",
    address=0x17,
    spec="#3.14.7.3",
    fields=(
        Field("aamvirtual", 23, 1, ACCESS_WARL, "#3.14.7.3 aamvirtual"),
        Field("aamsize", 20, 3, ACCESS_WARL, "#3.14.7.3 aamsize"),
        Field("aampostincrement", 19, 1, ACCESS_WARL, "#3.14.7.3 aampostincrement"),
        Field("write", 16, 1, ACCESS_WARL, "#3.14.7.3 write"),
        Field("target_specific", 14, 2, ACCESS_WARL, "#3.14.7.3 target-specific"),
    ),
)

#: aarsize/aamsize encodings: the access is 8 << size bits wide (#3.14.7.1).
AASIZE_32 = 2
AASIZE_64 = 3
AASIZE_128 = 4

#: regno ranges an Access Register command addresses (#3.14.7.1 regno).
REGNO_CSR_BASE = 0x0000
REGNO_GPR_BASE = 0x1000
REGNO_FPR_BASE = 0x1020


def regno_of_gpr(index: int) -> int:
    """regno for GPR x`index` (#3.14.7.1: 0x1000 + index)."""
    return REGNO_GPR_BASE + index


def regno_of_csr(number: int) -> int:
    """regno for CSR `number` (#3.14.7.1: the CSR number itself)."""
    return REGNO_CSR_BASE + number


# ── abstractauto — DMI 0x18 (#3.14.8) ─────────────────────────────────────────
#
# Re-executes the last command automatically when a `data` or `progbuf`
# register is accessed, which is how a debugger reads a block of memory without
# a DMI write per word. Optional: a DM that does not implement a bit reads it
# back as 0, so a debugger writes all ones to discover what is supported.

ABSTRACTAUTO = Register(
    name="abstractauto",
    address=0x18,
    spec="#3.14.8",
    fields=(
        Field("autoexecprogbuf", 16, 16, ACCESS_WARL, "#3.14.8 autoexecprogbuf", reset=0),
        Field("autoexecdata", 0, 12, ACCESS_WARL, "#3.14.8 autoexecdata", reset=0),
    ),
)


# ── dmcs2 — DMI 0x32 (#3.14.3) ────────────────────────────────────────────────
#
# Two features in one register, told apart by hgselect: halt/resume groups
# (hgselect=0) and the external triggers (hgselect=1). grouptype picks halt
# groups from resume groups; group 0 means "no group", which is the reset state
# and the only one a DM without halt groups implements.
#
# v1.0 only -- there is no DMI 0x32 in 0.13, so a read of it there is a
# nonexistent-register access, not a dmcs2 of zero.

DMCS2 = Register(
    name="dmcs2",
    address=0x32,
    spec="#3.14.3",
    fields=(
        Field("grouptype", 11, 1, ACCESS_WARL, "#3.14.3 grouptype", reset=0),
        Field("dmexttrigger", 7, 4, ACCESS_WARL, "#3.14.3 dmexttrigger", reset=0),
        Field("group", 2, 5, ACCESS_WARL, "#3.14.3 group", reset=0),
        Field("hgwrite", 1, 1, ACCESS_W1, "#3.14.3 hgwrite"),
        Field("hgselect", 0, 1, ACCESS_WARL, "#3.14.3 hgselect", reset=0),
    ),
)

#: dmcs2.grouptype encodings (#3.14.3 grouptype).
GROUPTYPE_HALT = 0
GROUPTYPE_RESUME = 1

#: group 0 is "not in any group" (#3.14.3 group), and the reset value.
GROUP_NONE = 0


# ── haltsum0-3 — DMI 0x40, 0x13, 0x34, 0x35 (#3.14.10) ────────────────────────
#
# A four-level tree: each bit of haltsum0 is one hart, each bit of haltsum1 is
# 32 harts, and so on. Only haltsum0 is meaningful on a single-hart DM, and the
# address order is not the level order -- haltsum1 sits at 0x13, below
# haltsum0 at 0x40.

HALTSUM0 = Register(name="haltsum0", address=0x40, spec="#3.14.10",
                    fields=(Field("haltsum0", 0, 32, ACCESS_R, "#3.14.10 haltsum0"),))
HALTSUM1 = Register(name="haltsum1", address=0x13, spec="#3.14.10",
                    fields=(Field("haltsum1", 0, 32, ACCESS_R, "#3.14.10 haltsum1"),))
HALTSUM2 = Register(name="haltsum2", address=0x34, spec="#3.14.10",
                    fields=(Field("haltsum2", 0, 32, ACCESS_R, "#3.14.10 haltsum2"),))
HALTSUM3 = Register(name="haltsum3", address=0x35, spec="#3.14.10",
                    fields=(Field("haltsum3", 0, 32, ACCESS_R, "#3.14.10 haltsum3"),))

#: Harts covered by one bit at each level of the haltsum tree (#3.14.10).
HALTSUM_LEVELS = (HALTSUM0, HALTSUM1, HALTSUM2, HALTSUM3)


def haltsum_bit(hart: int, level: int = 0) -> int:
    """The bit index in haltsum`level` that covers `hart` (#3.14.10)."""
    return (hart >> (5 * level)) & 0x1F if level else hart & 0x1F


# ── data0-11 and progbuf0-15 — DMI 0x04-0x0F, 0x20-0x2F (#3.14.9) ─────────────
#
# Arrays rather than named registers: their count is discovered from
# abstractcs.datacount and abstractcs.progbufsize, and accessing one beyond
# that count is an access to a nonexistent register.

DATA0, DATA11 = 0x04, 0x0F
PROGBUF0, PROGBUF15 = 0x20, 0x2F
NEXTDM = 0x1D
AUTHDATA = 0x30
CONFSTRPTR0 = 0x19


def data_address(index: int) -> int:
    """DMI address of data`index` (#3.14.9: data0 at 0x04)."""
    if not 0 <= index <= DATA11 - DATA0:
        raise ValueError(f"data{index} does not exist (data0-data11 only)")
    return DATA0 + index


def progbuf_address(index: int) -> int:
    """DMI address of progbuf`index` (#3.14.9: progbuf0 at 0x20)."""
    if not 0 <= index <= PROGBUF15 - PROGBUF0:
        raise ValueError(f"progbuf{index} does not exist (progbuf0-progbuf15 only)")
    return PROGBUF0 + index

# ══════════════════════════════════════════════════════════════════════════════
# Hart-side debug CSRs (Sdext ch.4) and the Trigger Module (Sdtrig ch.5)
#
# These live in the hart's CSR space, not in DMI space: a debugger reaches them
# through an Access Register abstract command, and native (self-hosted) debug
# code reaches the trigger CSRs directly. They are defined here, beside the DMI
# registers, because the same three consumers need them: predictor.py to model
# what a command writes, coverage.py to name bins, and the native-trigger model
# to decide whether a trigger fires.
#
# Field positions are for XLEN=64 where they differ: dcsr is 32 bits on both,
# but tdata1.type/dmode sit at [XLEN-1:XLEN-4] and [XLEN-5].
# ══════════════════════════════════════════════════════════════════════════════

#: dcsr — Debug Control and Status (Sdext 4.9.1), CSR 0x7b0. Accessible only
#: from Debug Mode: a read or write from M-mode raises an illegal instruction.
DCSR = Register(
    name="dcsr",
    address=0x7B0,
    spec="Sdext 4.9.1",
    fields=(
        Field("debugver", 28, 4, ACCESS_R, "Sdext 4.9.1 debugver", reset=4),
        Field("ebreakvs", 17, 1, ACCESS_WARL, "Sdext 4.9.1 ebreakvs", reset=0),
        Field("ebreakvu", 16, 1, ACCESS_WARL, "Sdext 4.9.1 ebreakvu", reset=0),
        Field("ebreakm", 15, 1, ACCESS_RW, "Sdext 4.9.1 ebreakm", reset=0),
        Field("ebreaks", 13, 1, ACCESS_WARL, "Sdext 4.9.1 ebreaks", reset=0),
        Field("ebreaku", 12, 1, ACCESS_WARL, "Sdext 4.9.1 ebreaku", reset=0),
        Field("stepie", 11, 1, ACCESS_WARL, "Sdext 4.9.1 stepie", reset=0),
        Field("stopcount", 10, 1, ACCESS_WARL, "Sdext 4.9.1 stopcount"),
        Field("stoptime", 9, 1, ACCESS_WARL, "Sdext 4.9.1 stoptime"),
        Field("cause", 6, 3, ACCESS_R, "Sdext 4.9.1 cause"),
        Field("v", 5, 1, ACCESS_WARL, "Sdext 4.9.1 v", reset=0),
        Field("mprven", 4, 1, ACCESS_WARL, "Sdext 4.9.1 mprven"),
        Field("nmip", 3, 1, ACCESS_R, "Sdext 4.9.1 nmip"),
        Field("step", 2, 1, ACCESS_RW, "Sdext 4.9.1 step", reset=0),
        Field("prv", 0, 2, ACCESS_WARL, "Sdext 4.9.1 prv"),
    ),
)

#: dcsr.cause values (Sdext 4.9.1, table "cause").
DCSR_CAUSE_EBREAK = 1
DCSR_CAUSE_TRIGGER = 2
DCSR_CAUSE_HALTREQ = 3
DCSR_CAUSE_STEP = 4
DCSR_CAUSE_RESETHALTREQ = 5

#: dpc and the two scratch registers (Sdext 4.9.2/4.9.3). dpc is XLEN wide and
#: has no fields; dscratch0/1 are free for the DM's use -- hartinfo.nscratch
#: says how many of them the DM takes, and a debugger must save/restore those.
DPC = Register(name="dpc", address=0x7B1, spec="Sdext 4.9.2", fields=())
DSCRATCH0 = Register(name="dscratch0", address=0x7B2, spec="Sdext 4.9.3", fields=())
DSCRATCH1 = Register(name="dscratch1", address=0x7B3, spec="Sdext 4.9.3", fields=())

#: tselect — which trigger tdata1/2/3 address (Sdtrig 5.7.1). WARL over the
#: implemented trigger indices: write all ones and read back to discover how
#: many there are.
TSELECT = Register(name="tselect", address=0x7A0, spec="Sdtrig 5.7.1", fields=())

#: tdata1 — the selected trigger's type and configuration (Sdtrig 5.7.2). The
#: type and dmode fields sit at the top of XLEN; everything below depends on
#: the type, so the per-type layouts are separate definitions.
TDATA1_TYPE_LSB_RV32, TDATA1_TYPE_LSB_RV64 = 28, 60

#: tdata1.type values (Sdtrig 5.7.2).
TRIGGER_TYPE_NONE = 0
TRIGGER_TYPE_MCONTROL = 2
TRIGGER_TYPE_ICOUNT = 3
TRIGGER_TYPE_ITRIGGER = 4
TRIGGER_TYPE_ETRIGGER = 5
TRIGGER_TYPE_MCONTROL6 = 6
TRIGGER_TYPE_TMEXTTRIGGER = 7
TRIGGER_TYPE_DISABLED = 15

#: tdata1.action values (Sdtrig, "Actions"). 0 is the native one: raise a
#: breakpoint exception, for software using triggers with no debugger attached.
TRIGGER_ACTION_BREAKPOINT = 0
TRIGGER_ACTION_DEBUG_MODE = 1

#: mcontrol6 (Sdtrig 5.7.12), the low fields; type/dmode are above them.
MCONTROL6 = Register(
    name="mcontrol6",
    address=0x7A1,
    spec="Sdtrig 5.7.12",
    fields=(
        Field("uncertain", 26, 1, ACCESS_WARL, "Sdtrig 5.7.12 uncertain", reset=0),
        Field("hit1", 25, 1, ACCESS_WARL, "Sdtrig 5.7.12 hit1", reset=0),
        Field("vs", 24, 1, ACCESS_WARL, "Sdtrig 5.7.12 vs", reset=0),
        Field("vu", 23, 1, ACCESS_WARL, "Sdtrig 5.7.12 vu", reset=0),
        Field("hit0", 22, 1, ACCESS_WARL, "Sdtrig 5.7.12 hit0", reset=0),
        Field("select", 21, 1, ACCESS_WARL, "Sdtrig 5.7.12 select", reset=0),
        Field("size", 16, 3, ACCESS_WARL, "Sdtrig 5.7.12 size", reset=0),
        Field("action", 12, 4, ACCESS_WARL, "Sdtrig 5.7.12 action", reset=0),
        Field("chain", 11, 1, ACCESS_WARL, "Sdtrig 5.7.12 chain", reset=0),
        Field("match", 7, 4, ACCESS_WARL, "Sdtrig 5.7.12 match", reset=0),
        Field("m", 6, 1, ACCESS_WARL, "Sdtrig 5.7.12 m", reset=0),
        Field("uncertainen", 5, 1, ACCESS_WARL, "Sdtrig 5.7.12 uncertainen", reset=0),
        Field("s", 4, 1, ACCESS_WARL, "Sdtrig 5.7.12 s", reset=0),
        Field("u", 3, 1, ACCESS_WARL, "Sdtrig 5.7.12 u", reset=0),
        Field("execute", 2, 1, ACCESS_WARL, "Sdtrig 5.7.12 execute", reset=0),
        Field("store", 1, 1, ACCESS_WARL, "Sdtrig 5.7.12 store", reset=0),
        Field("load", 0, 1, ACCESS_WARL, "Sdtrig 5.7.12 load", reset=0),
    ),
)

#: icount (Sdtrig 5.7.13): fire after `count` instructions retire in an enabled
#: mode. `pending` is set when count reaches 0 and cleared as the trigger fires.
ICOUNT = Register(
    name="icount",
    address=0x7A1,
    spec="Sdtrig 5.7.13",
    fields=(
        Field("vs", 26, 1, ACCESS_WARL, "Sdtrig 5.7.13 vs", reset=0),
        Field("vu", 25, 1, ACCESS_WARL, "Sdtrig 5.7.13 vu", reset=0),
        Field("hit", 24, 1, ACCESS_WARL, "Sdtrig 5.7.13 hit", reset=0),
        Field("count", 10, 14, ACCESS_WARL, "Sdtrig 5.7.13 count", reset=1),
        Field("m", 9, 1, ACCESS_WARL, "Sdtrig 5.7.13 m", reset=0),
        Field("pending", 8, 1, ACCESS_RW, "Sdtrig 5.7.13 pending", reset=0),
        Field("s", 7, 1, ACCESS_WARL, "Sdtrig 5.7.13 s", reset=0),
        Field("u", 6, 1, ACCESS_WARL, "Sdtrig 5.7.13 u", reset=0),
        Field("action", 0, 6, ACCESS_WARL, "Sdtrig 5.7.13 action", reset=0),
    ),
)

#: itrigger (5.7.14) and etrigger (5.7.15): fire on an interrupt or exception
#: taken FROM an enabled mode, before the handler's first instruction. Their
#: m/s/u bits name the mode the trap came from, not the mode it goes to.
ITRIGGER = Register(
    name="itrigger",
    address=0x7A1,
    spec="Sdtrig 5.7.14",
    fields=(
        Field("hit", 24, 1, ACCESS_WARL, "Sdtrig 5.7.14 hit", reset=0),
        Field("vs", 12, 1, ACCESS_WARL, "Sdtrig 5.7.14 vs", reset=0),
        Field("vu", 11, 1, ACCESS_WARL, "Sdtrig 5.7.14 vu", reset=0),
        Field("nmi", 10, 1, ACCESS_WARL, "Sdtrig 5.7.14 nmi", reset=0),
        Field("m", 9, 1, ACCESS_WARL, "Sdtrig 5.7.14 m", reset=0),
        Field("s", 7, 1, ACCESS_WARL, "Sdtrig 5.7.14 s", reset=0),
        Field("u", 6, 1, ACCESS_WARL, "Sdtrig 5.7.14 u", reset=0),
        Field("action", 0, 6, ACCESS_WARL, "Sdtrig 5.7.14 action", reset=0),
    ),
)

ETRIGGER = Register(
    name="etrigger",
    address=0x7A1,
    spec="Sdtrig 5.7.15",
    fields=(
        Field("hit", 24, 1, ACCESS_WARL, "Sdtrig 5.7.15 hit", reset=0),
        Field("vs", 12, 1, ACCESS_WARL, "Sdtrig 5.7.15 vs", reset=0),
        Field("vu", 11, 1, ACCESS_WARL, "Sdtrig 5.7.15 vu", reset=0),
        Field("m", 9, 1, ACCESS_WARL, "Sdtrig 5.7.15 m", reset=0),
        Field("s", 7, 1, ACCESS_WARL, "Sdtrig 5.7.15 s", reset=0),
        Field("u", 6, 1, ACCESS_WARL, "Sdtrig 5.7.15 u", reset=0),
        Field("action", 0, 6, ACCESS_WARL, "Sdtrig 5.7.15 action", reset=0),
    ),
)

#: tdata2 (5.7.3): the match value -- an address, or a cause bitmask for
#: itrigger/etrigger. tdata3/textra (5.7.4) is context matching; a DUT without
#: it must raise an illegal instruction on access, since no implemented trigger
#: uses that register.
TDATA2 = Register(name="tdata2", address=0x7A2, spec="Sdtrig 5.7.3", fields=())
TDATA3 = Register(name="tdata3", address=0x7A3, spec="Sdtrig 5.7.4", fields=())

#: tinfo (5.7.6): bit N set means trigger type N is supported by the selected
#: trigger; bit 0 means the trigger does not exist.
TINFO = Register(
    name="tinfo",
    address=0x7A4,
    spec="Sdtrig 5.7.6",
    fields=(Field("version", 24, 8, ACCESS_R, "Sdtrig 5.7.6 version"),
            Field("info", 0, 16, ACCESS_R, "Sdtrig 5.7.6 info")),
)

#: The hart-side registers, keyed by CSR number. Separate from REGISTERS: these
#: are not reachable over DMI directly, only through an abstract command.
CSR_REGISTERS: Dict[int, Register] = {
    r.address: r for r in (DCSR, DPC, DSCRATCH0, DSCRATCH1,
                           TSELECT, TDATA2, TDATA3, TINFO)
}

#: tdata1 layouts by trigger type, for decoding what a write configured.
TDATA1_LAYOUTS: Dict[int, Register] = {
    TRIGGER_TYPE_MCONTROL6: MCONTROL6,
    TRIGGER_TYPE_ICOUNT: ICOUNT,
    TRIGGER_TYPE_ITRIGGER: ITRIGGER,
    TRIGGER_TYPE_ETRIGGER: ETRIGGER,
}


def tdata1_type(word: int, xlen: int = 64) -> int:
    """The type field of a tdata1 word, which sits at [XLEN-1:XLEN-4]."""
    lsb = TDATA1_TYPE_LSB_RV64 if xlen == 64 else TDATA1_TYPE_LSB_RV32
    return (word >> lsb) & 0xF


def tdata1_dmode(word: int, xlen: int = 64) -> int:
    """tdata1.dmode: set means only Debug Mode may write this trigger."""
    lsb = TDATA1_TYPE_LSB_RV64 if xlen == 64 else TDATA1_TYPE_LSB_RV32
    return (word >> (lsb - 1)) & 1


#: Every DMI register this model defines, keyed by DMI address. Being here says
#: the register's fields are known, NOT that a read of it can be predicted --
#: that is `predictor.has_model()`, which is a narrower set and depends on the
#: declared DUT configuration.
REGISTERS: Dict[int, Register] = {
    r.address: r
    for r in (
        DMCONTROL, DMSTATUS, HARTINFO, HALTSUM1, HAWINDOWSEL, HAWINDOW,
        ABSTRACTCS, COMMAND, ABSTRACTAUTO, DMCS2, HALTSUM2, HALTSUM3, HALTSUM0,
    )
}


def register_at(address: int) -> Optional[Register]:
    """Look up a modeled register by DMI address, or None if unmodeled."""
    return REGISTERS.get(address)
