#!/usr/bin/env bash
# px89: one container step on hasu (by copy of px88's notes/px88/hasu/ctr.sh).
#
#   ctr.sh BLOCK NAME IMAGE [KVM=1] [NET=1] -- CMD...
#
# The lane directory is mounted at its own path, the command runs under
# `taskset -c <the block's CPUs>` inside the container, `--memory 12g`,
# the pids and process limits hasu-env/README.md names, no core files.
# /dev/kvm only with KVM=1. NET=1 adds /dev/net/tun and CAP_NET_ADMIN
# (a tap inside the container's own network namespace: dnsmasq and the
# guest on one wire; nothing of the host's network is touched).
# Prints `END NAME exit=N` (indented: the gauntlet's step owns its END).
set -uo pipefail
L=/home/mfwolffe/lanes/px89
P=/home/mfwolffe/lanes/hasu-env/bin/podman
B=$1 N=$2 I=$3; shift 3
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; *) echo "ctr.sh: BLOCK is A or B" >&2; exit 2 ;; esac
kvm=0 net=0
while :; do
    case ${1:-} in
        KVM=1) kvm=1; shift ;; KVM=0) shift ;;
        NET=1) net=1; shift ;; NET=0) shift ;;
        *) break ;;
    esac
done
[ "${1:-}" = -- ] && shift
dev=(); [ "$kvm" = 1 ] && dev+=(--device /dev/kvm)
[ "$net" = 1 ] && dev+=(--device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW)
echo "  $(date -u +%FT%TZ) container $N: $I, CPUs $cpus, kvm=$kvm net=$net: $*"
rc=0
"$P" run --rm --name "px89-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    ${dev[@]+"${dev[@]}"} -v "$L:$L" -w "${CTR_WD:-$L}" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e PAX_REQUIRE_UEFI=1 -e PX89_CPUS="$cpus" \
    ${CTR_ENV:-} "$I" taskset -c "$cpus" "$@" || rc=$?
echo "  $(date -u +%FT%TZ) container $N exit=$rc"
exit $rc
