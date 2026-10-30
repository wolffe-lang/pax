#!/usr/bin/env bash
# px78b: the maintainer's allow-list line on a copy of the built stick, by the stick's own paxfat (as the
# runbook's step 2 adds it from another OS); the copy held to check-usb with the five boot files and the list
# as boot/install-targets plus that one line; then the staged name. Block A held.
set -euo pipefail
L=/home/mfwolffe/lanes/px78b
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -n 9; do python3 -I -c 'import time; time.sleep(30)'; done
printf '%s block A acquired (line)\n' "$(date -u +%FT%TZ)"
cd $L/stick
. tools/lib.sh
load_limine_pin
plain=$L/sout/pax-install-197330ad.img
k=$L/sout/pax-install-kasumi-197330ad.img
rm -f "$k" "$k.tmp"
cp --sparse=always "$plain" "$k.tmp"
esp=$(python3 -I -c '
import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$k.tmp")
echo "ESP at byte $esp"
printf 'model=Samsung SSD 860 serial=<kasumi-serial>\n' > $L/allow-line
$L/sout/disktools/paxfat --offset "$esp" append "$k.tmp" $L/allow-line /pax/install-targets
$L/sout/disktools/paxfat --offset "$esp" cat "$k.tmp" /pax/install-targets > $L/install-targets.on-stick
cat boot/install-targets $L/allow-line > $L/install-targets.expected
cmp $L/install-targets.on-stick $L/install-targets.expected
n=$(grep -cvE '^[[:space:]]*(#|$)' $L/install-targets.on-stick || true)
[ "$n" = 1 ] && grep -qxF 'model=Samsung SSD 860 serial=<kasumi-serial>' $L/install-targets.on-stick
echo "PASS /pax/install-targets on the copy: boot/install-targets plus the one line ($n entry)"
tools/check-usb "$k.tmp" --expect "/boot/pax=$L/sout/kernel/kmain_console.elf" --expect "/boot/initramfs.cpio=$L/sout/release.cpio" \
 --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI" --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" \
 --expect "/boot/limine/limine.conf=$PWD/boot/limine-usb.conf" --expect "/pax/install-targets=$L/install-targets.expected" | tee $L/slogs/kasumi-usb-check.log
mv "$k.tmp" "$k"
chmod 444 "$k"
for n in 1 2; do sha256sum "$k" | tee $L/kasumi-hasu-build-read-$n.sha256; done
stat -c '%s' "$k"
flock -u 9; exec 9>&-
printf '%s block A RELEASED (line)\n' "$(date -u +%FT%TZ)"
