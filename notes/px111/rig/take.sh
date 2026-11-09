#!/usr/bin/env bash
# notes/px111/rig/take.sh SHA WHAT [ARGS…] — one heavy take of tests/mpx5-pty at SHA, run from a
# checkout of SHA (this file is that commit's): WHAT is `build` (tests/mpx5-pty --only build) or
# `suite` (the whole suite; ARGS go to it, e.g. --tier native --firmware bios --accel kvm), in a
# container with KVM, under both of the block's locks. PAX_BUILD is $L/pb-<sha8>.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
SHA=$1 WHAT=$2; shift 2
here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"
checkout_ok "$SHA" || exit 3
cd "$CO"
PB=$L/pb-${SHA:0:8}
mkdir -p "$PB"
CTR_ENV="-e PAX_BUILD=$PB"
take || exit 4
echo "take: $SHA $WHAT $*; uptime: $(uptime)"
case $WHAT in
    build) step build ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx5-pty --only build "$@"' x "$@" ;;
    suite) step suite ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx5-pty "$@"' x "$@" ;;
    plant) rawstep plant ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx5-pty "$@"' x "$@" ;;
    *) echo "take: no such thing: $WHAT"; exit 2 ;;
esac
