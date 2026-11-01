#!/usr/bin/env bash
# px85: the freeze load. Pause the container px85-NAME with podman's cgroup
# freezer for FROZEN ms, let it run RUNNING ms, again, from the moment its
# stall harness starts its rounds (OUT/rounds.started) until they end
# (OUT/rounds.done) or the container is gone. No signal is sent to any
# process: the freezer stops every task in the container's cgroup at once
# (the guest's vCPU, QEMU's main loop, the harness), as a hypervisor that
# deschedules a whole runner VM does, while the host's clock runs on.
# Measured on hasu (2026-11-01): `podman pause` takes 46-214 ms and
# `unpause` 47-89 ms, so a 300 ms hold freezes the container 370-530 ms.
#   freeze.sh NAME OUT FROZEN RUNNING
P=/home/mfwolffe/lanes/hasu-env/bin/podman
c=px85-$1 out=$2 frozen=$3 running=$4
ms() { date +%s%3N; }
secs() { awk -v m="$1" 'BEGIN { printf "%.3f", m / 1000 }'; }
echo "$(date -u +%FT%TZ) freeze $c: waiting for its rounds (frozen ${frozen} ms, running ${running} ms)"
until [ -e "$out/rounds.started" ] && "$P" container exists "$c" 2>/dev/null; do
    [ -e "$out/rounds.done" ] && exit 0
    sleep 1
done
echo "$(date -u +%FT%TZ) freeze $c: rounds started"
n=0 total=0
while "$P" container exists "$c" 2>/dev/null && [ ! -e "$out/rounds.done" ]; do
    a=$(ms)
    "$P" pause "$c" > /dev/null 2>&1 || break
    sleep "$(secs "$frozen")"
    "$P" unpause "$c" > /dev/null 2>&1
    b=$(ms)
    n=$((n + 1)) total=$((total + b - a))
    sleep "$(secs "$running")"
done
"$P" unpause "$c" > /dev/null 2>&1 || true
echo "$(date -u +%FT%TZ) freeze $c: $n freezes, $total ms frozen in all (from each pause to its unpause's return)"
