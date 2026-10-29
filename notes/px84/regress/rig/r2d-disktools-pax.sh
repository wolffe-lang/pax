set -euo pipefail
L=/mnt/steamlib/lanes/px84
W=$L/build/r2-disktools
# px75's engine shim: tools/e2fs's programs run in this container, the pinned image's release.
export PATH=$L/shim:$L/oracles/bin:$PATH PAX_ENGINE=podman
rm -rf $W/native/install $W/high-native
tests/mpx6-disktools --only pax --tier native --firmware bios --work "$W"
