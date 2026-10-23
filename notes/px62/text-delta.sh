#!/usr/bin/env bash
# px62, kasumi only: kmain_console's sections at the base (pax trunk
# c0d394ee, px61) and at the lane's head, both tiers, built in
# px13-ubuntu on CPUs 4-7 (the boots keep 0-3). Prints `size -A` rows.
#   text-delta.sh BASE_SRC HEAD_SRC OUT
set -euo pipefail
L=$HOME/lanes/px62
base=$1 head=$2 out=$3
mkdir -p "$out" "$L/cache" "$L/tmp"
for side in base head; do
    src=$base; [ "$side" = head ] && src=$head
    for tier in native release; do
        podman run --rm --cpuset-cpus 4-7 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" \
            localhost/px13-ubuntu bash -c '
                set -euo pipefail; cd "$1"; w=$(tools/fetch-wolf | tail -1)
                flag=(); [ "$3" = release ] && flag=(--release)
                elf=$(PAX_WOLF=$w tools/build-kernel ${flag[@]+"${flag[@]}"} --src kernel/kmain_console.lu "$2" 2>/dev/null)
                size -A "$elf" | awk "\$1 ~ /^\\.(text|rodata|data|bss)\$/ { print \$1, \$2 }"
                sha256sum "$elf" | cut -d" " -f1
            ' px62 "$src" "$out/$side-$tier" "$tier" > "$out/$side-$tier.size"
        echo "$side $tier: $(tr '\n' ' ' < "$out/$side-$tier.size")"
    done
done
