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

COV_DIR=$(readlink -f "${1:?usage: xcelium_cov_report.sh <cov_dir> <report_txt>}")
REPORT=${2:?usage: xcelium_cov_report.sh <cov_dir> <report_txt>}

# Default to the 21.09 vManager install, NOT 23.03. Both are installed here and
# only this one authenticates: 23.03's imc dies in its Java licence layer
# (LMF-01513 / FLEXnet -8 "Authentication Failed") before opening anything,
# while xrun authenticates against the same licence file. Per-product gap, not a
# broken licence. 21.09 warns it is older than the 23.03 data and reads it
# correctly -- UCIS is versioned for exactly that.
IMC_ROOT=${IMC_ROOT:-/home/icdesign/cadence/installs/VMANAGER2109}
IMC=${IMC:-$IMC_ROOT/bin/imc}
# The imc wrapper resolves its own installation from PATH and exits with
# "Unable to find the Cadence installation in your path" without this, even when
# invoked by absolute path.
export PATH="$IMC_ROOT/tools.lnx86/bin:$IMC_ROOT/bin:$PATH"

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

imc is part of vManager, not Xcelium. Point IMC_ROOT at a vManager install
and re-run, e.g.
    make coverage_merge IMC_ROOT=/path/to/VMANAGER2109
Use the 21.09 install where both are present -- 23.03's imc fails licence
authentication here even though xrun succeeds against the same file.
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
