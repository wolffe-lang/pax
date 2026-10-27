# tests/mpx6-nvme.d/fstab.sh — /etc/fstab by PARTUUID= on an NVMe
# partition (px75): PAX mounted nvme0n1p2 at /mnt from its fstab line
# before this ran; the guest mounted it by node first (its init is a
# shell). What is mounted, and the tree.
echo "== mounts"
/bin/nodes mounts
echo "== ls"
ls -ln /mnt
echo "== end"
