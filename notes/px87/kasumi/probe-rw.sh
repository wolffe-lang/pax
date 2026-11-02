#!/usr/bin/env bash
# px87 probe: kmain_screen at a commit, built native, its read watch on each firmware.
#   probe-rw.sh WORKTREE OUTDIR CAP [WORD]   (WORD: a kernel command-line word for the ISO, optional)
set -euo pipefail
W=$1 OUT=$2 CAP=$3 WORD=${4:-}
L=/home/mfwolffe/lanes/px87
cd "$W"
export PAX_CACHE=$L/cache PAX_BUILD=$OUT TMPDIR=$L/tmp
mkdir -p "$OUT/native"
printf 'commit %s\n' "$(git rev-parse HEAD)"
export PAX_WOLF=$(tools/fetch-wolf)
tools/fetch-limine >/dev/null
elf=$(tools/build-kernel --src kernel/kmain_screen.lu "$OUT/native")
conf=$PWD/boot/limine.conf
if [ -n "$WORD" ]; then
    cp boot/limine.conf "$OUT/word.conf"
    printf '\n    cmdline: %s\n' "$WORD" >> "$OUT/word.conf"
    conf=$OUT/word.conf
fi
tools/mkimage --conf "$conf" "$elf" "$OUT/native/kmain_screen.iso" >/dev/null
sha256sum "$elf" "$OUT/native/kmain_screen.iso"
nm -n "$elf" | grep -E ' (pax_fb_fill|pax_fb_copy|pax_halt)$'
port=12350
for fw in bios uefi; do
    port=$((port + 1))
    start=$SECONDS
    rc=0
    python3 tests/mpx3-screen.d/readwatch.py --elf "$elf" --firmware "$fw" --serial "$OUT/rw-$fw.serial.log" \
        --port "$port" --cap "$CAP" --timeout 1500 "$OUT/native/kmain_screen.iso" || rc=$?
    printf 'probe %s: exit %s in %s s\n' "$fw" "$rc" "$((SECONDS - start))"
    tr -d '\r' < "$OUT/rw-$fw.serial.log" | grep -aE '^(screen|scroll|timer): ' || true
done
