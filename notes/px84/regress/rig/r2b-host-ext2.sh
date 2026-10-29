set -euo pipefail
L=/mnt/steamlib/lanes/px84
W=$L/build/r2-disktools
rm -rf $W/ext2
python3 -I tests/mpx6-disktools.d/ext2.py "$W/bin/paxext2" "$W/ext2"
