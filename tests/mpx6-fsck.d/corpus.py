#!/usr/bin/env python3
"""Seeded ext2 damage, from ext2-doc tables 3.3/3.12/3.13/4.1.
No implementation source is used. mke2fs and e2fsck are black boxes.
Every row starts from the same clean image; no oracle output is edited.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

EPOCH = 1700000000


def run(argv):
    return subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env={**os.environ,
                          'LC_ALL': 'C', 'E2FSPROGS_FAKE_TIME': str(EPOCH)})


class Image:
    def __init__(self, raw):
        self.b = bytearray(raw)
        self.bs = 1024 << self.u(1024 + 24)
        self.first = self.u(1024 + 20)
        self.ipg = self.u(1024 + 40)
        self.isize = self.u(1024 + 88, 2)
        self.gdt = (self.first + 1) * self.bs

    def u(self, at, size=4):
        return int.from_bytes(self.b[at:at + size], 'little')

    def put(self, at, value, size=4):
        self.b[at:at + size] = value.to_bytes(size, 'little')

    def ino(self, n):
        return self.u(self.gdt + (n - 1) // self.ipg * 32 + 8) * self.bs + (n - 1) % self.ipg * self.isize

    def entries(self, n):
        ino = self.ino(n)
        for j in range(12):
            block = self.u(ino + 40 + j * 4)
            if not block:
                continue
            at, end = block * self.bs, (block + 1) * self.bs
            while at < end:
                length = self.u(at + 4, 2)
                assert length >= 8 and at + length <= end
                yield bytes(self.b[at + 8:at + 8 + self.b[at + 6]]).decode(), self.u(at), at
                at += length

    def named(self, name):
        return next((n, at) for text, n, at in self.entries(2) if text == name)

    def bit(self, block, index, value):
        at = block * self.bs + index // 8
        mask = 1 << (index % 8)
        self.b[at] = (self.b[at] | mask) if value else (self.b[at] & ~mask)


def make(work, mke2fs, seed):
    source = work / 'source'
    source.mkdir(exist_ok=True)
    rng = random.Random(seed)
    (source / 'alpha').write_bytes(rng.randbytes(8192))
    (source / 'beta').write_bytes(rng.randbytes(8192))
    (source / 'branch').mkdir(exist_ok=True)
    (source / 'branch' / 'leaf').write_bytes(b'leaf\n')
    for entry in sorted(source.rglob('*'), reverse=True):
        os.utime(entry, (EPOCH, EPOCH))
    os.utime(source, (EPOCH, EPOCH))
    base = work / 'base.img'
    with base.open('wb') as f:
        f.truncate(16 * 1024 * 1024)
    p = run([mke2fs, '-q', '-F', '-t', 'ext2', '-b', '4096', '-I', '256',
             '-O', 'filetype,sparse_super,large_file,^resize_inode,^dir_index',
             '-U', '72727272-7272-4272-8272-727272727272', '-E', 'lazy_itable_init=0,hash_seed=72727272-7272-4272-8272-727272727272',
             '-d', source, base])
    (work / 'mke2fs.log').write_bytes(p.stdout)
    if p.returncode:
        raise RuntimeError(p.stdout.decode())
    canonical = Image(base.read_bytes())
    # mke2fs -d copies host ctime, which utime cannot set. Canonicalize
    # the fixture's inode times from the documented fields, not a golden.
    for ino in range(1, canonical.u(1024) + 1):
        at = canonical.ino(ino)
        if canonical.u(at, 2):
            for off in (8, 12, 16):
                canonical.put(at + off, EPOCH)
            if canonical.isize >= 160:
                for off in (132, 136, 140, 148):
                    canonical.put(at + off, 0)
                canonical.put(at + 144, EPOCH)
    raw = bytes(canonical.b)
    base.write_bytes(raw)
    rows = []

    def row(name, finding, change):
        image = Image(raw)
        change(image)
        path = work / (name + '.img')
        path.write_bytes(image.b)
        rows.append({'name': name, 'expected': finding,
                     'sha256': hashlib.sha256(image.b).hexdigest()})

    def inode_field(name, offset, value, size=4):
        return lambda im: im.put(im.ino(im.named(name)[0]) + offset, value, size)

    row('clean', 'none', lambda im: None)
    row('lost-writes', 'none; older committed payload is structurally clean', lambda im: im.put(im.u(im.ino(im.named('alpha')[0]) + 40) * im.bs, 0))
    row('dirty', 'filesystem not clean', lambda im: im.put(1082, 0, 2))
    row('group-free-count', 'Free blocks count wrong for group', lambda im: im.put(im.gdt + 12, 0, 2))
    row('super-free-count', 'Free blocks count wrong', lambda im: im.put(1036, 0))
    row('group-inode-count', 'Free inodes count wrong for group', lambda im: im.put(im.gdt + 14, 0, 2))
    row('super-inode-count', 'Free inodes count wrong', lambda im: im.put(1040, 0))
    row('directory-count', 'Directories count wrong for group', lambda im: im.put(im.gdt + 16, 0, 2))
    row('block-bit-cleared', 'Block bitmap differences', lambda im: im.bit(im.u(im.gdt), im.u(im.ino(im.named('alpha')[0]) + 40), False))
    row('block-bit-set', 'Block bitmap differences', lambda im: im.bit(im.u(im.gdt), im.u(1028) - 1, True))
    row('inode-bit-cleared', 'Inode bitmap differences', lambda im: im.bit(im.u(im.gdt + 4), im.named('alpha')[0] - 1, False))
    row('inode-bit-set', 'Inode bitmap differences', lambda im: im.bit(im.u(im.gdt + 4), im.ipg - 1, True))
    row('link-count', 'ref count', inode_field('alpha', 26, 7, 2))
    row('inode-block-count', 'i_blocks', inode_field('alpha', 28, 0))
    row('directory-size', 'i_size', inode_field('branch', 4, 17))
    row('bad-directory-inode', 'deleted/unused inode', lambda im: im.put(im.named('alpha')[1], im.ipg))
    row('bad-directory-type', 'incorrect filetype', lambda im: im.put(im.named('alpha')[1] + 7, 2, 1))
    row('cross-linked-block', 'multiply-claimed block', lambda im: im.put(im.ino(im.named('beta')[0]) + 40, im.u(im.ino(im.named('alpha')[0]) + 40)))
    row('disconnected-file', 'Unattached inode', lambda im: im.put(im.named('alpha')[1], 0))

    def orphan(im):
        n, at = im.named('alpha')
        im.put(at, 0)
        im.put(im.ino(n) + 26, 0, 2)
    row('orphan', 'Deleted inode has zero dtime', orphan)
    row('missing-lost-found', 'lost+found not found', lambda im: im.put(im.named('lost+found')[1], 0))
    row('bad-directory-record', 'directory corrupted', lambda im: im.put(im.named('alpha')[1] + 4, 4, 2))
    (work / 'manifest.json').write_text(json.dumps({'seed': seed, 'rows': rows}, indent=2) + '\n')
    return rows


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    im = Image(path.read_bytes())
    rows = []
    seen = set()

    def visit(ino, name):
        at = im.ino(ino)
        mode = im.u(at, 2)
        size = im.u(at + 4)
        kind = mode & 0xf000
        blocks = [im.u(at + 40 + i * 4) for i in range(12)]
        data = b''.join(im.b[b * im.bs:(b + 1) * im.bs] if b else bytes(im.bs) for b in blocks)[:size]
        rows.append((name, ino, mode, im.u(at + 2, 2), im.u(at + 24, 2), size,
                     im.u(at + 26, 2), hashlib.sha256(data).hexdigest() if kind != 0x4000 else 'directory'))
        if kind == 0x4000:
            if ino in seen:
                raise RuntimeError('directory cycle')
            seen.add(ino)
            for child, target, _ in im.entries(ino):
                if target and child not in ('.', '..'):
                    visit(target, name.rstrip('/') + '/' + child)
    visit(2, '/')
    return sorted(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--mke2fs', default='mke2fs')
    ap.add_argument('--e2fsck', default='e2fsck')
    ap.add_argument('--checker')
    ap.add_argument('--seed', type=int, default=72)
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    rows = make(args.work, args.mke2fs, args.seed)
    results = []
    failures = 0
    unsupported = 0
    for row in rows:
        name = row['name']
        original = args.work / (name + '.img')
        fixed = args.work / (name + '.oracle.img')
        shutil.copyfile(original, fixed)
        report = run([args.e2fsck, '-fn', original])
        repair = run([args.e2fsck, '-fy', fixed])
        verify = run([args.e2fsck, '-fn', fixed])
        for phase, p in [('report', report), ('repair', repair), ('verify', verify)]:
            (args.work / f'{name}.oracle.{phase}.log').write_bytes(p.stdout)
        result = {**row, 'oracle_report': report.returncode,
                  'oracle_repair': repair.returncode, 'oracle_verify': verify.returncode}
        okay = repair.returncode in (0, 1) and verify.returncode == 0
        if args.checker:
            tested = args.work / (name + '.wolf.img')
            shutil.copyfile(original, tested)
            before = digest(tested)
            n = run([args.checker, '-fn', tested])
            same = before == digest(tested)
            y = run([args.checker, '-fy', tested])
            v = run([args.e2fsck, '-fn', tested])
            again = run([args.checker, '-fn', tested])
            for phase, p in [('report', n), ('repair', y), ('verify', v), ('again', again)]:
                (args.work / f'{name}.wolf.{phase}.log').write_bytes(p.stdout)
            same_tree = tree(tested) == tree(fixed) if v.returncode == 0 else False
            result.update(tree_equal=same_tree, wolf_report=n.returncode, wolf_repair=y.returncode,
                          wolf_verify=v.returncode, wolf_again=again.returncode,
                          report_unchanged=same)
            okay = okay and same_tree and same and n.returncode == report.returncode and y.returncode == repair.returncode and v.returncode == 0 and again.returncode == 0
        expected_refusal = args.checker and name == 'bad-directory-record'
        if expected_refusal:
            refused_safely = (n.returncode == 4 and y.returncode == 4 and
                              digest(tested) == before and b'unsupported:' in y.stdout and
                              b'malformed record' in y.stdout)
            result['supported'] = False
            result['safe_refusal'] = refused_safely
            unsupported += 1
            failures += not refused_safely
        else:
            failures += not okay
        result['pass'] = okay
        result['oracle_findings'] = report.stdout.decode(errors='replace').splitlines()
        if args.checker:
            result['wolf_findings'] = n.stdout.decode(errors='replace').splitlines()
        results.append(result)
        print(('UNSUPPORTED ' if expected_refusal and refused_safely else 'PASS ' if okay else 'FAIL ') + name + ': ' + json.dumps({k: v for k, v in result.items() if not k.endswith('_findings')}), flush=True)
    (args.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'corpus: {len(rows) - unsupported - failures} parity rows, {unsupported} unsupported, {failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
