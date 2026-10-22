#!/usr/bin/env bash
# Separate M2 probe image, never silently substituted for the M1 dev image.
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
printf '%s\n' $$ > "$L/m2-pax.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/m2-pax.status; exit "$s"' EXIT
[ "$(cat "$L/lld-build.status")" = 0 ]
[ ! -e "$L/m2-probe" ]
mkdir -p "$L/m2-probe"
cp -a "$L/session4-build/mpx5-wolf/root" "$L/m2-probe/root"
r=$L/m2-probe/root
cp "$L/lld-out/ld.lld" "$r/usr/bin/ld.lld"
cp "$L/m2/cc" "$r/usr/bin/cc"
cp "$L/w/bore/id" "$r/bin/id"
mkdir -p "$r/usr/lib/wolf-musl"
cp "$L/m2/sysroot/"* "$r/usr/lib/wolf-musl/"
printf '%s\n' '/bin/as 1000 1000 /bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m' > "$r/etc/pax-run"
printf '%s\n' '/home/pax 755 1000 1000' '/tmp 1777 0 0' > "$L/m2-probe/owners"
podman run --rm -v "$L:$L" -w "$L/pax" -e L="$L" -e PAX_CACHE="$L/cache" localhost/px13-ubuntu bash -c '
 set -euo pipefail
 readelf -hW "$L/lld-out/ld.lld" | grep -E "Type: +EXEC"
 ! readelf -lW "$L/lld-out/ld.lld" | grep INTERP
 readelf -dW "$L/lld-out/ld.lld" | grep "no dynamic section"
 r=$L/m2-probe/root
 args=(/home/pax/:755:1000:1000 /tmp/:1777)
 while IFS= read -r f; do
   mode=644; [ -x "$f" ] && mode=755
   args+=("/${f#"$r/"}=$f:$mode")
 done < <(find "$r" -type f | LC_ALL=C sort)
 tools/mkinitramfs "$L/m2-probe/m2.cpio" "${args[@]}" > "$L/m2-probe/initramfs.log"
 tools/mkimage --conf boot/limine-initramfs.conf --add "$L/m2-probe/m2.cpio" initramfs.cpio \
   "$L/session4-build/mpx5-wolf/native/kmain_console.elf" "$L/m2-probe/m2.iso"
 '
cd "$L/pax"
PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu tools/linux-tree \
 --root "$r" --keys "$L/m2.keys" --prompt '$ ' --argv0 /bin/as --size 1g --rdev --nsproc \
 --owners "$L/m2-probe/owners" "$L/m2-probe/linux.tty" -- \
 /bin/as 1000 1000 /bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m
PAX_BUILD="$L/m2-probe" taskset -c 0-3 tools/qemu-halt --accel tcg --firmware bios \
 --serial "$L/m2-probe/pax.serial.log" --timeout 900 --qemu -m --qemu 2048M \
 --elf "$L/session4-build/mpx5-wolf/native/kmain_console.elf" --marker 'halt|PANIC .*' \
 --type "$L/m2.keys" --prompt '$ ' "$L/m2-probe/m2.iso" > "$L/m2-probe/verdict.log" 2>&1
cat "$L/m2-probe/verdict.log"
