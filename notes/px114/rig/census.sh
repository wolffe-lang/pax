#!/usr/bin/env bash
# px114's census (pax#329): what a live image writes at run time that it does not ship.
# The image booted twice under KVM by tools/qemu-halt, the same session typed into each
# (census.keys: two cd's through lope's hook, sudo -n true, pax-install --check, then the tree
# listed with ls -laRn --full-time and five files hashed and printed): once on QEMU's user
# network through an igb (kernel/dhcp takes a lease), once with no network device.
# census-diff.py then holds each listing to the image's own rows.
#   census.sh WORK ELF ISO     run from a checkout (its tools/qemu-halt boots the image)
# Environment: PODMAN, the container engine; IMAGE, a container image with QEMU (Ubuntu 24.04's);
# LIGHT_CPUS and LIGHT_MEM, the CPUs and memory the boots get (taskset inside the container).
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
[ $# -eq 3 ] || { echo 'usage: census.sh WORK ELF ISO'; exit 2; }
W=$(realpath "$1") ELF=$(realpath "$2") ISO=$(realpath "$3")
here=$(cd "$(dirname "$0")" && pwd)
CO=$(git -C "$here" rev-parse --show-toplevel)
: "${PODMAN:?}" "${IMAGE:?}" "${LIGHT_CPUS:?}" "${LIGHT_MEM:?}"
[ -z "$(git -C "$CO" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; exit 3; }
echo "census: checkout $(git -C "$CO" rev-parse HEAD)"
sha256sum "$ELF" "$ISO"
mkdir -p "$W/tmp"
mounts=(-v "$W:$W" -v "$CO:$CO")
for d in "$(dirname "$ELF")" "$(dirname "$ISO")"; do mounts+=(-v "$d:$d:ro"); done
rc=0
for leg in net nonet; do
    out=$W/$leg; rm -rf "$out"; mkdir -p "$out"
    net=(); [ "$leg" = net ] && net=(--qemu -netdev --qemu user,id=n0,ipv6=off --qemu -device --qemu igb,netdev=n0,mac=52:54:00:12:34:56)
    echo "$(date -u +%FT%TZ) census: leg $leg"
    "$PODMAN" run --rm --memory "$LIGHT_MEM" --device /dev/kvm "${mounts[@]}" -w "$CO" \
        -e TMPDIR="$W/tmp" -e PAX_BUILD="$W/build" -e PAX_TYPE_PAUSE=2 \
        "$IMAGE" taskset -c "$LIGHT_CPUS" tools/qemu-halt --firmware bios --serial "$out/serial.log" --timeout 600 \
        --qemu -m --qemu 2048M --elf "$ELF" ${net[@]+"${net[@]}"} \
        --type "$here/census.keys" --prompt '$ ' --marker 'halt|PANIC .*' "$ISO" > "$out/halt.log" 2>&1 < /dev/null
    r=$?; [ "$r" = 0 ] || rc=$r
    echo "$(date -u +%FT%TZ) census: leg $leg exit=$r"; tail -n 1 "$out/halt.log"
done
exit "$rc"
