#!/bin/bash
# px17, inside px13-ubuntu (privileged, rootless): pelt's plumbing, black-box.
set -u
cd /w
R=/w/root
rm -rf $R; mkdir -p $R/bin $R/etc $R/dev $R/proc /w/out
for u in cat echo false head ls sleep tail true wc; do cp /progs/bore/$u $R/bin/$u; done
cp /progs/pelt/pelt $R/bin/pelt
printf '%s\n' 'PAX. Kernel: wolf. Shell: wolf. Tools: wolf. Nothing here existed last year.' > $R/etc/motd
printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\n' > $R/etc/words
echo /bin/pelt > $R/etc/pax-run
sha256sum $R/bin/* $R/etc/*
mount --bind /dev $R/dev
mount -t proc proc $R/proc
python3 /pax/tools/linux-tty --keys /w/plumb.keys --prompt '$ ' /w/out/plumb.tty -- \
  /usr/bin/env PATH=/bin /usr/bin/strace -f -tt -o /w/out/plumb.strace /usr/sbin/chroot $R /bin/pelt
echo "strace rc $(cat /w/out/plumb.tty.rc)"
python3 /pax/tools/linux-tty --keys /w/plumb.keys --prompt '$ ' /w/out/plumb-plain.tty -- \
  /usr/bin/env PATH=/bin /usr/sbin/chroot $R /bin/pelt
echo "plain rc $(cat /w/out/plumb-plain.tty.rc)"
umount $R/proc; umount $R/dev
echo done
