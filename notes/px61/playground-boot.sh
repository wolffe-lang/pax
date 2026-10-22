#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/playground-boot.pid"
ulimit -c 0
uptime
mkdir -p "$L/play-session"
sha256sum "$L/out/pax-playground.iso"
sha256sum "$L/out/pax-playground.iso"
taskset -c 8-11 "$L/pax/tools/qemu-halt" --firmware bios --serial "$L/play-session/play.log" --timeout 900 \
    --accel tcg --qemu -m --qemu 512M --elf "$(cat "$L/w/elf.path")" --marker 'halt|PANIC .*' \
    --type "$L/pax/notes/px61/playground.keys" --prompt '$ ' "$L/out/pax-playground.iso" > "$L/play-session/play.verdict" 2>&1
tr -d '\r' < "$L/play-session/play.log" > "$L/play-session/play.txt"
python3 -I - "$L/play-session/play.txt" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(errors='replace')
for row in ('hi', '/home/pax', 'hello, wolf', 'std: WOLF, roundtrip true', 'std-st=0'):
    assert row in s.splitlines(), 'missing playground row '+row
assert 'PAX: init /bin/env ended with status 0; nothing left to run' in s
print('playground maintainer session: PASS')
PY
uptime
cat "$L/play-session/play.verdict"
