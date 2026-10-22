"""Reject missing output, wrong status and identical unusable-helper output."""
from pathlib import Path
import subprocess
import sys
import tempfile

compare = Path(__file__).with_name('compare.py')
with tempfile.TemporaryDirectory(prefix='px61-compare-') as d:
    d = Path(d)
    (d / 'linux').mkdir()
    (d / 'run-names').write_text('selfcheck-root\n')
    (d / 'linux/selfcheck-root.tty').write_text('$ /bin/selfcheck; echo selfcheck-status=$?\nselfcheck-status=0\n$ exit 0\n')
    log = d / 'serial'
    def run(text):
        log.write_text(text)
        return subprocess.run([sys.executable, '-I', str(compare), str(d), str(log), str(d/'sessions')], capture_output=True, text=True)
    good = 'run 1: /bin/env\nuser: sh pid 2 start\n$ user: sh pid 2 syscall 273: -ENOSYS\n/bin/selfcheck; echo selfcheck-status=$?\nselfcheck-status=0\n$ exit 0\nuser: frames free 20 before, 20 after\n'
    r = run(good)
    assert r.returncode == 0, r.stdout + r.stderr
    (d / 'linux/selfcheck-root.tty').write_bytes(b'\x1b[6n$ /bin/selfcheck; echo selfcheck-status=$?\r\r\nselfcheck-status=0\r\n$ exit 0\r\r\n')
    r = run(good)
    assert r.returncode == 0, r.stdout + r.stderr
    r = run(good.replace('selfcheck-status=0\n', 'selfcheck-status=1\n'))
    assert r.returncode == 1 and 'FAIL F2 static table checks' in r.stdout
    r = run('run 1: /bin/env\nuser: frames free 20 before, 20 after\n')
    assert r.returncode == 1 and 'missing first prompt' in r.stdout
    (d / 'run-names').write_text('probes-root\n')
    body = "$ sh childstate.sh\n/bin/ps: invalid option -- p\nUsage: ps [-o COL]\n$ exit 0\n"
    (d / 'linux/probes-root.tty').write_text(body)
    r = run('run 1: /bin/env\n' + body + 'user: frames free 20 before, 20 after\n')
    assert r.returncode == 1 and 'PASS F1 probes-root' in r.stdout and 'FAIL F2 unexercised process-group probe' in r.stdout
print('px61 comparator selftest: PASS (green; wrong status, empty replay and identical unusable helper red)')
