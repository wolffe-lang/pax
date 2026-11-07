#!/usr/bin/env bash
# notes/px106/rig/suite.sh SHA [TIER] [FIRMWARE] — tests/mpx5-sudo at SHA on a build host whose
# container engine and QEMU live apart, under one heavy take (lib.sh): the build in a container
# (tests/mpx5-sudo --only build), mpx5-accounts' archive and notes/px46/vmtty for the real-root
# recording made on another Linux host, the container sides on the host (--only auth), and the boots
# in a container with KVM. Run from a checkout of SHA (this file is that commit's).
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
SHA=$1 TIER=${2:-native} FW=${3:-bios}
here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"
checkout_ok "$SHA" || exit 3
cd "$CO"
short=${SHA:0:8}
PB=$L/pb-$short
mkdir -p "$PB"
CTR_ENV="-e PAX_BUILD=$PB"
take || exit 4
( while :; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E 'Package id 0|CPU:' | head -1 | tr -s ' '; sleep 60; done ) > "$L/runs/sensors-$short.log" 2>&1 &
spid=$!
trap 'kill $spid 2>/dev/null' EXIT
echo "suite: $SHA ($TIER, $FW)"
step build ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx5-sudo --only build --tier '"$TIER" || exit 1
step acct-build ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx5-accounts --only build --tier native && cc -static -O1 -o '"$PB"'/vmtty notes/px46/vmtty.c'
step auth env PAX_BUILD="$PB" PAX_ENGINE="$P" taskset -c "$CPUS" tests/mpx5-sudo --only auth --images "$PB/mpx5-sudo"
arc=$?
step boot ctr 1 localhost/px75-ubuntu:2 tests/mpx5-sudo --images "$PB/mpx5-sudo" --tier "$TIER" --firmware "$FW"
brc=$?
echo "RESULT auth=$arc boot=$brc"
[ "$arc" = 0 ] && [ "$brc" = 0 ]
