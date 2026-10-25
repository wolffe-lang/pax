# tests/mpx6-nodes.d/nodes.sh — the block nodes' session (px79): run by
# pelt (/bin/sh) as PAX's pid 1 and as the Linux guest's command
# (tools/linux-nodes), the same programs, on the same three disks: vda a
# 64 MiB GPT disk (vda1 16 MiB with no file system, vda2 32 MiB of
# ext2), vdb 16 MiB blank, vdc 4 MiB blank, read-only, its device given
# QEMU's geometry 100/4/17. Each `== <section>` line starts what
# tests/mpx6-nodes.d/compare holds to the guest's.
echo "== stat"
/bin/nodes stat /dev/vda /dev/vda1 /dev/vda2 /dev/vdb /dev/vdc /dev/vda3 /dev/vdd /dev/vda0
echo "== ls"
ls -l /dev/vda /dev/vda1 /dev/vda2 /dev/vdb /dev/vdc
echo "== dev"
/bin/nodes dev
echo "== sys"
/bin/nodes sys
echo "== ioctl"
/bin/nodes ioctl /dev/vda
/bin/nodes ioctl /dev/vda2
/bin/nodes ioctl /dev/vdb
/bin/nodes ioctl /dev/vdc
echo "== io"
/bin/nodes io /dev/vda
/bin/nodes io /dev/vda1
/bin/nodes io /dev/vdc
echo "== wio"
/bin/nodes wio /dev/vdb
/bin/nodes wio /dev/vda1
/bin/nodes wio /dev/vdc
echo "== holds"
/bin/nodes excl /dev/vda
/bin/nodes excl /dev/vda1
/bin/nodes rrpart /dev/vda
/bin/nodes rrpart /dev/vda1
/bin/nodes rrpart /dev/vdb
/bin/nodes hold /dev/vda1 rrpart /dev/vda
/bin/nodes hold /dev/vda rrpart /dev/vda
/bin/nodes hold /dev/vda1 del /dev/vda 1
/bin/nodes holdx /dev/vda1 holdx /dev/vda1 stat /dev/vda1
/bin/nodes holdx /dev/vda holdx /dev/vda1 stat /dev/vda1
/bin/nodes holdx /dev/vda2 mount /dev/vda2 /mnt
/bin/nodes holdx /dev/vda mount /dev/vda2 /mnt
echo "== mounted"
/bin/nodes mount /dev/vda2 /mnt
/bin/nodes mounts
/bin/nodes rrpart /dev/vda
/bin/nodes excl /dev/vda
/bin/nodes excl /dev/vda2
/bin/nodes excl /dev/vda1
/bin/nodes wio /dev/vda
/bin/nodes del /dev/vda 2
/bin/nodes umount /mnt
echo "== blkpg"
/bin/nodes del /dev/vda 1
/bin/nodes del /dev/vda 9
/bin/nodes sys
/bin/nodes add /dev/vda 1 1048576 4194304
/bin/nodes add /dev/vda 3 1048576 4194304
/bin/nodes add /dev/vda 5 1048576 1048576
/bin/nodes add /dev/vda 6 67108864 512
/bin/nodes add /dev/vda 7 512 512
/bin/nodes add /dev/vda 3 52428800 1048576
/bin/nodes add /dev/vda 1 1048576 1048576
/bin/nodes add /dev/vda1 8 512 512
/bin/nodes sys
/bin/nodes dev
/bin/nodes rrpart /dev/vda
/bin/nodes sys
/bin/nodes dev
echo "== end"
