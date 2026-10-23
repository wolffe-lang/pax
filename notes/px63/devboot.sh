#!/usr/bin/env bash
# px63, kasumi only: a development boot of kmain_console with a disk.
# The kernel and the image are built in px13-ubuntu on CPUs 0-3; pelt
# and boreutils are copies of the orchestrator's playground build
# (~/lanes/orch-paxplay/w, read only), the suites build their own.
#   devboot.sh RUN SCRIPT [IMAGE-SOURCE-DIR] [fstab-options]
# SCRIPT runs as /bin/sh /etc/disk.sh (pid 1); the disk is mounted at
# /mnt; afterwards e2fsck -fn and a debugfs listing of the image.
# IMAGE=FILE boots a copy of FILE instead of a new image.
set -euo pipefail
L=$HOME/lanes/px63
run=$1; script=$2; from=${3:-}; opts=${4:-defaults}
printf '%s\n' $$ > "$L/devboot-$run.pid"
ulimit -c 0
B=$L/runs/$run; rm -rf "$B"; mkdir -p "$B/root/bin" "$B/root/etc"
W=$HOME/lanes/orch-paxplay/w
for u in ls cat stat mkdir rm rmdir mv cp ln touch chmod chown readlink wc head tail echo printf sort; do strip -o "$B/root/bin/$u" "$W/bore/$u"; done
strip -o "$B/root/bin/sh" "$W/pelt/pelt"
cp "$script" "$B/root/etc/disk.sh"
printf '/dev/vda /mnt ext2 %s 0 0\n' "$opts" > "$B/root/etc/fstab"
printf '/bin/sh /etc/disk.sh\n' > "$B/root/etc/pax-run"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
    set -euo pipefail; cd "$1/pax"; w=$(tools/fetch-wolf | tail -1); tools/fetch-limine >/dev/null
    tools/mkdiskprobe "$2/root/bin" > "$2/probe.txt"
    elf=$(PAX_WOLF=$w tools/build-kernel --src kernel/kmain_console.lu "$2/k" 2>"$2/build.log")
    echo "$elf" > "$2/elf.path"
    args=(); for f in "$2"/root/bin/*; do args+=("/bin/${f##*/}=$f:755"); done
    tools/mkinitramfs "$2/i.cpio" "${args[@]}" /mnt/:755 /tmp/:1777 "/etc/disk.sh=$2/root/etc/disk.sh:644" "/etc/fstab=$2/root/etc/fstab:644" "/etc/pax-run=$2/root/etc/pax-run:644" > "$2/i.txt"
    tools/mkimage --conf boot/limine-initramfs.conf --add "$2/i.cpio" initramfs.cpio "$elf" "$2/dev.iso" > /dev/null
' px63 "$L" "$B"
img=$B/disk.img
if [ -n "${IMAGE:-}" ]; then
    cp "$IMAGE" "$img"
elif [ -n "$from" ]; then
    SOURCE_DATE_EPOCH=1700000000 "$L/pax/tools/mkdisk" --from "$from" ${ATTRS:+--attrs "$ATTRS"} "${DISKSIZE:-64M}" "$img" > "$B/mkdisk.txt"
else
    SOURCE_DATE_EPOCH=1700000000 "$L/pax/tools/mkdisk" "${DISKSIZE:-64M}" "$img" > "$B/mkdisk.txt"
fi
cp "$img" "$B/disk.before.img"
cd "$L/pax"
t0=$(date +%s.%N); rc=0
taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$B/serial.log" --timeout "${TIMEOUT:-240}" --accel tcg --qemu -m --qemu 1G \
    --elf "$(cat "$B/elf.path")" --marker 'halt|PANIC .*' \
    --qemu -drive --qemu "file=$img,if=none,id=d0,format=raw" --qemu -device --qemu virtio-blk-pci,drive=d0 \
    "$B/dev.iso" > "$B/verdict" 2>&1 || rc=$?
t1=$(date +%s.%N)
echo "boot rc=$rc wall=$(echo "$t1 - $t0" | bc)" > "$B/summary"
cat "$B/verdict" >> "$B/summary"
"$L/pax/tools/e2fs" "$B" e2fsck -fn disk.img > "$B/fsck.txt" 2>&1 && echo "e2fsck clean" >> "$B/summary" || echo "e2fsck rc=$?" >> "$B/summary"
"$L/pax/tools/e2fs" "$B" debugfs -R "ls -l /" disk.img > "$B/ls.txt" 2>&1 || true
echo done >> "$B/summary"
