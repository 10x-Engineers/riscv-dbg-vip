#!/usr/bin/env python3
"""
run_regression.py — run the CVA6 Debug VIP regression and report it.

Reads cva6_sim/regress/regression.yaml, runs each test, collects its output
under sim_outputs/<name>/, and prints a verdict table plus merged functional
coverage.

    python3 mk/run_regression.py                      # everything
    python3 mk/run_regression.py --only step_classes,cmderr
    python3 mk/run_regression.py --coverage           # build with -coverage all
    python3 mk/run_regression.py --list

Exit status is non-zero when a test's result differs from its declared
`expect`. A test that is expected to fail and fails is not a regression -- the
point is to notice when a result CHANGES, which is why the yaml records the
known state rather than an aspiration.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: python3 -m pip install --user pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "cva6_sim"
SUITE = SIM / "regress" / "regression.yaml"

# Session verdict, e.g. "Session complete - 9/9 passed" or "... (1 failed)".
RE_VERDICT = re.compile(r"Session complete\s*-\s*(\d+)/(\d+)\s*passed")
RE_UVM_ERR = re.compile(r"UVM_ERROR\s*:\s*(\d+)")
# Per-coverpoint lines emitted by dm_spec_coverage. Tagged so this does not
# have to parse prose that will be reworded.
RE_COV = re.compile(r"(CG|CP)\s+(\S+)\s+([\d.]+)%")
RE_TOTAL = re.compile(r"SPEC_TOTAL\s+([\d.]+)%")


def load_suite() -> dict:
    return yaml.safe_load(SUITE.read_text(encoding="utf-8"))


def run_one(test: dict, defaults: dict, coverage: bool) -> dict:
    name = test["name"]
    cfg = test["config"]
    elf = test.get("elf", defaults.get("elf"))
    timeout = test.get("timeout_s", defaults.get("timeout_s", 900))
    target = "soc_test_cov" if coverage else "soc_test"

    # Check inputs before launching. A missing config kills the Python client
    # instantly while the simulator keeps running with nothing driving it, so
    # the test burns its whole timeout and reports `timeout` -- indistinguishable
    # from a hung DUT. Better to say which file is missing.
    for path, what in ((SIM / cfg, "config"), (SIM / elf, "ELF") if elf else (None, None)):
        if path is not None and not path.exists():
            return {"name": name, "result": "error", "elapsed": 0.0, "steps": "-",
                    "uvm_errors": 0, "coverage": {}, "spec_total": None,
                    "expect": test.get("expect", defaults.get("expect", "pass")),
                    "covers": test.get("covers", []),
                    "note": f"missing {what}: {path}"}

    cmd = ["make", target, f"CFG_FILE={cfg}"]
    if elf:
        cmd.append(f"ELF={elf}")

    started = time.time()
    # Own process group, so a timeout can kill the whole tree. `make` spawns
    # xrun which spawns xmsim; killing only `make` leaves xmsim running with
    # the pipe open, so the read blocks forever and the timeout never actually
    # takes effect -- one hung test stalls the entire regression.
    proc = subprocess.Popen(cmd, cwd=SIM, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(5)
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out = ""
    out = out or ""
    elapsed = time.time() - started

    log_dir = SIM / "sim_outputs" / name
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "regress.log").write_text(out, encoding="utf-8")

    m = RE_VERDICT.search(out)
    errs = RE_UVM_ERR.findall(out)
    uvm_errors = int(errs[-1]) if errs else 0

    # A dead Python client leaves the simulator running with nothing driving
    # it, so the test reaches its timeout looking exactly like a hung DUT. The
    # traceback is in the output either way -- say so rather than making
    # someone read a 900-second log to find a TypeError on line one.
    client_died = ("Traceback (most recent call last)" in out and
                   "Session complete" not in out)

    if client_died:
        last = [ln for ln in out.splitlines()
                if ln.strip() and not ln.startswith((" ", "\t"))]
        result = "error"
    elif timed_out:
        result = "timeout"
    elif m:
        passed, total = int(m.group(1)), int(m.group(2))
        result = "pass" if passed == total and uvm_errors == 0 else "fail"
    else:
        # No verdict line: the session died before reporting. That is distinct
        # from failing its checks, and worth its own state -- most often it
        # means fail-fast aborted on a known defect.
        result = "partial"

    cov = {k: float(v) for _, k, v in RE_COV.findall(out)}
    tot = RE_TOTAL.search(out)

    return {
        "name": name, "result": result, "elapsed": elapsed,
        "steps": (f"{m.group(1)}/{m.group(2)}" if m else "-"),
        "uvm_errors": uvm_errors,
        "coverage": cov,
        "spec_total": float(tot.group(1)) if tot else None,
        "expect": test.get("expect", defaults.get("expect", "pass")),
        "covers": test.get("covers", []),
        "note": ("python client died: " + last[-1][:90]) if client_died and last else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated test names")
    ap.add_argument("--coverage", action="store_true",
                    help="build with -coverage all and collect functional coverage")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", default=None,
                    help="write a markdown report here")
    a = ap.parse_args()

    suite = load_suite()
    defaults = suite.get("defaults", {})
    tests = suite["tests"]

    if a.only:
        want = set(a.only.split(","))
        tests = [t for t in tests if t["name"] in want]
        missing = want - {t["name"] for t in tests}
        if missing:
            return int(bool(sys.stderr.write(
                f"unknown test(s): {', '.join(sorted(missing))}\n")))

    if a.list:
        print(f"{suite['suite']}: {len(tests)} test(s)")
        for t in tests:
            print(f"  {t['name']:<24} {t.get('expect', 'pass'):<8} {t['config']}")
        return 0

    print(f"=== {suite['suite']} -- {len(tests)} test(s), "
          f"{'with' if a.coverage else 'without'} coverage ===\n")

    results = []
    for i, t in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {t['name']} ... ", end="", flush=True)
        r = run_one(t, defaults, a.coverage)
        results.append(r)
        flag = "" if r["result"] == r["expect"] else "  <-- CHANGED"
        note = f"  {r['note']}" if r.get("note") else ""
        print(f"{r['result']:<8} {r['steps']:>7}  {r['elapsed']:6.1f}s{flag}{note}",
              flush=True)

    # ── Verdict table ────────────────────────────────────────────────────
    changed = [r for r in results if r["result"] != r["expect"]]
    print(f"\n{'test':<24} {'result':<9} {'expected':<9} {'steps':>7} {'errors':>7}")
    print("-" * 62)
    for r in results:
        print(f"{r['name']:<24} {r['result']:<9} {r['expect']:<9} "
              f"{r['steps']:>7} {r['uvm_errors']:>7}")

    by = {}
    for r in results:
        by[r["result"]] = by.get(r["result"], 0) + 1
    print("\n" + ", ".join(f"{k}={v}" for k, v in sorted(by.items())))

    # ── Merged functional coverage ───────────────────────────────────────
    # Per-run values merged by taking the max: a bin hit in any run is covered.
    # This is a lower bound on true merged coverage, because two runs can hit
    # different bins of the same coverpoint and the max only credits one of
    # them. Stated rather than presented as the merged number.
    if a.coverage:
        merged: dict[str, float] = {}
        for r in results:
            for k, v in r["coverage"].items():
                merged[k] = max(merged.get(k, 0.0), v)
        if merged:
            print("\n=== functional coverage, best across the suite ===")
            print("(per-run maxima -- a LOWER BOUND on merged coverage; two runs")
            print(" hitting different bins of one coverpoint credit only the higher)")
            for k in sorted(merged):
                bar = "#" * int(merged[k] / 5)
                print(f"  {k:<26} {merged[k]:6.2f}%  {bar}")
            cps = [v for k, v in merged.items() if k.startswith("cp_")]
            if cps:
                print(f"\n  mean over {len(cps)} coverpoints: "
                      f"{sum(cps) / len(cps):6.2f}%")

    if changed:
        print(f"\n{len(changed)} test(s) differ from expected:")
        for r in changed:
            print(f"  {r['name']}: expected {r['expect']}, got {r['result']}")
        print("\nThat is what this regression is for. Either the RTL changed, or")
        print("regression.yaml's `expect` is stale -- update it deliberately, not")
        print("to make the run green.")

    if a.report:
        write_report(Path(a.report), suite, results, a.coverage)
        print(f"\nwrote {a.report}")

    return 1 if changed else 0


def write_report(path: Path, suite: dict, results: list, coverage: bool) -> None:
    from datetime import date
    out = [f"# {suite['suite']} — regression report", "",
           f"Generated {date.today().isoformat()}.", "",
           "| Test | Result | Expected | Steps | UVM errors | Covers |",
           "|---|---|---|---:|---:|---|"]
    for r in results:
        mark = "" if r["result"] == r["expect"] else " ⚠"
        covers = ", ".join(f"`{c}`" for c in r["covers"][:4])
        out.append(f"| {r['name']} | {r['result']}{mark} | {r['expect']} | "
                   f"{r['steps']} | {r['uvm_errors']} | {covers} |")
    if coverage:
        merged: dict[str, float] = {}
        for r in results:
            for k, v in r["coverage"].items():
                merged[k] = max(merged.get(k, 0.0), v)
        out += ["", "## Functional coverage", "",
                "Per-run maxima across the suite — a **lower bound** on merged",
                "coverage, because two runs hitting different bins of one",
                "coverpoint credit only the higher. A true merge needs `imc`.", "",
                "| Coverpoint | Best |", "|---|---:|"]
        for k in sorted(merged):
            out.append(f"| `{k}` | {merged[k]:.2f}% |")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
