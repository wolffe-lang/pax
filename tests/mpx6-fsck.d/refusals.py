#!/usr/bin/env python3
"""Usage, preen and malformed-journal safety; unsupported is not parity."""
from pathlib import Path
import json
import os
import runpy
import shutil
import struct
import subprocess
import sys

checker, work = Path(sys.argv[1]), Path(sys.argv[2])
repo = Path(__file__).resolve().parents[2]
work.mkdir(parents=True, exist_ok=True)


def run(args):
    return subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env={**os.environ, 'LC_ALL': 'C'})


missing = work/'absent.img'
assert not missing.exists()
for args, code in [([], 16), (['-ny', missing], 16), (['-y', missing], 8),
                   (['-z', missing], 16), (['-n', work], 8)]:
    p = run([checker, *args])
    assert p.returncode == code and not missing.exists(), (args, p.returncode, p.stdout)
print('PASS usage: exact statuses, missing repair target not created')
for name in ['group-free-count', 'block-bit-cleared', 'link-count', 'cross-linked-block']:
    initial = work.parent/'corpus'/(name+'.img')
    a, b = work/(name+'.oracle'), work/(name+'.wolf')
    shutil.copyfile(initial, a); shutil.copyfile(initial, b)
    ep, wp = run(['e2fsck', '-fp', a]), run([checker, '-fp', b])
    (work/(name+'.oracle.log')).write_bytes(ep.stdout)
    (work/(name+'.wolf.log')).write_bytes(wp.stdout)
    assert ep.returncode == wp.returncode, (name, ep.returncode, wp.returncode, wp.stdout)
    if wp.returncode == 4:
        assert b.read_bytes() == initial.read_bytes()
    else:
        p = run(['e2fsck', '-fn', b]); assert p.returncode == 0, p.stdout
    print('PASS preen-' + name + ': status ' + str(wp.returncode))

api = runpy.run_path(str(repo/'tools/mkjournal'), run_name='px72_journal')
base = work.parent/'journal/base.img'
results = []
for name in ['tag-past-end', 'bad-revoke-count', 'csum3']:
    image = work/(name+'.img')
    shutil.copyfile(base, image)
    v = api['Vol'](str(image), 0)
    blocks, bs = image.stat().st_size // v.bs, v.bs
    mapping = v.map[:]
    v.f.close()
    spec = work/(name+'.spec')
    text = 'start 1 1\n'
    if name == 'csum3': text += 'feature csum3\n'
    text += 'tx\n' + ('revoke 1\n' if name == 'bad-revoke-count' else f'write {blocks + 1 if name == "tag-past-end" else blocks - 1} aa\n') + 'commit\nrecover\n'
    spec.write_text(text)
    p = run(['python3', '-I', repo/'tools/mkjournal', image, spec]); assert p.returncode == 0, p.stdout
    if name == 'bad-revoke-count':
        with image.open('r+b') as f:
            f.seek(mapping[1] * bs + 12); f.write(struct.pack('>I', 12))
    oracle = work/(name+'.oracle')
    shutil.copyfile(image, oracle)
    en = run(['e2fsck', '-fn', oracle])
    ey = run(['e2fsck', '-fy', oracle])
    before = image.read_bytes()
    wn = run([checker, '-fn', image])
    assert image.read_bytes() == before, (name, 'report-only changed image')
    wp = run([checker, '-fy', image])
    assert wp.returncode == 4 and image.read_bytes() == before and b'unsupported:' in wp.stdout, (name, wp.returncode, wp.stdout)
    for label, p in [('oracle-report', en), ('oracle-repair', ey), ('wolf-report', wn), ('wolf-repair', wp)]:
        (work/(name+'.'+label+'.log')).write_bytes(p.stdout)
    row = {'case': name, 'oracle_report': en.returncode, 'oracle_repair': ey.returncode,
           'wolf_report': wn.returncode, 'wolf_repair': wp.returncode, 'unchanged': True, 'supported': False}
    results.append(row)
    print('UNSUPPORTED journal-' + name + ': ' + json.dumps(row))
(work/'results.json').write_text(json.dumps(results, indent=2)+'\n')
