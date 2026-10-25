#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px81
P=$L/pax
W=$L/wording
# Exact xsh key sequence; only files that sequence reaches are needed.
podman run --rm -i --memory 8g --ulimit core=0:0 -v "$L:$L:Z" -w "$P" \
 -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e SOURCE_DATE_EPOCH=1700000000 \
 localhost/px80-ubuntu taskset -c 8-11 bash -s <<'INNER'
set -euo pipefail
L=/home/mfwolffe/lanes/px81; W=$L/wording
mkdir -p "$W/xroot/bin" "$W/xroot/g" "$W/bin"
cc -static -O1 -o "$W/bin/vmjob-px52" notes/px52/vmjob.c
cp "$L/build/mpx5-pelt/pelt/pelt" "$W/xroot/bin/sh"
cp "$L/build/mpx5-pelt/root/bin/as" "$W/xroot/bin/as"
cp "$W/bore/"* "$W/xroot/bin/"
printf '/g 1777 0 0\n' > "$W/owners"
args=(/g/:1777)
for f in "$W/xroot/bin/"*; do args+=("/bin/${f##*/}=$f:755"); done
tools/mkinitramfs "$W/xsh.cpio" "${args[@]}" > "$W/xsh.initramfs.txt"
for role in root pax; do
 argv='/bin/sh -i -m'; [ "$role" = root ] || argv='/bin/as 1000 1000 /bin/sh -i -m'
 printf '%s\n' "$argv" > "$W/$role.run"
 tools/mkinitramfs "$W/$role.cpio" "${args[@]}" "/etc/pax-run=$W/$role.run:644" > "$W/$role.initramfs.txt"
 tools/mkimage --conf boot/limine-initramfs.conf --add "$W/$role.cpio" initramfs.cpio \
  "$L/build/mpx5-pelt/native/kmain_console.elf" "$W/$role.iso"
done
INNER
for take in rec1 rec2; do
 for role in root pax; do
  argv='/bin/sh -i -m'; name=xsh
  if [ "$role" = pax ]; then argv='/bin/as 1000 1000 /bin/sh -i -m'; name=xsh-user; fi
  echo "begin real-root Linux $take $role $(date -Is)"
  PX48_TIMEOUT=240 bash "$P/notes/px48/linux-vm.sh" "$P" "$W/bin/vmjob-px52" "$W/xsh.cpio" \
   "$P/user/console/execs.keys" "$argv" "$W/$take" "$name"
  test "$(cat "$W/$take/$name.tty.rc")" = 0
 done
done
for f in xsh.tty xsh-user.tty xsh.tty.rc xsh-user.tty.rc; do cmp "$W/rec1/$f" "$W/rec2/$f"; done
echo 'PASS repeated real-root/root-and-user recordings are byte-identical'
"$P/tools/linux-tree" --root "$W/xroot" --keys "$P/user/console/execs.keys" --prompt '$ ' \
 --argv0 /bin/as --size 512m --rdev --nsproc --owners "$W/owners" "$W/container-user.tty" -- /bin/as 1000 1000 /bin/sh -i -m
. "$P/tools/lib.sh"
for n in xsh xsh-user; do serial_norm "$W/rec1/$n.tty" > "$W/$n.norm"; done
serial_norm "$W/container-user.tty" > "$W/container-user.norm"
cmp "$W/xsh-user.norm" "$W/container-user.norm"
echo 'PASS container user matches real-root guest user recording'
for role in root pax; do
 echo "begin PAX native BIOS $role $(date -Is)"
 PAX_TYPE_PAUSE=0.6 "$P/tools/qemu-halt" --firmware bios --no-screen --serial "$W/pax-$role.serial.log" --timeout 240 \
  --qemu -m --qemu 1024M --elf "$L/build/mpx5-pelt/native/kmain_console.elf" --type "$P/user/console/execs.keys" \
  --prompt '$ ' --marker 'halt|PANIC .*' "$W/$role.iso" > "$W/pax-$role.halt.log" 2>&1
 serial_norm "$W/pax-$role.serial.log" > "$W/pax-$role.norm"
done
