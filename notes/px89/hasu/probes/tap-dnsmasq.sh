#!/usr/bin/env bash
# px89 probe: a tap inside the container's own network namespace,
# dnsmasq on it (a black box), QEMU's tap netdev and a socket netdev on
# one hub (no machine), slirp-dhcp.py at the socket's end as the client.
# LEASE is dnsmasq's lease time; T1/T2 optional option 58/59 values.
set -u
P=/home/mfwolffe/lanes/px89/scripts/probes
W=/home/mfwolffe/lanes/px89/tmp/tapprobe-$$
mkdir -p $W
LEASE=${LEASE:-2m}
ip tuntap add dev tap0 mode tap || { echo "tuntap: refused"; exit 3; }
ip addr add 192.168.89.1/24 dev tap0
ip link set tap0 up
ip -br addr
opts=()
[ -n "${T1:-}" ] && opts+=(--dhcp-option=option:T1,$T1)
[ -n "${T2:-}" ] && opts+=(--dhcp-option=option:T2,$T2)
dnsmasq --version | head -1
dnsmasq --no-daemon --user=root --port=0 --interface=tap0 --bind-interfaces --dhcp-authoritative \
  --dhcp-range=192.168.89.50,192.168.89.99,255.255.255.0,$LEASE --dhcp-option=option:router,192.168.89.1 \
  --dhcp-option=option:dns-server,192.168.89.53,192.168.89.54 --dhcp-leasefile=$W/leases --log-dhcp --log-facility=$W/dnsmasq.log "${opts[@]}" &
d=$!
qemu-system-x86_64 -M none -nodefaults -nographic -display none -monitor none -serial none \
  -netdev tap,id=t,ifname=tap0,script=no,downscript=no -netdev socket,id=s,udp=127.0.0.1:47691,localaddr=127.0.0.1:47690 \
  -netdev hubport,id=h1,hubid=0,netdev=t -netdev hubport,id=h2,hubid=0,netdev=s &
q=$!
sleep 2
python3 -I "$P/slirp-dhcp.py" 47690 47691
rc=$?
kill $q $d; wait $q $d 2>/dev/null
echo "== dnsmasq log"; cat $W/dnsmasq.log; echo "== leases"; cat $W/leases
exit $rc
