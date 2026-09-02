#!/usr/bin/env bash
# Reproduces the debug-subsystem divergence figure quoted in Section IV-A of
# camera_ready.md: "across the eleven source files present in both trees --
# five in the Debug Module register file, six in the JTAG DTM -- 1102 of
# 3333 lines differ (33%)".
#
# Method: for every file present in BOTH debug-subsystem source trees (the
# vendored riscv-dbg package: Debug Module + JTAG DTM), count changed lines
# as `diff` add/delete lines, against the v0.13 (Ibex) tree taken as the
# baseline line count.
#
# Pinned at:
#   CVA6-fork/corev_apu/riscv-dbg          58f8c84   (spec v1.0 fork)
#   ibex-demo-system                       0a8ce38   (vendors pulp_riscv_dbg
#                                                     unmodified at v0.13)
#
# Run from the pydebug repository root.
set -euo pipefail

V10=CVA6-fork/corev_apu/riscv-dbg/src              # v1.0 fork
V013=ibex-demo-system/vendor/pulp_riscv_dbg/src    # v0.13 baseline

for d in "$V10" "$V013"; do
    [ -d "$d" ] || { echo "missing: $d (submodules not checked out?)" >&2; exit 1; }
done

total=0; changed=0; files=0
printf '%-22s %8s %8s\n' FILE BASELINE CHANGED
while read -r f; do
    n=$(wc -l < "$V013/$f")
    d=$(diff "$V013/$f" "$V10/$f" | grep -c '^[<>]' || true)
    total=$((total + n)); changed=$((changed + d)); files=$((files + 1))
    printf '%-22s %8d %8d\n' "$f" "$n" "$d"
done < <(comm -12 <(ls "$V10" | sort) <(ls "$V013" | sort))

printf '\n%d shared files: %d of %d baseline lines differ (%d%%)\n' \
    "$files" "$changed" "$total" $((100 * changed / total))
