#!/bin/bash
# px35 on kasumi: pax#29 N8 counted. Runs TREE's mpx4-net (native bios, every leg) N times with K busy
# loops on CPUS and the suite under taskset -c CPUS, and reads each peer capture: the two echo requests
# the ARP answer lets go (seq 3, 4), how far apart, and whether a reply landed between them.
# usage: netrace.sh TREE N K CPUS OUTDIR
set -u
tree=$1 n=$2 k=$3 cpus=$4 out=$5
mkdir -p "$out"; cd "$tree" || exit 2
export PAX_CACHE=$HOME/lanes/px35/cache PAX_REQUIRE_UEFI=1 TMPDIR=$HOME/lanes/px35/tmp
pids=()
for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
for ((i = 1; i <= n; i++)); do
    taskset -c $cpus env --default-signal=INT,QUIT,HUP,TERM tests/mpx4-net --images build/mpx4-net --firmware bios --tier native > "$out/run-$i.out" 2>&1
    rc=$?
    cp build/mpx4-net-native-bios-peer.pcap "$out/peer-$i.pcap" 2>/dev/null
    v=$(python3 - "$out/peer-$i.pcap" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read(); o = 24; ev = []
while o < len(d) and len(ev) < 4:
    ts, tu, cl, ol = struct.unpack('<IIII', d[o:o+16]); f = d[o+16:o+16+cl]; o += 16 + cl
    if f[12:14] == b'\x08\x00' and f[23] == 1:
        ihl = (f[14] & 15) * 4; m = f[14+ihl:]
        ev.append(('req' if m[0] == 8 else 'rep') + str(struct.unpack('>H', m[6:8])[0]) + '@' + str(int(ts * 1e6 + tu)))
t0 = int(ev[0].split('@')[1])
print(' '.join(e.split('@')[0] + '+' + str(int(e.split('@')[1]) - t0) for e in ev))
PY
)
    echo "$i rc=$rc N8=$(grep -a -c 'PASS N8 native bios peer' "$out/run-$i.out") $v" >> "$out/lines.txt"
    rm -f "$out/peer-$i.pcap"
done
for p in "${pids[@]}"; do kill "$p"; done
echo done > "$out/done"
