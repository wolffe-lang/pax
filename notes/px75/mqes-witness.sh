#!/usr/bin/env bash
# px75, hasu only: the smallest I/O queue, on hasu's own QEMU 11.1 (CI's
# 8.2 has no `mqes`): the single session's image (tests/mpx6-nvme's
# build, nvme-single.iso: names.sh's sizes writes and reads) booted with
# `mqes=1,max_ioqpairs=1`, an I/O queue of two entries whose phase turns
# at every second command; its sizes section held to the guest's
# (tests/mpx6-nvme.d/linux/names.session). On the host, not in the rig,
# under block B's lock: `flock …/hasu-block-B.lock taskset -c 6-11 bash
# notes/px75/mqes-witness.sh`.
set -uo pipefail
L=/home/mfwolffe/lanes/px75; T=$L/pax; B=$L/build/mpx6-nvme; W=$L/mqes
cd "$T"
rm -rf "$W"; mkdir -p "$W"
cp "$B/disks/a.img" "$W/n.img"
tools/qemu-halt --firmware bios --serial "$W/serial.log" --timeout 600 --qemu -m --qemu 1G \
    --elf "$B/native/kmain_console.elf" --marker 'halt|PANIC .*' --nvme "$W/n.img;mqes=1,max_ioqpairs=1" \
    "$B/native/nvme-single.iso" > "$W/verdict" 2>&1
echo "qemu-halt $?: $(tail -n 1 "$W/verdict")"
qemu-system-x86_64 --version | head -n 1
python3 tests/mpx6-nvme.d/session pax "$W/serial.log" > "$W/session"
tr -d '\r' < "$W/serial.log" | grep -E '^nvme0: ' | head -n 2
python3 tests/mpx6-nvme.d/compare "$W/session" tests/mpx6-nvme.d/linux/names.session sizes
