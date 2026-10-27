# tests/mpx6-nvme.d/error.sh — a media error (px75): QEMU's blkdebug
# fails every read of sector 4096 of the disk (byte 2 MiB) with EIO, which
# QEMU's controller answers with a status; the reads before, at, across
# and after it.
echo "== rd"
/bin/nodes rd /dev/nvme0n1 0 4096
/bin/nodes rd /dev/nvme0n1 2097152 512
/bin/nodes rd /dev/nvme0n1 2093056 8192
/bin/nodes rd /dev/nvme0n1 2095104 4096
/bin/nodes rd /dev/nvme0n1 4194304 4096
/bin/nvme sum /dev/nvme0n1 1048576 2097152
echo "== end"
