#!/bin/sh
# black-box: what QEMU's q35 presents for -device virtio-net-pci (no guest runs: -S)
q=${PAX_QEMU:-qemu-system-x86_64}
$q --version | head -n 1
( printf 'info pci\ninfo network\nquit\n' ) | $q -machine q35 -cpu max -m 256M -accel tcg -display none -S -nic none \
  -netdev user,id=n0 -device virtio-net-pci,netdev=n0,mac=52:54:00:12:34:56 -monitor stdio -serial none -parallel none 2>&1
