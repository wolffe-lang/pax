set -euo pipefail
L=/mnt/steamlib/lanes/px84
rm -rf $L/build/r4-fsck
# The container's e2fsprogs is the pinned image's package (1.47.0-2.4~exp1ubuntu4.1).
PAX_FSCK_ORACLE_BIN=$L/oracles/e2fs-bin tests/mpx6-fsck --tier native --firmware bios --work $L/build/r4-fsck
