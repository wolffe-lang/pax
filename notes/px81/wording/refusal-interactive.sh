#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px81
W=$L/wording
for role in root pax; do
 argv=(/bin/sh -i -m)
 [ "$role" = root ] || argv=(/bin/as 1000 1000 /bin/sh -i -m)
 tools/linux-tree --root "$W/xroot" --keys "$L/refusal.keys" --prompt '$ ' --argv0 "${argv[0]}" \
 --size 512m --rdev --nsproc --owners "$W/owners" "$W/refusal-$role.tty" -- "${argv[@]}"
done
python3 -I - <<'PY'
from pathlib import Path
import re
for role in ('root','pax'):
 p=Path('/home/mfwolffe/lanes/px81/wording')/('refusal-'+role+'.tty')
 b=p.read_bytes(); n=re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]',b'',b).replace(b'\r',b'')
 want=b"pelt: line 50: $'\\377': a byte that is not UTF-8 cannot be carried yet (pelt#65)"
 assert want in n.splitlines(),n
 assert b'REFUSE-STATUS=2' in n.splitlines(),n
 assert b'EXECUTED' not in n.splitlines(),n
 assert Path(str(p)+'.rc').read_text().strip()=='0'
 print('PASS interactive',role,': exact line50 refusal, status2, command not invoked, shell continued')
PY
