# tests/mpx6-nodes.d/numbers.sh — the numbers past 15 (px79, R-px79-1), as
# nodes.sh is run: vda and vdb two copies of tests/mpx6-part's `full`
# fixture (128 partitions each).
echo "== sys"
/bin/nodes sys
echo "== stat"
/bin/nodes stat /dev/vda15 /dev/vda16 /dev/vda128 /dev/vdb15 /dev/vdb16 /dev/vdb128
echo "== rescan"
/bin/nodes del /dev/vda 20
/bin/nodes del /dev/vda 16
/bin/nodes add /dev/vda 16 2560000 1024
/bin/nodes stat /dev/vda16 /dev/vda20
/bin/nodes rrpart /dev/vda
/bin/nodes stat /dev/vda16 /dev/vda17 /dev/vda20 /dev/vda128 /dev/vdb16
/bin/nodes ioctl /dev/vda100
echo "== end"
