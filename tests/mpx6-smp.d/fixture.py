#!/usr/bin/env python3
"""SMP-BUILD's fixture (the processor census's baseline): 256 deterministic incompressible blobs of
8192 bytes (2 MiB a pack) as loose objects, fifteen repositories of them (three rounds of one job and
four), and the same den's own pack and index on the host as the oracle.

  python3 -I tests/mpx6-smp.d/fixture.py ROOT OUT DEN

OUT holds `bench` and `run` (tests/mpx6-smp writes them first); this writes OUT/root.cpio (/bin/den,
/bin/bench, /etc/pax-run and the repositories under /bench), OUT/expected.json (each output file's
trailer) and the oracle's lines on stdout.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zlib

sys.dont_write_bytecode = True
root, out, den = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
objects = out / 'objects'
shutil.rmtree(objects, ignore_errors=True)
objects.mkdir()
ids = []
for i in range(256):
    body = b''.join(hashlib.sha256(f'cpu-pack-{i}-{j}'.encode()).digest() for j in range(256))
    raw = f'blob {len(body)}\0'.encode() + body
    oid = hashlib.sha1(raw).hexdigest()
    (objects / oid).write_bytes(zlib.compress(raw))
    ids.append(oid)
(out / 'list').write_text(''.join(oid + '\n' for oid in ids))
(out / 'HEAD').write_text('ref: refs/heads/main\n')
(out / 'config').write_text('[core]\nrepositoryformatversion = 0\nbare = false\n')
args = [str(root / 'tools/mkinitramfs'), str(out / 'root.cpio'),
        '/bin/den=' + str(den), '/bin/bench=' + str(out / 'bench'),
        '/etc/pax-run=' + str(out / 'run')]
for r in range(3):
    for jobs in [1, 4]:
        for k in range(jobs):
            base = f'/bench/r{r}-j{jobs}-{k}'
            args += [base + '/.git/objects/pack/', base + '/.git/refs/heads/',
                     base + '/list=' + str(out / 'list'), base + '/.git/HEAD=' + str(out / 'HEAD'),
                     base + '/.git/config=' + str(out / 'config')]
            args += [base + '/.git/objects/' + oid[:2] + '/' + oid[2:] + '=' + str(objects / oid) for oid in ids]
with (out / 'archive.log').open('w') as f:
    subprocess.run(args, check=True, stdout=f)
oracle = out / 'oracle'
shutil.rmtree(oracle, ignore_errors=True)
(oracle / '.git/objects/pack').mkdir(parents=True)
(oracle / '.git/refs/heads').mkdir(parents=True)
for name in ['HEAD', 'config']:
    shutil.copyfile(out / name, oracle / '.git' / name)
for oid in ids:
    dst = oracle / '.git/objects' / oid[:2] / oid[2:]
    dst.parent.mkdir(exist_ok=True)
    shutil.copyfile(objects / oid, dst)
with (out / 'list').open('rb') as f:
    subprocess.run([str(den), 'pack-objects', '--window=0', '.git/objects/pack/pack'], cwd=oracle, stdin=f, check=True,
                   stdout=subprocess.DEVNULL)
expected = {}
for p in sorted((oracle / '.git/objects/pack').iterdir()):
    data = p.read_bytes()
    assert hashlib.sha1(data[:-20]).digest() == data[-20:], p
    expected[p.name] = data[-20:].hex()
    print('ORACLE', p.name, 'sha256=' + hashlib.sha256(data).hexdigest(), 'bytes=' + str(len(data)))
assert len(expected) == 2, expected
(out / 'expected.json').write_text(json.dumps(expected))
print('INPUT objects=256 bytes=2097152 list-sha256=' + hashlib.sha256((out / 'list').read_bytes()).hexdigest())
