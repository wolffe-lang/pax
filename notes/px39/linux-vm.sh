#!/bin/bash
# px39, on kasumi: the real-root Linux reference of tests/mpx5-users.
# Boots a real Linux under QEMU (the host's own kernel image, run as a
# guest and never read) with notes/px39/vminit.c as pid 1 and the
# credentials programs in its initramfs, as notes/px38/vm-run.sh does:
# root of the initial user namespace with every capability, no account
# anywhere. TCG, 1 CPU, 1 GiB, no network, no disk.
#
#   linux-vm.sh PAXROOT BINDIR OUTDIR [SESSIONS]
#
# BINDIR: the static programs (tools/mkcred's four, and vminit built the
# same way). OUTDIR gets vm.log (the console), vm.meta, and for each
# session S the lines it wrote as S.txt and its exit status as S.rc.
# SESSIONS: comma-separated (default: all seven). Exit 0 when the guest
# wrote its last marker.
set -uo pipefail
pax=$1 bin=$2 out=$3 sessions=${4:-cred,cred-user,ident,ident-user,ids,soak,soak-user}
k=${PX39_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
pairs=("/init=$bin/vminit:755")
for p in cred ids ident as; do pairs+=("/$p=$bin/$p:755"); done
"$pax/tools/mkinitramfs" "$work/probes.cpio" "${pairs[@]}" > "$out/vm.initramfs.txt" || exit 2
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    for p in cred ids ident as vminit; do echo "$p: $(sha256sum "$bin/$p" | cut -d' ' -f1)"; done
    echo "sessions: $sessions"
} > "$out/vm.meta"
timeout "${PX39_TIMEOUT:-2400}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
    -kernel "$k" -initrd "$work/probes.cpio" \
    -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init px39=$sessions" < /dev/null > "$out/vm.log" 2>&1
rc=$?
echo "qemu exit: $rc" >> "$out/vm.meta"
tr -d '\r' < "$out/vm.log" | sed -e 's/^.*\(=== px39 vm: \)/\1/' | sed -n '/^=== px39 vm: /,/^=== px39 vm: done/p' > "$out/vm.txt"
grep '^=== px39 vm: ' "$out/vm.txt" | head -n 2 >> "$out/vm.meta"
for s in ${sessions//,/ }; do
    awk -v s="$s" '$0 == "=== BEGIN " s { on = 1; next } index($0, "=== END " s " status ") == 1 { on = 0 } on' "$out/vm.txt" > "$out/$s.txt"
    sed -n "s/^=== END $s status //p" "$out/vm.txt" > "$out/$s.rc"
    echo "$s: $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")" >> "$out/vm.meta"
done
grep -q '^=== px39 vm: done' "$out/vm.txt" || { echo "linux-vm: the guest did not reach its last marker (qemu exit $rc)" >&2; exit 1; }
exit 0
