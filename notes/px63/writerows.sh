#!/usr/bin/env bash
# px63, kasumi only: the write rows by hand before the suite: one
# starting image, the write session on the Linux guest and on PAX (each
# on its own copy), e2fsck -fn of both, the session outputs compared and
# the two trees compared (tools/e2tree; times relative to each session's
# own clock line, within a second).
#   writerows.sh RUN [fstab-options]
set -euo pipefail
L=$HOME/lanes/px63
run=${1:-w1}; opts=${2:-defaults}
printf '%s\n' $$ > "$L/writerows-$run.pid"
ulimit -c 0
B=$L/runs/$run; rm -rf "$B"; mkdir -p "$B/bin" "$B/tree/pre"
W=$HOME/lanes/orch-paxplay/w
for u in ls cat stat readlink wc head tail echo mkdir rm rmdir mv cp ln touch chmod chown; do strip -o "$B/bin/$u" "$W/bore/$u"; done
strip -o "$B/bin/sh" "$W/pelt/pelt"
podman run --rm --cpuset-cpus 0-3 -v "$L:$L:Z" localhost/px13-ubuntu bash -c "cd $L/pax && tools/mkdiskprobe $B/bin" > "$B/probe.txt"
printf 'kept\n' > "$B/tree/pre/kept.txt"; printf 'gone\n' > "$B/tree/pre/gone.txt"
SOURCE_DATE_EPOCH=1700000000 "$L/pax/tools/mkdisk" --from "$B/tree" --label pax-write 64M "$B/start.img" > "$B/mkdisk.txt"
cp "$B/start.img" "$B/linux.img"
t0=$(date +%s)
taskset -c 0-3 "$L/pax/tools/linux-blk" --busybox "$L/bin/busybox" --file "$L/pax/tests/mpx6-ext2.d/write.sh=/etc/disk/write.sh" \
    "$B/linux" "$B/linux.img" "$B"/bin/* -- "/bin/sh /etc/disk/write.sh" > "$B/linux.txt" 2>&1 || echo "linux-blk rc=$?" >> "$B/summary"
echo "linux guest in $(( $(date +%s) - t0 )) s" >> "$B/summary"
"$L/pax/tools/e2fs" "$B" e2fsck -fn linux.img > "$B/linux.fsck" 2>&1 && echo "linux image: e2fsck clean" >> "$B/summary" || echo "linux image: e2fsck rc=$?" >> "$B/summary"
"$L/pax/tools/e2tree" "$B/linux.img" > "$B/linux.tree"
IMAGE=$B/start.img "$L/pax/notes/px63/devboot.sh" "$run-pax" "$L/pax/tests/mpx6-ext2.d/write.sh" "" "$opts" > "$B/pax.txt" 2>&1 || echo "devboot rc=$?" >> "$B/summary"
cat "$L/runs/$run-pax/summary" >> "$B/summary"
cp "$L/runs/$run-pax/disk.img" "$B/pax.img"
"$L/pax/tools/e2tree" "$B/pax.img" > "$B/pax.tree"
python3 "$L/pax/notes/px63/compare.py" "$L/runs/$run-pax/serial.log" "$B/linux/serial.log" "$B/session" >> "$B/summary" 2>&1 || true
python3 "$L/pax/notes/px63/treecmp.py" "$B/session.pax" "$B/pax.tree" "$B/session.linux" "$B/linux.tree" >> "$B/summary" 2>&1 || true
echo done >> "$B/summary"
