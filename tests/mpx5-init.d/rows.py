#!/usr/bin/env python3
"""tests/mpx5-init.d/rows.py — px124 (pax#352): the rows of tests/mpx5-init on
one tier and firmware. The image's tree is tests/mpx5-init's (its files.txt);
this program adds /etc/shadow (passwords made now, hashed by mkshadow on its
standard input), makes the ISO and, for I13, a disk whose ext2 volume is `/`,
and types at the console through COM1 (tools/qemu-run, two FIFOs).

Boot 1, the tree in memory (an ISO, `quiet`): the run list is `/bin/login`, as
an installer writes it; login as pid 1 execs /bin/init.
  I1  /proc/1/cmdline is `/bin/init`; pax's login shell's parent is 1, it leads
      its session (its sid its pid), the console (4:64, tty_nr 1088) is its
      controlling terminal, and pid 1 has none (tty_nr 0).
  I2  /run is a tmpfs, 0755 root's; /run/user 0755 root's; XDG_RUNTIME_DIR is
      /run/user/1000, 0700 pax's; /run/user/0 and /run/user/1001 made at boot
      (root's and bob's), none for lobo (/bin/false).
  I3  a typed `sudo id -u` asks pax's password; `sudo -n id -u` after it, in the
      same session, is not asked (sudo's parent is the shell, not pid 1).
  I4  `stty -echo; exit`: `pax login:` again within 10 s, the machine running.
  I5  the session's leftovers at the logout: a background `sleep` ended by the
      hangup; one that ignores SIGHUP killed 2000 ms later, and init's one line
      names it (`SIGKILL to 1 of 2`).
  I6  `detach` (user/elf/detach.c: setsid, then it sleeps 20 s) lives on after
      the logout, pid 1's child in a session of its own, and is gone (reaped,
      no zombie) once its 20 s are up.
  I7  the console's modes back: pax's session ends `stty -echo; exit`, and in
      bob's session ttymode (user/elf/ttymode.c) reads `echo` and `icanon`
      (login echoes a name itself, so its prompt shows nothing either way).
  I8  a second account, bob, logs in after the logout: `id -un`, its runtime
      directory /run/user/1001, 0700 bob's.
  I11 the boot hook's service (/run/svc.pid) has its pid and pid 1's session
      before the first logout and after the third.
  I9  `logout` (bob) and Ctrl-D at an empty prompt (pax again) each give
      `pax login:` again.
  I10 sudo across a logout: in pax's next session `sudo -n id -u` is refused
      (`a password is required`): the first session's record is void.
  I12 root's `reboot -h`: the kernel's end (`PAX: the end: SIGTERM to …`), then
      `halt`.
Boots 2 and 3, one disk whose ext2 volume is `/` (root=/dev/vda), /tmp and /run
the kernel's and init's:
  I13 pax leaves a file in its runtime directory and one in its home and runs
      `sudo reboot`; the next boot of the disk has the home's file, an empty
      /run/user/1000 that is pax's 0700 again on /run's tmpfs, and `sudo
      poweroff` ends the machine (QEMU exits 0).

Exit 0 when every row held, 1 otherwise. A row that cannot be reached (the
machine halted at a logout) fails by name with what the console said.
"""
import argparse
import os
import pathlib
import re
import secrets
import select
import shutil
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FAILS = []
ARGS = None
PASSWORDS = {}
MARK = 'PX124-ROW-'
DETACH_S = 20


def say(line):
    print('mpx5-init %s %s: %s' % (ARGS.tier, ARGS.leg, line), flush=True)


def ok(row, why):
    say('PASS %s: %s' % (row, why))


def bad(row, why):
    FAILS.append(row)
    print('FAIL %s %s %s: %s' % (row, ARGS.tier, ARGS.leg, why), flush=True)


def run(argv, data=b'', timeout=300, env=None):
    r = subprocess.run([str(a) for a in argv], input=data, capture_output=True, timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError('%s: exit %d: %s' % (argv[0], r.returncode, r.stderr.decode(errors='replace')[-400:]))
    return r


class Console:
    """QEMU through tools/qemu-run, COM1 on two FIFOs: the transcript read as it
    comes, lines typed a byte every 20 ms (mpx5-burrowd's console, no network)."""

    def __init__(self, out, iso, drive=None):
        out.mkdir(parents=True, exist_ok=True)
        self.out = out
        self.out_fifo, self.in_fifo, self.mon = (out / n for n in ('com1.out', 'com1.in', 'monitor'))
        for f in (self.out_fifo, self.in_fifo):
            if f.exists():
                f.unlink()
            os.mkfifo(f, 0o600)
        self.rfd = os.open(self.out_fifo, os.O_RDWR | os.O_NONBLOCK)
        self.wfd = os.open(self.in_fifo, os.O_RDWR)
        self.log = open(out / 'serial.log', 'wb')
        self.seen = b''
        self.cursor = 0
        cmd = [ROOT / 'tools/qemu-run', '--firmware', ARGS.leg, '--accel', ARGS.accel, '--timeout', '900',
               '--serial', self.out_fifo, '--serial-input', self.in_fifo] + (['--drive', drive] if drive else []) + [iso, '--',
               '-monitor', 'unix:%s,server=on,wait=off' % self.mon, '-m', '768M']
        self.q = subprocess.Popen([str(x) for x in cmd], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

    def pump(self, wait=0.1):
        r, _, _ = select.select([self.rfd], [], [], wait)
        if not r:
            return
        try:
            data = os.read(self.rfd, 65536)
        except BlockingIOError:
            return
        if data:
            self.log.write(data)
            self.log.flush()
            self.seen += data.replace(b'\r', b'')

    def text(self, tail=600):
        return self.seen.decode(errors='replace')[-tail:]

    def wait(self, pattern, timeout=120):
        """The first match after the cursor; the cursor moves past it. None after
        `timeout` seconds or QEMU's end."""
        rx = re.compile(pattern.encode() if isinstance(pattern, str) else pattern, re.M)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            m = rx.search(self.seen, self.cursor)
            if m:
                self.cursor = m.end()
                return m
            if self.q.poll() is not None:
                self.pump(0.2)
                m = rx.search(self.seen, self.cursor)
                if m:
                    self.cursor = m.end()
                    return m
                return None
            self.pump(0.1)
        return None

    def raw(self, data):
        time.sleep(0.2)
        for ch in data:
            os.write(self.wfd, bytes([ch]))
            time.sleep(0.02)

    def type(self, line):
        self.raw(line.encode() + b'\r')

    def command(self, line, n, timeout=120):
        """`echo MARKB$((n+0)); line; echo MARKE$((n+0))`: what `line` wrote, the
        lines between the two marks as printed (never their echo, which the
        console may wrap anywhere), or None."""
        self.type('echo %sB$((%d+0)); %s; echo %sE$((%d+0))' % (MARK, n, line, MARK, n))
        b = self.wait(r'^%sB%d\n' % (MARK, n), timeout)
        if not b:
            return None
        e = self.wait(r'^%sE%d$' % (MARK, n), timeout)
        if not e:
            return None
        return self.seen[b.end():e.start()].decode(errors='replace')

    def running(self):
        return self.q.poll() is None

    def quit(self, halt_timeout=0):
        if halt_timeout:
            self.wait(r'^halt$', halt_timeout)
        if self.q.poll() is None:
            try:
                s = socket.socket(socket.AF_UNIX)
                s.connect(str(self.mon))
                s.sendall(b'quit\n')
                s.close()
            except OSError:
                pass
            try:
                self.q.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.q.terminate()
                self.q.wait(timeout=30)
        self.pump(0.2)
        self.log.close()
        os.close(self.rfd)
        os.close(self.wfd)


def make_shadow(work):
    for k in ('root', 'pax', 'bob'):
        PASSWORDS[k] = secrets.token_urlsafe(18)
    mk = ARGS.images / 'tools' / 'mkshadow'
    text = run([mk, '--cost', '14', '8', '1'], data=('root %s\npax %s\nbob %s\nlobo !\n' % (
        PASSWORDS['root'], PASSWORDS['pax'], PASSWORDS['bob'])).encode(), timeout=600).stdout.decode()
    (work / 'shadow').write_text(text)
    os.chmod(work / 'shadow', 0o600)


def files(work):
    out = [l for l in (ARGS.images / 'files.txt').read_text().splitlines() if l]
    return out + ['/etc/shadow=%s:600' % (work / 'shadow')]


def iso(work, name, cmdline):
    conf = work / (name + '.conf')
    text = (ROOT / 'boot/limine-initramfs-quiet.conf').read_text()
    conf.write_text(text.replace('cmdline: quiet', 'cmdline: ' + cmdline))
    run([ROOT / 'tools/mkinitramfs', work / (name + '.cpio')] + files(work))
    run([ROOT / 'tools/mkimage', '--conf', conf, '--add', work / (name + '.cpio'), 'initramfs.cpio', ARGS.elf,
         work / (name + '.iso')])
    return work / (name + '.iso')


def disk(work):
    """The tree as an ext2 volume (mke2fs -d), every inode's mode and owner set
    after by debugfs from files.txt (the host's own uid wrote them)."""
    stage = work / 'disk-tree'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    attrs = {'/': (0o755, 0, 0)}
    for d in ('dev', 'proc', 'sys'):
        (stage / d).mkdir()
        attrs['/' + d] = (0o755, 0, 0)
    for line in files(work):
        if '=' in line:
            path, rest = line.split('=', 1)
            src, spec = rest.split(':')[0], rest.split(':')[1:]
            mode = int(spec[0], 8)
            uid = int(spec[1]) if len(spec) > 1 else 0
            gid = int(spec[2]) if len(spec) > 2 else 0
            dst = stage / path.lstrip('/')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            attrs[path] = (0o100000 | mode, uid, gid)
        else:
            f = line.split(':')
            path = f[0].rstrip('/')
            (stage / path.lstrip('/')).mkdir(parents=True, exist_ok=True)
            attrs[path] = (0o040000 | int(f[1], 8), int(f[2]) if len(f) > 2 else 0, int(f[3]) if len(f) > 3 else 0)
    for p in sorted(stage.rglob('*')):
        key = '/' + p.relative_to(stage).as_posix()
        if key not in attrs:
            attrs[key] = ((0o040755 if p.is_dir() else 0o100644), 0, 0)
    img = work / 'root.img'
    env = dict(PATH='/usr/sbin:/sbin:/usr/bin:/bin', E2FSPROGS_FAKE_TIME='1700000000')
    size = sum(f.stat().st_size for f in stage.rglob('*') if f.is_file())
    mib = (size * 3 // 2) // (1 << 20) + 64  # the tree, half again for ext2's own, room to write
    run(['mke2fs', '-q', '-F', '-t', 'ext2', '-L', 'px124-root', '-d', stage, img, '%dM' % mib], env=env)
    cmds = ''
    for path, (mode, uid, gid) in sorted(attrs.items()):
        cmds += 'sif %s mode 0%o\nsif %s uid %d\nsif %s gid %d\n' % (path, mode, path, uid, path, gid)
    (work / 'debugfs.cmd').write_text(cmds)
    run(['debugfs', '-w', '-f', work / 'debugfs.cmd', img], env=env)
    run(['e2fsck', '-fn', img], env=env)
    return img


def login(con, who, row):
    """`who` logs in at `pax login:`; the shell's prompt. False (and the row
    red) when a prompt does not come."""
    if not con.wait(r'login: $', 60):
        bad(row, 'no `login:` prompt for %s: %r' % (who, con.text(400)))
        return False
    con.type(who)
    if not con.wait(r'Password: $', 30):
        bad(row, 'no Password: prompt for %s: %r' % (who, con.text(400)))
        return False
    con.type(PASSWORDS[who])
    if not con.wait(r'\$ $', 60):
        bad(row, '%s did not log in: %r' % (who, con.text(400)))
        return False
    return True


def asked_sudo(con, n, who):
    """`sudo id -u` typed, `who`'s password at its prompt: (asked, the lines
    after the prompt, or all it wrote when it asked nothing)."""
    con.type('echo %sB$((%d+0)); sudo id -u; echo %sE$((%d+0))' % (MARK, n, MARK, n))
    b = con.wait(r'^%sB%d\n' % (MARK, n), 60)
    if not b:
        return False, ''
    m = con.wait(r'\[sudo\] password for %s: $|^%sE%d$' % (who, MARK, n), 60)
    if m and m.group(0).startswith(b'[sudo]'):
        at = m.end()
        con.type(PASSWORDS[who])
        m2 = con.wait(r'^%sE%d$' % (MARK, n), 60)
        return True, con.seen[at:m2.start()].decode(errors='replace') if m2 else ''
    return False, con.seen[b.end():m.start()].decode(errors='replace') if m else ''


def stat_of(con, pid, n):
    """/proc/PID/stat's fields as a list (None when it cannot be read)."""
    out = con.command('cat /proc/%d/stat 2>&1' % pid, n) or ''
    line = out.strip().splitlines()[-1] if out.strip() else ''
    if ')' not in line or 'No such file' in line:
        return None
    return [line.split(' ', 1)[0]] + line[line.rindex(')') + 2:].split(' ')


def logged_out(con, how, row, t0):
    """`pax login:` again after a logout `how`, the machine still running."""
    m = con.wait(r'login: $', 15)
    dt = time.monotonic() - t0
    if m and con.running():
        return dt
    why = 'the machine ended' if not con.running() else 'no prompt'
    halt = re.search(rb'PAX: init [^\n]* ended[^\n]*', con.seen)
    bad(row, 'after %s: %s within %.0f s%s: %r' % (how, why, dt, (' (%s)' % halt.group(0).decode()) if halt else '',
                                                    con.text(300)))
    return None


def boot1(con):
    if not con.wait(r'svc: started\n', 180):
        bad('I11', 'the boot hook never ran (no `svc: started`): %r' % con.text(600))
    if not login(con, 'pax', 'I1'):
        return
    # I1
    out = con.command("tr '\\0' ' ' < /proc/1/cmdline; echo; cut -d' ' -f4,6,7 /proc/$$/stat; echo $$; cut -d' ' -f7 /proc/1/stat", 1) or ''
    lines = [l.strip() for l in out.strip().splitlines()]
    shell = None
    if len(lines) >= 4 and len(lines[1].split()) == 3:
        init_cmd, (ppid, sid, tty), me, init_tty = lines[0], lines[1].split(), lines[2], lines[3]
        shell = int(me) if me.isdigit() else None
        if init_cmd == '/bin/init' and ppid == '1' and sid == me and tty == '1088' and init_tty == '0':
            ok('I1', 'pid 1 is /bin/init (no terminal); pax\'s shell %s: parent 1, its own session, the console its terminal' % me)
        else:
            bad('I1', 'pid 1 %r (tty_nr %s); the shell %s: ppid %s sid %s tty_nr %s' % (init_cmd, init_tty, me, ppid, sid, tty))
    else:
        bad('I1', 'unreadable: %r' % out)
    # I2
    out = con.command("echo X=$XDG_RUNTIME_DIR; stat -c '%n %u %g %a %F' /run /run/user /run/user/0 /run/user/1000 "
                      "/run/user/1001 $XDG_RUNTIME_DIR; ls /run/user; cat /proc/self/mounts", 2) or ''
    want = ['X=/run/user/1000', '/run 0 0 755 directory', '/run/user 0 0 755 directory', '/run/user/0 0 0 700 directory',
            '/run/user/1000 1000 1000 700 directory', '/run/user/1001 1001 1001 700 directory']
    got = [l.strip() for l in out.splitlines()]
    mount = [l for l in got if l.split()[1:3] == ['/run', 'tmpfs']]
    listing = ' '.join(l for l in got if re.fullmatch(r'[0-9 ]+', l))
    if all(w in got for w in want) and mount and listing.split() == ['0', '1000', '1001']:
        ok('I2', '/run a tmpfs (%s); %s' % (mount[0], '; '.join(want)))
    else:
        bad('I2', 'missing %s; /run/user lists %r; the mount %r' % ([w for w in want if w not in got], listing, mount))
    # I3
    a1, b1 = asked_sudo(con, 3, 'pax')
    out = con.command('sudo -n id -u 2>&1', 4) or ''
    if a1 and b1.split() == ['0'] and out.strip() == '0':
        ok('I3', 'sudo asked pax once; sudo -n inside the session ran as uid 0 (the terminal\'s record)')
    else:
        bad('I3', 'first sudo asked=%s %r; sudo -n %r' % (a1, b1[-200:], out))
    # The session's leftovers and a process that leaves it.
    svc = (con.command('cat /run/svc.pid', 5) or '').strip()
    svc_stat = stat_of(con, int(svc), 6) if svc.isdigit() else None
    bg = (con.command('sleep 100000 & echo $!', 7) or '').strip().splitlines()[-1:]
    ig = (con.command("pelt -c 'trap \"\" HUP; exec sleep 100000' < /dev/null > /dev/null 2>&1 & echo $!", 8) or '').strip().splitlines()[-1:]
    t_detach = time.monotonic()
    dt = (con.command('detach /tmp/dt %d && cat /tmp/dt' % DETACH_S, 9) or '').strip().split()
    bg = int(bg[0]) if bg and bg[0].isdigit() else None
    ig = int(ig[0]) if ig and ig[0].isdigit() else None
    dt_pid = int(dt[0]) if len(dt) == 2 and dt[0].isdigit() else None
    if not (bg and ig and dt_pid and dt[0] == dt[1]):
        bad('I5', 'the jobs did not start: sleep %r, the SIGHUP-ignoring one %r, detach %r' % (bg, ig, dt))
    # I4: the logout.
    mark = len(con.seen)
    t0 = time.monotonic()
    con.type('stty -echo; exit')
    took = logged_out(con, '`stty -echo; exit`', 'I4', t0)
    if took is None:
        for r in ('I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12'):
            bad(r, 'not reached: the logout gave no login prompt')
        return
    ok('I4', '`exit` gave `pax login:` again %.1f s later, the machine running' % took)
    said = re.search(rb'init: the session of pid (\d+): SIGKILL to (\d+) of (\d+) still there 2000 ms after its SIGHUP',
                     con.seen[mark:])
    # Session 2: bob.
    con.type('bob')
    if not con.wait(r'Password: $', 15):
        for r in ('I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12'):
            bad(r, 'not reached: no Password: prompt for bob')
        return
    con.type(PASSWORDS['bob'])
    if not con.wait(r'\$ $', 60):
        bad('I8', 'bob did not log in: %r' % con.text(300))
        return
    # I5
    gone = [p for p, n in ((bg, 10), (ig, 11)) if p and stat_of(con, p, n) is None]
    if bg and ig and len(gone) == 2 and said and int(said.group(1)) == shell and said.group(2, 3) == (b'1', b'2'):
        ok('I5', 'the background sleep ended at the hangup; the one ignoring SIGHUP was killed, and init said: %s'
           % said.group(0).decode())
    else:
        bad('I5', 'ended %s of sleep %s and %s; init said %r (the session %s)'
            % (gone, bg, ig, said.group(0).decode() if said else None, shell))
    # I6
    st = stat_of(con, dt_pid, 12) if dt_pid else None
    left = DETACH_S + 3 - (time.monotonic() - t_detach)
    con.command('sleep %d' % max(1, int(left + 1)), 13, timeout=DETACH_S + 60)
    st2 = stat_of(con, dt_pid, 14) if dt_pid else None
    if st and st[1] in ('S', 'R') and st[2] == '1' and st[4] == str(dt_pid) and st2 is None:
        ok('I6', 'detach (%d) outlived the logout: pid 1\'s child in its own session; gone %d s after its start, reaped'
           % (dt_pid, DETACH_S))
    else:
        bad('I6', 'detach %s after the logout: %s; after its %d s: %s' % (dt_pid, st[:5] if st else None, DETACH_S,
                                                                          st2[:5] if st2 else 'gone'))
    # I7
    modes = (con.command('ttymode', 15) or '').split()
    if modes[:1] == ['lflag'] and 'echo' in modes and 'icanon' in modes:
        ok('I7', 'the console\'s modes put back: pax left it `-echo`; in bob\'s session %s' % ' '.join(modes))
    else:
        bad('I7', 'in bob\'s session the console\'s modes: %r' % ' '.join(modes)[:300])
    # I8
    out = con.command("id -un; echo X=$XDG_RUNTIME_DIR; stat -c '%u %g %a' $XDG_RUNTIME_DIR", 16) or ''
    got = [l.strip() for l in out.splitlines()]
    if got[:3] == ['bob', 'X=/run/user/1001', '1001 1001 700']:
        ok('I8', 'bob logged in after pax\'s logout: %s' % '; '.join(got[:3]))
    else:
        bad('I8', 'bob\'s session: %r' % got)
    # I11, before the second logout
    svc2 = stat_of(con, int(svc), 17) if svc.isdigit() else None
    # I9: logout
    t0 = time.monotonic()
    con.type('logout')
    took = logged_out(con, '`logout`', 'I9', t0)
    if took is None:
        for r in ('I10', 'I11', 'I12'):
            bad(r, 'not reached: `logout` gave no login prompt')
        return
    # Session 3: pax again. I10: the first session's record void here.
    con.type('pax')
    if not con.wait(r'Password: $', 15):
        bad('I10', 'no Password: prompt for pax again')
        return
    con.type(PASSWORDS['pax'])
    if not con.wait(r'\$ $', 60):
        bad('I10', 'pax did not log in again')
        return
    out = con.command('sudo -n id -u 2>&1; echo rc=$?', 18) or ''
    if 'a password is required' in out and 'rc=1' in out:
        ok('I10', 'pax\'s next session: sudo -n refused (%s): the record of the session before is void'
           % out.strip().splitlines()[0])
    else:
        bad('I10', 'pax\'s next session: sudo -n said %r' % out.strip())
    svc3 = stat_of(con, int(svc), 19) if svc.isdigit() else None
    if svc_stat and svc2 and svc3 and svc_stat[4] == svc2[4] == svc3[4] == '1':
        ok('I11', 'the hook\'s service, pid %s, in pid 1\'s session before the first logout and after the second' % svc)
    else:
        bad('I11', 'the service %r: %s, %s, %s' % (svc, svc_stat[:5] if svc_stat else None, svc2[:5] if svc2 else None,
                                                    svc3[:5] if svc3 else None))
    # I9: Ctrl-D at an empty prompt
    t0 = time.monotonic()
    con.raw(b'\x04')
    took2 = logged_out(con, 'Ctrl-D at an empty prompt', 'I9', t0)
    if took2 is not None:
        ok('I9', '`logout` (%.1f s) and Ctrl-D at an empty prompt (%.1f s) each gave `pax login:` again' % (took, took2))
    else:
        bad('I12', 'not reached: Ctrl-D gave no login prompt')
        return
    # I12: root's reboot -h, the kernel's end.
    if not login(con, 'root', 'I12'):
        return
    con.type('reboot -h')
    end = con.wait(r'^PAX: the end: [^\n]*$', 60)
    halt = con.wait(r'^halt$', 60)
    if end and halt:
        ok('I12', 'reboot -h: %s; halt' % end.group(0).decode())
    else:
        bad('I12', 'reboot -h: the end %r, halt %s: %r' % (end.group(0) if end else None, bool(halt), con.text(400)))


def boot_disk(work, img):
    """I13: two boots of one disk whose volume is `/`."""
    the_iso = iso(work, 'disk', 'quiet root=/dev/vda')
    a = Console(ARGS.out / 'boot2-disk', the_iso, str(img))
    try:
        if not login(a, 'pax', 'I13'):
            return
        out = a.command('touch $XDG_RUNTIME_DIR/left /home/pax/kept; ls -A $XDG_RUNTIME_DIR', 1) or ''
        if out.split() != ['left']:
            bad('I13', 'the first boot: the runtime directory holds %r' % out)
        a.type('sudo reboot')
        if a.wait(r'\[sudo\] password for pax: $', 30):
            a.type(PASSWORDS['pax'])
        restarted = a.wait(r'reboot\(2\): the volumes written and marked clean[^\n]*restarting', 60)
        try:
            a.q.wait(timeout=60)
        except subprocess.TimeoutExpired:
            pass
        if not restarted:
            bad('I13', 'sudo reboot: no restart line: %r' % a.text(400))
            return
    finally:
        a.quit()
    b = Console(ARGS.out / 'boot3-disk', the_iso, str(img))
    try:
        if not login(b, 'pax', 'I13'):
            return
        out = b.command("ls -A $XDG_RUNTIME_DIR; echo n=$?; stat -c '%u %g %a' $XDG_RUNTIME_DIR; ls /home/pax; cat /proc/self/mounts", 2) or ''
        got = [l.strip() for l in out.splitlines()]
        root = [l for l in got if l.split()[1:3] in (['/', 'ext2'], ['/', 'ext3'])]
        run_ = [l for l in got if l.split()[1:3] == ['/run', 'tmpfs']]
        b.type('sudo poweroff')
        if b.wait(r'\[sudo\] password for pax: $', 30):
            b.type(PASSWORDS['pax'])
        try:
            rc = b.q.wait(timeout=120)
        except subprocess.TimeoutExpired:
            rc = None
        if got[:3] == ['n=0', '1000 1000 700', 'kept'] and root and run_ and rc == 0:
            ok('I13', '/ on the disk (%s); after sudo reboot the runtime directory is empty, pax\'s 0700, on %s; '
               'the home\'s file kept; sudo poweroff ended QEMU 0' % (root[0], run_[0]))
        else:
            bad('I13', 'the second boot: %r; / %r; /run %r; QEMU at poweroff %r' % (got[:4], root, run_, rc))
    finally:
        b.quit()


def main():
    global ARGS
    a = argparse.ArgumentParser()
    for k in ('images', 'elf', 'tier', 'leg', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    ARGS = a.parse_args()
    ARGS.images = pathlib.Path(ARGS.images)
    ARGS.out = pathlib.Path(ARGS.out)
    if ARGS.out.exists():
        shutil.rmtree(ARGS.out)
    ARGS.out.mkdir(parents=True)
    work = ARGS.out / 'work'
    work.mkdir()
    missing = (ARGS.images / 'missing.txt').read_text().strip() if (ARGS.images / 'missing.txt').exists() else ''
    if missing:
        say('the tree has no %s' % missing)
    make_shadow(work)
    the_iso = iso(work, 'image', 'quiet')
    con = Console(ARGS.out / 'boot1', the_iso)
    try:
        boot1(con)
    except Exception as e:  # a row's reading that broke is that run's red, never a silent pass
        bad('I0', 'boot 1 stopped at %s: %s; the console: %r' % (type(e).__name__, e, con.text(300)))
    finally:
        con.quit()
    if shutil.which('mke2fs') and shutil.which('debugfs') and shutil.which('e2fsck'):
        try:
            img = disk(work)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            bad('I13', 'the disk could not be made: %s' % e)
        else:
            try:
                boot_disk(work, img)
            except Exception as e:
                bad('I13', 'the disk\'s boots stopped at %s: %s' % (type(e).__name__, e))
    else:
        say('SKIPPED LOUDLY I13: no mke2fs, debugfs or e2fsck on this host')
    for p in sorted(ARGS.out.rglob('*')):
        if p.is_file() and p.suffix not in ('.iso', '.img', '.cpio') and p.stat().st_size < 64 << 20:
            data = p.read_bytes()
            for k, v in PASSWORDS.items():
                if v.encode() in data:
                    bad('I0', 'a password (%s\'s) reached %s' % (k, p.relative_to(ARGS.out)))
    say('%s' % ('FAIL ' + ' '.join(sorted(set(FAILS))) if FAILS else 'PASS'))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
