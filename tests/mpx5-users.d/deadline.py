#!/usr/bin/env python3
"""Execute the actual deadline selection for both memory and disk roots."""
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'tests/mpx5-users'
text = source.read_text()
match = re.search(r'(?ms)^\s*deadline=900\n.*?^\s*hrc=0$', text)
if match is None:
    raise SystemExit('FAIL deadline: missing bounded deadline selection')
assert '--timeout "$deadline"' in text, 'selected deadline does not reach qemu-halt'
for disk in ('0', '1'):
    for session in ('soak-user', 'soak', 'own-soak', 'own-soak-user', 'chk-soak',
                    'chk-soak-user', 'rights-soak', 'rights-soak-user', 'cred', 'ident-user'):
        script = 'set -eu\ns=$1\nPAX_ROOTDISK=$2\n' + match.group() + '\nprintf "%s" "$deadline"\n'
        result = subprocess.run(['bash', '-c', script, 'deadline-test', session, disk],
                                check=True, text=True, capture_output=True)
        want = '1200' if session == 'soak-user' or (session == 'chk-soak' and disk == '1') else '900'
        assert result.stdout == want, ('deadline', session, disk, result.stdout, want)
for session, command in [('soak', '/bin/ident soak 100000'),
                         ('soak-user', '/bin/as 1000 1000 /bin/ident soak 100000'),
                         ('chk-soak', '/bin/chk soak 100000'),
                         ('chk-soak-user', '/bin/as 1000 1000 /bin/chk soak 100000')]:
    assert re.search(r'(?m)^\s*' + re.escape(session) + r'\)\s+echo "' +
                     re.escape(command) + r'"\s*;;\s*$', text), 'full count changed: ' + session
print('PASS deadline: only soak-user and rootdisk chk-soak get 1200s; all four 100000-round counts unchanged')
