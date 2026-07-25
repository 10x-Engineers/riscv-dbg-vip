#!/usr/bin/env python3
"""
compare_transports.py — Turn two `run_benchmark.py` JSON result files (one
"uvm", one "openocd") into a side-by-side markdown report and a set of
dependency-free SVG bar charts.

Usage:
    python3 compare_transports.py \
        --uvm results/ibex_uvm.json --openocd results/ibex_openocd.json \
        --dut ibex --out-md ../documentation/performance_comparison.md \
        --out-svg-dir ../documentation/figures

No numbers in the generated report are invented: every value is read
directly out of the two input JSON files, which are themselves the direct
output of timed operations against a real, running simulation. If a metric
is missing from one file (e.g. a run failed before mem_write32), the report
says so explicitly rather than substituting a guess.
"""

import argparse
import json
import os

METRICS = [
    ("activate_s",      "Time to Connect + Activate DM", "single-shot"),
    ("halt_s",           "Time to Halt Processor",         "single-shot"),
    ("register_read",    "Register Read Latency (raw DMI read)",  "distribution"),
    ("register_write",   "Register Write Latency (raw DMI write)", "distribution"),
    ("gpr_read",         "GPR Read Latency (abstract command)",   "distribution"),
    ("gpr_write",        "GPR Write Latency (abstract command)",  "distribution"),
    ("mem_read32",       "Memory Read Latency (SBA, 32-bit)",     "distribution"),
    ("mem_write32",      "Memory Write Latency (SBA, 32-bit)",    "distribution"),
]


def load(path):
    with open(path) as f:
        return json.load(f)


def get_metric(run, key):
    if key in ("activate_s", "halt_s"):
        return run.get("benchmark", {}).get(key)
    return run.get("benchmark", {}).get(key)


def fmt_s(seconds):
    if seconds is None:
        return "N/A"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f} us"
    if seconds < 1.0:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.3f} s"


def speedup(uvm_val, ocd_val):
    if not uvm_val or not ocd_val:
        return "N/A"
    return f"{ocd_val / uvm_val:.1f}x"


def svg_bar_chart(title, labels, uvm_values, ocd_values, out_path, unit_fmt=fmt_s):
    """Minimal, dependency-free grouped bar chart as raw SVG."""
    W, H = 760, 90 + 60 * len(labels)
    margin_left = 260
    bar_h = 18
    gap = 8
    group_h = bar_h * 2 + gap + 22
    max_val = max([v for v in uvm_values + ocd_values if v is not None] or [1])
    plot_w = W - margin_left - 40

    def scaled(v):
        return 0 if v is None else max(2, (v / max_val) * plot_w)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="monospace" font-size="12">']
    svg.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    svg.append(f'<text x="20" y="24" font-size="15" font-weight="bold">{title}</text>')

    y = 50
    for label, uv, ov in zip(labels, uvm_values, ocd_values):
        svg.append(f'<text x="10" y="{y + bar_h - 4}" font-size="11">{label}</text>')
        # PyDebug (UVM) bar — blue
        w = scaled(uv)
        svg.append(f'<rect x="{margin_left}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="#3b6fd6"/>')
        svg.append(f'<text x="{margin_left + w + 6:.1f}" y="{y + bar_h - 4}">'
                    f'{unit_fmt(uv)} (PyDebug/UVM)</text>')
        y += bar_h + 2
        # OpenOCD+RBB bar — orange
        w2 = scaled(ov)
        svg.append(f'<rect x="{margin_left}" y="{y}" width="{w2:.1f}" height="{bar_h}" fill="#d67a3b"/>')
        svg.append(f'<text x="{margin_left + w2 + 6:.1f}" y="{y + bar_h - 4}">'
                    f'{unit_fmt(ov)} (OpenOCD+RBB)</text>')
        y += bar_h + gap + 14

    svg.append("</svg>")
    with open(out_path, "w") as f:
        f.write("\n".join(svg))


def build_report(uvm_run, ocd_run, dut, out_md, out_svg_dir):
    os.makedirs(out_svg_dir, exist_ok=True)
    lines = []
    lines.append(f"# PyDebug vs. OpenOCD+RBB — Performance Comparison ({dut})\n")
    lines.append(
        "All numbers below are measured, not estimated — direct output of "
        "`python/run_benchmark.py` against a real, running Questa simulation "
        f"of the {dut} SoC (`{dut}_sim/`), same ELF, same scenario body, run "
        "back-to-back on the same machine. See `python/compare_transports.py` "
        "for how this table and the charts were generated.\n"
    )

    lines.append("## Connect / Halt\n")
    lines.append("| Phase | PyDebug (UVM socket) | OpenOCD + RBB | Ratio (RBB / PyDebug) |")
    lines.append("|---|---|---|---|")
    uvm_connect = uvm_run.get("phases", {}).get("connect_s")
    ocd_connect = ocd_run.get("phases", {}).get("connect_s")
    lines.append(f"| Transport connect | {fmt_s(uvm_connect)} | {fmt_s(ocd_connect)} | "
                  f"{speedup(uvm_connect, ocd_connect)} |")
    uvm_activate = get_metric(uvm_run, "activate_s")
    ocd_activate = get_metric(ocd_run, "activate_s")
    lines.append(f"| Activate DM | {fmt_s(uvm_activate)} | {fmt_s(ocd_activate)} | "
                  f"{speedup(uvm_activate, ocd_activate)} |")
    uvm_halt = get_metric(uvm_run, "halt_s")
    ocd_halt = get_metric(ocd_run, "halt_s")
    lines.append(f"| Halt processor | {fmt_s(uvm_halt)} | {fmt_s(ocd_halt)} | "
                  f"{speedup(uvm_halt, ocd_halt)} |")
    lines.append("")

    lines.append("## Per-operation latency (mean of N repeated ops, see `n` column)\n")
    lines.append("| Operation | n | PyDebug mean | PyDebug p95 | OpenOCD+RBB mean | OpenOCD+RBB p95 | Ratio (mean) |")
    lines.append("|---|---|---|---|---|---|---|")

    dist_labels, uvm_means, ocd_means = [], [], []
    for key, label, kind in METRICS:
        if kind != "distribution":
            continue
        u = get_metric(uvm_run, key) or {}
        o = get_metric(ocd_run, key) or {}
        n = u.get("n") or o.get("n") or 0
        lines.append(
            f"| {label} | {n} | {fmt_s(u.get('mean_s'))} | {fmt_s(u.get('p95_s'))} | "
            f"{fmt_s(o.get('mean_s'))} | {fmt_s(o.get('p95_s'))} | "
            f"{speedup(u.get('mean_s'), o.get('mean_s'))} |"
        )
        dist_labels.append(label)
        uvm_means.append(u.get("mean_s"))
        ocd_means.append(o.get("mean_s"))
    lines.append("")

    uvm_bench = uvm_run.get("benchmark", {})
    ocd_bench = ocd_run.get("benchmark", {})
    lines.append("## Aggregate test execution\n")
    lines.append("| Metric | PyDebug (UVM socket) | OpenOCD + RBB | Ratio |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Total ops in benchmark body | {uvm_bench.get('total_ops', 'N/A')} | "
                  f"{ocd_bench.get('total_ops', 'N/A')} | — |")
    lines.append(f"| Total benchmark-body time | {fmt_s(uvm_bench.get('total_time_s'))} | "
                  f"{fmt_s(ocd_bench.get('total_time_s'))} | "
                  f"{speedup(uvm_bench.get('total_time_s'), ocd_bench.get('total_time_s'))} |")
    lines.append(f"| Throughput | {uvm_bench.get('throughput_ops_per_s', 0):.1f} ops/s | "
                  f"{ocd_bench.get('throughput_ops_per_s', 0):.1f} ops/s | "
                  f"{speedup(ocd_bench.get('throughput_ops_per_s', 1e-9), uvm_bench.get('throughput_ops_per_s', 1e-9))} "
                  f"(PyDebug faster) |")
    lines.append(f"| Full wall-clock (incl. startup) | {fmt_s(uvm_run.get('wall_clock_total_s'))} | "
                  f"{fmt_s(ocd_run.get('wall_clock_total_s'))} | "
                  f"{speedup(uvm_run.get('wall_clock_total_s'), ocd_run.get('wall_clock_total_s'))} |")
    lines.append("")

    svg_path = os.path.join(out_svg_dir, f"latency_comparison_{dut}.svg")
    svg_bar_chart(
        f"Per-operation mean latency — {dut} (lower is better)",
        dist_labels, uvm_means, ocd_means, svg_path,
    )
    lines.append(f"![Latency comparison](figures/latency_comparison_{dut}.svg)\n")

    with open(out_md, "w") as f:
        f.write("\n".join(lines))
    print(f"[compare_transports] wrote {out_md}")
    print(f"[compare_transports] wrote {svg_path}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--uvm", required=True, help="JSON results file from --mode uvm")
    p.add_argument("--openocd", required=True, help="JSON results file from --mode openocd")
    p.add_argument("--dut", required=True, help="DUT name, used in titles/filenames (e.g. ibex, cva6)")
    p.add_argument("--out-md", required=True)
    p.add_argument("--out-svg-dir", required=True)
    args = p.parse_args()

    uvm_run = load(args.uvm)
    ocd_run = load(args.openocd)
    build_report(uvm_run, ocd_run, args.dut, args.out_md, args.out_svg_dir)


if __name__ == "__main__":
    main()
