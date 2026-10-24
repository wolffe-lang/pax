#!/usr/bin/env bash
# px68, kasumi only: the crash row twice with the same kernel and probe
# (seed 67, 1,500 operations, 24 kills): journalled (the gate, the torn
# row, the session and the halt timed thrice) and px67's ext2 (the same
# kills read as px67 read them, timed thrice), CPUs 0-3 (the caller holds
# the lock). Writes $L/crash/<name>-{j,e}/crash.txt.
#   crash.sh NAME KERNEL-ELF [PROBE]   (PROBE: user/elf/mounts.c's static build)
set -uo pipefail
L=$HOME/lanes/px68; T=${PAX_TREE:-$L/pax}
name=$1; elf=$2; probe=${3:-$L/guest/probe/mounts}
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp
ulimit -c 0
cd "$T"
mkdir -p "$L/crash"
rm -rf "$L/crash/$name-j" "$L/crash/$name-e"
echo "== journalled $(date -u +%H:%M:%S)"
taskset -c 0-3 python3 tools/root-crash --kernel "$elf" --probe "$probe" --n 24 --seed 67 --ops 1500 \
    --times 3 --torn --check "$L/crash/$name-j"
jr=$?
echo "== ext2 $(date -u +%H:%M:%S)"
taskset -c 0-3 python3 tools/root-crash --kernel "$elf" --probe "$probe" --n 24 --seed 67 --ops 1500 \
    --times 3 --no-journal "$L/crash/$name-e"
er=$?
echo "== done $(date -u +%H:%M:%S): journalled exit $jr, ext2 exit $er"
rm -f "$L/crash/$name-j/churn.img" "$L/crash/$name-e/churn.img" "$L/crash"/*/*.p2
exit $(( jr != 0 ? jr : er ))
