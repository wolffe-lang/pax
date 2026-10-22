#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/boreutils-twice.pid"
ulimit -c 0
uptime
U=$(awk '{print $1}' "$L/w/bore/sums.txt" | tr '\n' ' ')
podman run --rm --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e U="$U" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
    set -euo pipefail; cd "$L/pax"
    tools/mkboreutils "$L/bin/bore-all-second" $U
'
cmp "$L/w/bore/sums.txt" "$L/bin/bore-all-second/sums.txt"
sha256sum "$L/w/bore/sums.txt" "$L/bin/bore-all-second/sums.txt"
python3 -I - "$L" <<'PY'
from pathlib import Path
import hashlib, sys
l = Path(sys.argv[1])
for turn in range(2):
    count = 0
    for directory in (l/'w/bore', l/'bin/bore-all-second'):
        for line in (directory/'sums.txt').read_text().splitlines():
            name, digest, size = line.split()
            b = (directory/name).read_bytes()
            assert hashlib.sha256(b).hexdigest() == digest and len(b) == int(size), name
            count += 1
    assert count == 94
    print('PASS all 47 static digests in both builds, independent read', turn+1)
PY
uptime
echo 'boreutils twice: PASS'
