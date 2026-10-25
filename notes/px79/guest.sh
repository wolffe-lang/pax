#!/usr/bin/env bash
# px79, kasumi only: the Linux guest (the installed 7.3.0-4 image under
# QEMU, TCG, CPUs 0-3) with up to three virtio disks, black box: what
# its nodes, /proc and /sys files, ioctls and raw I/O answer
# (tools/linux-nodes, the probe user/elf/nodes.c). The caller holds the
# cores' lock. Writes $G/<run>/.
#   guest.sh RUN...
set -uo pipefail
L=$HOME/lanes/px79; T=${PAX_TREE:-$L/pax}; G=$L/guest
mkdir -p "$G" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp
cd "$T"
ulimit -c 0
P=$L/probe/nodes
[ -x "$P" ] || { echo "no probe $P"; exit 2; }
K=${PAX_LINUX_KERNEL:-/usr/lib/modules/7.3.0-4-cachyos/vmlinuz}
echo "guest kernel: $K ($(file -b "$K" | sed -n 's/.*version \([^ ]*\).*/\1/p'))"
# disk A: a 64 MiB GPT disk, partition 1 16 MiB (no file system), partition 2 an ext2 of 32 MiB
diskA() {
    local d=$1
    rm -f "$d" "$d.p2"
    truncate -s 64M "$d"
    SOURCE_DATE_EPOCH=1700000000 tools/mkdisk --home 32M "$d.p2" > /dev/null || return 1
    dd if="$d.p2" of="$d" bs=512 seek=34816 conv=notrunc status=none
    rm -f "$d.p2"
    SOURCE_DATE_EPOCH=1700000000 tools/mkgpt --label px79a "$d" 1:linux:2048:34815:one 2:linux:34816:100351:home > /dev/null
}
lnx() { taskset -c 0-3 tools/linux-nodes --kernel "$K" "$@"; }
for R in "$@"; do
    rm -rf "$G/$R"; mkdir -p "$G/$R"
    W=$G/$R
    case $R in
    g1) # three disks: A (GPT, ext2 on 2), B blank 16 MiB, C blank 4 MiB; every read-only question
        diskA "$W/a.img"; truncate -s 16M "$W/b.img"; truncate -s 4M "$W/c.img"
        lnx --drive "$W/a.img" --drive "$W/b.img" --drive "$W/c.img" "$W" "$P" -- \
            "nodes stat /dev/vda /dev/vda1 /dev/vda2 /dev/vdb /dev/vdc /dev/vda3" \
            "stat -c '%t,%T %F %a %U %G %s %b %B %o %h %D' /dev/vda /dev/vda2 /dev/vdb" \
            "ls -l /dev" \
            "nodes dev" "nodes sys" \
            "nodes ioctl /dev/vda" "nodes ioctl /dev/vda2" "nodes ioctl /dev/vdb" "nodes ioctl /dev/vdc" \
            "nodes io /dev/vda" "nodes io /dev/vda1" "nodes io /dev/vdb" \
            "ls -l /sys/block /sys/class/block" "ls /sys/block/vda /sys/block/vda/vda1" \
            "cat /sys/block/vda/uevent /sys/block/vda/vda1/uevent" \
            "cat /proc/partitions" > "$W/run.txt" 2>&1 ;;
    g2) # writes and rescans: B blank, A as g1
        diskA "$W/a.img"; truncate -s 16M "$W/b.img"
        lnx --drive "$W/a.img" --drive "$W/b.img" "$W" "$P" -- \
            "nodes wio /dev/vdb" "nodes wio /dev/vda1" "nodes wio /dev/vda" \
            "nodes excl /dev/vda" "nodes excl /dev/vda1" "nodes excl /dev/vdb" \
            "nodes rrpart /dev/vda" "nodes rrpart /dev/vda1" "nodes rrpart /dev/vdb" \
            "/bin/nodes hold /dev/vda1 rrpart /dev/vda" "/bin/nodes hold /dev/vda rrpart /dev/vda" \
            "nodes mount /dev/vda2 /mnt" "nodes mounts" "cat /proc/mounts" \
            "nodes rrpart /dev/vda" "nodes excl /dev/vda" "nodes excl /dev/vda2" "nodes excl /dev/vda1" \
            "nodes wio /dev/vda1" "nodes del /dev/vda 2" "nodes del /dev/vda 1" "nodes sys" \
            "nodes add /dev/vda 1 1048576 4194304" "nodes add /dev/vda 3 1048576 4194304" "nodes add /dev/vda 5 1048576 1048576" \
            "nodes add /dev/vda 6 67108864 512" "nodes add /dev/vda 7 512 512" "nodes add /dev/vda 1 1048576 1048576" "nodes sys" "nodes dev" \
            "nodes umount /mnt" "nodes rrpart /dev/vda" "nodes sys" "nodes dev" \
            "nodes pattern /dev/vdb 0x7061786469736b00" "nodes mount /dev/vdb /mnt" > "$W/run.txt" 2>&1
        tools/blk-pattern "$W/b.img" > "$W/b-pattern.txt" 2>&1 || true ;;
    g3) # the installer's steps: a GPT written to a blank B through its node, rescanned, an ext2 put
        # into B2 through its node and mounted by node; holds against mount, delete and rescan; a raw
        # write to A while A2 is mounted
        diskA "$W/a.img"; truncate -s 16M "$W/b.img"
        rm -f "$W/gpt.img"; SOURCE_DATE_EPOCH=1700000000 tools/mkgpt --size 16M --label px79b "$W/gpt.img" 1:esp:2048:10239:esp 2:linux:10240:26623:root > /dev/null
        dd if="$W/gpt.img" of="$W/gpt-head.bin" bs=512 count=34 status=none
        dd if="$W/gpt.img" of="$W/gpt-tail.bin" bs=512 skip=32735 count=33 status=none
        SOURCE_DATE_EPOCH=1700000000 tools/mkdisk --home 8M "$W/home.img" > /dev/null
        lnx --drive "$W/a.img" --drive "$W/b.img" --file "$W/gpt-head.bin=/gpt-head.bin" --file "$W/gpt-tail.bin=/gpt-tail.bin" \
            --file "$W/home.img=/home.img" "$W" "$P" -- \
            "/bin/nodes holdx /dev/vda2 mount /dev/vda2 /mnt" "/bin/nodes holdx /dev/vda mount /dev/vda2 /mnt" \
            "/bin/nodes holdx /dev/vda1 holdx /dev/vda1 stat /dev/vda1" "/bin/nodes holdx /dev/vda holdx /dev/vda1 stat /dev/vda1" \
            "/bin/nodes hold /dev/vda1 del /dev/vda 1" "/bin/nodes hold /dev/vda1 rrpart /dev/vda" \
            "nodes mount /dev/vda2 /mnt" "nodes wio /dev/vda" "nodes put /dev/vda 0 /gpt-head.bin" "nodes rrpart /dev/vda" \
            "nodes umount /mnt" "nodes rrpart /dev/vda" "nodes sys" \
            "nodes put /dev/vdb 0 /gpt-head.bin" "nodes put /dev/vdb 16760320 /gpt-tail.bin" "nodes sys" "nodes rrpart /dev/vdb" \
            "nodes sys" "nodes dev" "nodes stat /dev/vdb1 /dev/vdb2" "nodes ioctl /dev/vdb2" \
            "nodes put /dev/vdb2 0 /home.img" "nodes mount /dev/vdb2 /mnt" "nodes mounts" "ls -la /mnt" "nodes umount /mnt" \
            "nodes mount /dev/vdb1 /mnt" "nodes mount /dev/vdb /mnt" "nodes mount /dev/null /mnt" "nodes mount /dev/vdz /mnt" "nodes mount vdb2 /mnt" > "$W/run.txt" 2>&1
        { cmp "$W/gpt-head.bin" <(dd if="$W/b.img" bs=512 count=34 status=none) && echo "head: the table's bytes"
          cmp "$W/gpt-tail.bin" <(dd if="$W/b.img" bs=512 skip=32735 count=33 status=none) && echo "tail: the table's bytes"
          dd if="$W/b.img" of="$W/b2.img" bs=512 skip=10240 count=16384 status=none
          tools/e2fs "$W" e2fsck -fn b2.img; echo "e2fsck -fn exit $?"; rm -f "$W/b2.img"
          dd if="$W/a.img" of="$W/a2.img" bs=512 skip=34816 count=65536 status=none
          tools/e2fs "$W" e2fsck -fn a2.img; echo "e2fsck -fn A2 exit $?"; rm -f "$W/a2.img"; } > "$W/host.txt" 2>&1 ;;
    g4) # numbers past 15 on two disks, a rescan's minors; a read-only disk with QEMU's own geometry
        tests/mpx6-part.d/fixtures "$W/fx" full > /dev/null
        cp "$W/fx/full.img" "$W/a.img"; cp "$W/fx/full.img" "$W/b.img"; truncate -s 4M "$W/c.img"
        lnx --drive "$W/a.img" --drive "$W/b.img" --drive "$W/c.img,ro;cyls=100,heads=4,secs=17" "$W" "$P" -- \
            "nodes sys" "nodes stat /dev/vda15 /dev/vda16 /dev/vda128 /dev/vdb15 /dev/vdb16 /dev/vdb128 /dev/vdc" \
            "nodes del /dev/vda 20" "nodes del /dev/vda 16" "nodes add /dev/vda 16 2560000 1024" "nodes stat /dev/vda16" \
            "nodes rrpart /dev/vda" "nodes stat /dev/vda16 /dev/vda17 /dev/vda20 /dev/vda128 /dev/vdb16" \
            "nodes ioctl /dev/vdc" "nodes io /dev/vdc" "nodes wio /dev/vdc" "nodes sys" "nodes rrpart /dev/vdc" "nodes ioctl /dev/vda100" > "$W/run.txt" 2>&1 ;;
    *) echo "unknown run $R" ;;
    esac
    sed -n '/linux-nodes: uname/,$p' "$W/serial.log" | tr -d '\r' > "$W/guest.txt"
    echo "== $R: $(grep -c 'run [0-9]* status' "$W/guest.txt") runs; $(tail -n 1 "$W/serial.log")"
done
