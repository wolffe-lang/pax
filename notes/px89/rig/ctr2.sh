#!/usr/bin/env bash
# px89: one container step on hasu (by copy of px88's notes/px88/hasu/ctr.sh).
#
#   ctr2.sh BLOCK NAME IMAGE [KVM=1] [NET=1] [ENGINE=1] [HOSTNET=1] -- CMD...
#
# ctr2.sh is ctr.sh and ENGINE=1: a container engine for the suites'
# Linux sides that run throwaway containers (tools/linux-tree, tools/e2fs):
# hasu's own podman binary (its Nix store mounted read-only at its own
# path) as a remote client of the lane's podman service (podman-service.sh,
# on the host: rootless, the lane's storage), through scripts/podman-remote
# (every `run` given --memory 12g and taskset inside, as px88's
# podman-blk did). The paths it mounts are the lane directory's, the same
# on both sides.
#
# The lane directory is mounted at its own path, the command runs under
# `taskset -c <the block's CPUs>` inside the container, `--memory 12g`,
# the pids and process limits hasu-env/README.md names, no core files.
# /dev/kvm only with KVM=1. NET=1 adds /dev/net/tun and CAP_NET_ADMIN
# and CAP_SYS_ADMIN (the Linux reference sides unshare a network
# namespace of their own; a tap inside the container's own network namespace: dnsmasq and the
# guest on one wire; nothing of the host's network is touched).
# HOSTNET=1 (never with NET=1): the container in hasu's own network
# namespace, so its 127.0.0.1 is the one the engine's `--network host`
# containers listen on (tools/lobo-session's Linux side); no tap, no device.
# Prints `END NAME exit=N` (indented: the gauntlet's step owns its END).
set -uo pipefail
L=/home/mfwolffe/lanes/px89
P=/home/mfwolffe/lanes/hasu-env/bin/podman
B=$1 N=$2 I=$3; shift 3
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; C) cpus=12-17 ;; *) echo "ctr.sh: BLOCK is A, B or C" >&2; exit 2 ;; esac
kvm=0 net=0 engine=0 hostnet=0
while :; do
    case ${1:-} in
        KVM=1) kvm=1; shift ;; KVM=0) shift ;;
        NET=1) net=1; shift ;; NET=0) shift ;;
        ENGINE=1) engine=1; shift ;; ENGINE=0) shift ;;
        HOSTNET=1) hostnet=1; shift ;; HOSTNET=0) shift ;;
        *) break ;;
    esac
done
[ "${1:-}" = -- ] && shift
dev=(); [ "$kvm" = 1 ] && dev+=(--device /dev/kvm)
[ "$net" = 1 ] && dev+=(--device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW --cap-add SYS_ADMIN)
[ "$hostnet" = 1 ] && [ "$net" = 1 ] && { echo "ctr2.sh: HOSTNET=1 and NET=1 together would put a tap in hasu's network" >&2; exit 2; }
[ "$hostnet" = 1 ] && dev+=(--network host)
[ "$engine" = 1 ] && dev+=(-v /nix/store:/nix/store:ro -e "PAX_ENGINE=$L/scripts/podman-remote" -e PAX_TREE_IMAGE=localhost/px75-ubuntu:2 -e PAX_E2FS_IMAGE=localhost/px75-ubuntu:2)
echo "  $(date -u +%FT%TZ) container $N: $I, CPUs $cpus, kvm=$kvm net=$net engine=$engine hostnet=$hostnet: $*"
rc=0
"$P" run --rm --name "px89-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    ${dev[@]+"${dev[@]}"} -v "$L:$L" -w "${CTR_WD:-$L}" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e PAX_REQUIRE_UEFI=1 -e PX89_CPUS="$cpus" \
    ${CTR_ENV:-} "$I" taskset -c "$cpus" "$@" || rc=$?
echo "  $(date -u +%FT%TZ) container $N exit=$rc"
exit $rc
