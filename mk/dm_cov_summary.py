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

#: (metric, covered-of-total pattern, excluded-count pattern). imc leaves
#: excluded items out of the total, so a report written after `source
#: dm_exclusions.tcl` sums the same way; the excluded count is shown beside it
#: so a 100% never hides how much was taken out to get there.
METRICS = (
    ("block", r"Number of covered blocks:\s*(\d+) of (\d+)",
     r"Number of excluded blocks:\s*(\d+)"),
    ("expression", r"Number of covered expressions:\s*(\d+) of (\d+)",
     r"Number of excluded expressions:\s*(\d+)"),
    ("toggle", r"Number of covered signal bits:\s*(\d+) of (\d+)",
     r"Number of excluded signal bits:\s*(\d+)"),
    ("fsm state", r"Number of covered states:\s*(\d+) of (\d+)",
     r"Number of excluded states:\s*(\d+)"),
    ("fsm transition", r"Number of covered transitions:\s*(\d+) of (\d+)",
     r"Number of excluded transitions:\s*(\d+)"),
)


def main() -> int:
    if len(sys.argv) not in (2, 3):
        return int(bool(sys.stderr.write(f"usage: {sys.argv[0]} <dm_code.rpt> [title]\n")))
    path = Path(sys.argv[1])
    title = sys.argv[2] if len(sys.argv) == 3 else "Debug subsystem code coverage (JTAG/DTM, DM, its bus bridges, ndmreset, and the processor boundary)"
    if not path.exists():
        return int(bool(sys.stderr.write(f"no such report: {path}\n")))

    # dm_cov.sh writes "== <instance>" before each instance's section.
    parts = re.split(r"^== (\S+)$", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    if not parts:
        return int(bool(sys.stderr.write(
            f"{path}: no '== <instance>' markers -- was this written by dm_cov.sh?\n")))

    def cell(hit: int, of: int, excl: int) -> str:
        pct = f"{100 * hit / of:6.2f}%" if of else "   n/a"
        return f"{pct} ({hit}/{of}" + (f", {excl} excl)" if excl else ")")

    rows, totals = [], {m: [0, 0, 0] for m, *_ in METRICS}
    for name, body in zip(parts[0::2], parts[1::2]):
        cells = []
        for metric, pat, xpat in METRICS:
            m = re.search(pat, body)
            if m:
                hit, of = int(m.group(1)), int(m.group(2))
                x = re.search(xpat, body)
                excl = int(x.group(1)) if x else 0
                for i, v in enumerate((hit, of, excl)):
                    totals[metric][i] += v
                cells.append(cell(hit, of, excl))
            else:
                # A wrapper with no logic of its own has no block section at
                # all. Say so rather than printing 0%, which reads as a hole.
                cells.append("—")
        rows.append((name.split(".", 2)[-1], cells))

    w = max(len(r[0]) for r in rows) + 2
    cw = 27
    hdr = f"{'instance':<{w}}" + "".join(f"{m:>{cw}}" for m, *_ in METRICS)
    print(f"\n=== {title} ===")
    print(hdr)
    print("-" * len(hdr))
    for name, cells in rows:
        print(f"{name:<{w}}" + "".join(f"{c:>{cw}}" for c in cells))
    print("-" * len(hdr))
    tot = "".join(
        f"{(cell(*totals[m]) if totals[m][1] else '—'):>{cw}}" for m, *_ in METRICS)
    print(f"{'DEBUG SUBSYSTEM TOTAL':<{w}}" + tot)
    print("\nToggle is listed separately on purpose: it is dominated by wide buses")
    print("whose upper bits a single-hart, 32-bit-DMI configuration never drives.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
