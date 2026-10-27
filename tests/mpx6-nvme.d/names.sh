# tests/mpx6-nvme.d/names.sh — the names session (px75): run by pelt
# (/bin/sh) as PAX's pid 1 and as the Linux guest's command
# (tools/linux-nodes), the same programs, on the same disks: vda a 64 MiB
# GPT disk (px79's A: vda1 16 MiB with no file system, vda2 32 MiB of
# ext2) on virtio, and a copy of it on QEMU's NVMe controller (nvme0n1).
# Each `== <section>` line starts what tests/mpx6-nvme.d/compare holds to
# the guest's.
echo "== stat"
/bin/nodes stat /dev/nvme0n1 /dev/nvme0n1p1 /dev/nvme0n1p2 /dev/vda /dev/nvme0n1p3 /dev/nvme0n2 /dev/nvme1n1
echo "== dev"
/bin/nodes dev
echo "== sys"
/bin/nodes sys
echo "== ioctl"
/bin/nodes ioctl /dev/nvme0n1
/bin/nodes ioctl /dev/nvme0n1p2
echo "== io"
/bin/nodes io /dev/nvme0n1
/bin/nodes io /dev/nvme0n1p1
echo "== before"
/bin/nvme sum /dev/nvme0n1 0 67108864
/bin/nvme sum /dev/vda 0 67108864
echo "== sizes"
/bin/nvme sizes /dev/nvme0n1p1 0x7078373573697a65
echo "== after"
/bin/nvme sum /dev/nvme0n1 0 67108864
/bin/nvme sum /dev/nvme0n1p2 0 33554432
echo "== end"
