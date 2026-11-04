#!/usr/bin/env bash
# px89: the metal stick at one commit (launch.sh runs this as
# `wire-build.sh BLOCK SHA`): tools/mkwire root in the container, tools/mkwire
# stick on the host (tools/mkdisk --usb runs its FAT tools in rootless
# podman, as px86's stick did), then the qualification under QEMU
# (wire-qualify.sh, in the container, KVM), BIOS and UEFI, on copies.
set -uo pipefail
L=/home/mfwolffe/lanes/px89
S=$L/scripts
B=$1 SHA=$2
G="git -c commit.gpgsign=false"
flock "$L/git.lock" $G -C "$L/pax" fetch -q origin '+refs/heads/px89*:refs/remotes/origin/px89*' || exit 1
full=$($G -C "$L/pax" rev-parse "$SHA^{commit}") || exit 1
WT=$L/wt-${full:0:8}
[ -d "$WT" ] || flock "$L/git.lock" $G -C "$L/pax" worktree add -q --detach "$WT" "$full" || exit 1
O=$L/wire/${full:0:8}
mkdir -p "$O"
echo "  wire stick at $full in $O"
CTR_WD=$WT bash "$S/ctr.sh" "$B" wire-root localhost/px89-dhcp:1 -- \
    bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); tools/mkwire root "$1"; exit $?' px89 "$O" || exit 1
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; esac
( cd "$WT" && export PATH=/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH \
    PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_CACHE=$L/cache TMPDIR=$L/tmp \
    SOURCE_DATE_EPOCH=$($G -C "$WT" show -s --format=%ct HEAD) WIRE_TARGETS="${WIRE_TARGETS:-}" && \
    taskset -c "$cpus" tools/mkwire stick "$O" ) || { echo "  mkwire stick failed"; exit 1; }
CTR_WD=$WT bash "$S/ctr.sh" "$B" wire-qualify localhost/px89-dhcp:1 KVM=1 -- bash "$S/wire-qualify.sh" "$O" || exit 1
