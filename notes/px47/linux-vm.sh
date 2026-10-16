#!/bin/bash
# px47, on kasumi: the real-root Linux side of a typed session, px46's
# notes/px46/linux-vm.sh with the keys and the name as arguments. Boots
# a real Linux under QEMU (the host's own kernel image, run as a guest
# and never read) with notes/px46/vmtty as pid 1: root of the initial
# user namespace with every capability, devtmpfs at /dev (its own modes:
# tty0 0620 root:tty, console 0600), the four protected settings written
# to 1 (R7). TCG, 1 CPU, 1 GiB (PX47_MEM MiB), no network, no disk. The initramfs is
# the suite's own archive, byte for byte (its owners and modes are the
# image's), followed by one holding /px46/vmtty, /px46/keys and
# /px46/prompt.
#
#   linux-vm.sh PAXROOT VMTTY ARCHIVE.cpio KEYS OUTDIR NAME
#
# OUTDIR gets NAME.tty (every byte the terminal showed), NAME.tty.rc
# (pelt's status), NAME.log (the console) and vm-NAME.meta.
set -uo pipefail
pax=$1 vmtty=$2 image=$3 keys=$4 out=$5 name=$6
k=${PX47_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
printf '$ ' > "$work/prompt"
"$pax/tools/mkinitramfs" "$work/init.cpio" "/px46/vmtty=$vmtty:755" "/px46/keys=$keys:644" \
    "/px46/prompt=$work/prompt:644" > "$work/init.txt" || exit 2
cat "$image" "$work/init.cpio" > "$work/all.cpio"
timeout "${PX47_TIMEOUT:-1800}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m "${PX47_MEM:-1024}" -nographic -no-reboot -nic none \
    -kernel "$k" -initrd "$work/all.cpio" \
    -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/px46/vmtty" < /dev/null > "$out/$name.log" 2>&1
rc=$?
tr -d '\r' < "$out/$name.log" | sed -n 's/^H //p' | xxd -r -p > "$out/$name.tty"
tr -d '\r' < "$out/$name.log" | sed -n 's/^=== px46 vm: status //p' > "$out/$name.tty.rc"
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1) ($(uname -r))"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1), exit $rc"
    echo "image archive: $(sha256sum "$image" | cut -d' ' -f1)"
    echo "initramfs: $(sha256sum "$work/all.cpio" | cut -d' ' -f1)"
    echo "vmtty: $(sha256sum "$vmtty" | cut -d' ' -f1)"
    echo "keys: $keys $(sha256sum "$keys" | cut -d' ' -f1)"
    tr -d '\r' < "$out/$name.log" | grep '^=== px46 vm: ' | grep -v '^=== px46 vm: begin'
    echo "$name.tty: $(wc -c < "$out/$name.tty") bytes, $(sha256sum "$out/$name.tty" | cut -d' ' -f1); status $(cat "$out/$name.tty.rc")"
} > "$out/vm-$name.meta"
grep -q '^=== px46 vm: done' <(tr -d '\r' < "$out/$name.log") || { echo "linux-vm: the session did not reach its last marker (qemu exit $rc)" >&2; exit 1; }
