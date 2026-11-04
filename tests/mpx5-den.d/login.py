#!/usr/bin/env python3
"""px98: den at the console as a user who logged in, and the terminal that login gives.

    login.py text PREPARE.lu > pax-login
    login.py run ISO HOME.img LOG FIRMWARE [OVMF_CODE]

`text` prints the installed system's console login, the very text
`pax-install` writes as /etc/pax-login (user/install/prepare.lu's
`installed_login`, its string literals joined and unescaped), so the image
boots the login an install has, not a copy of it.

`run` boots ISO (kmain_console with tests/mpx5-den's login archive: its
/etc/pax-run runs four logins in turn) with HOME.img as its ext2 /home, under
FIRMWARE, and types at each `login:` and at each prompt on COM1, waiting for
every prompt before the next line, as tests/mpx6-install.d/den.py does. Nothing
the user types is redirected: den writes to the terminal. QEMU's monitor ends the
machine after the kernel's `halt` line (no host signal). Then the rows, on the
serial log as tools/lib.sh's serial_norm leaves it:

  L1 the terminal is the account's: in run 1 (the installed login, `pax`)
     `stat -L` of /dev/stdin says `1000 1000 600`; its owner may chmod it
     (`620`, then back), and may not chown it to root (-EPERM: `Operation not
     permitted`, status 1);
  L2 the standard streams by name: `echo > /dev/stdout` and `> /dev/stderr`
     print, status 0, and no line in run 1 says `Permission denied`;
  L3 den at the terminal, in a fresh directory under /tmp (the archive's tree)
     and under the home directory (the ext2 disk): init, status, add, commit,
     log --no-decorate, status, each status 0; no `fatal: denied`; status says
     `On branch main` four times and log prints both commits' subjects;
  L4 the hand-back: run 2 (the installed login, `root`) finds the terminal
     `0 0 600`, root's den status in the user's repository status 0, and
     /dev/tty still fixed (root's chown of it `Read-only file system`);
     run 3 (the installed login, `pax`) has it `1000 1000 600` again and run 4
     (the live medium's login, root only) `0 0 600`;
  L5 the end: no -ENOSYS from den but set_robust_list (273) and rseq (334);
     no `refused:` line; `PAX: init /bin/pelt ended with status 0; nothing
     left to run`; no panic; the `halt` line.

Prints PASS lines; a failed row is `FAIL <row> <firmware>: …`. Exit 0, 1 on a
failed row, 2 on a usage error.
"""
from pathlib import Path
import os
import re
import socket
import subprocess
import sys
import threading
import time


def login_text(prepare):
    src = Path(prepare).read_text(encoding='utf-8')
    i = src.index('fn installed_login() -> str {')
    j = src.index('\n}\n', i)
    out = []
    for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', src[i:j]):
        out.append(re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}[m.group(1)], lit))
    return ''.join(out)


# Each login: the account typed at `login:`, then the lines typed at its prompts.
USER_A = [
    'echo PX98-RUN1-BEGIN',
    'id',
    "stat -L -c 'PX98-TERM %u %g %a' /dev/stdin",
    "chmod 620 /dev/stdin; stat -L -c 'PX98-CHMOD %u %g %a' /dev/stdin; chmod 600 /dev/stdin",
    'chown 0 /dev/stdin; echo PX98-CHOWN-USER=$?',
    'echo PX98-OUT > /dev/stdout; echo PX98-STDOUT=$?',
    'echo PX98-ERR > /dev/stderr; echo PX98-STDERR=$?',
    "printf '[user]\\n\\tname = PAX User\\n\\temail = user@example.invalid\\n' > ~/.gitconfig",
    "printf '[init]\\n\\tdefaultBranch = main\\n' >> ~/.gitconfig",
]
for where, d in (('TMP', '/tmp/den-tmp'), ('HOME', '/home/pax/den-home')):
    tag = where.lower()
    USER_A += [
        f'mkdir {d} && cd {d}',
        f'den init; echo PX98-{where}-INIT=$?',
        f'den status; echo PX98-{where}-STATUS1=$?',
        f'echo one > a.txt; den add a.txt; echo PX98-{where}-ADD=$?',
        f"den commit -q -m '{tag}: first'; echo PX98-{where}-COMMIT1=$?",
        f"echo two >> a.txt; den commit -q -a -m '{tag}: second'; echo PX98-{where}-COMMIT2=$?",
        f'den log --no-decorate; echo PX98-{where}-LOG=$?',
        f'den status; echo PX98-{where}-STATUS2=$?',
    ]
USER_A += ['cd /', 'echo PX98-RUN1-END', 'exit']
ROOT_B = [
    'echo PX98-RUN2-BEGIN',
    "stat -L -c 'PX98-ROOT-TERM %u %g %a' /dev/stdin",
    'cd /home/pax/den-home && den status; echo PX98-ROOT-STATUS=$?',
    'cd /; chown 0 /dev/tty; echo PX98-TTY-FIXED=$?',
    'echo PX98-RUN2-END', 'exit',
]
USER_C = ["stat -L -c 'PX98-AGAIN-TERM %u %g %a' /dev/stdin", 'exit']
LIVE_D = ["stat -L -c 'PX98-LIVE-TERM %u %g %a' /dev/stdin", 'exit']
RUNS = [('pax', USER_A), ('root', ROOT_B), ('pax', USER_C), ('root', LIVE_D)]


def run(iso, home, logp, firmware, ovmf):
    logp = Path(logp)
    mon = str(logp) + '.mon'
    if os.path.exists(mon):
        os.unlink(mon)
    accel = 'kvm:tcg' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg'
    cmd = ['qemu-system-x86_64', '-machine', 'q35,accel=' + accel, '-cpu', 'max', '-m', '1024M',
           '-display', 'none', '-serial', 'stdio', '-monitor', 'unix:' + mon + ',server=on,wait=off',
           '-nic', 'none', '-no-reboot', '-parallel', 'none',
           '-drive', f'file={iso},format=raw,media=cdrom,readonly=on', '-boot', 'd',
           '-drive', f'file={home},if=none,id=d1,format=raw', '-device', 'virtio-blk-pci,drive=d1']
    if firmware == 'uefi':
        cmd += ['-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=' + ovmf]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    buf = bytearray()
    lock = threading.Lock()
    out = logp.open('wb')

    def reader():
        for b in iter(lambda: p.stdout.read1(8192), b''):
            with lock:
                buf.extend(b)
            out.write(b)
            out.flush()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def text():
        with lock:
            return bytes(buf)

    def wait(pred, what, seconds=600):
        end = time.monotonic() + seconds
        while not pred(text()):
            assert p.poll() is None, 'QEMU exited: ' + what
            assert time.monotonic() < end, 'timeout ' + what + '\n' + text()[-3000:].decode(errors='replace')
            time.sleep(.1)

    def send(s):
        for b in s.encode():
            p.stdin.write(bytes([b]))
            p.stdin.flush()
            time.sleep(.01)
        p.stdin.write(b'\r')
        p.stdin.flush()

    why = ''
    try:
        for k, (account, lines) in enumerate(RUNS, 1):
            mark = b'\nrun %d: ' % k
            wait(lambda s: mark in s and b'login: ' in s.split(mark, 1)[1], f'run {k} login prompt')
            send(account)
            for n, line in enumerate(lines, 1):
                assert '$ ' not in line, line
                wait(lambda s: s.split(mark, 1)[1].split(b'login: ', 1)[1].count(b'$ ') >= n, f'run {k} prompt {n}')
                send(line)
        wait(lambda s: re.search(rb'\nhalt\r?\n', s) is not None or b'PANIC ' in s, 'halt', 300)
    except AssertionError as e:
        why = str(e)[:1500]
    finally:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as m:
                m.settimeout(10)
                m.connect(mon)
                g = bytearray()
                while b'(qemu)' not in g:
                    g.extend(m.recv(4096))
                m.sendall(b'quit\n')
                while m.recv(4096):
                    pass
        except OSError:
            pass
        p.wait(timeout=20)
        thread.join(timeout=5)
        out.close()
    return why


def norm(raw):
    s = raw.replace('\r', '')
    s = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', s)
    return s


def part(s, k):
    """Run k's transcript: from its `run k:` line to the next run's (or the
    end), the kernel's own lines left out (tests/mpx5-den's run_part rule: a
    line from `user: ` on is the kernel's, wherever in the line it starts)."""
    m = re.search(r'(?m)^run %d: .*$' % k, s)
    if not m:
        return ''
    rest = s[m.end():]
    n = re.search(r'(?m)^run %d: ' % (k + 1), rest)
    rest = rest[:n.start()] if n else rest
    out = []
    for line in rest.split('\n'):
        i = line.find('user: ')
        if i == 0:
            continue
        out.append(line[:i] if i > 0 else line)
    return '\n'.join(out)


def rows(logp, firmware, why):
    s = norm(Path(logp).read_bytes().decode('latin-1'))
    fails = []

    def bad(row, msg):
        fails.append(row)
        print(f'FAIL {row} {firmware}: {msg}', flush=True)

    if why:
        bad('L5', 'the sessions did not finish: ' + why)
    r1, r2, r3, r4 = (part(s, k) for k in (1, 2, 3, 4))
    l1 = r1.splitlines()

    def has(lines, word):
        return word in lines

    # L1
    w = ''
    if not has(l1, 'PX98-TERM 1000 1000 600'):
        w += ' the terminal is %r, not 1000 1000 600;' % ([x for x in l1 if x.startswith('PX98-TERM ')] or ['none'])
    if not has(l1, 'PX98-CHMOD 1000 1000 620'):
        w += ' its owner\'s chmod 620: %r;' % ([x for x in l1 if x.startswith('PX98-CHMOD ')] or ['none'])
    if not has(l1, 'PX98-CHOWN-USER=1') or 'Operation not permitted' not in r1:
        w += ' a user\'s chown of the terminal was not -EPERM (%r);' % [x for x in l1 if 'CHOWN' in x or 'chown:' in x]
    if w:
        bad('L1', w)
    else:
        print(f'PASS L1 {firmware}: the login gave the terminal to pax (1000 1000 600); its owner may chmod it, not chown it to root (EPERM)', flush=True)
    # L2
    w = ''
    for word in ('PX98-OUT', 'PX98-STDOUT=0', 'PX98-ERR', 'PX98-STDERR=0'):
        if not has(l1, word):
            w += f' no {word};'
    pd = [x for x in l1 if 'Permission denied' in x]
    if pd:
        w += ' %d lines say Permission denied (%r);' % (len(pd), pd[0][:120])
    if w:
        bad('L2', w)
    else:
        print(f'PASS L2 {firmware}: echo > /dev/stdout and > /dev/stderr print as pax, status 0; nothing says Permission denied', flush=True)
    # L3
    w = ''
    for where in ('TMP', 'HOME'):
        for step in ('INIT', 'STATUS1', 'ADD', 'COMMIT1', 'COMMIT2', 'LOG', 'STATUS2'):
            if not has(l1, f'PX98-{where}-{step}=0'):
                got = [x for x in l1 if x.startswith(f'PX98-{where}-{step}=')]
                w += f' {where.lower()} {step.lower()}: {got[0] if got else "no line"};'
    fd = [x for x in l1 if x.startswith('fatal: ')]
    if fd:
        w += ' %d fatal lines (%r);' % (len(fd), fd[0][:120])
    if sum(1 for x in l1 if x == 'On branch main') < 4:
        w += ' status said On branch main %d times, not 4;' % sum(1 for x in l1 if x == 'On branch main')
    for subj in ('tmp: first', 'tmp: second', 'home: first', 'home: second'):
        if not has(l1, '    ' + subj):
            w += f' log has no {subj!r};'
    if w:
        bad('L3', w)
    else:
        print(f'PASS L3 {firmware}: den init, status, add, commit, log --no-decorate and status at the terminal as pax, under /tmp and under ~ (ext2), each status 0; no fatal line', flush=True)
    # L4
    w = ''
    l2, l3, l4 = r2.splitlines(), r3.splitlines(), r4.splitlines()
    if not has(l2, 'PX98-ROOT-TERM 0 0 600'):
        w += ' root\'s login left it %r;' % ([x for x in l2 if x.startswith('PX98-ROOT-TERM')] or ['none'])
    if not has(l2, 'PX98-ROOT-STATUS=0'):
        w += ' root\'s den status: %r;' % [x for x in l2 if 'STATUS' in x or x.startswith('fatal')]
    if not has(l2, 'PX98-TTY-FIXED=1') or 'Read-only file system' not in r2:
        w += ' /dev/tty was not fixed (%r);' % [x for x in l2 if 'TTY' in x or 'chown:' in x]
    if not has(l3, 'PX98-AGAIN-TERM 1000 1000 600'):
        w += ' the second pax login: %r;' % ([x for x in l3 if x.startswith('PX98-AGAIN')] or ['none'])
    if not has(l4, 'PX98-LIVE-TERM 0 0 600'):
        w += ' the live login: %r;' % ([x for x in l4 if x.startswith('PX98-LIVE')] or ['none'])
    if w:
        bad('L4', w)
    else:
        print(f'PASS L4 {firmware}: root\'s login took the terminal back (0 0 600), root\'s den status 0, /dev/tty fixed; pax\'s again 1000 1000 600, the live login\'s 0 0 600', flush=True)
    # L5
    w = ''
    ns = sorted({m.group(2) for m in re.finditer(r'(?m)^user: (den|git) pid \d+ syscall (\d+): -ENOSYS$', s)}, key=int)
    for x in ns:
        if x not in ('273', '334'):
            w += f' -ENOSYS for {x};'
    # Root's chown of /dev/tty (L4) is refused by name, once: what PAX keeps fixed.
    fixed = re.compile(r'^user: chown pid \d+ syscall \d+: refused: a mode, an owner, times or a link of what PAX keeps fixed')
    rf = [x for x in s.splitlines() if ': refused: ' in x]
    tty = [x for x in rf if fixed.match(x)]
    rf = [x for x in rf if not fixed.match(x)]
    if rf:
        w += ' %d refused lines (%s);' % (len(rf), rf[0][:160])
    if len(tty) != 1:
        w += ' %d refusals of a fixed node by chown, not 1 (root\'s /dev/tty);' % len(tty)
    if not re.search(r'(?m)^PAX: init /bin/pelt ended with status 0; nothing left to run$', s):
        w += ' no "PAX: init /bin/pelt ended with status 0";'
    if 'PANIC ' in s:
        w += ' the kernel panicked;'
    if not re.search(r'(?m)^halt$', s):
        w += ' no halt line;'
    if w:
        bad('L5', w)
    else:
        print(f'PASS L5 {firmware}: -ENOSYS from den only for {ns or "none"} (of 273 334); nothing refused; init ended, status 0; halted', flush=True)
    return 1 if fails else 0


def main():
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == 'text':
        sys.stdout.write(login_text(a[1]))
        return 0
    if len(a) in (5, 6) and a[0] == 'run':
        _, iso, home, logp, firmware = a[:5]
        ovmf = a[5] if len(a) == 6 else ''
        why = run(iso, home, logp, firmware, ovmf)
        return rows(logp, firmware, why)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
