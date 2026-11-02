#!/usr/bin/env bash
# px88 chain r3 (behind both of the block's locks, launch.sh): the head's
# suite (every session, native BIOS and release UEFI), then I-peak's red
# (the row's commit, before getrusage) and its green (the head).
#   r3.sh BLOCK HEAD ROW
set -uo pipefail
B=$1 HEAD=$2 ROW=$3
S=/home/mfwolffe/lanes/px88/scripts
bash "$S/suite.sh" "$B" "r3-green-${HEAD:0:8}" "$HEAD" both bios:native:all uefi:release:all
bash "$S/inst.sh" "$B" "r3-peak-red-${ROW:0:8}" "$ROW"
bash "$S/inst.sh" "$B" "r3-peak-green-${HEAD:0:8}" "$HEAD"
