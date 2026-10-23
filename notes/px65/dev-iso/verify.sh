#!/usr/bin/env bash
# px65: px64's verify.sh (px62's), lane-local: the static wolf 0.2.35, its
# runtime and worker (user/wolf.sums) from this lane's own tools/mkwolf
# build on kasumi (~/lanes/px65/wolf-out, the bytes CI's mpx5-wolf job
# rebuilds), and the native link stack (user/wolf-link.sums) reused from
# px60's retained build, never rebuilt: every file's sha256 read twice
# against the recorded digest, then copied; the copies read again. The std tree is the compiler's STD-PIN fetched again
# (tools/mkwolf-std: a git fetch by revision, no build).
set -euo pipefail
L=$HOME/lanes/px65/dev
P=$HOME/lanes/px60
WO=$HOME/lanes/px65/wolf-out
printf '%s\n' $$ > "$L/verify.pid"
mkdir -p "$L/final-out" "$L/link-out"
check() { # sums-file srcdir dstdir
    while read -r name sha bytes; do
        [ -n "$name" ] || continue
        for k in 1 2; do
            got=$(sha256sum "$2/$name" | cut -d' ' -f1)
            [ "$got" = "$sha" ] || { echo "MISMATCH $name read $k: $got, recorded $sha"; exit 1; }
        done
        [ "$(wc -c < "$2/$name" | tr -d ' ')" = "$bytes" ] || { echo "SIZE $name"; exit 1; }
        mkdir -p "$3/$(dirname "$name")"
        cp -p "$2/$name" "$3/$name"
        [ "$(sha256sum "$3/$name" | cut -d' ' -f1)" = "$sha" ] || { echo "COPY $name"; exit 1; }
        echo "verified twice, copied: $name $sha $bytes"
    done < "$1"
}
check "$L/pax/user/wolf.sums" "$WO" "$L/final-out"
cp "$WO/sums.txt" "$L/final-out/sums.txt"
check "$L/pax/user/wolf-link.sums" "$P/link-out" "$L/link-out"
cp "$P/link-out/sums.txt" "$L/link-out/sums.txt"
podman run --rm --cpuset-cpus 12-15 -v "$L:$L:Z" -e L="$L" -w "$L/pax" localhost/px57-rust bash -c '
set -euo pipefail
rm -rf "$L/std"
tools/mkwolf-std "$L/std"
tests/mpx5-wolf.d/verify-bins "$L/final-out"
'
echo "verify.sh done"
