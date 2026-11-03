#!/usr/bin/env bash
# px88 chain r4 (behind both of the block's locks, launch.sh): the head's suite
# (every session, native BIOS and release UEFI), the usage probe's end on a
# kernel that cannot fork (hang.sh), I-peak green at the head. I-peak's red
# was seen red by name in r3-B (26872978: `unavailable (-38)`), so every step
# here should be 0, and the chain's status is its worst step's.
#   r4.sh BLOCK HEAD HANGSHA
set -uo pipefail
B=$1 HEAD=$2 HANG=$3
S=/home/mfwolffe/lanes/px88/scripts
echo "r4: head $HEAD, hang check $HANG"
worst=0
bash "$S/suite.sh" "$B" "r4-green-${HEAD:0:8}" "$HEAD" both bios:native:all uefi:release:all || worst=1
bash "$S/hang.sh" "$B" "r4-hang-${HANG:0:8}" "$HANG" || worst=1
bash "$S/inst.sh" "$B" "r4-peak-green-${HEAD:0:8}" "$HEAD" || worst=1
echo "r4: worst step exit=$worst"
exit "$worst"
