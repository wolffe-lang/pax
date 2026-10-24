#!/usr/bin/env bash
# px68 (px67's, its paths), kasumi only (px63's run-suite.sh on this lane's CPUs, 0-3): a
# suite built in the Ubuntu baseline container, its images booted under
# TCG on the host. No package installed.
#   run-suite.sh SUITE [OUTNAME]
# PAX_TREE: the tree to build and boot from (default the lane's clone;
# the batches give a snapshot taken at their start). PAX_ROOTDISK=1:
# after the boots, tools/rootdisk-leg (CI's step) boots the same images
# again through tools/qemu-rootdisk, `/` on a disk made of each ISO's
# initramfs ($B.disk.log). px68: PAX_RECORD=1 runs the Linux side with
# --record (the suite's record written into the tree: committed by hand).
set -uo pipefail
L=$HOME/lanes/px68
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
    ' px68 "$T" "$suite" "$how" > "$B.build.log" 2>&1
brc=$?
lrc=-
if grep -q -- '--only linux' "tests/$suite"; then
    lrc=0
    rec=(); [ "${PAX_RECORD:-0}" = 1 ] && rec=(--record)
    taskset -c 0-3 "tests/$suite" --only linux --images "$B/$suite" ${rec[@]+"${rec[@]}"} > "$B.linux.log" 2>&1 || lrc=$?
fi
img=$B/$(ls "$B" | grep -m1 "^$suite\$" || echo "$suite")
# A disk image the build container began and could not finish (tools/mkdisk
# needs a container engine, which the build container has none of) is
# all zeros at its head: removed, so the suite makes it on this host.
for d in "$img"/*.img; do
    [ -f "$d" ] && cmp -s -n 4096 "$d" /dev/zero && rm -f "$d"
done
rc=0
env -u PAX_ROOTDISK taskset -c 0-3 "tests/$suite" --images "$img" --tier native --firmware bios > "$B.boot.log" 2>&1 || rc=$?
drc=-
if [ "${PAX_ROOTDISK:-0}" = 1 ]; then
    # the CI step's own tool: the same images booted again with / on a disk
    drc=0
    PAX_BUILD=$B taskset -c 0-3 tools/rootdisk-leg "$suite" --tier native --firmware bios > "$B.disk.log" 2>&1 || drc=$?
    printf '%s disk leg rc=%s: %s; pass %s fail %s\n' "$suite" "$drc" "$(grep -a 'with / on a disk:' "$B.disk.log" | tail -n 1 | sed 's/^[^:]*: //')" \
        "$(grep -c 'PASS' "$B.disk.log")" "$(grep -c -E 'FAIL|NOT HALTED' "$B.disk.log")"
fi
printf '%s build rc=%s linux rc=%s boot rc=%s %ss pass %s fail %s\n' "$suite" "$brc" "$lrc" "$rc" $(( $(date +%s) - t0 )) "$(grep -c 'PASS' "$B.boot.log")" "$(grep -c -E 'FAIL|NOT HALTED' "$B.boot.log")"
