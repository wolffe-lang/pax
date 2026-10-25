# tests/mpx6-nodes.d/fstab.sh — /etc/fstab by node (px79): vdb a GPT disk
# with an ext2 on vdb2, the table naming it `/dev/vdb2`; held to the
# guest's mount(2) of the same node on the same disk (gpt.sh's mount
# section).
echo "== mount"
/bin/nodes mounts
ls -l /mnt
echo "== end"
