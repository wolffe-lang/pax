#!/usr/bin/env bash
# notes/px129/rig/qemu-legs.sh OUT LEG... — px129's QEMU measurement of the console, from a checkout
# of the commit under test, inside the px75-ubuntu image (QEMU, OVMF, gcc; KVM passed in): build the
# console kernel (kmain_console, native tier), conspeed (tools/mkconspeed) and one image a mode and
# scroll way, with conspeed as init over the committed streams (tests/mpx3-conspeed.d/streams), then
# boot each LEG and read its table off the screen (screen-run.py beside this file).
#   LEG  ACCEL:WxH:WAY[:serial]   ACCEL kvm or tcg; WAY fbwrite (the metal's scroll: redraw) or probe
#        (the kernel's own choice at attach; QEMU's framebuffer reads cheap, so it copies);
#        `serial` boots with COM1 to a file (the harness's machine) instead of none (the metal's)
# Writes OUT/<leg>.{txt,ppm,qemu.log} and OUT/legs.txt (a line a leg: its exit, seconds, the
# table's sha256). Exit 0 when every leg's init ended, else 1; 2 on a build error.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=${1:?OUT}; shift
mkdir -p "$out"
out=$(cd "$out" && pwd)
PAX_WOLF=$(tools/fetch-wolf | tail -n 1) || exit 2
export PAX_WOLF
tools/fetch-limine > /dev/null || exit 2
elf=$(tools/build-kernel --src kernel/kmain_console.lu "$out/k" 2> "$out/build-kernel.log") || { cat "$out/build-kernel.log"; exit 2; }
echo "kernel: $elf $(sha256sum < "$elf" | cut -c1-64)"
tools/mkconspeed "$out/bin" || exit 2
S=tests/mpx3-conspeed.d/streams
files=(/bin/conspeed="$out/bin/conspeed":755 /etc/pax-run="$out/pax-run":644)
for f in $(cd "$S" && find . -type f | sort); do files+=("/streams/${f#./}=$S/${f#./}:644"); done
printf '%s\n' "/bin/conspeed /streams/fuss /streams/fussopen /streams/cub" > "$out/pax-run"
tools/mkinitramfs "$out/conspeed.cpio" "${files[@]}" > "$out/initramfs.txt" || exit 2
tail -n 1 "$out/initramfs.txt"
rc=0
: > "$out/legs.txt"
for leg in "$@"; do
    IFS=: read -r accel mode way com <<< "$leg"
    name=$accel-$mode-$way${com:+-$com}
    conf=$out/$mode-$way.conf
    iso=$out/$mode-$way.iso
    if [ ! -f "$iso" ]; then
        cp boot/limine-initramfs.conf "$conf"
        printf '\n    resolution: %s\n' "$mode" >> "$conf"
        [ "$way" = fbwrite ] && printf '    cmdline: fbwrite\n' >> "$conf"
        tools/mkimage --conf "$conf" --add "$out/conspeed.cpio" initramfs.cpio "$elf" "$iso" > /dev/null || exit 2
    fi
    ser=(); [ "$com" = serial ] && ser=(--serial "$out/$name.serial.log")
    t0=$SECONDS
    python3 -I "$here/screen-run.py" --qemu-run tools/qemu-run --iso "$iso" --mode "$mode" --accel "$accel" \
        --font font/spleen-8x16.bdf --out "$out/$name" --timeout 1500 ${ser[@]+"${ser[@]}"}
    lrc=$?
    [ "$lrc" = 0 ] || rc=1
    printf '%s exit=%s secs=%s table=%s\n' "$name" "$lrc" "$((SECONDS - t0))" "$(sha256sum < "$out/$name.txt" | cut -c1-64)" >> "$out/legs.txt"
    echo "--- $name (exit $lrc)"
    grep -A 30 '^conspeed 1' "$out/$name.txt"
done
cat "$out/legs.txt"
exit "$rc"
