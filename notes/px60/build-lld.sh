#!/usr/bin/env bash
# Bounded M2 experiment. LLVM source only; no kernel/libc source inspected.
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
[ -f "$L/lld-build.started" ] || date +%s > "$L/lld-build.started"
printf '%s\n' $$ > "$L/lld-build.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/lld-build.status; exit "$s"' EXIT
podman build -t localhost/px60-lld -f "$L/musl/Containerfile.lld" "$L/musl"
mkdir -p "$L/llvm-download" "$L/llvm-build" "$L/lld-out"
# --foreground signals only this child, never a host process group.
started=$(cat "$L/lld-build.started")
remaining=$((started + 3600 - $(date +%s)))
[ "$remaining" -gt 0 ] || { echo "M2 wall: one-hour source-build budget exhausted"; exit 124; }
timeout --foreground "$remaining" taskset -c 0-7 podman run --rm --name px60-lld-build \
 --cpuset-cpus 0-7 -v "$L:/work" -w /work localhost/px60-lld sh -c '
 set -eu
 if [ ! -f /work/llvm-download/llvm-project-17.0.6.src.tar.xz ]; then
 curl -fL --retry 3 https://github.com/llvm/llvm-project/releases/download/llvmorg-17.0.6/llvm-project-17.0.6.src.tar.xz \
   -o /work/llvm-download/llvm-project-17.0.6.src.tar.xz
 fi
 sha256sum /work/llvm-download/llvm-project-17.0.6.src.tar.xz
 sha256sum /work/llvm-download/llvm-project-17.0.6.src.tar.xz
 echo "58a8818c60e6627064f312dbf46c02d9949956558340938b71cf731ad8bc0813  /work/llvm-download/llvm-project-17.0.6.src.tar.xz" | sha256sum -c -
 if [ ! -d /work/llvm-download/llvm-project-17.0.6.src ]; then
 tar -xJf /work/llvm-download/llvm-project-17.0.6.src.tar.xz -C /work/llvm-download
 fi
 cmake -S /work/llvm-download/llvm-project-17.0.6.src/llvm -B /work/llvm-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_FLAGS="-fno-pie --rtlib=compiler-rt" \
  -DCMAKE_CXX_FLAGS="-fno-pie -stdlib=libc++ --rtlib=compiler-rt -unwindlib=libunwind" \
  -DCMAKE_EXE_LINKER_FLAGS="-static -no-pie -stdlib=libc++ --rtlib=compiler-rt -unwindlib=libunwind" \
  -DCMAKE_CXX_STANDARD_LIBRARIES="-Wl,--start-group -lc++ -lc++abi -lunwind -Wl,--end-group" -DLLVM_USE_LINKER=lld \
  -DLLVM_ENABLE_PROJECTS=lld -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_ENABLE_LIBCXX=ON \
  -DLLVM_BUILD_STATIC=ON -DLLVM_ENABLE_PIC=OFF -DLLVM_PARALLEL_LINK_JOBS=1 \
  -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_LIBXML2=OFF \
  -DLLVM_ENABLE_TERMINFO=OFF -DLLVM_ENABLE_FFI=OFF -DLLVM_ENABLE_LIBEDIT=OFF \
  -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF
 ninja -C /work/llvm-build -j 8 lld
 cp -L /work/llvm-build/bin/ld.lld /work/lld-out/ld.lld
 /work/lld-out/ld.lld --version
 sha256sum /work/lld-out/ld.lld
 sha256sum /work/lld-out/ld.lld
 '
