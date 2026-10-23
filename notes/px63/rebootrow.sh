#!/usr/bin/env bash
# px63, kasumi only: the reboot row by hand: one image of kmain_console
# whose script writes /home/pax/notes.txt and runs /bin/reboot on the
# first boot (QEMU's -no-reboot ends the run at the reset) and reads the
# note back on the second, the same disk image on both (the volume
# mounted at /home by /etc/fstab); e2fsck -fn and debugfs between.
#   rebootrow.sh RUN [fstab-options]
set -euo pipefail
L=$HOME/lanes/px63
run=${1:-b1}; opts=${2:-defaults}
printf '%s\n' $$ > "$L/rebootrow-$run.pid"
ulimit -c 0
B=$L/runs/$run; rm -rf "$B"; mkdir -p "$B/root/bin" "$B/tree/pax"
W=$HOME/lanes/orch-paxplay/w
for u in ls cat chown; do strip -o "$B/root/bin/$u" "$W/bore/$u"; done
strip -o "$B/root/bin/sh" "$W/pelt/pelt"
printf '/dev/vda /home ext2 %s 0 2\n' "$opts" > "$B/fstab"
printf '/bin/sh /etc/disk/reboot.sh\n' > "$B/pax-run"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
    set -euo pipefail; cd "$1/pax"; w=$(tools/fetch-wolf | tail -1); tools/fetch-limine >/dev/null
    tools/mkdiskprobe "$2/root/bin" > "$2/probe.txt"; rm -f "$2/root/bin/disk"
    elf=$(PAX_WOLF=$w tools/build-kernel --src kernel/kmain_console.lu "$2/k" 2>"$2/build.log")
    echo "$elf" > "$2/elf.path"
    args=(); for f in "$2"/root/bin/*; do args+=("/bin/${f##*/}=$f:755"); done
    tools/mkinitramfs "$2/i.cpio" "${args[@]}" /home/:755 /home/pax/:755:1000:1000 /tmp/:1777 \
        "/etc/disk/reboot.sh=$1/pax/tests/mpx6-ext2.d/reboot.sh:644" "/etc/fstab=$2/fstab:644" "/etc/pax-run=$2/pax-run:644" > "$2/i.txt"
    tools/mkimage --conf boot/limine-initramfs.conf --add "$2/i.cpio" initramfs.cpio "$elf" "$2/reboot.iso" > /dev/null
' px63 "$L" "$B"
printf '/pax 755 1000 1000\n' > "$B/attrs"
SOURCE_DATE_EPOCH=1700000000 "$L/pax/tools/mkdisk" --from "$B/tree" --attrs "$B/attrs" --label pax-home 32M "$B/home.img" > "$B/mkdisk.txt"
cd "$L/pax"
drive=(-drive "file=$B/home.img,if=none,id=d0,format=raw" -device virtio-blk-pci,drive=d0)
t0=$(date +%s.%N); rc=0
taskset -c 0-3 tools/qemu-run --firmware bios --serial "$B/boot1.log" --timeout 240 --accel tcg "$B/reboot.iso" -- -m 1G "${drive[@]}" > "$B/boot1.verdict" 2>&1 || rc=$?
t1=$(date +%s.%N)
echo "boot 1: qemu-run status $rc, $(echo "$t1 - $t0" | bc) s" > "$B/summary"
"$L/pax/tools/e2fs" "$B" e2fsck -fn home.img > "$B/fsck1.txt" 2>&1 && echo "between: e2fsck clean" >> "$B/summary" || echo "between: e2fsck rc=$?" >> "$B/summary"
"$L/pax/tools/e2fs" "$B" debugfs -R "cat /pax/notes.txt" home.img > "$B/note.txt" 2>/dev/null || true
echo "between: debugfs reads /pax/notes.txt: $(cat "$B/note.txt")" >> "$B/summary"
rc=0
taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$B/boot2.log" --timeout 240 --accel tcg --qemu -m --qemu 1G \
    --elf "$(cat "$B/elf.path")" --marker 'halt|PANIC .*' --qemu -drive --qemu "file=$B/home.img,if=none,id=d0,format=raw" \
    --qemu -device --qemu virtio-blk-pci,drive=d0 "$B/reboot.iso" > "$B/boot2.verdict" 2>&1 || rc=$?
t2=$(date +%s.%N)
echo "boot 2: qemu-halt status $rc; the row $(echo "$t2 - $t0" | bc) s" >> "$B/summary"
"$L/pax/tools/e2fs" "$B" e2fsck -fn home.img > "$B/fsck2.txt" 2>&1 && echo "after: e2fsck clean" >> "$B/summary" || echo "after: e2fsck rc=$?" >> "$B/summary"
echo done >> "$B/summary"
