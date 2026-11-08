#!/usr/bin/env python3
"""px103: PAX's typed sudo session (upgrade.py's U14, captures in PAXDIR) against Linux's (sudo-linux.sh).

    sudo-compare.py PAXDIR LINUXDIR

The same lines, the same sudoers (Linux's has one more line, Defaults logfile). Compared byte for byte:
s-root.txt, s-wolf.txt and (px106) s-lobo.txt with NO normalisation. px106 retires px103's N1: PAX's sudo
asks for the caller's password before it says no, as Linux's does, so lobo's two answers under -n are
"sudo: a password is required" on both, and neither logs them. The one name left:
  N2 s-log.txt: each entry unwrapped first (sudo wraps at 80 columns, and the next mask moves the wrap); the
     time stamp is masked (Mon DD HH:MM:SS); PWD= is masked (/root on PAX's console, / in the container);
     px106: `TTY=NAME ; ` is dropped (PAX's lines are typed at its console, ttyS0; the container's run with no
     terminal, so Linux's sudo writes none); PAX's first five entries are U13's own uses on this disk before
     the session (R-px106-6 B3: wolf's `sudo -n /bin/id` refused at boot 1; at boot 2 /bin/id after a wrong
     password, `-n` within the timestamp, `-k` then `-n` refused, /bin/poweroff) and are dropped, those five
     exactly and in that order, so a change in U13's own logging shows here too.
     px106: PAX's two extra lines for lobo's refusals are gone; any entry left over is a difference.
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
    t = t.replace('\n    ', ' ')
    t = re.sub(r'^\w{3} [ \d]\d \d\d:\d\d:\d\d ', 'STAMP ', t, flags=re.M)
    t = re.sub(r'TTY=\S+ ; ', '', t)
    return re.sub(r'PWD=\S+', 'PWD=*', t)


U13 = ['STAMP : wolf : a password is required ; PWD=* ; USER=root ; COMMAND=/bin/id',
       'STAMP : wolf : PWD=* ; USER=root ; COMMAND=/bin/id',
       'STAMP : wolf : PWD=* ; USER=root ; COMMAND=/bin/id',
       'STAMP : wolf : a password is required ; PWD=* ; USER=root ; COMMAND=/bin/id',
       'STAMP : wolf : PWD=* ; USER=root ; COMMAND=/bin/poweroff']
pl = norm((pax/'s-log.txt').read_text()).splitlines()
ll = norm((lin/'s-log.txt').read_text()).splitlines()
if pl[:len(U13)] == U13:
    pl = pl[len(U13):]
what = f's-log.txt: {len(ll)} entries equal after N2 (unwrapped; stamp, TTY= and PWD masked; U13\'s five dropped); no entry for lobo on either'
if pl != ll:
    i = next((k for k in range(min(len(pl), len(ll))) if pl[k] != ll[k]), min(len(pl), len(ll)))
    what = (f's-log.txt: PAX {len(pl)} entries, Linux {len(ll)} after N2; the first difference, entry {i}: '
            f'PAX {pl[i] if i < len(pl) else "(none)"!r}, Linux {ll[i] if i < len(ll) else "(none)"!r}')
say(pl == ll, what)
sys.exit(1 if bad else 0)
