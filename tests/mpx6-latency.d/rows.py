#!/usr/bin/env python3
# rows.py — tests/mpx6-latency's rows (px131), from each boot's report
# (the probe's lines as the host's echo collected them, else the serial
# log).
#
#   rows.py --guard-loads MIB            the guard's run list for a boot of MIB MiB
#   rows.py --l6-again --images DIR BOOT...   the boots whose every L6 hold so far is unmeasured
#   rows.py --accel A --images DIR --com1 0|1 BOOT...   the rows (BOOT is tier-firmware-mib)
#
# L1 every load's line, with samples; the end line; the instrument on.
# L2 each GUARD load: the sleeper's worst lateness, the loopback echo's
#    and the host's network echo's worst round trip, each over the same boot's
#    `spin` (the CPU's hog with no system call), at most BOUND; the host's
#    ping may also be spin's worst plus NET_SLACK_US (decision 1's 10 ms:
#    since device wake-ups run at once, spin's worst ping is a few
#    milliseconds, and three times that is within a host's own stall), with
#    the instrument's longest interrupts-off stretch printed beside it; under TCG
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
# L6 a hog under a ping flood offered at FLOOD_RATE datagrams a second
#    (`flood:R`, echo-host.py paces it): its ops (1 ms of CPU each) at least
#    FLOOD_SHARE of `spin`'s (device wake-ups that run at once must not
#    starve a CPU-bound process), the offered and answered rates printed. A
#    host that offered under OFFER_MIN of the rate is `unmeasured`, neither
#    a pass nor a failure: tests/mpx6-latency holds that boot's L6 again, a
#    fresh boot of `spin` and the paced flood, at most HOLDS holds in all; a
#    measured result is final at once; HOLDS unmeasured holds are
#    `FAIL L6-unmeasured`, a red under its own name. Under TCG SKIPPED by name.
# ~L6 the saturating flood (`flood`: as fast as the guest answers, 16 in
#    flight): its answered rate, the hog's share and the sleeper's worst,
#    bounded by nothing (the rate is the host's: its CPUs set it), so every
#    record carries the curve, on both tiers.
# L3 `~` lines: every load's figures (the measurement table's rows).
# Exit 0 when L1, L2, L4, L5 and L6 held; 3 when the only red is
# L6-unmeasured; 1 otherwise.
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
NET_SLACK_US = 10000  # L2: the host's ping may be spin's worst plus 10 ms (decision 1's bound for anything)

# L4's loads (long calls with interrupts off at this head: the clocks must
# keep the counter's time across them) and its bound: a clock's elapsed
# time within 2 % of the counter's over a window of SECONDS (a tick is 0.3 %
# of 3 s).
def clocked(mib):
    return ['console:65536', 'write:%d' % (mib // 16)]

CLOCK_BOUND = 0.02
WAKE_BOUND = 3.0   # L5: the ping's p99 beside `spin`, over its p99 at `idle`
FLOOD_SHARE = 0.5  # L6: the paced flood's ops over `spin`'s
# L6's offered rate (decision 21): every take so far delivered at least
# 8,300 answered pings a second to its saturating flood, the slowest a light
# slot of two CPUs beside heavy jobs; half of that, so any slot offers it
# with room. The native kernel's hog keeps about 0.95 of its share there.
FLOOD_RATE = 4000
OFFER_MIN = 0.9  # L6: below this share of FLOOD_RATE offered, the rig did not deliver it: unmeasured
HOLDS = 3        # L6: holds at most, while unmeasured


def guard_loads(mib):
    """The guard's run list: idle, spin, the paced and the saturating
    floods, the guarded and the pending loads."""
    return ['idle', 'spin', 'flood:%d' % FLOOD_RATE, 'flood'] + guard(mib) + [p for p, _ in pending(mib)]

LINE = re.compile(r'^latprobe (\S+): wake n (\d+) p50 (\d+) p99 (\d+) max (\d+); lo n (\d+) p50 (\d+) max (\d+) lost (\d+); '
                  r'(?:net n (\d+) p50 (\d+) max (\d+) lost (\d+)|net -); ops (\d+) max (\d+); '
                  r'(?:irqoff (\d+) vector 0x([0-9a-f]+) nr (\d+); schedgap (\d+); ticks (\d+) of (\d+); sys (.*)|irqoff -.*)$')


HOST = re.compile(r'^hostnet (\S+): n (\d+) p50 (\d+) p99 (\d+) max (\d+) lost (\d+)(?: sent (\d+) secs ([0-9.]+))?$')
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
            g = h.groups()
            host[g[0]] = [int(x) for x in g[1:6]] + [int(g[6]) if g[6] else None, float(g[7]) if g[7] else None]
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
                         mono=int(c.group(1)) if c else None, real=int(c.group(2)) if c else None, tsc=int(c.group(3)) if c else None,
                         sent=None, secs=None)
    for k, (n, p50, p99, mx, lost, sent, secs) in host.items():
        if k in out:
            out[k].update(nn=n, n50=p50, n99=p99, nmax=mx, nlost=lost, sent=sent, secs=secs)
    return out


def say(s):
    print('mpx6-latency: ' + s, flush=True)


def l2_parts(r, base):
    """L2's columns for a load against the same boot's `spin`: (name, the
    worst beside the load, spin's, the limit). The sleeper and the loopback
    echo: BOUND times spin's. The host's ping: the larger of BOUND times
    spin's and spin's plus NET_SLACK_US (decision 22)."""
    parts = [('wake', r['wmax'], base['wmax'], BOUND * max(base['wmax'], 1)),
             ('lo', r['lmax'], base['lmax'], BOUND * max(base['lmax'], 1))]
    if r['nmax'] is not None and base['nmax'] is not None:
        parts.append(('net', r['nmax'], base['nmax'], max(BOUND * max(base['nmax'], 1), base['nmax'] + NET_SLACK_US)))
    return parts


def l2_holds(parts):
    return all(v <= limit for _, v, _, limit in parts)


def l2_text(parts):
    out = []
    for n, v, bv, limit in parts:
        t = '%s %d/%d us = %.2f' % (n, v, max(bv, 1), v / max(bv, 1))
        if n == 'net':
            t += ' (limit %d us)' % limit
        out.append(t)
    return ', '.join(out)


def l6_verdict(spin, fl):
    """L6 at the paced flood: ('pass' | 'fail' | 'unmeasured', its text)."""
    share = fl['ops'] / max(spin['ops'], 1)
    secs, sent = fl.get('secs'), fl.get('sent')
    if not secs or sent is None:
        return 'unmeasured', 'flood:%d %d ops of 1 ms, spin %d: %.2f; the host counted no offered datagrams' % (
            FLOOD_RATE, fl['ops'], spin['ops'], share)
    offered, answered = sent / secs, (fl.get('nn') or 0) / secs
    text = 'flood:%d %d ops of 1 ms, spin %d: %.2f; offered %.0f a second, answered %.0f, lost %s, p50 %s us' % (
        FLOOD_RATE, fl['ops'], spin['ops'], share, offered, answered, fl.get('nlost'), fl.get('n50'))
    if offered < OFFER_MIN * FLOOD_RATE:
        return 'unmeasured', text + '; the host offered under %.0f %% of %d a second' % (OFFER_MIN * 100, FLOOD_RATE)
    return ('pass' if share >= FLOOD_SHARE else 'fail'), text


def l6_holds(boot, results):
    """L6 over a boot's holds in order, each l6_verdict's (state, text):
    the first measured one decides; each unmeasured hold before it is a
    NOTE; HOLDS unmeasured holds are FAIL L6-unmeasured. Returns (the
    verdict, the lines to say)."""
    lines = []
    for i, (state, text) in enumerate(results):
        hold = i + 1
        if state == 'unmeasured':
            lines.append('NOTE L6 %s: unmeasured, hold %d of %d: %s%s'
                         % (boot, hold, HOLDS, text, '; held again, a fresh boot' if hold < HOLDS else ''))
            continue
        lines.append('%s L6 %s: %s; bound %.2f%s' % ('PASS' if state == 'pass' else 'FAIL', boot, text, FLOOD_SHARE,
                                                    ' (hold %d of %d)' % (hold, HOLDS) if hold > 1 else ''))
        return state, lines
    lines.append('FAIL L6-unmeasured %s: the host offered under %.0f %% of %d datagrams a second in %d of %d holds'
                 % (boot, OFFER_MIN * 100, FLOOD_RATE, len(results), HOLDS))
    return 'unmeasured', lines


def l6_again(results):
    """Hold L6 again: every hold so far unmeasured, and fewer than HOLDS."""
    return 0 < len(results) < HOLDS and all(state == 'unmeasured' for state, _ in results)


def flood_curve(boot, spin, fl):
    """~L6: the saturating flood's figures, bounded by nothing."""
    secs = fl.get('secs')
    rate = '%.0f a second (offered %.0f)' % ((fl.get('nn') or 0) / secs, (fl.get('sent') or 0) / secs) if secs else '-'
    return ('~L6 %s flood: answered %s, the hog %.2f of spin\'s ops (%d of %d), the sleeper\'s worst %d us, lost %s; '
            'bounded by nothing (the saturating flood: the host sets its rate)'
            % (boot, rate, fl['ops'] / max(spin['ops'], 1), fl['ops'], spin['ops'], fl['wmax'], fl.get('nlost')))


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


def l6_results(images, tier, boot):
    """The paced flood's verdicts over a boot's holds (its directory, then
    BOOT-hold2, BOOT-hold3), each against the same hold's `spin`."""
    out = []
    for hold in range(1, HOLDS + 1):
        b = images / tier / (boot if hold == 1 else '%s-hold%d' % (boot, hold))
        if not b.exists():
            break
        rep = (b / 'report.txt').read_text(errors='replace') if (b / 'report.txt').exists() else ''
        ser = (b / 'serial.log').read_text(errors='replace') if (b / 'serial.log').exists() else ''
        rows = parse(rep) or parse(ser)
        s, f = rows.get('spin'), rows.get('flood:%d' % FLOOD_RATE)
        out.append(l6_verdict(s, f) if s and f else ('unmeasured', 'no spin or flood:%d line in hold %d' % (FLOOD_RATE, hold)))
    return out


def wake_rows(boot, tier, accel, rows, want, images):
    """L5: the host's ping beside `spin` against `idle`; L6: the paced flood
    against `spin`, over its holds; ~L6: the saturating flood. Returns
    (fail, unmeasured)."""
    fail = 0
    paced = 'flood:%d' % FLOOD_RATE
    s = rows.get('spin')
    if tier != 'linux' and s and rows.get('flood'):
        say(flood_curve(boot, s, rows['flood']))
    if tier == 'linux' or paced not in want:
        return 0, 0
    i = rows.get('idle')
    if not (i and s and rows.get(paced)) or i.get('n99') is None or s.get('n99') is None:
        say('FAIL L5 %s: no idle, spin or %s line with the host\'s pings' % (boot, paced))
        return 1, 0
    r5 = s['n99'] / max(i['n99'], 1)
    t5 = 'the ping beside spin p99 %d us (p50 %d), at idle p99 %d us (p50 %d): %.2f' % (s['n99'], s['n50'], i['n99'], i['n50'], r5)
    if accel != 'kvm':
        say('SKIP L5 %s reason=%s: %s' % (boot, accel, t5))
        say('SKIP L6 %s reason=%s: %s' % (boot, accel, l6_verdict(s, rows[paced])[1]))
        return 0, 0
    if r5 <= WAKE_BOUND:
        say('PASS L5 %s: %s; bound %.1f' % (boot, t5, WAKE_BOUND))
    else:
        say('FAIL L5 %s: %s; bound %.1f' % (boot, t5, WAKE_BOUND))
        fail = 1
    verdict, lines = l6_holds(boot, l6_results(images, tier, boot))
    for line in lines:
        say(line)
    return fail | (verdict == 'fail'), int(verdict == 'unmeasured')


def main(argv):
    if argv[:1] == ['--guard-loads']:
        print(' '.join(guard_loads(int(argv[1]))))
        return 0
    if argv[:1] == ['--l6-again']:
        images = Path(argv[argv.index('--images') + 1])
        for boot in argv[argv.index('--images') + 2:]:
            tier = boot.split('-')[0]
            if tier != 'linux' and (images / tier / boot).exists() and l6_again(l6_results(images, tier, boot)):
                print(boot)
        return 0
    accel = argv[argv.index('--accel') + 1]
    images = Path(argv[argv.index('--images') + 1])
    boots = [a for a in argv[argv.index('--com1') + 2:]]
    fail = unmeasured = 0
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
            parts = l2_parts(r, base)
            ratios = l2_text(parts)
            lost = r['llost'] + (r['nlost'] or 0)
            bound = 'bound %.1f x spin, net max(%.1f x spin, spin + %d ms); irqoff %s us, nr %s' % (
                BOUND, BOUND, NET_SLACK_US // 1000, r['irq'], r['nr'])
            if g in todo:
                say('~L2 %s %s: %s; not bounded until %s' % (boot, g, ratios, todo[g]))
            elif accel != 'kvm':
                say('SKIP L2 %s %s reason=%s: %s' % (boot, g, accel, ratios))
            elif l2_holds(parts) and lost == 0:
                say('PASS L2 %s %s: %s; %s' % (boot, g, ratios, bound))
            else:
                say('FAIL L2 %s %s: %s; lost %d; %s' % (boot, g, ratios, lost, bound))
                fail = 1
        fail |= clock_rows(boot, tier, int(mib), rows, want)
        f, u = wake_rows(boot, tier, accel, rows, want, images)
        fail |= f
        unmeasured |= u
        for k, r in rows.items():
            say('~L3 %s %s: wake p50 %s p99 %s max %s; lo p50 %s max %s lost %s; net p50 %s max %s lost %s; ops %s max %s; '
                'irqoff %s vec 0x%s nr %s; schedgap %s; ticks %s of %s; sys %s; clocks mono %s real %s tsc %s'
                % (boot, k, r['w50'], r['w99'], r['wmax'], r['l50'], r['lmax'], r['llost'], r['n50'], r['nmax'], r['nlost'],
                   r['ops'], r['opmax'], r['irq'], r['vec'], r['nr'], r['gap'], r['td'], r['te'], r['sys'], r['mono'], r['real'], r['tsc']))
    return 1 if fail else (3 if unmeasured else 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
