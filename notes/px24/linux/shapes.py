#!/usr/bin/env python3
"""px24 scratch: every syscall in a set of strace -f files, with the
flags, option levels and names, fcntl commands, ioctl requests, clocks
and the like each was seen with. One line per distinct shape, counted."""
import re, sys, collections
shapes = collections.Counter()
errs = collections.defaultdict(collections.Counter)
pending = {}
line_re = re.compile(r'^(\d+)\s+(.*)$')
call_re = re.compile(r'^([a-z_0-9]+)\((.*)\)\s+= (-?\d+|0x[0-9a-f]+|\?)(?: ([A-Z]+) .*)?(?: \(.*\))?$')
def args_of(s):
    out, depth, cur, q = [], 0, '', False
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur += c
            if c == '\\': cur += s[i+1]; i += 1
            elif c == '"': q = False
        elif c == '"': q = True; cur += c
        elif c in '([{': depth += 1; cur += c
        elif c in ')]}': depth -= 1; cur += c
        elif c == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += c
        i += 1
    if cur.strip(): out.append(cur.strip())
    return out
def shape(name, a):
    g = lambda i: a[i] if i < len(a) else '?'
    if name in ('socket',): return f"{g(0)}, {g(1)}, {g(2)}"
    if name in ('setsockopt', 'getsockopt'):
        v = g(3) if name == 'setsockopt' else ''
        return f"{g(1)}, {g(2)}" + (f", {v}" if v else '') + f", len {g(4)}"
    if name == 'fcntl': return f"{g(1)}" + (f", {g(2)}" if len(a) > 2 and not g(2).isdigit() else (', <n>' if len(a) > 2 else ''))
    if name == 'ioctl': return f"{g(1)}"
    if name in ('epoll_ctl',):
        ev = re.sub(r'data=\{.*', '', g(3))
        return f"{g(1)}, {ev}"
    if name in ('epoll_create1', 'eventfd2', 'pipe2'): return g(len(a)-1)
    if name in ('epoll_wait', 'epoll_pwait', 'epoll_pwait2'): return f"maxevents {g(2)}, timeout {'<ms>' if g(3) not in ('-1','0') else g(3)}" + (f", sigmask {g(4)}" if len(a) > 4 else '')
    if name in ('poll', 'ppoll'):
        evs = sorted(set(re.findall(r'events=([A-Z|]+)', g(0))))
        t = g(2)
        return f"events {'/'.join(evs)}, nfds {'1' if g(1)=='1' else 'n'}, timeout {t if t in ('-1','0','NULL') else '<t>'}"
    if name == 'accept4': return f"addr {g(1) if g(1)=='NULL' else '<addr>'}, {g(3)}"
    if name in ('sendto', 'recvfrom'): return f"flags {g(3)}, addr {g(4) if g(4)=='NULL' else '<addr>'}"
    if name in ('sendmsg', 'recvmsg'):
        c = 'control' if 'msg_control=' in g(1) and 'msg_controllen=0' not in g(1) else 'no control'
        return f"{c}, flags {g(2)}"
    if name in ('clock_gettime', 'clock_nanosleep', 'clock_getres'): return g(0) + (f", {g(1)}" if name == 'clock_nanosleep' else '')
    if name == 'getrandom': return f"len {g(1)}, {g(2)}"
    if name == 'prctl': return g(0)
    if name in ('mmap',): return f"{g(2)}, {g(3)}, fd {'-1' if g(4)=='-1' else '<fd>'}"
    if name in ('mprotect',): return g(2)
    if name in ('madvise',): return g(2)
    if name == 'futex': return re.sub(r'\d+', '', g(1))
    if name in ('openat',): return f"{g(2)}"
    if name == 'open': return g(1)
    if name in ('rt_sigaction',): return g(0)
    if name in ('rt_sigprocmask',): return f"{g(0)}, {g(1)}"
    if name in ('clone',): return re.sub(r'child_stack=\S+', 'child_stack=…', ', '.join(x for x in a if 'flags=' in x))
    if name == 'clone3':
        m = re.search(r'flags=([A-Z_|]+)', a[0]); return m.group(1) if m else '?'
    if name in ('shutdown', 'listen'): return g(1) if name == 'shutdown' else '<backlog>'
    if name in ('lseek',): return g(2)
    if name in ('wait4',): return g(2)
    if name in ('kill', 'tgkill', 'tkill'): return g(len(a)-1)
    if name in ('arch_prctl', 'prlimit64'): return g(0) if name == 'arch_prctl' else g(1)
    if name in ('sendfile', 'copy_file_range', 'splice'): return '<fds>'
    if name in ('newfstatat', 'statx'): return g(3) if name == 'newfstatat' else f"{g(2)}, {g(3)}"
    if name in ('socketpair',): return f"{g(0)}, {g(1)}, {g(2)}"
    if name in ('bind', 'connect'):
        m = re.search(r'sa_family=(\w+)', g(1)); return m.group(1) if m else '?'
    if name in ('dup3',): return g(2)
    if name in ('sigaltstack', 'timerfd_create', 'timerfd_settime', 'signalfd4', 'inotify_init1', 'memfd_create', 'unlink', 'unlinkat', 'mkdir', 'rename', 'chmod', 'fchmod', 'umask', 'access', 'faccessat2', 'ftruncate', 'fsync', 'fdatasync', 'flock'): return g(1) if name in ('timerfd_settime', 'flock', 'faccessat2') else ''
    return ''
for path in sys.argv[1:]:
    for raw in open(path, errors='replace'):
        m = line_re.match(raw.rstrip('\n'))
        if not m: continue
        pid, rest = m.groups()
        if rest.endswith('<unfinished ...>'):
            pending[pid] = rest[:-len('<unfinished ...>')].rstrip(); continue
        r = re.match(r'^<\.\.\. (\S+) resumed>(.*)$', rest)
        if r:
            rest = pending.pop(pid, r.group(1) + '(') + r.group(2)
        if rest.startswith('+++') or rest.startswith('---'):
            if rest.startswith('---'):
                shapes[('(signal delivered)', rest.split()[1])] += 1
            continue
        c = call_re.match(rest)
        if not c:
            if rest.startswith('exit') : shapes[(rest.split('(')[0], '')] += 1
            else: shapes[('(unparsed)', rest[:60])] += 1
            continue
        name, argstr, ret, err = c.groups()
        sh = shape(name, args_of(argstr))
        shapes[(name, sh)] += 1
        if err: errs[(name, sh)][err] += 1
for (name, sh), n in sorted(shapes.items()):
    e = errs.get((name, sh))
    es = ('  [' + ', '.join(f"{k}×{v}" for k, v in sorted(e.items())) + ']') if e else ''
    print(f"{name}\t{sh}\t{n}{es}")
