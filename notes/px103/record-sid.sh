#!/usr/bin/env bash
# record-sid.sh — px103: the recording of user/elf/sid.c on a real Linux.
#
#   notes/px103/record-sid.sh SID_BINARY OUT.txt
#
# A real Linux (the host's installed kernel image, booted under QEMU with
# KVM; nothing of the host is touched) with the program as its init: it
# mounts /proc and a devtmpfs, runs the driver as root, and powers off.
# The kernel's fs.suid_dumpable is its default 0 (the program prints it
# first; PAX's is fixed at 0). OUT.txt gets the driver's lines, from the
# first (`mount nosuid tmpfs`) to the last (`sid: done`), carriage returns
# removed. Run in a light slot; the guest has no network.
set -uo pipefail
bin=$1 out=$2
kernel=${PX103_KERNEL:-/run/current-system/kernel}
tmp=$(mktemp -d "${TMPDIR:?TMPDIR must be set}/record-sid.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
python3 "$(dirname "$0")/../../tools/mkinitramfs" "$tmp/sid.cpio" "/init=$bin:755" "/bin/sid=$bin:755" > /dev/null || exit 2
timeout 180 qemu-system-x86_64 -enable-kvm -m 512 -kernel "$kernel" -initrd "$tmp/sid.cpio" \
    -append "console=ttyS0 panic=-1 rdinit=/init" -nographic -no-reboot -serial stdio -monitor none -net none > "$tmp/serial" 2>&1
tr -d '\r' < "$tmp/serial" | awk '/^suid_dumpable / { printf "%s\n", $0 > "/dev/stderr"; next } /^mount nosuid tmpfs: / { on = 1 } on { print } /^sid: done$/ { exit }' > "$out"
grep -qx 'sid: done' "$out" || { echo "record-sid: the guest did not finish" >&2; exit 1; }
