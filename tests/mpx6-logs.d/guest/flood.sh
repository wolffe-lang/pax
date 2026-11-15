#!/bin/pelt
# tests/mpx6-logs.d/guest/flood.sh N — N records of about 110 bytes each written to /dev/kmsg at
# info, `px133-flood K` and padding, as root: past the ring's 128 KiB when N is 2000 (px133's G3).
n=$1 i=1
pad=abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz
while [ "$i" -le "$n" ]; do
    echo "<6>px133-flood $i $pad" > /dev/kmsg
    i=$((i + 1))
done
echo "flood: $n written"
