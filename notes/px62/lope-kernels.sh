#!/usr/bin/env bash
# px62, kasumi only: tests/mpx5-lope's boot with one image's programs
# and another kernel (base, head, ...): RUN's built images copied, the
# ELF swapped, the ISO made again from the same initramfs, then the
# suite's boot (native, BIOS) on CPUs 0-3 against RUN's Linux sessions.
#   lope-kernels.sh RUN NAME=ELF...
set -uo pipefail
L=$HOME/lanes/px62
run=$1; shift
src=$L/build/$run/mpx5-lope
cd "$L/pax"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
for kv in "$@"; do
    name=${kv%%=*} elf=${kv#*=}
    B=$L/build/$run-$name; rm -rf "$B"; mkdir -p "$B"
    cp -a "$src" "$B/mpx5-lope"
    cp "$elf" "$B/mpx5-lope/native/kmain_console.elf"
    PAX_BUILD=$B tools/mkimage --conf boot/limine-initramfs.conf --add "$B/mpx5-lope/lope.cpio" initramfs.cpio \
        "$B/mpx5-lope/native/kmain_console.elf" "$B/mpx5-lope/native/lope.iso" > /dev/null || { echo "$name: mkimage failed"; continue; }
    rc=0
    PAX_BUILD=$B taskset -c 0-3 tests/mpx5-lope --images "$B/mpx5-lope" --tier native --firmware bios > "$B.boot.log" 2>&1 || rc=$?
    echo "$name $(sha256sum < "$elf" | cut -c1-16) rc=$rc"
    grep -a 'FAIL\|PASS L1' "$B.boot.log" | cut -c1-200
done
