#!/usr/bin/env python3
"""px92: the dev image's compiler files out of the dev archive, and the root partition of the dev leg's target
(its allocated extents) as an image debugfs can read."""
import importlib.machinery, importlib.util, os, sys
from pathlib import Path
root, cpio, target, out = map(Path, sys.argv[1:5])
loader = importlib.machinery.SourceFileLoader('pax_distribution', str(root/'tools/distribution-root'))
spec = importlib.util.spec_from_loader(loader.name, loader); m = importlib.util.module_from_spec(spec); loader.exec_module(m)
rows = m.read_cpio(cpio.read_bytes())
n = 0
for name, (mode, uid, gid, data) in rows.items():
    if name.startswith(('usr/bin/', 'usr/lib/wolf-musl/', 'usr/share/wolf/compiler-std/')) and mode & 0o170000 == 0o100000:
        p = out/'tree'/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); p.chmod(mode & 0o777); n += 1
print(f'{n} files of the dev toolchain')
start = 69206016
rb = 1000135659520
with open(target, 'rb') as f, open(out/'root.img', 'wb') as o:
    o.truncate(rb)
    at, end = start, start + rb
    while at < end:
        try:
            data = os.lseek(f.fileno(), at, os.SEEK_DATA)
        except OSError:
            break
        if data >= end:
            break
        hole = min(os.lseek(f.fileno(), data, os.SEEK_HOLE), end)
        f.seek(data); o.seek(data - start)
        left = hole - data
        while left:
            b = f.read(min(left, 1 << 20)); o.write(b); left -= len(b)
        at = hole
print('root partition extracted')
