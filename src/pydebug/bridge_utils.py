"""
bridge_utils.py — Utility functions for locating shipped C and SV source files.

These functions allow integrators to find the installed pydebug bridge sources
for inclusion in their simulator build scripts (Makefiles, Vivado TCL, etc.).

Usage:
    from pydebug.bridge_utils import get_c_bridge_files
    for f in get_c_bridge_files():
        print(f"  -I{f.parent} {f}")  # add to simulator compile command
"""

from pathlib import Path


def _package_dir() -> Path:
    """Return the root directory of the installed pydebug package."""
    return Path(__file__).parent


def get_c_bridge_dir() -> Path:
    """Return the directory containing C bridge sources (uvm_bridge.c, etc.)."""
    return _package_dir() / "c_bridge"


def get_sv_kit_dir() -> Path:
    """Return the directory containing SV integration kit files."""
    return _package_dir() / "sv_kit"


def get_template_dir() -> Path:
    """Return the directory containing example testbench tops."""
    return get_sv_kit_dir() / "templates"


def get_example_configs_dir() -> Path:
    """Return the directory containing example JSON/OpenOCD configs."""
    return get_sv_kit_dir() / "configs"


def get_c_bridge_files() -> list[Path]:
    """Return a list of all C bridge source file paths."""
    d = get_c_bridge_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.[ch]"))


def get_sv_kit_files() -> list[Path]:
    """Return all shared SV VIP/kit source paths (excludes templates/).

    Testbench tops under templates/ are per-SoC starting points meant to be
    copied out via `pydebug init`, not compiled alongside the shared kit —
    a customer's own tb_top_<soc>.sv would otherwise be compiled twice, and
    an unrelated SoC's template would be pulled in as a duplicate top module.
    """
    d = get_sv_kit_dir()
    if not d.exists():
        return []
    templates_dir = get_template_dir()
    return sorted(
        f for f in d.glob("**/*.sv")
        if templates_dir not in f.parents
    )
