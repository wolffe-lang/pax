#!/bin/bash
# px35 on kasumi: a tree of SHA in ~/lanes/px35/t-TAG with the network suites' images built
# (mpx4-net on the host; mpx4-tcp and mpx4-unix in px13-ubuntu; mpx4-unix's Linux side from the host).
# usage: build.sh TAG SHA [suites]   done-file ev/TAG/build.done
set -u
L=~/lanes/px35; tag=${1:?}; sha=${2:?}; suites=${3:-"mpx4-net mpx4-tcp mpx4-unix"}
ev=$L/ev/$tag; tree=$L/t-$tag
mkdir -p $L/ev $L/tmp $L/cache
mkdir "$ev" "$tree" || { echo "TAG $tag exists"; exit 2; }
cd $L/pax && git fetch -q origin && git archive "$sha" | tar -x -C "$tree" || { echo "no tree" > $ev/build.done; exit 2; }
echo "$sha" > $ev/sha
export PAX_CACHE=$L/cache PAX_REQUIRE_UEFI=1 WOLF_PAIRING_REQUIRE_SIBLING=1 TMPDIR=$L/tmp
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
cd "$tree"
export PAX_WOLF=$(tools/fetch-wolf 2>$ev/fetch-wolf.err) || { echo "fetch-wolf failed" > $ev/build.done; exit 2; }
{ "$PAX_WOLF" --version; qemu-system-x86_64 --version | head -1; uname -sr; } > $ev/versions.txt 2>&1
want() { case " $suites " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
if want mpx4-net; then tests/mpx4-net --no-boot > $ev/mpx4-net.build.out 2>&1; echo "mpx4-net build rc=$?" >> $ev/build.txt; fi
podman run --rm --privileged -v "$tree":/pax -v $L/cache:/cache -v $L/st/lobo:/lobo:ro -e PAX_CACHE=/cache -e PAX_REQUIRE_UEFI=1 -e TMPDIR=/pax/build/tmp -e S="$suites" -w /pax px13-ubuntu bash -c '
  set -u; mkdir -p build/tmp; W=$(tools/fetch-wolf) || exit 2; export PAX_WOLF=$W
  want() { case " $S " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
  want mpx4-tcp && { tests/mpx4-tcp --no-boot; echo "mpx4-tcp build rc $?"; }
  want mpx4-unix && { tests/mpx4-unix --only build --lobo /lobo; echo "mpx4-unix build rc $?"; }
  true' > $ev/container-build.out 2>&1
grep -a "build rc" $ev/container-build.out >> $ev/build.txt
if want mpx4-unix; then tests/mpx4-unix --only linux --images build/mpx4-unix > $ev/mpx4-unix-linux.out 2>&1; echo "mpx4-unix linux rc=$?" >> $ev/build.txt; fi
echo done > $ev/build.done
