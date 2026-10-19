#!/bin/bash
# px52 on kasumi: suites built in px13-ubuntu (cpus 12-15) and booted on kasumi (native, BIOS, TCG, cpus 8-11,
# while a loop holds 0-3), one after the other; mpx5-jobs from an earlier build TAG when given as jobs:TAG.
#   regress.sh RUN SUITE|jobs:TAG...
L=$HOME/lanes/px52; P=$L/pax/notes/px52; R=$1; shift
export PX52_BUILD_CPUS=12-15 PX52_CPUS=8-11
for s in "$@"; do
    case $s in
        jobs:*) t=${s#jobs:}; echo "== mpx5-jobs ($t)"; bash $P/boot.sh mpx5-jobs $t --tier native --firmware bios ;;
        *) echo "== $s"; t=$R-$s
           if grep -q -- '--only build' $L/pax/tests/$s; then bash $P/build.sh $s $t --only build --tier native; else bash $P/build.sh $s $t --no-boot --tier native; fi \
             && bash $P/boot.sh $s $t --tier native --firmware bios ;;
    esac
    echo "== $s: $?"
done
