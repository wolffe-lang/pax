#!/bin/sh
# Same static programs and commands on PAX and the Linux guest.
echo 'AHCI BEGIN inventory'
/bin/pax-install --inventory
echo 'AHCI END inventory'
echo 'AHCI BEGIN identity'
cat /sys/block/sda/device/model
cat /sys/block/sda/device/serial
cat /sys/block/sdb/device/model
cat /sys/block/sdb/device/serial
cat /sys/block/sdc/device/model
cat /sys/block/sdc/device/serial
cat /sys/block/nvme0n1/device/model
cat /sys/block/nvme0n1/device/serial
echo 'AHCI END identity'
echo 'AHCI BEGIN names'
cat /sys/block/sda/dev
cat /sys/block/sdb/dev
cat /sys/block/sdc/dev
cat /sys/block/sda/size
cat /sys/block/sda/ro
echo 'AHCI END names'
echo 'AHCI BEGIN before'
/bin/nvme sum /dev/sda 0 67108864
/bin/nvme sum /dev/sdb 0 67108864
/bin/nvme sum /dev/sdc 0 67108864
echo 'AHCI END before'
echo 'AHCI BEGIN bytes'
/bin/nvme sizes /dev/sda 0x7078373562616863
echo 'AHCI END bytes'
echo 'AHCI BEGIN after'
/bin/nvme sum /dev/sda 0 67108864
echo 'AHCI END after'
echo 'AHCI SESSION END'
