#!/usr/bin/env bash
# px62: px60's dev-iso.sh boot, lane-local: hash the ISO twice, boot it
# with 2 GiB under TCG on CPUs 0-3, type dev.keys (px60's session and
# `cd /bin; ../home/pax; pwd`), check it.
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px62/dev
printf '%s\n' $$ > "$L/boot.pid"
sha256sum "$L/out/pax-dev.iso"
sha256sum "$L/out/pax-dev.iso"
rm -rf "$L/dev-boot"; mkdir -p "$L/dev-boot"
cd "$L/pax"
PAX_BUILD="$L/dev-boot" taskset -c 0-3 tools/qemu-halt --accel tcg --firmware bios \
 --serial "$L/dev-boot/dev.serial.log" --timeout 900 --qemu -m --qemu 2048M \
 --elf "$L/w/native/kmain_console.elf" --marker 'halt|PANIC .*' \
 --type "$L/pax/notes/px62/dev-iso/dev.keys" --prompt '$ ' "$L/out/pax-dev.iso" > "$L/dev-boot/verdict.log" 2>&1 || true
cat "$L/dev-boot/verdict.log"
python3 -I "$L/pax/notes/px62/dev-iso/check-dev-session.py" "$L/dev-boot/dev.serial.log"
