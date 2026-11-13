# notes/px130/rig/lib.sh — px130's build-host rig (px123's shape), sourced by step.sh through
# GAUNTLET_RIG_DIR (the recorder runs a stored copy of step.sh, never this tree's). The rig runs from
# a clean checkout of the commit under test. The host's facts are in the file PX130_HOST names (shell
# assignments kept beside the lane, never in the tree):
#   L       the lane's directory (everything the rig writes is under it; TMPDIR is $L/tmp)
#   CPUS    the CPUs the take may use (taskset inside each container)
#   P       the container engine (rootless podman)
#   MEM     each container's memory (12g on a block, the light slot's 6g)
#   NETIMG  the burrowd rig's image (QEMU 8.2.2, OVMF, OpenSSH 9.6p1, dnsmasq, iproute2, e2fsprogs, gcc,
#           clang: px112's df1ae8c6e5de under this lane's tag)
#   DEVWOLF, DEVSTD  user/wolf.pin's dev compiler and its std (tools/mkwolf's and tools/mkwolf-std's
#           builds, copied by value; the burrowd suite holds them to user/wolf.sums and WOLF_STD_REV)
#   TASKSET the taskset inside the containers (taskset, or a host's taskset.real)
# and, read by take.sh alone: LOCKS (the lock files, in the host's one order) and REC (the recorder,
# a copy by value of the planning repo's tools/gauntlet-record.sh).
# PAX_BUILD is the build directory every step of one take shares.
: "${PX130_HOST:?PX130_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX130_HOST"
: "${L:?}" "${CPUS:?}" "${P:?}" "${NETIMG:?}" "${DEVWOLF:?}" "${DEVSTD:?}" "${PAX_BUILD:?the build directory of the take}"
R=$(realpath "$L")
export TMPDIR=$L/tmp PAX_CACHE=$L/cache
mkdir -p "$TMPDIR" "$PAX_CACHE" "$L/home" "$PAX_BUILD"
CO=$(realpath "$(git rev-parse --show-toplevel)")
# ctr KIND IMAGE CMD...: a container of IMAGE in the checkout, the take's CPUs inside. KIND 0: no
# devices; 1: KVM; net: KVM, /dev/net/tun, NET_ADMIN and NET_RAW (the burrowd rig's tap and dnsmasq,
# the push suite's fixtures); sys: net's and SYS_ADMIN, /proc/sys writable (linux-tree's script sets a
# sysctl in its own network namespace), with PAX_ENGINE this directory's engine-ns (a suite's Linux side:
# tools/linux-tty --pid1 unshares a pid namespace, tools/linux-tree a container).
ctr() {
    local kind=$1 img=$2; shift 2
    local dev=()
    case $kind in
        1) dev=(--device /dev/kvm) ;;
        net) dev=(--device /dev/kvm --device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW) ;;
        sys) dev=(--device /dev/kvm --device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW --cap-add SYS_ADMIN
                  --security-opt systempaths=unconfined
                  -e PAX_ENGINE="$(realpath "${GAUNTLET_RIG_DIR:?}")/engine-ns" -e PAX_REQUIRE_QEMU=1) ;;
    esac
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --memory "${MEM:-12g}" --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" "${mnt[@]}" \
        --security-opt label=disable -w "$CO" \
        -e TMPDIR="$TMPDIR" -e PAX_CACHE="$PAX_CACHE" -e PAX_BUILD="$PAX_BUILD" -e HOME="$L/home" -e PAX_REQUIRE_UEFI=1 \
        -e PAX_DEV_WOLF_DIR="$DEVWOLF" -e PAX_DEV_STD_DIR="$DEVSTD" -e PAX_REQUIRE_BURROWD_RIG=1 -e PYTHONUNBUFFERED=1 \
        -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
        "$img" "${TASKSET:-taskset}" -c "$CPUS" "$@" < /dev/null
}
