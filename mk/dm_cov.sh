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
# Every instance that IS the Debug Module. `report -inst X` covers ONLY X --
# it does not recurse, and the legacy `report` command has no -recursive option
# at all. Naming just i_dm_top therefore measured the wrapper's port toggles and
# none of the logic: 816 signal bits and not one line of dm_csrs, dm_mem or
# dm_sba. Every instance has to be named.
DM_INSTS=(
    tb_top_soc.dut.i_dm_top
    tb_top_soc.dut.i_dm_top.i_dm_csrs
    tb_top_soc.dut.i_dm_top.i_dm_sba
    tb_top_soc.dut.i_dm_top.i_dm_mem
    tb_top_soc.dut.i_dmi_jtag      # sibling of dm_top in ariane_testharness
)
DM_INST=${DM_INSTS[0]}

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
    # (a) DM-only code coverage. One report per instance, appended into one
    # file -- see DM_INSTS above for why each must be named.
    # One file per instance, concatenated afterwards. `-append` was tried first
    # and silently produced a report containing only the first instance -- no
    # error, just missing data, which is the worst possible failure for a
    # coverage number someone is going to quote.
    for inst in "${DM_INSTS[@]}"; do
        printf 'report -detail -all -inst %s -metrics code -out %s/.part.%s.rpt\n' \
               "$inst" "$OUT" "$inst"
    done
    # (b) functional coverage across the whole testbench. -all matters: without
    # it this is the *Uncovered* report, where a covergroup at 100% is absent
    # rather than listed, and the reader cannot tell the two apart.
    printf 'report -detail -all -metrics covergroup -out %s/functional.rpt\n' "$OUT"
    # (c) Browsable HTML, which needs no GUI or X11. report_metrics DOES accept
    # -recursive, unlike the legacy report command. (There is no report_summary
    # command in imc 21.09 -- an earlier version of this script called one and
    # it failed silently, producing no summary at all.)
    printf 'report_metrics -detail -metrics code -inst %s -recursive -out %s/dm_code_html\n' \
           "$DM_INST" "$OUT"
    printf 'report_metrics -detail -metrics covergroup -out %s/functional_html\n' "$OUT"
    printf 'exit\n'
} > "$tcl"

"$IMC" -exec "$tcl" -nostdout -logfile "$OUT/imc.log" > "$OUT/imc.stdout" 2>&1
rc=$?
echo "imc exit=$rc  (see $OUT/imc.log)"

# Stitch the per-instance reports into one, and fail loudly if an instance
# produced nothing -- a renamed or moved instance would otherwise just vanish
# from the report and quietly inflate the DM's coverage.
: > "$OUT/dm_code.rpt"
missing=()
for inst in "${DM_INSTS[@]}"; do
    part="$OUT/.part.$inst.rpt"
    if [ -s "$part" ] && grep -q '^Instance name:' "$part"; then
        {
            printf '\n%s\n== %s\n%s\n' "$(printf '=%.0s' {1..78})" "$inst" \
                   "$(printf '=%.0s' {1..78})"
            cat "$part"
        } >> "$OUT/dm_code.rpt"
    else
        missing+=("$inst")
    fi
    rm -f "$part"
done
if [ ${#missing[@]} -gt 0 ]; then
    printf 'WARNING: no coverage reported for %s\n' "${missing[@]}" >&2
    echo "  Check the instance path in DM_INSTS -- imc reports an unknown" >&2
    echo "  instance as an empty section rather than as an error." >&2
fi
echo "DM instances reported: $(( ${#DM_INSTS[@]} - ${#missing[@]} ))/${#DM_INSTS[@]}"

# imc states counts, never percentages, and has no notion of "the Debug Module"
# as a unit -- so sum across the instances that make it up.
python3 "$(dirname "${BASH_SOURCE[0]}")/dm_cov_summary.py" "$OUT/dm_code.rpt" || true
ls -la "$OUT"
