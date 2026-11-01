#!/usr/bin/env bash
# px85: run CMD in a container on hasu block A (CPUs 0-5), both of the
# block's locks held for this command alone, the block name outside
# (the lane rules of 2026-10-31), every wait printed at least each minute.
#
#   ctr.sh NAME WORKDIR [KVM=0|1] -- CMD...
#
# The lane directory is mounted at its own path; PAX_CACHE is the lane's
# cache (copied from px83's, never moved); TMPDIR is the lane's. The
# command runs under `taskset -c 0-5` inside the container (rootless podman
# has no cpuset controller here: hasu-env/README.md). No /dev/kvm unless
# KVM=1: F8 on CI is TCG.
set -uo pipefail
L=/home/mfwolffe/lanes/px85
P=/home/mfwolffe/lanes/hasu-env/bin/podman
N=$1 W=$2; shift 2
kvm=0
case ${1:-} in KVM=1) kvm=1; shift;; KVM=0) shift;; esac
[ "${1:-}" = -- ] && shift
stamp() { date -u +%FT%TZ; }
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
echo "$(stamp) px85 $N: acquiring hasu-block-A.lock"
until flock -n 9; do echo "$(stamp) hasu-block-A.lock held by another lane; waiting"; sleep 60; done
exec 8>/home/mfwolffe/lanes/hasu-A.lock
until flock -n 8; do echo "$(stamp) hasu-A.lock held by another lane; waiting"; sleep 60; done
echo "$(stamp) block A acquired (both locks)"
dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
rc=0
"$P" run --rm --name "px85-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    ${dev[@]+"${dev[@]}"} -v "$L:$L" -w "$W" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e CARGO_INCREMENTAL=0 -e PAX_REQUIRE_UEFI=1 \
    ${CTR_ENV:-} localhost/px75-ubuntu:2 taskset -c 0-5 "$@" || rc=$?
flock -u 8; exec 8>&-
flock -u 9; exec 9>&-
echo "$(stamp) block A released ($N, rc=$rc)"
echo "$(stamp) END $N exit=$rc"
exit $rc
