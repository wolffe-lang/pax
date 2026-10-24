#!/usr/bin/env bash
# px68, kasumi only: the Linux guest (this host's kernel under QEMU, TCG)
# with its root on an ext3 partition (tools/linux-root --fstype), black
# box: what it says mounting a journalled root, a power cut's state, the
# replay at the next boot, a root named ext2, and an incompatible feature
# it does not know. The probe built in the baseline container. Writes
# $G/<run>/ and prints each run's lines.
#   guest.sh [RUN...]   (default: all)
set -uo pipefail
L=$HOME/lanes/px68; T=${PAX_TREE:-$L/pax}; G=$L/guest
mkdir -p "$G" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_ENGINE=podman TMPDIR=$L/tmp
cd "$T"
ulimit -c 0
if [ ! -x "$G/probe/mounts" ]; then
    podman run --rm --cpuset-cpus 0-3 -v "$L:$L:Z" localhost/px13-ubuntu bash -c "cd '$T' && tools/mkrootprobe '$G/probe'" || exit 2
fi
P=$G/probe/mounts
S=512
lr() { taskset -c 0-3 tools/linux-root "$@"; }
p2() { dd if="$1" of="$2" bs=$S skip=20480 count=49152 status=none; }
put2() { dd if="$2" of="$1" bs=$S seek=20480 conv=notrunc status=none; }
p4() { dd if="$1" of="$2" bs=$S skip=69632 count=16384 status=none; }
put4() { dd if="$2" of="$1" bs=$S seek=69632 conv=notrunc status=none; }
show() { echo "== $1"; grep -E 'EXT[234]-fs|JBD2|jbd2|VFS|recovery|Kernel panic|mounts: |^table: .* / |^/dev/root|churn: (begin|end)|killed' "$G/$1/serial.log" | head -n 40; cat "$G/$1/host.txt"; }
want() { [ $# -eq 0 ] || printf ' %s ' "$@" | grep -q " $R "; }
runs=" $* "
[ $# -eq 0 ] && runs=" g1 g1n g2 g3 g4 g5 g6 g7 "
for R in g1 g1n g2 g3 g4 g5 g6 g7; do
    case $runs in *" $R "*) ;; *) continue ;; esac
    rm -rf "$G/$R"; mkdir -p "$G/$R"
    case $R in
    g1) # a clean boot of a fresh ext3 root, rootfstype=ext3, the kernel's lines
        lr --fstype ext3 --append loglevel=7 "$G/g1" "$P" > "$G/g1/run.txt" 2>&1 ;;
    g1n) # the same disk again, rootfstype left out: which type the kernel names
        cp --sparse=always "$G/g1/disk.img" "$G/g1n/disk.img"
        lr --fstype none --append loglevel=7 --disk "$G/g1n/disk.img" "$G/g1n" "$P" > "$G/g1n/run.txt" 2>&1 ;;
    g2) # the same disk, rootfstype=ext2: the ext2 driver and a journal
        cp --sparse=always "$G/g1/disk.img" "$G/g2/disk.img"
        lr --fstype ext2 --append loglevel=7 --timeout 120 --disk "$G/g2/disk.img" "$G/g2" "$P" > "$G/g2/run.txt" 2>&1 ;;
    g3) # a power cut in a write session on a fresh ext3 root
        lr --fstype ext3 --append loglevel=7 --init-args "churn 1200" --kill 'churn: 900 ' "$G/g3" "$P" > "$G/g3/run.txt" 2>&1
        p2 "$G/g3/disk.img" "$G/g3/p2.img"
        tools/e2fs "$G/g3" dumpe2fs -h p2.img > "$G/g3/dumpe2fs.txt" 2>&1
        tools/e2fs "$G/g3" debugfs -R logdump p2.img > "$G/g3/logdump.txt" 2>&1
        rm -f "$G/g3/p2.img" ;;
    g4) # the next boot of g3's disk: the replay, then a clean end
        cp --sparse=always "$G/g3/disk.img" "$G/g4/disk.img"
        lr --fstype ext3 --append loglevel=7 --disk "$G/g4/disk.img" "$G/g4" "$P" > "$G/g4/run.txt" 2>&1
        p2 "$G/g4/disk.img" "$G/g4/p2.img"
        tools/e2fs "$G/g4" dumpe2fs -h p2.img > "$G/g4/dumpe2fs.txt" 2>&1
        rm -f "$G/g4/p2.img" ;;
    g5) # g3's disk repaired by the host's e2fsck -fy instead (the replay is e2fsck's)
        cp --sparse=always "$G/g3/disk.img" "$G/g5/disk.img"
        p2 "$G/g5/disk.img" "$G/g5/p2.img"
        tools/e2fs "$G/g5" e2fsck -fy p2.img > "$G/g5/e2fsck-fy.txt" 2>&1; echo "e2fsck -fy exit $?" >> "$G/g5/e2fsck-fy.txt"
        tools/e2fs "$G/g5" dumpe2fs -h p2.img > "$G/g5/dumpe2fs.txt" 2>&1
        tools/e2tree "$G/g5/p2.img" > "$G/g5/tree.txt"
        p2 "$G/g4/disk.img" "$G/g5/p2-g4.img"
        tools/e2tree "$G/g5/p2-g4.img" > "$G/g5/tree-g4.txt"
        rm -f "$G/g5/p2.img" "$G/g5/p2-g4.img"
        printf '' > "$G/g5/serial.log"; printf 'trees under /churn, e2fsck -fy against the guest replay: %s\n' \
            "$(diff <(grep '^/churn' "$G/g5/tree.txt" | cut -f1-8,10-12) <(grep '^/churn' "$G/g5/tree-g4.txt" | cut -f1-8,10-12) > "$G/g5/tree.diff" && echo same || echo "differ ($(wc -l < "$G/g5/tree.diff") lines)")" > "$G/g5/host.txt" ;;
    g6) # an incompatible feature the kernel does not know on the ext3 root (bit 0x80000000 by debugfs)
        cp --sparse=always "$G/g1/disk.img" "$G/g6/disk.img"
        p2 "$G/g6/disk.img" "$G/g6/p2.img"
        tools/e2fs "$G/g6" debugfs -w -R "ssv feature_incompat 0x80000002" p2.img > "$G/g6/debugfs.txt" 2>&1
        tools/e2fs "$G/g6" dumpe2fs -h p2.img 2>&1 | grep -E 'features' >> "$G/g6/debugfs.txt"
        put2 "$G/g6/disk.img" "$G/g6/p2.img"; rm -f "$G/g6/p2.img"
        lr --fstype none --append loglevel=7 --timeout 120 --disk "$G/g6/disk.img" "$G/g6" "$P" > "$G/g6/run.txt" 2>&1 ;;
    g7) # the same on the probe's mount(2) of partition 4 (an ext2 volume, as ext2 and as ext4)
        cp --sparse=always "$G/g1/disk.img" "$G/g7/disk.img"
        p4 "$G/g7/disk.img" "$G/g7/p4.img"
        tools/e2fs "$G/g7" debugfs -w -R "ssv feature_incompat 0x80000002" p4.img > "$G/g7/debugfs.txt" 2>&1
        put4 "$G/g7/disk.img" "$G/g7/p4.img"; rm -f "$G/g7/p4.img"
        lr --fstype ext3 --append loglevel=7 --disk "$G/g7/disk.img" "$G/g7" "$P" > "$G/g7/run.txt" 2>&1 ;;
    esac
    show "$R"
done
