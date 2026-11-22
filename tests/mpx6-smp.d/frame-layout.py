#!/usr/bin/env python3
"""FRAME-LAYOUT: every byte offset into boot/isr.S's frame that the entry path reads by number agrees
with kernel/interrupts' `Frame` (its fields in order, eight bytes each), so a change to the frame
cannot move one of them silently.

  python3 -I tests/mpx6-smp.d/frame-layout.py [ROOT]        the check (ROOT the tree, default .)
  python3 -I tests/mpx6-smp.d/frame-layout.py --selftest    the check's own proof: the tree green,
                                                            each planted disagreement red

What is held to the `Frame`:
  - boot/isr.S, `pax_isr_common` and `pax_sysret`: each vector compare (`cmpq $0x100`, `$0x102`,
    `$0x103`, `$32`, `N(%rsp)`), each CS test (`testb $3`, `cmpq $0x23`), each RFLAGS test
    (`testq $0x200`, `$0x100`), the RIP compare (`cmpq %rcx`), and the vector the common path hands
    kernel/klock's `pax_klock_resumed` (the `movq N(%rsp), %rdi` before that call: the lock's
    release store is skipped for an NMI's frame by that word);
  - kernel/user's W_VECTOR and W_CS, kernel/sched's W_RAX, W_RIP, W_CS, W_RFLAGS, W_RSP, W_SS and
    FRAME_WORDS (word indexes: offset / 8, and the field count).
"""
import pathlib
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True


def frame_fields(src):
    m = re.search(r'^struct Frame \{\n(.*?)^\}', src, re.M | re.S)
    if not m:
        return None
    names = re.findall(r'^\s*(\w+):\s*u64,', m[1], re.M)
    return {n: 8 * i for i, n in enumerate(names)}, len(names)


def body(src, start, end):
    i = src.find(f'\n{start}:\n')
    j = src.find(end, i)
    return src[i:j] if i >= 0 and j > i else ''


def const(src, name):
    m = re.search(rf'^const {name}: u64 = (\d+)\b', src, re.M)
    return int(m[1]) if m else None


def check(root):
    root = pathlib.Path(root)
    why = []
    got = frame_fields((root / 'kernel/interrupts/interrupts.lu').read_text())
    if not got:
        return ['no `struct Frame` in kernel/interrupts/interrupts.lu']
    off, nfields = got
    isr = (root / 'boot/isr.S').read_text()
    code = body(isr, 'pax_isr_common', '.size pax_isr_common') + body(isr, 'pax_sysret', '.size pax_sysret')
    if not code:
        return ['no pax_isr_common or pax_sysret in boot/isr.S']
    rules = [(r'cmpq\s+\$(?:0x10[0-3]|32),\s*(\d+)\(%rsp\)', 'vector'),
             (r'testb\s+\$3,\s*(\d+)\(%rsp\)', 'cs'), (r'cmpq\s+\$0x23,\s*(\d+)\(%rsp\)', 'cs'),
             (r'testq\s+\$0x[12]00,\s*(\d+)\(%rsp\)', 'rflags'), (r'cmpq\s+%rcx,\s*(\d+)\(%rsp\)', 'rip')]
    seen = 0
    for pat, field in rules:
        for m in re.finditer(pat, code):
            seen += 1
            if int(m[1]) != off.get(field):
                why.append(f'boot/isr.S `{m[0]}` reads byte {m[1]}; the frame\'s {field} is at {off.get(field)}')
    if seen < 10:
        why.append(f'boot/isr.S: {seen} frame reads found, 10 or more expected (the patterns no longer match the code)')
    lines = code.split('\n')
    calls = [k for k, ln in enumerate(lines) if re.match(r'\s*call\s+pax_klock_resumed\b', ln)]
    if not calls:
        why.append('boot/isr.S: no `call pax_klock_resumed` in the common path')
    for k in calls:
        loads = [re.search(r'movq\s+(\d+)\(%rsp\),\s*%rdi', ln) for ln in lines[max(0, k - 5):k]]
        loads = [x for x in loads if x]
        if not loads:
            why.append('boot/isr.S: the vector handed to pax_klock_resumed is not read from the frame (`movq N(%rsp), %rdi`)')
        elif int(loads[-1][1]) != off.get('vector'):
            why.append(f'boot/isr.S hands pax_klock_resumed byte {loads[-1][1]}; the frame\'s vector is at {off.get("vector")}')
    words = [('kernel/user/user.lu', 'W_VECTOR', 'vector'), ('kernel/user/user.lu', 'W_CS', 'cs'),
             ('kernel/sched/sched.lu', 'W_RAX', 'rax'), ('kernel/sched/sched.lu', 'W_RIP', 'rip'),
             ('kernel/sched/sched.lu', 'W_CS', 'cs'), ('kernel/sched/sched.lu', 'W_RFLAGS', 'rflags'),
             ('kernel/sched/sched.lu', 'W_RSP', 'rsp'), ('kernel/sched/sched.lu', 'W_SS', 'ss')]
    for path, name, field in words:
        v = const((root / path).read_text(), name)
        if v is None or v * 8 != off.get(field):
            why.append(f'{path} {name} = {v}; the frame\'s {field} is word {None if off.get(field) is None else off[field] // 8}')
    fw = const((root / 'kernel/sched/sched.lu').read_text(), 'FRAME_WORDS')
    if fw != nfields:
        why.append(f'kernel/sched/sched.lu FRAME_WORDS = {fw}; the frame has {nfields} words')
    return why


def selftest(root):
    root = pathlib.Path(root)
    files = ['kernel/interrupts/interrupts.lu', 'boot/isr.S', 'kernel/user/user.lu', 'kernel/sched/sched.lu']
    plants = [('the tree as it is', None, None, None),
              ('a field before the vector', 'kernel/interrupts/interrupts.lu', '    rax: u64,\n    vector: u64,',
               '    rax: u64,\n    pad: u64,\n    vector: u64,'),
              ('the lock handed the error code', 'boot/isr.S', 'movq    120(%rsp), %rdi',
               'movq    128(%rsp), %rdi'),
              ('the lock handed the frame\'s address', 'boot/isr.S', 'movq    120(%rsp), %rdi',
               'movq    %rsp, %rdi'),
              ('a continuation compare off by a word', 'boot/isr.S', 'cmpq    $0x103, 120(%rsp)',
               'cmpq    $0x103, 112(%rsp)'),
              ('kernel/user\'s vector word moved', 'kernel/user/user.lu', 'const W_VECTOR: u64 = 15',
               'const W_VECTOR: u64 = 16')]
    bad = 0
    for name, path, old, new in plants:
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            for f in files:
                (td / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(root / f, td / f)
            if path:
                s = (td / path).read_text()
                if s.count(old) != 1:
                    print(f'FAIL FRAME-LAYOUT-SELFTEST {name}: the plant\'s text is not in {path} once')
                    bad += 1
                    continue
                (td / path).write_text(s.replace(old, new))
            why = check(td)
            want_red = path is not None
            if bool(why) != want_red:
                print(f'FAIL FRAME-LAYOUT-SELFTEST {name}: {"green" if not why else why}')
                bad += 1
            else:
                print(f'PASS FRAME-LAYOUT-SELFTEST {name}: {why[0] if why else "green"}')
    print(f'frame-layout-selftest: {len(plants) - bad} of {len(plants)} cases as expected')
    return bad == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    here = pathlib.Path(__file__).resolve().parents[2]
    if args and args[0] == '--selftest':
        sys.exit(0 if selftest(args[1] if len(args) > 1 else here) else 1)
    why = check(args[0] if args else '.')
    if why:
        print(f'FAIL FRAME-LAYOUT {why[0]}')
        for w in why[1:]:
            print(f'INFO FRAME-LAYOUT {w}')
        sys.exit(1)
    print('PASS FRAME-LAYOUT every frame offset boot/isr.S, kernel/user and kernel/sched read by number is the Frame\'s')
