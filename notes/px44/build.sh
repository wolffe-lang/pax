#!/bin/bash
# px44: build the programs inside px13-ubuntu (Ubuntu 24.04, glibc 2.39;
# never kasumi's own glibc): tools/mkcred's nine (px39's four, px42's
# `own` and `perm`, px43's `chk` and `seven`, px44's `setid`), and
# notes/px44/vminit.
#   build.sh PAXROOT OUTDIR      (run inside the container)
set -euo pipefail
pax=$1 out=$2
"$pax/tools/mkcred" "$out"
cc -static -no-pie -O1 -Wall -Wextra -Wno-unused-result -Wno-unused-function -Wl,--build-id=none -Wl,-z,noexecstack \
    -I "$pax/user/elf" -o "$out/vminit" "$pax/notes/px44/vminit.c"
printf '%s %s %s\n' vminit "$(sha256sum "$out/vminit" | cut -d' ' -f1)" "$(wc -c < "$out/vminit")"
cc --version | sed -n 1p
ldd --version | sed -n 1p
