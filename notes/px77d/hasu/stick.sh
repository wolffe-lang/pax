#!/usr/bin/env bash
# px77d: the triage stick from a kernel ELF, the 56b9f554 live archive (px77c's build of px77b's
# recipe, copied) and boot/limine-triage.conf; px77b's stick-build checks, on the host.
#   stick.sh KERNEL.elf COMMIT OUT.img
set -euo pipefail
L=/home/mfwolffe/lanes/px77d
elf=$1 head=$2 stick=$3
cd "$L/pax"
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
. tools/lib.sh
O=${OUTDIR:-$L/base-out}
export SOURCE_DATE_EPOCH=$(cat "$O/source-date-epoch")
cpio=$O/release.cpio
conf=${CONF:-$L/pax/boot/limine-triage.conf}
load_limine_pin
expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
 --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
 --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
 --expect "/boot/limine/limine.conf=$conf")
rm -f "$stick"
tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$stick" > "$stick.usb-build.log"
tools/check-usb "$stick" "${expected[@]}" | tee "$stick.usb-check.log"
sha256sum "$stick"
stat -c '%s' "$stick"
