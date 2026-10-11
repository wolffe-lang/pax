#!/bin/bash
# px29: boot a probe image, type KEYS, capture the speaker; usage:
# boot.sh IMGDIR TREE KEYS OUT [accel] [firmware]   -> OUT.{serial.log,wav,tones,timeline,verdict}
set -u
img=$1; tree=$2; keys=$3; out=$4; accel=${5:-auto}; fw=${6:-bios}
ring=$(awk '$1=="pax_spk_ring"{print $2}' $img/syms); st=$(awk '$1=="pax_spk_state"{print $2}' $img/syms)
rm -f $out.*; cd $tree
tools/qemu-halt --firmware $fw --accel $accel --serial $out.serial.log --timeout 600 --elf $img/k.elf --marker halt \
  --type $keys --prompt '$ ' --keyboard serial --cmd "x /8gx 0x$st" --cmd "x /1024gx 0x$ring" \
  --qemu -audiodev --qemu "wav,id=snd0,path=$out.wav" --qemu -machine --qemu pcspk-audiodev=snd0 $img/p.iso > $out.verdict 2>&1
echo "halt rc $?" >> $out.verdict
python3 tools/wav-notes $out.wav > $out.tones 2>&1
python3 - $out.serial.log.cmd1 $out.serial.log.cmd2 > $out.timeline <<'PY'
import re, sys
def words(p):
    o=[]
    for l in open(p):
        if ":" in l: o += [int(w,16) for w in re.findall(r"0x([0-9a-fA-F]+)", l.split(":",1)[1])]
    return o
s, r = words(sys.argv[1]), words(sys.argv[2]); n = s[6]
print("events", n)
for k in range(min(n,1024)):
    w = r[k]; print("event %d tick %d %s %d" % (k, w >> 17, "on" if w & 0x10000 else "off", w & 0xffff))
PY
echo done > $out.done
