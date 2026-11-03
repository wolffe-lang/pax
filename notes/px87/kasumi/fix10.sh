#!/usr/bin/env bash
# px87 on kasumi (PX87_SLOT=4-7, by hostchain.sh): R-px87-17's conditions, red first.
#   red-t7b        tests/mpx3-console --tier native --firmware bios at T7's reason commit, before the boot line says
#                  why: T7 red by name
#   red-t7c        the same at T7's no-screen commit, before the kernel says `by none`: T7 red by name
#   mpx6-firmware  --tier native --firmware both at HEAD with PAX_BUILD the short $L/f10/b (mpx6-triage's T2 with
#                  the boot line's new words; mpx6-nmi's sockets at most 98 bytes)
# Every step runs and prints END.
#   fix10.sh T7B T7C HEAD
set -uo pipefail
T7B=$1 T7C=$2 HEAD=$3 F=$L/f10
[ ! -e "$F" ] || { echo "$F exists"; exit 3; }
mkdir -p "$F"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
for c in "$T7B" "$T7C" "$HEAD"; do
    git -C "$L/pax" worktree add -q --detach "$F/${c:0:8}" "$c" || exit 3
    printf 'worktree %s %s\n' "${c:0:8}" "$(git -C "$F/${c:0:8}" log --oneline -1 | cut -c1-100)"
done
p=$F/b/firmware/native/mpx6-nmi/native/bios/mce-initramfs.report/qmp.sock
printf 'the longest socket %s: %d bytes\n' "$p" "${#p}"
red() { # sha name
    ctr bash "$L/bin/run.sh" "$F/${1:0:8}" "$F/b-$2" "$2" tests/mpx3-console --tier native --firmware bios > "$F/$2.log" 2>&1
    local rc=$?
    grep -aE 'PASS T7|FAIL T7' "$F/$2.log" | cut -c1-260 | head -6
    return $rc
}
fw() {
    ctr bash "$L/bin/run.sh" "$F/${HEAD:0:8}" "$F/b" mpx6-firmware tests/mpx6-firmware --tier native --firmware both > "$F/fw.log" 2>&1
    local rc=$?
    grep -aE 'PASS (F1[01]|T1/T2)|FAIL|OSError' "$F/fw.log" | cut -c1-200 | head -12
    return $rc
}
CTR_ROOT=1 CTR_CAPS=1 step red-t7b red "$T7B" red-t7b
CTR_ROOT=1 CTR_CAPS=1 step red-t7c red "$T7C" red-t7c
step mpx6-firmware fw
printf '%s fix10 done\n' "$(ts)"
