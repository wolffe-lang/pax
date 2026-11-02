#!/usr/bin/env bash
# px87: the one gauntlet at the head HEAD, run by hostchain.sh (one hold of kasumi-cores-0-3.lock, CPUs 0-3),
# a fresh clone ($L/gaunt), fresh build directories. It stops at the first nonzero step and prints every step's
# `END <step> exit=N`. Every QEMU boot is TCG (kasumi's firmware has VT-x off) in localhost/px76-ubuntu
# (QEMU 8.2.2, Ubuntu's OVMF), as CI's runners boot.
#   1 ci-plan       python3 -I tests/ci-plan (the planner's proofs, kernel/identity's rule among them)
#   2 ci-budgets    python3 -I tests/ci-budgets.py
#   3 pax-release   python3 -I tests/pax-release
#   4 mpx1          tests/mpx1 --firmware both (boot/start.S's new request: the entry and the responses)
#   5 mpx3-screen   tests/mpx3-screen --tier both --firmware both: V0-V7 (V7 the read watch and fbread's control)
#   6 mpx3-console  tests/mpx3-console --tier both --firmware both: T0-T7 (T6 the identity line, T7 the boot
#                   line), as the rootless container's root with CAP_SYS_ADMIN in its user namespace (the Linux
#                   side's pid namespace, tools/linux-tty --pid1)
#   7 u7            tests/usb-stick's U7 (the live login on the USB topology, both firmwares; the stick image by
#                   tools/mkdisk on the host, its disk tools in podman)
#   8 mpx6-install  tests/mpx6-install --rows smoke --tier native --firmware bios: the units, I-inventory, the
#                   as-user rows (I-user-check, I-user-reboot, I-poweroff), the installs, the faults, the used disks
#   9 mpx6-firmware tests/mpx6-firmware --tier native --firmware both (kernel/screen and kmain_console's F5, F8)
#   gauntlet.sh HEAD
set -uo pipefail
HEAD=$1
S=$L/gaunt B=$L/gbuild
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; [ "$rc" = 0 ] || { echo "GAUNTLET STOPPED at $n"; exit "$rc"; }; }
rm -rf "$S" "$B" && git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b gauntlet "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
mkdir -p "$B"
printf '%s gauntlet at %s\n' "$(ts)" "$HEAD"
inc() { local n=$1; shift; ctr bash "$L/bin/run.sh" "$S" "$B/$n" "$n" "$@"; }
step ci-plan inc ci-plan python3 -I tests/ci-plan
step ci-budgets inc ci-budgets python3 -I tests/ci-budgets.py
step pax-release inc pax-release python3 -I tests/pax-release
step mpx1 inc mpx1 tests/mpx1 --firmware both
step mpx3-screen inc mpx3-screen tests/mpx3-screen --tier both --firmware both
CTR_ROOT=1 CTR_CAPS=1 step mpx3-console inc mpx3-console tests/mpx3-console --tier both --firmware both
step u7 bash "$L/bin/probe-u7.sh" "$S" "$B/u7"
step mpx6-install inc mpx6-install tests/mpx6-install --rows smoke --tier native --firmware bios --work "$B/mpx6-install/work"
step mpx6-firmware inc mpx6-firmware tests/mpx6-firmware --tier native --firmware both
printf '%s GAUNTLET GREEN at %s\n' "$(ts)" "$HEAD"
