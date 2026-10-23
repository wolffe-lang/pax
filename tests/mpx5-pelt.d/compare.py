"""Compare every replay. px62: the FIFO row px61 named apart (R-px61-1,
pax#108) is an ordinary parity row: 22 of 22."""
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
lines = log.read_bytes().decode('utf-8').splitlines()
failed = False

def norm(text):
    # Same job-pid mask as tests/mpx5-jobs; no semantic line removed.
    text = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', text)
    text = re.sub(r'\x1b[()][A-Za-z0-9]', '', text)
    text = re.sub(r'\x1b[c78DEHM=>]', '', text).replace('\r', '')
    return re.sub(r'(?m)^(\[\d+\]) \d+$', r'\1 PID', text)

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
    expected = norm(ref.read_bytes().decode('utf-8'))
    (out / (name + '.pax')).write_text(actual)
    (out / (name + '.linux')).write_text(expected)
    if name.startswith('corpus-'):
        def cases(text):
            return dict((m.group(1), m.group(2)) for m in re.finditer(r'(?ms)^CASE:([^\n]+)\n(.*?^CASE-STATUS:\d+\n)', text))
        a, b = cases(actual), cases(expected)
        diff(name + ' complete envelope', expected, actual)
        fixture = Path(__file__).resolve().parents[2] / 'user/console/fork/diff'
        required = sorted(str(p.relative_to(fixture))[:-3] for p in fixture.rglob('*.sh'))
        for case in required:
            if case not in a or case not in b:
                print('FAIL F1 missing corpus row: ' + name + ' ' + case); failed = True; continue
            diff(name + ' ' + case, b[case], a[case])
            if case == 'builtin/c_s_dot_special_file' and 'from the fifo\nfifo: 0' not in a[case]:
                # px62: the row the FIFO served; equal failures are not parity.
                print('FAIL F1 the FIFO row did not read its FIFO: ' + name); failed = True
        for witness in ('subshell: another process', 'substitution: another process', 'stage: another process',
                        'background subshell: a process', 'background group: a process', 'kept: 0 0', 'replaced'):
            if witness not in actual.splitlines():
                print('FAIL F2 fork witness ' + name + ': ' + witness); failed = True
        print('F1 corpus ' + name + ': ' + str(len(required)) + ' parity rows required')
    else:
        diff(name, expected, actual)
    if not actual.startswith('$ '):
        print('FAIL F2 missing first prompt: ' + name); failed = True
    if name.startswith(('c_jc_mixed_pipeline-', 'jc_subshell_stop-', 'jc_subshell_redir_stop-')):
        if not re.search(r'(?m)^\[\d+\].*\bStopped\b', actual):
            print('FAIL F2 control key did not stop the job: ' + name); failed = True
    if name.startswith('c_jc_mixed_pipeline-') and not re.search(r'stopped jobs', actual, re.I):
        print('FAIL F2 first exit did not refuse the stopped job: ' + name); failed = True
    if name.startswith(('jc_subshell_stop-', 'jc_subshell_redir_stop-')):
        if not all(row in actual.splitlines() for row in ('back', 'st=0')):
            print('FAIL F2 foreground resume did not complete: ' + name); failed = True
    if name.startswith('probes-') and any(x in actual for x in ('ps: invalid option', 'Usage: ps', 'ps-pgid:')):
        print('FAIL F2 unexercised process-group probe: ' + name); failed = True
    if name.startswith('selfcheck-') and 'selfcheck-status=0' not in actual.splitlines():
        print('FAIL F2 static table checks: ' + name); failed = True
    if name.startswith('shapes-') and len(re.findall(r'(?m)^SHAPE:[^\n]+:8$', actual)) != 11:
        print('FAIL F2 missing shape row: ' + name); failed = True
raise SystemExit(1 if failed else 0)
