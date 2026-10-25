#!/usr/bin/env python3
"""Independent assertions on the typed playground session (no golden edits)."""
from pathlib import Path
import re
import sys
s = Path(sys.argv[1]).read_bytes().decode('utf-8', 'replace').replace('\r', '')
s = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', s)
s = re.sub(r'\x1b[()][A-Za-z0-9]|\x1b[c78DEHM=>]', '', s)
boots = s.split('PAX: the console')[1:]
assert len(boots) == 2, len(boots)
for i, boot in enumerate(boots, 1):
    assert re.search(r'^root: PARTUUID=[0-9a-fA-F-]+ \(vda2\) on /: ext2, read-write, write-back$', boot, re.M), boot
    assert f'clean, mount {i};' in boot, boot
    assert 'fstab: /dev/vda2 is /: ext2, read-write, write-back' in boot
assert 'marked clean; restarting' in boots[0]
second = boots[1]
def answer(command):
    assert command in second, command
    return second.split(command, 1)[1].split('$ ', 1)[0]
assert '\nhello\n' in answer('cat /etc/motd')
assert '/usr/share/tunes' in answer('lope list')
assert 'written on PAX, before the reboot' in answer('cat notes.txt')
assert 'root wrote this in /root' in answer('cat /root/note')
assert '/dev/root / ext2 rw,relatime 0 0' in answer('cat /proc/self/mounts')
assert 'tmpfs /tmp tmpfs' in answer('cat /proc/self/mounts')
assert '\nhalt\n' in second
print('PASS playground: both root boots, reboot persistence, lope, notes, mount table and halt')
