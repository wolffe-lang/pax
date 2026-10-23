#!/usr/bin/env bash
# px63, kasumi only: the read rows by hand before the suite: the fixture
# image, the Linux guest's session (tools/linux-blk, kasumi's own Linux
# 7.2.8 under QEMU, read-only), PAX's (kmain_console, the fixture
# mounted read-only by /etc/fstab), and the two outputs compared.
#   readrows.sh RUN
set -euo pipefail
L=$HOME/lanes/px63
run=${1:-r1}
printf '%s\n' $$ > "$L/readrows-$run.pid"
ulimit -c 0
B=$L/runs/$run; rm -rf "$B"; mkdir -p "$B/bin"
W=$HOME/lanes/orch-paxplay/w
for u in ls cat stat readlink wc head tail echo; do strip -o "$B/bin/$u" "$W/bore/$u"; done
strip -o "$B/bin/sh" "$W/pelt/pelt"
podman run --rm --cpuset-cpus 0-3 -v "$L:$L:Z" localhost/px13-ubuntu bash -c "cd $L/pax && tools/mkdiskprobe $B/bin" > "$B/probe.txt"
t0=$(date +%s)
python3 "$L/pax/tests/mpx6-ext2.d/fixture" "$B/tree" > "$B/fixture.txt"
SOURCE_DATE_EPOCH=1700000000 "$L/pax/tools/mkdisk" --from "$B/tree" --attrs "$B/tree.attrs" --label pax-fixture 160M "$B/fixture.img" > "$B/mkdisk.txt"
rm -rf "$B/tree"
echo "fixture made in $(( $(date +%s) - t0 )) s" > "$B/summary"
cp "$B/fixture.img" "$B/linux.img"
t0=$(date +%s)
taskset -c 0-3 "$L/pax/tools/linux-blk" --ro --busybox "$L/bin/busybox" --file "$L/pax/tests/mpx6-ext2.d/read.sh=/etc/disk/read.sh" \
    "$B/linux" "$B/linux.img" "$B"/bin/* -- "/bin/sh /etc/disk/read.sh" > "$B/linux.txt" 2>&1 || echo "linux-blk rc=$?" >> "$B/summary"
echo "linux guest in $(( $(date +%s) - t0 )) s" >> "$B/summary"
cmp "$B/fixture.img" "$B/linux.img" && echo "linux left the image unchanged" >> "$B/summary"
IMAGE=$B/fixture.img "$L/pax/notes/px63/devboot.sh" "$run-pax" "$L/pax/tests/mpx6-ext2.d/read.sh" "" ro > "$B/pax.txt" 2>&1 || echo "devboot rc=$?" >> "$B/summary"
cat "$L/runs/$run-pax/summary" >> "$B/summary"
cmp "$B/fixture.img" "$L/runs/$run-pax/disk.img" && echo "PAX left the image unchanged" >> "$B/summary"
python3 "$L/pax/notes/px63/compare.py" "$L/runs/$run-pax/serial.log" "$B/linux/serial.log" "$B/session" >> "$B/summary" 2>&1 || true
echo done >> "$B/summary"
