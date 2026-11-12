# notes/px131/rig/lib.sh — px131's build-host rig (px129's shape, copied), sourced by step.sh through
# GAUNTLET_RIG_DIR (the recorder runs a stored copy of step.sh, never this tree's). The rig runs from
# a clean checkout of the commit under test. The host's facts are in the file PX131_HOST names (shell
# assignments kept beside the lane, never in the tree):
#   L       the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   CPUS    the CPUs the take may use (taskset inside each container)
#   P       the container engine (rootless podman)
#   MEM     each container's memory (12g on a block, the light slot's 6g)
#   LK, LM  (optional) a Linux kernel and its modules' directory, for mpx6-latency's Linux column
# and, read by take.sh alone: LOCKS (the lock files, in the host's one order) and REC (the recorder,
# a copy by value of the planning repo's tools/gauntlet-record.sh).
# PAX_BUILD is the build directory every step of one take shares.
: "${PX131_HOST:?PX131_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX131_HOST"
: "${L:?}" "${CPUS:?}" "${P:?}" "${PAX_BUILD:?the build directory of the take}"
R=$(realpath "$L")
export TMPDIR=$L/tmp PAX_CACHE=$L/cache
mkdir -p "$TMPDIR" "$PAX_CACHE" "$L/home" "$PAX_BUILD"
CO=$(realpath "$(git rev-parse --show-toplevel)")
# ctr KVM IMAGE CMD...: a container of IMAGE in the checkout, the take's CPUs inside. CTR_CAPS adds
# capabilities (a suite's Linux side that mounts inside its container: SYS_ADMIN, rootless).
ctr() {
    local kvm=$1 img=$2; shift 2
    local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    local lin=(); [ -n "${LK:-}" ] && lin=(-v /nix/store:/nix/store:ro -e "PAX_LINUX_KERNEL=$LK" -e "PAX_LINUX_MODULES=${LM:-}")
    local caps=(); for c in ${CTR_CAPS:-}; do caps+=(--cap-add "$c"); done
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" "${mnt[@]}" ${lin[@]+"${lin[@]}"} ${caps[@]+"${caps[@]}"} -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" -e PAX_BUILD="$PAX_BUILD" -e HOME="$L/home" -e PAX_REQUIRE_UEFI=1 \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" taskset -c "$CPUS" "$@" < /dev/null
}
