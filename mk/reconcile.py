#!/usr/bin/env python3
"""
reconcile.py — cross-check a coverage model against a testplan, both ways.

The coverage model and the testplan are built independently from the same
specification, by different authors or at least in separate passes. This script
compares them mechanically, so the comparison is not performed by the same
reasoning that produced either side.

It reports two kinds of disagreement, and both are findings:

  bins with no testplan item   a hole -- nobody planned to exercise this
  items hitting no bin         a blind spot in the model, or a test with no
                               verification objective

Agreement is the only result that confirms anything.

    python3 reconcile.py coverage.yaml --testplan ../testplans/plan.md
    python3 reconcile.py coverage.yaml --testplan plan.yaml --emit-holes holes.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: python3 -m pip install --user pyyaml")

TC_ID = re.compile(r"\b((?:TC-)?[A-Z][A-Z0-9]{1,8}-\d{3}(?:-[A-Z0-9]{1,3})?)\b")


def load_coverage(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_testplan(path: str) -> tuple[dict[str, str], str]:
    """
    Return ({item_id: description}, raw_text).

    Accepts a generated YAML plan or a markdown table plan -- a coverage model
    should not care which form the testplan author chose.
    """
    text = Path(path).read_text(encoding="utf-8")
    items: dict[str, str] = {}

    if path.endswith((".yaml", ".yml")):
        doc = yaml.safe_load(text) or {}
        for row in doc.get("tests", []):
            rid = row.get("id", "")
            if rid:
                items[rid] = " ".join(str(row.get(k, "")) for k in
                                      ("summary", "objective", "description"))
        return items, text

    # Markdown: every table row whose first cell is an item id.
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if cells and TC_ID.fullmatch(cells[0]):
            items[cells[0]] = " ".join(cells[1:])
    return items, text


def bins_of(cov: dict):
    """Yield (covergroup, coverpoint, bin, record) across the model."""
    for cg in cov.get("covergroups", []):
        cgname = cg.get("name", "?")
        for cp in cg.get("coverpoints", []):
            cpname = cp.get("name", "?")
            for b in cp.get("bins", []):
                yield cgname, cpname, b.get("name", "?"), b
        for x in cg.get("crosses", []):
            xname = x.get("name", "?")
            for b in x.get("bins", []) or [{"name": "(all cells)", **x}]:
                yield cgname, xname, b.get("name", "?"), b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("coverage")
    ap.add_argument("--testplan", required=True)
    ap.add_argument("--emit-holes", metavar="PATH")
    ap.add_argument("--scope", help="comma-separated id prefixes to check for orphans (default: inferred from what the model claims)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    cov = load_coverage(a.coverage)
    items, plan_text = load_testplan(a.testplan)

    # ── Structural check, before any testplan comparison ──────────────────
    # A cross naming a coverpoint that does not exist generates SystemVerilog
    # that will not compile, and the reconciler would otherwise report the
    # model as healthy. Catch it here rather than at elaboration.
    structural: list[str] = []
    for cg in cov.get("covergroups", []):
        defined = {cp.get("name") for cp in cg.get("coverpoints", [])}
        for x in cg.get("crosses", []):
            for leg in x.get("of", []):
                if leg not in defined:
                    structural.append(
                        f"{cg.get('name')}.{x.get('name')}: cross references "
                        f"undefined coverpoint {leg!r} "
                        f"(defined: {', '.join(sorted(n for n in defined if n))})")
    if structural:
        print(f"── {len(structural)} STRUCTURAL ERROR(S) ──")
        for e in structural:
            print(f"  {e}")
        print("\n  The generated SystemVerilog will not compile. Fix these first.\n")

    holes, covered, excluded = [], [], []
    claimed_items: set[str] = set()

    for cg, cp, bn, b in bins_of(cov):
        kind = b.get("kind", "explicit")
        refs = b.get("testplan", []) or []
        entry = {"cg": cg, "cp": cp, "bin": bn, "kind": kind,
                 "why": b.get("why", ""), "spec": b.get("spec", ""),
                 "refs": refs}

        # A bin declared unreachable on this DUT is an exclusion, not a hole --
        # provided it says why. It stays in the model so a DUT that can reach
        # it gets measured.
        if b.get("reachable") is False:
            if b.get("why"):
                entry["kind"] = "unreachable"
                excluded.append(entry)
            else:
                entry["problem"] = "reachable: false with no stated reason"
                holes.append(entry)
            continue

        if kind in ("ignore", "illegal"):
            # Exclusions are legitimate, but only with a stated reason. An
            # unexplained exclusion is indistinguishable from an oversight.
            if not (b.get("why") or b.get("reason")):
                entry["problem"] = f"{kind} bin with no stated reason"
                holes.append(entry)
            else:
                excluded.append(entry)
            continue

        # A bin may name its testplan items, or be matched by id appearing in
        # the plan text -- the model author should not have to know the plan's
        # internal structure.
        hit = [r for r in refs if r in items]
        if not hit and refs:
            entry["problem"] = ("names testplan items that do not exist: "
                                + ", ".join(r for r in refs if r not in items))
            holes.append(entry)
        elif not refs:
            entry["problem"] = "no testplan item claims this bin"
            holes.append(entry)
        else:
            claimed_items.update(hit)
            covered.append(entry)

    # Orphan reporting is only meaningful inside the scope the model covers.
    # A model for two features will "orphan" every item of the other thirteen,
    # which buries the real finding under noise. Infer scope from the id
    # prefixes the model actually claims, unless the user names it.
    def prefix(i: str) -> str:
        core = i[3:] if i.startswith("TC-") else i
        return core.split("-")[0]

    if a.scope:
        scope = set(a.scope.split(","))
    else:
        scope = {prefix(i) for i in claimed_items}

    orphan_items = sorted(i for i in set(items) - claimed_items
                          if prefix(i) in scope)
    out_of_scope = len(items) - len(claimed_items) - len(orphan_items)

    # ── Report ─────────────────────────────────────────────────────────────
    total = len(holes) + len(covered) + len(excluded)
    print(f"coverage model : {a.coverage}")
    print(f"testplan       : {a.testplan}  ({len(items)} items)")
    print(f"bins           : {total}  "
          f"({len(covered)} claimed, {len(excluded)} excluded, {len(holes)} holes)")

    if holes:
        print(f"\n── {len(holes)} HOLE(S): a bin nothing plans to exercise ──")
        for h in holes:
            print(f"  {h['cg']}.{h['cp']}.{h['bin']}  [{h['kind']}]")
            print(f"    {h['problem']}")
            if h["spec"]:
                print(f"    spec: {h['spec']}")
            if h["why"]:
                print(f"    why:  {h['why'][:100]}")
        print("\n  Each of these is a proposed new testplan item.")

    if out_of_scope:
        print(f"  scope          : {', '.join(sorted(scope)) or '(none)'}  "
              f"({out_of_scope} item(s) outside it, not checked)")

    if orphan_items:
        print(f"\n── {len(orphan_items)} TESTPLAN ITEM(S) in scope contributing to no bin ──")
        for i in orphan_items[:30]:
            print(f"  {i}  {items[i][:82]}")
        if len(orphan_items) > 30:
            print(f"  ... and {len(orphan_items) - 30} more")
        print("\n  Either the coverage model is blind to these, or they have no")
        print("  verification objective. One of the two is wrong -- decide which.")

    if not holes and not orphan_items:
        print("\nNo disagreement. Both artifacts claim the same behaviours.")
        if not a.quiet:
            print("Worth a sceptical look: perfect agreement between two")
            print("supposedly independent passes can mean one was derived")
            print("from the other.")

    if a.emit_holes and holes:
        out = ["# Coverage holes — proposed testplan items", "",
               f"Generated from `{a.coverage}` against `{a.testplan}`.", "",
               "Each row is a bin the coverage model says matters and no testplan",
               "item claims. Each needs a testplan item and a test, or a",
               "documented exclusion.", "",
               "| Covergroup | Coverpoint | Bin | Spec | Why it matters |",
               "|---|---|---|---|---|"]
        for h in holes:
            why = (h["why"] or h["problem"]).replace("|", "\\|")[:120]
            out.append(f"| `{h['cg']}` | `{h['cp']}` | `{h['bin']}` | "
                       f"{h['spec'] or '—'} | {why} |")
        Path(a.emit_holes).write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\nwrote {a.emit_holes}")

    return 1 if (holes or structural) else 0


if __name__ == "__main__":
    sys.exit(main())
