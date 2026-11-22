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


def cap_for(job, outputs):
    """A job's `timeout-minutes` in seconds for the plan's outputs (tier, also_release, kvm): a number, or an
    expression over them, evaluated (`&&` and `||` as and and or, an absent output as the empty string)."""
    body = text.split('  ' + job + ':\n', 1)[1]
    body = re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]
    plain = re.search(r'^    timeout-minutes: (\d+)$', body, re.M)
    if plain:
        return int(plain[1]) * 60
    expr = re.search(r'^    timeout-minutes: \$\{\{(.*)\}\}$', body, re.M)[1]
    py = re.sub(r"needs\.plan\.outputs\.(\w+)", lambda m: repr(outputs.get(m[1], '')), expr)
    py = py.replace('&&', ' and ').replace('||', ' or ')
    return int(eval(py, {'__builtins__': {}}, {})) * 60


def tier_bound(job, tier):
    """px84, px113: a job's limit in the named tier (a TCG run with no release legs added), from cap_for."""
    return cap_for(job, {'tier': tier, 'also_release': '[]', 'kvm': 'no'})


def install_floors():
    """px84 (R-px84-6): mpx6-install, per tier. Each phase's floor is its
    peak over the recorded runs; a cancelled run's unreached phases are
    absent, never zero, so it raises a floor only where it got to. A big row
    is its kasumi wall time scaled by the larger runner/kasumi ratio of the
    same smoke installs, or its peak on the runner where runs have finished
    it (pax#467's chain, 2026-11-17), whichever is larger. The all tier also
    runs the serial-less install, a step of its own: its peak too."""
    d = json.loads((DATA / 'install.json').read_text())
    names = ['units', 'inputs', 'smoke', 'faults', 'faults_tail', 'full_rows']
    peak = {n: max(r['phases'][n] for r in d['ci'] if n in r['phases']) for n in names}
    ratio = max(x['ci'] / x['kasumi'] for x in d['ratio'])
    scaled = {k: int(-(-v['kasumi_seconds'] * ratio // 1)) for k, v in d['big'].items()}
    seen = {k: max([r['phases']['big_' + k] for r in d['ci'] if 'big_' + k in r['phases']], default=0) for k in scaled}
    big = {k: max(scaled[k], seen[k]) for k in scaled}
    noserial = max([r['phases']['noserial'] for r in d['ci'] if 'noserial' in r['phases']], default=0)
    full = sum(peak.values()) + big['500gb'] + 180
    every = full + big['4tb'] + noserial
    pr = max(r['seconds'] for r in d['pr'] if r['conclusion'] == 'success')
    print('mpx6-install: phase peaks %s (sum %ds), runner/kasumi %.3f, 500 GB %ds (scaled %ds, runner peak %ds), '
          '4 TB %ds (scaled %ds, runner peak %ds), serial-less %ds, setup/artifacts=180s' %
          (' '.join('%s=%d' % kv for kv in peak.items()), sum(peak.values()), ratio, big['500gb'], scaled['500gb'],
           seen['500gb'], big['4tb'], scaled['4tb'], seen['4tb'], noserial))
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
    # one word names the row (budget/mpx6-install/<tier>), as yew's are, so a plant's record can be
    # held to it by name
    print('%s budget/mpx6-install/%s CI budget mpx6-install (tier %s): bound=%ds sizing-floor=%ds margin=%ds' %
          ('PASS' if ok else 'FAIL', tier, tier, seconds, floor, seconds - floor))
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
# pax#467's follow-up: mpx5-jobs from its wall times, each tier against its own peak (no phase
# data for this job); the row named budget/mpx5-jobs/<tier>.
jobs = json.loads((DATA / 'jobs.json').read_text())
for tier in ('pr', 'full', 'all'):
    seen = [r['seconds'] for r in jobs['ci'] if r['tier'] == tier and r['conclusion'] == 'success']
    if not seen:
        continue
    floor = max(seen)
    seconds = tier_bound('mpx5-jobs', tier)
    ok = seconds * 10 >= floor * 14
    print('%s budget/mpx5-jobs/%s CI budget mpx5-jobs (tier %s): bound=%ds sizing-floor=%ds margin=%ds (%d runs)' %
          ('PASS' if ok else 'FAIL', tier, tier, seconds, floor, seconds - floor, len(seen)))
    failed |= not ok
# The twice rule (twice.json): a job's time cap is at least twice its slowest green run of the shape the cap
# applies to (its tier, the release legs a kernel change adds, KVM or TCG), so a slow runner is never a red
# that is no one's. Every job of the workflow but the plan and the verdict is held: a row for each measured
# shape (budget/twice/<job>/<shape>), an exception where twice passes GitHub's limit on a hosted job (its cap
# must then be that limit, budget/twice/<job>/<shape>/limit), or an unmeasured entry with its reason. A job
# with none of the three fails budget/twice/coverage, so a new job arrives with its entry.
twice = json.loads((DATA / 'twice.json').read_text())
LIMIT = twice['limit_minutes'] * 60


def shape(r):
    return r['tier'] + ('+release' if r['also_release'] != '[]' else '') + ('+kvm' if r['kvm'] == 'yes' else '')


for r in twice['rows']:
    cap = cap_for(r['job'], {'tier': r['tier'], 'also_release': r['also_release'], 'kvm': r['kvm']})
    ok = cap >= 2 * r['seconds']
    print('%s budget/twice/%s/%s cap=%ds slowest-green=%ds (run %d%s) twice=%ds margin=%ds' %
          ('PASS' if ok else 'FAIL', r['job'], shape(r), cap, r['seconds'], r['run'],
           ', the %s tier bounds it' % r['from'] if 'from' in r else '', 2 * r['seconds'], cap - 2 * r['seconds']))
    failed |= not ok
for r in twice['exceptions']:
    cap = cap_for(r['job'], {'tier': r['tier'], 'also_release': r['also_release'], 'kvm': r['kvm']})
    ok = cap >= LIMIT and r['seconds'] < LIMIT
    print('%s budget/twice/%s/%s/limit cap=%ds slowest-green=%ds (run %d): twice passes the %ds limit, so the cap is the limit' %
          ('PASS' if ok else 'FAIL', r['job'], shape(r), cap, r['seconds'], r['run'], LIMIT))
    failed |= not ok
held = {r['job'] for r in twice['rows'] + twice['exceptions']} | {u['job'] for u in twice['unmeasured']}
workflow_jobs = [j for j in re.findall(r'^  ([A-Za-z0-9_-]+):\s*$', text.split('\njobs:\n', 1)[1], re.M)
                 if j not in ('plan', 'tier')]
missing = [j for j in workflow_jobs if j not in held]
print('%s budget/twice/coverage every job but the plan and the verdict has a row, an exception or an unmeasured entry (%d jobs)%s' %
      ('FAIL' if missing else 'PASS', len(workflow_jobs), ': none for ' + ' '.join(missing) if missing else ''))
failed |= bool(missing)
# The silence cap (silence.json): a wrapped suite step is stopped when it prints nothing for its limit
# (tools/silence-cap), long before its job's cap when it hangs. Each limit is at least twice the longest silence
# measured inside that step, and at least the floor; it is under the job's cap on every leg (a one-leg tier's cap
# may come first); the step is exactly `tools/silence-cap LIMIT -- tests/JOB $PAX_LEGS`, so its exit 124 fails the
# job (no `||`, no pipe, no continue-on-error); no other step uses the tool; and the plan job runs its selftest.


def job_body(job):
    body = text.split('  ' + job + ':\n', 1)[1]
    return re.split(r'\n  [A-Za-z0-9_-]+:\n', body, maxsplit=1)[0]


silence = json.loads((DATA / 'silence.json').read_text())
for r in silence['rows']:
    job, limit = r['job'], r['limit_minutes']
    need = max(silence['floor_minutes'], 5 * -(-2 * r['seconds'] // 300))
    every_cap = cap_for(job, {'tier': 'all', 'also_release': '[]', 'kvm': 'no'})
    body = job_body(job)
    step = '        run: tools/silence-cap %d -- tests/%s $PAX_LEGS\n' % (limit, job)
    why = []
    if limit < need:
        why.append('limit %d min under max(%d, twice %d s)' % (limit, silence['floor_minutes'], r['seconds']))
    if limit * 60 >= every_cap:
        why.append('limit %d min not under the every-leg cap %d s' % (limit, every_cap))
    if step not in body:
        why.append('the suite step is not `%s`' % step.strip())
    if 'continue-on-error' in body:
        why.append('the job has continue-on-error')
    print('%s budget/silence/%s limit=%dmin silence=%ds (run %d) need=%dmin cap(all)=%ds%s' %
          ('FAIL' if why else 'PASS', job, limit, r['seconds'], r['run'], need, every_cap, ': ' + '; '.join(why) if why else ''))
    failed |= bool(why)
wrapping = sorted(j for j in workflow_jobs if 'tools/silence-cap' in job_body(j))
listed = sorted(r['job'] for r in silence['rows'])
plan_runs = 'python3 -I tests/silence-cap-selftest' in job_body('plan')
ok = wrapping == listed and plan_runs
print('%s budget/silence/only the steps silence.json lists use tools/silence-cap (%s), and the plan job runs its selftest (%s)' %
      ('PASS' if ok else 'FAIL', ' '.join(wrapping) or 'none', 'yes' if plan_runs else 'no'))
failed |= not ok
sys.exit(1 if failed else 0)
