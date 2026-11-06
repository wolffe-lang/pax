#!/usr/bin/env python3
"""px103: PAX's typed sudo session (upgrade.py's U14, captures in PAXDIR) against Linux's (sudo-linux.sh).

    sudo-compare.py PAXDIR LINUXDIR

The same lines, the same sudoers (Linux's has one more line, Defaults logfile). Compared byte for byte:
s-root.txt and s-wolf.txt with NO normalisation. The rest, each named:
  N1 s-lobo.txt: Linux asks for a password before it says no (lobo has no rule and PAX has no passwords,
     R1), so its two answers are "sudo: a password is required"; PAX's are its own refusals. The exit
     status line (rc=1) is equal.
  N2 s-log.txt: the time stamp is masked (Mon DD HH:MM:SS); PWD= is masked (/root on PAX's console, / in the
     container); PAX's first line is U13's own use (wolf running /bin/id before the session) and is dropped;
     the lines for lobo's two refusals are PAX's alone (Linux logs a refusal only after a password
     attempt) and are named below.
Exits 0 and prints the verdict per file, 1 on a difference outside the names.
"""
from pathlib import Path
import re
import sys

pax, lin = Path(sys.argv[1]), Path(sys.argv[2])
bad = 0


def say(ok, what):
    global bad
    print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    bad += not ok


for f in ('s-root', 's-wolf'):
    a, b = (pax/f'{f}.txt').read_bytes(), (lin/f'{f}.txt').read_bytes()
    say(a == b, f'{f}.txt: {a.count(b"rc=")} commands, PAX and Linux byte for byte ({len(a)} bytes), no normalisation')

a, b = (pax/'s-lobo.txt').read_text(), (lin/'s-lobo.txt').read_text()
N1_PAX = 'sudo: lobo is not in the sudoers file.\nrc=1\nUser lobo is not allowed to run sudo on pax.\nrc=1\n'
N1_LIN = 'sudo: a password is required\nrc=1\nsudo: a password is required\nrc=1\n'
say(a == N1_PAX and b == N1_LIN, 's-lobo.txt: both refuse with rc=1; the words are the named difference N1 (Linux asks for a password first)')


def norm(t):
    t = re.sub(r'^\w{3} [ \d]\d \d\d:\d\d:\d\d ', 'STAMP ', t, flags=re.M)
    return re.sub(r'PWD=\S+', 'PWD=*', t)


pl = norm((pax/'s-log.txt').read_text()).splitlines()
ll = norm((lin/'s-log.txt').read_text()).splitlines()
if pl and pl[0] == 'STAMP : wolf : PWD=* ; USER=root ; COMMAND=/bin/id':
    pl = pl[1:]
extra = ['STAMP : lobo : user NOT in sudoers ; PWD=* ; USER=root ;', '    COMMAND=/bin/id',
         'STAMP : lobo : user NOT in sudoers ; PWD=* ; USER=root ;', '    COMMAND=list']
rest = [l for l in pl if l not in extra]
say(rest == ll and len(pl) - len(rest) == 4,
    f's-log.txt: {len(ll)} lines equal after N2 (stamp and PWD masked, U13\'s line dropped); PAX\'s four extra lines are lobo\'s two refusals')
sys.exit(1 if bad else 0)
