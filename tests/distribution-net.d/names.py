#!/usr/bin/env python3
"""tests/distribution-net.d/names.py — px127: a program built on the dev image dials names.

    names.py SERIAL.LOG DNS.LOG LISTEN.LOG PORT TAG

The dev ISO's console, after distribution-net's witness, names the router
(10.0.2.2, which QEMU's user network hands to this host) as its only
nameserver, as an installed system's /etc/resolv.conf names its router;
tools/dns-fixture answers there (github.com is 10.0.2.2, everything else
NXDOMAIN) and a listener of this suite's own takes 10.0.2.2:PORT. At the
console user/console/distribution-names.keys types a program, builds it
with `wolf build` (the image's compiler, its musl link) and runs it: the
program dials each `HOST:PORT` it is given with std.net's `connect`.
Rows, each `PASS <row> …` or `FAIL <row> …` at column 0:
  N2  the program builds on the box (`PX127-BUILD=0`);
  N3  through DNS: github.com connects, nosuch.test answers `io`, the
      address 10.0.2.2 connects; the fixture answered the guest's A
      question for github.com; the listener took two connections;
  N4  from /etc/hosts alone: hosts.test connects, and the fixture was
      never asked for it.
Exit 0 when every row passed, 1 otherwise.
"""
import re
import sys
from pathlib import Path

serial, dns, listen = map(Path, sys.argv[1:4])
port, tag = sys.argv[4], sys.argv[5]
failed = 0


def row(name, good, why):
    global failed
    print('%s %s %s: %s' % ('PASS' if good else 'FAIL', name, tag, why), flush=True)
    failed |= not good


text = re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]', b'', serial.read_bytes()).replace(b'\r', b'').decode('latin-1')
lines = text.splitlines()


def block(begin, end):
    """The program's lines between two marker lines (the kernel's own lines left out)."""
    try:
        b = lines.index(begin)
        e = lines.index(end, b)
    except ValueError:
        return None
    return [l for l in lines[b + 1:e] if not l.startswith('user: ') and not l.startswith('$ ')]


asked = [l.split(' ', 3)[3] for l in (dns.read_text().splitlines() if dns.exists() else []) if l.startswith('QUERY ')]
accepts = [l for l in (listen.read_text().splitlines() if listen.exists() else []) if l.startswith('ACCEPT ')]

# wolf build's progress line has no newline of its own at a console, so the
# status may follow it on the same line; the typed command says `=$?`.
built = [m.group(1) for l in lines if not l.startswith('$ ') for m in [re.search(r'PX127-BUILD=([0-9]+)$', l)] if m]
row('N2', built == ['0'], 'wolf build of the dialer at the console: exit %s' % (built or 'not seen'))

want = ['github.com:%s: connected' % port, 'nosuch.test:%s: io' % port, '10.0.2.2:%s: connected' % port]
got = block('PX127-DNS=begin', 'PX127-DNS=end')
if got != want:
    row('N3', False, 'the dialer through DNS answered %s, not %s' % (got, want))
elif 'A github.com -> 10.0.2.2' not in asked:
    row('N3', False, 'the DNS fixture did not answer the guest\'s A question for github.com: %s' % asked)
elif len(accepts) < 2:
    row('N3', False, 'the listener took %d connections, not 2' % len(accepts))
else:
    row('N3', True, 'github.com from the DNS fixture connected, nosuch.test io, 10.0.2.2 connected (%s)' % ', '.join(sorted(set(asked))))

want = ['hosts.test:%s: connected' % port]
got = block('PX127-HOSTS=begin', 'PX127-HOSTS=end')
if got != want:
    row('N4', False, 'the dialer with /etc/hosts naming hosts.test answered %s, not %s' % (got, want))
elif any('hosts.test' in q for q in asked):
    row('N4', False, 'hosts.test was asked of DNS: /etc/hosts was not read first (%s)' % asked)
else:
    row('N4', True, 'hosts.test from /etc/hosts alone connected, never asked of DNS')
sys.exit(1 if failed else 0)
