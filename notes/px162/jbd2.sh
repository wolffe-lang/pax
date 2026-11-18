#!/usr/bin/env bash
# jbd2.sh KERNEL MODULES OUT — black-box Linux: boots KERNEL (its MODULES
# directory's virtio and ext4 modules, decompressed into an initramfs) under
# QEMU (TCG) with jbd2look.c as init, an ext3 disk (mke2fs -t ext3, 64 MiB,
# 4 KiB blocks) as vda and a plain ext2 disk as vdb. OUT/serial.log is the
# guest's console; OUT/look.txt its LOOK lines. Nothing of Linux's source is
# read: the kernel and its modules are run.
set -euo pipefail
kernel=$1 modules=$2 out=$3
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$out"; mkdir -p "$out/root/lib/modules" "$out/root/proc" "$out/root/sys" "$out/root/dev"
cc -static -O2 -Wall -Wextra -Werror "$here/jbd2look.c" -o "$out/root/init"
order=() seen=" "
add() {
    local m=$1 line d n path
    grep -Eq "/${m//-/[-_]}\.ko\$" "$modules/modules.builtin" && return
    line=$(grep -E "/${m//-/[-_]}\.ko(\.zst|\.xz|\.gz)?:" "$modules/modules.dep" | head -n 1)
    [ -n "$line" ] || { echo "jbd2.sh: no module $m" >&2; exit 2; }
    for d in $(echo ${line#*:} | tr ' ' '\n' | tac); do n=${d##*/}; add "${n%%.ko*}"; done
    path=${line%%:*}
    case $seen in *" $path "*) return ;; esac
    seen="$seen$path "; order+=("$path")
}
for m in virtio_pci virtio_blk ext4; do add "$m"; done
: > "$out/root/lib/modules/order"
for path in "${order[@]}"; do
    n=${path##*/}; n=${n%%.ko*}
    case $path in
        *.zst) zstd -q -d -c "$modules/$path" > "$out/root/lib/modules/$n.ko" ;;
        *.xz) xz -d -c "$modules/$path" > "$out/root/lib/modules/$n.ko" ;;
        *.gz) gzip -d -c "$modules/$path" > "$out/root/lib/modules/$n.ko" ;;
        *) cp "$modules/$path" "$out/root/lib/modules/$n.ko" ;;
    esac
    echo "$n" >> "$out/root/lib/modules/order"
done
(cd "$out/root" && find . | cpio -o -H newc --quiet) > "$out/initramfs.cpio"
truncate -s 64M "$out/vda.img"; mke2fs -q -F -t ext3 -b 4096 "$out/vda.img"
truncate -s 16M "$out/vdb.img"; mke2fs -q -F -t ext2 -b 4096 "$out/vdb.img"
timeout 600 qemu-system-x86_64 -machine q35 -accel tcg -cpu max -m 256M -nographic -no-reboot \
    -kernel "$kernel" -initrd "$out/initramfs.cpio" -append "console=ttyS0 loglevel=4 panic=-1" \
    -drive "file=$out/vda.img,if=none,id=d0,format=raw" -device virtio-blk-pci,drive=d0 \
    -drive "file=$out/vdb.img,if=none,id=d1,format=raw" -device virtio-blk-pci,drive=d1 \
    < /dev/null > "$out/serial.log" 2>&1 || true
tr -d '\r' < "$out/serial.log" | grep -E '^LOOK |EXT4-fs|JBD2' > "$out/look.txt" || true
echo "kernel: $(file -b "$kernel" | sed -n 's/.*version \([^ ]*\).*/\1/p')"
echo "modules: $(tr '\n' ' ' < "$out/root/lib/modules/order")"
grep -q '^LOOK end$' "$out/look.txt"
