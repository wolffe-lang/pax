set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r2-disktools
tests/mpx6-disktools --tier native --firmware bios --oracle-bin $L/oracles/bin --work $L/build/r2-disktools
