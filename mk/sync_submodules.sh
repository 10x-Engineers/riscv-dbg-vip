#!/usr/bin/env bash
# Put every submodule at the commit this checkout pins, from the remote the
# pinning .gitmodules names:
#   riscv-dbg-vip -> CVA6-fork, ibex-demo-system
#   CVA6-fork     -> corev_apu/riscv-dbg (the Debug Module under test) and the
#                    rest of CVA6's own submodules
#
# Three things `git pull` alone gets wrong, each seen on a real checkout:
#   1. Submodules stay where they were. A pull moves only the parent, so
#      CVA6-fork can sit on a months-old pin (6a39e2c3, fork master, June).
#   2. Submodule URLs never refresh. CVA6-fork a3f6c39d moved riscv-dbg from
#      pulp-platform to the 10x fork, but a clone made before that keeps
#      fetching from pulp, which has none of the 10x branches or commits.
#      `git submodule sync` re-reads .gitmodules into the local config.
#   3. `--remote` ignores the pins. It takes each branch tip instead: CVA6-fork
#      master (June), and PR #4's head for the DM, which fails Xcelium
#      elaboration. This script never passes it.
#
# Usage: mk/sync_submodules.sh [--pull] [--force]
#   --pull   first fast-forward the current branch of riscv-dbg-vip
#   --force  proceed even if a submodule has uncommitted changes (they may be
#            lost when the pinned commit is checked out)
set -euo pipefail

PULL=0 FORCE=0
for arg in "$@"; do
    case $arg in
        --pull)  PULL=1 ;;
        --force) FORCE=1 ;;
        *) echo "usage: $0 [--pull] [--force]" >&2; exit 2 ;;
    esac
done

cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

# Refuse to check a pinned commit out over local work unless told to.
dirty=$(git submodule foreach --quiet --recursive \
        'if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "  $displaypath"; fi')
if [[ -n $dirty && $FORCE -eq 0 ]]; then
    echo "Submodules with uncommitted changes (commit or stash them, or rerun with --force):" >&2
    echo "$dirty" >&2
    exit 1
fi

if [[ $PULL -eq 1 ]]; then
    git pull --ff-only
fi

git submodule sync --recursive --quiet
git submodule update --init --recursive

# Report what is checked out against what is pinned. `git submodule status`
# prefixes '+' for a checkout that differs from the pin, '-' for one not
# initialised and 'U' for a merge conflict; a space means it matches.
echo
echo "riscv-dbg-vip $(git rev-parse --short HEAD) ($(git rev-parse --abbrev-ref HEAD))"
bad=0
while IFS= read -r line; do   # IFS= keeps the leading status column
    flag=${line:0:1} sha=$(awk '{print $1}' <<<"${line:1}") path=$(awk '{print $2}' <<<"${line:1}")
    case $path in
        CVA6-fork|ibex-demo-system|CVA6-fork/corev_apu/riscv-dbg)
            printf '  %-32s %s  %s\n' "$path" "${sha:0:8}" "$(git -C "$path" remote get-url origin)" ;;
    esac
    [[ $flag == " " ]] || { echo "  NOT AT PIN ($flag): $path" >&2; bad=1; }
done < <(git submodule status --recursive)

exit $bad
