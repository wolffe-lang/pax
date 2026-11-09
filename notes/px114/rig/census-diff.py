#!/usr/bin/env python3
"""px114's census (pax#329): a live tree's listing against the image it booted from.

    census-diff.py IMAGE.cpio SERIAL.log...

IMAGE.cpio is the image's root archive (newc, as tools/distribution-root writes it: every
row's mtime 0). Each SERIAL.log is a boot's serial log holding census.keys' session: the
listing between PX114-CENSUS=begin and the first `== ` line (ls -laRn --full-time of every
top-level entry, /dev /proc /sys by their own line only). For each log it prints

    NEW      a path the image does not ship (its mode, owner, size and time)
    CHANGED  a path the image ships whose mtime, size or owner is not the image's
    MISSING  a path the image ships that the live tree lacks

and then the lines the session printed after the listing (the files it hashed)."""
import re
import sys

ENTRY = re.compile(r'^([dlcbps-][rwxsStT-]{9})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+|\d+,\s*\d+)\s+'
                   r'(\d{4}-\d\d-\d\d \S+ \S+) (.*)$')


def image_rows(path):
    blob = open(path, 'rb').read()
    rows, o = {}, 0
    while True:
        h = blob[o:o + 110]
        assert h[:6] == b'070701', 'not a newc archive'
        f = [int(h[i:i + 8], 16) for i in range(6, 110, 8)]
        name = blob[o + 110:o + 110 + f[11] - 1].decode()
        s = (o + 110 + f[11] + 3) & ~3
        o = (s + f[6] + 3) & ~3
        if name == 'TRAILER!!!':
            return rows
        rows['/' + name] = (f[1], f[2], f[3], f[6], f[5])


def live_rows(log):
    t = open(log, 'rb').read()
    t = re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]', b'', t).replace(b'\r', b'').decode('latin-1')
    lines = t.splitlines()
    b = lines.index('PX114-CENSUS=begin')
    e = lines.index('PX114-CENSUS=end')
    live, cur, k = {}, None, b + 1
    while k < e and not lines[k].startswith('== '):
        line = lines[k]
        k += 1
        if line.startswith('/') and line.endswith(':'):
            cur = line[:-1]
            continue
        m = ENTRY.match(line)
        if not m:
            continue
        name = m[7].strip()
        if m[1][0] == 'l':
            name = name.split(' -> ')[0]
        if len(name) > 1 and name[0] == name[-1] == "'":
            name = name[1:-1]
        if name.startswith('/') or cur is None:
            path = name
        elif name == '.':
            path = cur
        elif name == '..':
            continue
        else:
            path = cur.rstrip('/') + '/' + name
        live[path] = (m[1], int(m[3]), int(m[4]), m[5], m[6])
    return live, lines[k:e]


def main(argv):
    img = image_rows(argv[0])
    for log in argv[1:]:
        live, tail = live_rows(log)
        print(f'== {log}: {len(live)} live paths, {len(img)} image rows')
        for p in sorted(live):
            if p == '/':
                continue
            perm, u, g, s, when = live[p]
            if p not in img:
                print('  NEW     ', perm, u, g, s, when, p)
                continue
            mode, uid, gid, size, mtime = img[p]
            changed = []
            if not when.startswith('1970-01-01 00:00:00') or mtime != 0:
                changed.append('mtime ' + when)
            if perm[0] == '-' and str(size) != s:
                changed.append(f'size {size} -> {s}')
            if (u, g) != (uid, gid):
                changed.append(f'owner {uid}:{gid} -> {u}:{g}')
            if changed:
                print('  CHANGED ', p, '; '.join(changed))
        for p in sorted(img):
            if p not in live:
                print('  MISSING ', p)
        for line in tail:
            if not line.startswith('$ '):
                print('  | ' + line)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
