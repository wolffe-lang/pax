#!/usr/bin/env bash
# notes/px111/rig/plant.sh — px111's plant take (`take.sh SHA plant BASE ROW…`), recorded by
# tools/gauntlet-record.sh: the probe image alone (PAX_PTY_IMAGES), native BIOS under KVM, its
# output unindented so tests/mpx5-pty's `FAIL <row>` lines reach the record at column 0.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
: "${GAUNTLET_RECORD:?the path of the recorder}"
# shellcheck disable=SC1090
. "$here/lib.sh"
CO=$(realpath "$(git -C "$here" rev-parse --show-toplevel)")
# shellcheck disable=SC1090
. "$GAUNTLET_RECORD"
CTR_ENV="${CTR_ENV:-} -e PAX_PTY_IMAGES=probe"
gauntlet_step pty-probe ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf 2>/dev/null) && exec tests/mpx5-pty --tier native --firmware bios --accel kvm' || exit $?
