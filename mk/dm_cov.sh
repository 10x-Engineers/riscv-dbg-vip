#!/usr/bin/env bash
# Report (a) code coverage for the Debug Module instances only, (b) overall
# functional (covergroup) coverage, (c) both as HTML, (d) the code-coverage
# text and HTML reports again with the unreachable-code exclusions applied, and
# (e) the functional reports again with mk/fcov_exclusions.tcl applied.
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
#
# That includes everything below them. An earlier list stopped at these five
# and quoted 100% while the DTM's TAP sat at 68/78 blocks, uncounted.
DM=tb_top_soc.dut.i_dm_top
DTM=tb_top_soc.dut.i_dmi_jtag      # sibling of dm_top in ariane_testharness
TB=tb_top_soc.dut                   # ariane_testharness
DM_INSTS=(
    $DM
    $DM.i_dm_csrs
    $DM.i_dm_csrs.gen_haltsum0_single
    $DM.i_dm_sba
    $DM.i_dm_mem
    $DM.i_dm_mem.gen_rom_snd_scratch.i_debug_rom
    $DTM
    $DTM.i_dmi_jtag_tap
    $DTM.i_dmi_jtag_tap.i_tck_inv
    $DTM.i_dmi_jtag_tap.i_tck_inv.i_tc_clk_inverter
    $DTM.i_dmi_jtag_tap.i_dft_tck_mux
    $DTM.i_dmi_jtag_tap.i_dft_tck_mux.i_tc_clk_mux2
    $DTM.i_dmi_cdc
    # cdc_2phase is type-parameterised: scored only because of
    # mk/xcelium_cov.ccf, and reported as missing here if that ever lapses.
    $DTM.i_dmi_cdc.i_cdc_req
    $DTM.i_dmi_cdc.i_cdc_req.i_src
    $DTM.i_dmi_cdc.i_cdc_req.i_dst
    $DTM.i_dmi_cdc.i_cdc_resp
    $DTM.i_dmi_cdc.i_cdc_resp.i_src
    $DTM.i_dmi_cdc.i_cdc_resp.i_dst
    # The DM's own connections to the rest of the SoC, which make up the debug
    # subsystem together with the DM and DTM:
    #   i_dm_axi2mem    AXI slave -> DM memory: how the hart fetches the debug
    #                   ROM, program buffer and abstract-command data
    #   i_dm_axi_master DM system-bus master -> AXI: System Bus Access
    #   i_rstgen_main   consumes ndmreset and resets the rest of the SoC
    $TB.i_dm_axi2mem
    $TB.i_dm_axi_master
    $TB.i_rstgen_main
    $TB.i_rstgen_main.i_rstgen_bypass
    # The boundary with the processor and the testbench: only the DM-facing
    # glue is measured. mk/dm_cov_exclude.py excludes everything else in these
    # two instances by name (BOUNDARY_KEEP), and says so in the report.
    #   TB              debug_req gating, ndmreset, the DMI/JTAG and DM bus glue
    #   TB.i_ariane     the hart's debug_req_i port
    $TB
    $TB.i_ariane
)
# `code` is block, expression and toggle only; FSM has to be asked for.
METRICS=code:fsm
# Roots of the HTML reports. report_metrics -recursive accepts exactly one
# -inst (*E,report.recursive.mult_entities otherwise), and i_dmi_jtag is not
# under i_dm_top, so each root gets its own report directory.
declare -A HTML_ROOTS=(
    [dm]=tb_top_soc.dut.i_dm_top
    [dmi_jtag]=tb_top_soc.dut.i_dmi_jtag
    [dm_axi2mem]=tb_top_soc.dut.i_dm_axi2mem
    [dm_axi_master]=tb_top_soc.dut.i_dm_axi_master
    [rstgen_main]=tb_top_soc.dut.i_rstgen_main
)

# report_metrics refuses to write into an existing directory
# (*E,report.dir_exist) and imc still exits 0, so a rerun would leave the
# previous run's HTML in place looking current.
emit_html() {   # emit_html <suffix>
    local key
    for key in "${!HTML_ROOTS[@]}"; do
        rm -rf "$OUT/${key}_code_html$1"
        printf 'report_metrics -detail -metrics %s -inst %s -recursive -out %s/%s_code_html%s\n' \
               "$METRICS" "${HTML_ROOTS[$key]}" "$OUT" "$key" "$1"
    done
}

emit_parts() {   # emit_parts <tag>: one legacy text report per DM instance
    local inst
    for inst in "${DM_INSTS[@]}"; do
        printf 'report -detail -all -inst %s -metrics %s -out %s/.part%s.%s.rpt\n' \
               "$inst" "$METRICS" "$OUT" "$1" "$inst"
    done
}

mkdir -p "$OUT"
# Step (d) is conditional; do not let a previous run's output stand in for it.
rm -rf "$OUT"/*_code_html_excl "$OUT"/imc_excl.* "$OUT/dm_exclusions.tcl" \
       "$OUT/dm_code_excl.rpt" "$OUT"/imc_fexcl.* "$OUT/functional_excl.rpt" \
       "$OUT/functional_html_excl"
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
    emit_parts ""
    # (b) functional coverage across the whole testbench. -all matters: without
    # it this is the *Uncovered* report, where a covergroup at 100% is absent
    # rather than listed, and the reader cannot tell the two apart.
    printf 'report -detail -all -metrics covergroup -out %s/functional.rpt\n' "$OUT"
    # (c) Browsable HTML, which needs no GUI or X11. report_metrics DOES accept
    # -recursive, unlike the legacy report command. (There is no report_summary
    # command in imc 21.09 -- an earlier version of this script called one and
    # it failed silently, producing no summary at all.)
    emit_html ""
    rm -rf "$OUT/functional_html"
    printf 'report_metrics -detail -metrics covergroup -out %s/functional_html\n' "$OUT"
    printf 'exit\n'
} > "$tcl"

"$IMC" -exec "$tcl" -nostdout -logfile "$OUT/imc.log" > "$OUT/imc.stdout" 2>&1
rc=$?
echo "imc exit=$rc  (see $OUT/imc.log)"

# Stitch the per-instance reports into one, and fail loudly if an instance
# produced nothing -- a renamed or moved instance would otherwise just vanish
# from the report and quietly inflate the DM's coverage.
stitch() {   # stitch <tag> <report>
    local inst part missing=()
    : > "$2"
    for inst in "${DM_INSTS[@]}"; do
        part="$OUT/.part$1.$inst.rpt"
        if [ -s "$part" ] && grep -q '^Instance name:' "$part"; then
            {
                printf '\n%s\n== %s\n%s\n' "$(printf '=%.0s' {1..78})" "$inst" \
                       "$(printf '=%.0s' {1..78})"
                cat "$part"
            } >> "$2"
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
}
stitch "" "$OUT/dm_code.rpt"

# imc states counts, never percentages, and has no notion of "the Debug Module"
# as a unit -- so sum across the instances that make it up.
python3 "$(dirname "${BASH_SOURCE[0]}")/dm_cov_summary.py" "$OUT/dm_code.rpt" || true

# (d) The same reports with the unreachable-code exclusions applied. The
# exclusions are generated from dm_code.rpt, so this needs a second imc pass.
if python3 "$(dirname "${BASH_SOURCE[0]}")/dm_cov_exclude.py" "$OUT/dm_code.rpt" \
        --out "$OUT/dm_exclusions.tcl"; then
    {
        printf 'load -run %s/merged\n' "$COV_DIR"
        printf 'source %s/dm_exclusions.tcl\n' "$OUT"
        emit_parts ".excl"
        emit_html "_excl"
        printf 'exit\n'
    } > "$tcl"
    "$IMC" -exec "$tcl" -nostdout -logfile "$OUT/imc_excl.log" > "$OUT/imc_excl.stdout" 2>&1
    echo "imc (exclusions) exit=$?  (see $OUT/imc_excl.log)"
    stitch ".excl" "$OUT/dm_code_excl.rpt"
    python3 "$(dirname "${BASH_SOURCE[0]}")/dm_cov_summary.py" "$OUT/dm_code_excl.rpt" \
        "Debug subsystem code coverage, unreachable and out-of-scope code excluded" || true
fi
# (e) Functional coverage with the bins this DUT cannot produce excluded. Its
# own pass, so a failure in (d) does not take this number with it.
{
    printf 'load -run %s/merged\n' "$COV_DIR"
    printf 'source %s/fcov_exclusions.tcl\n' "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
    printf 'report -detail -all -metrics covergroup -out %s/functional_excl.rpt\n' "$OUT"
    printf 'report_metrics -detail -metrics covergroup -out %s/functional_html_excl\n' "$OUT"
    printf 'exit\n'
} > "$tcl"
"$IMC" -exec "$tcl" -nostdout -logfile "$OUT/imc_fexcl.log" > "$OUT/imc_fexcl.stdout" 2>&1
echo "imc (functional exclusions) exit=$?  (see $OUT/imc_fexcl.log)"
fsum() {   # fsum <report> <label>
    [ -s "$1" ] || { echo "$2: no report" >&2; return; }
    awk -v label="$2" '
        /^Number of covered cover bins:/   { split($0, a, ": "); split(a[2], c, " of "); cov = c[1]; tot = c[2] }
        /^Number of excluded cover bins:/  { split($0, a, ": "); exc = a[2] + 0 }
        # "N of M": imc already leaves excluded bins out of M.
        END { if (tot) printf "%s: %d/%d bins covered (%.2f%%), %d excluded\n",
                              label, cov, tot, 100 * cov / tot, exc }' "$1"
}
fsum "$OUT/functional.rpt"      "Functional coverage"
fsum "$OUT/functional_excl.rpt" "Functional coverage, unreachable bins excluded"

# imc exits 0 on command errors, so its log is the only place they show up.
# NOMATCH is only a warning, but it means an exclusion named nothing and was
# dropped -- the excluded numbers are then wrong without saying so.
grep -hE '\*E,|\*W,NOMATCH' "$OUT/imc.log" "$OUT/imc_excl.log" "$OUT/imc_fexcl.log" 2>/dev/null >&2
ls -la "$OUT"
