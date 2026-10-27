# tests/mpx6-nvme.d/root.sh — `/` on an NVMe partition (px75): the disk
# booted from QEMU's NVMe controller, `root=PARTUUID=` its partition 2.
echo "== mounts"
/bin/nodes mounts
echo "== dev"
/bin/nodes dev
echo "== write"
/bin/nvme sum /dev/nvme0n1 0 1048576
echo px75 > /etc/px75-note
/bin/nodes sync
echo "== end"
