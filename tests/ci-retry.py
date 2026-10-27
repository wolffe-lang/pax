"""Exercise retry exits, scope, attempt limit and immutable first evidence."""
from pathlib import Path
import subprocess
import sys
import tempfile

TOOL = Path(__file__).resolve().parents[1] / 'tools/ci-retry'
KNOWN = "linux-tty: prompt 24 ('$ ') did not come for step 24: substitution\nmpx5-pelt: FAIL F0 Linux replay\n"


def case(root, name, outcomes, label='mpx5-pelt-linux', known=True, lose=None):
    d = root / name
    d.mkdir()
    logs, keep, counter = d / 'logs', d / 'evidence', d / 'count'
    keep.mkdir()
    (keep / 'tty').write_text('first terminal bytes')
    code = '''
from pathlib import Path
import json, sys
counter, logs, keep = map(Path, sys.argv[1:4])
n = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(n))
if n == 2:
    (keep / 'tty').write_text('second terminal bytes')
    lose = sys.argv[6]
    if lose:
        victim = logs / lose
        if victim.exists():
            victim.unlink()
print(sys.argv[5], end='')
exits = json.loads(sys.argv[4])
sys.exit(exits[min(n - 1, len(exits) - 1)])
'''
    import json
    r = subprocess.run([sys.executable, '-I', str(TOOL), label,
                        '--logs', str(logs), '--keep', str(keep), '--',
                        sys.executable, '-I', '-c', code, str(counter), str(logs), str(keep),
                        json.dumps(outcomes), KNOWN if known else 'unrelated failure\n', lose or ''],
                       capture_output=True, text=True)
    return r, int(counter.read_text()), logs


with tempfile.TemporaryDirectory(prefix='px83-ci-retry-') as tmp:
    root = Path(tmp)
    r, n, logs = case(root, 'green', [0])
    assert (r.returncode, n) == (0, 1), r.stdout + r.stderr
    assert '::warning::' not in r.stdout
    r, n, logs = case(root, 'recovered', [1, 0])
    assert (r.returncode, n) == (0, 2), r.stdout + r.stderr
    assert '::warning::flaky-known:pax#196' in r.stdout
    assert (logs / 'attempt-1.log').read_text() == KNOWN
    assert (logs / 'first-evidence/tty').read_text() == 'first terminal bytes'
    r, n, _ = case(root, 'still-red', [1, 1, 0])
    assert (r.returncode, n) == (1, 2), r.stdout + r.stderr
    for name, code, kwargs in [('build-error', 2, {}), ('signal-exit', 137, {}),
                               ('unknown-label', 1, {'label': 'unlisted'}),
                               ('unknown-failure', 1, {'known': False})]:
        r, n, _ = case(root, name, [code, 0], **kwargs)
        assert (r.returncode, n) == (code, 1), name + r.stdout + r.stderr
        assert '::warning::' not in r.stdout
    for name in ['attempt-1.log', 'first-evidence/tty']:
        r, n, _ = case(root, 'lose-' + name.replace('/', '-'), [1, 0], lose=name)
        assert (r.returncode, n) == (1, 2), 'ci-retry-first-log-loss: ' + r.stdout + r.stderr
        assert 'ci-retry-first-log-loss' in r.stdout
    print('PASS ci-retry-first-log-loss: rerun cannot hide missing original evidence')
    print('PASS ci-retry: one issue-scoped retry; original exit codes and transcripts retained')
