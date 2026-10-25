#!/usr/bin/env bash
# kasumi: replace a host-built root disk's ESP with paxfat's, leaving the
# GPT/root/BIOS stage alone, then boot the same disk under both firmwares.
set -euo pipefail
L=$HOME/lanes/px69
P=$L/pax
exec 9> "$HOME/lanes/kasumi-cores-8-11.lock"; flock 9
taskset -pc 8-11 $$
ulimit -c 0
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp SOURCE_DATE_EPOCH=1700000000
W=$L/fat/boot
mkdir -p "$W"
"$P/tools/mkdisk" --gpt --no-journal --kernel "$(cat "$L/play/w/elf.path")" --root "$L/play/w/preflight.cpio" --label px69-fat-boot 128M "$W/disk.img" > "$W/mkdisk.log" 2>&1
podman run --rm -i --cpuset-cpus 8-11 -v "$L:$L:Z" -e L="$L" -e W="$W" -e SOURCE_DATE_EPOCH localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
export PATH=/opt/px69-oracle-bin:$PATH
mcopy -i "$W/disk.img@@2097152" ::/boot/limine/limine.conf "$W/limine.conf"
"$L/bin/paxfat" --offset 2M mkfs "$W/disk.img" 64M
for d in /EFI /EFI/BOOT /boot /boot/limine; do "$L/bin/paxfat" --offset 2M mkdir "$W/disk.img" "$d"; done
"$L/bin/paxfat" --offset 2M copy "$W/disk.img" "$L/cache/limine-12.9.1/BOOTX64.EFI" /EFI/BOOT/BOOTX64.EFI
"$L/bin/paxfat" --offset 2M copy "$W/disk.img" "$W/limine.conf" /boot/limine/limine.conf
"$L/bin/paxfat" --offset 2M copy "$W/disk.img" "$L/cache/limine-12.9.1/limine-bios.sys" /boot/limine/limine-bios.sys
"$L/bin/paxfat" --offset 2M copy "$W/disk.img" "$(cat "$L/play/w/elf.path")" /boot/pax
mdir -/ -i "$W/disk.img@@2097152" :: > "$W/mdir.log"
INNER
for fw in bios uefi; do
    cp --sparse=always "$W/disk.img" "$W/$fw.img"
    PAX_REQUIRE_UEFI=1 PAX_BUILD=$W "$P/tools/qemu-halt" --boot-disk --firmware "$fw" \
        --elf "$(cat "$L/play/w/elf.path")" --serial "$W/$fw.serial" --marker halt "$W/$fw.img" > "$W/$fw.boot" 2>&1
    grep -a 'disktools-preflight: end' "$W/$fw.serial"
    grep -a 'root: PARTUUID=' "$W/$fw.serial"
    cat "$W/$fw.boot"
done
