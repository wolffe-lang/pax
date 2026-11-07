# notes/px106/rig/lib.sh — px106's build-host rig, sourced by suite.sh, witness.sh and chain.sh.
# The rig runs from a checkout of the commit under test (its own copy of these files), never from
# a live tree. The host's facts are in the file $PX106_HOST names (shell assignments kept beside the
# lane, never in the tree):
#   L      the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   LOCK1  LOCK2  a heavy take's two lock names, the outer first (one long flock each)
#   CPUS   the heavy slot's CPUs (taskset inside each container)
#   P      the container engine (rootless podman)
#   LIGHT  the host's light helper (one light lock, its own CPUs in LIGHT_CPUS, LIGHT_MEM)
#   (witness.sh prep only, px93's files it copies by value:) INPUTS_SRC, px93's built inputs;
#   SRC_DIR, the directory of base-dev.cpio, limine-download and lope-local; STICK_A and STICK_D,
#   the 9c88ec8a and 8b4e98ae install sticks, with STICK_A_READ and STICK_D_READ, px93's sha256
#   reads of them; ALLOW_SRC, the 860's allow line
# Container steps mount the lane by both its spelled and its real path (worktrees record the real
# one), and work in the checkout by its real path.
: "${PX106_HOST:?PX106_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX106_HOST"
: "${L:?}" "${LOCK1:?}" "${LOCK2:?}" "${CPUS:?}" "${P:?}" "${LIGHT:?}"
R=$(realpath "$L")
export TMPDIR=$L/tmp PAX_CACHE=$L/cache
mkdir -p "$TMPDIR" "$L/runs" "$PAX_CACHE"
ts() { date -u +%FT%TZ; }
# step NAME CMD...: START and END lines at column 0, the output two spaces in, the END line's exit.
step() {
    local n=$1; shift
    printf 'START %s %s\n' "$n" "$(ts)"
    "$@" 2>&1 | sed -u 's/^/  /'
    local rc=${PIPESTATUS[0]}
    printf 'END %s exit=%s %s\n' "$n" "$rc" "$(ts)"
    return "$rc"
}
# take: both lock names, fds 8 and 9, for the rest of the calling script.
take() {
    exec 8>"$LOCK1"
    printf '%s px106: waiting on %s, then %s\n' "$(ts)" "$LOCK1" "$LOCK2"
    flock -w 21600 8 || { echo "$(ts) the first lock wait timed out"; return 4; }
    exec 9>"$LOCK2"
    flock -w 21600 9 || { echo "$(ts) the second lock wait timed out"; return 4; }
    printf '%s px106: both locks held (CPUs %s)\n' "$(ts)" "$CPUS"
}
# checkout_ok SHA: this script's own checkout is SHA and clean.
checkout_ok() {
    CO=$(git -C "$here" rev-parse --show-toplevel)
    CO=$(realpath "$CO")
    [ "$(git -C "$CO" rev-parse HEAD)" = "$1" ] || { echo "the checkout is not at $1"; return 3; }
    [ -z "$(git -C "$CO" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; return 3; }
}
# ctr KVM IMAGE CMD...: a container of IMAGE in the checkout, the slot's CPUs inside, 12 GiB.
ctr() {
    local kvm=$1 img=$2; shift 2
    local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" "${mnt[@]}" -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" ${CTR_ENV:-} \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" taskset -c "${RUN_CPUS:-$CPUS}" "$@" < /dev/null
}
