#!/usr/bin/env python3
"""
dm_cov_summary.py — turn dm_cov.sh's per-instance report into one table.

`imc`'s text report states counts per instance and never a percentage, and it
has no notion of "the Debug Module" as a unit — `report -inst X` covers only X,
with no recursion. So the DM's actual numbers have to be summed across the
instances that make it up. Doing that by hand is how a number gets quoted that
nobody can reproduce.

Toggle coverage is reported separately rather than folded into one figure. It
is dominated by wide buses whose upper bits a single-hart, 32-bit-DMI
configuration never drives, so averaging it with block coverage produces a
number that is neither.

    python3 dm_cov_summary.py out/dm_code.rpt
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

METRICS = (
    ("block", r"Number of covered blocks:\s*(\d+) of (\d+)"),
    ("expression", r"Number of covered expressions:\s*(\d+) of (\d+)"),
    ("toggle", r"Number of covered signal bits:\s*(\d+) of (\d+)"),
)


def main() -> int:
    if len(sys.argv) != 2:
        return int(bool(sys.stderr.write(f"usage: {sys.argv[0]} <dm_code.rpt>\n")))
    path = Path(sys.argv[1])
    if not path.exists():
        return int(bool(sys.stderr.write(f"no such report: {path}\n")))

    # dm_cov.sh writes "== <instance>" before each instance's section.
    parts = re.split(r"^== (\S+)$", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    if not parts:
        return int(bool(sys.stderr.write(
            f"{path}: no '== <instance>' markers -- was this written by dm_cov.sh?\n")))

    rows, totals = [], {m: [0, 0] for m, _ in METRICS}
    for name, body in zip(parts[0::2], parts[1::2]):
        cells = []
        for metric, pat in METRICS:
            m = re.search(pat, body)
            if m:
                hit, of = int(m.group(1)), int(m.group(2))
                totals[metric][0] += hit
                totals[metric][1] += of
                cells.append(f"{100 * hit / of:6.2f}% ({hit}/{of})")
            else:
                # A wrapper with no logic of its own has no block section at
                # all. Say so rather than printing 0%, which reads as a hole.
                cells.append("—")
        rows.append((name.split(".", 2)[-1], cells))

    w = max(len(r[0]) for r in rows) + 2
    hdr = f"{'instance':<{w}}" + "".join(f"{m:>20}" for m, _ in METRICS)
    print("\n=== Debug Module code coverage (DM instances only) ===")
    print(hdr)
    print("-" * len(hdr))
    for name, cells in rows:
        print(f"{name:<{w}}" + "".join(f"{c:>20}" for c in cells))
    print("-" * len(hdr))
    tot = "".join(
        f"{(f'{100 * totals[m][0] / totals[m][1]:6.2f}% ({totals[m][0]}/{totals[m][1]})' if totals[m][1] else '—'):>20}"
        for m, _ in METRICS)
    print(f"{'DEBUG MODULE TOTAL':<{w}}" + tot)
    print("\nToggle is listed separately on purpose: it is dominated by wide buses")
    print("whose upper bits a single-hart, 32-bit-DMI configuration never drives.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
