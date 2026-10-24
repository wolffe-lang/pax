#!/usr/bin/env bash
# px68, kasumi only: the replay's time at boot (the prediction's last
# open row). A journal-suite cut disk (`mounts churn 1500`) killed S s
# after `churn: begin`, then booted again with init=/bin/mounts under
# QEMU's trace with host timestamps; notes/px68/replay-time.py reads the
# span. CPUs 0-3 (the caller holds the lock).
#   replay-time.sh ELF CUT-IMG OUT [S...]   (default S: 7 15 25)
set -uo pipefail
L=$HOME/lanes/px68; T=${PAX_TREE:-$L/pax}
elf=$1 cut=$2 out=$3; shift 3
[ $# -gt 0 ] || set -- 7 15 25
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp PAX_BUILD=$out
ulimit -c 0
mkdir -p "$out"
cd "$T"
for s in "$@"; do
    d=$out/rt$s.img
    cp --sparse=always "$cut" "$d"
    log=$out/rt$s-cut.serial.log
    rm -f "$log" "$log.qpid"
    taskset -c 0-3 tools/qemu-run --firmware bios --serial "$log" --timeout 300 --boot-disk "$d" -- -m 512M -pidfile "$log.qpid" > "$log.verdict" 2>&1 &
    qp=$!
    t0=
    for _ in $(seq 1 6000); do
        if [ -z "$t0" ] && grep -aq 'churn: begin' "$log" 2>/dev/null; then t0=$(date +%s%N); fi
        if [ -n "$t0" ] && [ $(( $(date +%s%N) - t0 )) -ge $((s * 1000000000)) ]; then
            kill -9 "$(cat "$log.qpid")" 2>/dev/null || true
            break
        fi
        kill -0 "$qp" 2>/dev/null || break
        sleep 0.05
    done
    wait "$qp" 2>/dev/null || true
    p1=$(tools/mkgpt --print "$d" | awk '$1 == 1 { split($4, r, "-"); print r[1] }')
    p2=$(tools/mkgpt --print "$d" | awk '$1 == 2 { split($4, r, "-"); print r[1] }')
    c=$out/rt$s.conf
    SOURCE_DATE_EPOCH=1 tools/disktools "$out" mcopy -n -i "rt$s.img@@$((p1 * 512))" ::/boot/limine/limine.conf "rt$s.conf" > /dev/null 2>&1
    sed -i -E 's/^(\s*(kernel_)?cmdline:.*)$/\1 init=\/bin\/mounts/' "$c"
    SOURCE_DATE_EPOCH=1 tools/disktools "$out" mcopy -o -m -i "rt$s.img@@$((p1 * 512))" "rt$s.conf" ::/boot/limine/limine.conf > /dev/null 2>&1
    rm -f "$c"
    log=$out/rt$s.serial.log
    taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$log" --timeout 300 --qemu -m --qemu 512M --elf "$elf" \
        --marker 'halt|PANIC .*' --boot-disk --qemu -msg --qemu timestamp=on \
        --qemu -trace --qemu virtio_blk_handle_write --qemu -trace --qemu virtio_blk_handle_read \
        --qemu -trace --qemu virtio_blk_req_complete --qemu -D --qemu "$out/rt$s.trace" "$d" > "$log.verdict" 2>&1
    echo "killed $s s in, after op $(grep -a '^churn: [0-9]' "$out/rt$s-cut.serial.log" | tail -n 1 | cut -d' ' -f2): $(grep -a -m1 'recovering the journal' "$log" | tr -d '\r')"
    # The trace is kept when it could not be read (2026-10-24's run lost
    # QEMU 11.1.2's lines by deleting them).
    python3 notes/px68/replay-time.py "$out/rt$s.trace" "$d" $((p2 * 512)) && rm -f "$out/rt$s.trace"
    rm -f "$d"
done
