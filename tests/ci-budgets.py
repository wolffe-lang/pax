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
    named tier's minutes, else the trailing default's. px113: a plain
    `timeout-minutes: N` is every tier's N."""
    body = text.split('  ' + job + ':\n', 1)[1]
    body = re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]
    plain = re.search(r'^    timeout-minutes: (\d+)$', body, re.M)
    if plain:
        return int(plain[1]) * 60
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


YS_PHASES = ['setup', 'programs', 'native', 'release', 's0',
             'native bios', 'release bios', 'native uefi', 'release uefi', 'post']
YS_ONE_LEG = ['setup', 'programs', 'native', 's0', 'native bios', 'post']


def yew_screen_floors(job):
    """px113 (pax#305): mpx5-yew and mpx5-screen, per tier. Each phase's
    floor is its peak over the job's attempts in yew-screen.json (every
    completed attempt 2026-11-01 to 2026-11-09, read from the job logs): a
    green attempt's phases, and a cancelled attempt's phases up to the one
    it was cut in, that one a lower bound; an attempt with a FAIL row is a
    red of its own, never a sample. The all tier (and a partial dispatch,
    which may name every leg) runs every phase; pr and full run one leg,
    native BIOS, and no release build."""
    d = json.loads((DATA / 'yew-screen.json').read_text())
    obs = [r for r in d['ci'] if r['job'] == job and 'red' not in r]
    peak = {n: max(r['phases'][n] for r in obs if n in r['phases']) for n in YS_PHASES}
    every = sum(peak.values())
    one = sum(peak[n] for n in YS_ONE_LEG)
    print('%s: %d attempts, phase peaks %s (every leg %ds, native BIOS alone %ds)' %
          (job, len(obs), ' '.join('%s=%d' % (n.replace(' ', '-'), v) for n, v in peak.items()), every, one))
    return {'all': every, 'partial': every, 'full': one, 'pr': one}


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


def ahci_root_floor():
    """px75b (R-px75b-6): mpx5-users-ahci builds mpx5-users' native BIOS
    images and boots all 25 again with / on AHCI. Its leg is sized from
    two things, the larger kept: its own CI observations, and the users
    job's virtio root leg (the same boots on another bus) scaled by the
    two legs' ratio measured side by side on one host under TCG, as CI
    boots."""
    ahci = json.loads((DATA / 'ahci-root.json').read_text())
    users_root = max(r['rootdisk']['seconds'] for r in runs
                     if r['job'] == 'mpx5-users' and r['rootdisk']
                     and r['rootdisk']['conclusion'] in ('success', 'cancelled'))
    tcg = ahci['host_tcg_seconds']
    scaled = -(-users_root * tcg['ahci'] // tcg['virtio'])
    observed = [r for r in ahci['ci'] if r['leg']['conclusion'] in ('success', 'cancelled')]
    leg = max([scaled] + [r['leg']['seconds'] for r in observed])
    build = max(r['build']['seconds'] for r in ahci['ci'])
    print('mpx5-users-ahci: users root observed floor=%ds x tcg %d/%d = %ds, ci leg peak=%s, build peak=%ds, setup/artifacts=180s' %
          (users_root, tcg['ahci'], tcg['virtio'], scaled,
           max((r['leg']['seconds'] for r in observed), default='none'), build))
    return build + leg + 180


SP_TIERS = {'all': ('all',), 'partial': ('all', 'partial'), 'full': ('full',), 'pr': ('pr',)}


def job_steps(job):
    """px122: the job's named steps in the workflow, in order (`      - name: …`); the steps GitHub
    names itself (setup, `uses:` without a name, the post steps) are the 180 s allowance's."""
    body = text.split('  ' + job + ':\n', 1)[1]
    body = re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]
    return re.findall(r'^      - name: (.+)$', body, re.M)


def step_floors(job):
    """px122 (trunk's cancelled runs of 2026-11-11): mpx3-shell and mpx5-pelt, step by step, per
    tier, from their attempts in shell-pelt.json (notes/px122/measure/runs.py). Each named step's
    floor is its peak over the tier's attempts where it completed or was cut at the limit (a cut
    step is a lower bound, which can only raise the floor); a step that failed is a red of its own,
    never a sample; a step the tier skips costs nothing. The job's floor is its named steps' sum and
    180 s for what GitHub runs itself. Also returns the named steps no attempt of the job has ever
    timed: a new step in a budgeted job is red here, on its pull request, until it is measured."""
    d = json.loads((DATA / 'shell-pelt.json').read_text())
    rows = [r for r in d['ci'] if r['job'] == job]
    steps = job_steps(job)
    timed = {n for r in rows for n, (_, c) in r['steps'].items() if c in ('success', 'cancelled')}
    out = {}
    for tier, kinds in SP_TIERS.items():
        peak = {}
        for r in rows:
            if r['tier'] not in kinds:
                continue
            for n, (secs, c) in r['steps'].items():
                if c in ('success', 'cancelled'):
                    peak[n] = max(peak.get(n, 0), secs)
        n_obs = len([r for r in rows if r['tier'] in kinds])
        out[tier] = sum(peak.get(n, 0) for n in steps) + 180
        print('%s (tier %s): %d attempts, step peaks %s, setup/post=180s' % (
            job, tier, n_obs, ' '.join('%d' % peak.get(n, 0) for n in steps)))
    return out, [n for n in steps if n not in timed]


floors = {
    'mpx2-interrupts': max(r['seconds'] for r in interrupts if r['conclusion'] == 'success'),
    'mpx2-heap': max(heap),
    'mpx5-pelt': envelope('mpx5-pelt', 600),  # one Linux replay, measured <=504s plus timeout handling
    'mpx5-users': envelope('mpx5-users', 300),  # rootdisk chk-soak deadline delta
    'mpx5-users-ahci': ahci_root_floor(),  # px75b, R-px75b-6
}
failed = False
for job, floor in floors.items():
    # px122: mpx5-pelt's limit is tiered now; these rows are its all tier's (every leg)
    seconds = tier_bound(job, 'all')
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
# px113 (pax#305): yew's two jobs, each tier against its floor.
for job in ('mpx5-yew', 'mpx5-screen'):
    for tier, floor in yew_screen_floors(job).items():
        seconds = tier_bound(job, tier)
        ok = seconds * 10 >= floor * 14
        # one word names the row (budget/<job>/<tier>), so a plant's
        # record can be held to it by name
        print('%s budget/%s/%s CI budget %s (tier %s): bound=%ds sizing-floor=%ds margin=%ds' %
              ('PASS' if ok else 'FAIL', job, tier, job, tier, seconds, floor, seconds - floor))
        failed |= not ok
# px122: mpx3-shell and mpx5-pelt, each tier against its floor, step by step; and every named step
# of either job timed by some attempt.
for job in ('mpx3-shell', 'mpx5-pelt'):
    tiers, untimed = step_floors(job)
    for tier, floor in tiers.items():
        seconds = tier_bound(job, tier)
        ok = seconds * 10 >= floor * 14
        print('%s budget/%s/%s CI budget %s (tier %s): bound=%ds sizing-floor=%ds margin=%ds' %
              ('PASS' if ok else 'FAIL', job, tier, job, tier, seconds, floor, seconds - floor))
        failed |= not ok
    print('%s budget/%s/steps CI budget %s: %s' % (
        'FAIL' if untimed else 'PASS', job, job,
        'no attempt has timed ' + '; '.join(repr(n) for n in untimed) if untimed
        else 'every named step timed by an attempt'))
    failed |= bool(untimed)
sys.exit(1 if failed else 0)
