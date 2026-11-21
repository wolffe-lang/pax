#!/usr/bin/env python3
"""fsck.ext2 at size: px84's five geometries, the owner's root, a repair past
block 2^31. No implementation source is used; mke2fs and e2fsck are black boxes.

    capacity.py CHECKER WORK

Rows (one verdict line each; a planned row without one is a FAIL):
  F-size-8G, -64G, -500G, -4T, -16T  px84's sizes (16 TiB less a block the
      largest), 16 inodes a group as tests/mpx6-disktools.d/big.py makes them:
      -fn exits 0 with no finding where e2fsck -fn exits 0; -fy changes no
      byte; the checker's peak resident set is at most the floor plus its
      planned state (one bit a block, three bytes an inode) plus 64 MiB.
  F-big-repair  two block bitmap differences planted past block 2^31 of the
      16T image: -fy repairs both as e2fsck -fy does (the superblock, the
      descriptors and both bitmap blocks equal, but for the check times) and
      e2fsck -fn is clean after.
  F-size-owner, F-size-owner-ext3  the owner's root: 244,173,745 blocks and
      61,046,784 inodes (mke2fs's default density at that size), ext2 and
      ext3. Local-only: they write about 16 GB of inode tables each, so they
      run only with PAX_FSCK_LOCAL_BIG=1 and otherwise print SKIP and why.
  F-local-skips  the skipped set is exactly the local rows, or empty when
      PAX_FSCK_LOCAL_BIG=1; every planned row printed one verdict.

The checker runs from a small parent (peak.py) under RLIMIT_AS; the floor is
/bin/true measured the same way. e2fsck's peak is measured the same way when
it is a native binary (PAX_FSCK_ORACLE_BIN); a containerized oracle's is not
measurable from here and is printed as such.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

EPOCH = 1700000000
UUID = '72727272-7272-4272-8272-727272727272'
FEATURES = 'filetype,sparse_super,large_file,^resize_inode,^dir_index'
CLEAN = b'fsck.ext2: 0 findings, 0 planned repairs, 0 uncorrected'
MIB = 1 << 20
LOCAL = ['F-size-owner', 'F-size-owner-ext3']
ROWS = ['F-size-8G', 'F-size-64G', 'F-size-500G', 'F-size-4T', 'F-size-16T',
        'F-big-repair', *LOCAL]

checker, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
here = Path(__file__).resolve().parent
work.mkdir(parents=True, exist_ok=True)
local = os.environ.get('PAX_FSCK_LOCAL_BIG') == '1'
verdicts = {}


def verdict(row, kind, text):
    verdicts.setdefault(row, []).append(kind)
    print(f'{kind} {row}: {text}', flush=True)


def run(argv):
    return subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          env={**os.environ, 'LC_ALL': 'C', 'E2FSPROGS_FAKE_TIME': str(EPOCH)})


def measured(tag, cap, argv):
    """Run argv from peak.py; return (status, peak KiB, seconds, output)."""
    out = work / (tag + '.peak.json')
    p = run([sys.executable, '-I', '-B', here / 'peak.py', out, cap, *argv])
    (work / (tag + '.log')).write_bytes(p.stdout)
    m = json.loads(out.read_text())
    return m['status'], m['maxrss_kib'], m['seconds'], p.stdout


def native(program):
    path = shutil.which(program)
    if not path:
        return False
    with open(path, 'rb') as f:
        return f.read(4) == b'\x7fELF'


def extents(path):
    """Yield (offset, length) of every data extent, by SEEK_DATA/SEEK_HOLE."""
    with open(path, 'rb') as f:
        end = os.fstat(f.fileno()).st_size
        at = 0
        while at < end:
            try:
                start = os.lseek(f.fileno(), at, os.SEEK_DATA)
            except OSError:
                return
            stop = os.lseek(f.fileno(), start, os.SEEK_HOLE)
            yield start, stop - start
            at = stop


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for start, length in extents(path):
            h.update(struct.pack('<QQ', start, length))
            f.seek(start)
            while length:
                chunk = f.read(min(length, 8 * MIB))
                assert chunk, ('short read', path, start)
                h.update(chunk)
                length -= len(chunk)
    return h.hexdigest()


def allocated(path):
    return path.stat().st_blocks * 512


def read(path, at, n):
    with open(path, 'rb') as f:
        f.seek(at)
        b = f.read(n)
    assert len(b) == n, ('short read', path, at, n)
    return b


def geometry(path):
    sb = read(path, 1024, 1024)
    inodes, blocks, bpg, ipg = (struct.unpack_from('<I', sb, at)[0] for at in (0, 4, 32, 40))
    first = struct.unpack_from('<I', sb, 20)[0]
    return {'blocks': blocks, 'inodes': inodes, 'groups': (blocks - first + bpg - 1) // bpg,
            'bpg': bpg, 'ipg': ipg, 'first': first}


def make(path, size, ext3, small):
    """A fresh image of SIZE bytes by mke2fs; returns its seconds."""
    path.unlink(missing_ok=True)
    with path.open('wb') as f:
        f.truncate(size)
    blocks = size // 4096
    groups = (blocks + 32767) // 32768
    argv = ['mke2fs', '-q', '-F', '-t', 'ext3' if ext3 else 'ext2', '-b', '4096', '-I', '256',
            '-O', FEATURES, '-U', UUID, '-E', 'lazy_itable_init=0,hash_seed=' + UUID]
    if small:
        argv += ['-N', str(groups * 16)]
    start = time.monotonic()
    p = run([*argv, path])
    (work / (path.stem + '.mke2fs.log')).write_bytes(p.stdout)
    assert p.returncode == 0, ('mke2fs', p.returncode, p.stdout[-400:])
    return time.monotonic() - start


def need_space(path, size, small):
    blocks = size // 4096
    groups = (blocks + 32767) // 32768
    # One inode-table block a group, or mke2fs's default of an inode per
    # 16 KiB (256 bytes each: 64 bytes a 4 KiB block); bitmaps and backups;
    # a journal of at most 1 GiB.
    tables = groups * 4096 if small else blocks * 64
    needed = tables + groups * 3 * 4096 + (1 << 30)
    free = shutil.disk_usage(path.parent).free
    assert free > needed + (2 << 30), ('space', path.parent, free, needed)


FLOOR = None


def floor():
    global FLOOR
    if FLOOR is None:
        status, peak, _, _ = measured('floor', 0, ['true'])
        assert status == 0, ('floor', status)
        FLOOR = peak
    return FLOOR


def cap_for(g):
    return g['blocks'] // 8 + 3 * g['inodes'] + (1 << 30)


def oracle(tag, args):
    if native('e2fsck'):
        status, peak, seconds, out = measured(tag, 16 << 30, ['e2fsck', *args])
        return status, peak, seconds, out
    start = time.monotonic()
    p = run(['e2fsck', *args])
    (work / (tag + '.log')).write_bytes(p.stdout)
    return p.returncode, None, time.monotonic() - start, p.stdout


def size_row(row, size, ext3=False, small=True):
    image = work / (row + '.img')
    try:
        need_space(image, size, small)
        made = make(image, size, ext3, small)
        g = geometry(image)
        if not small:
            assert (g['blocks'], g['inodes']) == (244173745, 61046784), ('owner geometry', g)
        planned = g['blocks'] // 8 + 3 * g['inodes']
        es, epeak, esec, eout = oracle(row + '.e2fsck', ['-fn', image])
        assert es == 0, ('e2fsck -fn', es, eout[-400:])
        before = digest(image)
        ws, wpeak, wsec, wout = measured(row + '.wolf-n', cap_for(g), [checker, '-fn', image])
        assert ws == 0 and CLEAN in wout, ('fsck.ext2 -fn', ws, wout[-400:])
        ys, _, ysec, yout = measured(row + '.wolf-y', cap_for(g), [checker, '-fy', image])
        assert ys == 0 and CLEAN in yout, ('fsck.ext2 -fy', ys, yout[-400:])
        assert digest(image) == before, ('fsck.ext2 -fy changed a clean image',)
        bound = floor() + (planned + 64 * MIB) // 1024
        assert wpeak <= bound, ('peak', wpeak, 'KiB over', bound)
        verdict(row, 'PASS', json.dumps({
            'blocks': g['blocks'], 'groups': g['groups'], 'inodes': g['inodes'],
            'planned_bytes': planned, 'peak_kib': wpeak, 'floor_kib': floor(),
            'e2fsck_peak_kib': epeak if epeak is not None else 'not measured (container oracle)',
            'fsck_seconds': wsec, 'repair_mode_seconds': ysec, 'e2fsck_seconds': round(esec, 3),
            'mke2fs_seconds': round(made, 3), 'allocated_bytes': allocated(image)}))
    except Exception as e:  # every failure is this row's FAIL, never a silent stop
        verdict(row, 'FAIL', repr(e)[:600])
    finally:
        image.unlink(missing_ok=True)


def flip(path, block_bitmap, index, value):
    """Set or clear one bit of an on-disk bitmap block; assert it changes."""
    at = block_bitmap * 4096 + index // 8
    with open(path, 'r+b') as f:
        f.seek(at)
        old = f.read(1)[0]
        new = old | (1 << index % 8) if value else old & ~(1 << index % 8)
        assert new != old, ('bit already', value, block_bitmap, index)
        f.seek(at)
        f.write(bytes([new]))


def big_repair():
    row = 'F-big-repair'
    wolf, ref = work / (row + '.wolf.img'), work / (row + '.oracle.img')
    try:
        size = (1 << 44) - 4096
        need_space(wolf, size, True)
        make(wolf, size, False, True)
        p = run(['cp', '--sparse=always', wolf, ref])
        assert p.returncode == 0, ('cp', p.stdout)
        g = geometry(wolf)
        gd = read(wolf, 4096, g['groups'] * 32)
        last, middle = g['groups'] - 1, 65536
        assert last > middle and middle * g['bpg'] > 1 << 31
        last_bb = struct.unpack_from('<I', gd, last * 32)[0]
        middle_bb, middle_ib = struct.unpack_from('<II', gd, middle * 32)
        tail = g['blocks'] - 1 - g['first'] - last * g['bpg']
        planted = [(last, last_bb, tail, True), (middle, middle_bb, middle_ib - g['first'] - middle * g['bpg'], False)]
        for image in (wolf, ref):
            for _, bitmap, index, value in planted:
                flip(image, bitmap, index, value)
        oy = run(['e2fsck', '-fy', ref])
        (work / (row + '.oracle-y.log')).write_bytes(oy.stdout)
        assert oy.returncode == 1, ('e2fsck -fy', oy.returncode, oy.stdout[-600:])
        before = digest(wolf)
        ns, _, _, nout = measured(row + '.wolf-n', cap_for(g), [checker, '-fn', wolf])
        assert ns == 4 and digest(wolf) == before, ('fsck.ext2 -fn', ns, nout[-600:])
        ys, ypeak, ysec, yout = measured(row + '.wolf-y', cap_for(g), [checker, '-fy', wolf])
        assert ys == 1, ('fsck.ext2 -fy', ys, yout[-600:])
        for group, _, _, _ in planted:
            assert f'Block bitmap differences in group {group}'.encode() in yout, ('report', group, yout[-600:])
        ev = run(['e2fsck', '-fn', wolf])
        (work / (row + '.verify.log')).write_bytes(ev.stdout)
        assert ev.returncode == 0, ('e2fsck -fn after repair', ev.returncode, ev.stdout[-600:])
        again = run([checker, '-fn', wolf])
        assert again.returncode == 0 and CLEAN in again.stdout, ('again', again.returncode, again.stdout[-400:])
        a, b = bytearray(read(wolf, 1024, 1024)), bytearray(read(ref, 1024, 1024))
        for lo, hi in ((48, 52), (64, 68)):  # write time, last-check time
            a[lo:hi] = b[lo:hi] = bytes(4)
        assert a == b, ('superblock differs from the oracle repair',
                        [i for i in range(1024) if a[i] != b[i]][:16])
        assert read(wolf, 4096, len(gd)) == read(ref, 4096, len(gd)), ('descriptors differ',)
        for _, bitmap, _, _ in planted:
            assert read(wolf, bitmap * 4096, 4096) == read(ref, bitmap * 4096, 4096), ('bitmap differs', bitmap)
        verdict(row, 'PASS', json.dumps({'groups': [p[0] for p in planted], 'blocks': g['blocks'],
                                         'repair_peak_kib': ypeak, 'repair_seconds': ysec}))
    except Exception as e:
        verdict(row, 'FAIL', repr(e)[:600])
    finally:
        wolf.unlink(missing_ok=True)
        ref.unlink(missing_ok=True)


def main():
    floor()
    print(f'capacity: floor {floor()} KiB (/bin/true from peak.py); e2fsck '
          + ('native' if native('e2fsck') else 'in a container: its peak is not measured'), flush=True)
    for row, size in [('F-size-8G', 8 << 30), ('F-size-64G', 64 << 30), ('F-size-500G', 500000000000),
                      ('F-size-4T', 4000000000000), ('F-size-16T', (1 << 44) - 4096)]:
        size_row(row, size)
    big_repair()
    owner = 244173745 * 4096
    for row, ext3 in [('F-size-owner', False), ('F-size-owner-ext3', True)]:
        if local:
            size_row(row, owner, ext3=ext3, small=False)
        else:
            verdict(row, 'SKIP', 'local-only: the owner\'s root (244,173,745 blocks, 61,046,784 inodes) writes '
                    'about 16 GB of inode tables; run with PAX_FSCK_LOCAL_BIG=1')
    missing = [r for r in ROWS if len(verdicts.get(r, [])) != 1]
    skipped = sorted(r for r in ROWS if verdicts.get(r) == ['SKIP'])
    want = [] if local else sorted(LOCAL)
    if missing or skipped != want:
        verdict('F-local-skips', 'FAIL', json.dumps({'without_one_verdict': missing, 'skipped': skipped, 'expected': want}))
    else:
        verdict('F-local-skips', 'PASS', json.dumps({'skipped': skipped, 'local': local}))
    failed = [r for r, v in verdicts.items() if 'FAIL' in v]
    print(f'capacity: {sum(v == ["PASS"] for v in verdicts.values())} pass, {len(skipped)} skip, {len(failed)} fail', flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
