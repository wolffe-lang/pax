#!/usr/bin/env python3
"""Measure the installed tree at 128 and 448 MiB, three checks per size."""
from pathlib import Path
import json
import runpy
import subprocess
import sys
import time

repo, work = Path(sys.argv[1]), Path(sys.argv[2])
p = work/'measure'
p.mkdir(parents=True, exist_ok=True)
api = runpy.run_path(str(repo/'tools/mkdisk'), run_name='px72_mkdisk')
stage = p/'stage'
stage.mkdir(exist_ok=True)
tree, _, _ = api['root_tree'](str(work/'native/rescue/root.cpio'), str(stage))
rows = []
for mib in [128, 448]:
    image = p/(str(mib)+'.img')
    with image.open('wb') as f:
        f.truncate(mib*1024*1024)
    subprocess.run(['mke2fs', '-q', '-F', '-t', 'ext2', '-b', '4096', '-d', tree, str(image)], check=True)
    times = []
    for i in range(3):
        start = time.perf_counter()
        q = subprocess.run([str(work/'bin/fsck.ext2'), '-fn', str(image)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        times.append(round(time.perf_counter()-start, 6))
        (p/f'{mib}-{i}.log').write_bytes(q.stdout)
        assert q.returncode == 0, q.stdout
    row = {'size_mib': mib, 'linux_seconds': times}
    rows.append(row)
    print(json.dumps(row), flush=True)
(p/'results.json').write_text(json.dumps(rows, indent=2)+'\n')
