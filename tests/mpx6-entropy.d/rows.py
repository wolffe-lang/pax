#!/usr/bin/env python3
"""tests/mpx6-entropy.d/rows.py — dw02: the rows of tests/mpx6-entropy.

    rows.py --images DIR NAME...

Each NAME is a boot, TIER-LEG-ACCEL-CONFIG, under DIR/boots/NAME (serial.log,
rc). The probes' lines are read from the serial log and held to the contract
(notes/dw02-the-entropy-contract.md, section 3):

  ready   the source is RDRAND and healthy: every valid flag set and both
          devices answer what was asked;
  none    the CPU has no RDRAND: the strict calls answer -1 EAGAIN;
  failed  RDRAND failed a draw (`fail`) or the boot's check (`stuck`): the
          strict calls answer -1 EIO, those that may not wait EAGAIN.

The insecure path (GRND_INSECURE, AT_RANDOM) answers in every state. Every
probe line is printed as a `~` line first: the measurement table. Prints
`mpx6-entropy: PASS <row> …` or `mpx6-entropy: FAIL <row> …` per row and
boot; exit 0 when every row held, 1 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

ME = 'mpx6-entropy'
STRICT = ['0', 'NONBLOCK', 'RANDOM', 'RANDOM|NONBLOCK']
INSECURE = ['INSECURE', 'INSECURE|NONBLOCK']
INVALID = ['RANDOM|INSECURE', '0x8']
CAP = 16384  # px131: getrandom(2)'s bytes a call
WOLF_TRAP = 134  # wolf's TRAP_EXIT_CODE

GR = re.compile(r'entropy: (early|later) getrandom (first )?flags (\S+) n (\d+) ret (-?\d+) errno (\S+) words (\d+) hirep (\d+)$')
RD = re.compile(r'entropy: (early|later) read (\S+)( nonblock)? n (\d+) ret (-?\d+) errno (\S+)(?: words (\d+) hirep (\d+)| open)$')
CP = re.compile(r'entropy: (early|later) cap (.*)$')
CPUID = re.compile(r'entropy: early cpuid vendor (\S+) rdrand (\d) rdseed (\d)$')
AUX = re.compile(r'entropy: (early|later) auxv at_random (\d) nonzero (\d) hieq (\d)$')
WOLF_GAVE = re.compile(r'wolf-entropy: os_random 32 gave (\d+)$')
WOLF_END = re.compile(r'user: wolf-entropy pid \d+ (exit_group (\d+)|killed: .*)')

failed = False


def say(*a):
    print(f'{ME}:', *a, flush=True)


def row(ok, name, boot, what):
    global failed
    if ok:
        say(f'PASS {name} {boot}: {what}')
    else:
        failed = True
        say(f'FAIL {name} {boot}: {what}')


class Boot:
    def __init__(self, d, name):
        self.name = name
        self.cfg = name.rsplit('-', 1)[1]
        self.serial = (d / 'serial.log').read_text(errors='replace') if (d / 'serial.log').exists() else ''
        self.rc = (d / 'rc').read_text().strip() if (d / 'rc').exists() else '?'
        self.lines = [ln.rstrip('\r') for ln in self.serial.splitlines()]
        self.gr = {}   # (phase, first, flags, n) -> (ret, errno, words, hirep)
        self.rd = {}   # (phase, path, nonblock, n) -> (ret, errno, words, hirep)
        self.cap = {'early': [], 'later': []}
        self.cpuid = None
        self.aux = {}
        self.wolf_gave = None
        self.wolf_end = None
        for ln in self.lines:
            if m := GR.search(ln):
                self.gr[(m[1], bool(m[2]), m[3], int(m[4]))] = (int(m[5]), m[6], int(m[7]), int(m[8]))
            elif m := RD.search(ln):
                w = (int(m[7]), int(m[8])) if m[7] is not None else (0, 0)
                self.rd[(m[1], m[2], bool(m[3]), int(m[4]))] = (int(m[5]), m[6]) + w
            elif m := CP.search(ln):
                self.cap[m[1]].append(m[2])
            elif m := CPUID.search(ln):
                self.cpuid = (m[1], int(m[2]), int(m[3]))
            elif m := AUX.search(ln):
                self.aux[m[1]] = (int(m[2]), int(m[3]), int(m[4]))
            elif m := WOLF_GAVE.search(ln):
                self.wolf_gave = int(m[1])
            elif m := WOLF_END.search(ln):
                self.wolf_end = int(m[2]) if m[2] is not None else -1

    def probe_lines(self):
        return [ln[ln.index('entropy: '):] for ln in self.lines if 'entropy: ' in ln]

    def capd(self, phase='early'):
        """The capability's first (`before the draws`) reading as words: key -> rest."""
        out = {}
        for c in self.cap[phase]:
            k, _, v = c.partition(' ')
            out.setdefault(k, v)
        return out

    def capd_last(self, phase='early'):
        out = {}
        for c in self.cap[phase]:
            k, _, v = c.partition(' ')
            out[k] = v
        return out

    def has(self, s):
        return any(s in ln for ln in self.lines)


def state_of(b):
    """What the contract says this boot's source is: ready, none or failed."""
    if b.cfg in ('present', 'retry'):
        return 'ready'
    if b.cfg == 'masked':
        return 'none'
    if b.cfg in ('fail', 'stuck'):
        return 'failed'
    # default: as its CPU says
    if b.cpuid is None:
        return None
    return 'ready' if b.cpuid[1] == 1 else 'none'


def strict_errno(state, flags):
    if state == 'none':
        return 'EAGAIN'
    return 'EAGAIN' if 'NONBLOCK' in flags else 'EIO'


def want_ok(got, n):
    """A delivered request: ret n, and independent words."""
    if got is None:
        return False, 'no line'
    ret, err, words, hirep = got
    want = min(n, CAP)
    return ret == want and err == '0' and hirep == 0, f'ret {ret} errno {err} hirep {hirep}/{words}, want ret {want} hirep 0'


def want_refused(got, errno):
    if got is None:
        return False, 'no line'
    ret, err = got[0], got[1]
    return ret == -1 and err == errno, f'ret {ret} errno {err}, want -1 {errno}'


def check(b):
    n = b.name
    for ln in b.probe_lines():
        print(f'~ {n} {ln}')
    capl = b.capd()
    print(f'~ {n} rc {b.rc}; capability {"absent" if not b.cap["early"] else "; ".join(b.cap["early"])}')
    # E0: the boot halted and the probe ended.
    row(b.rc == '0' and b.has('entropy: early end'), 'E0', n,
        f'qemu-halt {b.rc}, the probe\'s end line {"seen" if b.has("entropy: early end") else "missing"}')
    st = state_of(b)
    if st is None:
        row(False, 'E0', n, 'no cpuid line: the configuration\'s state is unknown')
        return
    if b.cpuid is not None:
        print(f'~ {n} cpuid vendor {b.cpuid[0]} rdrand {b.cpuid[1]} rdseed {b.cpuid[2]}; the contract\'s state {st}')

    # E1/E2/E5/E6: the strict calls and the devices, and the capability.
    why = []
    ok = True
    for f in STRICT:
        g = b.gr.get(('early', False, f, 32))
        good, w = want_ok(g, 32) if st == 'ready' else want_refused(g, strict_errno(st, f))
        ok &= good
        why.append(f'flags {f} n 32: {w}')
    for f in ('0',):
        g = b.gr.get(('early', False, f, 4096))
        good, w = want_ok(g, 4096) if st == 'ready' else want_refused(g, strict_errno(st, f))
        ok &= good
        why.append(f'flags {f} n 4096: {w}')
    for (path, nb, k) in (('/dev/urandom', False, 4096), ('/dev/random', False, 4096), ('/dev/random', True, 32),
                          ('/dev/urandom', True, 32)):
        g = b.rd.get(('early', path, nb, k))
        if st == 'ready':
            good, w = (g is not None and g[0] == k and g[1] == '0' and g[3] == 0,
                       f'ret {g[0]} errno {g[1]} hirep {g[3]}/{g[2]}' if g else 'no line')
        else:
            good, w = want_refused(g, 'EAGAIN' if (st == 'none' or nb) else 'EIO')
        ok &= good
        why.append(f'read {path}{" nonblock" if nb else ""} n {k}: {w}')
    if st == 'ready':
        capok = capl.get('ready') == 'yes' and capl.get('source') == 'rdrand'
        why.append(f'capability ready {capl.get("ready", "absent")} source {capl.get("source", "absent")}')
        rowname = 'E1'
    elif st == 'none':
        capok = capl.get('ready') == 'no' and capl.get('reason') == 'no-rdrand'
        why.append(f'capability ready {capl.get("ready", "absent")} reason {capl.get("reason", "absent")}')
        rowname = 'E2'
    else:
        want_reason = 'stuck' if b.cfg == 'stuck' else 'failed'
        last = b.capd_last()
        capok = last.get('ready') == 'no' and last.get('reason') == want_reason
        why.append(f'capability ready {last.get("ready", "absent")} reason {last.get("reason", "absent")}, want {want_reason}')
        rowname = 'E6' if b.cfg == 'stuck' else 'E5'
    row(ok and capok, rowname, n, '; '.join(why))

    # E3: the insecure path answers whatever the source; AT_RANDOM; glibc's start-up.
    why = []
    ok = True
    for f in INSECURE:
        g = b.gr.get(('early', False, f, 32))
        good = g is not None and g[0] == 32 and g[1] == '0'
        ok &= good
        why.append(f'flags {f} n 32: ' + (f'ret {g[0]} errno {g[1]} hirep {g[3]}/{g[2]}' if g else 'no line'))
    for k in (4096, 65536):
        g = b.gr.get(('early', False, 'INSECURE', k))
        good = g is not None and g[0] == min(k, CAP) and g[1] == '0'
        ok &= good
        why.append(f'flags INSECURE n {k}: ' + (f'ret {g[0]} errno {g[1]} hirep {g[3]}/{g[2]}' if g else 'no line'))
    a = b.aux.get('early')
    ok &= a is not None and a[0] == 1 and a[1] == 1
    why.append(f'AT_RANDOM {"present nonzero" if a and a[0] and a[1] else a} hieq {a[2] if a else "-"}')
    ok &= b.has('entropy: early malloc ok')
    why.append('static glibc started and allocated' if b.has('entropy: early malloc ok') else 'no `malloc ok`')
    row(ok, 'E3', n, '; '.join(why))

    # E4: retry's counts.
    if b.cfg == 'retry':
        last = b.capd_last()
        try:
            retried, failed_draws = int(last.get('retried', '-1')), int(last.get('failed', '-1'))
        except ValueError:
            retried, failed_draws = -1, -1
        row(st == 'ready' and retried >= 9 and failed_draws == 0 and last.get('ready') == 'yes', 'E4', n,
            f'capability retried {last.get("retried", "absent")} failed {last.get("failed", "absent")} '
            f'ready {last.get("ready", "absent")}: want retried >= 9, failed 0, ready yes')

    # E7: sizes.
    why = []
    ok = True
    g = b.gr.get(('early', False, '0', 0))
    good = g is not None and g[0] == 0 and g[1] == '0'
    ok &= good
    why.append('n 0: ' + (f'ret {g[0]} errno {g[1]}' if g else 'no line'))
    for k in (1, 7, 256, 16384, 65536, 1048576):
        g = b.gr.get(('early', False, '0', k))
        if st == 'ready':
            good = g is not None and g[0] == min(k, CAP) and g[1] == '0' and (k < 16 or g[3] == 0)
            w = f'n {k}: ' + (f'ret {g[0]} hirep {g[3]}/{g[2]}' if g else 'no line') + f', want {min(k, CAP)}'
        else:
            good, w0 = want_refused(g, strict_errno(st, '0'))
            w = f'n {k}: {w0}'
        ok &= good
        why.append(w)
    g = b.rd.get(('early', '/dev/urandom', False, 1048576))
    if st == 'ready':
        good = g is not None and g[0] == 1048576 and g[1] == '0' and g[3] == 0
        w = 'read /dev/urandom n 1048576: ' + (f'ret {g[0]} hirep {g[3]}/{g[2]}' if g else 'no line')
    else:
        good, w0 = want_refused(g, strict_errno(st, '0'))
        w = f'read /dev/urandom n 1048576: {w0}'
    ok &= good
    why.append(w)
    row(ok, 'E7', n, '; '.join(why))

    # E8: early and later alike.
    why = []
    ok = True
    first = b.gr.get(('early', True, '0', 32))
    own = b.gr.get(('early', False, '0', 32))
    ok &= first is not None and own is not None and first[:2] == own[:2]
    why.append(f'the first call {first[:2] if first else None}, the row {own[:2] if own else None}')
    for f in ('0', 'INSECURE'):
        e = b.gr.get(('early', False, f, 32))
        later = b.gr.get(('later', False, f, 32))
        ok &= e is not None and later is not None and e[:2] == later[:2]
        why.append(f'flags {f}: early {e[:2] if e else None}, later {later[:2] if later else None}')
    e = b.rd.get(('early', '/dev/urandom', False, 4096))
    later = b.rd.get(('later', '/dev/urandom', False, 32))
    ok &= e is not None and later is not None and (e[0] == -1) == (later[0] == -1) and e[1] == later[1]
    why.append(f'/dev/urandom: early {e[:2] if e else None}, later {later[:2] if later else None}')
    la = b.aux.get('later')
    ok &= la is not None and la[1] == 1
    ok &= b.has('entropy: early child status 0') and b.has('entropy: later end')
    why.append('the later process ran to its end' if b.has('entropy: later end') else 'no later end')
    row(ok, 'E8', n, '; '.join(why))

    # E9: wolf's os_random.
    if st == 'ready':
        row(b.wolf_gave == 32 and b.wolf_end == 0, 'E9', n, f'os_random(32) gave {b.wolf_gave}, exit {b.wolf_end}: want 32, 0')
    else:
        row(b.wolf_gave is None and b.wolf_end == WOLF_TRAP, 'E9', n,
            f'os_random(32) gave {b.wolf_gave}, exit {b.wolf_end}: want no count and exit {WOLF_TRAP} (the trap)')

    # E10: EINVAL.
    why = []
    ok = True
    for f in INVALID:
        g = b.gr.get(('early', False, f, 32))
        good, w = want_refused(g, 'EINVAL')
        ok &= good
        why.append(f'flags {f}: {w}')
    row(ok, 'E10', n, '; '.join(why))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', required=True)
    ap.add_argument('names', nargs='+')
    a = ap.parse_args()
    root = Path(a.images) / 'boots'
    for name in a.names:
        check(Boot(root / name, name))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
