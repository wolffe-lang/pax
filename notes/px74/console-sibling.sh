#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px74
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp
export PAX_ENGINE=$L/reference-engine PAX_TREE_IMAGE=docker.io/library/python:3.12-slim
export PAX_REQUIRE_UEFI=1
cd "$L/pax-final"
printf '%s\n' "$$" > "$L/runs/console-sibling.pid"
exec > "$L/runs/console-sibling.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$L/runs/console-sibling.exit"' EXIT
printf 'console sibling queued %s\n' "$(date -Is)"
exec 9>/home/mfwolffe/lanes/kasumi-cores-12-15.lock
flock 9
    printf 'console sibling start %s\n' "$(date -Is)"
    d=$PAX_BUILD/mpx3-console
    for s in ask-serial ask-ps2 pelt-serial pelt-eof-serial pelt-eof-ps2; do
        case $s in ask-*) p=ask; k=ask; prompt='> '; args=(tty);; pelt-eof-*) p=pelt; k=pelt-eof; prompt='$ '; args=();; *) p=pelt; k=pelt; prompt='$ '; args=();; esac
        tools/linux-tree --root "$d/$p/root" --keys "user/console/$k.keys" --prompt "$prompt" \
            --argv0 "/bin/$p" --rdev "$d/linux/$s.tty" -- "/bin/$p" "${args[@]}"
    done
    podman run --rm --memory 12g --ulimit core=0:0 -v "$L:$L:Z" \
        -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e PAX_REQUIRE_UEFI -e SOURCE_DATE_EPOCH=1700000000 \
        -w "$L/pax-final" localhost/px80-ubuntu taskset -c 12-15 "$L/in.sh" bash -c '
set -euo pipefail
w=$PAX_BUILD/mpx3-console
cp /home/mfwolffe/lanes/px74/final-build/mpx6-usb/native/kmain_console.elf "$w/native/kmain_console.elf"
for p in ask pelt; do
    tools/mkimage --conf boot/limine-initramfs.conf --add "$w/$p.cpio" initramfs.cpio "$w/native/kmain_console.elf" "$w/native/console-$p.iso"
done
tests/mpx3-console --images "$w" --tier native --firmware both
python3 -I tools/usb-typing mpx3-console --tier native --firmware both
' 9>&-
