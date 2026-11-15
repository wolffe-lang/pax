#!/usr/bin/env bash
# notes/px130/rig/record.sh BIN KERNEL OUT — the Linux side of tests/mpx5-kmsg (px111's
# notes/px111/rig/record.sh, the same shape): an archive holding BIN's kmsgprobe and as (tools/mkkmsg's
# and tools/mkas's builds), notes/px111/vminit.c's program as /init and the suite's run list as
# /px111/run, booted as a real Linux (KERNEL, a lane host's installed image, booted and never read)
# under QEMU with KVM, one CPU, 1 GiB, no network, no disk, with `printk.devkmsg=on` (bootparam's
# kernel-parameters: Linux limits a burst of writes to /dev/kmsg by default and drops the rest, which
# a flood that overtakes a reader (K28) cannot be held to; PAX limits none). Writes OUT/probe-root.txt and
# OUT/probe-user.txt (each run's `K<n>: ` lines), OUT/probe.serial and OUT/record.meta. Run from a
# checkout of the commit under test, inside the rig's container (lib.sh's `ctr 1`).
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
BIN=${1:?the probe directory} KERNEL=${2:?a Linux kernel image} OUT=${3:?the output directory}
rm -rf "$OUT"; mkdir -p "$OUT"
printf '/bin/kmsgprobe\n/bin/as 1000 1000 /bin/kmsgprobe user\n' > "$OUT/probe.run"
tools/mkinitramfs "$OUT/probe.cpio" "/init=$BIN/vminit:755" "/px111/run=$OUT/probe.run:644" \
    "/bin/kmsgprobe=$BIN/kmsgprobe:755" "/bin/as=$BIN/as:755" /tmp/:1777 > "$OUT/probe.initramfs.txt" || exit 2
echo "START vm $(date -u +%FT%TZ)"
timeout 1800 qemu-system-x86_64 -enable-kvm -cpu host -smp 1 -m 1024 -kernel "$KERNEL" -initrd "$OUT/probe.cpio" \
    -append "console=ttyS0 quiet loglevel=0 printk.devkmsg=on panic=-1 rdinit=/init" -nographic -no-reboot -serial stdio -monitor none \
    -net none < /dev/null > "$OUT/probe.serial" 2>&1
rc=$?
tr -d '\r' < "$OUT/probe.serial" > "$OUT/probe.txt"
k=0
for n in probe-root probe-user; do
    k=$((k + 1))
    awk -v k="$k" '/^=== px111 vm: run / { r++; on = (r == k); next } /^=== px111 vm: / { on = 0; next } on && /^K[0-9]+: /' \
        "$OUT/probe.txt" > "$OUT/$n.txt"
done
{
    echo "kernel: $(basename "$(dirname "$KERNEL")") $(sha256sum "$KERNEL" | cut -d' ' -f1)"
    echo "qemu: $(qemu-system-x86_64 --version | head -n 1), exit $rc"
    echo "initramfs: $(sha256sum "$OUT/probe.cpio" | cut -d' ' -f1)"
    for f in kmsgprobe vminit as; do echo "$f: $(sha256sum "$BIN/$f" | cut -d' ' -f1)"; done
    grep '^=== px111 vm: ' "$OUT/probe.txt"
    for n in probe-root probe-user; do echo "$n.txt: $(wc -l < "$OUT/$n.txt") lines, $(sha256sum "$OUT/$n.txt" | cut -d' ' -f1)"; done
} > "$OUT/record.meta"
echo "END vm exit=$rc $(date -u +%FT%TZ)"
grep -q '^=== px111 vm: done' "$OUT/probe.txt" || { echo "the guest did not finish"; exit 1; }
