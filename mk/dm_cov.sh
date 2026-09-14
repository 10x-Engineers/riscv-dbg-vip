#!/usr/bin/env bash
# Report (a) code coverage for the Debug Module instance only and
# (b) overall functional (covergroup) coverage, from the merged sweep data.
set -o pipefail
COV_DIR=${1:?usage: dm_cov.sh <cov_dir> <out_dir>}
OUT=${2:?usage: dm_cov.sh <cov_dir> <out_dir>}
IMC=${IMC:-/home/icdesign/cadence/installs/VMANAGER2303/bin/imc}
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
