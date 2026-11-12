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
#    and the network echo's worst round trip, each over the same boot's
#    `spin` (the CPU's hog with no system call), at most BOUND; under TCG
#    SKIPPED by name (TCG's timings are the emulator's first).
# L3 `~` lines: every load's figures (the measurement table's rows).
# Exit 0 when L1 and L2 held, 1 otherwise.
import re
import sys
from pathlib import Path

# The guarded loads: the worst of the measurement table that a user can
# cause at will (notes/px131-long-kernel-paths.md), each sized for the boot.
def guard(mib):
    return ['hole:1024', 'console:65536', 'fork:%d' % (mib // 8)]

BOUND = 3.0  # the worst beside a guarded load, over the worst beside `spin`

LINE = re.compile(r'^latprobe (\S+): wake n (\d+) p50 (\d+) p99 (\d+) max (\d+); lo n (\d+) p50 (\d+) max (\d+) lost (\d+); '
                  r'(?:net n (\d+) p50 (\d+) max (\d+) lost (\d+)|net -); ops (\d+) max (\d+); '
                  r'(?:irqoff (\d+) vector 0x([0-9a-f]+) nr (\d+); schedgap (\d+); ticks (\d+) of (\d+); sys (.*)|irqoff -.*)$')


def parse(text):
    out = {}
    for l in text.replace('\r', '').splitlines():
        m = LINE.match(l.strip())
        if not m:
            continue
        g = m.groups()
        num = lambda i: int(g[i]) if g[i] is not None else None
        out[g[0]] = dict(wn=num(1), w50=num(2), w99=num(3), wmax=num(4), ln=num(5), l50=num(6), lmax=num(7), llost=num(8),
                         nn=num(9), n50=num(10), nmax=num(11), nlost=num(12), ops=num(13), opmax=num(14),
                         irq=num(15), vec=g[16], nr=num(17), gap=num(18), td=num(19), te=num(20), sys=g[21])
    return out


def say(s):
    print('mpx6-latency: ' + s, flush=True)


def main(argv):
    if argv[:1] == ['--guard-loads']:
        print(' '.join(['idle', 'spin'] + guard(int(argv[1]))))
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
        instr = all(r['irq'] is not None for r in rows.values()) and rows
        if missing or thin or not ended or not instr:
            say('FAIL L1 %s: lines %d of %d (missing %s), no samples %s, end line %s, instrument %s, qemu-halt %s'
                % (boot, len(rows), len(want), ' '.join(missing) or '-', ' '.join(thin) or '-', ended, 'on' if instr else 'off', rc))
            fail = 1
        else:
            say('PASS L1 %s: %d loads, each with samples, the end line, the instrument on (qemu-halt %s)' % (boot, len(rows), rc))
        base = rows.get('spin')
        for g in guard(int(mib)):
            r = rows.get(g)
            if r is None or base is None:
                if g in want:
                    say('FAIL L2 %s %s: no line (or no spin baseline)' % (boot, g))
                    fail = 1
                continue
            parts = [('wake', r['wmax'], base['wmax']), ('lo', r['lmax'], base['lmax'])]
            if r['nmax'] is not None and base['nmax'] is not None:
                parts.append(('net', r['nmax'], base['nmax']))
            ratios = ['%s %d/%d us = %.2f' % (n, v, max(bv, 1), v / max(bv, 1)) for n, v, bv in parts]
            worst = max(v / max(bv, 1) for _, v, bv in parts)
            lost = r['llost'] + (r['nlost'] or 0)
            if accel != 'kvm':
                say('SKIP L2 %s %s reason=%s: %s' % (boot, g, accel, ', '.join(ratios)))
            elif worst <= BOUND and lost == 0:
                say('PASS L2 %s %s: %s; bound %.1f x spin' % (boot, g, ', '.join(ratios), BOUND))
            else:
                say('FAIL L2 %s %s: %s; lost %d; bound %.1f x spin (irqoff %s us, nr %s)'
                    % (boot, g, ', '.join(ratios), lost, BOUND, r['irq'], r['nr']))
                fail = 1
        for k, r in rows.items():
            say('~L3 %s %s: wake p50 %s p99 %s max %s; lo p50 %s max %s lost %s; net p50 %s max %s lost %s; ops %s max %s; '
                'irqoff %s vec 0x%s nr %s; schedgap %s; ticks %s of %s; sys %s'
                % (boot, k, r['w50'], r['w99'], r['wmax'], r['l50'], r['lmax'], r['llost'], r['n50'], r['nmax'], r['nlost'],
                   r['ops'], r['opmax'], r['irq'], r['vec'], r['nr'], r['gap'], r['td'], r['te'], r['sys']))
    return fail


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
