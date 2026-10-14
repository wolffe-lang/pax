#!/usr/bin/env bash
# px41 on hasu (KVM): pax#47. trunk's kernel and image, release; ten censuses a boot, 5 s rounds:
# file-nr read by `cat` (trunk's census), then by the shell itself. Three boots each, no added load.
L=~/lanes/px41
sed -i 's/--accel tcg/--accel ${ACCEL:-tcg}/' $L/st/censusloop.sh
export ACCEL=kvm
bash $L/st/censusloop.sh $L/t-trunk release 3 0 - $L/ev/hasu-census-cat-kvm 5 2 $L/st/censusloop10.steps
bash $L/st/censusloop.sh $L/t-trunk release 3 0 - $L/ev/hasu-census-read-kvm 5 2 $L/st/censusloop10-read.steps
echo done > $L/ev/hasu-census.done
