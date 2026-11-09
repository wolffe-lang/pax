#!/usr/bin/env bash
# notes/px111/rig/take.sh SHA WHAT [ARGS…] — one heavy take of tests/mpx5-pty at SHA, run from a
# checkout of SHA (this file is that commit's): WHAT is `kernel` (kmain_console alone, its
# compiler's errors), `build` (tests/mpx5-pty --only build), `gauntlet` (the recorded local
# gauntlet, gauntlet.sh), `plant BASE ROW…` (the plant's record, plant.sh) or `suite` (the whole suite; ARGS go to it, e.g. --tier native --firmware bios --accel kvm), in a
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
    kernel) step kernel ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && mkdir -p "$PAX_BUILD/k" && tools/build-kernel "$@" --src kernel/kmain_console.lu "$PAX_BUILD/k" > /dev/null' x "$@" ;;
    gauntlet)
        # The recorder (tools/gauntlet-record.sh of the planning repo, a copy by value at
        # $L/gauntlet-record.sh) on this host, in this checkout; each step a container.
        export CTR_ENV PX111_HOST GAUNTLET_RECORD=$L/gauntlet-record.sh
        mkdir -p "$L/records"
        bash "$GAUNTLET_RECORD" --output "$L/records/green-${SHA:0:8}.log" -- bash notes/px111/rig/gauntlet.sh ;;
    plant)
        # A plant's record: this checkout is the plant branch, one commit on BASE ($1); its
        # rows ($2…) red by name (tests/mpx5-pty's FAIL lines reach the record at column 0).
        export CTR_ENV PX111_HOST GAUNTLET_RECORD=$L/gauntlet-record.sh
        base=$1; shift
        mkdir -p "$L/records"
        bash "$GAUNTLET_RECORD" --output "$L/records/plant-${SHA:0:8}.log" --base "$base" --plant "$@" -- bash notes/px111/rig/plant.sh ;;
    *) echo "take: no such thing: $WHAT"; exit 2 ;;
esac
