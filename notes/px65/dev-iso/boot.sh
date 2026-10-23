#!/usr/bin/env bash
# px65: px64's boot.sh (px62's), lane-local: hash the ISO twice, boot it with 2 GiB
# under TCG on CPUs 12-15 (QEMU 8.2.2 in the lane's own container), type
# dev.keys (mpx5-scent's session as root, `su pax`, the session again as
# pax, then px62's dev session from its `cd`), check both: px62's
# check-dev-session.py (wolf at the console) and check-scent-session.py
# (mpx5-scent's rows, twice, in order).
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px65/dev
printf '%s\n' $$ > "$L/boot.pid"
sha256sum "$L/out/pax-dev.iso"
sha256sum "$L/out/pax-dev.iso"
rm -rf "$L/dev-boot"; mkdir -p "$L/dev-boot"
t0=$(date +%s)
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" localhost/px65-ubuntu bash -c '
cd "$L/pax"
PAX_BUILD="$L/dev-boot" taskset -c 12-15 tools/qemu-halt --accel tcg --firmware bios \
 --serial "$L/dev-boot/dev.serial.log" --timeout 900 --qemu -m --qemu 2048M \
 --elf "$L/w/native/kmain_console.elf" --marker "halt|PANIC .*" \
 --type "$L/pax/notes/px64/dev-iso/dev.keys" --prompt "\$ " "$L/out/pax-dev.iso" > "$L/dev-boot/verdict.log" 2>&1
echo "qemu-halt rc=$?"
cat "$L/dev-boot/verdict.log"
python3 -I "$L/pax/notes/px62/dev-iso/check-dev-session.py" "$L/dev-boot/dev.serial.log"; echo "check-dev-session rc=$?"
python3 -I "$L/pax/notes/px64/dev-iso/check-scent-session.py" "$L/pax" "$L/dev-boot/dev.serial.log"; echo "check-scent-session rc=$?"
'
echo "boot.sh done $(( $(date +%s) - t0 ))s $(date -Is)"
