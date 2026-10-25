#!/usr/bin/env bash
# px80 (px65's verify.sh, lane-local): the dev ISO's inputs, each read twice
# against its record before it is copied and read again:
#  - the static wolf 0.2.35, its worker and runtime (user/wolf.sums): px65's
#    bytes, taken from the playground's pax-dev.iso (px65's 02f979be...) and
#    verified against the pin (their sums have not moved since fd9827bd);
#  - the native link bundle (user/wolf-link.sums, px80's): the new ld.lld
#    from notes/px80/build-lld.sh, px60's cc and sysroot from that ISO;
#  - the std tree, the compiler's STD-PIN fetched again (tools/mkwolf-std).
set -euo pipefail
L=$HOME/lanes/px80/dev
P=$HOME/lanes/px80
printf '%s\n' $$ > "$L/verify.pid"
rm -rf "$L/final-out" "$L/link-out"; mkdir -p "$L/final-out" "$L/link-out"
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
check "$L/pax/user/wolf.sums" "$P/wolf-bin" "$L/final-out"
check "$L/pax/user/wolf-link.sums" "$P/link-new" "$L/link-out"
podman run --rm --cpuset-cpus 0-3 -v "$L:$L:Z" -e L="$L" -w "$L/pax" localhost/px57-rust bash -c '
set -euo pipefail
rm -rf "$L/std"
tools/mkwolf-std "$L/std"
tests/mpx5-wolf.d/verify-bins "$L/final-out"
'
echo "verify.sh done"
