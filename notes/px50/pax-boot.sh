#!/bin/bash
# px50 on kasumi: one image of a suite build booted on PAX (TCG, BIOS), its runs cut out as the suite cuts them.
#   pax-boot.sh BUILDDIR(the suite's work dir) TIER IMAGE KERNEL OUTDIR [KEYS]
L=$HOME/lanes/px50
B=$1 T=$2 IM=$3 K=$4 O=$5 KEYS=${6:-/dev/null}
mkdir -p $O
cd $L/pax
cp $KEYS $O/keys 2>/dev/null || : > $O/keys
export PAX_CACHE=$L/cache PAX_BUILD=$O
tools/qemu-halt --firmware bios --serial $O/serial.log --timeout 900 --qemu -m --qemu 512M --elf $B/$T/$K.elf --marker 'halt|PANIC .*' --type $O/keys --prompt '$ ' $B/$T/$IM.iso > $O/verdict 2>&1
echo "qemu-halt: $?"; tail -2 $O/verdict
. tools/lib.sh; serial_norm $O/serial.log > $O/serial.norm
n=$(grep -c '^run [0-9]*: ' $O/serial.norm)
for k in $(seq 1 $n); do
  awk -v k="$k" '$0 ~ "^run " k ": " { on = 1; next } on && /^run [0-9]+: |^run: [0-9]+ commands$|^user: frames free / { exit } on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' $O/serial.norm > $O/run$k.session
done
grep -a 'refused\|ENOSYS\|PANIC' $O/serial.norm | sed -E 's/pid [0-9]+/pid N/' | sort | uniq -c
