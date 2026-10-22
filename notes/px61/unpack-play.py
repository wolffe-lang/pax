"""Extract our newc image to a fresh root and record its ownership map."""
from pathlib import Path
import os
import stat
import sys

archive, root, owners = map(Path, sys.argv[1:])
root.mkdir(parents=True, exist_ok=False)
data = archive.read_bytes()
at = 0
rows = []
while at < len(data):
    h = data[at:at + 110]
    if h[:6] != b'070701':
        raise SystemExit('not a newc header at ' + str(at))
    f = [int(h[6 + 8*i:14 + 8*i], 16) for i in range(13)]
    mode, uid, gid, size, namesize = f[1], f[2], f[3], f[6], f[11]
    at += 110
    name = data[at:at + namesize - 1].decode()
    at = (at + namesize + 3) & ~3
    payload = data[at:at + size]
    at = (at + size + 3) & ~3
    if name == 'TRAILER!!!':
        break
    p = Path(name)
    if p.is_absolute() or '..' in p.parts:
        raise SystemExit('unsafe archive path: ' + name)
    if str(p) == '.':
        continue
    dest = root / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    if stat.S_ISDIR(mode):
        dest.mkdir(exist_ok=True)
    elif stat.S_ISREG(mode):
        dest.write_bytes(payload)
    else:
        raise SystemExit('unsupported archive kind: ' + name)
    dest.chmod(stat.S_IMODE(mode))
    os.utime(dest, (0, 0))
    rows.append('/%s %o %d %d\n' % (p.as_posix(), stat.S_IMODE(mode), uid, gid))
owners.write_text(''.join(rows))
print('extracted', len(rows), 'entries')
