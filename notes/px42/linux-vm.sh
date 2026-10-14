#!/bin/bash
# px42, on kasumi: the real-root Linux reference of the owners sessions
# of tests/mpx5-users. Boots a real Linux under QEMU (the host's own
# kernel image, run as a guest and never read) with notes/px42/vminit.c
# as pid 1, as notes/px39/linux-vm.sh does: root of the initial user
# namespace with every capability, no account anywhere. TCG, 1 CPU,
# 1 GiB, no network, no disk.
#
#   linux-vm.sh PAXROOT BINDIR OUTDIR [SESSIONS [IMAGE.cpio]]
#
# BINDIR: the static programs (notes/px42/build.sh's). OUTDIR gets
# vm.log (the console), vm.meta, and for each session S the lines it
# wrote as S.txt and its exit status as S.rc. SESSIONS: comma-separated
# (default own,own-user,perm,soak,soak-user). With IMAGE.cpio (for the
# sessions `ls` and `ls-names`) the initramfs is that archive, byte for
# byte, followed by a second archive holding only /init: the root Linux
# unpacks is the tree PAX's image carries. Exit 0 when the guest wrote
# its last marker.
set -uo pipefail
pax=$1 bin=$2 out=$3 sessions=${4:-own,own-user,perm,soak,soak-user} image=${5:-}
k=${PX42_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
tag=vm; [ -z "$image" ] || tag=vm-image
if [ -n "$image" ]; then
    "$pax/tools/mkinitramfs" "$work/init.cpio" "/init=$bin/vminit:755" > "$out/$tag.initramfs.txt" || exit 2
    cat "$image" "$work/init.cpio" > "$work/probes.cpio"
else
    pairs=("/init=$bin/vminit:755")
    for p in own perm as; do pairs+=("/$p=$bin/$p:755"); done
    "$pax/tools/mkinitramfs" "$work/probes.cpio" "${pairs[@]}" > "$out/$tag.initramfs.txt" || exit 2
fi
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    [ -z "$image" ] || echo "image archive: $(sha256sum "$image" | cut -d' ' -f1)"
    for p in own perm as vminit; do echo "$p: $(sha256sum "$bin/$p" | cut -d' ' -f1)"; done
    echo "sessions: $sessions"
} > "$out/$tag.meta"
timeout "${PX42_TIMEOUT:-2400}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
    -kernel "$k" -initrd "$work/probes.cpio" \
    -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init px42=$sessions" < /dev/null > "$out/$tag.log" 2>&1
rc=$?
echo "qemu exit: $rc" >> "$out/$tag.meta"
tr -d '\r' < "$out/$tag.log" | sed -e 's/^.*\(=== px42 vm: \)/\1/' | sed -n '/^=== px42 vm: /,/^=== px42 vm: done/p' > "$out/$tag.txt"
grep '^=== px42 vm: ' "$out/$tag.txt" | head -n 2 >> "$out/$tag.meta"
for s in ${sessions//,/ }; do
    awk -v s="$s" '$0 == "=== BEGIN " s { on = 1; next } index($0, "=== END " s " status ") == 1 { on = 0 } on' "$out/$tag.txt" > "$out/$s.txt"
    sed -n "s/^=== END $s status //p" "$out/$tag.txt" > "$out/$s.rc"
    echo "$s: $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")" >> "$out/$tag.meta"
done
grep -q '^=== px42 vm: done' "$out/$tag.txt" || { echo "linux-vm: the guest did not reach its last marker (qemu exit $rc)" >&2; exit 1; }
exit 0
