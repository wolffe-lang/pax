#!/usr/bin/env python3
"""last-cases.py PAX_LAST OUT — px133's L1: PAX's last and lastb held byte for byte to util-linux's
(this host's /usr/bin/last and lastb) on files of utmp(5) records written here as utmp(5) lays them
out (x86-64: 384 bytes, 32-bit time) in the shapes Ubuntu's login and OpenSSH's sshd write (measured
in a container: docs/SOURCES.md, px133): a boot, the console, an ssh logout, a dropped session, a clean
shutdown, a session open at a power cut, one open at a shutdown, a session over a day, names and hosts
past their columns, refused logins. Each file is read with each option set by both;
every difference is `FAIL L1 …` at column 0. Exit 0, 1, or 3 when this host has no util-linux last.
`still logged in` against `gone - no logout` turns on whether a record's pid lives on THIS host (pid 1
does, 4000000 does not), the same question for both programs."""
import os
import shutil
import struct
import subprocess
import sys

PAX = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
T0 = 1794600000  # 2026-11-13T21:20:00Z


def rec(kind, pid=0, line='', rid='', user='', host='', t=0, usec=0, addr=b'', term=0, exit_=0, session=0):
    b = bytearray(384)
    struct.pack_into('<hxxi', b, 0, kind, pid)
    for at, width, s in ((8, 32, line), (40, 4, rid), (44, 32, user), (76, 256, host)):
        e = s.encode()[:width]
        b[at:at + len(e)] = e
    struct.pack_into('<hhiii', b, 332, term, exit_, session, t, usec)
    b[348:348 + len(addr)] = addr
    return bytes(b)


def boot(t):
    return rec(2, 0, '~', '~~', 'reboot', '0.0.1', t)


def down(t):
    return rec(1, 0, '~', '~~', 'shutdown', '0.0.1', t)


def login(t, pid, line, user, host='', addr=b''):
    return rec(7, pid, line, line[-4:] if line.startswith('pts/') else line[-4:], user, host, t, addr=addr)


def logout(t, pid, line, term=0, exit_=0):
    return rec(8, pid, line, '', '', '', t, term=term, exit_=exit_)


A = bytes([192, 168, 89, 1])
GONE = 4000000  # a pid no process has
FILES = {
    # boot, the console, a logout over ssh, a dropped one, a clean shutdown, a boot, the console still on,
    # an ssh session whose process is gone
    'story': [boot(T0), login(T0 + 10, 1, 'console', 'root'),
              login(T0 + 20, 140, 'pts/0', 'pax', '192.168.89.1', A), logout(T0 + 95, 140, 'pts/0', 0, 0),
              login(T0 + 100, 150, 'pts/0', 'pax', '192.168.89.1', A), logout(T0 + 3725, 150, 'pts/0', 1, 0),
              down(T0 + 4000),
              boot(T0 + 4100), login(T0 + 4110, 1, 'console', 'root'),
              login(T0 + 4200, GONE, 'pts/1', 'pax', '192.168.89.1', A)],
    # a session open at a power cut: the next boot with no shutdown before it
    'crash': [boot(T0), login(T0 + 10, 1, 'console', 'root'), login(T0 + 20, 140, 'pts/0', 'pax', '192.168.89.1', A),
              boot(T0 + 200), login(T0 + 210, 1, 'console', 'root')],
    # a session open at a clean shutdown
    'down': [boot(T0), login(T0 + 10, 1, 'console', 'root'), down(T0 + 300), boot(T0 + 400)],
    # long sessions: a day and more
    'long': [boot(T0), login(T0 + 10, 140, 'pts/0', 'pax', '192.168.89.1', A), logout(T0 + 10 + 90061, 140, 'pts/0'),
             down(T0 + 200000)],
    # names past the columns' widths, an empty host, an IPv6 address
    'wide': [boot(T0), login(T0 + 5, 141, 'pts/10', 'averyveryverylongname', 'host.with.a.long.name.example',
                             bytes([192, 168, 89, 77])), logout(T0 + 6, 141, 'pts/10')],
    # (a file with no record says `FILE begins` with the time now: held by G5's run on the guest's files,
    # not here, where two programs' `now` can differ by a second)
    # failed logins (lastb): console and ssh, as Ubuntu's login and sshd wrote them
    'btmp': [rec(7, 43, 'console', 'cons', 'UNKNOWN', '', T0 + 1), rec(7, 43, 'console', 'cons', 'pax', '', T0 + 5),
             rec(6, 113, 'ssh:notty', '', 'pax', '192.168.89.1', T0 + 60, addr=A),
             rec(6, 117, 'ssh:notty', '', 'nosuch', '192.168.89.1', T0 + 62, addr=A)],
}

OPTS = [[], ['-x'], ['-F'], ['-i'], ['-w'], ['-a'], ['-n', '2'], ['-3'], ['-x', '-F'], ['-w', '-x'], ['-R']]


def main():
    if not shutil.which('last') or not shutil.which('lastb'):
        print('SKIP L1 this host has no util-linux last and lastb', flush=True)
        return 3 if os.environ.get('PAX_REQUIRE_BURROWD_RIG') != '1' else 1
    if not os.path.isfile(PAX):
        print('FAIL L1 no PAX last at %s (tools/mklogd)' % PAX, flush=True)
        return 1
    env = dict(PATH='/usr/bin:/bin', TZ='UTC', LC_ALL='C')
    for prog in ('last', 'lastb'):
        link = os.path.join(OUT, prog)
        if os.path.lexists(link):
            os.unlink(link)
        os.symlink(PAX, link)
    bad = []
    n = 0
    for name, recs in FILES.items():
        path = os.path.join(OUT, name)
        with open(path, 'wb') as f:
            f.write(b''.join(recs))
        os.utime(path, (T0, T0))  # an empty file's `begins` line is its time: the same for both
        prog = 'lastb' if name == 'btmp' else 'last'
        for opts in OPTS:
            argv = opts + ['-f', path]
            p = subprocess.run([os.path.join(OUT, prog)] + argv, capture_output=True, env=env)
            l = subprocess.run([prog] + argv, capture_output=True, env=env)
            n += 1
            if (p.returncode, p.stdout, p.stderr) != (l.returncode, l.stdout, l.stderr):
                tag = '%s%s' % (name, ''.join('_' + o.strip('-') for o in opts))
                with open(os.path.join(OUT, tag + '.pax'), 'wb') as f:
                    f.write(p.stdout + p.stderr + b'status %d\n' % p.returncode)
                with open(os.path.join(OUT, tag + '.linux'), 'wb') as f:
                    f.write(l.stdout + l.stderr + b'status %d\n' % l.returncode)
                bad.append('%s %s' % (prog, ' '.join(argv)))
    for argv in (['-f', '/nonexistent'], ['-f']):
        p = subprocess.run([os.path.join(OUT, 'last')] + argv, capture_output=True, env=env)
        l = subprocess.run(['last'] + argv, capture_output=True, env=env)
        n += 1
        if (p.returncode, p.stdout, p.stderr) != (l.returncode, l.stdout, l.stderr):
            bad.append('last %s' % ' '.join(argv))
    if bad:
        print('FAIL L1 %d of %d runs differ from util-linux: %s' % (len(bad), n, '; '.join(bad[:8])), flush=True)
        return 1
    print('PASS L1 %d runs of last and lastb byte for byte as util-linux\'s, %d files' % (n, len(FILES)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
