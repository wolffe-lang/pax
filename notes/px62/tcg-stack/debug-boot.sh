#!/usr/bin/env bash
# px62 debug: build a patched kernel from TREE into OUT, then boot lope1's images with it.
set -euo pipefail
L=$HOME/lanes/px62
tree=$1 out=$2 name=$3
python3 $L/dbgk/debug-patch.py "$tree"
mkdir -p "$out"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
  set -euo pipefail; cd "$1"; w=$(tools/fetch-wolf | tail -1)
  PAX_WOLF=$w tools/build-kernel --src kernel/kmain_console.lu "$2"' px62 "$tree" "$out" > "$out.build.log" 2>&1 || { grep -a -i error -A3 "$out.build.log" | head -20; exit 1; }
cd $L && bash pax/notes/px62/lope-kernels.sh lope1 "$name=$out/kmain_console.elf" 2>&1 | head -2 | cut -c1-150
f=$L/build/lope1-$name/mpx5-lope-native-bios.serial.log
tr -d '\r' < "$f" | grep -a -o 'dbg slow pid [0-9]* nr [0-9]* dtms [0-9]*' | awk '{print $4}' | sort -n | uniq -c | sort -rn | head -8
tr -d '\r' < "$f" | grep -a 'dbg slow pid 7[4-9]' | head -5
