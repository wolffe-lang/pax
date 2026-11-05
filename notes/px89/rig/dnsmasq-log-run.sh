#!/usr/bin/env bash
# px89: the dnsmasq log witness in a lane container (NET=1 for the dummy
# interface). launch.sh runs it as `dnsmasq-log-run.sh BLOCK`.
set -uo pipefail
L=/home/mfwolffe/lanes/px89
CTR_WD=$L bash "$L/scripts/ctr2.sh" "$1" dnslog localhost/px89-dhcp:1 NET=1 -- bash "$L/scripts/probes/dnsmasq-log.sh" "$L/build/dnslog"
