#!/usr/bin/env bash
# px88: tests/mpx5-forks at one commit, on hasu, inside a chain that holds
# the block (notes/px88/hasu/launch.sh). Built from the commit, never from
# a live tree: a worktree of the lane's clone at SHA.
#
#   suite.sh BLOCK RUN SHA BUILD_TIERS [LEG:TIER:SESSIONS ...]
#
# 1. build (px88's container: musl-gcc, wolf by the pin from the lane's
#    cache, Limine): `tests/mpx5-forks --only build --tier BUILD_TIERS`;
# 2. the Linux side on the host (the engine is podman-blk, the image
#    px75's, which has python3): `--only linux`;
# 3. each LEG:TIER:SESSIONS boot (sessions comma-separated, `all` for the
#    four) in the container with /dev/kvm: `--images … --firmware LEG
#    --tier TIER`, PAX_FORKS_SESSIONS set.
# Every step prints `END <step> exit=N`; the script goes on past a red
# boot (a red-first run wants every session's verdict) but not past a
# failed build or Linux side.
set -uo pipefail
B=$1 RUN=$2 SHA=$3 BT=$4; shift 4
L=/home/mfwolffe/lanes/px88
S=$L/scripts
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; esac
export PATH=/home/mfwolffe/lanes/hasu-env/bin:$PATH
# The lane's clone is shared by its chains (one a block): its git steps
# take a lane-local lock (never a block's).
G="flock /home/mfwolffe/lanes/px88/git.lock git"
[ -d "$L/pax/.git" ] || $G clone -q https://github.com/wolffe-lang/pax.git "$L/pax"
$G -C "$L/pax" fetch -q origin '+refs/heads/px88*:refs/remotes/origin/px88*' || { echo "END fetch exit=1"; exit 1; }
WT=$L/wt-${SHA:0:8}
[ -d "$WT" ] || $G -C "$L/pax" worktree add -q --detach "$WT" "$SHA" || { echo "END worktree exit=1"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$L/pax" rev-parse "$SHA^{commit}")" ] || { echo "END worktree exit=1 (not at $SHA)"; exit 1; }
echo "worktree $WT at $(git -C "$WT" rev-parse HEAD)"
R=$L/build/$RUN
rm -rf "$R"; mkdir -p "$R" "$L/tmp"
if ! /home/mfwolffe/lanes/hasu-env/bin/podman image exists localhost/px88-ubuntu:1; then
    /home/mfwolffe/lanes/hasu-env/bin/podman build -q -t localhost/px88-ubuntu:1 -f "$S/Containerfile" "$S" || { echo "END image exit=1"; exit 1; }
fi
CTR_WD=$WT bash "$S/ctr.sh" "$B" "$RUN-build" localhost/px88-ubuntu:1 -- env PAX_BUILD="$R" bash -c '
    set -u; export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); "$PAX_WOLF" --version | head -n 1
    tests/mpx5-forks --only build --tier "$1"' x "$BT" > "$R/build.log" 2>&1
brc=$?
tail -n 3 "$R/build.log"
echo "END $RUN-build exit=$brc"
[ "$brc" = 0 ] || exit "$brc"
lrc=0
( cd "$WT" && PAX_BUILD=$R PAX_ENGINE=$S/podman-blk PAX_TREE_IMAGE=localhost/px75-ubuntu:2 PX88_CPUS=$cpus TMPDIR=$L/tmp \
    taskset -c "$cpus" tests/mpx5-forks --only linux --images "$R/mpx5-forks" ) > "$R/linux.log" 2>&1 || lrc=$?
tail -n 6 "$R/linux.log"
echo "END $RUN-linux exit=$lrc"
[ "$lrc" = 0 ] || exit "$lrc"
worst=0
for spec in "$@"; do
    IFS=: read -r leg tier sess <<< "$spec"
    [ "$sess" = all ] && sess="forks usage forks-user usage-user"
    sess=${sess//,/ }
    name="$RUN-boot-$leg-$tier-${sess// /+}"
    CTR_WD=$WT bash "$S/ctr.sh" "$B" "${name//+/-}" localhost/px88-ubuntu:1 KVM=1 -- env PAX_BUILD="$R" PAX_FORKS_SESSIONS="$sess" \
        tests/mpx5-forks --images "$R/mpx5-forks" --firmware "$leg" --tier "$tier" > "$R/$name.log" 2>&1
    rc=$?
    grep -E '^mpx5-forks: (PASS|FAIL|SKIP)' "$R/$name.log" | cut -c1-600
    echo "END $name exit=$rc"
    [ "$rc" = 0 ] || worst=$rc
done
exit "$worst"
