#!/bin/bash
# px45, on kasumi: the real-root Linux reference of the `rights` sessions
# of tests/mpx5-users, with the four protected settings at 1 (vminit.c
# writes them first: ruling #75 R7's reference, "vm-protected"). A copy of
# notes/px44/linux-vm.sh. Boots a real Linux under QEMU (the host's own kernel
# image, run as a guest and never read) with notes/px45/vminit.c as pid
# 1: root of the initial user namespace with every capability, no
# account anywhere. TCG, 1 CPU, 1 GiB, no network, no disk. The
# initramfs is IMAGE.cpio (PAX's archive for these sessions, byte for
# byte) followed by a second archive holding only /init. One boot a
# session: the probe changes the image's files.
#
#   linux-vm.sh PAXROOT BINDIR OUTDIR IMAGE.cpio [SESSIONS]
#
# OUTDIR gets, for each session S, S.txt (the lines it wrote), S.rc (its
# exit status), S.log (the console) and vm-rights.meta (the kernel image's
# digest, QEMU's version, the archives' and programs' digests). Exit 0
# when every boot wrote its last marker.
set -uo pipefail
pax=$1 bin=$2 out=$3 image=$4 sessions=${5:-rights,rights-user,rights-soak,rights-soak-user}
k=${PX45_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
"$pax/tools/mkinitramfs" "$work/init.cpio" "/init=$bin/vminit:755" > "$out/vm-rights.initramfs.txt" || exit 2
cat "$image" "$work/init.cpio" > "$work/probes.cpio"
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "image archive: $(sha256sum "$image" | cut -d' ' -f1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    for p in rights as sig priv vminit; do echo "$p: $(sha256sum "$bin/$p" | cut -d' ' -f1)"; done
    echo "sessions: $sessions"
} > "$out/vm-rights.meta"
ok=0
for s in ${sessions//,/ }; do
    timeout "${PX45_TIMEOUT:-3600}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
        -kernel "$k" -initrd "$work/probes.cpio" \
        -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init px45=$s" < /dev/null > "$out/$s.log" 2>&1
    rc=$?
    tr -d '\r' < "$out/$s.log" | sed -e 's/^.*\(=== px45 vm: \)/\1/' | sed -n '/^=== px45 vm: /,/^=== px45 vm: done/p' > "$out/$s.vm.txt"
    awk -v s="$s" '$0 == "=== BEGIN " s { on = 1; next } index($0, "=== END " s " status ") == 1 { on = 0 } on' "$out/$s.vm.txt" > "$out/$s.txt"
    sed -n "s/^=== END $s status //p" "$out/$s.vm.txt" > "$out/$s.rc"
    grep -m3 '^=== px45 vm: ' "$out/$s.vm.txt" | sed "s/^/$s: /" >> "$out/vm-rights.meta"
    echo "$s: qemu exit $rc, $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")" >> "$out/vm-rights.meta"
    grep -q '^=== px45 vm: done' "$out/$s.vm.txt" || { echo "linux-vm: $s did not reach its last marker (qemu exit $rc)" >&2; ok=1; }
done
exit $ok
