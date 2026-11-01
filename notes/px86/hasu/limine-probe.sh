#!/usr/bin/env bash
# px86: Limine 12.9.1's bios-install observed as a black box on PAX's table over a used disk's first sectors.
# For each case: an old file system at byte 1048576 (where the 860's partition 1 began), then PAX's own table
# (sgdisk here: p3 bios 2048-4095, p1 esp 4096-135167, p2 linux 135168-), then `limine bios-install IMG 3`.
# Records the exit status, stdout and stderr apart, and whether the image changed.
set -u
L=/home/mfwolffe/lanes/px86
LIM=$L/cache/limine-12.9.1/limine
W=$L/probe/limine
rm -rf "$W"; mkdir -p "$W"; cd "$W"
mkdir -p tree/EFI/BOOT; echo old > tree/EFI/BOOT/BOOTX64.EFI
"$LIM" --version 2>&1 | head -1
pax_table() {
  sgdisk -Z "$1" >/dev/null 2>&1
  sgdisk -a 1 -n 3:2048:4095 -t 3:ef02 -n 1:4096:135167 -t 1:ef00 -n 2:135168:0 -t 2:8300 "$1" >/dev/null
}
for c in blank fat32 fat16 ext4 ext2 swap iso; do
  img=$W/$c.img; rm -f "$img"; truncate -s 2G "$img"
  case $c in
    fat32) mkfs.vfat -F 32 -n OLD-ESP --offset 2048 "$img" 524288 >/dev/null ;;
    fat16) mkfs.vfat -F 16 -n OLD-FAT16 --offset 2048 "$img" 131072 >/dev/null ;;
    ext4) mke2fs -q -t ext4 -L old-root -E offset=1048576 -d tree "$img" 512M ;;
    ext2) mke2fs -q -t ext2 -L old-ext2 -E offset=1048576 "$img" 512M ;;
    swap) truncate -s 512M sw.img; mkswap -L old-swap sw.img >/dev/null; dd if=sw.img of="$img" bs=4096 count=1 seek=256 conv=notrunc status=none ;;
    iso) xorriso -as mkisofs -quiet -V OLD-LIVE -o old.iso tree 2>/dev/null; dd if=old.iso of="$img" conv=notrunc status=none ;;
  esac
  pax_table "$img"
  before=$(dd if="$img" bs=1M count=2 status=none | sha256sum | cut -c1-16)
  "$LIM" bios-install "$img" 3 > "$c.out" 2> "$c.err"; rc=$?
  after=$(dd if="$img" bs=1M count=2 status=none | sha256sum | cut -c1-16)
  printf '== %s: exit=%s first-2MiB %s -> %s\n' "$c" "$rc" "$before" "$after"
  printf -- '-- stdout:\n'; cat "$c.out"; printf -- '-- stderr:\n'; cat "$c.err"
  blkid -p -O 1048576 -S 1048576 "$img" 2>&1 | sed 's/^/-- blkid p3: /'
  blkid -p "$img" 2>&1 | sed 's/^/-- blkid disk: /'
  rm -f "$img"
done
