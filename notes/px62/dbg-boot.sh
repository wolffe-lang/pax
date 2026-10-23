#!/usr/bin/env bash
# px62, kasumi only: build one C probe in px13-ubuntu, put it alone in an
# initramfs as the first program (with ARGS), boot it under the kernel a
# suite run built, TCG on CPUs 0-3; the serial log on stdout's file.
#   dbg-boot.sh SRC.c RUNDIR [ARGS...]
set -euo pipefail
L=$HOME/lanes/px62
src=$1 run=$2; shift 2
d=$L/dbg; rm -rf "$d"; mkdir -p "$d/root/bin" "$d/root/etc"
ulimit -c 0
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" localhost/px13-ubuntu \
    cc -static -no-pie -O1 -o "$d/root/bin/x" "$src"
echo "/bin/x $*" > "$d/root/etc/pax-run"
cd "$L/pax"
export PAX_CACHE=$L/cache PAX_BUILD=$d
tools/mkinitramfs "$d/x.cpio" "/bin/x=$d/root/bin/x:755" /t/:755 "/etc/pax-run=$d/root/etc/pax-run:644" > /dev/null
tools/mkimage --conf boot/limine-initramfs.conf --add "$d/x.cpio" initramfs.cpio "$L/build/$run/mpx3-maps/native/kmain_console.elf" "$d/x.iso" > /dev/null
taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$d/serial.log" --timeout "${DBG_TIMEOUT:-120}" \
    --elf "$L/build/$run/mpx3-maps/native/kmain_console.elf" --marker 'halt|PANIC .*' "$d/x.iso" > "$d/verdict" 2>&1 || true
tr -d '\r' < "$d/serial.log" | sed -n '/^run 1/,$p'
tail -1 "$d/verdict"
