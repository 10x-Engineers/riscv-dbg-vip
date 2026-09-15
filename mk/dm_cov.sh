#!/usr/bin/env bash
# Report (a) code coverage for the Debug Module instance only and
# (b) overall functional (covergroup) coverage, from the merged sweep data.
set -o pipefail
COV_DIR=$(readlink -f "${1:?usage: dm_cov.sh <cov_dir> <out_dir>}")
OUT=$(mkdir -p "${2:?usage: dm_cov.sh <cov_dir> <out_dir>}" && readlink -f "$2")
# Use the 21.09 vManager install, NOT 23.03. Both are installed; only this one
# authenticates against this site's licence file. The 23.03 imc dies in its Java
# licence layer (LMF-01513 / FLEXnet -8 "Authentication Failed") before it opens
# anything, while xrun authenticates against the very same file -- so this is a
# per-product licence gap, not a broken licence. 21.09 warns that it is older
# than the 23.03 coverage data and then reads it correctly; UCIS is versioned for
# exactly this.
IMC_ROOT=${IMC_ROOT:-/home/icdesign/cadence/installs/VMANAGER2109}
IMC=${IMC:-$IMC_ROOT/bin/imc}
# The imc wrapper resolves its own installation from PATH and exits with
# "Unable to find the Cadence installation in your path" without this.
export PATH="$IMC_ROOT/tools.lnx86/bin:$IMC_ROOT/bin:$PATH"
DM_INST=tb_top_soc.dut.i_dm_top

mkdir -p "$OUT"
runs=("$COV_DIR"/scope/*/)
[ -e "${runs[0]}" ] || { echo "no runs under $COV_DIR/scope/" >&2; exit 1; }
echo "merging ${#runs[@]} run(s)"

tcl=$(mktemp -t dmcov_XXXXXX.tcl)
trap 'rm -f "$tcl"' EXIT
{
    printf 'merge'; printf ' %s' "${runs[@]}"
    printf ' -out %s/merged -overwrite\n' "$COV_DIR"
    printf 'load -run %s/merged\n' "$COV_DIR"
    # (a) DM-only code coverage, recursing into dm_csrs/dm_mem/dm_sba/...
    printf 'report -detail -inst %s -metrics code -out %s/dm_code.rpt\n' "$DM_INST" "$OUT"
    # (b) functional coverage across the whole testbench
    printf 'report -detail -metrics covergroup -out %s/functional.rpt\n' "$OUT"
    # (c) DM instance summary, for the single headline number
    printf 'report_summary -inst %s -metrics code -out %s/dm_summary.rpt\n' "$DM_INST" "$OUT"
    printf 'report_summary -metrics covergroup -out %s/func_summary.rpt\n' "$OUT"
    printf 'exit\n'
} > "$tcl"

"$IMC" -exec "$tcl" -nostdout -logfile "$OUT/imc.log" > "$OUT/imc.stdout" 2>&1
echo "imc exit=$?  (see $OUT/imc.log)"
ls -la "$OUT"
