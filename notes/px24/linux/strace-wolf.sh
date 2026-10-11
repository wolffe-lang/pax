#!/usr/bin/env bash
# px24: the wolf witness under strace -f on Linux, sized under wolf-lang#713. Inside px13-ubuntu.
set -uo pipefail
W=/w/st
out=$W/wolf-strace
rm -rf "$out"; mkdir -p "$out"
B=$W/bin/waitwolf
sha256sum "$B" > "$out/sums.txt"
uname -r >> "$out/sums.txt"; strace -V | head -n 1 >> "$out/sums.txt"
timeout 60 strace -f -s 96 -o "$out/loop-6.strace" "$B" loop 7080 6 > "$out/loop-6.out" 2>&1; echo "rc=$?" >> "$out/loop-6.out"
timeout 60 strace -f -s 96 -o "$out/serve-12.strace" "$B" serve 7081 12 > "$out/serve-12.out" 2>&1 &
sp=$!
sleep 0.5
timeout 60 strace -f -s 96 -o "$out/call-12.strace" "$B" call 127.0.0.1 7081 12 > "$out/call-12.out" 2>&1; echo "rc=$?" >> "$out/call-12.out"
wait $sp; echo "rc=$?" >> "$out/serve-12.out"
timeout 60 taskset -c 0 strace -f -s 96 -o "$out/loop-6-1cpu.strace" "$B" loop 7082 6 > "$out/loop-6-1cpu.out" 2>&1; echo "rc=$?" >> "$out/loop-6-1cpu.out"
head -n 5 "$out"/*.out
wc -l "$out"/*.strace
