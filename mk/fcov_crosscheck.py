#!/usr/bin/env python3
"""
fcov_crosscheck.py -- replay a run's DMI stream through the Python coverage
model and compare it, bin for bin, with what the SystemVerilog covergroups
recorded for the same run.

`src/pydebug/sv/fcov/covergroups.sv` is the coverage of record. The Python twin
in `pydebug.model.coverage` exists so a replay -- of a trace, of a unit test, of
a hardware session -- can be scored without a simulator. Two models of the same
thing, written by hand, agree only until someone changes one of them, which is
what this script catches: it feeds the recorded DMI traffic to the Python model
and diffs the resulting bins against `imc`'s functional report.

Only the DMI-visible covergroups are compared. The Sdext groups
(cg_debug_entry, cg_step_external, cg_hart_mode) and the two that read the DM's
own registers (cg_abstract_cmd, cg_sba) sample backdoors that no replay of the
DMI stream can reconstruct; the Python model registers them as exclusions and
this script lists them as "not modelled" rather than quietly skipping them.

    python3 mk/fcov_crosscheck.py out/functional.rpt \\
        cva6_sim/sim_outputs/coverage/*.model_trace

Exit status is 1 if a bin is hit on one side and not the other.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydebug.api.observer import OP_READ, OP_WRITE            # noqa: E402
from pydebug.model.coverage import DebugCoverageModel          # noqa: E402


def replay(traces: list[Path], cov: DebugCoverageModel) -> DebugCoverageModel:
    """Feed every trace's DMI accesses to one coverage model, in file order.

    The trace records what the SV reference model saw: `W <addr> <data>` for a
    write and `R <addr> <rtl> ...` for a read. That is the same stream the
    covergroups sample, so replaying it is the like-for-like comparison.
    """
    for path in traces:
        for line in path.read_text(errors="replace").splitlines():
            f = line.split()
            if len(f) >= 3 and f[0] == "W":
                cov.sample(OP_WRITE, int(f[1], 16), int(f[2], 16), None)
            elif len(f) >= 3 and f[0] == "R":
                cov.sample(OP_READ, int(f[1], 16), None, int(f[2], 16))
    return cov


def parse_sv_report(path: Path) -> dict[tuple[str, str, str], bool]:
    """{(covergroup, coverpoint, bin): hit} from imc's functional report.

    The report is indented by depth: a covergroup at column 0, its coverpoints
    under `|--`, and their bins under `| |--`. Cross bins are skipped: the
    Python model has no crosses in this slice.
    """
    out: dict[tuple[str, str, str], bool] = {}
    group = point = ""
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"^(cg_\w+)\s", line)
        if m:
            group, point = m.group(1), ""
            continue
        m = re.match(r"^\|--(\w+)\s+(\S+)", line)
        if m:
            point = m.group(1)
            continue
        m = re.match(r"^\| \|--(\S+)\s+(\d+\.\d+)%", line)
        if m and group and point.startswith("cp_"):
            name, pct = m.group(1), float(m.group(2))
            if "," in name:                      # a cross bin
                continue
            out[(group, point, name)] = pct > 0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="imc functional report (out/functional.rpt)")
    ap.add_argument("traces", nargs="+")
    a = ap.parse_args()

    sv = parse_sv_report(Path(a.report))
    if not sv:
        print(f"{a.report}: no covergroup bins parsed -- wrong file?", file=sys.stderr)
        return 1
    # The run-control slice's exclusions depend on the DUT (stickyunavail, the
    # hart count); the trace names its config in a "C" record. Its own warnings
    # are silenced here: this script compares the external-debug bins, and the
    # run-control model has its own test.
    logging.getLogger("pydebug.model.coverage").setLevel(logging.ERROR)
    traces = [Path(t) for t in a.traces]
    cov = replay(traces, DebugCoverageModel(supports_stickyunavail=True))
    report = cov.report()
    py_hit = {k for k in report["hit"]}
    py_bins = {b for b in report["counts"]}

    #: Run-control groups the Python model has always had, under its own names
    #: (dmi_access, dmcontrol.*, dmstatus.*, cross.*). They are covered by the
    #: model's own closure test, not by this bin-for-bin comparison.
    RUN_CONTROL = {"cg_dmi_access", "cg_dmcontrol_write", "cg_dmstatus_read",
                   "cg_hart_transition"}
    groups = {g for g, _p, _b in sv}
    modelled = sorted(groups & {k.split(".")[0] for k in py_bins})
    run_control = sorted(groups & RUN_CONTROL)
    not_modelled = sorted(groups - set(modelled) - RUN_CONTROL)

    agree, only_sv, only_py, missing = 0, [], [], []
    for (group, point, name), hit in sorted(sv.items()):
        if group not in modelled:
            continue
        key = f"{group}.{point}.{name}"
        if key not in py_bins:
            missing.append(key)
            continue
        if hit == (key in py_hit):
            agree += 1
        elif hit:
            only_sv.append(key)
        else:
            only_py.append(key)

    print(f"compared {len(a.traces)} trace(s) against {a.report}")
    print(f"  covergroups modelled : {', '.join(modelled)}")
    print(f"  modelled under the Python model's own names (its own closure "
          f"test): {', '.join(run_control) or 'none'}")
    print(f"  not modelled (DM/hart backdoor, stated exclusions): "
          f"{', '.join(not_modelled) or 'none'}")
    print(f"  bins agreeing        : {agree}")
    for label, items in (("hit in SV, not in the Python model", only_sv),
                         ("hit in the Python model, not in SV", only_py),
                         ("in SV, absent from the Python model", missing)):
        if items:
            print(f"  {label}: {len(items)}")
            for k in items:
                print(f"    {k}")
    hit_exclusions = [k for k in report["excluded_hits"] if not k.startswith("cg_")]
    if hit_exclusions:
        print(f"  run-control exclusions the suite hits anyway (not part of this "
              f"comparison): {', '.join(hit_exclusions)}")

    bad = only_sv + only_py + missing
    print("MISMATCH" if bad else "the two models agree on every compared bin")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
