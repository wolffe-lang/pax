#!/usr/bin/env bash
# notes/px119/rig/take.sh MANIFEST OUTPUT [--base SHA --plant ROW…] — one record of MANIFEST (a file
# beside this one) at this checkout's head: the block's two lock names, the block's first, one long
# flock each, then the recorder (REC, PX119_HOST's) in steps mode with --keep-going and --preflight.
# PAX_BUILD is the lane's pb-<sha8>-<manifest>. Run from a clean checkout of the head (a worktree);
# never from a live tree.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
here=$(cd "$(dirname "$0")" && pwd)
: "${PX119_HOST:?PX119_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX119_HOST"
: "${L:?}" "${P:?}" "${LOCK1:?}" "${LOCK2:?}" "${REC:?}"
man=${1:?a manifest} out=${2:?the record}; shift 2
CO=$(git -C "$here" rev-parse --show-toplevel)
cd "$CO" || exit 2
PAX_BUILD=$L/pb-$(git rev-parse --short=8 HEAD)-$(basename "$man" .manifest)
PATH=$(dirname "$P"):$PATH
export PAX_BUILD PX119_HOST PATH
echo "take: $(git rev-parse HEAD) $man -> $out; waiting on $LOCK1, then $LOCK2 at $(date -u +%FT%TZ)"
flock -w 21600 "$LOCK1" flock -w 21600 "$LOCK2" bash "$REC" --output "$out" --steps "$here/$man" --keep-going \
    --preflight 'bash notes/px119/rig/step.sh preflight' "$@"
rc=$?
echo "take: exit $rc at $(date -u +%FT%TZ)"
exit "$rc"
