#!/usr/bin/env bash
# Run inside px81's baseline container, CPUs8-11. Source ISO copied read-only.
set -euo pipefail
L=$HOME/lanes/px81
# Container HOME differs; the lane path is explicit rather than inferred.
L=/home/mfwolffe/lanes/px81
cd "$L/pax"
W=$L/dev-iso
mkdir -p "$W"
[ "$(sha256sum "$W/base.iso" | cut -d' ' -f1)" = 893ae1b90446a05e8e4d607d56a7eca956d15f8848d7495ce433e798041a50de ]
xorriso -osirrox on -indev "$W/base.iso" -extract /initramfs.cpio "$W/base.cpio"
strip -o "$W/pelt" "$L/build/mpx5-pelt/pelt/pelt"
python3 -I notes/px81/dev-iso/repack.py "$W/base.cpio" "$W/pelt" "$W/friendly.cpio" > "$W/payload-manifest.txt"
elf=$L/build/mpx5-pelt/native/kmain_console.elf
tools/mkimage --conf boot/limine-initramfs-quiet.conf --add "$W/friendly.cpio" initramfs.cpio \
 "$elf" "$W/pax-dev-pelt-friendly.iso"
for n in 1 2; do
 sha256sum "$W/base.iso" "$W/base.cpio" "$W/pelt" "$W/friendly.cpio" "$elf" "$W/pax-dev-pelt-friendly.iso" > "$W/readback-$n.sha256"
done
cmp "$W/readback-1.sha256" "$W/readback-2.sha256"
