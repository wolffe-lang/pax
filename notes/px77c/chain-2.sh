#!/usr/bin/env bash
# px77c: the Linux spelling oracle (again: run1's ide-hd drives were read-only, which QEMU refuses),
# the macOS-edited copy's ESP, leg B (kasumi tonight: the target alone, the line written on macOS),
# the runbook's CachyOS step on a fresh copy, its ESP, then leg C (the leg reading the Linux-written line).
L=/home/mfwolffe/lanes/px77c
printf '%s\n' "$$" > "$L/chain-2.pid"
bash "$L/linux-oracle.sh" ident
bash "$L/esp-check.sh" "$L/copy-legB-mac.img" "$L/esp-check-legB-mac.txt"
bash "$L/leg.sh" B "$L/copy-legB-mac.img" tcg "$L/metal-onedisk.py"
cp "$L/out/pax-install-56b9f554.img" "$L/copy-legC-linux.img"
bash "$L/linux-oracle.sh" cachyos "$L/copy-legC-linux.img"
bash "$L/esp-check.sh" "$L/copy-legC-linux.img" "$L/esp-check-legC-linux.txt"
bash "$L/leg.sh" C "$L/copy-legC-linux.img" kvm "$L/metal-noappend.py"
printf '%s CHAIN-2 DONE\n' "$(date -u +%FT%TZ)"
