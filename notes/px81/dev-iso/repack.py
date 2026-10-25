"""Replace only pelt and motd in a verified newc payload; retain all other bytes."""
from pathlib import Path
import hashlib
import sys

source, shell, output = map(Path, sys.argv[1:])
blob = source.read_bytes()
pelt = shell.read_bytes()
assert pelt[:4] == b'\x7fELF'
rows = []
offset = 0
seen = set()
changed = set()
sha = lambda b: hashlib.sha256(b).hexdigest()
while True:
    head = blob[offset:offset+110]
    assert len(head) == 110 and head[:6] == b'070701', offset
    fields = [int(head[i:i+8], 16) for i in range(6, 110, 8)]
    length, namesize = fields[6], fields[11]
    namebytes = blob[offset+110:offset+110+namesize]
    assert namebytes[-1:] == b'\0'
    name = namebytes[:-1].decode('utf-8')
    start = (offset + 110 + namesize + 3) & ~3
    data = blob[start:start+length]
    assert len(data) == length
    offset = (start+length+3) & ~3
    assert name not in seen, name
    seen.add(name)
    old = data
    if name in ('bin/sh', 'bin/pelt'):
        assert fields[1] & 0o170000 == 0o100000
        data = pelt
        changed.add(name)
    if name == 'etc/motd':
        text = data.decode('utf-8').splitlines()
        text[0] = 'PAX dev: friendly pelt 0b5eaa5, wolf 0.2.35; px80 dev payload with the current PAX kernel.'
        text += ['', 'Friendly editing is opt-in: set -o friendly -o suggest -o histsearch',
                 "Optional dim/green palette: PELT_COLORS='command=green:shadow=brblack+dim'",
                 'Try: echo prefix_suffix, then type echo prefix; abbr add hi "echo hello"; hi Space; !!; echo !$; Alt-.']
        data = ('\n'.join(text)+'\n').encode()
        changed.add(name)
    print(name, sha(old), sha(data), 'changed' if data != old else 'retained')
    fields[6] = len(data)
    h = b'070701' + b''.join(f'{n:08x}'.encode() for n in fields)
    rec = h + namebytes
    rec += b'\0' * (-len(rec) % 4)
    rec += data
    rec += b'\0' * (-len(rec) % 4)
    rows.append(rec)
    if name == 'TRAILER!!!': break
assert changed == {'bin/sh', 'bin/pelt', 'etc/motd'}, changed
assert not blob[offset:].strip(b'\0'), 'nonzero archive trailer'
output.write_bytes(b''.join(rows))
print('PAYLOAD', sha(output.read_bytes()), len(rows), 'records; exactly three allowed replacements')
