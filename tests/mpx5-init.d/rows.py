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

Lifecycle boots, a boot each, independent of I4 and of each other:
  I14 observe a live adopted setsid child (PPid=1), release it, then require
      ENOENT within 5000 guest monotonic milliseconds without logging out.
      Missing observations and inspection errors fail, never mean reaped.
  I15 root literally executes `exec /bin/login` and authenticates again;
      boot hooks and boot-status recording each remain at one call, the
      service and pid 1 identities stay unchanged, and a sudo-record
      sentinel survives. The fixture counts boot-status invocations only.
  I16 the login records across a console logout (utmp(5): when init finds
      that a session's process has ended it marks its utmp entry
      DEAD_PROCESS): root logs in, `exit`s, and 3 s after `login:` logs in
      again; `last -R -e --time-format iso` (tools/mklogd's last) shows two
      sessions of root on one line, the newer still logged in, the older
      ended `[logout]` at least 2 s before the newer began (a session closed
      only by the next login on its line ends at that login's time), and one
      `reboot` line: the boot's record, written once.

Alpha boots (pax.services= on the kernel command line, after `quiet`), a boot each:
  I17 `pax.services=alpha`, the tree's /bin/alpha: one process whose comm is
      `alpha`, its parent 1, its process group its own pid, its session 1
      (init's: a job, never a session leader); its descriptors 0 /dev/null, 1
      and 2 /dev/kmsg; `alpha list --format=1` answers (status 0); the
      suite's hook `svc` (no unit of its name) ran once; /proc/1/cmdline still
      `/bin/init`.
  I18 the same boot: root SIGKILLs alpha (the pid of its own first line on
      the serial log, `manager … pid N`): init's line `init: /bin/alpha ended
      (killed by signal 9); again in 1 s`, and a new alpha (a second
      `manager … pid M` line, M not N) within 10 s of it (1 s, and the TCG
      margin); `svc` not run again.
  I22 the same boot: root's `reboot -h`: alpha's `stopping every unit (TERM)`
      and `exit 0` on the serial log before the kernel's `PAX: the end:` line,
      which names no SIGKILL (nor any `PAX: SIGKILL at the end:` line), and no
      `init: /bin/alpha ended` after the reboot was typed.
  I19 `pax.services=alpha` with no /bin/alpha in the tree: one `init:` line
      naming /bin/alpha, and the hooks run (`svc: started`).
  I20 `pax.services=alpha`, /bin/alpha a pelt script that exits 2 at once:
      one `init:` line naming its status, `svc: started` once, and no `again
      in` line within 15 s (alpha is not started again).
  I21 no word (boot 1) and `pax.services=hooks`: no process whose comm is
      `alpha`, and the hooks as today (`svc: started`).

Exit 0 when every selected row held, 1 otherwise. A row that cannot be reached (the
machine halted at a logout) fails by name with what the console said.
"""
import argparse
import calendar
import json
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
        raise RuntimeError('%s: exit %d: %s %s' % (argv[0], r.returncode, r.stdout.decode(errors='replace')[-300:],
                                                  r.stderr.decode(errors='replace')[-300:]))
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


def iso(work, name, cmdline, rows=None):
    conf = work / (name + '.conf')
    text = (ROOT / 'boot/limine-initramfs-quiet.conf').read_text()
    conf.write_text(text.replace('cmdline: quiet', 'cmdline: ' + cmdline))
    run([ROOT / 'tools/mkinitramfs', work / (name + '.cpio')] + (files(work) if rows is None else rows))
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
    attrs = {'/': (0o040755, 0, 0)}  # debugfs's `sif … mode` takes the whole mode, the type's bits too
    for d in ('dev', 'proc', 'sys'):
        (stage / d).mkdir()
        attrs['/' + d] = (0o040755, 0, 0)
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


def login(con, who, row, prompted=False):
    """`who` logs in at `pax login:` (already read when `prompted`: a logout's
    row waited for it); the shell's prompt. False (and the row red) when a
    prompt does not come."""
    if not prompted and not con.wait(r'login: $', 60):
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
    # I21, the no-word half: no alpha process (the hooks ran: I11's `svc: started` above)
    NO_WORD['alpha'] = alpha_pids(con, 90)
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
    # I12: root's reboot -h, the kernel's end (the prompt Ctrl-D gave, read above).
    if not login(con, 'root', 'I12', prompted=True):
        return
    con.type('reboot -h')
    end = con.wait(r'^PAX: the end: [^\n]*\n', 60)
    halt = con.wait(r'^halt$', 60)
    if end and halt:
        ok('I12', 'reboot -h: %s; halt' % end.group(0).decode().strip())
    else:
        bad('I12', 'reboot -h: the end %r, halt %s: %r' % (end.group(0) if end else None, bool(halt), con.text(400)))


def boot_disk(work, img):
    """I13: two boots of one disk whose volume is `/`."""
    the_iso = iso(work, 'disk', 'quiet root=/dev/vda rw')  # rw: without it / mounts read-only, as Linux's
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


def proc_fields(line):
    """Strict stat parsing: a missing/failed observation is never absence."""
    at = line.rfind(') ')
    if at < 0 or ' (' not in line[:at]:
        raise ValueError('not a proc stat: %r' % line)
    fields = [line.split(' ', 1)[0]] + line[at + 2:].split()
    if (len(fields) < 21 or len(fields[1]) != 1 or fields[1] not in 'RSDZTtWXxIKP'
            or any(not fields[i].isdigit() for i in (0, 2, 4, 20))):
        raise ValueError('incomplete proc stat: %r' % line)
    return fields


def console_identity(con, n):
    out = con.command('echo $$; cat /proc/1/stat', n)
    lines = out.strip().splitlines() if out is not None else []
    if len(lines) != 2 or not lines[0].isdigit():
        raise ValueError('unreadable console identity: %r' % out)
    init = proc_fields(lines[1])
    if init[0] != '1' or init[1] == 'Z':
        raise ValueError('pid 1 not alive: %r' % out)
    return lines[0], init[20]


def orphan_before_logout(con):
    if not login(con, 'pax', 'I14'):
        return
    before = console_identity(con, 140)
    path = '/tmp/init-orphan-release'
    out = con.command('orphan ' + path, 141)
    m = re.fullmatch(r'READY ([1-9][0-9]*) ([1-9][0-9]*)\s*', out or '')
    if not m or m[1] != m[2]:
        bad('I14', 'no valid child handshake: %r' % out)
        return
    pid = m[1]
    observed = con.command('orphan inspect ' + pid, 142)
    if observed is None or not observed.startswith('PRESENT '):
        bad('I14', 'missing initial live observation of %s: %r' % (pid, observed))
        return
    child = proc_fields(observed[len('PRESENT '):].strip())
    if child[0] != pid or child[1] not in ('S', 'R') or child[2] != '1' or child[4] != pid:
        bad('I14', 'not a live adopted child in its own session: %r' % observed)
        return
    result = con.command('orphan release %s %s; echo ORPHAN-RC=$?' % (pid, path), 143, timeout=30)
    after = console_identity(con, 144)
    expected = ['GONE ' + pid, 'ORPHAN-RC=0']
    if result is not None and result.strip().splitlines() == expected and after == before:
        ok('I14', 'observed live child %s PPid=1 SID=%s; reaped within 5000 guest ms before any logout; '
           'console shell %s and pid 1 unchanged' % (pid, pid, before[0]))
    else:
        bad('I14', 'observed live child %s PPid=1 SID=%s; release/check %r; console identities %r -> %r'
            % (pid, pid, result, before, after))


def second_start_snapshot(con, n):
    out = con.command('echo HOOK; cat /var/log/init-hook.calls; echo STATUS; cat /var/log/init-boot.calls; '
                      'echo SERVICE; p=$(cat /run/svc.pid); echo $p; cat /proc/$p/stat; '
                      'echo SENTINEL; cat /var/run/sudo/ts/init-second-start; echo DONE', n)
    if out is None:
        raise ValueError('no second-start snapshot')
    sections = {}
    name = None
    for line in out.strip().splitlines():
        if line in ('HOOK', 'STATUS', 'SERVICE', 'SENTINEL', 'DONE'):
            if line in sections:
                raise ValueError('duplicate snapshot section: %r' % out)
            name = line
            sections[name] = []
        elif name is not None:
            sections[name].append(line)
        else:
            raise ValueError('unreadable snapshot: %r' % out)
    if set(sections) != {'HOOK', 'STATUS', 'SERVICE', 'SENTINEL', 'DONE'} or sections['DONE']:
        raise ValueError('incomplete snapshot: %r' % out)
    service = sections['SERVICE']
    if len(service) != 2 or not service[0].isdigit():
        raise ValueError('unreadable service: %r' % service)
    st = proc_fields(service[1])
    if st[0] != service[0] or st[1] not in ('S', 'R'):
        raise ValueError('service is not alive: %r' % service)
    return sections['HOOK'], sections['STATUS'], (st[0], st[20]), sections['SENTINEL']


def second_start(con):
    if not login(con, 'root', 'I15'):
        return
    identity = console_identity(con, 150)
    made = con.command('echo keep > /var/run/sudo/ts/init-second-start; echo CREATED=$?', 151)
    if made is None or made.strip() != 'CREATED=0':
        bad('I15', 'could not establish timestamp sentinel: %r' % made)
        return
    before = second_start_snapshot(con, 152)
    if before[0] != ['hook'] or before[1] != ['record'] or before[3] != ['keep']:
        bad('I15', 'initial boot duties not observed exactly once: %r' % (before,))
        return
    con.type('exec /bin/login')
    if not login(con, 'root', 'I15'):
        return
    after = second_start_snapshot(con, 153)
    identity2 = console_identity(con, 154)
    if before == after and identity == identity2:
        ok('I15', 'exec /bin/login: hook and boot-status each called once, service %s and pid 1 unchanged, '
           'sudo timestamp sentinel kept; console shell %s' % (before[2][0], identity[0]))
    else:
        bad('I15', 'exec /bin/login repeated boot duties: hook/status/service/sentinel %r -> %r; '
            'console identities %r -> %r' % (before, after, identity, identity2))


ISO_STAMP = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00')


def stamps(line):
    """The ISO times on a `last --time-format iso` line, in seconds since the epoch."""
    return [calendar.timegm(time.strptime(t, '%Y-%m-%dT%H:%M:%S+00:00')) for t in ISO_STAMP.findall(line)]


def logout_verdict(out):
    """I16's reading of `last -R -e --time-format iso`: (held, why). A reading
    that is not two sessions of root on one line and one boot is red."""
    lines = [l for l in (out or '').splitlines() if l.strip()]
    roots = [l for l in lines if l.split()[0] == 'root']
    boots = [l for l in lines if l.split()[0] == 'reboot']
    shown = ' | '.join(lines)
    if len(roots) != 2 or len(boots) != 1:
        return False, 'want two sessions of root and one boot: %r' % shown
    newer, older = roots
    t_new, t_old = stamps(newer), stamps(older)
    same_line = newer.split()[1] == older.split()[1]
    if not (same_line and len(t_new) == 1 and 'still logged in' in newer and len(t_old) == 2):
        return False, 'the login records after a logout: %r' % shown
    if t_old[1] == t_new[0]:
        return False, 'no record of the logout: root\'s first session ends at the next login\'s start: %r' % shown
    if older.rstrip().endswith('[logout]') and t_old[1] <= t_new[0] - 2:
        return True, ('the logout is its own record: root on %s ended [logout] %d s before the next login; '
                      'one boot record' % (older.split()[1], t_new[0] - t_old[1]))
    return False, 'the logout\'s record: %r' % shown


def logout_record(con):
    if not login(con, 'root', 'I16'):
        return
    con.type('exit')
    if not con.wait(r'login: $', 15) or not con.running():
        bad('I16', 'no `login:` after root\'s exit: %r' % con.text(300))
        return
    time.sleep(3)
    if not login(con, 'root', 'I16', prompted=True):
        return
    out = con.command('last -R -e --time-format iso', 160)
    if out is None:
        bad('I16', 'last printed nothing between its marks: %r' % con.text(300))
        return
    held, why = logout_verdict(out)
    (ok if held else bad)('I16', why)


def lifecycle_boots(the_iso):
    for row, check in (('I14', orphan_before_logout), ('I15', second_start), ('I16', logout_record)):
        con = Console(ARGS.out / ('boot-' + row), the_iso)
        try:
            check(con)
        except Exception as e:
            bad(row, '%s: %s; console %r' % (type(e).__name__, e, con.text(300)))
        finally:
            con.quit()


NO_WORD = {}


def alpha_pids(con, n):
    """An explicitly complete enumeration; failed reads never mean absence."""
    out = con.command('echo BEGIN-ALPHA; r=0; for d in /proc/[0-9]*; do '
                      'if [ ! -e "$d/comm" ]; then continue; fi; c=; '
                      'if read c < "$d/comm"; then '
                      'if [ "$c" = alpha ]; then echo "A=${d#/proc/}"; fi; '
                      'else r=1; fi; done; echo END-ALPHA $r', n)
    lines = out.splitlines() if out is not None else []
    if not lines or lines[0] != 'BEGIN-ALPHA' or lines[-1] != 'END-ALPHA 0':
        raise ValueError('incomplete alpha enumeration: %r' % out)
    middle = lines[1:-1]
    if any(not re.fullmatch(r'A=[1-9][0-9]*', l) for l in middle) or len(set(middle)) != len(middle):
        raise ValueError('malformed alpha enumeration: %r' % out)
    return [int(l[2:]) for l in middle]


def check_cmdline(con, row):
    """Confirm this boot's actual newline-terminated kernel interface."""
    expected = getattr(con, 'expected_cmdline', None)
    if expected is None:  # Mocked direct driver calls have no real boot.
        return
    got = con.command('cat /proc/cmdline; echo CMDLINE-RC=$?', 190)
    if got is None or got.splitlines() != [expected, 'CMDLINE-RC=0']:
        raise ValueError('%s command-line prerequisite: got %r, wanted %r plus LF' % (row, got, expected))


def seen_after(con, start, pattern, timeout):
    """The first match of `pattern` anywhere in the transcript after byte `start`, waited for up to `timeout`
    seconds (the cursor untouched: alpha's records and the console's lines reach the wire in either order)."""
    rx = re.compile(pattern.encode() if isinstance(pattern, str) else pattern, re.M)
    end = time.monotonic() + timeout
    while True:
        m = rx.search(con.seen, start)
        if m or time.monotonic() >= end or not con.running():
            return m
        con.pump(0.1)


def alpha_tree(work, alpha):
    """files() with /bin/alpha as `alpha` says: 'real' (the tree's), 'none' (left out), 'stub' (exits 2)."""
    rows = [l for l in files(work) if not l.startswith('/bin/alpha=')]
    if alpha == 'real':
        return files(work)
    if alpha in ('stub', 'stub1', 'noexec'):
        code = 1 if alpha == 'stub1' else 2
        stub = work / ('alpha-' + alpha)
        stub.write_text('#!/bin/pelt\nexit %d\n' % code)
        os.chmod(stub, 0o755 if alpha != 'noexec' else 0o644)
        rows.append('/bin/alpha=%s:%s' % (stub, '755' if alpha != 'noexec' else '644'))
    return rows


def alpha_boot(con):
    """I17, I18 and I22: pax.services=alpha, the tree's /bin/alpha."""
    first = seen_after(con, 0, r'manager [0-9][^ \n]* pid ([0-9]+) root /', 180)
    hook = seen_after(con, 0, r'svc: started\n', 180)
    if not first:
        bad('I17', 'no `manager … pid N root /` line from alpha on the serial log: %r' % con.text(600))
    if not hook:
        bad('I17', 'the boot hook never ran (no `svc: started`): %r' % con.text(600))
    if not login(con, 'root', 'I17'):
        bad('I18', 'not reached: I17 could not log in')
        return
    check_cmdline(con, 'I17')
    pids = alpha_pids(con, 170)
    if not pids or len(pids) != 1:
        bad('I17', 'one alpha process wanted; /proc/*/comm gave %r' % pids)
        bad('I18', 'not reached: no unique live alpha to restart')
        return
    pid = pids[0]
    out = con.command("cat /proc/%d/stat; ls -l /proc/%d/fd/0 /proc/%d/fd/1 /proc/%d/fd/2; "
                      "alpha list --format=1 > /tmp/list.json; echo status=$?; cat /var/log/init-hook.calls; "
                      "tr '\\0' ' ' < /proc/1/cmdline; echo" % (pid, pid, pid, pid), 171) or ''
    lines = [l.strip() for l in out.strip().splitlines()]
    why = []
    st = proc_fields(lines[0]) if lines else []
    if not st or st[0] != str(pid) or st[1] not in ('S', 'R') or st[2:5] != ['1', str(pid), '1']:
        why.append('not a live alpha with parent 1, own group and session 1: %r' % st)
    listing = con.command('alpha list --format=1; echo LIST-RC=$?', 191)
    try:
        parts = listing.splitlines()
        reply = json.loads('\n'.join(parts[:-1]))
        if parts[-1] != 'LIST-RC=0' or reply.get('v') != 1 or reply.get('ok') is not True or not isinstance(reply.get('units'), list):
            raise ValueError('not a successful format-1 list')
    except (AttributeError, IndexError, TypeError, ValueError) as e:
        why.append('invalid list response: %s: %r' % (e, listing))
    for fd, target in (('0', '/dev/null'), ('1', '/dev/kmsg'), ('2', '/dev/kmsg')):
        if not any(re.search(r'/fd/%s -> %s$' % (fd, re.escape(target)), l) for l in lines):
            why.append('fd %s is not %s' % (fd, target))
    if 'status=0' not in lines:
        why.append('`alpha list --format=1` did not answer (%r)' % [l for l in lines if l.startswith('status=')])
    if lines.count('hook') != 1:
        why.append('the hook ran %d times' % lines.count('hook'))
    if '/bin/init' not in lines:
        why.append('/proc/1/cmdline is not /bin/init')
    if first and int(first.group(1)) != pid:
        why.append('alpha\'s own line says pid %s, /proc says %d' % (first.group(1).decode(), pid))
    if why:
        bad('I17', '; '.join(why) + ': %r' % out[-600:])
    else:
        ok('I17', 'alpha pid %d: parent 1, its own group, session 1; 0 /dev/null, 1 and 2 /dev/kmsg; `alpha list` answers; '
                  '`svc` ran once; pid 1 is /bin/init' % pid)
    if getattr(ARGS, 'rows', 'all') == 'alpha-smoke':
        return
    # The guest clock is taken immediately before SIGKILL, not on host log receipt.
    mark = len(con.seen)
    killed = con.command('init-clock %d; echo KILL-RC=$?' % pid, 192)
    km = re.fullmatch(r'KILL-MS ([0-9]+)\nKILL-RC=0\n', killed or '')
    line = seen_after(con, mark, r'init: /bin/alpha ended \(killed by signal 9\); again in 1 s', 30)
    again = seen_after(con, mark, r'manager [0-9][^ \n]* pid ([0-9]+) root /', 40)
    hooks = con.command('cat /var/log/init-hook.calls', 172) or ''
    why = []
    took = None
    if not km:
        why.append('no successful timestamped guest kill: %r' % killed)
    if not line:
        why.append('no `init: /bin/alpha ended (killed by signal 9); again in 1 s` line')
    if not again or int(again.group(1)) == pid:
        why.append('no new alpha (`manager … pid M`, M not %d)' % pid)
    else:
        new_pid = int(again.group(1))
        live = alpha_pids(con, 193)
        raw = con.command('cat /proc/%d/stat' % new_pid, 194)
        st2 = proc_fields((raw or '').strip())
        if live != [new_pid] or st2[0] != str(new_pid) or st2[1] not in ('S', 'R') or st2[2:5] != ['1', str(new_pid), '1']:
            why.append('replacement is not the unique live job of pid 1: %r %r' % (live, st2))
        if km:
            took = int(st2[20]) * 10 - int(km[1])
            if not 500 <= took <= 10000:
                why.append('guest restart delay %d ms outside [500,10000], 10 ms tick grain' % took)
    if hooks.split().count('hook') != 1:
        why.append('the hook ran %d times' % hooks.split().count('hook'))
    if why:
        bad('I18', '; '.join(why) + ': %r' % con.text(600))
    else:
        ok('I18', 'SIGKILL to %d: unique replacement %s after %d guest ms; hook not rerun' % (
            pid, again.group(1).decode(), took))
    # I22 runs on its own fresh boot: a restart plant must not remove its manager.


def alpha_shutdown_verdict(after, halted):
    end = re.search(rb'^PAX: the end: [^\n]*\n', after, re.M)
    if not end or not halted:
        return False, 'missing kernel end or real halt'
    before = after[:end.start()]
    if not re.search(rb'^(?:<\d+>)?alpha: @\d+ stopping every unit \(TERM\)$', before, re.M):
        return False, 'missing alpha TERM record before kernel end'
    if not re.search(rb'^(?:<\d+>)?alpha: @\d+ exit 0$', before, re.M):
        return False, 'missing alpha exit 0 before kernel end'
    if b'SIGKILL' in end.group(0) or b'PAX: SIGKILL at the end:' in after:
        return False, 'kernel end required SIGKILL'
    if b'init: /bin/alpha ended' in after:
        return False, 'init restarted alpha during shutdown'
    return True, 'alpha stopped and exited before kernel end; real halt observed'


def alpha_shutdown(con):
    """I22 alone, independent of the restart check's boot."""
    if not login(con, 'root', 'I22'):
        return
    check_cmdline(con, 'I22')
    if len(alpha_pids(con, 220)) != 1:
        bad('I22', 'not reached: no unique live alpha to shut down')
        return
    mark = len(con.seen)
    con.type('reboot -h')
    end = seen_after(con, mark, r'^PAX: the end: [^\n]*\n', 90)
    halted = bool(seen_after(con, mark, r'^halt$', 60)) if end else False
    held, why = alpha_shutdown_verdict(con.seen[mark:], halted)
    (ok if held else bad)('I22', why)


def alpha_fallback(con, row, want):
    """I19 and I20: the console's own lines, no login: init's one line `want`, the hook once, no start again."""
    if not login(con, 'root', row):
        return
    check_cmdline(con, row)
    line = seen_after(con, 0, want, 20)
    hook = seen_after(con, 0, r'svc: started\n', 20)
    until = time.monotonic() + 15
    while time.monotonic() < until and con.running():
        con.pump(0.1)
    why = []
    if alpha_pids(con, 195):
        why.append('a manager remains after fallback')
    if not line:
        why.append('no init line matching %r' % want)
    elif len(re.findall(want.encode(), con.seen, re.M)) != 1:
        why.append('init\'s line %d times' % len(re.findall(want.encode(), con.seen, re.M)))
    if not hook or con.seen.count(b'svc: started\n') != 1:
        why.append('`svc: started` %d times' % con.seen.count(b'svc: started\n'))
    if b'again in' in con.seen:
        why.append('init starts /bin/alpha again (`again in`)')
    if why:
        bad(row, '; '.join(why) + ': %r' % con.text(600))
    else:
        ok(row, '%s; the hooks ran once; no start again' % line.group(0).decode().strip())


def hooks_boot(con):
    """I21's word half: pax.services=hooks."""
    hook = seen_after(con, 0, r'svc: started\n', 180)
    if not login(con, 'pax', 'I21'):
        return None
    check_cmdline(con, 'I21')
    return {'alpha': alpha_pids(con, 180), 'hook': bool(hook)}


def base_boot(con):
    """The red checkpoint's dry: real init, kernel cmdline and static alpha."""
    if not login(con, 'root', 'D0'):
        return
    check_cmdline(con, 'D0')
    out = con.command("tr '\\0' ' ' < /proc/1/cmdline; echo; alpha --version; echo VERSION-RC=$?", 196)
    if out is None or out.splitlines() != ['/bin/init ', 'alpha 0.0.0', 'VERSION-RC=0']:
        bad('D0', 'real init/static alpha not established: %r' % out)
    else:
        ok('D0', 'real pinned init, static alpha and kernel command-line interface')


def selection_boot(con, expect_alpha, invalid=False):
    if not login(con, 'root', 'I23'):
        return
    check_cmdline(con, 'I23')
    pids = alpha_pids(con, 197)
    held = len(pids) == 1 if expect_alpha else pids == []
    diagnostic = b'init: pax.services=wrong: neither alpha nor hooks; hooks'
    if held and con.seen.count(diagnostic) == int(invalid):
        ok('I23', 'literal first matching word selects %s; diagnostic count %d' % (
            'alpha' if expect_alpha else 'hooks', int(invalid)))
    else:
        bad('I23', 'selection gave pids %r and diagnostic count %d' % (pids, con.seen.count(diagnostic)))


def fixture_tree(work, mode):
    """Test-only disabled units and hooks, never installed by distribution-root."""
    rows = alpha_tree(work, 'real' if mode == 'real' else 'stub')
    for name, dest in (('vendor-test', '/usr/lib/alpha/units'), ('admin-test', '/etc/alpha/units')):
        unit = work / (name + '.unit')
        unit.write_text('alpha = 1\nenable = false\n[run]\nexec = ["/bin/sleep", "1"]\n')
        hook = work / (name + '.hook')
        hook.write_text('#!/bin/pelt\necho %s >> /var/log/replaced.calls\n' % name)
        rows += ['%s/%s.unit=%s:644' % (dest, name, unit), '/etc/pax-boot.d/%s=%s:755' % (name, hook)]
    boot = work / 'fixture-boot-status'
    boot.write_text('#!/bin/pelt\necho "$*" >> /var/log/init-boot.calls\n'
                    '/bin/mkdir -p /run/alpha\necho stale > /run/alpha/state\n')
    rows = [r for r in rows if not r.startswith('/bin/pax-boot-status=')]
    rows.append('/bin/pax-boot-status=%s:755' % boot)
    if mode == 'real':
        binary = next(r for r in rows if r.startswith('/bin/alpha='))
        rows = [r for r in rows if not r.startswith('/bin/alpha=')]
        rows.append(binary.replace('/bin/alpha=', '/usr/lib/fixture/alpha=', 1))
        wrapper = work / 'fixture-alpha'
        wrapper.write_text('#!/bin/pelt\nif [ -e /run/alpha/state ]; then echo stale; else echo clean; fi '
                           '> /run/alpha-state-check\nexec /usr/lib/fixture/alpha "$@"\n')
        rows.append('/bin/alpha=%s:755' % wrapper)
    return rows


def fixture_boot(con, real):
    selected = ('I24', 'I25') if real else ('I26',)
    if not login(con, 'root', selected[0]):
        for row in selected[1:]:
            bad(row, 'not reached: fixture login failed')
        return
    check_cmdline(con, selected[0])
    pids = alpha_pids(con, 198)
    out = con.command('if [ -e /var/log/replaced.calls ]; then cat /var/log/replaced.calls; fi; '
                      'echo LOCAL; cat /var/log/init-hook.calls; echo DONE', 199)
    expected = ['LOCAL', 'hook', 'DONE'] if real else ['admin-test', 'vendor-test', 'LOCAL', 'hook', 'DONE']
    held = out is not None and out.splitlines() == expected and (len(pids) == 1 if real else pids == [])
    if not real:
        held = held and con.seen.count(b'init: /bin/alpha ended with status 2 at its start;') == 1
    (ok if held else bad)(selected[0], 'replaced and local hooks: %r; alpha pids %r' % (out, pids))
    if real:
        state = con.command('cat /run/alpha-state-check', 200)
        (ok if state == 'clean\n' and len(pids) == 1 else bad)('I25', 'state before first exec: %r' % state)


def alpha_boots(work):
    cases = [
        ('alpha', 'quiet pax.services=alpha', 'real', alpha_boot, ('I17', 'I18')),
        ('alpha-shutdown', 'quiet pax.services=alpha', 'real', alpha_shutdown, ('I22',)),
        ('alpha-none', 'quiet pax.services=alpha', 'none',
         lambda c: alpha_fallback(c, 'I19', r'^init: [^\n]*/bin/alpha[^\n]*\n'), ('I19',)),
        ('alpha-noexec', 'quiet pax.services=alpha', 'noexec',
         lambda c: alpha_fallback(c, 'I19', r'^init: /bin/alpha not started[^\n]*\n'), ('I19',)),
        ('alpha-exit1', 'quiet pax.services=alpha', 'stub1',
         lambda c: alpha_fallback(c, 'I20', r'^init: /bin/alpha ended with status 1[^\n]*\n'), ('I20',)),
        ('alpha-exit2', 'quiet pax.services=alpha', 'stub',
         lambda c: alpha_fallback(c, 'I20', r'^init: /bin/alpha ended with status 2[^\n]*\n'), ('I20',)),
        ('no-word', 'quiet', 'real', hooks_boot, ('I21',)),
        ('hooks', 'quiet pax.services=hooks', 'real', hooks_boot, ('I21',)),
        ('invalid', 'quiet pax.services=wrong', 'real', lambda c: selection_boot(c, False, True), ('I23',)),
        ('first-hooks', 'quiet pax.services=hooks pax.services=alpha', 'real', lambda c: selection_boot(c, False), ('I23',)),
        ('first-alpha', 'quiet pax.services=alpha pax.services=hooks', 'real', lambda c: selection_boot(c, True), ('I23',)),
        ('spaces', 'quiet  pax.services=alpha  ', 'real', lambda c: selection_boot(c, True), ('I23',)),
        ('lookalike', 'quiet xpax.services=alpha pax.services=hooksx', 'real', lambda c: selection_boot(c, False), ('I23',)),
        ('fixture-alpha', 'quiet pax.services=alpha', 'fixture-real', lambda c: fixture_boot(c, True), ('I24', 'I25')),
        ('fixture-fallback', 'quiet pax.services=alpha', 'fixture-stub', lambda c: fixture_boot(c, False), ('I26',)),
    ]
    chosen = getattr(ARGS, 'rows', 'all')
    if chosen == 'alpha-smoke':
        cases = cases[:1]
    for name, cmdline, alpha, check, selected in cases:
        rows = fixture_tree(work, 'real' if alpha == 'fixture-real' else 'stub') if alpha.startswith('fixture-') else alpha_tree(work, alpha)
        image = iso(work, name, cmdline, rows)
        con = Console(ARGS.out / ('boot-' + name), image)
        con.expected_cmdline = cmdline
        before = len(FAILS)
        try:
            got = check(con)
            if name in ('hooks', 'no-word'):
                if got and got['alpha'] == [] and got['hook']:
                    ok('I21', '%s: no alpha; local hook ran' % name)
                else:
                    bad('I21', '%s: %r' % (name, got))
        except Exception as e:
            for row in selected:
                if row not in FAILS[before:]:
                    bad(row, 'not reached or unreadable: %s: %s' % (type(e).__name__, e))
        finally:
            con.quit()


def main():
    global ARGS
    a = argparse.ArgumentParser()
    for k in ('images', 'elf', 'tier', 'leg', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--rows', choices=('all', 'lifecycle', 'alpha', 'alpha-smoke', 'base'), default='all')
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
    if ARGS.rows in ('all', 'lifecycle'):
        lifecycle_boots(the_iso)
    if ARGS.rows == 'base':
        con = Console(ARGS.out / 'boot-base-dry', the_iso)
        con.expected_cmdline = 'quiet'
        try:
            base_boot(con)
        except Exception as e:
            bad('D0', '%s: %s' % (type(e).__name__, e))
        finally:
            con.quit()
    if ARGS.rows == 'all':
        con = Console(ARGS.out / 'boot1', the_iso)
        try:
            boot1(con)
        except Exception as e:  # a broken reading is red, never a silent pass
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
    if ARGS.rows in ('all', 'alpha', 'alpha-smoke'):
        alpha_boots(work)
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
