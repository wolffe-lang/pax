#!/usr/bin/env bash
# px87 on kasumi (PX87_SLOT=4-7, by hostchain.sh): the scroll fix after CI's mpx5-pelt slowdown, red first, then
# green, then the fork replay's slice again.
#   red-v8       tests/mpx3-screen --tier native --firmware bios at V8's commit, before the fix: V8 red by name
#   red-t7       tests/mpx3-console --tier native --firmware bios at T7's commit, before the boot line: T7 red
#   screen       tests/mpx3-screen --tier both --firmware both at HEAD (V1-V8)
#   console      tests/mpx3-console --tier both --firmware both at HEAD (T1-T7)
#   pelt-*       tests/mpx5-pelt's slice (PAX_PELT_CASES, native, BIOS) at HEAD and at BASE under TCG: the build
#                in the container, the Linux side once on the host (rootless podman, tools/linux-tree), the boots
#                in the container; each case's wall time from the suite's timestamped lines
# Every step runs and prints END.
#   fix9.sh V8SHA T7SHA HEAD BASE
set -uo pipefail
V8=$1 T7=$2 HEAD=$3 BASE=$4
F=$L/f9 TREE=docker.io/library/python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
CASES="corpus probes c_jc_mixed_pipeline cnf_cd"
[ ! -e "$F" ] || { echo "$F exists"; exit 3; }
mkdir -p "$F"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
for c in "$V8" "$T7" "$HEAD" "$BASE"; do
    [ -d "$F/${c:0:8}" ] || git -C "$L/pax" worktree add -q --detach "$F/${c:0:8}" "$c" || exit 3
    printf 'worktree %s %s\n' "${c:0:8}" "$(git -C "$F/${c:0:8}" log --oneline -1 | cut -c1-100)"
done
inc() { local w=$1 n=$2; shift 2; ctr bash "$L/bin/run.sh" "$F/${w:0:8}" "$F/b-$n" "$n" "$@"; }
rows() { grep -aE "$1" "$2" | cut -c1-260 | head -${3:-12}; }
redv8() { inc "$V8" red-v8 tests/mpx3-screen --tier native --firmware bios > "$F/red-v8.log" 2>&1; local rc=$?; rows 'PASS V[378]|FAIL V' "$F/red-v8.log"; return $rc; }
redt7() { inc "$T7" red-t7 tests/mpx3-console --tier native --firmware bios > "$F/red-t7.log" 2>&1; local rc=$?; rows 'PASS T[67]|FAIL T' "$F/red-t7.log" 6; return $rc; }
screen() { inc "$HEAD" screen tests/mpx3-screen --tier both --firmware both > "$F/screen.log" 2>&1; local rc=$?; rows 'PASS V[378]|FAIL|mpx3-screen: (PASS|FAIL)' "$F/screen.log" 20; return $rc; }
console() { inc "$HEAD" console tests/mpx3-console --tier both --firmware both > "$F/console.log" 2>&1; local rc=$?; rows 'PASS T7 native bios ask-serial|PASS T7 release uefi ask-serial|FAIL|mpx3-console: (PASS|FAIL)' "$F/console.log" 8; return $rc; }
step red-v8 redv8
CTR_ROOT=1 CTR_CAPS=1 step red-t7 redt7
step screen screen
CTR_ROOT=1 CTR_CAPS=1 step console console
pbuild() { # sha
    ctr bash -c "cd $F/${1:0:8} && export PAX_CACHE=$L/cache PAX_BUILD=$F/p-${1:0:8} TMPDIR=$L/tmp PAX_PELT_CASES='$CASES' PAX_WOLF=\$(tools/fetch-wolf) && tests/mpx5-pelt --only build --tier native --firmware bios" > "$F/pbuild-${1:0:8}.log" 2>&1
}
plinux() {
    podman image exists "$TREE" || podman pull -q "$TREE" || return 1
    ( cd "$F/${BASE:0:8}" && PAX_ENGINE=podman PAX_TREE_IMAGE=$TREE PAX_PELT_CASES="$CASES" PAX_CACHE=$L/cache TMPDIR=$L/tmp \
        PAX_BUILD=$F/p-linux tests/mpx5-pelt --only linux --images "$F/p-${BASE:0:8}/mpx5-pelt" ) > "$F/plinux.log" 2>&1 || { tail -5 "$F/plinux.log"; return 1; }
    rm -rf "$F/p-${HEAD:0:8}/mpx5-pelt/linux" && cp -a "$F/p-${BASE:0:8}/mpx5-pelt/linux" "$F/p-${HEAD:0:8}/mpx5-pelt/linux"
}
pboot() { # sha
    ctr bash -c "cd $F/${1:0:8} && export PAX_CACHE=$L/cache PAX_BUILD=$F/r-${1:0:8} TMPDIR=$L/tmp PAX_PELT_CASES='$CASES' PAX_WOLF=\$(tools/fetch-wolf); tests/mpx5-pelt --images $F/p-${1:0:8}/mpx5-pelt --tier native --firmware bios 2>&1 | python3 -u -c 'import sys,time
for l in sys.stdin: print(\"%.1f %s\" % (time.time(), l), end=\"\", flush=True)'; exit \${PIPESTATUS[0]}" > "$F/pboot-${1:0:8}.log" 2>&1
    local rc=$?
    grep -aE 'begin native bios|F3 native bios|mpx5-pelt: (PASS|FAIL)$' "$F/pboot-${1:0:8}.log" | cut -c1-160
    for f in "$F/r-${1:0:8}"/mpx5-pelt-native-bios-*.serial.log; do
        [ -f "$f" ] && printf '  %s: %s\n' "$(basename "$f" .serial.log)" "$(tr -d '\r' < "$f" | grep -am1 '^boot: [0-9]' || echo 'no boot line')"
    done
    return $rc
}
step pelt-build-head pbuild "$HEAD"
step pelt-build-base pbuild "$BASE"
step pelt-linux plinux
step pelt-boot-base pboot "$BASE"
step pelt-boot-head pboot "$HEAD"
printf '%s fix9 done\n' "$(ts)"
