#!/usr/bin/env python3
"""
dm_cov_exclude.py — generate imc code-coverage exclusions for the Debug Module.

Exclusions are derived from *justified patterns* matched against the coverage
report, never from hand-copied block indices. Indices shift whenever the RTL
moves by a line, and a stale index silently excludes the wrong block -- which
is worse than no exclusion at all, because it inflates coverage while looking
deliberate.

Every rule carries the reason the code is unreachable **on this DUT**, and the
condition that would make it reachable again. A rule that stops matching is
reported rather than ignored: if RTL-002 is fixed, the sbaccess rules stop
matching and the report says so, which is the signal to delete them.

    python3 mk/dm_cov_exclude.py out/dm_code.rpt --out out/dm_exclusions.tcl

Then, in imc:
    load -run <merged>
    source out/dm_exclusions.tcl
    report -detail -all -metrics code -inst <...> -out excluded.rpt
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: (rule name, source regex, reason, what would make it reachable)
RULES = [
    ("sba-access-size",
     r"3'b(001|010): begin|be_mask\[int'|else\s+be_mask = '1",
     "sbcs.sbaccess is hardwired to 3 (64-bit) by dm_csrs.sv:618, so the "
     "8/16/32-bit byte-enable arms can never be selected",
     "issue #147 (RTL-002) fixed, making sbaccess writable"),

    ("sba-unsupported-size",
     r"sbaccess_i > 3",
     "the spec's sberror=4 path needs sbaccess to hold an unsupported value; "
     "it is hardwired to 3 and cannot",
     "issue #147 (RTL-002) fixed"),

    ("readbyteenable-param",
     r"if \(ReadByteEnable\) be = be_mask",
     "ReadByteEnable is a compile-time parameter, so one arm is dead by "
     "parameterisation rather than by stimulus",
     "a build with the opposite ReadByteEnable value"),

    ("multi-hart-haltsum",
     r"dm::HaltSum[123]",
     "haltsum1/2/3 only exist above 32 harts; this SoC has one",
     "a multi-hart configuration"),

    ("multi-hart-state",
     r"stickyunavail_d\[i\]|resumereq_wdata_aligned\[wdata_hartsel\]",
     "requires a second hart, or a hart reporting unavailable; this SoC has "
     "one hart and it is always available",
     "a multi-hart configuration, or a hart that can go unavailable"),
]


def parse(report: Path):
    """Yield (instance, block_index, source) for every uncovered block."""
    txt = report.read_text(encoding="utf-8", errors="replace")
    for name, body in zip(*[iter(re.split(r"^== (\S+)$", txt, flags=re.M)[1:])] * 2):
        sec = re.search(r"Block Detail Report.*?(?=Expression Detail|Toggle Detail|\Z)",
                        body, re.S)
        if not sec:
            continue
        for hit, idx, _line, _kind, _org, src in re.findall(
                r"^(\d+)\s+(\d+)\s+(\d+)\s+(\S.*?)\s{2,}(\d+)\s+(.*)$", sec.group(0), re.M):
            if hit == "0":
                yield name, idx, src.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--out", default="dm_exclusions.tcl")
    a = ap.parse_args()

    rows = list(parse(Path(a.report)))
    if not rows:
        return int(bool(sys.stderr.write(
            f"{a.report}: no uncovered blocks found -- wrong file, or nothing to exclude\n")))

    matched: dict[str, list] = {r[0]: [] for r in RULES}
    unmatched = []
    for inst, idx, src in rows:
        for rule, pat, _why, _when in RULES:
            if re.search(pat, src):
                matched[rule].append((inst, idx, src))
                break
        else:
            unmatched.append((inst, idx, src))

    out = ["# " + "=" * 74,
           "# Debug Module code-coverage exclusions -- GENERATED, do not hand-edit.",
           "#   python3 mk/dm_cov_exclude.py <dm_code.rpt> --out <this file>",
           "#",
           "# Each exclusion states why the code is unreachable ON THIS DUT and what",
           "# would make it reachable again. Nothing is excluded for being hard.",
           "# " + "=" * 74, ""]
    total = 0
    for rule, _pat, why, when in RULES:
        hits = matched[rule]
        out.append(f"# ---- {rule} ({len(hits)} block(s)) ----")
        out += [f"#   why       : {why}", f"#   reachable : {when}"]
        if not hits:
            out.append("#   NO LONGER MATCHES -- the code is covered or gone; delete this rule.")
        for inst, idx, src in hits:
            total += 1
            out.append(f'exclude -inst {{{inst}}} -block {idx} '
                       f'-comment {{{rule}: {why}}}')
        out.append("")
    Path(a.out).write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"wrote {a.out}: {total} exclusion(s) across "
          f"{sum(1 for r in RULES if matched[r[0]])} rule(s)")
    if unmatched:
        print(f"\n{len(unmatched)} uncovered block(s) NOT excluded -- these are real "
              f"coverage holes, not unreachable code:")
        for inst, idx, src in unmatched[:40]:
            print(f"  {inst.split('.')[-1]:<12} block {idx:<4} {src[:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
