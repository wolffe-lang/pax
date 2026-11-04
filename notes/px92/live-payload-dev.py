#!/usr/bin/env python3
"""px92: px86's live payload (notes/px86's live-payload.py, BOOT.md's live-only login entry) applied to a given
archive, here the dev variant, written to a new file; every other archive row verified unchanged.

    live-payload-dev.py PAX_ROOT IN.cpio OUT.cpio OUT.txt
"""
from pathlib import Path
import hashlib, importlib.machinery, importlib.util, sys
root, src, out, txt = map(Path, sys.argv[1:])
loader = importlib.machinery.SourceFileLoader('pax_distribution', str(root/'tools/distribution-root'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)
assert not out.exists()
rows = m.read_cpio(src.read_bytes()); before = dict(rows)
rows['etc/pax-live-login'] = (0o100644, 0, 0, (root/'user/usb-login.sh').read_bytes())
rows['etc/pax-run'] = (0o100644, 0, 0, b'/bin/pelt /etc/pax-live-login\n')
rows.setdefault('root', (0o40700, 0, 0, b''))
rows['etc/pax-files.sha256'] = (0o100644, 0, 0, ''.join(
    f'{hashlib.sha256(data).hexdigest()}  {name}\n'
    for name, (mode, uid, gid, data) in sorted(rows.items())
    if mode & 0o170000 != 0o040000 and name != 'etc/pax-files.sha256').encode())
allowed = {'etc/pax-live-login', 'etc/pax-run', 'etc/pax-files.sha256', 'root'}
changed = {k for k in rows.keys() | before.keys() if rows.get(k) != before.get(k)}
assert changed <= allowed, changed
m.write_cpio(rows, out)
assert m.read_cpio(out.read_bytes()) == rows
txt.write_text('Live-only archive changes: '+', '.join(sorted(changed))+'\n'
    +f'All other modes, owners and bytes equal the verified {src.name}.\n')
print(txt.read_text(), end='')
