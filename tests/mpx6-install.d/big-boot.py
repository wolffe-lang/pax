#!/usr/bin/env python3
"""Boot a lane-owned installed target alone, reach pelt, then exit cleanly.
No image-wide copy/hash: inspect the root's fixed superblock window afterward.
"""
import argparse
from pathlib import Path
import re
import struct
import subprocess

p = argparse.ArgumentParser()
p.add_argument('repo', type=Path)
p.add_argument('work', type=Path)
p.add_argument('kernel', type=Path)
p.add_argument('--firmware', choices=['bios', 'uefi'], default='bios')
a = p.parse_args()
keys = a.work / ('big-boot-' + a.firmware + '.keys')
keys.write_text('exit\n')
serial = a.work / ('big-boot-' + a.firmware + '.serial')
image = a.work / 'target.img'
r = subprocess.run([str(x) for x in [a.repo / 'tools/qemu-halt', '--boot-disk', '--firmware', a.firmware,
    '--elf', a.kernel, '--timeout', '180', '--serial', serial, '--marker', 'halt', '--type', keys,
    '--prompt', '$ ', image]], capture_output=True)
(a.work / ('big-boot-' + a.firmware + '.log')).write_bytes(r.stdout + r.stderr)
assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
text = serial.read_text(errors='replace').replace('\r', '')
assert re.search(r'root: PARTUUID=[0-9a-fA-F-]+ \(vda2\) on /: ext2, read-write', text), text
assert '$ ' in text and 'PANIC' not in text and 'wolf-trap' not in text, text
with image.open('rb') as f:
    f.seek(69206016 + 1024)
    sb = f.read(1024)
assert struct.unpack_from('<H', sb, 58)[0] == 1, 'root not clean after exit'
assert struct.unpack_from('<H', sb, 52)[0] >= 1, 'root never mounted'
print('PASS I-big-boot-%s: target alone, interactive prompt, clean exit; capacity %d' % (a.firmware, image.stat().st_size), flush=True)
