set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r5-install
env -u PAX_INSTALL_ROWS -u PAX_INSTALL_BIG_ROWS tests/mpx6-install --tier native --firmware bios --work $L/build/r5-install
