set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r6-500gb
bash tests/mpx6-install.d/big-run "$PWD" $L/build/r5-install/inputs $L/build/r6-500gb 500000000000
