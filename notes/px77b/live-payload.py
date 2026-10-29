#!/usr/bin/env python3
"""Apply BOOT.md's existing live-only entry; verify every other archive row."""
from pathlib import Path
import hashlib, importlib.machinery, importlib.util, sys
root, out = map(Path, sys.argv[1:])
loader = importlib.machinery.SourceFileLoader('pax_distribution', str(root/'tools/distribution-root'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)
original = out/'release-original.cpio'
(out/'release.cpio').rename(original)
rows = m.read_cpio(original.read_bytes()); before = dict(rows)
rows['etc/pax-live-login'] = (0o100644, 0, 0, (root/'user/usb-login.sh').read_bytes())
rows['etc/pax-run'] = (0o100644, 0, 0, b'/bin/pelt /etc/pax-live-login\n')
rows.setdefault('root', (0o40700, 0, 0, b''))
# Reflect the live-only rows in the existing file inventory.
rows['etc/pax-files.sha256'] = (0o100644, 0, 0, ''.join(
    f'{hashlib.sha256(data).hexdigest()}  {name}\n'
    for name, (mode, uid, gid, data) in sorted(rows.items())
    if mode & 0o170000 != 0o040000 and name != 'etc/pax-files.sha256').encode())
allowed = {'etc/pax-live-login', 'etc/pax-run', 'etc/pax-files.sha256', 'root'}
changed = {k for k in rows.keys() | before.keys() if rows.get(k) != before.get(k)}
assert changed <= allowed
m.write_cpio(rows, out/'release.cpio')
assert m.read_cpio((out/'release.cpio').read_bytes()) == rows
(out/'live-payload.txt').write_text('Live-only archive changes: '+', '.join(sorted(changed))+'\n'
    +'All other modes, owners and bytes equal the verified release archive.\n'
    +'No kernel, program binary, pin, fstab or disk-root configuration changed.\n')
print((out/'live-payload.txt').read_text(), end='')
