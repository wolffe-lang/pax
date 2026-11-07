#!/usr/bin/env python3
"""px103: PAX's typed sudo session (upgrade.py's U14, captures in PAXDIR) against Linux's (sudo-linux.sh).

    sudo-compare.py PAXDIR LINUXDIR

The same lines, the same sudoers (Linux's has one more line, Defaults logfile). Compared byte for byte:
s-root.txt, s-wolf.txt and (px106) s-lobo.txt with NO normalisation. px106 retires px103's N1: PAX's sudo
asks for the caller's password before it says no, as Linux's does, so lobo's two answers under -n are
"sudo: a password is required" on both, and neither logs them. The one name left:
  N2 s-log.txt: the time stamp is masked (Mon DD HH:MM:SS); PWD= is masked (/root on PAX's console, / in the
     container); PAX's first line is U13's own use (wolf running /bin/id before the session) and is dropped.
     px106: PAX's two extra lines for lobo's refusals are gone; any line left over is a difference.
Exits 0 and prints the verdict per file, 1 on a difference outside the name.
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


for f in ('s-root', 's-wolf', 's-lobo'):
    a, b = (pax/f'{f}.txt').read_bytes(), (lin/f'{f}.txt').read_bytes()
    say(a == b, f'{f}.txt: {a.count(b"rc=")} commands, PAX and Linux byte for byte ({len(a)} bytes), no normalisation')


def norm(t):
    t = re.sub(r'^\w{3} [ \d]\d \d\d:\d\d:\d\d ', 'STAMP ', t, flags=re.M)
    return re.sub(r'PWD=\S+', 'PWD=*', t)


pl = norm((pax/'s-log.txt').read_text()).splitlines()
ll = norm((lin/'s-log.txt').read_text()).splitlines()
if pl and pl[0] == 'STAMP : wolf : PWD=* ; USER=root ; COMMAND=/bin/id':
    pl = pl[1:]
say(pl == ll, f's-log.txt: {len(ll)} lines equal after N2 (stamp and PWD masked, U13\'s line dropped); no line for lobo on either')
sys.exit(1 if bad else 0)
