#!/usr/bin/env bash
# px86: run one command in a block-A container (CPUs 0-5 by taskset inside), both block-A lock names held
# for this run alone, the block name outside (the lane rules of 2026-10-31).
#   ctr.sh NAME IMAGE KVM(0|1) CMD...
# Extra podman arguments: CTR_ENV (word-split). Prints START/END lines and exits with the command's status.
L=/home/mfwolffe/lanes/px86
N=$1 IMG=$2 KVM=$3; shift 3
ts() { date -u +%FT%TZ; }
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px86 %s acquiring hasu-block-A.lock\n' "$(ts)" "$N"
until flock -w 240 9; do printf '%s hasu-block-A.lock held; waiting (%s)\n' "$(ts)" "$N"; done
exec 8>/home/mfwolffe/lanes/hasu-A.lock
until flock -w 240 8; do printf '%s hasu-A.lock held; waiting (%s)\n' "$(ts)" "$N"; done
printf '%s block A acquired (both names) %s\n' "$(ts)" "$N"
dev=(); [ "$KVM" = 1 ] && dev=(--device /dev/kvm)
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px86-$N" --memory 12g --pids-limit 16384 \
  --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" -v "$L:$L" -w "${CTR_DIR:-$L/pax}" \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
  -e PAX_CACHE=$L/cache -e PAX_BUILD=${CTR_BUILD:-$L/pbuild} -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/inputs/lope-local \
  -e CARGO_INCREMENTAL=0 ${CTR_ENV:-} "$IMG" taskset -c 0-5 "$@" || rc=$?
flock -u 8; exec 8>&-
flock -u 9; exec 9>&-
printf '%s block A RELEASED (both names) %s rc=%s\n' "$(ts)" "$N" "$rc"
printf '%s END %s exit=%s\n' "$(ts)" "$N" "$rc"
exit $rc
