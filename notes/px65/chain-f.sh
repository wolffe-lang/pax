#!/bin/bash
# px65, kasumi: after kasumi's crash at 21:41 (no shutdown record) killed
# chain E during the dev ISO's boot: what chain E finished is kept (the
# two cost runs, copied before the crash; the dev ISO's verify, build and
# assemble), the ISO, its smoke twin, the kernel and the edk2 file hashed
# again against what was printed before the crash, the dev clone checked
# clean, then only what died: the dev ISO's boot (boot.sh starts its
# dev-boot/ afresh: the half-written one is discarded) and the playground
# (play-all.sh, never started).   chain-f.sh COMMIT
L=$HOME/lanes/px65; D=$L/dev; C=$1
echo "chain-f: for $C, $(date -Is)"; uptime
sha256sum "$D/out/pax-dev.iso" "$D/out/pax-dev-smoke.iso" "$D/w/native/kmain_console.elf" "$L/play/edk2-x86_64-code.fd"
sha256sum "$D/out/pax-dev.iso" "$D/out/pax-dev-smoke.iso" "$D/w/native/kmain_console.elf" "$L/play/edk2-x86_64-code.fd"
echo "dev clone: $(git -C "$D/pax" rev-parse HEAD), $(git -C "$D/pax" status --porcelain | wc -l) changed paths"
[ "$(git -C "$D/pax" rev-parse HEAD)" = "$(git -C "$L/pax" rev-parse "$C")" ] || { echo "chain-f: the dev clone is not at $C"; exit 2; }
t0=$(date +%s); bash "$D/pax/notes/px65/dev-iso/boot.sh" > "$D/boot.log" 2>&1; echo "dev boot rc=$? $(( $(date +%s) - t0 ))s"; tail -n 14 "$D/boot.log"
t0=$(date +%s); bash "$L/w-e/notes/px65/play-all.sh" "$C" > "$L/out/play-all-f.txt" 2>&1; echo "play-all rc=$? $(( $(date +%s) - t0 ))s"
echo "chain-f: done $(date -Is)"
