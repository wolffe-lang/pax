#!/bin/bash
# px48, on kasumi: the real-root Linux side of a typed program, px47's
# notes/px47/linux-vm.sh with the program's argv as an argument and
# notes/px48/vmjob as pid 1. Boots a real Linux under QEMU (the host's
# own kernel image, run as a guest and never read) with vmjob as pid 1:
# root of the initial user namespace with every capability, devtmpfs at
# /dev, the four protected settings written to 1 (R7). TCG, 1 CPU, 1 GiB
# (PX48_MEM MiB), no network, no disk. The initramfs is the suite's own
# archive, byte for byte, followed by one holding /px46/vmjob,
# /px46/keys, /px46/prompt and /px46/argv (one word a line).
#
#   linux-vm.sh PAXROOT VMJOB ARCHIVE.cpio KEYS ARGV OUTDIR NAME [PROMPT]
#
# OUTDIR gets NAME.tty (every byte the terminal showed), NAME.tty.rc
# (the program's status), NAME.log (the console) and vm-NAME.meta.
set -uo pipefail
pax=$1 vmjob=$2 image=$3 keys=$4 argv=$5 out=$6 name=$7 prompt=${8:-'$ '}
k=${PX48_KERNEL:-/usr/lib/modules/$(uname -r)/vmlinuz}
[ -r "$k" ] || { echo "linux-vm: no readable kernel image $k" >&2; exit 2; }
mkdir -p "$out"
work=$out/vm-work.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
printf '%s' "$prompt" > "$work/prompt"
printf '%s\n' $argv > "$work/argv"
"$pax/tools/mkinitramfs" "$work/init.cpio" "/px46/vmjob=$vmjob:755" "/px46/keys=$keys:644" \
    "/px46/prompt=$work/prompt:644" "/px46/argv=$work/argv:644" > "$work/init.txt" || exit 2
cat "$image" "$work/init.cpio" > "$work/all.cpio"
timeout "${PX48_TIMEOUT:-1800}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m "${PX48_MEM:-1024}" -nographic -no-reboot -nic none \
    -kernel "$k" -initrd "$work/all.cpio" \
    -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/px46/vmjob" < /dev/null > "$out/$name.log" 2>&1
rc=$?
tr -d '\r' < "$out/$name.log" | sed -n 's/^H //p' | xxd -r -p > "$out/$name.tty"
tr -d '\r' < "$out/$name.log" | sed -n 's/^=== px46 vm: status //p' > "$out/$name.tty.rc"
{
    echo "kernel: $k $(sha256sum "$k" | cut -d' ' -f1) ($(uname -r))"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1), exit $rc"
    echo "image archive: $(sha256sum "$image" | cut -d' ' -f1)"
    echo "initramfs: $(sha256sum "$work/all.cpio" | cut -d' ' -f1)"
    echo "vmjob: $(sha256sum "$vmjob" | cut -d' ' -f1)"
    echo "keys: $keys $(sha256sum "$keys" | cut -d' ' -f1)"
    echo "argv: $argv"
    tr -d '\r' < "$out/$name.log" | grep '^=== px46 vm: ' | grep -v '^=== px46 vm: begin'
    echo "$name.tty: $(wc -c < "$out/$name.tty") bytes, $(sha256sum "$out/$name.tty" | cut -d' ' -f1); status $(cat "$out/$name.tty.rc")"
} > "$out/vm-$name.meta"
grep -q '^=== px46 vm: done' <(tr -d '\r' < "$out/$name.log") || { echo "linux-vm: the session did not reach its last marker (qemu exit $rc)" >&2; exit 1; }
