#!/bin/bash
# px41 on kasumi: K8 itself under the reproducing load. Boots TREE's speaker image (release, bios) N
# times with the suite's chord session (user/console/speaker-chord.keys), K busy loops on CPUS and
# QEMU under taskset to the same CPUS, and judges each boot's timeline and capture twice: by trunk's
# tools/arp-check (every step within one tick of two) and by w6's (every tone within a tick of its place).
# usage: k8loop.sh TREE N K CPUS OUTDIR
set -u
L=~/lanes/px41; tree=$1 n=$2 k=$3 cpus=$4 out=$5
mkdir -p "$out"; cd "$tree" || exit 2
export TMPDIR=$L/tmp PAX_BUILD=$out/build; mkdir -p "$PAX_BUILD"
img=$tree/build/mpx3-speaker; elf=$img/release/kmain_console.elf; iso=$img/release/speaker.iso
ring_at=$(nm "$elf" | awk '$3 == "pax_spk_ring" { print $1 }'); state_at=$(nm "$elf" | awk '$3 == "pax_spk_state" { print $1 }')
{ uptime; echo "tree $tree n $n k $k cpus $cpus"; } > "$out/conditions.txt"
pids=(); for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c $cpus)
for ((i = 1; i <= n; i++)); do
    log=$out/boot-$i.serial.log; wav=$out/boot-$i.wav
    "${ts[@]}" tools/qemu-halt --firmware bios --serial "$log" --timeout 240 --elf "$elf" --marker 'halt' \
        --type user/console/speaker-chord.keys --prompt '$ ' --keyboard serial --cmd "x /8gx 0x$state_at" --cmd "x /1024gx 0x$ring_at" \
        --qemu -audiodev --qemu "wav,id=snd0,path=$wav" --qemu -machine --qemu pcspk-audiodev=snd0 "$iso" > "$log.verdict" 2>&1; rc=$?
    python3 - "$log.cmd1" "$log.cmd2" > "$out/boot-$i.timeline" 2>&1 <<'PY'
import re, sys
def words(path):
    out = []
    for line in open(path):
        if ":" not in line:
            continue
        out += [int(w, 16) for w in re.findall(r"0x([0-9a-fA-F]+)", line.split(":", 1)[1])]
    return out
state, ring = words(sys.argv[1]), words(sys.argv[2])
for k in range(state[6]):
    w = ring[k]
    print("event %d tick %d %s %d" % (k, w >> 17, "on" if w & 0x10000 else "off", w & 0xffff))
PY
    old=$(python3 $L/t-trunk/tools/arp-check $L/t-trunk/user/tunes/chords "$out/boot-$i.timeline" "$wav" 2>&1 | cut -c1-150)
    new=$(python3 $L/t-w6/tools/arp-check $L/t-w6/user/tunes/chords "$out/boot-$i.timeline" "$wav" 2>&1 | cut -c1-150)
    echo "$i rc=$rc old-rule: ${old%% *} new-rule: ${new%% *} | old: $old | new: $new" >> "$out/lines.txt"
    rm -f "$wav" "$log.cmd1" "$log.cmd2"
done
for p in "${pids[@]}"; do kill "$p"; done
uptime >> "$out/conditions.txt"
echo "boots $n: trunk's rule PASS $(grep -c 'old-rule: PASS' "$out/lines.txt"), the place rule PASS $(grep -c 'new-rule: PASS' "$out/lines.txt")" > "$out/counts.txt"
echo done > "$out/done"
