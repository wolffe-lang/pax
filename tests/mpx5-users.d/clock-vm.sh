#!/usr/bin/env bash
# tests/mpx5-users.d/clock-vm.sh — how tests/mpx5-users.d/linux/clock*.txt were made: the clock sessions run on a
# real Linux booted under QEMU, the program a child of pid 1 (tests/mpx5-users.d/clock-vminit.c), root of the initial
# user namespace with every capability; the user session after `as 1000 1000`. The kernel image is a Linux kernel run
# as a guest and never read. TCG, one CPU, 1 GiB, no network, no disk; the date the host's, given on the command line
# (clock-vminit.c says why). The initramfs is the archive tests/mpx5-users makes for the clock sessions (the same
# entries, by tools/mkinitramfs) followed by a second archive holding only /init. One boot a session.
#
#   tests/mpx5-users.d/clock-vm.sh KERNEL OUTDIR [SESSIONS]
#
# Builds the programs with tools/mkcred (the host's cc and static glibc: a baseline x86-64 Ubuntu, as for the suite)
# and clock-vminit.c beside them. OUTDIR gets, for each session S, S.txt (the lines it wrote), S.rc (its exit status),
# S.log (the console) and vm-clock.meta (the kernel image's digest, QEMU's version, the archives' and programs'
# digests, each boot's first lines). Exit 0 when every boot wrote its last marker, 1 when one did not, 2 on a tool error.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
pax=$(cd "$here/../.." && pwd)
k=${1:?usage: clock-vm.sh KERNEL OUTDIR [SESSIONS]} out=${2:?usage: clock-vm.sh KERNEL OUTDIR [SESSIONS]} sessions=${3:-clock,clock-user}
[ -r "$k" ] || { echo "clock-vm: no readable kernel image $k" >&2; exit 2; }
for t in qemu-system-x86_64 cc sha256sum; do command -v "$t" > /dev/null || { echo "clock-vm: missing $t" >&2; exit 2; }; done
mkdir -p "$out"
out=$(cd "$out" && pwd)
work=$out/vm-work.$$
mkdir -p "$work/bin"
trap 'rm -rf "$work"' EXIT
"$pax/tools/mkcred" "$work/bin" > "$out/vm-clock.programs.txt" || exit 2
cc -static -no-pie -O1 -Wall -Wextra -I "$pax/user/elf" -Wl,--build-id=none -o "$work/bin/vminit" "$here/clock-vminit.c" || exit 2
"$pax/tools/mkinitramfs" "$work/image.cpio" "/bin/clock=$work/bin/clock:755" "/bin/as=$work/bin/as:755" "/t/:777" "/t/clock/:777" \
    > "$out/vm-clock.image.txt" || exit 2
"$pax/tools/mkinitramfs" "$work/init.cpio" "/init=$work/bin/vminit:755" > "$out/vm-clock.initramfs.txt" || exit 2
cat "$work/image.cpio" "$work/init.cpio" > "$work/probes.cpio"
{
    echo "kernel: $(basename "$k") $(sha256sum "$k" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1)"
    echo "image archive: $(sha256sum "$work/image.cpio" | cut -d' ' -f1)"
    echo "initramfs: $(sha256sum "$work/probes.cpio" | cut -d' ' -f1)"
    for p in clock as vminit; do echo "$p: $(sha256sum "$work/bin/$p" | cut -d' ' -f1)"; done
    echo "sessions: $sessions"
} > "$out/vm-clock.meta"
ok=0
for s in ${sessions//,/ }; do
    timeout "${CLOCK_VM_TIMEOUT:-1200}" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 1 -m 1024 -nographic -no-reboot -nic none \
        -kernel "$k" -initrd "$work/probes.cpio" \
        -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init clockvm_now=$(date -u +%s) clockvm=$s" < /dev/null > "$out/$s.log" 2>&1
    rc=$?
    tr -d '\r' < "$out/$s.log" | sed -e 's/^.*\(=== clock vm: \)/\1/' | sed -n '/^=== clock vm: /,/^=== clock vm: done/p' > "$out/$s.vm.txt"
    awk -v s="$s" '$0 == "=== BEGIN " s { on = 1; next } index($0, "=== END " s " status ") == 1 { on = 0 } on' "$out/$s.vm.txt" > "$out/$s.txt"
    sed -n "s/^=== END $s status //p" "$out/$s.vm.txt" > "$out/$s.rc"
    grep -m3 '^=== clock vm: ' "$out/$s.vm.txt" | sed "s/^/$s: /" >> "$out/vm-clock.meta"
    echo "$s: qemu exit $rc, $(wc -l < "$out/$s.txt") lines, status $(cat "$out/$s.rc")" >> "$out/vm-clock.meta"
    grep -q '^=== clock vm: done' "$out/$s.vm.txt" || { echo "clock-vm: $s did not reach its last marker (qemu exit $rc)" >&2; ok=1; }
done
exit $ok
