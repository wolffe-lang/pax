# notes/px124/rig/lib.sh — px124's build-host rig (px119's shape), sourced by step.sh through
# GAUNTLET_RIG_DIR (the recorder runs a stored copy of step.sh, never this tree's). The rig runs from a
# clean checkout of the commit under test. The host's facts are in the file PX124_HOST names (shell
# assignments kept beside the lane, never in the tree):
#   L      the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   CPUS   the slot's CPUs (taskset inside each container)
#   P      the container engine (rootless podman)
#   DEVW   (burrowd's step) the dev compiler and its std, copied by value (PAX_DEV_WOLF_DIR and
#          PAX_DEV_STD_DIR: the suite holds them to user/wolf.sums and user/wolf.pin)
# and, read by take.sh alone: LOCK1 LOCK2 (the block's two lock names, the block's first) and REC
# (the recorder, a copy by value of the planning repo's tools/gauntlet-record.sh).
# PAX_BUILD is the build directory every step of one take shares.
: "${PX124_HOST:?PX124_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX124_HOST"
: "${L:?}" "${CPUS:?}" "${P:?}" "${PAX_BUILD:?the build directory of the take}"
R=$(realpath "$L")
export TMPDIR=$L/tmp PAX_CACHE=$L/cache
mkdir -p "$TMPDIR" "$PAX_CACHE" "$L/home" "$PAX_BUILD"
CO=$(realpath "$(git rev-parse --show-toplevel)")
# ctr KVM IMAGE CMD...: a container of IMAGE in the checkout, the slot's CPUs inside, 12 GiB.
ctr() {
    local kvm=$1 img=$2; shift 2
    local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" "${mnt[@]}" -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" -e PAX_BUILD="$PAX_BUILD" -e HOME="$L/home" -e PAX_REQUIRE_UEFI=1 \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" taskset -c "$CPUS" "$@" < /dev/null
}
# ctrnet IMAGE CMD...: ctr's container with KVM, /dev/net/tun and NET_ADMIN in its own network namespace
# (tests/mpx5-burrowd's tap and dnsmasq), the rig required (PAX_REQUIRE_BURROWD_RIG=1).
ctrnet() {
    local img=$1; shift
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
        --device /dev/kvm --device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW "${mnt[@]}" -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" -e PAX_BUILD="$PAX_BUILD" -e HOME="$L/home" -e PAX_REQUIRE_UEFI=1 \
        -e PAX_REQUIRE_BURROWD_RIG=1 -e PAX_DEV_WOLF_DIR="${DEVW:?}/wolf" -e PAX_DEV_STD_DIR="$DEVW/wolf-std" \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" taskset -c "$CPUS" "$@" < /dev/null
}
