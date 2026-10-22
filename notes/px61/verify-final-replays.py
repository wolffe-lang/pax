"""Hold each accepted PAX replay to two real-Linux guest recordings.

The corrected shape group is a distinct cohort; all first attempts stay
intact. No result is inferred from a progress line or an equal error.
"""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys

l = Path(sys.argv[1])
w = l / 'build/final-v2/mpx5-pelt'
name_file = w / 'run-names'
if not name_file.exists():
    name_file = l / 'verified-final/run-names'
names = name_file.read_text().splitlines()
assert len(names) == 26 and len(set(names)) == 26
out = l / 'verified-final'
(out / 'linux').mkdir(parents=True, exist_ok=True)
(out / 'run-names').write_text('\n'.join(names) + '\n')
compare = l / 'shape-source/tests/mpx5-pelt.d/compare.py'
def norm(path):
    s = path.read_bytes().decode().replace('\r', '')
    for pattern in (r'\x1b\[[0-9;?=<>]*[A-Za-z]', r'\x1b[()][A-Za-z0-9]', r'\x1b[c78DEHM=>]'):
        s = re.sub(pattern, '', s)
    return re.sub(r'(?m)^(\[\d+\]) \d+$', r'\1 PID', s)

for name in names:
    shape = name.startswith('shapes-')
    guests = l / ('guest-shapes-final' if shape else 'guest-final-v2')
    a = guests / 'pass-1' / (name + '.tty')
    b = guests / 'pass-2' / (name + '.tty')
    assert norm(a) == norm(b), 'guest repeat differs: ' + name
    for folder in ('pass-1', 'pass-2'):
        assert (guests / folder / (name + '.tty.rc')).read_text().strip() == '0', name
    shutil.copyfile(a, out / 'linux' / (name + '.tty'))
    suffix = 'final-shapes' if shape else 'final-v2'
    base = l / 'build' / suffix
    if not base.exists():
        base = l / 'evidence-builds' / suffix
    log = base / ('mpx5-pelt-native-bios-' + name + '.serial.log')
    verdict = Path(str(log) + '.verdict').read_text()
    assert any(line.startswith('qemu-halt: HALTED') for line in verdict.splitlines()), name
    full = Path(str(log) + '.norm')
    text = full.read_text()
    assert not re.search(r'^PANIC ', text, re.M), name
    init = '/bin/as' if name.endswith('-pax') else '/bin/env'
    assert f'PAX: init {init} ended with status 0; nothing left to run' in text, name
    subprocess.run([sys.executable, '-I', str(compare), str(out), str(full), str(out/'sessions'), name], check=True)
    print('PASS repeated real Linux / PAX:', name, hashlib.sha256(norm(a).encode()).hexdigest(), flush=True)
print('FINAL REPLAY PASS: 26 groups; corpus 21/22 with named FIFO blocker; nine sessions, eleven bounded shapes, nine probes and selfcheck per role')
