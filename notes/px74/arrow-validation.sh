#!/usr/bin/env bash
# Extend the raw-input oracle to every Shift+arrow, including pack's Shift+Down.
# Reuse only the already validated kernel ELFs; compile the changed C probe.
set -euo pipefail
L=/home/mfwolffe/lanes/px74
printf '%s\n' "$$" > "$L/runs/arrow-validation.pid"
exec > "$L/runs/arrow-validation.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$L/runs/arrow-validation.exit"' EXIT
printf 'arrow validation queued %s\n' "$(date -Is)"
exec 9>/home/mfwolffe/lanes/kasumi-cores-12-15.lock; flock 9
podman run --rm --memory 12g --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e PAX_BUILD="$L/arrow-build" -e TMPDIR="$L/tmp" \
    -e SOURCE_DATE_EPOCH=1700000000 -e PAX_REQUIRE_UEFI=1 \
    -w "$L/pax" localhost/px80-ubuntu taskset -c 12-15 "$L/in.sh" bash -c '
set -euo pipefail
L=/home/mfwolffe/lanes/px74
w=$PAX_BUILD
mkdir -p "$w"
cc -static -O1 -Wall -Wextra -o "$w/usbkeys" user/elf/usbkeys.c
printf "/bin/usbkeys\n" > "$w/run"
tools/mkinitramfs "$w/probe.cpio" "/bin/usbkeys=$w/usbkeys" "/etc/pax-run=$w/run" "/usbkeys=$w/usbkeys"
for tier in native release; do
    tools/mkimage --conf boot/limine-initramfs.conf --add "$w/probe.cpio" initramfs.cpio \
        "$L/final-build/mpx6-usb/$tier/kmain_console.elf" "$w/$tier.iso"
done
python3 -I tools/usb-session --image "$w/native.iso" --initrd "$w/probe.cpio" \
    --linux-kernel "$L/linux/vmlinuz" --output "$w/linux" --topology root --firmware bios
for tier in native release; do
    for firmware in bios uefi; do
        for topology in root hub nested; do
            python3 -I tools/usb-session --image "$w/$tier.iso" --reference "$w/linux/rows.txt" \
                --output "$w/$tier/$firmware-$topology" --topology "$topology" --firmware "$firmware"
        done
    done
done
sha256sum "$w/usbkeys" "$L/final-build/mpx6-usb/native/kmain_console.elf" "$L/final-build/mpx6-usb/release/kmain_console.elf"
' 9>&-
printf 'arrow validation complete %s\n' "$(date -Is)"
