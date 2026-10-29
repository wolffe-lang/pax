set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r5b-install
# CI's job installs gdisk, fdisk, dosfstools and mtools from Ubuntu 24.04; these are user/disktools.pin's same packages.
export PATH=$L/oracles/bin:$PATH
command -v sgdisk sfdisk fsck.fat mtype
env -u PAX_INSTALL_ROWS -u PAX_INSTALL_BIG_ROWS tests/mpx6-install --tier native --firmware bios --work $L/build/r5b-install --inputs $L/build/r5-install/inputs
