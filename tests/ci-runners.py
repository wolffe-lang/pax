"""Every CI job runs on a pinned runner image, never a moving label (pax#474).

GitHub moved `ubuntu-latest` from Ubuntu 24.04 to 26.04 underneath the
workflow in November 2026: glibc 2.39 became 2.43, gcc 13.3 became 15.2 and
apt's QEMU 8.2.2 became 10.2.1, job by job as runners were handed out. A
pelt linked against glibc 2.43 asks PAX for TCGETS2, which PAX refuses until
#448, and never prints its prompt. So every Linux job names `ubuntu-24.04`,
and a newer image is a change to PINNED and the workflow together, made on
purpose and measured, never one the label makes for us.

    python3 -I tests/ci-runners.py [WORKFLOW]   every job's runs-on
    python3 -I tests/ci-runners.py --runner     and this runner's image
    python3 -I tests/ci-runners.py --selftest   the check's own proof

Rows (one word names each, so a plant's record can be held to it by name):
  runner/<job>       the job's `runs-on` is the label PINNED names for it
  runner/workflows   ci.yml is the only workflow, so no job goes unchecked
  runner/image       (--runner, the plan job's step) the runner this runs on
                     is the image its label promises: /etc/os-release's ID
                     and VERSION_ID, and the hosted runner's $ImageOS when it
                     is set. The plan job names the same label as every other
                     Linux job, so its runner stands for theirs.
"""
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github/workflows'

# The label every Linux job names.
LINUX = 'ubuntu-24.04'
# The jobs that name another label, and why. macos-run boots the
# linux-built ISO with Homebrew's QEMU, which moves with Homebrew whatever
# the image; pinning its image is a change of its own.
PINNED = {'macos-run': 'macos-latest'}
# What a label's runner must report: os-release ID and VERSION_ID, and the
# hosted image's $ImageOS.
IMAGES = {'ubuntu-24.04': ('ubuntu', '24.04', 'ubuntu24')}


def jobs(text):
    """Each job of a workflow's `jobs:` map, with its `runs-on` (None when
    the job names none, e.g. a reusable workflow's `uses:`)."""
    body = text.split('\njobs:\n', 1)[1]
    found = []
    for m in re.finditer(r'^  ([A-Za-z0-9_-]+):[ \t]*\n((?:(?:    .*|[ \t]*)\n)*)', body, re.M):
        ro = re.search(r'^    runs-on:[ \t]*(.*?)[ \t]*$', m[2], re.M)
        found.append((m[1], ro[1] if ro else None))
    return found


def check_jobs(text):
    """The runner/<job> rows: [(ok, line)]."""
    rows = []
    for job, label in jobs(text):
        want = PINNED.get(job, LINUX)
        ok = label == want
        rows.append((ok, '%s runner/%s runs-on %s%s' % (
            'PASS' if ok else 'FAIL', job, label or '(none)',
            '' if ok else ', not %s (pax#474: a moving label moves the image under the run)' % want)))
    return rows


def check_workflows(names):
    others = sorted(n for n in names if n != 'ci.yml')
    return (not others, '%s runner/workflows %s' % (
        'FAIL' if others else 'PASS',
        'not checked here: ' + ' '.join(others) if others else 'ci.yml is the only workflow'))


def os_release(path):
    fields = {}
    try:
        text = Path(path).read_text()
    except OSError:
        return fields
    for line in text.splitlines():
        k, sep, v = line.partition('=')
        if sep and not line.startswith('#'):
            fields[k.strip()] = v.strip().strip('"')
    return fields


def check_image(label, release, image_os, image_version):
    want_id, want_version, want_image_os = IMAGES[label]
    got = os_release(release)
    ok = got.get('ID') == want_id and got.get('VERSION_ID') == want_version and \
        image_os in (None, want_image_os)
    return (ok, '%s runner/image %s %s, ImageOS %s, ImageVersion %s; %s wants %s %s, ImageOS %s' % (
        'PASS' if ok else 'FAIL', got.get('ID'), got.get('VERSION_ID'), image_os or '(unset)',
        image_version or '(unset)', label, want_id, want_version, want_image_os))


def selftest():
    """Each row says FAIL where it should and PASS where it should, on
    fixtures: a workflow with a pinned, a moving, a missing and an excepted
    runs-on, and the two images' os-release files."""
    d = ROOT / 'tests/ci-runners.d'
    flow = ('name: t\non: push\njobs:\n'
            '  pinned:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n\n'
            '  # a comment between jobs\n'
            '  moving:\n    needs: pinned\n    runs-on: ubuntu-latest\n'
            '  newer:\n    runs-on: ubuntu-26.04  \n'
            '  called:\n    uses: ./.github/workflows/other.yml\n'
            '  macos-run:\n    runs-on: macos-latest\n')
    want = {'pinned': True, 'moving': False, 'newer': False, 'called': False, 'macos-run': True}
    got = {line.split()[1][len('runner/'):]: ok for ok, line in check_jobs(flow)}
    cases = [('jobs', got == want, '%s' % got)]
    cases.append(('workflows', check_workflows(['ci.yml'])[0] and
                  not check_workflows(['ci.yml', 'other.yml'])[0], ''))
    for name, image_os, ok in [('os-release-24.04', 'ubuntu24', True), ('os-release-24.04', None, True),
                               ('os-release-24.04', 'ubuntu26', False), ('os-release-26.04', 'ubuntu26', False),
                               ('os-release-26.04', None, False), ('no-such-file', None, False)]:
        verdict = check_image(LINUX, d / name, image_os, None)
        cases.append(('image %s ImageOS=%s' % (name, image_os or 'unset'), verdict[0] == ok, verdict[1]))
    failed = False
    for name, ok, detail in cases:
        print('%s runner/selftest %s%s' % ('PASS' if ok else 'FAIL', name, '' if ok else ': ' + detail))
        failed |= not ok
    return failed


def main(argv):
    if argv == ['--selftest']:
        return 1 if selftest() else 0
    runner = '--runner' in argv
    rest = [a for a in argv if a != '--runner']
    workflow = Path(rest[0]) if rest else WORKFLOWS / 'ci.yml'
    rows = check_jobs(workflow.read_text())
    if not rest:
        rows.append(check_workflows(p.name for p in WORKFLOWS.iterdir()))
    if runner:
        rows.append(check_image(LINUX, '/etc/os-release', os.environ.get('ImageOS'),
                                os.environ.get('ImageVersion')))
    for _, line in rows:
        print(line)
    bad = sum(not ok for ok, _ in rows)
    print('ci-runners: %d of %d rows FAIL' % (bad, len(rows)) if bad else
          'ci-runners: every row of %d PASS' % len(rows))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
