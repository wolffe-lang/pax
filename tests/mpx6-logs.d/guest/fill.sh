#!/bin/pelt
# tests/mpx6-logs.d/guest/fill.sh — every capped file of /var/log past its cap, as root
# (px133's G8): kern.log to just under 1 MiB with the older four in place (so the next records
# rotate it and the oldest goes), wtmp and btmp past 1 MiB, sudo.log and burrowd.log past 1 MiB,
# pax-upgrade.log past 256 KiB. `yes` and `head -c` make the bytes; nothing else is touched.
cd /var/log || exit 1
for k in 1 2 3 4; do echo "px133-fill kern.log.$k" > kern.log.$k; done
yes 'px133-fill kern.log line of filler' | head -c 1040000 >> kern.log
head -c 1100000 /dev/zero >> wtmp
head -c 1100000 /dev/zero >> btmp
yes 'px133-fill sudo.log' | head -c 1100000 >> sudo.log
yes 'px133-fill burrowd.log' | head -c 1100000 >> burrowd.log
yes 'px133-fill pax-upgrade.log' | head -c 300000 >> pax-upgrade.log
chmod 600 btmp sudo.log burrowd.log
sync
ls -l /var/log
echo "fill: done"
