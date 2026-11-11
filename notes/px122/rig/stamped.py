"""notes/px122/rig/stamped.py — px122's timing rig, two modes:

  stamped.py stamp OUT   stdin to stdout, each line `+SECONDS ` (since the start) first; a line
                         `FAIL …` or `<name>: FAIL …` goes out at column 0 as `FAIL …`, unstamped,
                         so the recorder keeps it there; every line, stamped, also to OUT
  stamped.py times BUILD the rows' time per leg in BUILD/suite.stamped and BUILD/irq.stamped (each
                         boot's `S5` row closes it), and the kernel's own `boot: N ms` lines in the
                         session logs under BUILD, per tier
  stamped.py timed CMD…  CMD (its output passed through), then one line: its wall seconds, its exit
                         and the largest resident set of any process under it (getrusage's children)

Nothing here judges: the times step prints numbers for two takes to be compared.
"""
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

FAIL = re.compile(r'^(?:[\w.-]+: )?(FAIL .*)$')
ROW = re.compile(r'^\+([0-9.]+) \S+: (?:PASS|FAIL) S5 (native|release) (bios|uefi) (\S+): ')
BOOT = re.compile(r'^boot: ([0-9]+) ms from the kernel.s entry to its first program; the console drew for ([0-9]+) ms', re.M)


def stamp(out):
    t0 = time.monotonic()
    with open(out, 'w') as copy:
        for line in sys.stdin:
            line = line.rstrip('\n')
            s = '+%.1f %s' % (time.monotonic() - t0, line)
            m = FAIL.match(line)
            print(m.group(1) if m else s, flush=True)
            copy.write(s + '\n')
            copy.flush()


def rows(path):
    legs, prev, last = {}, 0.0, 0.0
    for line in path.read_text(errors='replace').splitlines():
        m = ROW.match(line)
        if line.startswith('+'):
            try:
                last = float(line[1:].split(' ', 1)[0])
            except ValueError:
                pass
        if not m:
            continue
        t = float(m.group(1))
        leg = m.group(2) + ' ' + m.group(3)
        n, s = legs.get(leg, (0, 0.0))
        legs[leg] = (n + 1, s + t - prev)
        prev = t
    return legs, last


def times(build):
    build = Path(build)
    for name in ('suite', 'irq'):
        p = build / (name + '.stamped')
        if not p.exists():
            print('times: %s: no %s' % (name, p))
            continue
        legs, last = rows(p)
        boots = sum(n for n, _ in legs.values())
        print('times: %s: %.1f s in all, %d boots' % (name, last, boots))
        for leg in sorted(legs):
            n, s = legs[leg]
            print('times: %s %s: %d boots, %.1f s, %.2f s a boot' % (name, leg, n, s, s / n))
    seen = {}
    for p in sorted(build.rglob('*.serial.log')):
        m = BOOT.search(p.read_text(errors='replace'))
        if not m:
            continue
        tier = 'release' if '-release-' in p.name or '/release/' in str(p) else 'native'
        seen.setdefault(tier, []).append((int(m.group(1)), int(m.group(2))))
    for tier in sorted(seen):
        b = [x for x, _ in seen[tier]]
        d = [y for _, y in seen[tier]]
        print('times: kernel boot %s: %d logs, median %d ms (min %d, max %d); console drew median %d ms'
              % (tier, len(b), statistics.median(b), min(b), max(b), statistics.median(d)))


def timed(cmd):
    t0 = time.monotonic()
    rc = subprocess.run(cmd).returncode
    wall = time.monotonic() - t0
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    print('timed: %.1f s wall, exit %d, peak RSS %d MiB: %s' % (wall, rc, rss // 1024, ' '.join(cmd)), flush=True)
    return rc


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'timed':
        sys.exit(timed(sys.argv[2:]))
    elif len(sys.argv) == 3 and sys.argv[1] == 'stamp':
        stamp(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == 'times':
        times(sys.argv[2])
    else:
        sys.exit('usage: stamped.py stamp OUT | times BUILD | timed CMD...')
