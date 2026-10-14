#!/bin/bash
# px41 on kasumi: pax#45 counted. Boots TREE's speaker image (TIER, bios) N times; each boot types
# KEYS (60 plays of a one-chord tune) and reads kernel/speaker's ring from the halted machine. K busy
# loops on CPUS with QEMU under taskset to the same CPUS (K=0: no added load, no taskset).
# ACCEL=kvm in the environment boots under KVM (hasu).
# usage: chordloop.sh TREE TIER N K CPUS OUTDIR [KEYS]
set -u
tree=$1 tier=$2 n=$3 k=$4 cpus=$5 out=$6 keys=${7:-$HOME/lanes/px41/st/chordloop.keys}
mkdir -p "$out"; cd "$tree" || exit 2
export TMPDIR=$HOME/lanes/px41/tmp PAX_BUILD=$out/build; mkdir -p "$PAX_BUILD"
img=$tree/build/mpx3-speaker; elf=$img/$tier/kmain_console.elf; iso=$img/$tier/speaker.iso
ring_at=$(nm "$elf" | awk '$3 == "pax_spk_ring" { print $1 }'); state_at=$(nm "$elf" | awk '$3 == "pax_spk_state" { print $1 }')
{ uptime; echo "tree $tree tier $tier n $n k $k cpus $cpus keys $keys"; } > "$out/conditions.txt"
pids=()
for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c $cpus)
acc=(); [ -n "${ACCEL:-}" ] && acc=(--accel "$ACCEL") # hasu: ACCEL=kvm
t0=$SECONDS
for ((i = 1; i <= n; i++)); do
    log=$out/boot-$i.serial.log
    "${ts[@]}" tools/qemu-halt --firmware bios --serial "$log" --timeout 600 "${acc[@]}" --elf "$elf" --marker 'halt' \
        --type "$keys" --prompt '$ ' --keyboard serial --cmd "x /8gx 0x$state_at" --cmd "x /1024gx 0x$ring_at" \
        --qemu -audiodev --qemu "wav,id=snd0,path=$out/boot.wav" --qemu -machine --qemu pcspk-audiodev=snd0 \
        "$iso" > "$log.verdict" 2>&1; rc=$?
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
n = state[6]
if n > 1024 or len(ring) < 1024:
    print("unreadable: %d events, %d ring words" % (n, len(ring))); sys.exit()
for k in range(n):
    w = ring[k]
    print("event %d tick %d %s %d" % (k, w >> 17, "on" if w & 0x10000 else "off", w & 0xffff))
PY
    echo "$i rc=$rc $(python3 $HOME/lanes/px41/st/steps.py "$out/boot-$i.timeline" | head -1)" >> "$out/lines.txt"
    rm -f "$out/boot.wav" "$log.cmd1" "$log.cmd2"
done
for p in "${pids[@]}"; do kill "$p"; done
{ echo "secs $((SECONDS - t0))"; uptime; } >> "$out/conditions.txt"
python3 $HOME/lanes/px41/st/steps.py "$out"/boot-*.timeline > "$out/counts.txt"
echo done > "$out/done"
