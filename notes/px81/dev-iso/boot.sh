#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px81
cd "$L/pax"
W=$L/dev-iso
cat > "$W/smoke.keys" <<'KEYS'
echo PX81-PID=$$
^~set -o friendly -o suggest -o histsearch
^~echo PX81-DEV-FRIENDLY
^~set +o friendly
^~exit 0
KEYS
for firmware in bios uefi; do
 PAX_TYPE_PAUSE=2 tools/qemu-halt --firmware "$firmware" --serial "$W/$firmware.serial.log" \
  --timeout 300 --qemu -m --qemu 2048M --elf "$L/build/mpx5-pelt/native/kmain_console.elf" \
  --type "$W/smoke.keys" --prompt '$ ' --marker 'halt|PANIC .*' \
  "$W/pax-dev-pelt-friendly.iso" > "$W/$firmware.halt.log" 2>&1
 python3 -I - "$W/$firmware.serial.log" <<'PY'
from pathlib import Path
import re,sys
b=Path(sys.argv[1]).read_bytes()
n=re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]', b'', b).replace(b'\r',b'')
for line in [b'PX81-PID=1', b'PX81-DEV-FRIENDLY', b'PAX: init /bin/env ended with status 0; nothing left to run']:
 assert line in n.splitlines(), line
assert b'\x1b[0;36m' in b
print('PASS dev ISO: pelt pid1, opt-in friendly colours, clean halt')
PY
done
