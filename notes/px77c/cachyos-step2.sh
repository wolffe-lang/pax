#!/bin/busybox sh
# px77c: docs/INSTALL-METAL.md step 2 ("Write the line on the stick") under Linux 7.2.4, busybox's
# sh, sed, tee and mount standing in for CachyOS's bash and util-linux; the guest is root, so `sudo`
# runs its arguments. The only change to the runbook's lines: sdX and sdc are the names found here.
export PATH=/usr/bin:/bin
for m in fat vfat nls_cp437 nls_iso8859-1 nls_utf8; do insmod /lib/fat/$m.ko || echo "insmod $m failed"; done
for b in /sys/block/sd*; do case $(readlink $b) in *usb*) sdX=${b##*/} ;; *ata*) tgt=${b##*/} ;; esac; done
echo "STEP2 the stick is $sdX, the target is $tgt"
printf 'STEP2 raw model=[%s] serial=[%s]\n' "$(cat /sys/block/$tgt/device/model)" "$(cat /sys/block/$tgt/device/serial)"
# --- the runbook's lines ---
sudo mount /dev/${sdX}1 /mnt
d=$tgt
printf 'model=%s serial=%s\n' "$(sed 's/ *$//' /sys/block/$d/device/model)" "$(sed 's/ *$//' /sys/block/$d/device/serial)" \
    | sudo tee -a /mnt/pax/install-targets
cat /mnt/pax/install-targets
sudo umount /mnt
# --- end ---
echo "STEP2 END"
