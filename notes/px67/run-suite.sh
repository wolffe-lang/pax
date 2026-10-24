#!/usr/bin/env bash
# px67, kasumi only (px63's run-suite.sh on this lane's CPUs, 0-3): a
# suite built in the Ubuntu baseline container, its images booted under
# TCG on the host. No package installed.
#   run-suite.sh SUITE [OUTNAME]
# PAX_TREE: the tree to build and boot from (default the lane's clone;
# the batches give a snapshot taken at their start). PAX_ROOTDISK=1:
# the boots go through tools/qemu-rootdisk (PAX_QEMU), `/` on a disk
# made of each ISO's initramfs, the cache under the run's directory.
set -uo pipefail
L=$HOME/lanes/px67
T=${PAX_TREE:-$L/pax}
suite=$1; run=${2:-$1}
ulimit -c 0
B=$L/build/$run
rm -rf "$B"; mkdir -p "$B" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu TMPDIR=$L/tmp
cd "$T"
t0=$(date +%s)
# px62's order: the build in the container (`--only build` where the
# suite has it), the Linux side on this host (`--only linux`: its
# throwaway containers and guests need the host's engine and kernel),
# then the boots. A suite with neither runs `--no-boot` in the container.
how=--no-boot
grep -q -- '--only build' "tests/$suite" && how="--only build"
if grep -q fetch-busybox "tests/$suite"; then tools/fetch-busybox "$L/bin" > /dev/null; fi
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e CARGO_INCREMENTAL=0 -e PAX_LOPE_REPO=${PAX_LOPE_REPO:-} localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/"$2" $3 --tier native
    ' px67 "$T" "$suite" "$how" > "$B.build.log" 2>&1
brc=$?
lrc=-
if grep -q -- '--only linux' "tests/$suite"; then
    lrc=0
    taskset -c 0-3 "tests/$suite" --only linux --images "$B/$suite" > "$B.linux.log" 2>&1 || lrc=$?
fi
img=$B/$(ls "$B" | grep -m1 "^$suite\$" || echo "$suite")
# A disk image the build container began and could not finish (tools/mkdisk
# needs a container engine, which the build container has none of) is
# all zeros at its head: removed, so the suite makes it on this host.
for d in "$img"/*.img; do
    [ -f "$d" ] && cmp -s -n 4096 "$d" /dev/zero && rm -f "$d"
done
rc=0
if [ "${PAX_ROOTDISK:-0}" = 1 ]; then
    export PAX_QEMU=$T/tools/qemu-rootdisk PAX_ROOTDISK_CACHE=$B/rootdisk
    find "$img" -name '*.iso' -print0 | xargs -0 -r "$T/tools/qemu-rootdisk" --prepare > "$B.prepare.log" 2>&1
fi
taskset -c 0-3 "tests/$suite" --images "$img" --tier native --firmware bios > "$B.boot.log" 2>&1 || rc=$?
if [ "${PAX_ROOTDISK:-0}" = 1 ]; then
    q=$(find "$B" -name '*.qemu.log' -print0 | xargs -0 cat 2>/dev/null)
    printf '%s: %s boots through qemu-rootdisk with / on the disk, %s left as they were\n' "$run" \
        "$(printf '%s\n' "$q" | grep -c 'as a disk with / on partition 2')" "$(printf '%s\n' "$q" | grep -c 'left as it is')"
fi
printf '%s build rc=%s linux rc=%s boot rc=%s %ss pass %s fail %s\n' "$suite" "$brc" "$lrc" "$rc" $(( $(date +%s) - t0 )) "$(grep -c 'PASS' "$B.boot.log")" "$(grep -c -E 'FAIL|NOT HALTED' "$B.boot.log")"
