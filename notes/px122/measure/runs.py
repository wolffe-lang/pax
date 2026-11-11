"""notes/px122/measure/runs.py SINCE OUT.json — px122: every attempt of the ci workflow's mpx3-shell and
mpx5-pelt jobs since SINCE (a date), step by step, read from GitHub's API in pages of 30 (the jobs
endpoint answers a page of 100 with a 502 on runs this large), for tests/ci-budgets.py.

Each attempt is one row: run, attempt, the head, the event, the plan's tier, the job's conclusion, and
each named step's seconds and conclusion. The tier is the run's verdict job's (`tier all`, `tier full`,
`tier pr`, `tier partial`), whose name the plan gives it; an attempt whose run has no verdict job yet
(still running) has the tier `unknown` and is no sample. A step GitHub names for
itself (`Set up job`, `Run actions/…`, `Post Run …`, `Complete job`) is not kept: the budget's fixed
180 s allowance covers them. A job copied into a later attempt unchanged (the same job id) counts once.
Uses `gh api`; reads only.
"""
import datetime
import json
import subprocess
import sys

REPO = 'wolffe-lang/pax'
JOBS = ('mpx3-shell', 'mpx5-pelt')
OWN = ('Set up job', 'Complete job')


def api(path):
    for _ in range(4):
        p = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
    sys.exit('runs.py: gh api %s: %s' % (path, p.stderr.strip()[:200]))


def secs(a, b):
    if not a or not b:
        return None
    f = lambda s: datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return int((f(b) - f(a)).total_seconds())


def main(since, out):
    runs, page = [], 1
    while True:
        d = api('repos/%s/actions/workflows/ci.yml/runs?per_page=100&page=%d&created=>=%s' % (REPO, page, since))
        runs += d['workflow_runs']
        if len(d['workflow_runs']) < 100:
            break
        page += 1
    rows, seen = [], set()
    for r in sorted(runs, key=lambda r: r['created_at']):
        if r['status'] != 'completed' and r['event'] != 'push':
            continue
        jobs, page = [], 1
        while True:
            d = api('repos/%s/actions/runs/%d/jobs?filter=all&per_page=30&page=%d' % (REPO, r['id'], page))
            jobs += d['jobs']
            if len(d['jobs']) < 30:
                break
            page += 1
        for j in jobs:
            if j['name'] not in JOBS or j['id'] in seen or j['status'] != 'completed':
                continue
            seen.add(j['id'])
            steps = {}
            for s in j['steps']:
                n = s['name']
                if n in OWN or n.startswith('Run actions/') or n.startswith('Post Run '):
                    continue
                steps[n] = [secs(s['started_at'], s['completed_at']) or 0, s['conclusion']]
            names = [x['name'] for x in jobs if x['name'].startswith('tier ')]
            tier = names[0].split(' ', 1)[1] if names else 'unknown'
            rows.append({'run': r['id'], 'attempt': j.get('run_attempt'), 'job': j['name'], 'head': r['head_sha'][:8],
                         'event': r['event'], 'tier': tier, 'conclusion': j['conclusion'],
                         'seconds': secs(j['started_at'], j['completed_at']), 'steps': steps})
    json.dump({'source': 'GitHub API, ci workflow runs created since %s, read %s' % (
        since, datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')), 'ci': rows},
        open(out, 'w'), indent=1, sort_keys=True)
    print('runs.py: %d runs, %d attempts of the two jobs' % (len(runs), len(rows)))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: runs.py SINCE OUT.json')
    main(sys.argv[1], sys.argv[2])
