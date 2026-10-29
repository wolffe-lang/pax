#!/usr/bin/env bash
# px77a's stick-smoke-build.sh, unchanged but for the lane, the name and the conf's path (the same file).
set -euo pipefail
L=/home/mfwolffe/lanes/px77b
cd "$L/pax"
. tools/lib.sh
export SOURCE_DATE_EPOCH=$(cat "$L/out/source-date-epoch")
head=$(cat "$L/out/commit")
[ "$head" = 101e7761cd648accacf9e4fbcb1bede5443a6de7 ]
elf=$L/out/kernel/kmain_console.elf
cpio=$L/out/release.cpio
conf=$PWD/boot/limine-usb.conf
load_limine_pin
stick=$L/out/pax-stick-101e7761.img
expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
 --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
 --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
 --expect "/boot/limine/limine.conf=$conf")
python3 -I tests/usb-tools
python3 -I tests/usb-linux-fetch
tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$stick" > "$L/logs/usb-build.log"
tools/check-usb "$stick" "${expected[@]}" | tee "$L/logs/usb-check.log"
tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$L/out/repeat.img" > "$L/logs/usb-repeat.log"
cmp "$stick" "$L/out/repeat.img"
echo 'PASS second stick build byte-identical'
for fault in efi mbr; do
 broken=$L/out/usb-$fault-red.img
 cp --sparse=always "$stick" "$broken"
 python3 -I tests/usb-stick.d/corrupt.py "$broken" "$fault"
 if tools/check-usb "$broken" > "$L/logs/usb-$fault-red.log" 2>&1; then echo 'FAIL corrupt image accepted'; exit 1; fi
 case $fault in
 efi) grep -F 'required boot file missing: /EFI/BOOT/BOOTX64.EFI' "$L/logs/usb-$fault-red.log" ;;
 mbr) grep -F 'protective MBR must cover the disk' "$L/logs/usb-$fault-red.log" ;;
 esac
 rm "$broken"
done
sha256sum "$stick" | tee "$L/image-hasu-read-1.sha256"
sha256sum "$stick" | tee "$L/image-hasu-read-2.sha256"
stat -c '%s' "$stick"
rm "$L/out/repeat.img"
