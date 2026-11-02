#!/usr/bin/env bash
# px87: tests/mpx6-install.d/asuser.py alone, its inputs built directly at the worktree's commit
# (the suite builds the same ones through mpx6-disktools --only build; the gauntlet runs the suite whole).
#   probe-asuser.sh BUILD_DIR   (run by run.sh inside the worktree)
set -euo pipefail
B=$1
rm -rf "$B/full" "$B/gate" "$B/su" "$B/k" "$B/asuser"
mkdir -p "$B/full" "$B/k"
export SOURCE_DATE_EPOCH=1700000000
tools/fetch-limine > /dev/null
tools/mkpelt "$B/full/pelt" > "$B/pelt.log" 2>&1
tools/mkdiskprobe "$B/full/probe" > "$B/probe.log" 2>&1
tools/mkinstall "$B/gate" > "$B/gate.log" 2>&1
tools/mksu "$B/su" > "$B/su.log" 2>&1
elf=$(tools/build-kernel --src kernel/kmain_console.lu "$B/k" 2> "$B/k.log")
sha256sum "$B/full/pelt/pelt" "$B/full/probe/reboot" "$B/gate/pax-install" "$B/su/su" "$elf"
python3 -I tests/mpx6-install.d/asuser.py "$PWD" "$B/asuser" "$B/gate" "$B/full" "$B/su" "$elf"
