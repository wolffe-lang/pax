set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r4-fsck
tests/mpx6-fsck --tier native --firmware bios --work $L/build/r4-fsck
