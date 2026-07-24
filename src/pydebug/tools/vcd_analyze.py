"""
pydebug.tools.vcd_analyze — minimal VCD value-change-timeline extractor.

Built for root-causing DV/RTL issues from a waveform *programmatically*
instead of opening a GUI: point it at a `+dump_waves`-produced VCD (see
cva6_sim/tb_top_cva6.sv and ibex_sim/tb_top_ibex.sv's scoped `$dumpvars`
blocks) and a set of signal-name substrings, and get a plain time-ordered
list of every value change for the matching signals — greppable, diffable,
and pasteable into an issue.

Usage:
    python3 -m pydebug.tools.vcd_analyze <file.vcd> --list
    python3 -m pydebug.tools.vcd_analyze <file.vcd> --match state_q --match cmdbusy
    python3 -m pydebug.tools.vcd_analyze <file.vcd> --match going --after 10000000 --before 20000000
"""
import argparse


def parse_vcd(path):
    """Returns (id_to_name: {id: full_hier_name}, changes: [(time, id, value)])."""
    id_to_name = {}
    scope_stack = []
    changes = []
    time = 0

    with open(path, "r", errors="ignore") as f:
        in_header = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            if in_header:
                if line.startswith("$scope"):
                    parts = line.split()
                    scope_stack.append(parts[2])
                elif line.startswith("$upscope"):
                    scope_stack.pop()
                elif line.startswith("$var"):
                    # $var <type> <width> <id> <name> [range] $end
                    parts = line.split()
                    vid = parts[3]
                    name = parts[4]
                    full = ".".join(scope_stack + [name])
                    id_to_name.setdefault(vid, full)
                elif line.startswith("$enddefinitions"):
                    in_header = False
                continue

            if line.startswith("#"):
                time = int(line[1:])
                continue
            if line[0] in "01xXzZ":
                changes.append((time, line[1:], line[0]))
            elif line[0] in "br":
                sp = line.index(" ")
                changes.append((time, line[sp + 1:], line[1:sp]))
    return id_to_name, changes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("vcd")
    ap.add_argument("--match", action="append", default=[],
                     help="substring (case-insensitive) to match against full hierarchical signal names; repeatable")
    ap.add_argument("--after", type=int, default=None, help="only show changes at or after this $time")
    ap.add_argument("--before", type=int, default=None, help="only show changes at or before this $time")
    ap.add_argument("--list", action="store_true", help="list matching signal names and exit (no timeline)")
    args = ap.parse_args()

    id_to_name, changes = parse_vcd(args.vcd)

    if args.match:
        wanted_ids = {
            vid for vid, name in id_to_name.items()
            if any(m.lower() in name.lower() for m in args.match)
        }
    else:
        wanted_ids = set(id_to_name.keys())

    if args.list:
        for vid in sorted(wanted_ids, key=lambda i: id_to_name[i]):
            print(id_to_name[vid])
        return

    for t, vid, val in changes:
        if vid not in wanted_ids:
            continue
        if args.after is not None and t < args.after:
            continue
        if args.before is not None and t > args.before:
            continue
        print(f"t={t:>10} {id_to_name[vid]:<60} = {val}")


if __name__ == "__main__":
    main()
