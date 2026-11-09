# notes/px111/rig/lib.sh — px111's build-host rig, sourced by take.sh and record.sh (px106's rig's
# shape). The rig runs from a checkout of the commit under test (its own copy of these files), never
# from a live tree. The host's facts are in the file $PX111_HOST names (kept beside the lane):
#   L      the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   LOCK1  LOCK2  a heavy take's two lock names, the outer first (one long flock each)
#   CPUS   the heavy slot's CPUs (taskset inside each container)
#   P      the container engine (rootless podman)
#   LIGHT  the host's light helper, LBLK its block (one light lock, its own CPUs)
#   KERNEL the Linux kernel image the guest boots (the host's own, never read)
: "${PX111_HOST:?PX111_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX111_HOST"
: "${L:?}" "${LOCK1:?}" "${LOCK2:?}" "${CPUS:?}" "${P:?}" "${LIGHT:?}" "${LBLK:?}" "${KERNEL:?}"
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
# rawstep NAME CMD...: as step, but the output unindented (a plant's FAIL lines at column 0).
rawstep() {
    local n=$1; shift
    printf 'START %s %s\n' "$n" "$(ts)"
    "$@" 2>&1
    local rc=$?
    printf 'END %s exit=%s %s\n' "$n" "$rc" "$(ts)"
    return "$rc"
}
# take: both lock names, fds 8 and 9, for the rest of the calling script (the block first).
take() {
    exec 8>"$LOCK1"
    printf '%s px111: waiting on %s, then %s\n' "$(ts)" "$LOCK1" "$LOCK2"
    flock -w 21600 8 || { echo "$(ts) the first lock wait timed out"; return 4; }
    exec 9>"$LOCK2"
    flock -w 21600 9 || { echo "$(ts) the second lock wait timed out"; return 4; }
    printf '%s px111: both locks held (CPUs %s)\n' "$(ts)" "$CPUS"
}
# checkout_ok SHA: this script's own checkout is SHA and clean.
checkout_ok() {
    CO=$(git -C "$here" rev-parse --show-toplevel)
    CO=$(realpath "$CO")
    [ "$(git -C "$CO" rev-parse HEAD)" = "$1" ] || { echo "the checkout is not at $1"; return 3; }
    [ -z "$(git -C "$CO" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; return 3; }
}
# ctr KVM IMAGE CMD...: a container of IMAGE in the checkout, RUN_CPUS (default the slot's) inside.
ctr() {
    local kvm=$1 img=$2; shift 2
    local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" "${mnt[@]}" -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" ${CTR_ENV:-} \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" bash -c 'taskset -c "$0" "$@"; exit $?' "${RUN_CPUS:-$CPUS}" "$@" < /dev/null
}
