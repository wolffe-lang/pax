#!/usr/bin/env python3
# tests/mpx6-smp.d/ledger-patch.py — the kernel lock's ledger lives in the test build alone (px166, stage 3). The
# shipped kernel's sources name no ledger; the test build (tools/build-kernel --test-words) applies
# tests/mpx6-smp.d/ledger.patch to its own copy of kernel/ (its hooks at each fresh take and release of the kernel
# lock, and /proc/pax-klock), beside tests/mpx6-smp.d/testwords.lu in kernel/testwords' place. Two rows:
#   LEDGER-PATCH      the patch touches kernel/interrupts, kernel/klock and kernel/procfs alone; every line it adds is
#                     one of the ledger's forms (a comment, `use testwords`, a `testwords.ledger_*` call, /proc/pax-klock's
#                     entry), and every line it removes comes back with `|| e == PAXKLOCK` added or as procfs's entry count
#                     one higher; and it applies to the checkout's kernel/ with its context exact (git apply). So the
#                     test build adds no lock, no interrupt mask and no other path, and a kernel change under one of its
#                     hunks is red here before any build.
#   KERNEL-NO-LEDGER  kernel/ and boot/ name no ledger (`ledger_`, `klock-ledger`, `pax-klock`, `PAXKLOCK`): the shipped
#                     kernel is built from them as they are.
#   ledger-patch.py ROOT        the rows for a checkout (exit 1 if either is red)
#   ledger-patch.py --selftest  each row red and green on synthetic trees
import os, pathlib, re, shutil, subprocess, sys, tempfile

FILES = ('kernel/interrupts/interrupts.lu', 'kernel/klock/klock.lu', 'kernel/procfs/procfs.lu')
FORMS = [
    r'',
    r'//.*',
    r'use testwords',
    r'(let \w+ = |n = )?testwords\.ledger_(now|took|gave|text)\((unsafe \{ f as u64 \}, \w+|base)?\)( //.*)?',
    r'pub const PAXKLOCK: u64 = \d+',
    r'const G_PAXKLOCK: u64 = \d+( //.*)?',
    r'if e == PAXKLOCK \{ return ("pax-klock"|G_PAXKLOCK) \}( //.*)?',
    r'\} else if g == G_PAXKLOCK \{',
]
NAMES = re.compile(r'ledger_|klock-ledger|pax-klock|PAXKLOCK')


def hunks(text):
    # the patch's files (from `+++ b/` lines) and its hunks as (file, [(kind, line)])
    files, out, cur, f = [], [], None, None
    for ln in text.splitlines():
        if ln.startswith('+++ '):
            f = ln[4:].split('\t')[0]
            f = f[2:] if f.startswith('b/') else f
            files.append(f)
            cur = None
        elif ln.startswith('--- ') or ln.startswith('diff ') or ln.startswith('index '):
            cur = None
        elif ln.startswith('@@'):
            cur = (f, [])
            out.append(cur)
        elif cur is not None and ln[:1] in (' ', '+', '-'):
            cur[1].append((ln[:1], ln[1:]))
    return files, out


def bump(r, a):
    m, n = re.fullmatch(r'pub const (ENTRIES|NONE): u64 = (\d+)', r.strip()), re.fullmatch(r'pub const (ENTRIES|NONE): u64 = (\d+)', a.strip())
    return bool(m and n and m[1] == n[1] and int(n[2]) == int(m[2]) + 1)


def check_patch(root):
    p = pathlib.Path(root) / 'tests/mpx6-smp.d/ledger.patch'
    if not p.exists():
        return ['no tests/mpx6-smp.d/ledger.patch']
    files, hs = hunks(p.read_text())
    why = []
    if sorted(set(files)) != sorted(FILES):
        why.append(f'it touches {sorted(set(files))}, want {sorted(FILES)}')
    for f, lines in hs:
        removed = [l for k, l in lines if k == '-']
        added = [l for k, l in lines if k == '+']
        paired = set()
        for r in removed:
            m = next((i for i, a in enumerate(added) if i not in paired and
                      (a.replace(' || e == PAXKLOCK', '') == r and a != r or bump(r, a))), None)
            if m is None:
                why.append(f'{f}: a removed line not given back: {r.strip()[:80]!r}')
            else:
                paired.add(m)
        for i, a in enumerate(added):
            if i in paired:
                continue
            if not any(re.fullmatch(form, a.strip()) for form in FORMS):
                why.append(f'{f}: an added line not of the ledger\'s forms: {a.strip()[:80]!r}')
    with tempfile.TemporaryDirectory() as td:
        t = pathlib.Path(td) / 'copy'
        for f in FILES:
            src = pathlib.Path(root) / f
            if src.exists():
                (t / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, t / f)
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=td)
        r = subprocess.run(['git', 'apply', '--check', str(p.resolve())], cwd=t, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            why.append('it does not apply to kernel/ as it is: ' + ' '.join(r.stderr.split())[:160])
    return why


def check_kernel(root):
    hits = []
    for d, pat in (('kernel', '*.lu'), ('boot', '*.S')):
        for f in sorted((pathlib.Path(root) / d).rglob(pat)):
            for i, ln in enumerate(f.read_text(errors='replace').splitlines(), 1):
                if NAMES.search(ln):
                    hits.append(f'{f.relative_to(root)}:{i}')
    return hits


def rows(root):
    rc = 0
    why = check_patch(root)
    if why:
        print(f'FAIL LEDGER-PATCH: {"; ".join(why[:3])}' + (f' (and {len(why) - 3} more)' if len(why) > 3 else ''))
        rc = 1
    else:
        print('PASS LEDGER-PATCH: tests/mpx6-smp.d/ledger.patch touches kernel/interrupts, kernel/klock and kernel/procfs '
              'alone, adds only the ledger\'s forms, and applies to kernel/ as it is')
    hits = check_kernel(root)
    if hits:
        print(f'FAIL KERNEL-NO-LEDGER: kernel/ or boot/ names the ledger at {hits[:4]}' + (f' and {len(hits) - 4} more' if len(hits) > 4 else ''))
        rc = 1
    else:
        print('PASS KERNEL-NO-LEDGER: kernel/ and boot/ name no ledger; the shipped kernel is built without one')
    return rc


# --- the self-test -------------------------------------------------------------------------------------------------
BASE = {
    'kernel/interrupts/interrupts.lu': 'fn pax_interrupt(f: *Frame) -> *Frame {\n    let fresh = klock.enter()\n    if fresh {\n'
                                       '        sched.ambient_resume()\n    }\n    f\n}\n',
    'kernel/klock/klock.lu': 'use percpu\n\npub fn leave() {\n    depth_down()\n    release()\n}\n',
    'kernel/procfs/procfs.lu': 'pub const ENTRIES: u64 = 69\npub const NONE: u64 = 69\n\npub fn fixed(e: u64) -> bool {\n'
                               '    e < PIDDIR || e == CMDLINE\n}\n\npub fn name(e: u64) -> str {\n    if e == CMDLINE { return "cmdline" }\n    ""\n}\n',
    'kernel/sched/sched.lu': 'pub fn run_next() {\n    switch()\n}\n',
    'kernel/sync/sync.lu': 'extern "c" fn pax_pause()\n\npub fn acquire(lock: u64) -> u64 {\n    let saved = irq_save()\n'
                           '    spin(lock)\n    saved\n}\n\npub fn release(lock: u64, saved: u64) {\n    store(lock)\n'
                           '    irq_restore(saved)\n}\n',
}
HOOKED = {
    'kernel/interrupts/interrupts.lu': 'fn pax_interrupt(f: *Frame) -> *Frame {\n    // the ledger: the TSC before the take\n'
                                       '    let t0 = testwords.ledger_now()\n    let fresh = klock.enter()\n    if fresh {\n'
                                       '        // # Safety: the frame\'s address.\n        testwords.ledger_took(unsafe { f as u64 }, t0)\n'
                                       '        sched.ambient_resume()\n    }\n    f\n}\n',
    'kernel/klock/klock.lu': 'use percpu\nuse testwords\n\npub fn leave() {\n    depth_down()\n    testwords.ledger_gave()\n    release()\n}\n',
    'kernel/procfs/procfs.lu': 'pub const ENTRIES: u64 = 70\npub const NONE: u64 = 70\npub const PAXKLOCK: u64 = 69\n\npub fn fixed(e: u64) -> bool {\n'
                               '    e < PIDDIR || e == CMDLINE || e == PAXKLOCK\n}\n\npub fn name(e: u64) -> str {\n    if e == CMDLINE { return "cmdline" }\n'
                               '    if e == PAXKLOCK { return "pax-klock" }\n    ""\n}\n',
    # px166 (stage 3a, unit 1): kernel/sync's hooks into the test build's lockled
    'kernel/sync/sync.lu': '// lockled: each word\'s acquisitions and ranks\nuse lockled\n\nextern "c" fn pax_pause()\n\n'
                           'pub fn acquire(lock: u64) -> u64 {\n    let saved = irq_save()\n    let t0 = lockled.now()\n'
                           '    spin(lock)\n    lockled.took(lock, t0)\n    saved\n}\n\npub fn release(lock: u64, saved: u64) {\n'
                           '    lockled.gave(lock)\n    store(lock)\n    irq_restore(saved)\n}\n',
}


def make(td, base, hooked, kernel=None):
    # ROOT with kernel/ as `kernel` (base unless given) and the patch from `base` to `hooked`
    root = pathlib.Path(td) / 'root'
    a, b = pathlib.Path(td) / 'a', pathlib.Path(td) / 'b'
    for d in (root, a, b):
        shutil.rmtree(d, ignore_errors=True)
    for f, s in (kernel or base).items():
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_text(s)
    for d, files in ((a, base), (b, {**base, **hooked})):
        for f, s in files.items():
            (d / f).parent.mkdir(parents=True, exist_ok=True)
            (d / f).write_text(s)
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=td)
    r = subprocess.run(['git', 'diff', '--no-index', '--no-prefix', 'a', 'b'], cwd=td, env=env, capture_output=True, text=True)
    # with --no-prefix, the directories a and b give the patch the paths a/kernel/... and b/kernel/..., as `git diff`
    # writes them in a checkout
    patch = r.stdout
    (root / 'tests/mpx6-smp.d').mkdir(parents=True, exist_ok=True)
    (root / 'tests/mpx6-smp.d/ledger.patch').write_text(patch)
    return root


def selftest():
    cases = []
    with tempfile.TemporaryDirectory() as td:
        def run(name, base, hooked, want_patch, want_kernel, kernel=None, drop_patch=False, says=None):
            root = make(td, base, hooked, kernel)
            if drop_patch:
                (root / 'tests/mpx6-smp.d/ledger.patch').unlink()
            wp, wk = check_patch(root), check_kernel(root)
            ok = (not wp) == want_patch and (not wk) == want_kernel and (says is None or any(re.search(says, w) for w in wp + wk))
            cases.append(ok)
            print(f'{"PASS" if ok else "FAIL"} LEDGER-PATCH-SELFTEST {name}: patch {"green" if not wp else "red"}, kernel '
                  f'{"green" if not wk else "red"}' + ('' if ok else f'; {wp[:2]} {wk[:2]}'))
        run('the ledger as a patch on a clean kernel: both green', BASE, HOOKED, True, True)
        run('the patch reaches kernel/sched too: red', BASE, {**HOOKED, 'kernel/sched/sched.lu': 'pub fn run_next() {\n    testwords.ledger_gave()\n    switch()\n}\n'},
            False, True, says=r'it touches')
        run('the patch takes the lock itself: red', BASE, {**HOOKED, 'kernel/klock/klock.lu': HOOKED['kernel/klock/klock.lu'].replace(
            '    testwords.ledger_gave()\n', '    testwords.ledger_gave()\n    klock.enter()\n')}, False, True, says=r"not of the ledger's forms")
        run('the patch masks interrupts: red', BASE, {**HOOKED, 'kernel/interrupts/interrupts.lu': HOOKED['kernel/interrupts/interrupts.lu'].replace(
            '    let t0 = testwords.ledger_now()\n', '    let t0 = testwords.ledger_now()\n    pax_cli()\n')}, False, True, says=r"not of the ledger's forms")
        run('the patch drops a kernel line: red', BASE, {**HOOKED, 'kernel/klock/klock.lu': HOOKED['kernel/klock/klock.lu'].replace('    depth_down()\n', '')},
            False, True, says=r'a removed line not given back')
        run('kernel/klock changed under a hunk: red before any build', BASE, HOOKED, False, True,
            kernel={**BASE, 'kernel/klock/klock.lu': BASE['kernel/klock/klock.lu'].replace('    depth_down()\n', '    depth_down_now()\n')},
            says=r'does not apply')
        run('no patch: red', BASE, HOOKED, False, True, drop_patch=True, says=r'no tests/mpx6-smp\.d/ledger\.patch')
        run('kernel/ still calls the ledger: red', BASE, HOOKED, False, False,
            kernel={**BASE, 'kernel/klock/klock.lu': HOOKED['kernel/klock/klock.lu']}, says=r'kernel/klock/klock\.lu:\d')
        run('kernel/ names /proc/pax-klock elsewhere: red', BASE, HOOKED, True, False,
            kernel={**BASE, 'kernel/sched/sched.lu': 'pub fn run_next() {\n    switch() // pax-klock\n}\n'},
            says=r'kernel/sched/sched\.lu:2')
        # px166 (stage 3a, unit 1): kernel/sync's hooks, and the names of the lock ranks
        run('the patch takes a second lock in kernel/sync: red', BASE, {**HOOKED, 'kernel/sync/sync.lu': HOOKED['kernel/sync/sync.lu'].replace(
            '    lockled.took(lock, t0)\n', '    lockled.took(lock, t0)\n    spin(lock + 8)\n')}, False, True, says=r"not of the ledger's forms")
        run('the patch masks interrupts in kernel/sync: red', BASE, {**HOOKED, 'kernel/sync/sync.lu': HOOKED['kernel/sync/sync.lu'].replace(
            '    lockled.gave(lock)\n', '    lockled.gave(lock)\n    pax_cli()\n')}, False, True, says=r"not of the ledger's forms")
        run('the patch moves the release store: red', BASE, {**HOOKED, 'kernel/sync/sync.lu': HOOKED['kernel/sync/sync.lu'].replace(
            '    store(lock)\n    irq_restore(saved)\n', '    irq_restore(saved)\n')}, False, True, says=r'a removed line not given back')
        for word in ('lockled', 'smpdebug', 'rankflip', 'LOCK-RANK'):
            run(f'kernel/ names {word}: red', BASE, HOOKED, True, False,
                kernel={**BASE, 'kernel/sched/sched.lu': f'pub fn run_next() {{\n    switch() // {word}\n}}\n'},
                says=r'kernel/sched/sched\.lu:2')
    bad = cases.count(False)
    print(f'ledger-patch-selftest: {len(cases) - bad} of {len(cases)} as wanted')
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        sys.exit(selftest())
    if len(sys.argv) != 2:
        sys.exit('usage: ledger-patch.py ROOT | --selftest')
    sys.exit(rows(sys.argv[1]))
