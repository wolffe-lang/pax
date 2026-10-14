#!/bin/bash
# px43, on kasumi: the real-root Linux reference of the `chk` sessions of
# tests/mpx5-users. Boots a real Linux under QEMU (the host's own kernel
# image, run as a guest and never read) with notes/px43/vminit.c as pid
# 1: root of the initial user namespace with every capability, no
# account anywhere. TCG, 1 CPU, 1 GiB, no network, no disk. The
# initramfs is IMAGE.cpio (PAX's archive for these sessions, byte for
# byte) followed by a second archive holding only /init. One boot a
# session: the probe changes the image's files.
#
#   linux-vm.sh PAXROOT BINDIR OUTDIR IMAGE.cpio [SESSIONS]
#
# OUTDIR gets, for each session S, S.txt (the lines it wrote), S.rc (its
# exit status), S.log (the console) and vm-chk.meta (the kernel image's
# digest, QEMU's version, the archives' and programs' digests). Exit 0
# when every boot wrote its last marker.
set -uo pipefail
pax=$1 bin=$2 out=$3 image=$4 sessions=${5:-chk,chk-user,chk-soak,chk-soak-user}
k=${PX43_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
"$pax/tools/mkinitramfs" "$work/init.cpio" "/init=$bin/vminit:755" > "$out/vm-chk.initramfs.txt" || exit 2
cat "$image" "$work/init.cpio" > "$work/probes.cpio"
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "image archive: $(sha256sum "$image" | cut -d' ' -f1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    for p in chk seven as vminit; do echo "$p: $(sha256sum "$bin/$p" | cut -d' ' -f1)"; done
    echo "sessions: $sessions"
} > "$out/vm-chk.meta"
ok=0
for s in ${sessions//,/ }; do
    timeout "${PX43_TIMEOUT:-3600}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
        -kernel "$k" -initrd "$work/probes.cpio" \
        -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init px43=$s" < /dev/null > "$out/$s.log" 2>&1
    rc=$?
    tr -d '\r' < "$out/$s.log" | sed -e 's/^.*\(=== px43 vm: \)/\1/' | sed -n '/^=== px43 vm: /,/^=== px43 vm: done/p' > "$out/$s.vm.txt"
    awk -v s="$s" '$0 == "=== BEGIN " s { on = 1; next } index($0, "=== END " s " status ") == 1 { on = 0 } on' "$out/$s.vm.txt" > "$out/$s.txt"
    sed -n "s/^=== END $s status //p" "$out/$s.vm.txt" > "$out/$s.rc"
    grep -m2 '^=== px43 vm: ' "$out/$s.vm.txt" | sed "s/^/$s: /" >> "$out/vm-chk.meta"
    echo "$s: qemu exit $rc, $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")" >> "$out/vm-chk.meta"
    grep -q '^=== px43 vm: done' "$out/$s.vm.txt" || { echo "linux-vm: $s did not reach its last marker (qemu exit $rc)" >&2; ok=1; }
done
exit $ok
