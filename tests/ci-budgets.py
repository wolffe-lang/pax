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


def tier_bound(job, tier):
    """px84: a limit tiered in the workflow, `${{ needs.plan.outputs.tier
    == 'all' && A || needs.plan.outputs.tier == 'pr' && B || C }}`: the
    named tier's minutes, else the trailing default's."""
    body = text.split('  ' + job + ':\n', 1)[1]
    body = re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]
    expr = re.search(r'^    timeout-minutes: \$\{\{(.*)\}\}$', body, re.M)[1]
    named = dict(re.findall(r"needs\.plan\.outputs\.tier == '(\w+)' && (\d+)", expr))
    default = re.search(r'\|\|\s*(\d+)\s*$', expr)[1]
    return int(named.get(tier, default)) * 60


def install_floors():
    """px84 (R-px84-6): mpx6-install, per tier. Each phase's floor is its
    peak over the recorded runs; a cancelled run's unreached phases are
    absent, never zero, so it raises a floor only where it got to. The big
    rows have no runner observation yet: each is its kasumi wall time scaled
    by the larger runner/kasumi ratio of the same smoke installs."""
    d = json.loads((DATA / 'install.json').read_text())
    names = ['units', 'inputs', 'smoke', 'faults', 'faults_tail', 'full_rows']
    peak = {n: max(r['phases'][n] for r in d['ci'] if n in r['phases']) for n in names}
    ratio = max(x['ci'] / x['kasumi'] for x in d['ratio'])
    big = {k: -(-v['kasumi_seconds'] * ratio // 1) for k, v in d['big'].items()}
    full = sum(peak.values()) + int(big['500gb']) + 180
    every = full + int(big['4tb'])
    pr = max(r['seconds'] for r in d['pr'] if r['conclusion'] == 'success')
    print('mpx6-install: phase peaks %s (sum %ds), runner/kasumi %.3f, 500 GB %ds, 4 TB %ds, setup/artifacts=180s' %
          (' '.join('%s=%d' % kv for kv in peak.items()), sum(peak.values()), ratio, big['500gb'], big['4tb']))
    return {'pr': pr, 'full': full, 'all': every}


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
# px84 (R-px84-6): the installer's limit is tiered; each tier against its floor.
for tier, floor in install_floors().items():
    seconds = tier_bound('mpx6-install', tier)
    ok = seconds * 10 >= floor * 14
    print('%s CI budget mpx6-install (tier %s): bound=%ds sizing-floor=%ds margin=%ds' %
          ('PASS' if ok else 'FAIL', tier, seconds, floor, seconds - floor))
    failed |= not ok
sys.exit(1 if failed else 0)
