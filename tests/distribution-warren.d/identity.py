#!/usr/bin/env python3
"""W0 of tests/distribution-warren: which warren the image carries, and that the host runs those same bytes.

    identity.py archive OUT ISO_INITRAMFS WORK   the image directory's dev archive; writes WORK/warren (0755),
                                                 WORK/warren-commit and WORK/warren-repo
    identity.py tree TREE COMMIT WARREN          warren's tree at COMMIT, and WARREN (the image's, on this host)
    identity.py rows CONSOLE_ROWS                the rows that file asks by default, one comma list

`archive` holds: ISO_INITRAMFS (the ISO's /boot/initramfs.cpio, read back) is OUT/dev.cpio byte for byte; the
archive's /etc/pax-release is OUT/pax-release; its `warren` row names a commit, and OUT/latest/resolution.txt's
`warren` line, when OUT has one, names the same commit (its repository is the one fetched); /usr/bin/warren is
0755 and is the bytes the archive's own /etc/pax-files.sha256 names; and it is a static x86-64 executable
(ET_EXEC, no PT_INTERP, no PT_DYNAMIC), so it runs on a Linux host as it runs on PAX. warren names no commit of
its own (`warren modules` names its package version), so the commit is the image's release file's.

`tree` holds: TREE's HEAD is COMMIT, it has tests/pax/console_rows.py, and WARREN `modules` exits 0 naming the
version TREE's src/wolf.pkg declares.

`rows` reads the default of console_rows.py's `rows` argument from its source text; the file is never imported.

Each holds or not as one row, W0, printed `PASS W0 …` or `FAIL W0 …`; the exit is 0 when it held.
"""
import ast
import hashlib
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

WARREN_REPO = 'https://github.com/wolffe-lang/warren'  # a pinned build's; a resolution names its own
SHA = re.compile(r'[0-9a-f]{40}')


def newc(blob):
    """name -> (mode, data) of a newc archive; refuses anything else."""
    rows, o = {}, 0
    while True:
        header = blob[o:o + 110]
        if header[:6] != b'070701':
            raise ValueError('not a newc archive at byte %d' % o)
        fields = [int(header[i:i + 8], 16) for i in range(6, 110, 8)]
        name = blob[o + 110:o + 110 + fields[11] - 1].decode()
        start = (o + 110 + fields[11] + 3) & ~3
        data = blob[start:start + fields[6]]
        if len(data) != fields[6]:
            raise ValueError('a short entry: ' + name)
        o = (start + fields[6] + 3) & ~3
        if name == 'TRAILER!!!':
            return rows
        if name in rows:
            raise ValueError('a duplicate entry: ' + name)
        rows[name] = (fields[1], data)


def static_x86_64(data):
    """None when DATA is a 64-bit little-endian x86-64 ET_EXEC with no PT_INTERP and no PT_DYNAMIC, else why not."""
    if data[:4] != b'\x7fELF' or data[4] != 2 or data[5] != 1:
        return 'not a 64-bit little-endian ELF'
    etype, machine = struct.unpack_from('<HH', data, 16)
    phoff, = struct.unpack_from('<Q', data, 32)
    phentsize, phnum = struct.unpack_from('<HH', data, 54)
    if machine != 0x3e:
        return 'e_machine %#x, not x86-64' % machine
    if etype != 2:
        return 'e_type %d, not ET_EXEC' % etype
    kinds = [struct.unpack_from('<I', data, phoff + i * phentsize)[0] for i in range(phnum)]
    if 3 in kinds:
        return 'it has PT_INTERP (a dynamic executable)'
    if 2 in kinds:
        return 'it has PT_DYNAMIC'
    return None


def archive(out, iso_initramfs, work):
    """W0's image half. Returns (held, lines)."""
    out, work = Path(out), Path(work)

    def no(why):
        line = 'FAIL W0 archive: ' + why
        print(line, flush=True)
        return False, [line]

    cpio = out / 'dev.cpio'
    if not cpio.is_file():
        return no(f'{cpio} is missing (the dev image is the one that carries warren)')
    blob = cpio.read_bytes()
    if Path(iso_initramfs).read_bytes() != blob:
        return no('the ISO\'s /boot/initramfs.cpio is not OUT/dev.cpio: the image booted is not the archive read')
    try:
        files = newc(blob)
    except ValueError as exc:
        return no('dev.cpio: ' + str(exc))
    release = files.get('etc/pax-release', (0, None))[1]
    if release is None:
        return no('the archive has no /etc/pax-release')
    if release != (out / 'pax-release').read_bytes():
        return no('the archive\'s /etc/pax-release is not OUT/pax-release')
    named = [line.split() for line in release.decode().splitlines() if line.split()[:1] == ['warren']]
    if len(named) != 1 or len(named[0]) != 3 or not SHA.fullmatch(named[0][1]):
        return no('/etc/pax-release has no one `warren COMMIT …` row (%d rows)' % len(named))
    commit = named[0][1]
    repo = WARREN_REPO
    resolution = out / 'latest/resolution.txt'
    if resolution.exists():
        lines = [line.split() for line in resolution.read_text().splitlines() if line.split()[:1] == ['warren']]
        if len(lines) != 1 or len(lines[0]) != 5:
            return no('latest/resolution.txt has no one warren line (%d)' % len(lines))
        if lines[0][1] != commit:
            return no(f'/etc/pax-release names warren {commit}, latest/resolution.txt {lines[0][1]}')
        repo = lines[0][3]
    if 'usr/bin/warren' not in files:
        return no('the archive has no /usr/bin/warren')
    mode, war = files['usr/bin/warren']
    if mode != 0o100755:
        return no('/usr/bin/warren is mode %o, not 100755' % mode)
    listed = {}
    for line in files.get('etc/pax-files.sha256', (0, b''))[1].decode().splitlines():
        digest, _, name = line.partition('  ')
        listed[name] = digest
    digest = hashlib.sha256(war).hexdigest()
    if listed.get('usr/bin/warren') != digest:
        return no('/usr/bin/warren is sha256 %s; /etc/pax-files.sha256 says %s' % (digest, listed.get('usr/bin/warren')))
    why = static_x86_64(war)
    if why:
        return no('/usr/bin/warren is not a static x86-64 executable: ' + why)
    (work / 'warren').write_bytes(war)
    os.chmod(work / 'warren', 0o755)
    (work / 'warren-commit').write_text(commit + '\n')
    (work / 'warren-repo').write_text(repo + '\n')
    line = (f'PASS W0 archive: warren {commit} ({"the resolution agrees" if resolution.exists() else "a pinned build"}),'
            f' /usr/bin/warren {len(war)} bytes sha256 {digest}, static x86-64, the ISO boots this archive')
    print(line, flush=True)
    return True, [line]


def package_version(tree):
    """src/wolf.pkg's one version field, read as warren's own build reads it."""
    text = re.sub(r'//[^\n]*', '', (Path(tree) / 'src/wolf.pkg').read_text())
    fields = list(re.finditer(r'\bversion\s*:', text))
    if len(fields) != 1:
        return None
    m = re.match(r'\s*"([0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?)"\s*[,}]', text[fields[0].end():])
    return m[1] if m else None


def tree(tree_dir, commit, warren):
    """W0's tree half. Returns (held, lines)."""
    tree_dir = Path(tree_dir)

    def no(why):
        line = 'FAIL W0 tree: ' + why
        print(line, flush=True)
        return False, [line]

    head = subprocess.run(['git', '-C', str(tree_dir), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if head != commit:
        return no(f'the tree\'s HEAD is {head or "unreadable"}, not {commit}')
    if not (tree_dir / 'tests/pax/console_rows.py').is_file():
        return no(f'warren {commit} has no tests/pax/console_rows.py')
    version = package_version(tree_dir)
    if version is None:
        return no('src/wolf.pkg declares no one version')
    try:
        ran = subprocess.run([str(warren), 'modules'], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return no(f'the image\'s warren did not run on this host: {exc}')
    said = ran.stdout.decode('utf-8', 'replace').splitlines()
    if ran.returncode != 0:
        return no(f'the image\'s warren `modules` exited {ran.returncode}')
    if not said or said[0] != f'warren {version}: modules':
        return no(f'the image\'s warren says {said[0] if said else "nothing"!r}; the tree at {commit} is {version}')
    line = f'PASS W0 tree: warren {commit} is version {version}; the image\'s warren, on this host, says so'
    print(line, flush=True)
    return True, [line]


def default_rows(path):
    """The default of the `rows` argument in console_rows.py's source; ValueError when there is none."""
    for node in ast.walk(ast.parse(Path(path).read_text(), str(path))):
        if (isinstance(node, ast.Call) and getattr(node.func, 'attr', None) == 'add_argument' and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'rows'):
            for kw in node.keywords:
                if kw.arg == 'default' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    rows = kw.value.value.split(',')
                    if rows and all(re.fullmatch(r'C[0-9]+', r) for r in rows):
                        return rows
                    raise ValueError('the rows default is not a list of row names: %r' % kw.value.value)
            raise ValueError('the rows argument has no default')
    raise ValueError('no rows argument')


def main(argv):
    if argv[:1] == ['archive'] and len(argv) == 4:
        return 0 if archive(*argv[1:])[0] else 1
    if argv[:1] == ['tree'] and len(argv) == 4:
        return 0 if tree(*argv[1:])[0] else 1
    if argv[:1] == ['rows'] and len(argv) == 2:
        try:
            print(','.join(default_rows(argv[1])))
        except ValueError as exc:
            print('FAIL W0 rows: ' + str(exc))
            return 1
        return 0
    print(__doc__.split('\n\n')[1], file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
