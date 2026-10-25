#!/usr/bin/env python3
"""Exercise px68's unchanged replay corpus against userspace fsck and e2fsck."""
from pathlib import Path
import argparse
import json
import os
import runpy
import shutil
import subprocess


def run(argv):
    return subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env={**os.environ, 'LC_ALL': 'C'})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checker', type=Path)
    ap.add_argument('work', type=Path)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    a.work.mkdir(parents=True, exist_ok=True)
    base = a.work / 'base.img'
    with base.open('wb') as f:
        f.truncate(32 * 1024 * 1024)
    p = run(['mke2fs', '-q', '-F', '-t', 'ext3', '-b', '4096', base])
    assert p.returncode == 0, p.stdout
    api = runpy.run_path(str(root / 'tools/mkjournal'), run_name='px72_mkjournal')
    v = api['Vol'](str(base), 0)
    size, blocks = len(v.map), len(base.read_bytes()) // 4096
    v.f.close()
    results = []
    for row in (root / 'tests/mpx6-journal.d/replays').read_text().splitlines():
        if not row or row.startswith('#'):
            continue
        name, spec = row.split('|')
        for key, value in [('B1', blocks - 4), ('B2', blocks - 3), ('B3', blocks - 2), ('MAX2', size - 2)]:
            spec = spec.replace('@' + key, str(value))
        path = a.work / (name + '.spec')
        path.write_text(spec.replace(' ', '\n').replace('_', ' ') + '\n')
        damaged = a.work / (name + '.img')
        shutil.copyfile(base, damaged)
        p = run(['python3', '-I', root / 'tools/mkjournal', damaged, path])
        assert p.returncode == 0, p.stdout
        oracle, wolf = a.work / (name + '.oracle.img'), a.work / (name + '.wolf.img')
        shutil.copyfile(damaged, oracle)
        shutil.copyfile(damaged, wolf)
        original = damaged.read_bytes()
        en = run(['e2fsck', '-fn', oracle])
        wn = run([a.checker, '-fn', wolf])
        unchanged = wolf.read_bytes() == original
        ep = run(['e2fsck', '-fy', oracle])
        wp = run([a.checker, '-fy', wolf])
        vp = run(['e2fsck', '-fn', wolf])
        for phase, p in [('oracle-report', en), ('wolf-report', wn), ('oracle', ep), ('wolf', wp), ('verify', vp)]:
            (a.work / (name + '.' + phase + '.log')).write_bytes(p.stdout)
        eb, wb = oracle.read_bytes(), wolf.read_bytes()
        diffs = [i for i in range(len(eb)) if eb[i] != wb[i]]
        # Only wall-clock check/write timestamps and the mount counter are
        # non-layout choices; retain every other differing offset as a RED.
        unexpected = [i for i in diffs if not (1072 <= i < 1078 or 1088 <= i < 1092)]
        okay = len(eb) == len(wb) and unchanged and en.returncode == wn.returncode and ep.returncode == wp.returncode and vp.returncode == 0 and not unexpected
        result = {'case': name, 'report_unchanged': unchanged, 'oracle_report': en.returncode, 'wolf_report': wn.returncode, 'oracle_rc': ep.returncode, 'wolf_rc': wp.returncode,
                  'verify_rc': vp.returncode, 'byte_differences': len(diffs),
                  'unexpected_offsets': unexpected[:30], 'pass': okay}
        results.append(result)
        print(('PASS ' if okay else 'FAIL ') + 'journal-' + name + ': ' + json.dumps(result), flush=True)
    (a.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    return int(any(not row['pass'] for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
