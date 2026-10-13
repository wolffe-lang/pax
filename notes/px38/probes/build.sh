#!/bin/bash
# px38: build the probes, static, with the container's glibc (run inside
# px13-ubuntu: Ubuntu 24.04, glibc 2.39; never kasumi's own glibc).
#   build.sh SRCDIR OUTDIR
set -euo pipefail
src=$1 out=$2
mkdir -p "$out"
for p in ids cred perm setid sig vminit; do
    cc -static -no-pie -O1 -Wall -Wextra -Wno-unused-result -Wno-unused-function -Wl,--build-id=none -Wl,-z,noexecstack \
        -o "$out/$p" "$src/$p.c"
    readelf -hW "$out/$p" | grep -Eq 'Type: +EXEC'
    ! readelf -lW "$out/$p" | grep -q INTERP
    printf '%s %s %s\n' "$p" "$(sha256sum "$out/$p" | cut -d' ' -f1)" "$(wc -c < "$out/$p")"
done
cc --version | head -n 1
ldd --version | head -n 1
