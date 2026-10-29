set -euo pipefail
L=/mnt/steamlib/lanes/px84
W=$L/build/r2-disktools
rm -rf $L/build/r3-highlinux
python3 -I tests/mpx6-disktools.d/high.py "$PWD" $L/build/r3-highlinux "$W/bin/paxext2" "$(cat $W/native.elf.path)" \
    --linux-kernel /host-modules/7.3.0-4-cachyos/vmlinuz --linux-modules /host-modules/7.3.0-4-cachyos
