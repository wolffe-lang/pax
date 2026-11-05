#!/usr/bin/env bash
# px89 probe: QEMU's user netdev and a socket netdev on one hub, no
# machine; slirp-dhcp.py at the socket's end. Inside the container.
set -u
P=/home/mfwolffe/lanes/px89/scripts/probes
qemu-system-x86_64 --version | head -1
qemu-system-x86_64 -M none -nodefaults -nographic -display none -monitor none -serial none \
  -netdev user,id=u,ipv6=off -netdev socket,id=s,udp=127.0.0.1:47681,localaddr=127.0.0.1:47680 \
  -netdev hubport,id=h1,hubid=0,netdev=u -netdev hubport,id=h2,hubid=0,netdev=s &
q=$!
sleep 1
python3 -I "$P/slirp-dhcp.py" 47680 47681
rc=$?
kill $q; wait $q 2>/dev/null
exit $rc
