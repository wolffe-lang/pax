#!/usr/bin/env python3
"""WAIT-CENSUS: every interruptible wait a process thread can enter in kernel/sched asks, once its state is set and
before it switches away, whether a signal that wakes it is already pending (`wake_if_signalled`), so a signal raised
while the thread was on its way to the wait from ring 3 on its own processor, with another holding the kernel lock,
cannot sleep with it: `poke` found that thread RUNNING and only reached it (a RESCHED its processor then takes after
the wait has begun), and the signal waited for whatever else ended the wait (tests/mpx6-smp's sleeper rounds, which
lost one to three of ten at 2, 4 and 16 processors until each wait asked).

  python3 -I tests/mpx6-smp.d/wait-census.py [ROOT]        the check (ROOT the tree, default .)
  python3 -I tests/mpx6-smp.d/wait-census.py --selftest    its own proof: the tree green, each planted wait red

What is held: in every kernel/*.lu file, each `put_field(<slot>, offset_of(Thread, state), <S>)` with S an
interruptible wait (SLEEPING, INPUT, PIPE, WAITING, FUTEX, SUSPEND) is followed, in the same function and before
its `run_next()`, by `wake_if_signalled(<slot>)`; kernel/sched defines `wake_if_signalled` and it asks
`signal_wakes`, the test `poke` applies. Exempt by name, each with its reason: kernel/sched's `sleep` (a kernel
thread's sleep: tgid 0, no signals).
"""
import pathlib
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WAITS = ('SLEEPING', 'INPUT', 'PIPE', 'WAITING', 'FUTEX', 'SUSPEND')
EXEMPT = {('sched', 'sleep'): "a kernel thread's sleep: tgid 0, no signals"}
WRITE = re.compile(r'put_field\((\w+), offset_of\(Thread, state\), (' + '|'.join(WAITS) + r')\)')
FN = re.compile(r'^(?:pub )?fn (\w+)\(', re.M)


def functions(src):
    """(name, start offset, end offset) of each top-level fn: from its line to the next top-level item."""
    starts = [(m[1], m.start()) for m in FN.finditer(src)]
    out = []
    for k, (name, a) in enumerate(starts):
        b = starts[k + 1][1] if k + 1 < len(starts) else len(src)
        out.append((name, a, b))
    return out


def check(root):
    root = pathlib.Path(root)
    why, seen = [], []
    for p in sorted((root / 'kernel').rglob('*.lu')):
        src = p.read_text()
        mod = p.parent.name if p.parent.name != 'kernel' else p.stem
        for name, a, b in functions(src):
            body = src[a:b]
            for m in WRITE.finditer(body):
                slot, state = m[1], m[2]
                where = f'{p.relative_to(root)} {name} ({state})'
                if (mod, name) in EXEMPT:
                    seen.append(f'{where} exempt: {EXEMPT[(mod, name)]}')
                    continue
                rest = body[m.end():]
                rn = rest.find('run_next()')
                ask = rest.find(f'wake_if_signalled({slot})')
                if ask < 0 or (rn >= 0 and ask > rn):
                    why.append(f'{where}: no wake_if_signalled({slot}) between the state write and run_next()')
                else:
                    seen.append(where)
    sched = (root / 'kernel/sched/sched.lu').read_text() if (root / 'kernel/sched/sched.lu').exists() else ''
    d = re.search(r'^fn wake_if_signalled\(.*?^\}', sched, re.M | re.S)
    if not d:
        why.append('kernel/sched defines no wake_if_signalled')
    elif 'signal_wakes(' not in d[0]:
        why.append("kernel/sched's wake_if_signalled does not ask signal_wakes")
    if not re.search(r'^fn signal_wakes\(', sched, re.M) or 'signal_wakes(' not in (re.search(r'^fn poke\(.*?^\}', sched, re.M | re.S) or [''])[0]:
        why.append("kernel/sched's poke does not ask signal_wakes (one test for both)")
    return why, seen


def main(argv):
    if argv[1:2] == ['--selftest']:
        return selftest()
    root = argv[1] if len(argv) > 1 else '.'
    why, seen = check(root)
    if why:
        for w in why:
            print(f'FAIL WAIT-CENSUS {w}')
        return 1
    waits = [s for s in seen if 'exempt' not in s]
    print(f'PASS WAIT-CENSUS {len(waits)} interruptible waits ask for a pending signal before they switch away: '
          + '; '.join(s.split(' ', 1)[1] for s in waits) + f' ({len(seen) - len(waits)} exempt)')
    return 0


def selftest():
    here = pathlib.Path(__file__).resolve().parent.parent.parent
    bad = 0
    cases = [
        ('the tree as it is', None, True),
        ('a ninth wait without the question',
         lambda s: s.replace('\nfn signal_wakes(', '\npub fn planted_wait(f: u64) -> u64 {\n    let c = cur()\n'
                             '    put_field(c, offset_of(Thread, state), WAITING)\n    run_next()\n}\n\nfn signal_wakes(', 1),
         False),
        ('a wait that asks after it has switched away',
         lambda s: s.replace('\nfn signal_wakes(', '\npub fn planted_late(f: u64) -> u64 {\n    let c = cur()\n'
                             '    put_field(c, offset_of(Thread, state), FUTEX)\n    let r = run_next()\n'
                             '    wake_if_signalled(c)\n    r\n}\n\nfn signal_wakes(', 1),
         False),
        ('wake_if_signalled that does not ask signal_wakes',
         lambda s: re.sub(r'(^fn wake_if_signalled\(.*?^\})', lambda m: m[1].replace('signal_wakes(', 'takes_any('), s,
                          count=1, flags=re.M | re.S),
         False),
    ]
    for name, plant, green in cases:
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            shutil.copytree(here / 'kernel', t / 'kernel')
            p = t / 'kernel/sched/sched.lu'
            if plant:
                s = p.read_text()
                s2 = plant(s)
                if s2 == s:
                    print(f'FAIL WAIT-CENSUS-SELFTEST {name}: the plant did not apply')
                    bad += 1
                    continue
                p.write_text(s2)
            why, _ = check(t)
            ok = (not why) == green
            print(f'{"PASS" if ok else "FAIL"} WAIT-CENSUS-SELFTEST {name}: {"green" if not why else why[0]}')
            bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
