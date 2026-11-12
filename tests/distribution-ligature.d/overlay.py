#!/usr/bin/env python3
"""tests/distribution-ligature.d/overlay.py BASE.cpio OUT.cpio SRC_DIR LDTIME SESSION

The suite's test archive: BASE (the dev image's archive, read-only) with every member as it is, plus
/usr/share/distribution-ligature/session.sh, /usr/share/distribution-ligature/src/ (SRC_DIR's files:
the programs' sources) and /usr/libexec/distribution-ligature/ldtime. A path BASE already has is
refused, so nothing of the image under test is replaced. The writer is tools/distribution-root's."""
import hashlib
import sys
from pathlib import Path


def read_cpio(blob):
    rows, off = {}, 0
    while True:
        h = blob[off:off + 110]
        assert h[:6] == b'070701', 'the base is not newc'
        f = [int(h[i:i + 8], 16) for i in range(6, 110, 8)]
        name = blob[off + 110:off + 110 + f[11] - 1].decode()
        start = (off + 110 + f[11] + 3) & ~3
        data = blob[start:start + f[6]]
        off = (start + f[6] + 3) & ~3
        if name == 'TRAILER!!!':
            return rows
        rows[name] = (f[1], f[2], f[3], data)


def write_cpio(rows, output):
    with output.open('wb') as out:
        for ino, (name, (mode, uid, gid, data)) in enumerate(sorted(rows.items()) + [('TRAILER!!!', (0, 0, 0, b''))], 1):
            encoded = name.encode() + b'\0'
            fields = [ino, mode, uid, gid, 2 if mode & 0o170000 == 0o040000 else 1, 0, len(data), 0, 0, 0, 0, len(encoded), 0]
            out.write(b'070701' + b''.join(f'{n:08x}'.encode() for n in fields) + encoded)
            out.write(b'\0' * (-out.tell() % 4))
            out.write(data)
            out.write(b'\0' * (-out.tell() % 4))


def main():
    base, out, src, ldtime, session = map(Path, sys.argv[1:6])
    rows = read_cpio(base.read_bytes())

    def put(name, data, mode):
        for parent in reversed(Path(name).parents):
            if parent.as_posix() != '.':
                rows.setdefault(parent.as_posix(), (0o40755, 0, 0, b''))
        assert name not in rows, 'the image under test already has ' + name
        rows[name] = (0o100000 | mode, 0, 0, data)

    put('usr/libexec/distribution-ligature/ldtime', ldtime.read_bytes(), 0o755)
    put('usr/share/distribution-ligature/session.sh', session.read_bytes(), 0o644)
    count = 0
    for f in sorted(src.rglob('*')):
        if f.is_file() and not f.is_symlink() and '.git' not in f.relative_to(src).parts:
            put('usr/share/distribution-ligature/src/' + f.relative_to(src).as_posix(), f.read_bytes(), 0o644)
            count += 1
    write_cpio(rows, out)
    print(f'overlay: {out.name} {out.stat().st_size} bytes, sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}, '
          f'{count} source files, ldtime and the session added; nothing of the image replaced')


main()
