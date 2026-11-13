#!/usr/bin/env python3
# rows.py — tests/mpx6-latency's rows (px131), from each boot's report
# (the probe's lines as the host's echo collected them, else the serial
# log).
#
#   rows.py --guard-loads MIB            the guard's run list for a boot of MIB MiB
#   rows.py --accel A --images DIR --com1 0|1 BOOT...   the rows (BOOT is tier-firmware-mib)
#
# L1 every load's line, with samples; the end line; the instrument on.
# L2 each GUARD load: the sleeper's worst lateness, the loopback echo's
#    and the host's network echo's worst round trip, each over the same boot's
#    `spin` (the CPU's hog with no system call), at most BOUND; under TCG
#    SKIPPED by name (TCG's timings are the emulator's first). Each PENDING
#    load is measured the same way and printed as a `~L2` line naming the
#    work that will bound it, held to nothing until then.
# L4 the clocks: over each CLOCKED load's window, the time CLOCK_MONOTONIC
#    and CLOCK_REALTIME say passed, each within CLOCK_BOUND of the time-stamp
#    counter's (a clock that counts delivered ticks loses the time a long
#    call takes); under TCG too (the counter is the guest's own).
# L5 the network's wake-ups: beside `spin`, the host's ping's p99 at most
#    WAKE_BOUND times its p99 at `idle` (the device's interrupt, netd and the
#    echo run at once, not a quantum a hop); under TCG SKIPPED by name.
# L6 a hog under a ping flood: `flood`'s ops (1 ms of CPU each) at least
#    FLOOD_SHARE of `spin`'s (device wake-ups that run at once must not
#    starve a CPU-bound process); under TCG SKIPPED by name.
# L3 `~` lines: every load's figures (the measurement table's rows).
# Exit 0 when L1, L2, L4, L5 and L6 held, 1 otherwise.
import re
import sys
from pathlib import Path

# The guarded loads: the worst of the measurement table that a user can
# cause at will whose fix has landed (notes/px131-long-kernel-paths.md):
# munmap of a terabyte where nothing is mapped, getrandom of 8 MiB and a
# read of 8 MiB of /proc/self/mem.
def guard(mib):
    return ['hole:1024', 'random:8', 'procmem:8']


# The worst that are measured but not yet bounded, each with the work that
# will bound it: the console's write (the console's own lane), a large
# write to a file of the tree and fork of a large process (structural:
# the note's proposals).
def pending(mib):
    return [('console:65536', 'the console write drawn in bounded pieces (its own lane)'),
            ('write:%d' % (mib // 16), 'a file write in bounded pieces (proposal)'),
            ('fork:%d' % (mib // 8), 'fork without the eager copy (proposal)')]

BOUND = 3.0  # the worst beside a guarded load, over the worst beside `spin`

# L4's loads (long calls with interrupts off at this head: the clocks must
# keep the counter's time across them) and its bound: a clock's elapsed
# time within 2 % of the counter's over a window of SECONDS (a tick is 0.3 %
# of 3 s).
def clocked(mib):
    return ['console:65536', 'write:%d' % (mib // 16)]

CLOCK_BOUND = 0.02
WAKE_BOUND = 3.0   # L5: the ping's p99 beside `spin`, over its p99 at `idle`
FLOOD_SHARE = 0.5  # L6: `flood`'s ops over `spin`'s

LINE = re.compile(r'^latprobe (\S+): wake n (\d+) p50 (\d+) p99 (\d+) max (\d+); lo n (\d+) p50 (\d+) max (\d+) lost (\d+); '
                  r'(?:net n (\d+) p50 (\d+) max (\d+) lost (\d+)|net -); ops (\d+) max (\d+); '
                  r'(?:irqoff (\d+) vector 0x([0-9a-f]+) nr (\d+); schedgap (\d+); ticks (\d+) of (\d+); sys (.*)|irqoff -.*)$')


HOST = re.compile(r'^hostnet (\S+): n (\d+) p50 (\d+) p99 (\d+) max (\d+) lost (\d+)$')
CLOCKS = re.compile(r'; clocks mono (-?\d+) real (-?\d+) tsc (\d+)$')


def parse(text):
    out = {}
    host = {}
    for l in text.replace('\r', '').splitlines():
        # a serial log's line may follow a console flood's bytes
        i = l.find('latprobe ')
        if i > 0 and not l.startswith('hostnet'):
            l = l[i:]
        h = HOST.match(l.strip())
        if h:
            host[h.group(1)] = [int(x) for x in h.groups()[1:]]
            continue
        l = l.strip()
        c = CLOCKS.search(l)
        if c:
            l = l[:c.start()]
        m = LINE.match(l)
        if not m:
            continue
        g = m.groups()
        num = lambda i: int(g[i]) if g[i] is not None else None
        out[g[0]] = dict(wn=num(1), w50=num(2), w99=num(3), wmax=num(4), ln=num(5), l50=num(6), lmax=num(7), llost=num(8),
                         nn=num(9), n50=num(10), nmax=num(11), nlost=num(12), ops=num(13), opmax=num(14),
                         irq=num(15), vec=g[16], nr=num(17), gap=num(18), td=num(19), te=num(20), sys=g[21],
                         mono=int(c.group(1)) if c else None, real=int(c.group(2)) if c else None, tsc=int(c.group(3)) if c else None)
    for k, (n, p50, p99, mx, lost) in host.items():
        if k in out:
            out[k].update(nn=n, n50=p50, n99=p99, nmax=mx, nlost=lost)
    return out


def say(s):
    print('mpx6-latency: ' + s, flush=True)


def clock_rows(boot, tier, mib, rows, want):
    """L4: each clocked load's two clocks against the counter."""
    fail = 0
    for g in clocked(mib):
        r = rows.get(g)
        if r is None:
            if g in want and tier != 'linux':
                say('FAIL L4 %s %s: no line' % (boot, g))
                fail = 1
            continue
        if r['tsc'] is None:
            say('FAIL L4 %s %s: no clocks in the line' % (boot, g))
            fail = 1
            continue
        t = max(r['tsc'], 1)
        km, kr = r['mono'] / t, r['real'] / t
        txt = 'CLOCK_MONOTONIC %d us, CLOCK_REALTIME %d us of the counter\'s %d us: %.3f and %.3f' % (r['mono'], r['real'], t, km, kr)
        if abs(km - 1) <= CLOCK_BOUND and abs(kr - 1) <= CLOCK_BOUND:
            say('PASS L4 %s %s: %s; bound %.0f %%' % (boot, g, txt, CLOCK_BOUND * 100))
        else:
            say('FAIL L4 %s %s: %s; bound %.0f %% (irqoff %s us)' % (boot, g, txt, CLOCK_BOUND * 100, r['irq']))
            fail = 1
    return fail


def wake_rows(boot, tier, accel, rows, want):
    """L5: the host's ping beside `spin` against `idle`; L6: `flood` against `spin`."""
    fail = 0
    if tier == 'linux' or 'flood' not in want:
        return 0
    i, s, f = rows.get('idle'), rows.get('spin'), rows.get('flood')
    if not (i and s and f) or i.get('n99') is None or s.get('n99') is None:
        say('FAIL L5 %s: no idle, spin or flood line with the host\'s pings' % boot)
        return 1
    r5 = s['n99'] / max(i['n99'], 1)
    t5 = 'the ping beside spin p99 %d us (p50 %d), at idle p99 %d us (p50 %d): %.2f' % (s['n99'], s['n50'], i['n99'], i['n50'], r5)
    r6 = f['ops'] / max(s['ops'], 1)
    t6 = 'flood %d ops of 1 ms, spin %d: %.2f; the flood\'s pings %d, p50 %s us, lost %s' % (f['ops'], s['ops'], r6, f.get('nn') or 0, f.get('n50'), f.get('nlost'))
    if accel != 'kvm':
        say('SKIP L5 %s reason=%s: %s' % (boot, accel, t5))
        say('SKIP L6 %s reason=%s: %s' % (boot, accel, t6))
        return 0
    if r5 <= WAKE_BOUND:
        say('PASS L5 %s: %s; bound %.1f' % (boot, t5, WAKE_BOUND))
    else:
        say('FAIL L5 %s: %s; bound %.1f' % (boot, t5, WAKE_BOUND))
        fail = 1
    if r6 >= FLOOD_SHARE:
        say('PASS L6 %s: %s; bound %.2f' % (boot, t6, FLOOD_SHARE))
    else:
        say('FAIL L6 %s: %s; bound %.2f' % (boot, t6, FLOOD_SHARE))
        fail = 1
    return fail


def main(argv):
    if argv[:1] == ['--guard-loads']:
        m = int(argv[1])
        print(' '.join(['idle', 'spin', 'flood'] + guard(m) + [p for p, _ in pending(m)]))
        return 0
    accel = argv[argv.index('--accel') + 1]
    images = Path(argv[argv.index('--images') + 1])
    boots = [a for a in argv[argv.index('--com1') + 2:]]
    fail = 0
    for boot in boots:
        tier, leg, mib = boot.split('-')
        b = images / tier / boot
        if not b.exists():
            continue
        rep = (b / 'report.txt').read_text(errors='replace') if (b / 'report.txt').exists() else ''
        ser = (b / 'serial.log').read_text(errors='replace') if (b / 'serial.log').exists() else ''
        rows = parse(rep) or parse(ser)
        want = (b / 'pax-run').read_text().split()[7:] if (b / 'pax-run').exists() else []
        ended = 'latprobe: end' in rep or 'latprobe: end' in ser
        rc = (b / 'rc').read_text().strip() if (b / 'rc').exists() else '?'
        missing = [w for w in want if w not in rows]
        thin = [k for k, r in rows.items() if r['wn'] == 0 or r['ln'] == 0]
        instr = tier == 'linux' or (all(r['irq'] is not None for r in rows.values()) and rows)
        if missing or thin or not ended or not instr:
            say('FAIL L1 %s: lines %d of %d (missing %s), no samples %s, end line %s, instrument %s, exit %s'
                % (boot, len(rows), len(want), ' '.join(missing) or '-', ' '.join(thin) or '-', ended, 'on' if instr else 'off', rc))
            fail = 1
        else:
            say('PASS L1 %s: %d loads, each with samples, the end line%s (exit %s)'
                % (boot, len(rows), '' if tier == 'linux' else ', the instrument on', rc))
        base = rows.get('spin')
        todo = {p: why for p, why in pending(int(mib))}
        for g in ([] if tier == 'linux' else guard(int(mib)) + list(todo)):
            r = rows.get(g)
            if r is None or base is None:
                if g in want and g not in todo:
                    say('FAIL L2 %s %s: no line (or no spin baseline)' % (boot, g))
                    fail = 1
                continue
            parts = [('wake', r['wmax'], base['wmax']), ('lo', r['lmax'], base['lmax'])]
            if r['nmax'] is not None and base['nmax'] is not None:
                parts.append(('net', r['nmax'], base['nmax']))
            ratios = ['%s %d/%d us = %.2f' % (n, v, max(bv, 1), v / max(bv, 1)) for n, v, bv in parts]
            worst = max(v / max(bv, 1) for _, v, bv in parts)
            lost = r['llost'] + (r['nlost'] or 0)
            if g in todo:
                say('~L2 %s %s: %s; not bounded until %s' % (boot, g, ', '.join(ratios), todo[g]))
            elif accel != 'kvm':
                say('SKIP L2 %s %s reason=%s: %s' % (boot, g, accel, ', '.join(ratios)))
            elif worst <= BOUND and lost == 0:
                say('PASS L2 %s %s: %s; bound %.1f x spin' % (boot, g, ', '.join(ratios), BOUND))
            else:
                say('FAIL L2 %s %s: %s; lost %d; bound %.1f x spin (irqoff %s us, nr %s)'
                    % (boot, g, ', '.join(ratios), lost, BOUND, r['irq'], r['nr']))
                fail = 1
        fail |= clock_rows(boot, tier, int(mib), rows, want)
        fail |= wake_rows(boot, tier, accel, rows, want)
        for k, r in rows.items():
            say('~L3 %s %s: wake p50 %s p99 %s max %s; lo p50 %s max %s lost %s; net p50 %s max %s lost %s; ops %s max %s; '
                'irqoff %s vec 0x%s nr %s; schedgap %s; ticks %s of %s; sys %s; clocks mono %s real %s tsc %s'
                % (boot, k, r['w50'], r['w99'], r['wmax'], r['l50'], r['lmax'], r['llost'], r['n50'], r['nmax'], r['nlost'],
                   r['ops'], r['opmax'], r['irq'], r['vec'], r['nr'], r['gap'], r['td'], r['te'], r['sys'], r['mono'], r['real'], r['tsc']))
    return fail


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
