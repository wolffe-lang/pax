#!/bin/bash
# px66, kasumi: how long from QEMU's start to the kernel's first line
# (`PAX: the console`), the same kernel and initramfs (tests/mpx6-part's
# boot session) from the ISO with a bare ext2 disk beside it and from the
# GPT disk alone, five boots each, SeaBIOS and OVMF, TCG, CPUs 0-3 (kasumi
# has no /dev/kvm: KVM is not measured here). Each boot is killed by its
# pid once the line is seen.
#   timing.sh BUILDDIR   (a tests/mpx6-part build: native/part-iso.iso,
#                         native/home.img, native/boot.img)
set -u
B=$1/native
code=/usr/share/edk2/x64/OVMF_CODE.4m.fd
vars=/usr/share/edk2/x64/OVMF_VARS.4m.fd
W=$(mktemp -d "${TMPDIR:-/tmp}/px66-timing.XXXXXX")
one() { # fw how -> seconds to the first line
    local fw=$1 how=$2 fwargs=() media=()
    cp "$vars" "$W/vars.fd"; cp "$B/home.img" "$W/home.img"; cp "$B/boot.img" "$W/boot.img"
    [ "$fw" = uefi ] && fwargs=(-drive "if=pflash,format=raw,unit=0,readonly=on,file=$code" -drive "if=pflash,format=raw,unit=1,file=$W/vars.fd")
    if [ "$how" = iso ]; then
        media=(-drive "file=$B/part-iso.iso,format=raw,media=cdrom,readonly=on" -boot d -drive "file=$W/home.img,if=none,id=d0,format=raw" -device virtio-blk-pci,drive=d0)
    else
        media=(-drive "file=$W/boot.img,if=none,id=d0,format=raw" -device virtio-blk-pci,drive=d0,bootindex=0)
    fi
    : > "$W/serial"
    local t0 t1
    t0=$(date +%s.%N)
    taskset -c 0-3 qemu-system-x86_64 -machine q35 -cpu max -m 512M -accel tcg -display none -monitor none -nic none \
        -serial "file:$W/serial" "${fwargs[@]}" "${media[@]}" < /dev/null > /dev/null 2>&1 &
    local q=$!
    while ! grep -aq 'PAX: the console' "$W/serial"; do sleep 0.01; kill -0 "$q" 2>/dev/null || break; done
    t1=$(date +%s.%N)
    kill "$q" 2>/dev/null; wait "$q" 2>/dev/null
    echo "$t1 - $t0" | bc
}
for fw in bios uefi; do
    for how in iso disk; do
        ts=()
        for k in 1 2 3 4 5; do ts+=("$(one "$fw" "$how")"); done
        printf '%s %s: %s  median %s s\n' "$fw" "$how" "${ts[*]}" "$(printf '%s\n' "${ts[@]}" | sort -n | sed -n 3p)"
    done
done
rm -rf "$W"
