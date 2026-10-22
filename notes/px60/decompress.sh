#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px60
podman run --rm -v "$L:/work" localhost/px60-musl sh -c '
 set -eu
 mkdir -p /work/m2/sysroot-uncompressed
 llvm-objcopy --version
 for f in crt1.o crti.o crtn.o libc.a libunwind.a; do
   llvm-objcopy --decompress-debug-sections /work/m2/sysroot/$f /work/m2/sysroot-uncompressed/$f
 done
 sha256sum /work/m2/sysroot-uncompressed/*
 sha256sum /work/m2/sysroot-uncompressed/*
 '
