#!/bin/bash
# px38, on kasumi: boot a real Linux under QEMU with the probes as its
# initramfs and pid 1 (probes/vminit.c): the "vm" root, root of the
# initial user namespace with every capability, no account anywhere.
#
#   vm-run.sh PAXROOT BINDIR OUT [PROBES [EXTRA]]
#
# PAXROOT: a pax tree (for tools/mkinitramfs). BINDIR: the static probes
# (probes/build.sh). OUT: the console log; OUT.txt gets it with carriage
# returns and the kernel's own lines removed. PROBES: comma-separated
# (default ids,cred,perm,setid,sig). The kernel is the host's own image,
# world-readable, run as a guest and never read: PX38_KERNEL, default
# /usr/lib/modules/$(uname -r)/vmlinuz. EXTRA goes on the kernel command
# line: `px38prot=1` has the init turn on fs.protected_hardlinks,
# _symlinks, _regular and _fifos before the probes (a distribution's
# setting; the kernel's own default is 0). TCG, 1 CPU, 1 GiB, no network,
# no disk. Exit 0 when the guest wrote its last marker.
set -uo pipefail
pax=$1 bin=$2 out=$3 probes=${4:-ids,cred,perm,setid,sig} extra=${5:-}
k=${PX38_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "vm-run: no readable kernel image $k" >&2; exit 2; }
work=$(dirname "$out")/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
pairs=("/init=$bin/vminit:755")
for p in ids cred perm setid sig; do pairs+=("/$p=$bin/$p:755"); done
"$pax/tools/mkinitramfs" "$work/probes.cpio" "${pairs[@]}" > "$out.initramfs.txt" || exit 2
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    echo "probes: $probes $extra"
} > "$out.meta"
timeout 900 qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
    -kernel "$k" -initrd "$work/probes.cpio" \
    -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init $extra px38=$probes" < /dev/null > "$out" 2>&1
rc=$?
echo "qemu exit: $rc" >> "$out.meta"
tr -d '\r' < "$out" | sed -e 's/^.*\(=== px38 vm: \)/\1/' | sed -n '/^=== px38 vm: /,/^=== px38 vm: done/p' > "$out.txt"
grep -q '^=== px38 vm: done' "$out.txt" || { echo "vm-run: the guest did not reach its last marker (qemu exit $rc)" >&2; exit 1; }
exit 0
