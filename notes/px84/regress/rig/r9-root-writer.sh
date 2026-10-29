set -euo pipefail
L=/mnt/steamlib/lanes/px84
W=$L/build/r2-disktools
# CI's mpx6-disktools job also runs mpx6-root with / written by paxext2.
export PATH=$L/shim:$L/oracles/bin:$PATH PAX_ENGINE=podman
export PAX_LINUX_KERNEL=/host-modules/7.3.0-4-cachyos/vmlinuz
rm -rf $L/build/r9-root
PAX_BUILD=$L/build/r9-root PAX_EXT2_WRITER="$W/bin/paxext2" tests/mpx6-root --fstype ext2 --tier native --firmware bios
