"""
model/dut_config.py — Loads the declared, per-target implementation-defined
values (dut_configs/*.json) into DMPredictor/DebugCoverageModel kwargs.

Every field here is either a spec "Preset"/declared-capability bit
(stickyunavail, impebreak, hasresethaltreq, ...) or a field the spec
explicitly leaves implementation-defined (havereset's reset value, "-" in
dm_registers.xml). None of it is derivable from other fields or from the
RTL by inspection alone -- it must be stated once, per target, and every
consumer (the SV dm_ref_model via dm_checker.sv, and this Python model)
reads the same declaration rather than each carrying its own copy or
guessing from what a specific RTL build happens to output.

Usage:
    from pydebug.model.dut_config import load_dut_config
    from pydebug.model.predictor import DMPredictor

    cfg = load_dut_config("cva6")
    p = DMPredictor(**cfg.predictor_kwargs())
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union

from .registers import (
    DMSTATUS_VERSION_0_13,
    DMSTATUS_VERSION_1_0,
)

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "dut_configs"

_VERSION_STRINGS = {
    "0.13": DMSTATUS_VERSION_0_13,
    "1.0": DMSTATUS_VERSION_1_0,
}


@dataclass(frozen=True)
class DutConfig:
    """The declared capability set for one real target, as read from
    dut_configs/<name>.json."""

    dut: str
    version: int
    authenticated: bool
    impebreak: bool
    hasresethaltreq: bool
    supports_hartreset: bool
    supports_hasel: bool
    resumeack_reset: bool
    stickyunavail: bool
    havereset_poweron: bool
    #: Every other declared key (Presets and optional features), as read.
    #: Only declared_config() interprets them.
    raw: Dict[str, Any]

    def predictor_kwargs(self) -> Dict[str, Any]:
        """kwargs suitable for DMPredictor(**...) / ModelBackedMockTransport(**...)."""
        return {
            "version": self.version,
            "authenticated": self.authenticated,
            "impebreak": self.impebreak,
            "hasresethaltreq": self.hasresethaltreq,
            "supports_hartreset": self.supports_hartreset,
            "supports_hasel": self.supports_hasel,
            "resumeack_reset": self.resumeack_reset,
            "stickyunavail": self.stickyunavail,
            "havereset_poweron": self.havereset_poweron,
        }


    def declared_config(self, num_harts: int = 1):
        """The whole declaration as a DeclaredConfig, the Python twin of the
        dm_cfg_t that dm_checker.sv's read_cfg() builds from the same file.
        Every key is required, as it is there: a missing Preset must fail
        loudly rather than be guessed."""
        from .predictor import DeclaredConfig

        r = self.raw

        def num(key: str) -> int:
            v = r[key]
            return int(v, 0) if isinstance(v, str) else int(v)

        flags = ("sba_enable", "abstractauto_enable", "hartarray_enable",
                 "authentication_enable", "haltgroups_enable", "relaxedpriv_reset",
                 "dataaccess", "sbaccess_writable", "sbaccess128", "sbaccess64",
                 "sbaccess32", "sbaccess16", "sbaccess8")
        numbers = ("progbufsize", "datacount", "nscratch", "datasize", "dataaddr",
                   "sbversion", "sbasize", "sbaccess_reset", "nextdm")
        return DeclaredConfig(
            num_harts=num_harts,
            **{k: bool(r[k]) for k in flags},
            **{k: num(k) for k in numbers},
            **self.predictor_kwargs(),
        )


def load_dut_config(name: Union[str, Path]) -> DutConfig:
    """Load dut_configs/<name>.json (e.g. "ibex", "cva6"), or a .json path.

    Raises FileNotFoundError with the searched path if the DUT name has no
    declared config yet -- deliberately not a silent default, since every
    field here is a fact about real hardware that must be stated, not
    guessed.
    """
    path = Path(name) if str(name).endswith(".json") else _CONFIG_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No DUT config declared at {path}")
    raw = json.loads(path.read_text())

    version_str = raw["version"]
    if version_str not in _VERSION_STRINGS:
        raise ValueError(
            f"{path}: unknown version {version_str!r} "
            f"(expected one of {sorted(_VERSION_STRINGS)})"
        )

    return DutConfig(
        dut=raw["dut"],
        version=_VERSION_STRINGS[version_str],
        authenticated=bool(raw["authenticated"]),
        impebreak=bool(raw["impebreak"]),
        hasresethaltreq=bool(raw["hasresethaltreq"]),
        supports_hartreset=bool(raw["supports_hartreset"]),
        supports_hasel=bool(raw["supports_hasel"]),
        resumeack_reset=bool(raw["resumeack_reset"]),
        stickyunavail=bool(raw["stickyunavail"]),
        havereset_poweron=bool(raw["havereset_poweron"]),
        raw=raw,
    )
