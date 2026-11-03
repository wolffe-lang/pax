#!/usr/bin/env bash
# px87 on hasu (block B, behind both of its locks: launch.sh): mpx5-pelt's fork replay, a fixed slice of it,
# at the lane's head and at its trunk base, to see whether px87 makes it slower and where. CI runs this suite
# under TCG; the slice runs under TCG (the container without /dev/kvm) and under KVM (with it).
#   measure.sh BLOCK HEAD BASE
# The slice: PAX_PELT_CASES="corpus probes c_jc_mixed_pipeline cnf_cd", --tier native --firmware bios (CI's
# largest per-case slowdowns are the output-heavy `probes` and `corpus`; the two small cases show the per-boot
# cost). Each case runs as root and as pax, a fresh boot each, as CI's step does.
# Variants (each a worktree of a fresh clone, every build from a commit):
#   base      BASE (trunk)
#   head      HEAD
#   readback  HEAD + a probe commit (local, never pushed): the scroll's old read-back path by default
#             (kernel/screen: set_readback(true)), to see the scroll's share
#   nohash    HEAD + a probe commit (local, never pushed): kernel/identity does not hash the loaded file, to see
#             the SHA-256's share
# The Linux side runs once (base's images; tools/linux-tree on the host through podman-blk) and is copied to the
# others. The probe commits are never signed (-c commit.gpgsign=false: hasu's own git configuration signs with a
# key a lane must not use). Every boot step's output is timestamped (seconds since the epoch), so a case's wall time is its `begin`
# line to its `F3` line; the head's serial logs carry the kernel's own `boot:` line (the time to the first program
# and the console's share).
set -uo pipefail
B=$1 HEAD=$2 BASE=$3
L=/home/mfwolffe/lanes/px87
P=/home/mfwolffe/lanes/hasu-env/bin/podman
I=localhost/px88-ubuntu:1
TREE=docker.io/library/python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
CASES="corpus probes c_jc_mixed_pipeline cnf_cd"
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; esac
M=$L/${PX87_MEASURE_DIR:-m2} G="flock $L/git.lock git"
[ ! -e "$M" ] || { echo "$M exists"; exit 3; }
mkdir -p "$M" "$L/cache" "$L/tmp"
ts() { date -u +%FT%TZ; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
clone() {
    [ -d "$L/pax" ] || $G clone -q https://github.com/wolffe-lang/pax.git "$L/pax" || return 1
    $G -C "$L/pax" fetch -q origin || return 1
    for v in base head readback nohash; do
        c=$HEAD; [ "$v" = base ] && c=$BASE
        $G -C "$L/pax" worktree add -q --detach "$M/$v" "$c" || return 1
    done
    sed -i 's/^    set_readback(boot_info.cmdline_has("fbread"))$/    set_readback(true)/' "$M/readback/kernel/screen/screen.lu"
    sed -i '/^            digest(f, addr, n)$/d' "$M/nohash/kernel/identity/identity.lu"
    git -C "$M/readback" -c user.name=px87-probe -c user.email=px87@probe.invalid -c commit.gpgsign=false commit -q -am "PROBE (never pushed): the scroll reads the framebuffer back by default" || return 1
    git -C "$M/nohash" -c user.name=px87-probe -c user.email=px87@probe.invalid -c commit.gpgsign=false commit -q -am "PROBE (never pushed): kernel/identity does not hash the loaded file" || return 1
    for v in base head readback nohash; do
        printf '%s %s %s\n' "$v" "$(git -C "$M/$v" rev-parse HEAD)" "$(git -C "$M/$v" diff --stat HEAD~1 2>/dev/null | tail -n 1 | sed 's/^ *//')"
    done
    git -C "$M/readback" show --stat --format=%s HEAD | head -3; git -C "$M/readback" diff HEAD~1 | grep '^[-+] '
    git -C "$M/nohash" diff HEAD~1 | grep '^[-+] '
}
step clone clone || exit 1
build() { # variant
    CTR_WD=$M/$1 bash "$L/bin/ctr.sh" "$B" "build-$1" "$I" -- bash -c "export PAX_BUILD=$M/$1-b PAX_PELT_CASES='$CASES' PAX_WOLF=\$(tools/fetch-wolf) && tests/mpx5-pelt --only build --tier native --firmware bios"
}
for v in base head readback nohash; do step "build-$v" build "$v" || exit 1; done
linux() {
    "$P" image exists "$TREE" || "$P" pull -q "$TREE" || return 1
    ( cd "$M/base" && export PATH=/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH \
        PAX_ENGINE=$L/bin/podman-blk PX87_CPUS=$cpus PAX_TREE_IMAGE=$TREE PAX_PELT_CASES="$CASES" PAX_CACHE=$L/cache \
        TMPDIR=$L/tmp PAX_BUILD=$M/base-linux && taskset -c "$cpus" tests/mpx5-pelt --only linux --images "$M/base-b/mpx5-pelt" ) || return 1
    for v in head readback nohash; do rm -rf "$M/$v-b/mpx5-pelt/linux"; cp -a "$M/base-b/mpx5-pelt/linux" "$M/$v-b/mpx5-pelt/linux" || return 1; done
}
step linux linux || exit 1
boot() { # variant accel
    local k=KVM=0; [ "$2" = kvm ] && k=KVM=1
    CTR_WD=$M/$1 bash "$L/bin/ctr.sh" "$B" "boot-$1-$2" "$I" "$k" -- bash -c "export PAX_BUILD=$M/run-$1-$2 PAX_PELT_CASES='$CASES' PAX_WOLF=\$(tools/fetch-wolf); tests/mpx5-pelt --images $M/$1-b/mpx5-pelt --tier native --firmware bios 2>&1 | python3 -u -c 'import sys,time
for l in sys.stdin: print(\"%.1f %s\" % (time.time(), l), end=\"\", flush=True)'; exit \${PIPESTATUS[0]}" > "$M/boot-$1-$2.log" 2>&1
    local rc=$?
    grep -aE '(begin|F3) native bios|mpx5-pelt: (PASS|FAIL)$|accel' "$M/boot-$1-$2.log" | grep -aE 'begin|F3|mpx5-pelt: (PASS|FAIL)' | cut -c1-200
    for f in "$M/run-$1-$2"/mpx5-pelt-native-bios-*.serial.log; do
        [ -f "$f" ] || continue
        printf '  %s: %s bytes; %s\n' "$(basename "$f" .serial.log)" "$(wc -c < "$f" | tr -d ' ')" "$(tr -d '\r' < "$f" | grep -am1 '^boot: [0-9]' || echo 'no boot line')"
    done
    return $rc
}
for va in base:tcg head:tcg readback:tcg nohash:tcg base:kvm head:kvm; do
    step "boot-${va%:*}-${va#*:}" boot "${va%:*}" "${va#*:}"
done
printf '%s measure done\n' "$(ts)"
