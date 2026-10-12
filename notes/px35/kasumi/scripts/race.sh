#!/bin/bash
# px35 on kasumi: the pax#39 race counted. Boots the probes image of TREE's mpx4-unix (native bios) N
# times, or runs the Linux side of the probes session N times, each with K busy loops on CPUs 0-3 and
# the boot itself under taskset -c ${CPUS:-0-3} (K=0, no taskset: an idle host), and counts the client's
# epoll_wait line.   usage: race.sh pax|linux TREE N K OUTDIR
set -u
side=$1 tree=$2 n=$3 k=$4 out=$5
mkdir -p "$out"; cd "$tree" || exit 2
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu TMPDIR=$HOME/lanes/px35/tmp
pids=()
for ((j = 0; j < k; j++)); do taskset -c ${CPUS:-0-3} bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c ${CPUS:-0-3})
w=build/mpx4-unix
for ((i = 1; i <= n; i++)); do
    if [ "$side" = pax ]; then
        log=$out/pax-$i.serial.log
        "${ts[@]}" tools/qemu-halt --firmware bios --serial "$log" --timeout 300 --qemu -m --qemu 256M \
            --elf $w/native/kmain_console.elf --marker 'halt|PANIC .*' $w/native/unix-probes.iso > "$log.verdict" 2>&1
        line=$(grep -a -m1 'client: epoll_wait' "$log" | sed 's/^.*client: /client: /')
    else
        o=$out/linux-$i.tty
        "${ts[@]}" tools/linux-tree --root $w/probes/root --keys $w/none.keys --prompt '$ ' --argv0 /bin/unixprobe --size 64m --sys "$o" -- /bin/unixprobe > "$o.err" 2>&1
        line=$(grep -a -m1 'client: epoll_wait' "$o" | tr -d '\r' | sed 's/^.*client: /client: /')
    fi
    echo "$i $line" >> "$out/lines.txt"
done
for p in "${pids[@]}"; do kill "$p"; done
sort -k2 "$out/lines.txt" | cut -d' ' -f2- | uniq -c > "$out/counts.txt"
echo done > "$out/done"
