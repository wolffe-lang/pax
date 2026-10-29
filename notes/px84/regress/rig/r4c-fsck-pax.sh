set -euo pipefail
L=/mnt/steamlib/lanes/px84
# The rescue disks come from tools/mkdisk: px75's engine shim runs its e2fsprogs in this container.
export PATH=$L/shim:$L/oracles/bin:$PATH PAX_ENGINE=podman
tests/mpx6-fsck --only rescue --tier native --firmware bios --work $L/build/r4-fsck
tests/mpx6-fsck --only pax-corpus --tier native --firmware bios --work $L/build/r4-fsck
