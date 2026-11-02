#!/usr/bin/env bash
# px88 chain r3 (behind both of the block's locks, launch.sh): the head's
# suite (every session, native BIOS and release UEFI), then I-peak's red
# (the row's commit, before getrusage) and its green (the head).
#   r3.sh BLOCK HEAD ROW
# The head may be moved while the chain waits for its block (the waiter is
# never killed): r3.head beside this script, when present, names the commit
# instead of HEAD. Either way the chain builds that commit, never a tree.
set -uo pipefail
B=$1 HEAD=$2 ROW=$3
S=/home/mfwolffe/lanes/px88/scripts
[ -s "$S/r3.head" ] && HEAD=$(tr -d ' \n' < "$S/r3.head")
echo "r3: head $HEAD (argument $2), row $ROW"
bash "$S/suite.sh" "$B" "r3-green-${HEAD:0:8}" "$HEAD" both bios:native:all uefi:release:all
bash "$S/inst.sh" "$B" "r3-peak-red-${ROW:0:8}" "$ROW"
bash "$S/inst.sh" "$B" "r3-peak-green-${HEAD:0:8}" "$HEAD"
