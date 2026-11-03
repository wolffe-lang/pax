#!/usr/bin/env bash
# px87 (copied from px88's notes/px88/hasu, by value): one container step of a chain on hasu (the chain holds the block's
# two locks: notes/px88/hasu/launch.sh).
#
#   ctr.sh BLOCK NAME IMAGE [KVM=1] -- CMD...
#
# The lane directory is mounted at its own path, the command runs under
# `taskset -c <the block's CPUs>` inside the container (rootless podman has
# no cpuset controller here: hasu-env/README.md), `--memory 12g`, the
# pids and process limits the README names, no core files. /dev/kvm only
# with KVM=1. Prints `END NAME exit=N`.
set -uo pipefail
L=/home/mfwolffe/lanes/px87
P=/home/mfwolffe/lanes/hasu-env/bin/podman
B=$1 N=$2 I=$3; shift 3
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; *) echo "ctr.sh: BLOCK is A or B" >&2; exit 2 ;; esac
kvm=0
case ${1:-} in KVM=1) kvm=1; shift ;; KVM=0) shift ;; esac
[ "${1:-}" = -- ] && shift
dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
echo "$(date -u +%FT%TZ) step $N: $I, CPUs $cpus, kvm=$kvm: $*"
rc=0
"$P" run --rm --name "px87-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    ${dev[@]+"${dev[@]}"} -v "$L:$L" -w "${CTR_WD:-$L}" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e PAX_REQUIRE_UEFI=1 -e PX87_CPUS="$cpus" \
    ${CTR_ENV:-} "$I" taskset -c "$cpus" "$@" || rc=$?
echo "$(date -u +%FT%TZ) END $N exit=$rc"
exit $rc
