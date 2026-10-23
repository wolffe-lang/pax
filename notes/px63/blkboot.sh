#!/usr/bin/env bash
# px63, kasumi only: build kmain_blk, wrap it, and boot it with a raw
# image as a virtio disk under TCG on CPUs 0-3.
#   blkboot.sh RUN SIZE [ro]
set -euo pipefail
L=$HOME/lanes/px63
run=${1:-blk1}; size=${2:-16M}; ro=${3:-}
ulimit -c 0
B=$L/runs/$run; mkdir -p "$B"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1/pax"; w=$(tools/fetch-wolf | tail -1); tools/fetch-limine >/dev/null
        elf=$(PAX_WOLF=$w tools/build-kernel --src kernel/kmain_blk.lu "$2/k" 2>"$2/build.log")
        tools/mkimage "$elf" "$2/blk.iso" >/dev/null
        echo "$elf" > "$2/elf.path"
    ' px63 "$L" "$B"
img=$B/disk.img
[ -n "$ro" ] || { rm -f "$img"; truncate -s "$size" "$img"; }
roopt=; [ -n "$ro" ] && roopt=,readonly=on
cd "$L/pax"
t0=$(date +%s.%N)
rc=0
taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$B/serial.log" --timeout 300 --accel tcg \
    --elf "$(cat "$B/elf.path")" --marker 'halt|PANIC .*' \
    --qemu -drive --qemu "file=$img,if=none,id=d0,format=raw$roopt" --qemu -device --qemu virtio-blk-pci,drive=d0 \
    "$B/blk.iso" > "$B/verdict" 2>&1 || rc=$?
t1=$(date +%s.%N)
echo "rc=$rc wall=$(echo "$t1 - $t0" | bc)"
cat "$B/verdict"; tr -d '\r' < "$B/serial.log"
