#!/usr/bin/env bash
# Reproduce the measured native link bundle in the lane's fixed build paths.
# Run on kasumi after staging this repository at $L/pax and px57-rust.
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
P=$L/pax
mkdir -p "$L/musl" "$L/m2/sysroot" "$L/link-out/sysroot"
cp "$P/notes/px60/musl/Containerfile" "$P/notes/px60/musl/Containerfile.lld" "$L/musl/"
podman build -t localhost/px60-musl -f "$L/musl/Containerfile" "$L/musl"
if [ ! -f "$L/lld-out/ld.lld" ]; then
    bash "$P/notes/px60/build-lld.sh"
fi
podman run --rm -v "$L:/work" localhost/px60-musl sh -c '
 set -eu
 for f in crt1.o crti.o crtn.o libc.a; do cp /usr/lib/$f /work/m2/sysroot/; done
 '
cp "$P/notes/px60/cc.rs" "$L/cc.rs"
podman run --rm --cpuset-cpus 0-3 -v "$L:/work" -w /work localhost/px57-rust bash -c '
 set -euo pipefail
 rustc --version
 rustc --edition=2024 --target x86_64-unknown-linux-musl -C relocation-model=static -C strip=symbols -C link-arg=-Wl,--build-id=none cc.rs -o /work/m2/cc
 rustc --test --edition=2024 --target x86_64-unknown-linux-musl -C relocation-model=static cc.rs -o /work/m2/cc-test
 /work/m2/cc-test --nocapture
 cp /opt/rust/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-musl/lib/self-contained/libunwind.a /work/m2/sysroot/
 '
bash "$P/notes/px60/decompress.sh"
cp "$L/lld-out/ld.lld" "$L/m2/cc" "$L/link-out/"
cp "$L/m2/sysroot-uncompressed/"* "$L/link-out/sysroot/"
awk '{print $2 "  " $1}' "$P/user/wolf-link.sums" | (cd "$L/link-out" && sha256sum -c -)
