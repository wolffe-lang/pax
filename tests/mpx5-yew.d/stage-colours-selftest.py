#!/usr/bin/env python3
"""Lock-free identity controls; these fixtures never execute a program."""
import hashlib
import os
from pathlib import Path
import runpy
import tempfile

HERE = Path(__file__).resolve().parent
stage = runpy.run_path(str(HERE / 'stage-colours.py'))['stage']
failures = 0
for case in ('valid', 'stale-source', 'wrong-sum', 'wrong-size', 'wrong-program'):
    with tempfile.TemporaryDirectory(prefix='yew-stage-', dir=os.environ['TMPDIR']) as temp:
        base = Path(temp)
        repo, images, root = (base / name for name in ('repo', 'images', 'root'))
        (repo / 'user').mkdir(parents=True)
        (repo / 'tests/mpx5-yew.d').mkdir(parents=True)
        revision = 'a' * 40
        (repo / 'user/yew.pin').write_text('YEW_REV=' + revision + '\n')
        (repo / 'tests/mpx5-yew.d/keyword.lu').write_bytes(b'if true { plain_word }\n')
        for name in ('yew', 'termwolf'):
            directory = images / name
            directory.mkdir(parents=True)
            data = (name + ' fixture, never executable').encode()
            (directory / name).write_bytes(data)
            (directory / 'sums.txt').write_text(f'{name} {hashlib.sha256(data).hexdigest()} {len(data)}\n')
        (images / 'yew/source.txt').write_text('yew ' + revision + '\n')
        if case == 'stale-source':
            (images / 'yew/source.txt').write_text('yew ' + 'b' * 40 + '\n')
        elif case == 'wrong-sum':
            (images / 'termwolf/termwolf').write_bytes(b'changed')
        elif case in ('wrong-size', 'wrong-program'):
            sums = images / 'yew/sums.txt'
            fields = sums.read_text().split()
            fields[2 if case == 'wrong-size' else 0] = '999' if case == 'wrong-size' else 'other'
            sums.write_text(' '.join(fields) + '\n')
        accepted = True
        try:
            stage(images, root, repo)
        except (OSError, ValueError):
            accepted = False
        good = accepted == (case == 'valid')
        if accepted:
            good = good and (root / 'bin/yew').read_bytes() == (images / 'yew/yew').read_bytes()
            good = good and (root / 'bin/yew').stat().st_mode & 0o777 == 0o755
        print(('PASS ' if good else 'FAIL ') + 'yew-stage-' + case, flush=True)
        failures += not good
raise SystemExit(int(bool(failures)))
