#!/usr/bin/env python3
"""SMP-BUILD's boot, timed from outside (the processor census's method): tools/qemu-halt boots the fixture's
image at `-smp N` with 2 GiB, and each BENCH BEGIN/END line is stamped by the host's monotonic clock as
it lands in the serial log (2 ms observation grain; the times include fork, exec and wait, and the
markers' own serial cost, the same in both batches). The stamps go to SERIAL.times as JSON
([round, jobs, seconds], …); rows.py --kind build judges them with the transcript.

  python3 -I tests/mpx6-smp.d/build.py FIRMWARE N TIMEOUT ELF ISO SERIAL

Exit: tools/qemu-halt's status (0 when the kernel halted after the bench).
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
fw, n, timeout, elf, iso, serial = sys.argv[1:]
root = Path(__file__).resolve().parent.parent.parent
log = Path(serial)
cmd = [str(root / 'tools/qemu-halt'), '--firmware', fw, '--timeout', timeout, '--no-screen', '--serial', serial,
       '--elf', elf, '--marker', 'halt', '--qemu', '-smp', '--qemu', n, '--qemu', '-m', '--qemu', '2048', iso]
seen, begins, times = 0, {}, []
start = last = time.monotonic()
with open(serial + '.qemu', 'w') as f:
    p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    while True:
        text = log.read_text(errors='replace').replace('\r', '') if log.exists() else ''
        lines = text[:text.rfind('\n') + 1].splitlines()
        for line in lines[seen:]:
            m = re.fullmatch(r'BENCH (BEGIN|END) round=(\d+) jobs=(\d+)(.*)', line)
            if not m:
                continue
            now, key = time.monotonic(), (int(m[2]), int(m[3]))
            if m[1] == 'BEGIN':
                begins[key] = now
            elif key in begins:
                times.append([key[0], key[1], round(now - begins.pop(key), 6)])
        seen = len(lines)
        if p.poll() is not None:
            break
        if time.monotonic() - last >= 60:
            print(f'mpx6-smp: build boot at {n} running {time.monotonic() - start:.0f} s', flush=True)
            last = time.monotonic()
        try:
            p.wait(timeout=0.002)
        except subprocess.TimeoutExpired:
            pass
Path(serial + '.times').write_text(json.dumps(times))
sys.exit(p.returncode)
