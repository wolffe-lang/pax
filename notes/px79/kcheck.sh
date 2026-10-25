#!/usr/bin/env bash
# px79, kasumi only: the kernel package's errors alone (wolf build with
# no error limit, the warnings left out), in px79-ubuntu on CPUs 0-3
# (the caller holds the cores' lock).
#   kcheck.sh [KMAIN]
set -euo pipefail
L=$HOME/lanes/px79
T=${PAX_TREE:-$L/pax}
k=${1:-kmain_console}
mkdir -p "$L/cache" "$L/tmp" "$L/kc"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px79-ubuntu bash -c '
    set -uo pipefail; cd "$1"; w=$(tools/fetch-wolf | tail -1)
    cd kernel && "$w" build "$2.lu" --target x86_64-unknown-none --emit=obj -o "$3/kc/$2.o" --error-limit=0 > "$3/kc/out.txt" 2>&1; echo "rc=$?"
    awk "/^error/{p=1} /^warning/{p=0} p" "$3/kc/out.txt" | head -150
' px79 "$T" "$k" "$L"
