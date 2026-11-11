#!/usr/bin/env bash
# notes/px118/apt-container.sh — tools/ci-apt against Ubuntu's real archive
# and a real apt, end to end, each take in a throwaway container (px118).
# tests/ci-apt-selftest proves the script's paths with a fake apt; this
# proves the paths' apt commands do what the script says on Ubuntu 24.04.
#
#   notes/px118/apt-container.sh WORKDIR ROW...
#
# The rows, each its own container from the runner-like image C0 makes,
# the checkout mounted read-only, WORKDIR/snap the snapshot directory:
#   C0  the runner-like image: tools/e2fs's pinned Ubuntu 24.04 with its
#       package indexes read in (`apt-get update`), as GitHub's runner
#       image carries them, tagged localhost/px118-runner:1.
#   C1  cold, with the network: the live path; a snapshot written, save=true,
#       every package installed.
#   C2  warm, no network at all (--network none): an exact hit installed
#       from the snapshot's files, no update; the same versions as C1's.
#   C3  cold, no network: exit 1, the ::error:: naming the key; nothing
#       installed.
#   C4  stale, no network: the snapshot given as an earlier image's:
#       installed with the warning naming it, no save.
#   C5  a hung archive: apt's proxy an address nothing answers
#       (192.0.2.1, TEST-NET-1), the bounds 20 s and 30 s: exit 1 inside
#       them, the ::error:: said.
# A row prints PASS or FAIL ROW at column 0; exit 0 when every row named held.
# PAX_ENGINE: podman (the default) or docker. PACKAGES: the list (the
# proof job's by default). RUN_OPTS: more options for every build and run
# (a memory limit).
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
[ $# -ge 2 ] || { echo "usage: apt-container.sh WORKDIR ROW..." >&2; exit 2; }
work=$(mkdir -p "$1" && cd "$1" && pwd); shift
engine=${PAX_ENGINE:-podman}
base=docker.io/library/ubuntu@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
image=localhost/px118-runner:1
pkgs=${PACKAGES:-qemu-system-x86 ovmf xorriso gdb}
read -r -a opts <<< "${RUN_OPTS:-}"
fail=0
bad() { echo "FAIL $*"; fail=1; }
ok() { echo "PASS $*"; }

# take NAME NETWORK|default [ENV...]: tools/ci-apt install in a fresh container;
# its output in WORKDIR/NAME.log, its GITHUB_OUTPUT in WORKDIR/NAME.out,
# the packages dpkg holds after in WORKDIR/NAME.dpkg; $rc, $secs.
take() {
    local name=$1 net=() t0 envs=()
    [ "$2" = default ] || net=(--network "$2")
    shift 2
    for e in "$@"; do envs+=(-e "$e"); done
    : > "$work/$name.out"
    t0=$SECONDS rc=0
    "$engine" run --rm ${opts[@]+"${opts[@]}"} "${net[@]}" -v "$root:/pax:ro" -v "$work:/w" \
        -e GITHUB_ACTIONS=true -e GITHUB_OUTPUT="/w/$name.out" -e PAX_APT_DIR=/w/snap -e RUNNER_TEMP=/tmp \
        -e ImageOS=ubuntu24 -e ImageVersion=px118-e2e "${envs[@]}" "$image" \
        bash -c "/pax/tools/ci-apt install $pkgs; rc=\$?; dpkg-query -W -f='\${Package} \${Version} \${db:Status-Abbrev}\n' $pkgs > /w/$name.dpkg 2>/dev/null; exit \$rc" \
        > "$work/$name.log" 2>&1 || rc=$?
    secs=$((SECONDS - t0))
}
installed() { [ "$(grep -c ' ii *$' "$work/$1.dpkg" 2>/dev/null)" = "$(wc -w <<< "$pkgs" | tr -d ' ')" ]; }
log() { tail -n 3 "$work/$1.log" | tr '\n' '|'; }
key=$(env ImageOS=ubuntu24 ImageVersion=px118-e2e "$root/tools/ci-apt" key $pkgs | sed -n 's/^key=//p')

for row in "$@"; do
    case $row in
    C0)
        printf 'FROM %s\nRUN apt-get update -q\n' "$base" > "$work/Containerfile"
        if "$engine" build ${opts[@]+"${opts[@]}"} -q -t "$image" -f "$work/Containerfile" "$work" > "$work/C0.log" 2>&1 \
            && "$engine" run --rm ${opts[@]+"${opts[@]}"} --network none "$image" sh -c 'ls /var/lib/apt/lists | grep -q _Packages'; then
            ok "C0 the runner-like image: Ubuntu 24.04 ($base) with its package indexes"
        else
            bad "C0 $(log C0)"
        fi ;;
    C1)
        rm -rf "$work/snap"
        take C1 default PAX_APT_HIT=false
        n=$(( $(wc -l < "$work/snap/MANIFEST" 2>/dev/null || echo 3) - 3 ))
        if [ "$rc" = 0 ] && grep -qx save=true "$work/C1.out" && installed C1 && [ "$n" -gt 0 ] \
            && grep -q "^ci-apt: live: the snapshot holds $n .deb(s) for $key" "$work/C1.log"; then
            ok "C1 cold with the network: the archive's $n .deb(s) installed and kept as the snapshot, save=true (${secs} s)"
        else
            bad "C1 rc=$rc $(log C1)"
        fi ;;
    C2)
        take C2 none PAX_APT_HIT=true PAX_APT_MATCHED="$key"
        if [ "$rc" = 0 ] && [ ! -s "$work/C2.out" ] && installed C2 && grep -q '^ci-apt: warm: the snapshot ' "$work/C2.log" \
            && ! grep -q 'apt-get update' "$work/C2.log" && cmp -s "$work/C1.dpkg" "$work/C2.dpkg"; then
            ok "C2 warm with no network: installed from the snapshot, the versions C1 installed (${secs} s)"
        else
            bad "C2 rc=$rc $(log C2) $(diff "$work/C1.dpkg" "$work/C2.dpkg" | tr '\n' '|')"
        fi ;;
    C3)
        mkdir -p "$work/empty"
        mv "$work/snap" "$work/snap.kept"
        take C3 none PAX_APT_HIT=false PAX_APT_UPDATE_SECS=20 PAX_APT_FETCH_SECS=30
        mv "$work/snap.kept" "$work/snap"
        if [ "$rc" = 1 ] && ! installed C3 \
            && grep -q "^::error::ci-apt: the archive did not answer within 20 + 30 s, and CI's cache holds no snapshot of these packages for this runner image ($key)" "$work/C3.log"; then
            ok "C3 cold with no network: exit 1, the ::error:: naming the key, nothing installed (${secs} s)"
        else
            bad "C3 rc=$rc $(log C3)"
        fi ;;
    C4)
        take C4 none PAX_APT_HIT=false PAX_APT_MATCHED="${key%-*}-earlier" PAX_APT_UPDATE_SECS=20 PAX_APT_FETCH_SECS=30
        if [ "$rc" = 0 ] && [ ! -s "$work/C4.out" ] && installed C4 \
            && grep -q "^::warning::ci-apt: the archive did not answer .*; installing the snapshot ${key%-*}-earlier" "$work/C4.log"; then
            ok "C4 stale with no network: an earlier image's snapshot installed with the warning, no save (${secs} s)"
        else
            bad "C4 rc=$rc $(log C4)"
        fi ;;
    C5)
        mv "$work/snap" "$work/snap.kept"
        printf 'Acquire::http::Proxy "http://192.0.2.1:9/";\nAcquire::https::Proxy "http://192.0.2.1:9/";\n' > "$work/unroutable.conf"
        take C5 default PAX_APT_HIT=false PAX_APT_UPDATE_SECS=20 PAX_APT_FETCH_SECS=30 APT_CONFIG=/w/unroutable.conf
        mv "$work/snap.kept" "$work/snap"
        if [ "$rc" = 1 ] && ! installed C5 && [ "$secs" -lt 120 ] \
            && grep -q "^::error::ci-apt: the archive did not answer within 20 + 30 s" "$work/C5.log"; then
            ok "C5 a hung archive: cut at the bounds, exit 1 after ${secs} s, the ::error:: said"
        else
            bad "C5 rc=$rc secs=$secs $(log C5)"
        fi ;;
    *) echo "apt-container.sh: no row $row" >&2; exit 2 ;;
    esac
done
exit "$fail"
