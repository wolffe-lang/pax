# tests/mpx6-nodes.d/gpt.sh — the second disk's session (px79), as
# nodes.sh is run: vda the 64 MiB GPT disk, vdb 16 MiB blank (a table and
# a file system are written to it here, through its nodes, as an
# installer writes a disk), vdc 16 MiB blank (a pattern written to every
# sector, which the host reads back: tools/blk-pattern), vdd an 8 MiB
# ext2 (read-only: what is copied into vdb2). The send section writes
# the table's files onto vdb2 by sendfile(2) and splice(2) (and asks
# copy_file_range(2)) before the mount section's copy covers them.
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
echo "== send"
/bin/nodes send /dev/vdb2 0 /etc/nodes/gpt-head.bin sendfile
/bin/nodes rd /dev/vdb2 0 17408
/bin/nodes rd /etc/nodes/gpt-head.bin 0 17408
/bin/nodes send /dev/vdb2 65536 /etc/nodes/gpt-tail.bin splice
/bin/nodes rd /dev/vdb2 65536 16896
/bin/nodes rd /etc/nodes/gpt-tail.bin 0 16896
/bin/nodes send /dev/vdb2 8387608 /etc/nodes/gpt-head.bin sendfile
/bin/nodes send /dev/vdb2 8387608 /etc/nodes/gpt-tail.bin splice
/bin/nodes send /dev/vdb2 131072 /etc/nodes/gpt-head.bin cfr
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
