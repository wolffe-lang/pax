#!/usr/bin/env bash
# notes/px122/rig/take.sh CHECKOUT MANIFEST OUTPUT [RECORDER ARGS…] — one record of MANIFEST (a file
# beside this one) at CHECKOUT's head (a clean worktree of the commit under test, never a live tree;
# it need not hold this rig): the host file's LOCKS taken in its order, one long flock each, then the
# recorder (REC) in steps mode with --keep-going and --preflight. PAX_BUILD is the lane's
# pb-<sha8>-<manifest>, removed first so a take never reads an earlier one's images.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
here=$(cd "$(dirname "$0")" && pwd)
: "${PX122_HOST:?PX122_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX122_HOST"
: "${L:?}" "${P:?}" "${LOCKS?}" "${REC:?}"
co=${1:?a checkout} man=${2:?a manifest} out=${3:?the record}; shift 3
cd "$co" || exit 2
PAX_BUILD=$L/pb-$(git rev-parse --short=8 HEAD)-$(basename "$man" .manifest)
PATH=$(dirname "$P"):$PATH
export PAX_BUILD PX122_HOST PATH
wrap=()
for lock in $LOCKS; do wrap+=(flock -w 21600 "$lock"); done
echo "take: $(git rev-parse HEAD) $man -> $out; waiting on $LOCKS at $(date -u +%FT%TZ)"
"${wrap[@]}" bash -c 'echo "take: holding the locks at $(date -u +%FT%TZ)"; rm -rf "$PAX_BUILD"; exec "$@"' x \
    bash "$REC" --output "$out" --steps "$here/$man" --keep-going --preflight "bash $here/step.sh preflight" "$@"
rc=$?
echo "take: exit $rc at $(date -u +%FT%TZ)"
exit "$rc"
