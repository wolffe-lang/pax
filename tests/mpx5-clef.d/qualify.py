#!/usr/bin/env python3
"""tests/mpx5-clef.d/qualify.py — the qualification's one list of cases (as02b).

    qualify.py gen ROOT              ROOT/usr/share/clef/qualify.sh from ROOT's corpus.list
    qualify.py split TRANSCRIPT OUT  the transcript's blocks, decoded, as OUT/<case>.{rc,out,obj}
    qualify.py host CLEF ROOT OUT    the same cases run by CLEF on this host, the same layout
    qualify.py compare A B           two layouts byte for byte; one line per difference
    qualify.py oracle TOOLS ROOT A GAS
                                     A's corpus objects against GNU as's (`as --64`), by clef's
                                     own structural comparison (TOOLS: clef's tools/, elf.py)

Every case runs in /usr/share/clef (the image's) or ROOT/usr/share/clef (the host's), so a
source's name in a message is the same on both: `corpus/<census path>` for the 43 x86-64
census sources, `bad/` for the two refused inputs. Outputs go to /tmp/q on the image and to
OUT/run on the host. A case's record is its status, everything it printed (standard output and
standard error, one stream, as the console is), and its output file when it makes one, both
in base64 (what reaches the console is bytes, never re-read text). The image's
script is plain POSIX sh (pelt), one block a case:

    Q <id> <words>
    rc=<status>
    -- out
    <what it printed, base64>
    -- obj
    <the output file, base64>
    Q <id> end

Exit 0, or 1 when `compare`/`oracle` find a difference (each printed), 2 on a usage error.
"""
import base64, os, pathlib, subprocess, sys

DIR = '/usr/share/clef'
CLEF = '/usr/bin/clef'
Q = '/tmp/q'


def cases(root):
    """(id, argv after clef, output file or None, setup) in order."""
    listed = (pathlib.Path(root) / DIR.lstrip('/') / 'corpus.list').read_text().split()
    out = [('version', ['--version'], None, None)]
    for i, src in enumerate(listed, 1):
        out.append(('c%02d' % i, ['--64', '-o', Q + '/c%02d.o' % i, 'corpus/' + src], Q + '/c%02d.o' % i, None))
    isr = 'corpus/pax/boot/isr.S'
    out.append(('expand', ['--expand', isr], None, None))
    out.append(('provenance', ['--provenance', '-o', Q + '/provenance.o', isr], Q + '/provenance.o', None))
    out.append(('c-form', ['-c', 'corpus/pax/boot/io.S', '-o', Q + '/c-form.o', '--target=x86_64-unknown-none-elf'], Q + '/c-form.o', None))
    io = 'corpus/pax/boot/io.S'
    out += [
        ('r-none', [], None, None),
        ('r-option', ['--bogus', io], None, None),
        ('r-c-source', ['bad/main.c'], None, None),
        ('r-target-no-c', ['--target=x86_64-unknown-none-elf', io], None, None),
        ('r-expand-o', ['--expand', '-o', Q + '/r-expand-o.o', io], None, None),
        ('r-foreign', ['--target=aarch64-unknown-none', '-c', io, '-o', Q + '/r-foreign.o'], None, None),
        ('r-same', ['-o', Q + '/self.S', Q + '/self.S'], None, None),
        ('r-missing', ['nosuch.S'], None, None),
        ('r-source', ['--64', '-o', Q + '/keep.o', 'bad/unknown.S'], Q + '/keep.o', 'previous'),
    ]
    return out


def sh_word(w):
    return w if all(c.isalnum() or c in '/._-=+,' for c in w) else "'" + w.replace("'", "'\\''") + "'"


def gen(root):
    lines = ['# qualify.sh — written by tests/mpx5-clef.d/qualify.py (as02b): clef on the',
             '# image over the copied corpus, its expansion and its refusals. POSIX sh.',
             'cd ' + DIR + ' || exit 9', '/bin/mkdir ' + Q + ' || exit 9']
    for cid, argv, obj, setup in cases(root):
        words = ' '.join(sh_word(w) for w in argv)
        lines.append('echo ' + sh_word('Q %s %s' % (cid, words)))
        if setup is not None:
            lines.append('echo %s > %s' % (setup, obj))
        lines.append('%s %s > %s/%s.out 2>&1' % (CLEF, words, Q, cid))
        lines.append('echo "rc=$?"')
        lines.append('echo "-- out"')
        lines.append('/bin/base64 %s/%s.out' % (Q, cid))
        if obj:
            lines.append('echo "-- obj"')
            lines.append('/bin/base64 ' + obj)
        lines.append('echo ' + sh_word('Q %s end' % cid))
    lines.append('echo "Q all end"')
    p = pathlib.Path(root) / DIR.lstrip('/') / 'qualify.sh'
    p.write_text('\n'.join(lines) + '\n')
    print(p)


def split(transcript, out):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    cur = part = None; buf = {}
    seen = []
    for line in pathlib.Path(transcript).read_text(errors='replace').split('\n'):
        if line.startswith('Q ') and line.endswith(' end') and cur and line == 'Q %s end' % cur:
            (out / (cur + '.rc')).write_text(buf['rc'])
            (out / (cur + '.out')).write_bytes(base64.b64decode(''.join(buf['out'])))
            if 'obj' in buf:
                (out / (cur + '.obj')).write_bytes(base64.b64decode(''.join(buf['obj'])))
            seen.append(cur); cur = part = None; buf = {}
        elif line.startswith('Q ') and cur is None and line != 'Q all end':
            cur = line.split()[1]; buf = {'rc': '', 'out': []}; part = None
        elif cur is not None:
            if line.startswith('rc=') and part is None:
                buf['rc'] = line[3:] + '\n'
            elif line == '-- out':
                part = 'out'
            elif line == '-- obj':
                part = 'obj'; buf['obj'] = []
            elif part:
                buf[part].append(line)
    (out / 'cases.txt').write_text(''.join(c + '\n' for c in seen))
    print('%d cases' % len(seen))


def host(clef, root, out):
    out = pathlib.Path(out).resolve(); run = out / 'run'; run.mkdir(parents=True, exist_ok=True)
    cwd = pathlib.Path(root) / DIR.lstrip('/')
    seen = []
    for cid, argv, obj, setup in cases(root):
        argv = [w.replace(Q, str(run)) for w in argv]
        o = obj.replace(Q, str(run)) if obj else None
        if setup is not None:
            pathlib.Path(o).write_text(setup + '\n')
        p = subprocess.run([clef] + argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / (cid + '.rc')).write_text('%d\n' % p.returncode)
        (out / (cid + '.out')).write_bytes(p.stdout)
        if o:
            (out / (cid + '.obj')).write_bytes(pathlib.Path(o).read_bytes() if os.path.exists(o) else b'')
        seen.append(cid)
    (out / 'cases.txt').write_text(''.join(c + '\n' for c in seen))
    print('%d cases' % len(seen))


def compare(a, b):
    a = pathlib.Path(a); b = pathlib.Path(b); bad = 0
    ca = (a / 'cases.txt').read_text().split(); cb = (b / 'cases.txt').read_text().split()
    if ca != cb:
        print('the case lists differ: %d against %d' % (len(ca), len(cb))); return 1
    for c in ca:
        for ext in ('rc', 'out', 'obj'):
            x = a / (c + '.' + ext); y = b / (c + '.' + ext)
            if x.exists() != y.exists() or (x.exists() and x.read_bytes() != y.read_bytes()):
                print('%s.%s differs' % (c, ext)); bad += 1
    print('%d cases, %d differences' % (len(ca), bad))
    return 1 if bad else 0


def oracle(tools, root, a, gas):
    sys.path.insert(0, str(pathlib.Path(tools).resolve()))
    from elf import ELF, differences
    gas = pathlib.Path(gas).resolve(); gas.mkdir(parents=True, exist_ok=True)
    cwd = pathlib.Path(root) / DIR.lstrip('/')
    bad = same = n = 0
    for cid, argv, obj, setup in cases(root):
        if not cid.startswith('c') or cid == 'c-form':
            continue
        n += 1
        src = argv[-1]; want = gas / (cid + '.o')
        subprocess.run(['as', '--64', src, '-o', str(want)], cwd=cwd, check=True)
        got = pathlib.Path(a) / (cid + '.obj')
        d = differences(ELF(want), ELF(got))
        if d:
            print('%s %s: %s' % (cid, src, sorted(d))); bad += 1
        same += want.read_bytes() == got.read_bytes()
    print('%d sources: %d structurally equal to GNU as, %d byte-identical files' % (n, n - bad, same))
    return 1 if bad else 0


def main(argv):
    if len(argv) >= 2 and argv[0] == 'gen' and len(argv) == 2: return gen(argv[1]) or 0
    if len(argv) == 3 and argv[0] == 'split': return split(argv[1], argv[2]) or 0
    if len(argv) == 4 and argv[0] == 'host': return host(*argv[1:]) or 0
    if len(argv) == 3 and argv[0] == 'compare': return compare(*argv[1:])
    if len(argv) == 5 and argv[0] == 'oracle': return oracle(*argv[1:])
    print(__doc__, file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
