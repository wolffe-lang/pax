#!/bin/bash
# px65, kasumi: the playground end to end at one tree commit, as px63
# made it (notes/px65/play/): build, assemble with a TEST disk (never
# the maintainer's pax-home.img), boot with the maintainer's session;
# then, since px66, the playground disk from the same build
# (notes/px65/disk/): pax-disk.img assembled twice (cmp), booted from a
# copy under SeaBIOS and under the Mac's edk2 code file as a read-only
# pflash ($L/edk2-x86_64-code.fd, copied from nomad-1).
#   play-all.sh COMMIT
set -u
L=$HOME/lanes/px65/play
C=$1
printf '%s\n' $$ > "$HOME/lanes/px65/play-all.pid"
mkdir -p "$L"
rm -rf "$L/pax"; git clone -q "$HOME/lanes/px65/pax" "$L/pax" && git -C "$L/pax" checkout -q --detach "$C" || exit 2
export PX65_TREE=$L/pax PX65_HEAD=$(git -C "$L/pax" rev-parse --short=8 HEAD) PX65_EPOCH=$(git -C "$L/pax" log -1 --format=%ct)
echo "tree $(git -C "$L/pax" rev-parse HEAD) $PX65_EPOCH"
t0=$(date +%s); bash "$L/pax/notes/px65/play/build.sh" > "$L/build.log" 2>&1; echo "build rc=$? $(( $(date +%s) - t0 ))s"; tail -n 6 "$L/build.log"
t0=$(date +%s); bash "$L/pax/notes/px65/play/assemble.sh" --disk 128M > "$L/assemble.log" 2>&1; echo "assemble rc=$? $(( $(date +%s) - t0 ))s"; tail -n 8 "$L/assemble.log"
t0=$(date +%s); bash "$L/pax/notes/px65/play/boot.sh" > "$L/boot.log" 2>&1; echo "boot rc=$? $(( $(date +%s) - t0 ))s"; tail -n 16 "$L/boot.log"
t0=$(date +%s); bash "$L/pax/notes/px65/disk/assemble.sh" > "$L/disk-assemble.log" 2>&1; echo "disk assemble rc=$? $(( $(date +%s) - t0 ))s"; tail -n 8 "$L/disk-assemble.log"
cp "$L/out-disk/pax-disk.img" "$L/pax-disk.first.img"
t0=$(date +%s); bash "$L/pax/notes/px65/disk/assemble.sh" > "$L/disk-assemble2.log" 2>&1; echo "disk assemble (second) rc=$? $(( $(date +%s) - t0 ))s"
cmp "$L/pax-disk.first.img" "$L/out-disk/pax-disk.img" && echo "disk: the second tools/mkdisk --gpt byte-identical"; rm -f "$L/pax-disk.first.img"
sha256sum "$L/out-disk/pax-disk.img"; sha256sum "$L/out-disk/pax-disk.img"
t0=$(date +%s); bash "$L/pax/notes/px65/disk/boot.sh" bios uefi > "$L/disk-boot.log" 2>&1; echo "disk boot rc=$? $(( $(date +%s) - t0 ))s"; cat "$L/disk-boot.log" | grep -v "^session: "
echo "play-all done $(date -Is)"
