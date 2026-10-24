#!/bin/bash
# px67, kasumi: how long from QEMU's start to the kernel's console line
# (`PAX: the console`, px66's mark) and to the first prompt (`$ `), the
# same kernel and the same system (the playground's archive and
# kmain_console), from px66's disk (`tools/mkdisk --gpt --initramfs`:
# the initramfs on the ESP, read by the firmware, `/` in memory) and
# from px67's (`--gpt --root`: no initramfs, `/` on partition 2), five
# boots each, SeaBIOS and OVMF, TCG, CPUs 0-3 (kasumi has no /dev/kvm:
# KVM is not measured here). Each boot is killed by its pid once the
# prompt is seen.
#   timing.sh INITRAMFS-DISK ROOT-DISK
set -u
code=/usr/share/edk2/x64/OVMF_CODE.4m.fd
vars=/usr/share/edk2/x64/OVMF_VARS.4m.fd
W=$(mktemp -d "${TMPDIR:-/tmp}/px67-timing.XXXXXX")
one() { # fw disk -> "console prompt" seconds
    local fw=$1 disk=$2 fwargs=()
    cp "$vars" "$W/vars.fd"; cp --sparse=always "$disk" "$W/boot.img"
    [ "$fw" = uefi ] && fwargs=(-drive "if=pflash,format=raw,unit=0,readonly=on,file=$code" -drive "if=pflash,format=raw,unit=1,file=$W/vars.fd")
    : > "$W/serial"
    local t0 t1= t2=
    t0=$(date +%s.%N)
    taskset -c 0-3 qemu-system-x86_64 -machine q35 -cpu max -m 512M -accel tcg -display none -monitor none -nic none \
        -serial "file:$W/serial" "${fwargs[@]}" -drive "file=$W/boot.img,if=none,id=d0,format=raw" \
        -device virtio-blk-pci,drive=d0,bootindex=0 < /dev/null > /dev/null 2>&1 &
    local q=$! n=0
    while kill -0 "$q" 2>/dev/null && [ $n -lt 6000 ]; do
        if [ -z "$t1" ] && grep -aq 'PAX: the console' "$W/serial"; then t1=$(date +%s.%N); fi
        if [ -n "$t1" ] && grep -aq '\$ ' "$W/serial"; then t2=$(date +%s.%N); break; fi
        sleep 0.01; n=$((n + 1))
    done
    kill "$q" 2>/dev/null; wait "$q" 2>/dev/null
    printf '%s %s\n' "$(echo "${t1:-0} - $t0" | bc)" "$(echo "${t2:-0} - $t0" | bc)"
}
for fw in bios uefi; do
    for d in "$1" "$2"; do
        cs=() ps=()
        for k in 1 2 3 4 5; do read -r c p < <(one "$fw" "$d"); cs+=("$c"); ps+=("$p"); done
        printf '%s %s: console %s median %s s; prompt %s median %s s\n' "$fw" "${d##*/}" "${cs[*]}" \
            "$(printf '%s\n' "${cs[@]}" | sort -n | sed -n 3p)" "${ps[*]}" "$(printf '%s\n' "${ps[@]}" | sort -n | sed -n 3p)"
    done
done
rm -rf "$W"
