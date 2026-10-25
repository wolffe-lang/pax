#!/usr/bin/env python3
"""Run every generated repair image through the same static binary on PAX."""
from pathlib import Path
import json
import os
import re
import runpy
import shutil
import subprocess
import sys

repo, work = Path(sys.argv[1]), Path(sys.argv[2])
d = Path(__file__).resolve().parent
api = runpy.run_path(str(d/'corpus.py'), run_name='px72_corpus')
p = work/'pax-corpus'
p.mkdir(parents=True, exist_ok=True)
(p/'run').write_text('/bin/fsck.ext2 -fy /dev/vdb\n')


def run(argv, name):
    q = subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (p/(name+'.log')).write_bytes(q.stdout)
    return q


q = run([repo/'tools/mkinitramfs', p/'init.cpio', '/bin/fsck.ext2='+str(work/'bin/fsck.ext2')+':755',
         '/etc/pax-run='+str(p/'run')+':644'], 'cpio')
assert q.returncode == 0, q.stdout
kernel = work/'native/kernel/kmain_console.elf'
if not kernel.exists(): kernel = work/'release/kernel/kmain_console.elf'
q = run([repo/'tools/mkdisk', '--gpt', '--kernel', kernel,
         '--initramfs', p/'init.cpio', '128M', p/'boot.img'], 'disk')
assert q.returncode == 0, q.stdout
results = []
for family in ['corpus', 'journal', 'refusals']:
    expected = json.loads((work/family/'results.json').read_text())
    for entry in expected:
        name = entry.get('name', entry.get('case'))
        source = work/family/(name+'.img')
        target = p/(family+'-'+name+'.img')
        shutil.copyfile(source, target)
        serial = p/(family+'-'+name+'.serial')
        q = run(['python3', '-I', d/'boot.py', repo, p/'boot.img', serial, 'bios', 'halt', target], family+'-'+name+'.boot')
        assert q.returncode == 0, q.stdout
        text = serial.read_text()
        match = re.search(r'fsck.ext2 pid 1 exit_group (\d+)', text)
        assert match, text
        code = int(match[1])
        want = entry['wolf_rc'] if family == 'journal' else entry['wolf_repair']
        assert code == want, (family, name, code, want, text)
        if not entry.get('supported', True):
            assert source.read_bytes() == target.read_bytes()
            row = {'case': family+'-'+name, 'supported': False, 'pax_status': code, 'unchanged': True}
            print('UNSUPPORTED PAX-' + name + ': refused without writes', flush=True)
        else:
            q = run([repo/'tools/e2fs', work, 'e2fsck', '-fn', target], family+'-'+name+'.verify')
            assert q.returncode == 0, q.stdout
            if family == 'corpus':
                compare = api['byte_differences'](name, work/family/(name+'.oracle.img'), target)
                assert not compare['unexpected_offsets'], compare
                assert api['tree'](target) == api['tree'](work/family/(name+'.oracle.img'))
            else:
                a, b = (work/family/(name+'.oracle.img')).read_bytes(), target.read_bytes()
                diff = [i for i,(x,y) in enumerate(zip(a,b)) if x != y and not (1072 <= i < 1078 or 1088 <= i < 1092)]
                assert len(a) == len(b) and not diff, (name, len(a), len(b), diff[:32])
            row = {'case': family+'-'+name, 'supported': True, 'pax_status': code, 'oracle_verify': 0, 'pass': True}
            print('PASS PAX-' + family + '-' + name, flush=True)
        results.append(row)
        target.unlink()
(p/'results.json').write_text(json.dumps(results, indent=2)+'\n')
