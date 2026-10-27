# tests/mpx6-nvme.d/two.sh — two controllers (px75): nvme0 with one
# namespace (a copy of px79's A), nvme1 with namespaces 1 (another copy)
# and 3 (16 MiB blank). The guest numbers the devices on major 259 in the
# order its probes finish (a race: measured three ways in three runs), so
# the `~` sections are held to the guest's with the minors folded and the
# set of minors held apart (tests/mpx6-nvme.d/compare).
echo "== dev~"
/bin/nodes dev
echo "== sys~"
/bin/nodes sys
echo "== io"
/bin/nvme sum /dev/nvme0n1 0 1048576
/bin/nvme sum /dev/nvme1n1 0 1048576
/bin/nvme sum /dev/nvme1n2 0 16777216
/bin/nvme sum /dev/nvme1n1p2 1024 4096
echo "== end"
