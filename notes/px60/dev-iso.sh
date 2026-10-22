#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
printf '%s\n' $$ > "$L/dev-iso.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/dev-iso.status; exit "$s"' EXIT
bash "$L/assemble.sh"
sha256sum "$L/out/pax-dev.iso"
sha256sum "$L/out/pax-dev.iso"
mkdir -p "$L/dev-boot"
cd "$L/pax"
PAX_BUILD="$L/dev-boot" taskset -c 0-3 tools/qemu-halt --accel tcg --firmware bios \
 --serial "$L/dev-boot/dev.serial.log" --timeout 900 --qemu -m --qemu 2048M \
 --elf "$L/w/native/kmain_console.elf" --marker 'halt|PANIC .*' \
 --type "$L/dev.keys" --prompt '$ ' "$L/out/pax-dev.iso" > "$L/dev-boot/verdict.log" 2>&1
cat "$L/dev-boot/verdict.log"
# A prompt, typed source or a halt alone is not execution evidence.
python3 -I "$L/pax/notes/px60/check-dev-session.py" "$L/dev-boot/dev.serial.log"
