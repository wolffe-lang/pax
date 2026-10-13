#!/bin/bash
# px38, on kasumi: boot PAX at trunk, unchanged, with one probe (probes/ids, or probes/priv) as its
# first program, and keep what it wrote. Nothing in the pax tree is
# changed: the kernel is kernel/kmain_console.lu built by the tree's own
# tools at its own pin, the image an initramfs of the probe, /etc/pax-run
# and the two account files the shell image has.
#
#   pax-boot.sh PAXROOT BINDIR OUTDIR [PROBE]
#
# PROBE: ids (the default) or priv; the files below are named for it.
# PAXROOT: a pax tree at the commit under test. BINDIR: the static
# probes. OUTDIR gets pax-PROBE.serial.log (the whole console),
# pax-PROBE.txt (the program's own lines) and pax-PROBE.kernel.txt (the
# kernel's `user:` lines: every -ENOSYS and every refusal by name).
set -uo pipefail
pax=$(cd "$1" && pwd) bin=$(cd "$2" && pwd) out=$3 probe=${4:-ids}
mkdir -p "$out"; out=$(cd "$out" && pwd)
export PAX_BUILD=$out/build PAX_CACHE=${PAX_CACHE:-$out/../cache} CARGO_INCREMENTAL=0
mkdir -p "$PAX_BUILD" "$PAX_CACHE"
wolf=$("$pax/tools/fetch-wolf" | tail -n 1) || exit 2
export PAX_WOLF=$wolf
"$pax/tools/fetch-limine" || exit 2
r=$PAX_BUILD/root
rm -rf "$r"; mkdir -p "$r/bin" "$r/etc"
cp "$bin/$probe" "$r/bin/$probe"
printf 'root:x:0:0:root:/:/bin/pelt\n' > "$r/etc/passwd"
printf 'root:x:0:\n' > "$r/etc/group"
echo "/bin/$probe /px38w" > "$r/etc/pax-run"
"$pax/tools/mkinitramfs" "$PAX_BUILD/$probe.cpio" "/bin/$probe=$r/bin/$probe:755" "/etc/passwd=$r/etc/passwd:644" "/etc/group=$r/etc/group:644" \
    "/etc/pax-run=$r/etc/pax-run:644" > "$out/pax-$probe.initramfs.txt" || exit 2
elf=$("$pax/tools/build-kernel" --src "$pax/kernel/kmain_console.lu" "$PAX_BUILD/native" 2> "$out/pax-$probe.build-kernel.log") || { tail -n 20 "$out/pax-$probe.build-kernel.log" >&2; exit 2; }
"$pax/tools/mkimage" --conf "$pax/boot/limine-initramfs.conf" --add "$PAX_BUILD/$probe.cpio" initramfs.cpio "$elf" "$PAX_BUILD/$probe.iso" > /dev/null || exit 2
log=$out/pax-$probe.serial.log
rm -f "$log"
"$pax/tools/qemu-halt" --firmware bios --serial "$log" --timeout 300 --qemu -m --qemu 256M --elf "$elf" --marker 'halt|PANIC .*' "$PAX_BUILD/$probe.iso" \
    > "$out/pax-$probe.verdict" 2>&1
rc=$?
. "$pax/tools/lib.sh"
serial_norm "$log" > "$out/pax-$probe.norm"
grep -a '^user: ' "$out/pax-$probe.norm" > "$out/pax-$probe.kernel.txt"
awk '/^user: exec pid 1 / { if (!on) { on = 1; next } } on && /^user: [^ ]+ pid 1 (exit_group|exit) [0-9]+ after / { exit }
     on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' "$out/pax-$probe.norm" > "$out/pax-$probe.txt"
{
    echo "pax: $(cd "$pax" && git rev-parse HEAD 2>/dev/null || cat "$pax/.px38-commit" 2>/dev/null)"
    echo "wolf: $("$wolf" --version | head -n 1)"
    echo "kernel: $(sha256sum "$elf" | cut -d' ' -f1)"
    echo "iso: $(sha256sum "$PAX_BUILD/$probe.iso" | cut -d' ' -f1)"
    echo "$probe: $(sha256sum "$bin/$probe" | cut -d' ' -f1)"
    echo "qemu-halt exit: $rc"
    sed -n 's/^accel: /accel: /p' "$log.meta" 2>/dev/null
} > "$out/pax-$probe.meta"
rm -rf "$PAX_BUILD"
[ "$rc" = 0 ] || { echo "pax-boot: qemu-halt exit $rc" >&2; tail -n 5 "$out/pax-$probe.verdict" >&2; exit 1; }
