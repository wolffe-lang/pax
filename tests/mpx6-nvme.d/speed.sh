# tests/mpx6-nvme.d/speed.sh — 1 GiB through /dev/nvme0n1 (px75): written
# in 1 MiB writes with tools/blk-pattern's pattern, fsync'd, read back and
# checked; the times on their own lines (`== time`, never compared).
echo "== speed"
/bin/nvme speed /dev/nvme0n1 1024
echo "== end"
