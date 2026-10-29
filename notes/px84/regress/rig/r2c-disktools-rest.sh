set -euo pipefail
L=/mnt/steamlib/lanes/px84
W=$L/build/r2-disktools
rm -rf $W/big $W/bounds
python3 -I tests/mpx6-disktools.d/big.py "$W/bin/paxext2" "$W/big"
python3 -I tests/mpx6-disktools.d/bounds.py "$W/bin" "$W/bounds" $L/oracles/bin
tests/mpx6-disktools --only pax --tier native --firmware bios --work "$W"
