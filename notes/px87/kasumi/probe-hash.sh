#!/usr/bin/env bash
# px87: what kernel/identity's boot-time SHA-256 costs, under TCG: kmain_console at the head (WITH) and the
# same commit plus one local commit that drops `identity.report()` (WITHOUT, never pushed), each booted three
# times (BIOS, a run list of /bin/poweroff alone); the `boot:` line's milliseconds compared.
#   probe-hash.sh WITH_WORKTREE WITHOUT_WORKTREE BUILD_DIR REBOOT_BINARY   (inside the container)
set -euo pipefail
WI=$1 WO=$2 B=$3 RB=$4
L=/home/mfwolffe/lanes/px87
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
rm -rf "$B"; mkdir -p "$B"
printf '/bin/poweroff\n' > "$B/run"
for v in with without; do
    W=$WI; [ "$v" = without ] && W=$WO
    cd "$W"
    export PAX_WOLF=$(tools/fetch-wolf)
    tools/fetch-limine > /dev/null
    printf '%s at %s\n' "$v" "$(git rev-parse HEAD)"
    elf=$(tools/build-kernel --src kernel/kmain_console.lu "$B/$v" 2> "$B/$v.build.log")
    tools/mkinitramfs "$B/$v.cpio" "/bin/poweroff=$RB:755" "/etc/pax-run=$B/run:644" > /dev/null
    tools/mkimage --conf boot/limine-initramfs.conf --add "$B/$v.cpio" initramfs.cpio "$elf" "$B/$v.iso" > /dev/null
    for k in 1 2 3; do
        tools/qemu-run --firmware bios --accel tcg --timeout 120 --serial "$B/$v-$k.log" "$B/$v.iso" || true
        printf '%s %s: %s | %s\n' "$v" "$k" "$(tr -d '\r' < "$B/$v-$k.log" | grep -a -m1 '^kernel: ' | cut -c1-60)" "$(tr -d '\r' < "$B/$v-$k.log" | grep -a -m1 '^boot: ')"
    done
done
