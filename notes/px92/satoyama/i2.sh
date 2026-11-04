#!/usr/bin/env bash
# px92: tests/distribution-boot (I2) from a checkout at a commit against a mkdistribution output, in
# px75-ubuntu:2 under KVM; the maintainer's exception (no locks, slot B's CPUs 4-7,12-15, 12 GiB).
#   i2.sh CHECKOUT SOUT NAME    (NAME: the run's directory under $L/i2/)
# SOUT's release.cpio is the live archive after px86's live payload; the ISO carries release-original.cpio,
# so the run's image directory links that one as release.cpio.
set -uo pipefail
L=/home/mfwolffe/lanes/px92 C=$1 S=$2 N=$3
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
D=$L/i2/$N
[ ! -e "$D" ] || { echo "$D exists"; exit 3; }
mkdir -p "$D" "$L/i2/$N.build"
for f in commit pax-release pax-banner dev.cpio; do ln "$S/$f" "$D/$f"; done
for f in "$S"/pax-*.iso; do ln "$f" "$D/$(basename "$f")"; done
if [ -e "$S/release-original.cpio" ]; then ln "$S/release-original.cpio" "$D/release.cpio"; else ln "$S/release.cpio" "$D/release.cpio"; fi
mkdir -p "$D/kernel" && ln "$S/kernel/kmain_console.elf" "$D/kernel/kmain_console.elf"
printf '%s i2 %s: checkout %s, images %s (%s)\n' "$(date -u +%FT%TZ)" "$N" "$(git -C "$C" rev-parse HEAD)" "$S" "$(cat "$S/commit")"
"$P" run --rm --name "px92-i2-$N" --memory 12g --pids-limit 16384 --device /dev/kvm -v "$L:$L" -w "$C" \
  -e PAX_BUILD="$L/i2/$N.build" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" \
  localhost/px75-ubuntu:2 taskset -c 4-7,12-15 bash -c "tests/distribution-boot $D"
rc=$?
printf '%s END i2-%s exit=%s\n' "$(date -u +%FT%TZ)" "$N" "$rc"
exit $rc
