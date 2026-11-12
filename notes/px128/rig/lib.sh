# notes/px128/rig/lib.sh — px128's build-host rig (px123's shape), sourced by step.sh through
# GAUNTLET_RIG_DIR (the recorder runs a stored copy of step.sh, never this tree's). The rig runs from a
# clean checkout of the commit under test. The host's facts are in the file PX128_HOST names (shell
# assignments kept beside the lane, never in the tree):
#   L        the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   CPUS     the CPUs the take may use (taskset inside each container)
#   P        the container engine (rootless podman)
#   MEM      each container's memory (12g on a block, the light slot's 6g)
#   IMAGES   a directory of image directories (tools/mkdistribution's OUT, read-only to the rig): each
#            step that boots one makes a fresh copy of it by hard links under PAX_BUILD
#   TASKSET  the taskset inside the containers
# and, read by take.sh alone: LOCKS (the lock files, in the host's one order; empty for a light take,
# which runs under the host's light-slot helper) and REC (the recorder, a copy by value).
: "${PX128_HOST:?PX128_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX128_HOST"
: "${L:?}" "${CPUS:?}" "${P:?}" "${IMAGES:?}" "${PAX_BUILD:?the build directory of the take}"
R=$(realpath "$L")
export TMPDIR=$L/tmp PAX_CACHE=$L/cache
mkdir -p "$TMPDIR" "$PAX_CACHE" "$L/home" "$PAX_BUILD"
CO=$(realpath "$(git rev-parse --show-toplevel)")
# ctr KIND IMAGE CMD...: a container of IMAGE in the checkout, the take's CPUs inside. KIND 0: no
# devices; 1: KVM.
ctr() {
    local kind=$1 img=$2; shift 2
    local dev=() mnt=(-v "$L:$L")
    [ "$kind" = 1 ] && dev=(--device /dev/kvm)
    [ "$R" = "$L" ] || mnt+=(-v "$R:$R")  # a lane directory behind a symbolic link: both spellings
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
        "${mnt[@]}" -v "$IMAGES:$IMAGES:ro" --security-opt label=disable -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" -e PAX_BUILD="$PAX_BUILD" -e HOME="$L/home" -e PYTHONUNBUFFERED=1 \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" "${TASKSET:-taskset}" -c "$CPUS" "$@" < /dev/null
}
# copy NAME: a fresh copy of $IMAGES/NAME (hard links, so nothing is duplicated) at $PAX_BUILD/img-NAME
copy() {
    local d=$PAX_BUILD/img-$1
    rm -rf "$d"; mkdir -p "$d/kernel"
    ln "$IMAGES/$1/commit" "$IMAGES/$1/kernel/kmain_console.elf" "$d/" 2>/dev/null || return 1
    mv "$d/kmain_console.elf" "$d/kernel/"
    local c; c=$(cat "$IMAGES/$1/commit")
    ln "$IMAGES/$1/pax-dev-${c:0:8}.cpio" "$d/" || return 1
    echo "$d"
}
