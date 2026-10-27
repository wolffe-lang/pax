#!/usr/bin/env bash
# px75, hasu's rig only (notes/px75/rig.md): the Linux guest (hasu's
# installed Linux 7.2.4 under the rig's QEMU 8.2.2, KVM, CPUs 6-11) with
# QEMU's NVMe controllers beside a virtio disk, black box: the names and
# numbers it gives, its /proc and /sys files, its ioctls' answers, what an
# injected media error reads as (tools/linux-nodes --nvme, the probe
# user/elf/nodes.c). The caller holds block B's lock (rig/run.sh). Writes
# $G/<run>/.
#   guest.sh RUN...
set -uo pipefail
L=/home/mfwolffe/lanes/px75; T=${PAX_TREE:-$L/pax}; G=$L/guest
mkdir -p "$G" "$L/tmp" "$L/cache" "$L/probe"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
cd "$T"
ulimit -c 0
P=$L/probe/nodes
[ -x "$P" ] || tools/mknodes "$L/probe" || exit 2
[ -x "$L/probe/busybox" ] || tools/fetch-busybox "$L/probe" || exit 2
K=${PAX_LINUX_KERNEL:?}; M=${PAX_LINUX_MODULES:?}
echo "guest kernel: $K ($(file -b "$K" | sed -n 's/.*version \([^ ]*\).*/\1/p')), modules $M"
# disk A: a 64 MiB GPT disk, partition 1 16 MiB (no file system), partition 2 an ext2 of 32 MiB (px79's)
diskA() {
    local d=$1
    rm -f "$d" "$d.p2"
    truncate -s 64M "$d"
    SOURCE_DATE_EPOCH=1700000000 tools/mkdisk --home 32M "$d.p2" > /dev/null || return 1
    dd if="$d.p2" of="$d" bs=512 seek=34816 conv=notrunc status=none
    rm -f "$d.p2"
    SOURCE_DATE_EPOCH=1700000000 tools/mkgpt --label px79a "$d" 1:linux:2048:34815:one 2:linux:34816:100351:home > /dev/null
}
lnx() { tools/linux-nodes --kernel "$K" --modules "$M" --busybox "$L/probe/busybox" --accel kvm "$@"; }
SYS="nodes dev|nodes sys|cat /proc/partitions|ls -l /sys/block /sys/class/block|ls /sys/class/nvme /sys/class/nvme-subsystem"
sys_cmds() { local IFS='|'; printf '%s\n' $SYS; }
for R in "$@"; do
    rm -rf "$G/$R"; mkdir -p "$G/$R"
    W=$G/$R
    case $R in
    n1) # vda (A) and one NVMe controller with A's copy: names, numbers, the files, the ioctls
        diskA "$W/a.img"; cp "$W/a.img" "$W/n.img"
        mapfile -t s < <(sys_cmds)
        lnx --drive "$W/a.img" --nvme "$W/n.img" "$W" "$P" -- "${s[@]}" \
            "nodes stat /dev/nvme0n1 /dev/nvme0n1p1 /dev/nvme0n1p2 /dev/nvme0 /dev/vda" \
            "nodes ioctl /dev/nvme0n1" "nodes ioctl /dev/nvme0n1p2" "nodes io /dev/nvme0n1" \
            "ls /sys/block/nvme0n1 /sys/block/nvme0n1/nvme0n1p1" \
            "cat /sys/block/nvme0n1/uevent /sys/block/nvme0n1/nvme0n1p1/uevent /sys/block/nvme0n1/removable /sys/block/nvme0n1/ro" \
            "cat /sys/block/nvme0n1/queue/logical_block_size /sys/block/nvme0n1/queue/physical_block_size /sys/block/nvme0n1/queue/max_hw_sectors_kb /sys/block/nvme0n1/queue/max_sectors_kb /sys/block/nvme0n1/queue/rotational /sys/block/nvme0n1/queue/nr_requests" \
            "cat /sys/class/nvme/nvme0/model /sys/class/nvme/nvme0/serial /sys/class/nvme/nvme0/firmware_rev /sys/class/nvme/nvme0/queue_count /sys/class/nvme/nvme0/sqsize" \
            "dmesg" > "$W/run.txt" 2>&1 ;;
    n2|n2b|n2c) # no virtio disk; two NVMe controllers, each A's copy: the instance order, the minors
        diskA "$W/a.img"; cp "$W/a.img" "$W/b.img"
        mapfile -t s < <(sys_cmds)
        lnx --nvme "$W/a.img" --nvme "$W/b.img" "$W" "$P" -- "${s[@]}" \
            "cat /sys/class/nvme/nvme0/serial /sys/class/nvme/nvme1/serial /sys/class/nvme/nvme0/address /sys/class/nvme/nvme1/address" \
            "nodes ioctl /dev/nvme1n1" > "$W/run.txt" 2>&1 ;;
    n3) # one controller, namespaces 1 and 3 (A's copy and a blank 16 MiB): the names
        diskA "$W/a.img"; cp "$W/a.img" "$W/n.img"; truncate -s 16M "$W/c.img"
        mapfile -t s < <(sys_cmds)
        lnx --drive "$W/a.img" --qemu -device --qemu nvme,id=c0,serial=paxnvme0 \
            --qemu -drive --qemu "file=$W/n.img,if=none,id=ns1,format=raw" --qemu -device --qemu nvme-ns,drive=ns1,bus=c0,nsid=1 \
            --qemu -drive --qemu "file=$W/c.img,if=none,id=ns3,format=raw" --qemu -device --qemu nvme-ns,drive=ns3,bus=c0,nsid=3 \
            "$W" "$P" -- "${s[@]}" "ls /sys/class/nvme/nvme0" "cat /sys/block/nvme0n2/nsid /sys/block/nvme0n1/nsid" > "$W/run.txt" 2>&1 ;;
    n4) # a 4096-byte LBA namespace, A's copy (its GPT is for 512-byte sectors)
        diskA "$W/a.img"
        mapfile -t s < <(sys_cmds)
        lnx --nvme "$W/a.img;logical_block_size=4096,physical_block_size=4096" "$W" "$P" -- "${s[@]}" \
            "nodes ioctl /dev/nvme0n1" "nodes io /dev/nvme0n1" \
            "cat /sys/block/nvme0n1/queue/logical_block_size /sys/block/nvme0n1/queue/physical_block_size /sys/block/nvme0n1/size" > "$W/run.txt" 2>&1 ;;
    n5) # a media error: QEMU's blkdebug fails reads of sector 4096 (byte 2 MiB) with EIO
        diskA "$W/a.img"
        printf '[inject-error]\nevent = "read_aio"\nerrno = "5"\nsector = "4096"\nonce = "off"\n' > "$W/blkdebug.cfg"
        lnx --qemu -drive --qemu "file=blkdebug:$W/blkdebug.cfg:$W/a.img,if=none,id=e0,format=raw" \
            --qemu -device --qemu nvme,serial=paxnvme0,drive=e0 "$W" "$P" -- \
            "nodes rd /dev/nvme0n1 0 4096" "nodes rd /dev/nvme0n1 2097152 512" "nodes rd /dev/nvme0n1 2093056 8192" "nodes rd /dev/nvme0n1 4194304 4096" \
            "dmesg" > "$W/run.txt" 2>&1 ;;
    *) echo "no run $R"; exit 2 ;;
    esac
    echo "== $R: $(grep -c . "$W/serial.log") serial lines; $(tail -n 1 "$W/serial.log")"
    rm -rf "$W/root" "$W/initramfs.cpio"
done
