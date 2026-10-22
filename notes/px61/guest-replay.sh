#!/usr/bin/env bash
# Same programs and keys under a real Linux kernel, never its source.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/guest-replay.pid"
ulimit -c 0
uptime
W=${PX61_GUEST_IMAGES:-$L/build/mpx5-pelt-r2/mpx5-pelt}
export TMPDIR=$L/tmp
podman run --rm --network none --ulimit core=0:0 -v "$L:$L:Z" localhost/px13-ubuntu \
    cc -static -O1 -o "$L/bin/vmjob" "$L/pax/notes/px52/vmjob.c"
for pass in 1 2; do
  O=${PX61_GUEST_OUT:-$L/guest}/pass-$pass
  mkdir -p "$O"
  while read -r name; do
    role=${name##*-}
    argv='/bin/env HOME=/ /bin/sh -i -m'
    [ "$role" = root ] || argv='/bin/as 1000 1000 /bin/env HOME=/home/pax /bin/sh -i -m'
    if [ -s "$O/$name.tty.rc" ] && [ "$(cat "$O/$name.tty.rc")" = 0 ]; then
      echo "guest $pass $name already recorded, kept"
      continue
    fi
    echo "guest $pass $name begin $(date -Is)"
    taskset -c 8-11 "$L/pax/notes/px61/linux-vm.sh" "$L/pax" "$L/bin/vmjob" "$W/pelt.cpio" \
        "$W/keys/$name.keys" "$argv" "$O" "$name" > "$O/$name.driver.log" 2>&1
    test -s "$O/$name.tty.rc"
    test "$(cat "$O/$name.tty.rc")" = 0
    echo "guest $pass $name done $(date -Is): $(cat "$O/$name.tty.rc")"
  done < "$W/run-names"
done
python3 -I - "$L/guest" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);bad=False
for f in sorted((p/'pass-1').glob('*.tty')):
    def norm(t):return re.sub(r'(?m)^(\[\d+\]) \d+$', r'\1 PID', t)
    a=norm(f.read_text()); b=norm((p/'pass-2'/f.name).read_text())
    same=a==b
    print(('PASS' if same else 'FAIL')+' guest repeated: '+f.name)
    bad |= not same
raise SystemExit(bad)
PY
