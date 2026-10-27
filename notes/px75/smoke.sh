#!/usr/bin/env bash
# px75, hasu's rig only: one boot of kmain_console with a virtio disk and
# QEMU's NVMe controller, pelt running SESSION's lines (a file of shell
# lines) as pid 1, the serial log in $S/<name>.serial.log. The caller holds
# block B's lock (rig/run.sh).
#   smoke.sh NAME SESSION [qemu-halt disk options...]
set -uo pipefail
L=/home/mfwolffe/lanes/px75; T=${PAX_TREE:-$L/pax}; S=$L/smoke
mkdir -p "$S" "$L/tmp" "$L/cache" "$L/probe"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
cd "$T"
ulimit -c 0
name=$1 sess=$2; shift 2
export PAX_WOLF=${PAX_WOLF:-$(tools/fetch-wolf)}
tools/fetch-limine > /dev/null || exit 2
[ -x "$L/probe/pelt/pelt" ] || tools/mkpelt "$L/probe/pelt" > /dev/null || exit 2
tools/mknodes "$L/probe" > /dev/null || exit 2
tools/mknvme "$L/probe" > /dev/null || exit 2
w=$S/$name; rm -rf "$w"; mkdir -p "$w"
printf '/bin/sh /etc/s.sh\n' > "$w/run"
tools/mkinitramfs "$w/i.cpio" "/bin/sh=$L/probe/pelt/pelt:755" "/bin/nodes=$L/probe/nodes:755" "/bin/nvme=$L/probe/nvme:755" \
    /mnt/:755 /tmp/:1777 "/etc/s.sh=$sess:644" "/etc/pax-run=$w/run:644" > /dev/null || exit 2
elf=$(tools/build-kernel --src kernel/kmain_console.lu "$S/kernel" 2> "$w/build.log") || { tail -5 "$w/build.log"; exit 2; }
tools/mkimage --conf boot/limine-initramfs.conf --add "$w/i.cpio" initramfs.cpio "$elf" "$w/i.iso" > /dev/null || exit 2
tools/qemu-halt --firmware bios --serial "$S/$name.serial.log" --timeout 600 --qemu -m --qemu 1G \
    --elf "$elf" --marker 'halt|PANIC .*' "$@" "$w/i.iso" > "$S/$name.verdict" 2>&1
echo "qemu-halt $?: $(tail -n 1 "$S/$name.verdict")"
