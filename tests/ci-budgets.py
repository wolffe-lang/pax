"""Check measured long-job envelopes; censored durations are lower bounds.

40% headroom is rounded upward in the workflow. This is a budget regression
check, not a claim that an unfinished job completed within its old timeout.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tests/ci-budgets.d'
workflow = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '.github/workflows/ci.yml'
text = workflow.read_text()
runs = json.loads((DATA / 'runs.json').read_text())
interrupts = json.loads((DATA / 'interrupts.json').read_text())
heap = [int(line.split('\t')[1]) for line in
        (ROOT / 'tests/mpx2-heap.d/ci-durations.tsv').read_text().splitlines()[1:]]


def bound(job):
    body = text.split('  ' + job + ':\n', 1)[1]
    body = re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]
    return int(re.search(r'^    timeout-minutes: (\d+)$', body, re.M)[1]) * 60


def envelope(job, extra):
    samples = [r for r in runs if r['job'] == job]
    main = max(r['main']['seconds'] for r in samples if r['main']['conclusion'] == 'success')
    roots = [r['rootdisk'] for r in samples if r['rootdisk'] and r['rootdisk']['conclusion'] in ('success', 'cancelled')]
    complete = max(r['seconds'] for r in roots if r['conclusion'] == 'success')
    observed = max(r['seconds'] for r in roots)
    # A cancelled rootdisk observation can raise the sizing floor but is
    # never described as a completed runtime or a proven upper bound.
    print('%s: main completed peak=%ds, root completed peak=%ds, root observed floor=%ds, extra=%ds, setup/artifacts=180s' %
          (job, main, complete, observed, extra))
    return main + observed + extra + 180


floors = {
    'mpx2-interrupts': max(r['seconds'] for r in interrupts if r['conclusion'] == 'success'),
    'mpx2-heap': max(heap),
    'mpx5-pelt': envelope('mpx5-pelt', 600),  # one Linux replay, measured <=504s plus timeout handling
    'mpx5-users': envelope('mpx5-users', 300),  # rootdisk chk-soak deadline delta
}
failed = False
for job, floor in floors.items():
    seconds = bound(job)
    ok = seconds * 10 >= floor * 14
    print('%s CI budget %s: bound=%ds sizing-floor=%ds margin=%ds' %
          ('PASS' if ok else 'FAIL', job, seconds, floor, seconds - floor))
    failed |= not ok
sys.exit(1 if failed else 0)
