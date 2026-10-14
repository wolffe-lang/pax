#!/bin/bash
# px41 on kasumi: a tree of SHA in ~/lanes/px41/t-TAG with mpx4-lobo's and mpx3-speaker's images built
# in px13-ubuntu (a baseline glibc), the container held to CPUs ${BUILD_CPUS:-0-7}. usage: build.sh TAG SHA [suites]   done-file ev/TAG/build.done
set -u
L=~/lanes/px41; tag=${1:?}; sha=${2:?}; suites=${3:-"mpx4-lobo mpx3-speaker"}
ev=$L/ev/$tag; tree=$L/t-$tag
mkdir -p $L/ev $L/tmp $L/cache
mkdir "$ev" "$tree" || { echo "TAG $tag exists"; exit 2; }
cd $L/pax && git fetch -q origin && git archive "$sha" | tar -x -C "$tree" || { echo "no tree" > $ev/build.done; exit 2; }
echo "$sha" > $ev/sha
podman run --rm --privileged --cpuset-cpus ${BUILD_CPUS:-0-7} -v $L:/w -e S="$suites" -e T="$tag" -w /w/t-$tag localhost/px13-ubuntu bash -c '
  set -u; export PAX_CACHE=/w/cache PAX_REQUIRE_UEFI=1 WOLF_PAIRING_REQUIRE_SIBLING=1 TMPDIR=/w/tmp CARGO_INCREMENTAL=0
  W=$(tools/fetch-wolf) || exit 2; export PAX_WOLF=$W; $W --version
  for s in $S; do tests/$s --no-boot > /w/ev/$T/$s.build.out 2>&1; echo "$s build rc $?"; done' > $ev/container-build.out 2>&1
grep -a "build rc" $ev/container-build.out > $ev/build.txt
{ qemu-system-x86_64 --version | head -1; uname -sr; } > $ev/versions.txt 2>&1
echo done > $ev/build.done
