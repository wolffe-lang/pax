#!/usr/bin/env bash
# px87 on kasumi: a worktree of the lane's clone pinned to one commit, for a build (never the live tree).
#   wt.sh SHA   ->  prints /home/mfwolffe/lanes/px87/w/<sha8>
set -euo pipefail
L=/home/mfwolffe/lanes/px87
sha=$1
git -C "$L/pax" fetch -q origin px87 'refs/heads/px87-plant-*:refs/remotes/origin/px87-plant-*' 2>/dev/null || git -C "$L/pax" fetch -q origin px87
full=$(git -C "$L/pax" rev-parse "$sha^{commit}")
d=$L/w/${full:0:8}
if [ ! -d "$d" ]; then
    mkdir -p "$L/w"
    git -C "$L/pax" worktree add -q --detach "$d" "$full"
fi
[ "$(git -C "$d" rev-parse HEAD)" = "$full" ] || { echo "worktree $d is not at $full" >&2; exit 3; }
[ -z "$(git -C "$d" status --porcelain --untracked-files=no)" ] || { echo "worktree $d is dirty" >&2; exit 3; }
echo "$d"
