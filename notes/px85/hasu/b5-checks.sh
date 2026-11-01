#!/usr/bin/env bash
# px85 batch 5, at a branch commit S: F1's clock legs on both compiler tiers,
# the three plan-job selftests in the container (Ubuntu's dash runs
# tools/fetch-retry), and the pipe rewrites against real kernels.
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu S=$1
s=${S:0:8} T=$L/wt-${S:0:8}
[ -d "$T" ] || git -C "$L/pax" worktree add -q --detach "$T" "$S"
"$H/ctr.sh" clock-native-$s "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/clock-$s" native
"$H/ctr.sh" clock-release-$s "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/clock-$s-release" release
"$H/ctr.sh" selftests-$s "$T" -- bash -c 'for c in "tests/fetch-retry-selftest" "python3 -I tests/usb-session-selftest" "python3 -I tests/pipe-shape-selftest" "tests/ci-plan"; do $c > /tmp/st.log 2>&1; rc=$?; grep -aE "^(PASS|FAIL)|^ci-plan: (PASS|FAIL)$" /tmp/st.log | tail -12; echo "END $c exit=$rc"; done'
"$H/ctr.sh" pipe-equiv-$s "$T" -- bash "$H/pipe-equiv.sh" "$L/build/clock-$s/mpx6-metal/kmain_metal.elf" "$L/build/clock-$s-release/mpx6-metal/kmain_metal.elf" "$L/runs/trunk-load/images/kmain_console.elf"
