#!/bin/bash
# px59 on kasumi: build notes/px59/vtprobe2.c static in px13-ubuntu, make
# its initramfs, run notes/px59/vt-run2.py (twice, compared). Launched
# with `setsid -f` and a pid file; QEMU under taskset -c 0-3.
set -euo pipefail
L=$HOME/lanes/px59 P=$HOME/lanes/px59/pax
mkdir -p $L/measure $L/out
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c \
  "ulimit -c 0; cc -static -O1 -o $L/measure/vtprobe2 $P/notes/px59/vtprobe2.c && sha256sum $L/measure/vtprobe2 $P/notes/px59/vtprobe2.c"
$P/tools/mkinitramfs $L/measure/vt2.cpio /vtprobe2=$L/measure/vtprobe2:755 > $L/measure/vt2.cpio.txt
K=/usr/lib/modules/$(uname -r)/vmlinuz
echo "kernel: $K $(sha256sum $K | cut -d' ' -f1); $(qemu-system-x86_64 --version | head -n1)"
python3 $P/notes/px59/vt-run2.py $L
