# tests/mpx6-nodes.d/gpt.sh — the second disk's session (px79), as
# nodes.sh is run: vda the 64 MiB GPT disk, vdb 16 MiB blank (a table and
# a file system are written to it here, through its nodes, as an
# installer writes a disk), vdc 16 MiB blank (a pattern written to every
# sector, which the host reads back: tools/blk-pattern), vdd an 8 MiB
# ext2 (read-only: what is copied into vdb2).
echo "== pattern"
/bin/nodes pattern /dev/vdc 0x7061786469736b00
echo "== table"
/bin/nodes put /dev/vdb 0 /etc/nodes/gpt-head.bin
/bin/nodes put /dev/vdb 16760320 /etc/nodes/gpt-tail.bin
/bin/nodes sys
/bin/nodes rrpart /dev/vdb
/bin/nodes sys
/bin/nodes dev
/bin/nodes stat /dev/vdb1 /dev/vdb2
/bin/nodes ioctl /dev/vdb2
echo "== mount"
/bin/nodes copy /dev/vdd /dev/vdb2
/bin/nodes mount /dev/vdb2 /mnt
/bin/nodes mounts
ls -l /mnt
/bin/nodes umount /mnt
/bin/nodes mount /dev/vdb1 /mnt
/bin/nodes mount /dev/vdb /mnt
/bin/nodes mount /dev/null /mnt
/bin/nodes mount /dev/vdz /mnt
/bin/nodes mount vdb2 /mnt
echo "== end"
