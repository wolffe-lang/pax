#!/bin/bash
# px35 on kasumi: race.sh for the fixed probe — the whole two-process block of the probes session
# (server and client lines, |-joined), PAX or Linux, N times, K busy loops on CPUS (default 0-3).
# usage: CPUS=a-b race2.sh pax|linux TREE N K OUTDIR
set -u
side=$1 tree=$2 n=$3 k=$4 out=$5 cpus=${CPUS:-0-3}
mkdir -p "$out"; cd "$tree" || exit 2
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu TMPDIR=$HOME/lanes/px35/tmp
pids=()
for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c $cpus)
w=build/mpx4-unix
block() { tr -d '\r' < "$1" | sed -n '/^== epoll, two processes/,/^server: the client ended/p' | grep -v '^user: ' | sed 's/user: .*$//' | paste -sd'|' -; }
for ((i = 1; i <= n; i++)); do
    if [ "$side" = pax ]; then
        log=$out/pax-$i.serial.log
        "${ts[@]}" tools/qemu-halt --firmware bios --serial "$log" --timeout 300 --qemu -m --qemu 256M \
            --elf $w/native/kmain_console.elf --marker 'halt|PANIC .*' $w/native/unix-probes.iso > "$log.verdict" 2>&1
        b=$(block "$log")
    else
        o=$out/linux-$i.tty
        "${ts[@]}" tools/linux-tree --root $w/probes/root --keys $w/none.keys --prompt '$ ' --argv0 /bin/unixprobe --size 64m --sys "$o" -- /bin/unixprobe > "$o.err" 2>&1
        b=$(block "$o")
    fi
    echo "$i $b" >> "$out/lines.txt"
done
for p in "${pids[@]}"; do kill "$p"; done
cut -d' ' -f2- "$out/lines.txt" | sort | uniq -c > "$out/counts.txt"
echo done > "$out/done"
