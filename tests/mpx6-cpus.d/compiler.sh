#!/usr/bin/env bash
# Build-only witness of the existing freestanding ABI; never run privileged stubs.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output}
mkdir -p "$out"
for tier in native release; do
    f=(); [ "$tier" != release ] || f=(--release)
    (cd "$root/tests/mpx6-cpus.d/compiler" && "$PAX_WOLF" build probe.lu --target x86_64-unknown-none --emit=obj "${f[@]}" -o "$out/$tier.o")
    objdump -d "$out/$tier.asm-cpu.o" > "$out/$tier.asm.dis"
    objdump -d "$out/$tier.o" > "$out/$tier.dis"
    grep -q 'gs:0x0' "$out/$tier.asm.dis"
    grep -q 'swapgs' "$out/$tier.asm.dis"
    grep -q 'lock cmpxchg' "$out/$tier.dis"
    printf 'PASS CPU-COMPILER %s: GS stubs and acquire CAS emitted\n' "$tier"
done
