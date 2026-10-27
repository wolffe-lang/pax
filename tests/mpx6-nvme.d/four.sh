# tests/mpx6-nvme.d/four.sh — a namespace of 4096-byte logical blocks
# (px75): a copy of px79's A behind `logical_block_size=4096`: its GPT,
# made for 512-byte sectors, is no table there (the guest finds none
# either); the size, the ioctls, raw reads and writes at odd offsets (the
# read-modify-write in the namespace's own blocks), every byte put back.
echo "== sys"
/bin/nodes sys
echo "== ioctl"
/bin/nodes ioctl /dev/nvme0n1
echo "== io"
/bin/nodes io /dev/nvme0n1
echo "== wio"
/bin/nodes wio /dev/nvme0n1
echo "== sizes"
/bin/nvme sizes /dev/nvme0n1 0x7078373573697a65
echo "== after"
/bin/nvme sum /dev/nvme0n1 0 67108864
echo "== end"
