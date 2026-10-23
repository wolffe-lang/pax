#!/usr/bin/env bash
# px63, kasumi only: compile one kernel entry point and print only the
# errors (wolf's warnings for undocumented pub items drown them).
#   kcheck.sh KMAIN
set -euo pipefail
L=$HOME/lanes/px63
k=${1:-kmain_console}
mkdir -p "$L/kc" "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        cd "$1/pax/kernel"; w=$(../tools/fetch-wolf 2>/dev/null | tail -1)
        "$w" build "$2.lu" --target x86_64-unknown-none --emit=obj -o "$1/kc/$2.o" --error-limit=0 > "$1/kc/$2.log" 2>&1
        rc=$?
        awk "/^error/{p=1} /^warning/{p=0} p" "$1/kc/$2.log" | head -150
        echo "wolf build rc=$rc"
    ' px63 "$L" "$k"
