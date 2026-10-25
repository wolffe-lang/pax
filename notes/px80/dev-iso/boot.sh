#!/usr/bin/env bash
# px80 (px65's boot.sh, px64's, px62's): hash the dev ISO twice, boot it with
# 2 GiB under TCG on the kasumi host (tools/qemu-halt, CPUs 0-3), type
# dev.keys (px64's: mpx5-scent's session as root, `su pax`, the session again
# as pax, then px62's dev session from its `cd`; px80 adds `ld.lld --version`
# after `wolf --version`), and check it: px62's
# check-dev-session.py (hello built and linked on PAX by the ISO's toolchain,
# run as uid 1000), px64's check-scent-session.py, and px80's
# check-linker.py (the ISO's linker says LLD 18.1.8 on PAX).
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px80/dev
printf '%s\n' $$ > "$L/boot.pid"
sha256sum "$L/out/pax-dev.iso"
sha256sum "$L/out/pax-dev.iso"
rm -rf "$L/dev-boot"; mkdir -p "$L/dev-boot"
t0=$(date +%s)
cd "$L/pax"
rc=0
PAX_BUILD="$L/dev-boot" taskset -c 0-3 tools/qemu-halt --accel tcg --firmware bios \
 --serial "$L/dev-boot/dev.serial.log" --timeout 900 --qemu -m --qemu 2048M \
 --elf "$L/w/native/kmain_console.elf" --marker "halt|PANIC .*" \
 --type "$L/pax/notes/px80/dev-iso/dev.keys" --prompt "\$ " "$L/out/pax-dev.iso" > "$L/dev-boot/verdict.log" 2>&1 || rc=$?
echo "qemu-halt rc=$rc"
cat "$L/dev-boot/verdict.log"
c=0
python3 -I "$L/pax/notes/px62/dev-iso/check-dev-session.py" "$L/dev-boot/dev.serial.log" || c=1
python3 -I "$L/pax/notes/px64/dev-iso/check-scent-session.py" "$L/pax" "$L/dev-boot/dev.serial.log" || c=1
python3 -I "$L/pax/notes/px80/dev-iso/check-linker.py" "$L/dev-boot/dev.serial.log" || c=1
echo "checks rc=$c"
echo "boot.sh done $(( $(date +%s) - t0 ))s $(date -Is)"
[ "$rc" = 0 ] && [ "$c" = 0 ]
