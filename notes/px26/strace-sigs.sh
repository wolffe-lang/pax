#!/bin/bash
# px26, inside px13-ubuntu (privileged, rootless): the new pelt (sh05) and
# boreutils (bu20) on a Linux pseudo-terminal, black-box, under strace.
# /progs/{pelt,bore}: pax's own tools/mkpelt and tools/mkboreutils builds.
set -u
cd /w
R=/w/root
rm -rf $R /w/out; mkdir -p $R/bin $R/etc $R/dev $R/proc /w/out
for u in cat echo env false head ls readlink sleep stat tail true wc; do cp /progs/bore/$u $R/bin/$u; done
cp /progs/pelt/pelt $R/bin/pelt
printf '%s\n' 'PAX. Kernel: wolf. Shell: wolf. Tools: wolf. Nothing here existed last year.' > $R/etc/motd
printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\n' > $R/etc/words
printf 'root:x:0:0:root:/:/bin/pelt\n' > $R/etc/passwd
printf 'root:x:0:\n' > $R/etc/group
echo /bin/pelt > $R/etc/pax-run
find $R -exec touch -h -d @0 {} +
sha256sum $R/bin/* $R/etc/*
mount --bind /dev $R/dev
mount -t proc proc $R/proc
python3 /pax/tools/linux-tty --isig --keys /w/strace-sigs.keys --prompt '$ ' /w/out/sigs.tty -- \
  /usr/bin/env PATH=/bin /usr/bin/strace -f -tt -o /w/out/sigs.strace /usr/sbin/chroot $R /bin/pelt
echo "strace rc $(cat /w/out/sigs.tty.rc)"
python3 /pax/tools/linux-tty --isig --keys /w/strace-long.keys --prompt '$ ' /w/out/long.tty -- \
  /usr/bin/env PATH=/bin /usr/bin/strace -f -tt -o /w/out/long.strace /usr/sbin/chroot $R /bin/pelt
echo "long strace rc $(cat /w/out/long.tty.rc)"
# each boreutils program of bu20's four, alone, for its own call list
for c in "ls -l /bin" "stat /etc/motd" "readlink /proc/self/exe" "env"; do
  n=$(echo $c | cut -d' ' -f1)
  /usr/bin/env -i PATH=/bin HOME=/ TERM=linux PAX=1 /usr/bin/strace -f -o /w/out/$n.strace /usr/sbin/chroot $R /bin/$c > /w/out/$n.out 2>&1
  /usr/bin/env -i PATH=/bin HOME=/ TERM=linux PAX=1 TZ=UTC0 /usr/bin/strace -f -o /w/out/$n-utc.strace /usr/sbin/chroot $R /bin/$c > /w/out/$n-utc.out 2>&1
done
umount $R/proc; umount $R/dev
echo done
