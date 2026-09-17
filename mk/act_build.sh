#!/usr/bin/env bash
# Build the riscv-arch-test (ACT4) native-debug programs for the CVA6 build under
# test and stage them for the regression.
#
#   bash mk/act_build.sh [EXTENSIONS]        # default: SdtrigSm
#
# Output: cva6_sim/sw/act/<test>.elf, one per program, and
#         cva6_sim/configs/act/<test>.json, one run_elf config per program.
#
# Needs (override with the variables below):
#   ACT_DIR    a riscv-arch-test checkout on the act4 branch
#   GCC15      RISC-V GCC 15+ (ACT4 refuses anything older)
#   SPIKE      a current Spike (the reference model: Sail has no Sdtrig)
#   UV, RUBY   uv and Ruby 3.2+ (ACT4's generator and its UDB gem); `mise install`
#              in ACT_DIR provides both
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
EXTENSIONS=${1:-SdtrigSm}
ACT_DIR=${ACT_DIR:-/work/10x-jkhalid/riscv-arch-test}
GCC15=${GCC15:-/opt/riscv15/bin}
SPIKE=${SPIKE:-/work/10x-jkhalid/tools/spike/bin}
MISE_INSTALLS=${MISE_INSTALLS:-$HOME/.local/share/mise/installs}
UV=${UV:-$(ls -d "$MISE_INSTALLS"/uv/*/uv-* 2>/dev/null | tail -1)}
RUBY=${RUBY:-$(ls -d "$MISE_INSTALLS"/ruby/*/bin 2>/dev/null | tail -1)}
CONFIG="$ROOT/cva6_sim/act/cv64a6-sdtrig/test_config.yaml"
NAME=cv64a6-sdtrig

export PATH="$GCC15:$SPIKE:$UV:$RUBY:$PATH"
# uv otherwise picks the first python3 on PATH; ACT4 needs 3.10+.
export UV_PYTHON=${UV_PYTHON:-$(command -v python3.14 || command -v python3.12)}

for tool in riscv64-unknown-elf-gcc spike uv ruby bundle; do
    command -v "$tool" > /dev/null || { echo "act_build: $tool not found" >&2; exit 1; }
done

# The Sdtrig generator hard-codes the trigger features it tests
# (SdtrigCommon.py UDB_DEFINES, "TODO: Relate to UDB") instead of reading the
# DUT's UDB config. Turn off what this CVA6 does not implement, for the length
# of the build only:
#   tdata3, scontext, mcontext -- SdtrigSupportTextra=0; Sdtrig requires an
#                                 illegal-instruction trap for trigger CSRs no
#                                 implemented trigger uses, and CVA6 raises it
#   VS/VU                      -- no H extension
GEN="$ACT_DIR/generators/testgen/src/testgen/priv/extensions/SdtrigCommon.py"
cp "$GEN" "$GEN.act_build_orig"
restore_gen() { mv -f "$GEN.act_build_orig" "$GEN"; }
trap restore_gen EXIT
python3 - "$GEN" <<'PY'
import sys
path = sys.argv[1]
src = open(path).read()
for name in ("UDB_TDATA3_AVAILABLE", "UDB_SCONTEXT_AVAILABLE", "UDB_MCONTEXT_AVAILABLE",
             "UDB_SDTRIG_VS_AVAILABLE", "UDB_SDTRIG_VU_AVAILABLE"):
    on = f'"#define {name}",'
    if on not in src:
        sys.exit(f"act_build: {name} not found in {path}; the generator changed, re-check the override")
    src = src.replace(on, f'"//#define {name}",')
# Every trigger-config helper writes tdata3 unconditionally, so with
# UDB_TDATA3_AVAILABLE off the write still happens and traps on a DUT without
# tdata3 -- the reference (Spike, which has it) does not, and the first trap
# check fails. Guard the write with the same define.
import re
pat = re.compile(r'(?P<ind>[ \t]*)_load_reg\(reg, tdata3\),\n(?P=ind)_csr_access\(f"csrw tdata3,[^\n]*\),\n')
src, n = pat.subn(lambda m: (f'{m["ind"]}"#ifdef UDB_TDATA3_AVAILABLE",\n{m.group(0)}'
                             f'{m["ind"]}"#endif",\n'), src)
if n == 0:
    sys.exit(f"act_build: no tdata3 writes found to guard in {path}; re-check the override")
# Upstream wrote the icount tests but left their bodies commented out (the
# suite is "partially implemented"), so SdtrigSm_Icount builds to an empty
# program that passes without arming a trigger. Switch the written cases on,
# and declare both triggers as supporting icount (CVA6: SdtrigIcount=1).
# UDB_ICOUNT_HARDWIRED_1 stays undefined: CVA6's count is not hard-wired to 1.
a, b = src.index("def _generate_icount_tests"), src.index("def _generate_itrigger_tests")
body, n = [], 0
for line in src[a:b].split("\n"):
    m = re.match(r"^(\s*)# (covergroup =.*|lines\.append\(.*|for trig_num.*| {4}.*)$", line)
    if m:
        line, n = m.group(1) + m.group(2), n + 1
    body.append(line)
if n == 0:
    sys.exit(f"act_build: no commented icount code found in {path}; re-check the override")
src = src[:a] + "\n".join(body) + src[b:]
src = src.replace('    "#define UDB_TDATA1_AVAILABLE",',
                  '    "#define UDB_ICOUNT_TRIG0_AVAILABLE",\n'
                  '    "#define UDB_ICOUNT_TRIG1_AVAILABLE",\n'
                  '    "#define UDB_TDATA1_AVAILABLE",', 1)
import ast
ast.parse(src)                       # an uncommenting mistake fails here, not in make
open(path, "w").write(src)
PY

# MISE is emptied and UV_RUN given directly: ACT4's Makefile otherwise runs
# through `mise exec`, whose pre-commit hook setup fails on this host and
# aborts the build before any test is generated.
make -C "$ACT_DIR" MISE= UV_RUN="uv run" CONFIG_FILES="$CONFIG" \
     EXTENSIONS="$EXTENSIONS" EXCLUDE_EXTENSIONS= FAST=True

OUT_ELF="$ROOT/cva6_sim/sw/act"
OUT_CFG="$ROOT/cva6_sim/configs/act"
rm -rf "$OUT_ELF"
mkdir -p "$OUT_ELF" "$OUT_CFG"
n=0
while IFS= read -r elf; do
    test=$(basename "$elf" .elf)
    cp "$elf" "$OUT_ELF/$test.elf"
    cat > "$OUT_CFG/$test.json" <<EOF
{
    "_comment": "Generated by mk/act_build.sh -- riscv-arch-test $test, run to its own tohost verdict.",
    "scenario":  "run_elf",
    "transport": "uvm",
    "mode":      "batch",
    "params": { "elf": "sw/act/$test.elf" },
    "uvm": { "socket_path": "/tmp/uvm_bridge.sock", "timeout": 900.0 }
}
EOF
    n=$((n + 1))
done < <(find "$ACT_DIR/work/$NAME/elfs" -name '*.elf' | sort)
echo "act_build: staged $n program(s) in $OUT_ELF"
