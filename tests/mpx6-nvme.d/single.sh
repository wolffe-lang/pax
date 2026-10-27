# tests/mpx6-nvme.d/single.sh — a single queue pair granted (px75): QEMU's
# controller with `max_ioqpairs=1` (Set Features, Number of Queues,
# answers one SQ and one CQ), the sizes session of names.sh on the same
# disk: its every answer the guest's (names'). QEMU 8.2, CI's, has no
# `mqes` to make the queue itself small; hasu's QEMU 11.1 does, and the
# note's witness boots with `mqes=1` (an I/O queue of two entries).
echo "== sizes"
/bin/nvme sizes /dev/nvme0n1p1 0x7078373573697a65
echo "== end"
