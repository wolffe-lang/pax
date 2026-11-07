#!/usr/bin/env bash
# notes/px106/rig/chain.sh SHA [CHUNK...] — one head through suite.sh, then the witness's chunks
# (default: build legs-x legs-d legs-a compare), each taking its own locks or the light helper; a
# failed build stops the witness. Logs and exit markers in $L/runs/<name>-<short>.{log,exit};
# chain-<short>.exit says `done` at the end. Run from a checkout of SHA (lib.sh's host file).
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
SHA=$1; shift
here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"
checkout_ok "$SHA" || exit 3
short=${SHA:0:8}
chunks=("$@"); [ ${#chunks[@]} -gt 0 ] || chunks=(suite build legs-x legs-d legs-a compare)
for c in "${chunks[@]}"; do
    case $c in
        suite) "$here/suite.sh" "$SHA" > "$L/runs/suite-$short.log" 2>&1; echo $? > "$L/runs/suite-$short.exit" ;;
        build) "$here/witness.sh" build "$SHA" > "$L/runs/w-build-$short.log" 2>&1; rc=$?; echo $rc > "$L/runs/w-build-$short.exit"
               [ "$rc" = 0 ] || { echo done > "$L/runs/chain-$short.exit"; exit "$rc"; } ;;
        *) "$here/witness.sh" "$c" "$SHA" > "$L/runs/w-$c-$short.log" 2>&1; echo $? > "$L/runs/w-$c-$short.exit" ;;
    esac
done
echo done > "$L/runs/chain-$short.exit"
