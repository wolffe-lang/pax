#!/bin/bash
# px65, kasumi: the three release archives by digest, each downloaded and
# hashed twice (two downloads, two reads each), in the lane's container:
# wolf 0.2.35 (linux x86-64), lupin 0.1.56 (glibc, tests/mkw's) and the
# new lupin 0.1.56 musl archive, whose binary is read as PAX's loader
# reads it (readelf: type, program headers, dynamic section).
L=$HOME/lanes/px65
mkdir -p "$L/ev/archives"
podman run --rm --cpuset-cpus 12-15 -v "$L:$L:Z" -e A="$L/ev/archives" localhost/px65-ubuntu bash -c '
set -u
cd "$A"
get() { # name url
    for k in 1 2; do
        rm -f "$1.$k"; curl -sSfL --retry 3 -o "$1.$k" "$2" || { echo "download $k of $1 failed"; return 1; }
        echo "download $k: $(sha256sum < "$1.$k" | cut -c1-64) $(wc -c < "$1.$k") $1"
        echo "  read again: $(sha256sum < "$1.$k" | cut -c1-64)"
    done
}
get wolf-0.2.35-x86_64-unknown-linux-gnu.tar.gz https://github.com/wolffe-lang/wolf-lang/releases/download/v0.2.35/wolf-0.2.35-x86_64-unknown-linux-gnu.tar.gz
get lupin-0.1.56-x86_64-unknown-linux-gnu.tar.gz https://github.com/wolffe-lang/wolf-interp/releases/download/v0.1.56/lupin-0.1.56-x86_64-unknown-linux-gnu.tar.gz
get lupin-0.1.56-x86_64-unknown-linux-musl.tar.gz https://github.com/wolffe-lang/wolf-interp/releases/download/v0.1.56/lupin-0.1.56-x86_64-unknown-linux-musl.tar.gz
for f in wolf-0.2.35-x86_64-unknown-linux-gnu lupin-0.1.56-x86_64-unknown-linux-gnu lupin-0.1.56-x86_64-unknown-linux-musl; do
    rm -rf "x-$f"; mkdir -p "x-$f"; tar -xzf "$f.tar.gz.1" -C "x-$f"
    echo "== $f: $(find "x-$f" -type f | wc -l) files"; find "x-$f" -maxdepth 2 | sort | head -20
done
m=$(find x-lupin-0.1.56-x86_64-unknown-linux-musl -name lupin -type f | head -n 1)
g=$(find x-lupin-0.1.56-x86_64-unknown-linux-gnu -name lupin -type f | head -n 1)
w=$(find x-wolf-0.2.35-x86_64-unknown-linux-gnu -name wolf -type f | head -n 1)
echo "== musl lupin: $m $(sha256sum < "$m" | cut -c1-64) $(wc -c < "$m")"
readelf -hW "$m" | grep -E "Type:|Machine:"
readelf -lW "$m" | grep -E "^ +[A-Z_]+ " | awk "{print \$1}" | sort | uniq -c
readelf -dW "$m" | head -2
"$m" --version
echo "== glibc lupin: $g $(sha256sum < "$g" | cut -c1-64)"; "$g" --version
echo "== wolf: $w $(sha256sum < "$w" | cut -c1-64)"; "$w" --version; cat "$(dirname "$w")/std/STD-REV" 2>/dev/null
'
