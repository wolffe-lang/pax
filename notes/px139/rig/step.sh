#!/usr/bin/env bash
# Stored recorder step; all host locations are supplied by the caller.
set -euo pipefail
: "${PX139_ROOT:?}" "${PX139_CPUS:?}" "${PAX_BUILD:?}"
export TMPDIR=$PX139_ROOT/tmp PAX_CACHE=$PX139_ROOT/cache
mkdir -p "$TMPDIR" "$PAX_CACHE" "$PAX_BUILD" "$PX139_ROOT/home"
co=$(git rev-parse --show-toplevel)
what=${1:?}; shift
case $what in
    probe) cmd='export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); bash tests/mpx3-screen-probe "$@"';;
    triage) cmd='export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); bash tests/mpx6-triage "$@"';;
    norms) cmd='python3 -I tests/mpx6-triage.d/probe-mask-test.py';;
    screen) cmd='export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); bash tests/mpx3-screen "$@"';;
    ci-plan) cmd='python3 -I tests/ci-plan';;
    *) exit 2;;
esac
podman run --rm --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    --device /dev/kvm -v "$PX139_ROOT:$PX139_ROOT" -w "$co" \
    -e TMPDIR -e PAX_CACHE -e PAX_BUILD -e HOME="$PX139_ROOT/home" -e PAX_REQUIRE_UEFI=1 \
    -e GIT_CONFIG_COUNT=2 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e GIT_CONFIG_KEY_1=commit.gpgsign -e GIT_CONFIG_VALUE_1=false \
    localhost/px75-ubuntu:2 /usr/bin/taskset -c "$PX139_CPUS" bash -c \
    'set -euo pipefail; taskset -pc $$; cmd=$1; shift; eval "$cmd"' x "$cmd" "$@"
