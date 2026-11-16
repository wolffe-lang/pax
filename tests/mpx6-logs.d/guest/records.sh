#!/bin/pelt
# tests/mpx6-logs.d/guest/records.sh TAG FIRST LAST — records `TAG N` for N from FIRST to LAST
# written to /dev/kmsg at info (<6>), one a write, as root (px133's G2 and G8).
tag=$1 i=$2 last=$3
while [ "$i" -le "$last" ]; do
    echo "<6>$tag $i" > /dev/kmsg
    i=$((i + 1))
done
echo "records: $tag $2 to $last written"
