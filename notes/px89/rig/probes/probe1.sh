#!/usr/bin/env bash
# px89: the black-box probes, behind the block's locks (launch.sh).
B=$1
S=/home/mfwolffe/lanes/px89/scripts
I=localhost/px89-dhcp:1
echo "== probe: QEMU's user-mode DHCP"
bash $S/ctr.sh $B probe-slirp $I -- bash $S/probes/slirp-dhcp.sh
echo "== probe: dnsmasq on a tap, lease 2m"
bash $S/ctr.sh $B probe-tap $I NET=1 -- bash $S/probes/tap-dnsmasq.sh
echo "== probe: dnsmasq on a tap, lease 30s, T1 10 T2 20"
CTR_ENV="-e LEASE=30s -e T1=10 -e T2=20" bash $S/ctr.sh $B probe-tap2 $I NET=1 -- bash $S/probes/tap-dnsmasq.sh
