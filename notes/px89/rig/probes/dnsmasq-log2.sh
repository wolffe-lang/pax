#!/usr/bin/env bash
# px89 witness 2: a log the caller (uid 1001) creates before dnsmasq starts
# as root: does dnsmasq keep its owner and mode, and does it write into it?
# And what this image offers a non-root CI mirror: sudo, /dev/kvm, tun.
set -uo pipefail
w=$1; rm -rf "$w"; mkdir -p "$w"; chown 1001:1001 "$w"; chmod 755 "$w"
umask 022
setpriv --reuid=1001 --regid=1001 --clear-groups sh -c "umask 022; : > '$w/dnsmasq-1.log'"
echo "== before: $(stat -c '%a %u:%g %s bytes' "$w/dnsmasq-1.log")"
ip link add pxlog0 type dummy && ip addr add 192.168.97.1/24 dev pxlog0 && ip link set pxlog0 up
dnsmasq --no-daemon --user=root --port=0 --interface=pxlog0 --bind-interfaces --dhcp-range=192.168.97.50,192.168.97.60,255.255.255.0,2m \
    --dhcp-leasefile="$w/leases" --log-dhcp --log-facility="$w/dnsmasq-1.log" &
p=$!; sleep 2; kill -TERM $p; wait $p
ip link del pxlog0
echo "== after: $(stat -c '%a %u:%g %s bytes' "$w/dnsmasq-1.log"); leases: $(stat -c '%a %u:%g' "$w/leases" 2>/dev/null || echo none)"
echo "== as uid 1001: $(setpriv --reuid=1001 --regid=1001 --clear-groups grep -c started "$w/dnsmasq-1.log" 2>&1) 'started' line(s)"
echo "== sudo: $(command -v sudo || echo none); setpriv: $(command -v setpriv); useradd: $(command -v useradd)"
echo "== /dev/kvm: $(stat -c '%a %u:%g' /dev/kvm 2>/dev/null || echo none); /dev/net/tun: $(stat -c '%a %u:%g' /dev/net/tun)"
echo "== os: $(. /etc/os-release; echo $PRETTY_NAME)"
