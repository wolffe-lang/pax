#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
printf '%s\n' $$ > "$L/m2.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/m2.status; exit "$s"' EXIT
mkdir -p "$L/m2/sysroot" "$L/m2/tmp"
podman run --rm -v "$L:/work" localhost/px60-musl sh -c '
 set -eu
 for f in crt1.o crti.o crtn.o libc.a; do cp /usr/lib/$f /work/m2/sysroot/; done
 apk info -v musl musl-dev lld lld-dev llvm17-static
 echo "STATIC LLD ARCHIVES:"
 find /usr -name "liblld*.a"
 echo "STATIC LINK OF PACKAGED LLD:"
 ld.lld -static /usr/lib/liblldELF.so -o /work/m2/lld-probe; rc=$?
 echo "lld static rc=$rc"
 ' || echo "packaged-static-lld step failed as recorded above"
podman run --rm -v "$L:/work" localhost/px57-rust \
 cp /opt/rust/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-musl/lib/self-contained/libunwind.a /work/m2/sysroot/
podman run --rm --cpuset-cpus 0-3 -v "$L:/work" -w /work/m2 \
 -e CC=/work/cc-lld.py -e WOLF_STD=/work/std -e TMPDIR=/work/m2/tmp \
 localhost/px13-ubuntu bash -c '
 set -uo pipefail
 for name in hello loop signal fork spawn exec host std; do
   echo "M2 BUILD $name"
   /work/final-out/wolf build --no-cache /work/pax/user/wolf/$name.lu -o /work/m2/$name
   rc=$?; echo "M2 BUILD $name rc=$rc"
   if [ "$rc" = 0 ]; then
     readelf -hW /work/m2/$name | grep Type
     readelf -dW /work/m2/$name
     /work/m2/$name; echo "M2 RUN $name rc=$?"
     sha256sum /work/m2/$name
   fi
 done
 '
sha256sum "$L/m2/sysroot/"*
sha256sum "$L/m2/sysroot/"*
