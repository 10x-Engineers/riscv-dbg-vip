#!/usr/bin/env bash
# Merge every scenario's Xcelium coverage database and report the combined
# functional coverage — the Xcelium equivalent of Questa's
# `vcover merge` + `vcover report -cvg -details`.
#
#   xcelium_cov_report.sh <cov_dir> <report_txt>
#
# <cov_dir> is the -covworkdir the runs wrote into: xrun lays it out as
# <cov_dir>/scope/<testname>/*.ucd, with the design model in
# <cov_dir>/scope/*.ucm. Merging is what makes a bin hit in ANY run count as
# covered, which is the number no single scenario log can show on its own.
#
# imc ships with vManager rather than Xcelium, so it is routinely absent or
# unlicensed on a machine where xrun itself works fine. That is a reporting
# gap, not a coverage-collection gap: the .ucd data is already on disk and can
# be merged later, or elsewhere. Say so plainly instead of failing blank.
set -o pipefail

COV_DIR=${1:?usage: xcelium_cov_report.sh <cov_dir> <report_txt>}
REPORT=${2:?usage: xcelium_cov_report.sh <cov_dir> <report_txt>}
IMC=${IMC:-imc}

runs=("$COV_DIR"/scope/*/)
if [ ! -e "${runs[0]}" ]; then
    echo "no coverage runs under $COV_DIR/scope/ -- run 'make coverage_regress' first" >&2
    exit 1
fi
echo "merging ${#runs[@]} coverage run(s) from $COV_DIR"

if ! command -v "$IMC" >/dev/null 2>&1; then
    cat >&2 <<EOF
imc not found (looked for: $IMC).

The coverage databases are collected and intact:
$(printf '  %s\n' "${runs[@]}")

imc is part of vManager, not Xcelium. Point IMC at it and re-run, e.g.
    make coverage_merge IMC=/path/to/VMANAGER/bin/imc
or merge these .ucd files on a machine that has a licensed imc.
EOF
    exit 1
fi

tcl=$(mktemp -t xcelium_cov_XXXXXX.tcl)
trap 'rm -f "$tcl"' EXIT
{
    printf 'merge'
    printf ' %s' "${runs[@]}"
    printf ' -out %s/merged -overwrite\n' "$COV_DIR"
    printf 'load -run %s/merged\n' "$COV_DIR"
    printf 'report -detail -metrics covergroup -out %s\n' "$REPORT"
    printf 'exit\n'
} > "$tcl"

# imc reports a licence failure as a Java stack trace on its own stdout, not in
# -logfile, so capture both: otherwise the trace buries the diagnosis below and
# the grep for it finds an empty log.
if ! "$IMC" -exec "$tcl" -nostdout -logfile "$COV_DIR/imc.log" \
        > "$COV_DIR/imc.stdout" 2>&1; then
    echo "imc failed -- see $COV_DIR/imc.log and $COV_DIR/imc.stdout" >&2
    # A licence failure is the common case and worth naming, because the
    # coverage data itself is fine and can be reported on another machine.
    if grep -qiE 'lic_error|LMF-[0-9]+|licen[sc]e' \
            "$COV_DIR/imc.log" "$COV_DIR/imc.stdout" 2>/dev/null; then
        cat >&2 <<EOF
imc could not check out a licence (vManager is licensed separately from
Xcelium). The merged coverage data is still valid and complete:
$(printf '  %s\n' "${runs[@]}")
Report it on a machine with a licensed imc, or set IMC= to one.
EOF
    fi
    exit 1
fi

echo "wrote $REPORT"
