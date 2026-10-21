#!/bin/bash
# px57 on kasumi: suites built in px13-ubuntu and booted on kasumi (native, BIOS, TCG), one after the other, each
# build on PX57_BUILD_CPUS and boot on PX57_CPUS (four cpus: process tests as on a 4-vcpu runner).
#   regress.sh RUN SUITE...      (the tree: PX57_TREE, default ~/lanes/px57/pax)
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}; P=$X/notes/px57; R=$1; shift
for s in "$@"; do
    echo "== $s"; t=$R-$s
    if grep -q -- '--only build' $X/tests/$s; then bash $P/build.sh $s $t --only build --tier native; else bash $P/build.sh $s $t --no-boot --tier native; fi \
      && bash $P/boot.sh $s $t --tier native --firmware bios
    echo "== $s: $?"
done
