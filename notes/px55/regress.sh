#!/bin/bash
# px55 on kasumi: suites built in px13-ubuntu and booted on kasumi (native, BIOS, TCG), one after the other, each
# build and boot on PX55_BUILD_CPUS / PX55_CPUS (four cpus: process tests as on a 4-vcpu runner).
#   regress.sh RUN SUITE...
L=$HOME/lanes/px55; P=$L/bin; R=$1; shift
for s in "$@"; do
    echo "== $s"; t=$R-$s
    if grep -q -- '--only build' $L/pax/tests/$s; then bash $P/build.sh $s $t --only build --tier native; else bash $P/build.sh $s $t --no-boot --tier native; fi \
      && bash $P/boot.sh $s $t --tier native --firmware bios
    echo "== $s: $?"
done
