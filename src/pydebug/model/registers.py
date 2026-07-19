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
    #3.14.1  dmstatus   (Debug Module Status,  DMI 0x11)
    #3.14.2  dmcontrol  (Debug Module Control, DMI 0x10)
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

ACCESS_R = "R"
ACCESS_RW = "R/W"
ACCESS_W1 = "W1"
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


#: Registers this model knows about, keyed by DMI address.
REGISTERS: Dict[int, Register] = {
    DMCONTROL.address: DMCONTROL,
    DMSTATUS.address: DMSTATUS,
}


def register_at(address: int) -> Optional[Register]:
    """Look up a modeled register by DMI address, or None if unmodeled."""
    return REGISTERS.get(address)
