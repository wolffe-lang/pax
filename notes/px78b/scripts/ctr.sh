# px78b: run a command in a block-A container (CPUs 0-5), the block held for it alone.
#   ctr.sh NAME IMAGE KVM(0|1) CMD...
L=/home/mfwolffe/lanes/px78b
N=$1 IMG=$2 KVM=$3; shift 3
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px78b %s acquiring block A\n' "$(date -u +%FT%TZ)" "$N"
until flock -n 9; do printf '%s block A held; waiting\n' "$(date -u +%FT%TZ)"; python3 -I -c 'import time; time.sleep(30)'; done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
dev=(); [ "$KVM" = 1 ] && dev=(--device /dev/kvm)
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px78b-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 "${dev[@]}" -v "$L:$L" -w "$L/pax" \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/inputs/lope-local -e CARGO_INCREMENTAL=0 \
 ${CTR_ENV:-} "$IMG" taskset -c 0-5 "$@" || rc=$?
flock -u 9; exec 9>&-
printf '%s block A RELEASED %s rc=%s\n' "$(date -u +%FT%TZ)" "$N" "$rc"
printf '%s END %s exit=%s\n' "$(date -u +%FT%TZ)" "$N" "$rc"
exit $rc
