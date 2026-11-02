#!/usr/bin/env bash
# px87: the lane's rebase onto trunk, commit by commit. For each pre-rebase commit OLD (BASE..OLDHEAD) and
# its rebased commit NEW (TRUNK..NEWHEAD), in order: the subjects equal, the patches equal (git patch-id
# --stable), and the trees differ only under notes/pm00 (trunk's own commits since BASE); any other
# difference stops the script. Prints the table: old8 new8 old new subject.
#   map.sh BASE OLDHEAD TRUNK NEWHEAD
set -euo pipefail
base=$1 oldhead=$2 trunk=$3 newhead=$4
old=($(git rev-list --reverse "$base..$oldhead"))
new=($(git rev-list --reverse "$trunk..$newhead"))
[ "${#old[@]}" = "${#new[@]}" ] || { echo "map.sh: ${#old[@]} old commits, ${#new[@]} new" >&2; exit 1; }
trunk_paths=$(git diff --name-only "$base" "$trunk" | sort)
printf '# trunk since %s: %s\n' "${base:0:8}" "$(echo $trunk_paths)"
for i in "${!old[@]}"; do
    o=${old[$i]} n=${new[$i]}
    so=$(git log -1 --format=%s "$o") sn=$(git log -1 --format=%s "$n")
    [ "$so" = "$sn" ] || { echo "map.sh: subject differs at $o" >&2; exit 1; }
    po=$(git show "$o" | git patch-id --stable | cut -d' ' -f1)
    pn=$(git show "$n" | git patch-id --stable | cut -d' ' -f1)
    [ "$po" = "$pn" ] || { echo "map.sh: patch differs at $o" >&2; exit 1; }
    d=$(git diff --name-only "$o" "$n" | sort)
    [ "$d" = "$trunk_paths" ] || { echo "map.sh: tree of $n differs from $o beyond trunk's paths: $d" >&2; exit 1; }
    printf '%s %s %s %s %s\n' "${o:0:8}" "${n:0:8}" "$o" "$n" "$so"
done
