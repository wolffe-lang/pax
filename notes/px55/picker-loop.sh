#!/bin/bash
# px55 on kasumi (pax#89): the pickers, 1,000 picks each, in px13-ubuntu with --network none (a network
# namespace of its own: nothing reaches the host's ports or another lane's), its ip_local_port_range read
# first: the old picker (a TCP socket bound to port 0, its port read, closed: tests/mpx4-session's free_port
# and, n at a time, tools/lobo-session's free_ports before px55), and the new ones (tests/mpx4-session's
# free_port as the suite defines it; tools/lobo-session --free-ports 1 and 6). Each pick's port is kept.
#   picker-loop.sh OUTDIR
L=$HOME/lanes/px55; P=$L/pax; O=$1
mkdir -p $O
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "
cd $P
echo \"kernel: \$(uname -r); ip_local_port_range: \$(cat /proc/sys/net/ipv4/ip_local_port_range); tree: \$(git log --oneline -1 2>/dev/null)\"
python3 - $O/old.txt <<'PY'
import socket, sys
lo, hi = map(int, open('/proc/sys/net/ipv4/ip_local_port_range').read().split())
got = []
for _ in range(1000):
    s = socket.socket(); s.bind(('127.0.0.1', 0)); got.append(s.getsockname()[1]); s.close()
open(sys.argv[1], 'w').write(''.join('%d\n' % q for q in got))
print('old picker: %d picks, %d inside %d-%d, %d at 49152 and up, ports %d to %d' % (len(got), sum(lo <= q <= hi for q in got), lo, hi, sum(q >= 49152 for q in got), min(got), max(got)))
PY
eval \"\$(sed -n '/^free_port() {/,/^}/p' tests/mpx4-session)\"
for i in \$(seq 1000); do free_port; done > $O/session-new.txt
python3 - $O/session-new.txt <<'PY'
import sys
lo, hi = map(int, open('/proc/sys/net/ipv4/ip_local_port_range').read().split())
got = [int(l) for l in open(sys.argv[1])]
print('mpx4-session free_port (new): %d picks, %d inside %d-%d, %d at 49152 and up, ports %d to %d' % (len(got), sum(lo <= q <= hi for q in got), lo, hi, sum(q >= 49152 for q in got), min(got), max(got)))
PY
python3 tools/lobo-session --free-ports 1 1000; echo \"status \$?\"
python3 tools/lobo-session --free-ports 6 200000; echo \"status \$?\"
" 2>&1 | tee $O/summary.txt
