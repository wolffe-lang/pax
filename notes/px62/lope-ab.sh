#!/usr/bin/env bash
# px62, kasumi only: what one lope query costs PAX's kernel, base against
# head. pelt as pid 1 runs `lope query` N times (no store: lope's process
# start and exit, what `gi`'s menu waits for twice), alone and in a
# command substitution (a fork, a pipe, its end at exit); each kernel boots
# the same initramfs R times under TCG on CPUs 0-3, and qemu-halt's
# elapsed is the measure. The programs are the dev chain's (dev/w).
#   lope-ab.sh N R NAME=ELF...
set -euo pipefail
L=$HOME/lanes/px62
n=$1 reps=$2; shift 2
A=$L/ab; rm -rf "$A"; mkdir -p "$A"
W=$L/dev/w
printf 'i=0\nwhile [ $i -lt %s ]; do\n    /bin/lope query zz > /dev/null 2>&1\n    x=$(/bin/lope query zz 2>&1)\n    i=$((i + 1))\ndone\necho ab-done $i\n' "$n" > "$A/bench.sh"
echo "/bin/sh /etc/bench.sh" > "$A/run"
cd "$L/pax"
export PAX_CACHE=$L/cache PAX_BUILD=$A
tools/mkinitramfs "$A/ab.cpio" "/bin/sh=$W/pelt/pelt:755" "/bin/lope=$W/lope/lope:755" \
    "/etc/bench.sh=$A/bench.sh:644" "/etc/pax-run=$A/run:644" > /dev/null
sha256sum "$W/pelt/pelt" "$W/lope/lope" "$A/ab.cpio"
for kv in "$@"; do
    name=${kv%%=*} elf=${kv#*=}
    tools/mkimage --conf boot/limine-initramfs.conf --add "$A/ab.cpio" initramfs.cpio "$elf" "$A/$name.iso" > /dev/null
    echo "$name $(sha256sum < "$elf" | cut -c1-16)"
done
for i in $(seq 1 "$reps"); do
    for kv in "$@"; do
        name=${kv%%=*} elf=${kv#*=}
        s=$A/$name.$i.serial
        taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$s" --timeout 600 --elf "$elf" \
            --marker 'halt|PANIC .*' "$A/$name.iso" > "$s.verdict" 2>&1 || true
        printf '%s rep %s: %s, %s, %s\n' "$name" "$i" "$(grep -a '^elapsed' "$s.meta")" \
            "$(tr -d '\r' < "$s" | grep -a -c 'user: lope pid .* exit_group')" "$(tr -d '\r' < "$s" | grep -a -o 'ab-done [0-9]*' | head -1)"
    done
done
