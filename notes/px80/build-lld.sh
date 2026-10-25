#!/usr/bin/env bash
# px80: build the dev ISO's static ld.lld at 18.1.8 (R-px80-1 A) from the
# unopened release tarball, by px60's notes/px60/build-lld.sh adapted:
# X86 only, static, clang + libc++/libc++abi + LLVM libunwind + compiler-rt,
# and zlib + zstd built in (R-px80-2 A). kasumi, CPUs 0-3, under the block's
# lock. The tarball is checked against the sha256 recorded below (read twice
# from the download; GitHub's asset size 132,067,260; Homebrew's llvm@18
# formula publishes the same sha256; LLVM's release key signs it) and only the
# directories the build needs are extracted. LLVM is compiled, never read.
#   build-lld.sh            the whole build (image, extract, configure, ninja)
#   PX80_STEP=configure     stop after cmake (to read CMakeCache.txt)
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px80
V=18.1.8
SHA=0b58557a6d32ceee97c8d533a59b9212d87e0fc4d2833924eb6c611247db2f2a
TAR=llvm-project-$V.src.tar.xz
started=$(date +%s)
printf '%s\n' $$ > "$L/lld-build.pid"
trap 's=$?; echo "$s $(( $(date +%s) - started ))s $(date -Is)" > "$L/lld-build.status"' EXIT
echo "px80 build-lld: start $(date -Is), step ${PX80_STEP:-all}"
mkdir -p "$L/dl" "$L/src" "$L/llvm-build" "$L/lld-out"
podman build -q -t localhost/px80-lld -f "$L/pax/notes/px80/Containerfile.lld" "$L/pax/notes/px80"
podman run --rm localhost/px80-lld sh -c 'apk info -vv | sort' > "$L/lld-out/apk-info.txt"
for k in 1 2; do
    got=$(sha256sum "$L/dl/$TAR" | cut -d' ' -f1)
    [ "$got" = "$SHA" ] || { echo "tarball sha256 read $k: $got, recorded $SHA"; exit 1; }
    echo "tarball sha256 read $k: $got"
done
taskset -c 0-3 podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:/work" -w /work \
    -e V="$V" -e STEP="${PX80_STEP:-all}" localhost/px80-lld sh -c '
 set -eu
 S=/work/src/llvm-project-$V.src
 if [ ! -d "$S/lld" ]; then
   tar -xJf /work/dl/llvm-project-$V.src.tar.xz -C /work/src \
     llvm-project-$V.src/cmake llvm-project-$V.src/llvm llvm-project-$V.src/lld \
     llvm-project-$V.src/libunwind llvm-project-$V.src/third-party
 fi
 set -x
 [ -f /work/llvm-build/build.ninja ] || cmake -S "$S/llvm" -B /work/llvm-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_FLAGS="-fno-pie --rtlib=compiler-rt" \
  -DCMAKE_CXX_FLAGS="-fno-pie -stdlib=libc++ --rtlib=compiler-rt -unwindlib=libunwind" \
  -DCMAKE_EXE_LINKER_FLAGS="-static -no-pie -stdlib=libc++ --rtlib=compiler-rt -unwindlib=libunwind" \
  -DCMAKE_CXX_STANDARD_LIBRARIES="-Wl,--start-group -lc++ -lc++abi -lunwind -Wl,--end-group" -DLLVM_USE_LINKER=lld \
  -DLLVM_ENABLE_PROJECTS=lld -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_ENABLE_LIBCXX=ON \
  -DLLVM_BUILD_STATIC=ON -DLLVM_ENABLE_PIC=OFF -DLLVM_PARALLEL_LINK_JOBS=1 \
  -DLLVM_ENABLE_ZLIB=FORCE_ON -DZLIB_USE_STATIC_LIBS=ON -DZLIB_LIBRARY=/lib/libz.a \
  -DLLVM_ENABLE_ZSTD=FORCE_ON -DLLVM_USE_STATIC_ZSTD=ON \
  -DLLVM_ENABLE_LIBXML2=OFF \
  -DLLVM_ENABLE_TERMINFO=OFF -DLLVM_ENABLE_FFI=OFF -DLLVM_ENABLE_LIBEDIT=OFF \
  -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF
 set +x
 [ "$STEP" != configure ] || exit 0
 ninja -C /work/llvm-build -j 4 lld
 cp -L /work/llvm-build/bin/ld.lld /work/lld-out/ld.lld
 /work/lld-out/ld.lld --version
 sha256sum /work/lld-out/ld.lld
 sha256sum /work/lld-out/ld.lld
 wc -c < /work/lld-out/ld.lld
 '
echo "px80 build-lld: done $(date -Is), $(( $(date +%s) - started ))s"
