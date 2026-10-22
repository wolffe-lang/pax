"""Compare every replay; name, measure and count the one ruled blocker."""
from pathlib import Path
import difflib
import re
import sys

images, log, out = map(Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)
names = (images / 'run-names').read_text().splitlines()
if len(sys.argv) == 5:
    if sys.argv[4] not in names:
        raise SystemExit('unknown replay case: ' + sys.argv[4])
    names = [sys.argv[4]]
lines = log.read_text(errors='replace').splitlines()
failed = False

def norm(text):
    # Same job-pid mask as tests/mpx5-jobs; no semantic line removed.
    return re.sub(r'(?m)^(\[\d+\]) \d+$', r'\1 PID', text.replace('\r', '')).strip('\n') + '\n'

def diff(name, a, b):
    global failed
    if a != b:
        failed = True
        print('FAIL F1 ' + name)
        print(''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True), 'Linux', 'PAX')))
    else:
        print('PASS F1 ' + name + ': byte-identical')

for k, name in enumerate(names, 1):
    start = next((i + 1 for i, line in enumerate(lines) if line.startswith(f'run {k}: ')), None)
    part = []
    if start is not None:
        for line in lines[start:]:
            if re.match(r'^run \d+: |^run: \d+ commands$|^user: frames free ', line):
                break
            p = line.find('user: ')
            if p == 0:
                continue
            part.append(line + '\n' if p < 0 else line[:p])
    actual = norm(''.join(part))
    ref = images / 'linux' / (name + '.tty')
    if not ref.is_file():
        print('FAIL F1 missing Linux reference: ' + name); failed = True; continue
    expected = norm(ref.read_text(errors='replace'))
    (out / (name + '.pax')).write_text(actual)
    (out / (name + '.linux')).write_text(expected)
    if name.startswith('corpus-'):
        def cases(text):
            return dict((m.group(1), m.group(2)) for m in re.finditer(r'(?ms)^CASE:([^\n]+)\n(.*?^CASE-STATUS:\d+\n)', text))
        a, b = cases(actual), cases(expected)
        fixture = Path(__file__).resolve().parents[2] / 'user/console/fork/diff'
        required = sorted(str(p.relative_to(fixture))[:-3] for p in fixture.rglob('*.sh'))
        for case in required:
            if case not in a or case not in b:
                print('FAIL F1 missing corpus row: ' + name + ' ' + case); failed = True; continue
            if case == 'builtin/c_s_dot_special_file':
                # R-px61-1: explicitly test both answers, not a wildcard waiver.
                good = ('from the fifo\nfifo: 0' in b[case] and ('Operation not permitted' in a[case] or 'Permission denied' in a[case]))
                print(('PASS' if good else 'FAIL') + ' F1 NAMED FIFO BLOCKER ' + name + '\nLinux:\n' + b[case] + 'PAX:\n' + a[case])
                failed |= not good
            else:
                diff(name + ' ' + case, b[case], a[case])
        for witness in ('subshell: another process', 'substitution: another process', 'stage: another process',
                        'background subshell: a process', 'background group: a process', 'kept: 0 0', 'replaced'):
            if witness not in actual.splitlines():
                print('FAIL F2 fork witness ' + name + ': ' + witness); failed = True
        print('F1 corpus ' + name + ': 21 parity rows required; 1 named FIFO blocker')
    else:
        diff(name, expected, actual)
    if not actual.startswith('$ '):
        print('FAIL F2 missing first prompt: ' + name); failed = True
    if name.startswith('probes-') and any(x in actual for x in ('ps: invalid option', 'Usage: ps', 'ps-pgid:')):
        print('FAIL F2 unexercised process-group probe: ' + name); failed = True
    if name.startswith('selfcheck-') and 'selfcheck-status=0' not in actual.splitlines():
        print('FAIL F2 static table checks: ' + name); failed = True
    if name.startswith('shapes-') and len(re.findall(r'(?m)^SHAPE:[^\n]+:8$', actual)) != 11:
        print('FAIL F2 missing shape row: ' + name); failed = True
raise SystemExit(1 if failed else 0)
