#!/usr/bin/env bash
# px87 (R-px87-15): gauntlet3's last step, mpx6-firmware, again at gauntlet3's tree under a short path.
# gauntlet3's build directory ($L/gbuild/mpx6-firmware) put the triage's fault3-reset QMP socket at 108 bytes,
# past sun_path's 107 and its NUL (leg.py: `OSError: AF_UNIX path too long`); here the tree is a worktree at
# $L/g/t and PAX_BUILD is $L/g/b. The longest socket path the step makes is printed first, for both firmwares.
# Run by hostchain.sh (one hold of kasumi-cores-0-3.lock, CPUs 0-3; `ctr` is a px76-ubuntu container):
#   firmware-short.sh HEAD
set -uo pipefail
HEAD=$1
G=$L/g
[ ! -e "$G" ] || { echo "$G exists: pick a new directory"; exit 3; }
mkdir -p "$G"
git -C "$L/pax" worktree add -q --detach "$G/t" "$HEAD" || exit 3
[ "$(git -C "$G/t" rev-parse HEAD)" = "$HEAD" ] || { echo "the worktree is not at $HEAD"; exit 3; }
[ -z "$(git -C "$G/t" status --porcelain --untracked-files=no)" ] || { echo "the worktree is dirty"; exit 3; }
printf '%s mpx6-firmware at %s, tree %s, build %s\n' "$(ts)" "$HEAD" "$G/t" "$G/b"
# tests/mpx6-firmware: PAX_BUILD=$base/firmware/<tier>; tests/mpx6-triage: work=$PAX_BUILD/mpx6-triage/<tier>,
# a leg's output $work/<firmware>/<leg>; tests/mpx6-triage.d/leg.py: <output>/qmp.sock. The longest leg name
# is fault3-reset.
for fw in bios uefi; do
    p=$G/b/firmware/native/mpx6-triage/native/$fw/fault3-reset/qmp.sock
    printf 'socket %s: %d bytes (sun_path holds 107 and a NUL)\n' "$p" "${#p}"
    [ "${#p}" -le 107 ] || { echo "still too long"; exit 3; }
done
old=$L/gbuild/mpx6-firmware/firmware/native/mpx6-triage/native/bios/fault3-reset/qmp.sock
printf 'gauntlet3 socket %s: %d bytes\n' "$old" "${#old}"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
step mpx6-firmware ctr bash "$L/bin/run.sh" "$G/t" "$G/b" mpx6-firmware tests/mpx6-firmware --tier native --firmware both
