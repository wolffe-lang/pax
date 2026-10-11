#!/bin/sh
# px27: the probe (user/elf/tree.c, the suite's own build) under strace on
# Linux, its root a tmpfs, inside a throwaway container (privileged for the
# mounts and the chroot, all inside it). Mounted from the host: /x, a staging
# directory holding the probe and taking the strace.
umask 022
mkdir /r && mount -t tmpfs -o size=64m,mode=755 none /r || exit 2
mkdir -p /r/bin /r/etc /r/dev /r/proc
cp /x/tree /r/bin/tree
echo /bin/tree > /r/etc/pax-run
chown -R 0:0 /r
find /r -exec touch -h -d @0 {} +
mount --bind /dev /r/dev
mount -t proc proc /r/proc
uname -r > /x/tree-probe.uname; strace -V | head -n 1 >> /x/tree-probe.uname; sha256sum /x/tree >> /x/tree-probe.uname
cd /r
strace -f -s 96 -o /x/tree-probe.strace chroot /r /bin/tree > /x/tree-probe.out 2>&1 < /dev/null
echo "rc=$?" >> /x/tree-probe.out
strace -f -s 48 -o /x/tree-soak.strace chroot /r /bin/tree soak > /x/tree-soak.out 2>&1 < /dev/null
echo "rc=$?" >> /x/tree-soak.out
umount /r/proc /r/dev
chmod -R a+rwX /x
