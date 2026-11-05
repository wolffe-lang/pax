#!/usr/bin/env bash
# px89: one suite at one commit, in the container, behind the block's
# locks (launch.sh runs this as `run.sh BLOCK NAME SHA [KVM=1] [NET=1] -- CMD...`).
# The commit is checked out in a worktree of its own (never the live
# tree: the lane rules, "Build from a commit"); the build directory is
# build/NAME. Every git here passes -c commit.gpgsign=false (the lane host's
# global config signs with the maintainer's key; nothing is committed
# here, and the flag is passed anyway).
set -uo pipefail
L=/home/mfwolffe/lanes/px89
S=$L/scripts
B=$1 N=$2 SHA=$3; shift 3
G="git -c commit.gpgsign=false"
flock "$L/git.lock" $G -C "$L/pax" fetch -q origin '+refs/heads/px89*:refs/remotes/origin/px89*' || { echo "  fetch failed"; exit 1; }
full=$($G -C "$L/pax" rev-parse "$SHA^{commit}") || { echo "  no commit $SHA"; exit 1; }
WT=$L/wt-${full:0:8}
[ -d "$WT" ] || flock "$L/git.lock" $G -C "$L/pax" worktree add -q --detach "$WT" "$full" || { echo "  worktree failed"; exit 1; }
[ "$($G -C "$WT" rev-parse HEAD)" = "$full" ] || { echo "  worktree $WT is not at $full"; exit 1; }
mkdir -p "$L/build/$N"
echo "  run $N at $full in $WT, build $L/build/$N"
opts=()
while :; do case ${1:-} in KVM=1|NET=1|KVM=0|NET=0) opts+=("$1"); shift ;; *) break ;; esac; done
[ "${1:-}" = -- ] && shift
CTR_WD=$WT CTR_ENV="-e PAX_BUILD=$L/build/$N ${CTR_ENV:-}" bash "$S/ctr.sh" "$B" "$N" localhost/px89-dhcp:1 ${opts[@]+"${opts[@]}"} -- \
    bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); "$@"; exit $?' px89-run "$@"
