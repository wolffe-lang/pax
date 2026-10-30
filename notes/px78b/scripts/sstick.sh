#!/usr/bin/env bash
# px78b: px77c's stick-build.sh (px77b's) at the stick head, then the maintainer's allow-list line on a copy.
set -euo pipefail
L=/home/mfwolffe/lanes/px78b
cd "$L/stick"
. tools/lib.sh
export SOURCE_DATE_EPOCH=$(cat "$L/sout/source-date-epoch")
head=$(cat "$L/sout/commit")
[ "$head" = 197330ad4042dd349ad698a5e60f3c66f65c9c2c ]
elf=$L/sout/kernel/kmain_console.elf
cpio=$L/sout/release.cpio
conf=$PWD/boot/limine-usb.conf
allow=$PWD/boot/install-targets
load_limine_pin
stick=$L/sout/pax-install-197330ad.img
expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
 --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
 --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
 --expect "/boot/limine/limine.conf=$conf"
 --expect "/pax/install-targets=$allow")
python3 -I tests/usb-tools
python3 -I tests/usb-linux-fetch
tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$stick" > "$L/slogs/usb-build.log"
tools/check-usb "$stick" "${expected[@]}" | tee "$L/slogs/usb-check.log"
entries=$(grep -cvE '^[[:space:]]*(#|$)' "$allow" || true)
[ "$entries" = 0 ] || { echo "FAIL boot/install-targets names $entries line(s)"; exit 1; }
echo "PASS the allow-list on the image is boot/install-targets ($(wc -l < "$allow") lines, $entries entries)"
tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$L/sout/repeat.img" > "$L/slogs/usb-repeat.log"
cmp "$stick" "$L/sout/repeat.img"
echo 'PASS second stick build byte-identical'
rm "$L/sout/repeat.img"
for fault in efi mbr; do
 broken=$L/sout/usb-$fault-red.img
 cp --sparse=always "$stick" "$broken"
 python3 -I tests/usb-stick.d/corrupt.py "$broken" "$fault"
 if tools/check-usb "$broken" > "$L/slogs/usb-$fault-red.log" 2>&1; then echo 'FAIL corrupt image accepted'; exit 1; fi
 case $fault in
 efi) grep -F 'required boot file missing: /EFI/BOOT/BOOTX64.EFI' "$L/slogs/usb-$fault-red.log" ;;
 mbr) grep -F 'protective MBR must cover the disk' "$L/slogs/usb-$fault-red.log" ;;
 esac
 rm "$broken"
done
sha256sum "$stick" | tee "$L/stick-plain-read-1.sha256"
sha256sum "$stick" | tee "$L/stick-plain-read-2.sha256"
