# /etc/wire.sh — px89's metal leg (tools/mkwire puts it on the stick, the
# token and the ESP's offset filled in): the lease kernel/dhcp took, the
# router's answer to the kernel's echo, one TCP connection a line of the
# stick's /pax/wire-target (the router's port 80 when it names none), and
# the record appended to /pax/logs/wire-<n>.txt on the stick. Only the
# disk whose ESP holds this stick's token is written; every other disk is
# only read (`paxfat cat` opens it read-only).
TOKEN=@TOKEN@
OFF=@OFF@
out=/tmp/wire.txt
echo "wire: waiting for the lease (kernel/dhcp, /var/lib/dhcp/pax.lease)"
n=0
while [ ! -e /var/lib/dhcp/pax.lease ] && [ "$n" -lt 60 ]; do
    sleep 1
    n=$((n + 1))
done
echo "px89 wire record" > "$out"
echo "== /var/lib/dhcp/pax.lease (waited $n s)" >> "$out"
cat /var/lib/dhcp/pax.lease >> "$out" 2>&1
echo "== /etc/resolv.conf" >> "$out"
cat /etc/resolv.conf >> "$out" 2>&1
router=
if [ -e /var/lib/dhcp/pax.lease ]; then
    while read -r k v; do
        if [ "$k" = router ]; then router=$v; fi
    done < /var/lib/dhcp/pax.lease
fi
stick=
for d in /dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde /dev/sdf /dev/sdg /dev/sdh; do
    if [ -e "$d" ]; then
        t=$(paxfat --offset "$OFF" cat "$d" /pax/wire-stick 2>/dev/null)
        if [ "$t" = "$TOKEN" ]; then stick=$d; fi
    fi
done
echo "== the stick: ${stick:-not found}" >> "$out"
probes=0
if [ -n "$stick" ] && paxfat --offset "$OFF" cat "$stick" /pax/wire-target > /tmp/wire-target 2>/dev/null; then
    while read -r ip port; do
        case $ip in ''|'#'*) continue ;; esac
        echo "== tcpprobe $ip $port" >> "$out"
        tcpprobe "$ip" "$port" >> "$out" 2>&1
        probes=$((probes + 1))
    done < /tmp/wire-target
fi
if [ "$probes" = 0 ]; then
    if [ -n "$router" ]; then
        echo "== tcpprobe $router 80 (the router: /pax/wire-target names no host)" >> "$out"
        tcpprobe "$router" 80 >> "$out" 2>&1
    else
        echo "== no lease, no router: no TCP connection made" >> "$out"
    fi
fi
if [ -n "$stick" ]; then
    k=1
    while paxfat --offset "$OFF" cat "$stick" "/pax/logs/wire-$k.txt" > /dev/null 2>&1; do
        k=$((k + 1))
    done
    if paxfat --offset "$OFF" append "$stick" "$out" "/pax/logs/wire-$k.txt"; then
        echo "== written to /pax/logs/wire-$k.txt on $stick" >> "$out"
    else
        echo "== NOT written to $stick (paxfat append failed)" >> "$out"
    fi
else
    echo "== no disk holds this stick's token: the record is on this screen only" >> "$out"
fi
cat "$out"
