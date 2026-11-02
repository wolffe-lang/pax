#!/usr/bin/env bash
# px88 chain r1 (behind both of the block's locks, notes/px88/hasu/launch.sh):
# the lane's image (notes/px88/hasu/Containerfile: px75's and Ubuntu 24.04's
# musl-tools), and black-box Linux before the witness is written: the
# exploration probe (notes/px88/linux/explore.c) built static with musl-gcc,
# run, and run again under strace -f for the calls musl's fork, vfork and
# posix_spawn make. Linux is hasu's own kernel, seen from a rootless
# container; nothing runs on the host but the engine.
set -uo pipefail
B=$1
L=/home/mfwolffe/lanes/px88
P=/home/mfwolffe/lanes/hasu-env/bin/podman
S=$L/scripts
W=$L/work/r1
mkdir -p "$W"
echo "$(date -u +%FT%TZ) r1: block $B held"
uname -a
if ! "$P" image exists localhost/px88-ubuntu:1; then
    echo "$(date -u +%FT%TZ) r1: building localhost/px88-ubuntu:1"
    "$P" build -q -t localhost/px88-ubuntu:1 -f "$S/Containerfile" "$S" || { echo "END image exit=1"; exit 1; }
fi
echo "END image exit=0 ($("$P" image inspect --format '{{.Id}}' localhost/px88-ubuntu:1))"
cp "$L/work/explore.c" "$W/explore.c"
bash "$S/ctr.sh" "$B" r1-explore localhost/px88-ubuntu:1 -- bash -c '
    set -u; cd "$1"
    cat /etc/px88-packages.txt
    musl-gcc --version | head -n 1
    musl-gcc -static -O1 -Wall -o explore explore.c || exit 2
    readelf -hW explore | grep -E "Type:"; readelf -lW explore | grep -c INTERP
    sha256sum explore
    echo "--- run"; ./explore; echo "rc=$?"
    echo "--- strace"; strace -f -qq -e trace=fork,vfork,clone,clone3,execve,wait4,exit_group,set_tid_address,rt_sigprocmask,getpid,gettid,mmap,munmap ./explore strace 2>&1; echo "rc=$?"
' r1 "$W"
rc=$?
echo "$(date -u +%FT%TZ) r1: done rc=$rc"
exit $rc
