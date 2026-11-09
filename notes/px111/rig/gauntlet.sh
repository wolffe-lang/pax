#!/usr/bin/env bash
# notes/px111/rig/gauntlet.sh — px111's local gauntlet at the commit it is run from, on the build
# host under take.sh's heavy take (`take.sh SHA gauntlet`), recorded by tools/gauntlet-record.sh
# (the planning repo's recorder, a copy by value in the lane's directory, GAUNTLET_RECORD). Each
# step a container with KVM (lib.sh's `ctr`), its output two spaces in (a test's own SKIP or END
# lines cannot break the record); the first nonzero step stops the run. The steps:
#   ci-plan        tests/ci-plan: the tiers map and the new job wired (the plan's own proof)
#   check          tests/mpx5-pty.d/check.py --selftest
#   pty-native     tests/mpx5-pty, native tier, BIOS and UEFI, KVM
#   pty-release    the same, release tier
#   pty-tcg        native tier, BIOS and UEFI, TCG
#   jobs           tests/mpx5-jobs, native BIOS (px48's job control on the console, whose
#                  sessions kernel/sched now keeps per terminal)
#   console        tests/mpx3-console, native BIOS (the console's line discipline, now by id)
#   users          tests/mpx5-users, native BIOS (priv.pax's /dev/ptmx rows)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
: "${GAUNTLET_RECORD:?the recorder's path}"
# shellcheck disable=SC1090
. "$here/lib.sh"
CO=$(realpath "$(git -C "$here" rev-parse --show-toplevel)")
# shellcheck disable=SC1090
. "$GAUNTLET_RECORD"
ind() { "$@" 2>&1 | sed -u 's/^/  /'; return "${PIPESTATUS[0]}"; }
suite() { ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf 2>/dev/null) && exec "$@"' x "$@"; }
gauntlet_step ci-plan ind ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan || exit $?
gauntlet_step check ind ctr 0 localhost/px75-ubuntu:2 python3 -I tests/mpx5-pty.d/check.py --selftest || exit $?
gauntlet_step pty-native ind suite tests/mpx5-pty --tier native --firmware both --accel kvm || exit $?
gauntlet_step pty-release ind suite tests/mpx5-pty --tier release --firmware both --accel kvm || exit $?
gauntlet_step pty-tcg ind suite tests/mpx5-pty --tier native --firmware both --accel tcg || exit $?
gauntlet_step jobs ind suite tests/mpx5-jobs --tier native --firmware bios || exit $?
gauntlet_step console ind suite tests/mpx3-console --tier native --firmware bios || exit $?
gauntlet_step users ind suite tests/mpx5-users --tier native --firmware bios || exit $?
