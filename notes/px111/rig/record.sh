#!/usr/bin/env bash
# notes/px111/rig/record.sh SHA — the Linux side of tests/mpx5-pty: each image's archive, as
# take.sh's build made it at SHA ($L/pb-<sha8>/mpx5-pty/IMAGE.cpio), followed by one holding
# notes/px111/vminit.c's program as /init and the image's run list as /px111/run, booted as a real
# Linux (KERNEL, the host's installed image, never read) under QEMU with KVM, one CPU, 1 GiB, no
# network, no disk; a light job. Writes $L/rec-<sha8>/<run>.txt (the run's lines, carriage returns
# out), IMAGE.serial and IMAGE.meta. Run from a checkout of SHA.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
SHA=$1
here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"
checkout_ok "$SHA" || exit 3
cd "$CO"
PB=$L/pb-${SHA:0:8}/mpx5-pty
OUT=$L/rec-${SHA:0:8}
rm -rf "$OUT"; mkdir -p "$OUT"
[ -x "$PB/bin/vminit" ] || { echo "no $PB/bin/vminit: take.sh build first"; exit 2; }
names() { case $1 in probe) echo "probe-root probe-user" ;; session) echo "session-root session-user" ;; esac; }
for im in probe session; do
    python3 tools/mkinitramfs "$OUT/$im.init.cpio" "/init=$PB/bin/vminit:755" "/px111/run=$PB/$im.run:644" > "$OUT/$im.init.txt" || exit 2
    cat "$PB/$im.cpio" "$OUT/$im.init.cpio" > "$OUT/$im.vm.cpio"
    printf 'START vm-%s %s\n' "$im" "$(ts)"
    "$LIGHT" "$LBLK" bash -c 'taskset -c "$LIGHT_CPUS" timeout 1800 qemu-system-x86_64 -enable-kvm -cpu host -smp 1 -m 1024 -kernel "$0" -initrd "$1" \
        -append "console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/init" -nographic -no-reboot -serial stdio -monitor none -net none < /dev/null' \
        "$KERNEL" "$OUT/$im.vm.cpio" > "$OUT/$im.serial" 2>&1
    rc=$?
    tr -d '\r' < "$OUT/$im.serial" > "$OUT/$im.txt"
    k=0
    for n in $(names "$im"); do
        k=$((k + 1))
        awk -v k="$k" '/^=== px111 vm: run / { r++; on = (r == k); next } /^=== px111 vm: / { on = 0; next } on' "$OUT/$im.txt" > "$OUT/$n.txt"
    done
    {
        echo "kernel: $(readlink -f "$KERNEL") $(sha256sum "$KERNEL" | cut -d' ' -f1)"
        echo "qemu: $(qemu-system-x86_64 --version | head -n 1), exit $rc"
        echo "archive: $im.cpio $(sha256sum "$PB/$im.cpio" | cut -d' ' -f1)"
        echo "initramfs: $(sha256sum "$OUT/$im.vm.cpio" | cut -d' ' -f1)"
        grep '^=== px111 vm: ' "$OUT/$im.txt"
        for n in $(names "$im"); do echo "$n.txt: $(wc -l < "$OUT/$n.txt") lines, $(sha256sum "$OUT/$n.txt" | cut -d' ' -f1)"; done
    } > "$OUT/$im.meta"
    printf 'END vm-%s exit=%s %s\n' "$im" "$rc" "$(ts)"
    grep -q '^=== px111 vm: done' "$OUT/$im.txt" || { echo "the $im guest did not finish"; exit 1; }
done
