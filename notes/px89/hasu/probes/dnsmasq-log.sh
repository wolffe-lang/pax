#!/usr/bin/env bash
# px89 witness (CI's red at D5): who can read the log dnsmasq 2.91 writes
# with --log-facility when it runs as root (CI's dhcp-wire runs it through
# sudo; the suite reads the log as the runner's user). In a lane container:
# dnsmasq as root on a dummy interface for 2 s, then the log's mode and
# owner, and a read as root and as uid 1001 (the runner's uid on GitHub's
# ubuntu-24.04 images).
set -uo pipefail
w=$1; rm -rf "$w"; mkdir -p "$w"; chmod 755 "$w"
umask 022
dpkg-query -W dnsmasq-base
ip link add pxlog0 type dummy && ip addr add 192.168.97.1/24 dev pxlog0 && ip link set pxlog0 up
dnsmasq --no-daemon --user=root --port=0 --interface=pxlog0 --bind-interfaces --dhcp-range=192.168.97.50,192.168.97.60,255.255.255.0,2m \
    --dhcp-leasefile="$w/leases" --log-dhcp --log-facility="$w/dnsmasq-1.log" &
p=$!; sleep 2; kill -TERM $p; wait $p
ip link del pxlog0
echo "== the log: $(stat -c '%a %U:%G %s bytes' "$w/dnsmasq-1.log")"
echo "== as root: $(grep -c 'started' "$w/dnsmasq-1.log") 'started' line(s)"
echo "== as uid 1001: grep -c says '$(setpriv --reuid=1001 --regid=1001 --clear-groups grep -c started "$w/dnsmasq-1.log" 2>/dev/null)'; its error: $(setpriv --reuid=1001 --regid=1001 --clear-groups grep -c started "$w/dnsmasq-1.log" 2>&1 >/dev/null)"
