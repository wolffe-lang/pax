#!/bin/bash
# px14, inside px13-ubuntu (privileged, rootless): pelt's spawn path, black-box.
set -u
cd /w
R=/w/root
cp /bin/busybox $R/bin/ls; sha256sum $R/bin/ls; mkdir -p $R/dev $R/proc
mount --bind /dev $R/dev
mount -t proc proc $R/proc
for v in nopath path; do
  pre=(); [ $v = path ] && pre=(/usr/bin/env PATH=/bin)
  python3 /pax/tools/linux-tty --keys /w/shell.keys --prompt '$ ' /w/out/$v.tty -- \
    ${pre[@]+"${pre[@]}"} /usr/bin/strace -f -tt -o /w/out/$v.strace /usr/sbin/chroot $R /bin/pelt
  echo "$v rc $(cat /w/out/$v.tty.rc)"
  python3 /pax/tools/linux-tty --keys /w/shell.keys --prompt '$ ' /w/out/$v-plain.tty -- \
    ${pre[@]+"${pre[@]}"} /usr/sbin/chroot $R /bin/pelt
  echo "$v plain rc $(cat /w/out/$v-plain.tty.rc)"
done
umount $R/proc; umount $R/dev
echo done
