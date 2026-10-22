#!/usr/bin/env python3
"""Exercise the actual deadline selection without booting unrelated images."""
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "tests/mpx5-users"
text = source.read_text()
match = re.search(r'(?m)^\s*deadline=900\n\s*\[ "\$s" != soak-user \] \|\| deadline=1200$', text)
if match is None:
    raise SystemExit("FAIL deadline: missing the soak-user-only 900/1200 selection")
assert '--timeout "$deadline"' in text, "selected deadline does not reach qemu-halt"
for session in ("soak-user", "soak", "own-soak", "own-soak-user", "chk-soak",
                "chk-soak-user", "rights-soak", "rights-soak-user", "cred", "ident-user"):
    script = 'set -eu\ns=$1\n' + match.group() + '\nprintf "%s" "$deadline"\n'
    result = subprocess.run(["bash", "-c", script, "deadline-test", session],
                            check=True, text=True, capture_output=True)
    want = "1200" if session == "soak-user" else "900"
    assert result.stdout == want, (session, result.stdout, want)
for session, command in (("soak", "/bin/ident soak 100000"),
                         ("soak-user", "/bin/as 1000 1000 /bin/ident soak 100000")):
    assert re.search(r'(?m)^\s*' + re.escape(session) + r'\)\s+echo "' +
                     re.escape(command) + r'"\s*;;\s*$', text), "full count changed: " + session
print("PASS deadline: soak-user 1200s; nine other session classes 900s; both 100000-round counts unchanged")
