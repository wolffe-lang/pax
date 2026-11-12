#!/usr/bin/env python3
"""rows.py — px112: burrowd on PAX, reached from the rig as from a LAN.

    rows.py --images DIR --elf KERNEL.elf --tier T --leg bios|uefi --accel A --out DIR

DIR is tests/mpx5-burrowd's P0 (files.txt, tools/mkshadow). One leg is two
boots of one image and one ext2 volume (label px112-keys, mounted on
/etc/burrowd by the image's fstab, write-through), the guest on a tap in
the rig's network namespace, leased 192.168.89.20 by dnsmasq for its MAC.
The volume holds the shipped /etc/burrowd/burrowd_config with its one
ListenAddress line made `ListenAddress 0.0.0.0`, so the rows reach the
guest from the LAN whichever default the images ship.
The rig's own sshd (the image's OpenSSH, on 192.168.89.1 port 2222, an
account `pax` with the same password line and key) is the Linux side every
held row is compared with.

The passwords (pax's, root's, lobo's, a wrong one) are made here by
Python's secrets and live in this process's memory: mkshadow hashes them
on its standard input, the rig's ssh reads them from its askpass
program's environment, the console's login reads root's from the serial
line with no echo. None is written to a file, an argument vector, a log
or a record; every record is scanned for them in memory (B9), a hit
named, never printed.

The rows, each `PASS <row> …` or `FAIL <row> …` at column 0:
  B0  the image: /bin/burrowd in it; /etc/shadow made (pax at the shipped
      cost, the others at 2^14); the ISO and the volume
  B1  boot 1: the console's `burrowd: host key 256 SHA256:… (made at this
      boot)` line before the login prompt; the key the rig's ssh is shown
      (accepted into a file of its own) has that fingerprint
  B2  publickey: `true`, `echo out; echo err >&2`, `exit 1`: stdout, stderr
      and status equal to the same through the rig's sshd
  B3  password (pax's, at the shipped cost): the same three, held alike
  B4  `id -u; id -g`: pax's 1000 and 1000
  B5  refusals, alike through both: a wrong password; root by its listed
      key and by its right password; an unlisted key; lobo, locked (`!`
      before its right password's hash), by key and by password; pax with
      ~/.ssh 0777 (StrictModes), by key; the methods list
      `publickey,password`
  B6  `exit 3` is 3; `kill -TERM $$` ends the session with 255 and
      burrowd's log names `signal TERM`
  B7  git 2.43 clones /home/pax/repo.git through burrowd (den's
      upload-pack), commits, pushes (den's receive-pack), clones again: the
      refs and every object equal to the same steps through sshd and git on
      Linux, `git fsck --full` clean; protocol v2 spoken (GIT_PROTOCOL
      through `env`)
  B8  at the console, root kills burrowd's listener (/var/run/burrowd.pid);
      a login works again within 5 s, a new pid
  B9  at the console, /var/log/burrowd.log is root's 0600 and has a line
      for each kind of login (`key SHA256:`, `key password`) and refusal;
      no password in the log, the serial transcript or any record
  B10 boot 2, the same volume: the same fingerprint with no `made at this
      boot`, and the rig's known_hosts line from boot 1 still verifies
  B12 a session without ptys, the client at a terminal: `ssh host` and
      `ssh -T host` each run the account's login shell with no pty
      (burrow's shell, px112), a line typed into it once the session has
      answered; for `ssh host` the pty refused by name and burrowd's line
      saying so, for -T neither (B9 finds both log lines); `ssh -t host`
      ends with status 255 right after the refused pty (OpenSSH's client,
      told to insist on a pty, measured on Linux too); `ssh host COMMAND`
      runs, no tty; what the client writes recorded
  B15 a bare `sudo` over ssh (px112, px124): since px124 the console is no
      terminal of pid 1's session (/bin/init gives it up before the first
      login), so a command over ssh, in that session at this burrow pin, has
      no controlling terminal: PAX's sudo refuses at once by name (`a terminal
      is required to read the password`, status 1) and burrowd answers the
      next connection. Until px124 sudo asked on the console and was stopped
      there while the client waited.
  B16 sudo over ssh as the README has it (px112, beside px115's upgrade):
      `sudo -k -S -p ''` with pax's password on standard input runs as root
      and remembers nothing, so a second session's `sudo -n` is asked. A
      plain `sudo -S` with no terminal remembers the password under its
      parent (px115's key), which is each ssh session's own shell: what a
      second session's `sudo -n` then does is recorded as measured, not held
      (until px124 the record was the console terminal's, every session's);
      `sudo -K` over ssh clears it after
  B17 the stack segment after a system call (pax#340): `/bin/sysret-ss`
      (tests/mpx5-burrowd.d/sysret-ss.c) makes a system call, reads SS and
      CS, stays in ring 3 for 200 ms across the timer's interrupts, and
      reads them again: 0x1b and 0x23 both times. SYSRETQ's SS comes from
      STAR's base; a processor that does not force its privilege bits
      leaves SS at 0x18 in ring 3, and the next interrupt's IRETQ raises
      #GP. On a processor that forces them this row cannot go red; the
      hosted job, which boots under KVM on its runner's processor, can
  B18 (px116, pax#334) a command over ssh has the console's variables with no
      `. /etc/shrc;` before it: WOLF_STD, LUPIN_STD and DEN_TLS_ROOTS are the
      values the image's /etc/shrc exports (the image's burrowd_config's
      SetEnv line, tools/system-env's), byte for byte as the rig's sshd
      given the same SetEnv line answers; then `wolf build --no-cache
      --emit=obj` of a program calling std.fs.write_text (pax#334's error
      named it) in pax's home exits 0 (the image has the dev compiler, its
      std and lupin's, no link stack). The same build with WOLF_STD taken
      away (`env -u`) is recorded beside it, not held (measured: 2, E0301,
      the method not found in lupin's std, as pax#334 found)
  B11 the stick's shape (R-px112-9, C): the live entry as pid 1
      (user/usb-login.sh), the shipped configuration (loopback), no
      /etc/shadow: its own key made at boot; the rig's ssh refused at
      connect (`Connection refused`); at the console burrow reaches
      burrowd on 127.0.0.1, which answers `Permission denied
      (publickey,password).` and logs it
  B30 (px124) an ssh session open across the console's logout: a command
      over ssh that prints, sleeps 12 s and prints again is running when root
      types `exit` at the console; the console asks `login:` again, the
      command ends with both lines and status 0, and burrowd's pid is the one
      it had before the logout (init hangs up the console's session alone)
  B31 (px124) pax's runtime directory, /run/user/1000, is there over ssh, 0700
      pax's (init made it at boot); XDG_RUNTIME_DIR over ssh is recorded, not
      held (burrowd's SetEnv line is one text for every account: unset)
  B32 (px124) `sudo -k -S -p '' /bin/poweroff` over ssh, pax's password on its
      standard input, ends boot 2: the console's end line, QEMU's status 0
B1-B10 are the installed shape: /bin/login as pid 1 (px124: it execs
/bin/init, which runs the hooks and starts the console's login) and the volume's
configuration the installer's (the shipped file's ListenAddress line made
`ListenAddress 0.0.0.0`, as user/install/prepare.lu writes it; the prepare
unit's I-burrowd-lan holds the installer to that).
Exit 0 when every row held, 1 otherwise, 3 when the rig cannot run here
(not root, no /dev/net/tun, ip, dnsmasq, mke2fs, ssh, sshd or git).
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
TAP, HOST, GUEST, MAC = 'pxbd0', '192.168.89.1', '192.168.89.20', '52:54:00:12:01:12'
SSHD_PORT = 2222
FAILS = []
ARGS = None
PASSWORDS = {}
MARK = 'BURROWD-ROW-'


def say(line):
    print(line, flush=True)


def ok(row, why):
    say('PASS %s %s' % (row, why))


def bad(row, why):
    FAILS.append(row)
    say('FAIL %s %s' % (row, why))


def run(argv, env=None, data=b'', timeout=300, check=True):
    r = subprocess.run([str(x) for x in argv], env=env, input=data, capture_output=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError('%s: exit %d: %s' % (' '.join(map(str, argv[:3])), r.returncode,
                                                r.stderr.decode(errors='replace')[-400:]))
    return r


def leaks(places):
    """The names of `places` ((name, bytes)) holding any password."""
    hits = []
    for name, data in places:
        b = data.encode() if isinstance(data, str) else data
        if any(pw.encode() in b for pw in PASSWORDS.values() if pw):
            hits.append(name)
    return hits


# ---------------------------------------------------------------- the rig

def rig_missing():
    why = []
    if os.getuid() != 0:
        why.append('not root')
    if not os.path.exists('/dev/net/tun'):
        why.append('no /dev/net/tun')
    for t in ('ip', 'dnsmasq', 'mke2fs', 'ssh', 'ssh-keygen', 'git', 'useradd', 'chpasswd'):
        if not shutil.which(t, path='/usr/sbin:/sbin:/usr/bin:/bin'):
            why.append('no ' + t)
    if not os.path.exists('/usr/sbin/sshd'):
        why.append('no /usr/sbin/sshd')
    return why


class Net:
    """The tap and dnsmasq, the rig's side of the LAN."""

    def __init__(self, out):
        self.out = out
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)
        run(['ip', 'tuntap', 'add', 'dev', TAP, 'mode', 'tap'])
        run(['ip', 'addr', 'add', HOST + '/24', 'dev', TAP])
        run(['ip', 'link', 'set', TAP, 'up'])
        log = out / 'dnsmasq.log'
        log.write_text('')
        self.p = subprocess.Popen(['dnsmasq', '--no-daemon', '--user=root', '--port=0', '--interface=' + TAP,
                                   '--bind-interfaces', '--dhcp-authoritative', '--leasefile-ro',
                                   '--dhcp-range=%s,%s,255.255.255.0,2m' % (GUEST, GUEST),
                                   '--dhcp-host=%s,%s' % (MAC, GUEST), '--dhcp-option=3,' + HOST,
                                   '--log-dhcp', '--log-facility=' + str(log)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self):
        self.p.terminate()
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)


class LinuxSide:
    """The rig's sshd on HOST:2222 serving an account `pax` (uid 1000 if
    free) with the same password line, key and repository as the guest."""

    def __init__(self, out, pax_line, pub, repo, setenv=''):
        self.dir = out / 'sshd'
        self.dir.mkdir()
        os.chmod(self.dir, 0o711)
        try:
            subprocess.run(['userdel', '-r', 'pax'], capture_output=True)
        except OSError:
            pass
        run(['useradd', '-m', '-s', '/bin/sh', 'pax'])
        run(['chpasswd', '-e'], data=('pax:%s\n' % pax_line.split(':')[1]).encode())
        home = pathlib.Path('/home/pax')
        ssh = home / '.ssh'
        ssh.mkdir(mode=0o700, exist_ok=True)
        (ssh / 'authorized_keys').write_text(pub)
        os.chmod(ssh / 'authorized_keys', 0o600)
        shutil.copytree(repo, home / 'repo.git', symlinks=True)
        run(['chown', '-R', 'pax:pax', str(home)])
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', self.dir / 'host'])
        (self.dir / 'sshd_config').write_text(
            'ListenAddress %s:%d\nHostKey %s\nPidFile %s\nPasswordAuthentication yes\nKbdInteractiveAuthentication no\n'
            'UsePAM no\nPermitRootLogin no\nStrictModes yes\nAcceptEnv GIT_PROTOCOL\nLogLevel VERBOSE\n'
            'AuthorizedKeysFile .ssh/authorized_keys\n%s'
            % (HOST, SSHD_PORT, self.dir / 'host', self.dir / 'sshd.pid', (setenv + '\n') if setenv else ''))
        pathlib.Path('/run/sshd').mkdir(exist_ok=True)
        self.log = open(self.dir / 'sshd.log', 'wb')
        self.p = subprocess.Popen(['/usr/sbin/sshd', '-D', '-e', '-f', self.dir / 'sshd_config'],
                                  stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        up = False
        while time.monotonic() < deadline and self.p.poll() is None:
            try:
                with socket.create_connection((HOST, SSHD_PORT), timeout=0.5) as c:
                    c.recv(64)
                up = True
                break
            except OSError:
                time.sleep(0.1)
        if not up:
            # The rig's own failure, named: every held row needs this sshd (the first takes: the image's
            # OpenSSH 9.6p1 refused PerSourcePenalties, which only later releases know).
            self.log.flush()
            raise SystemExit('the rig\'s sshd on %s:%d did not start: %r'
                             % (HOST, SSHD_PORT, (self.dir / 'sshd.log').read_text()[-400:]))

    def known(self):
        algo, blob = (self.dir / 'host.pub').read_text().split()[:2]
        return '[%s]:%d %s %s\n' % (HOST, SSHD_PORT, algo, blob)

    def close(self):
        self.p.terminate()
        self.p.wait(timeout=10)
        self.log.close()


# ---------------------------------------------------------------- the console

def tap_holders():
    """The pids that hold the rig's tap open: tun's fdinfo names the device (`iff:`); the rig's own
    container sees only its own processes."""
    held = set()
    for fd in pathlib.Path('/proc').glob('[0-9]*/fdinfo/*'):
        try:
            if ('iff:\t%s\n' % TAP) in fd.read_text():
                held.add(int(fd.parent.parent.name))
        except (OSError, ValueError):
            pass
    return held


def tap_released(timeout=30):
    """Waits until no process holds the tap; one still holding it after `timeout` s (a QEMU that
    outlived its wrapper, the rig's own) is killed. Returns what was killed."""
    end = time.monotonic() + timeout
    while tap_holders() and time.monotonic() < end:
        time.sleep(0.1)
    killed = sorted(tap_holders())
    for pid in killed:
        try:
            os.kill(pid, 9)
        except OSError:
            pass
    end = time.monotonic() + 10
    while tap_holders() and time.monotonic() < end:
        time.sleep(0.1)
    return killed


class Console:
    """QEMU through tools/qemu-run, COM1 on two FIFOs: the transcript read
    as it comes, lines typed a byte every 20 ms. Each boot starts with the tap
    let go by the boot before it, and quit() returns only once QEMU has let go of
    it: tools/qemu-run, terminated, ends before its QEMU does, and a boot that
    found the tap still held died at once (`could not configure /dev/net/tun
    (pxbd0): Device or resource busy`), an empty console."""

    def __init__(self, out, iso, drive):
        self.qlog = out / 'run' / 'com1.out.qemu.log'
        stale = tap_released()
        if stale:
            say('rig: the tap was still held by pid %s before this boot; killed' % stale)
        self.run = out / 'run'
        self.run.mkdir(mode=0o700, exist_ok=True)
        self.out_fifo, self.in_fifo, self.mon = (self.run / n for n in ('com1.out', 'com1.in', 'monitor'))
        for f in (self.out_fifo, self.in_fifo):
            if f.exists():
                f.unlink()
            os.mkfifo(f, 0o600)
        self.rfd = os.open(self.out_fifo, os.O_RDWR | os.O_NONBLOCK)
        self.wfd = os.open(self.in_fifo, os.O_RDWR)
        self.log = open(out / 'serial.log', 'wb')
        self.seen = b''
        self.cursor = 0
        cmd = [ROOT / 'tools/qemu-run', '--firmware', ARGS.leg, '--accel', ARGS.accel, '--timeout', '1500',
               '--serial', self.out_fifo, '--serial-input', self.in_fifo] + (['--drive', drive] if drive else []) + [iso, '--',
               '-monitor', 'unix:%s,server=on,wait=off' % self.mon, '-m', '1024M',
               '-netdev', 'tap,id=n0,ifname=%s,script=no,downscript=no' % TAP,
               '-device', 'virtio-net-pci,netdev=n0,mac=' + MAC]
        self.q = subprocess.Popen([str(x) for x in cmd], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

    def silent(self):
        """'' while the machine has written to its console; else why it never booted (QEMU's own
        words from tools/qemu-run's log), so a row cannot read an empty console as a missing line."""
        if self.seen.strip():
            return ''
        try:
            words = self.qlog.read_text(errors='replace').strip()[-300:]
        except OSError:
            words = ''
        return 'the machine never booted (its console is empty; QEMU: %r)' % (words or 'nothing')

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

    def text(self):
        return self.seen.decode(errors='replace')

    def wait(self, pattern, timeout=240):
        """The first match of the regular expression after the cursor; the
        cursor moves past it. None after `timeout` seconds or QEMU's end."""
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

    def type(self, line, secret=False):
        time.sleep(0.2)
        for ch in line.encode() + b'\r':
            os.write(self.wfd, bytes([ch]))
            time.sleep(0.02)

    def command(self, line, n, timeout=120):
        """Types `line; echo MARK$((n))`-shaped words so the marker's output
        (MARK<n>) is not its echo; the output between the echo and the mark."""
        start = len(self.seen)
        self.type('%s; echo %s$((%d+0))' % (line, MARK, n))
        m = self.wait(r'^%s%d$' % (MARK, n), timeout)
        if not m:
            return None
        body = self.seen[start:m.start()].decode(errors='replace')
        return body.split('\n', 1)[1] if '\n' in body else ''

    def quit(self, halt_timeout=60):
        """Waits for `halt` (or `halt_timeout`), then quits QEMU."""
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
        stale = tap_released()
        if stale:
            say('rig: QEMU outlived tools/qemu-run and held the tap; killed pid %s' % stale)
        self.pump(0.2)
        self.log.close()
        os.close(self.rfd)
        os.close(self.wfd)


# ---------------------------------------------------------------- ssh from the rig

class Client:
    def __init__(self, out):
        self.dir = out / 'client'
        self.dir.mkdir()
        os.chmod(self.dir, 0o700)
        self.key = self.dir / 'id_pax'
        self.other = self.dir / 'id_other'
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'px112-row', '-f', self.key])
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'px112-other', '-f', self.other])
        self.kh = self.dir / 'known_hosts'
        self.kh.write_text('')
        self.askpass = self.dir / 'askpass'
        self.askpass.write_text('#!/bin/sh\n# The rows\' askpass: the answer from the environment only.\n'
                                'printf \'%s\\n\' "$PX112_ANSWER"\n')
        os.chmod(self.askpass, 0o755)
        self.n = 0

    def pub(self, which='pax'):
        return (pathlib.Path(str(self.key if which == 'pax' else self.other) + '.pub')).read_text()

    def env(self, answer=None):
        e = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(self.dir), LC_ALL='C')
        if answer is not None:
            e.update(SSH_ASKPASS=str(self.askpass), SSH_ASKPASS_REQUIRE='force', PX112_ANSWER=answer)
        return e

    def ssh(self, where, args, user='pax', key='pax', password=None, prompts=1, timeout=120, kh=None, data=None):
        host, port = where
        argv = ['ssh', '-F', 'none', '-o', 'UserKnownHostsFile=%s' % (kh or self.kh), '-o', 'StrictHostKeyChecking=yes',
                '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=20', '-p', str(port), '-l', user]
        if password is None:
            argv += ['-o', 'BatchMode=yes', '-o', 'PreferredAuthentications=publickey',
                     '-i', self.key if key == 'pax' else self.other]
        else:
            argv += ['-o', 'BatchMode=no', '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
                     '-o', 'NumberOfPasswordPrompts=%d' % prompts]
        io = dict(stdin=subprocess.DEVNULL) if data is None else dict(input=data)
        r = subprocess.run([str(x) for x in argv + [host] + list(args)], **io,
                           capture_output=True, timeout=timeout, env=self.env(password))
        port_s = str(port).encode()
        return (r.returncode, r.stdout, r.stderr.replace(host.encode() + b' port ' + port_s, b'HOST port PORT')
                .replace(b'@' + host.encode(), b'@HOST').replace(b'\r\n', b'\n'))


    def ssh_start(self, where, args):
        """px124: `ssh` with pax's key, started and not waited for: the Popen (its output piped)."""
        host, port = where
        argv = ['ssh', '-F', 'none', '-o', 'UserKnownHostsFile=%s' % self.kh, '-o', 'StrictHostKeyChecking=yes',
                '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=20', '-o', 'BatchMode=yes',
                '-o', 'PreferredAuthentications=publickey', '-i', self.key, '-p', str(port), '-l', 'pax']
        return subprocess.Popen([str(x) for x in argv + [host] + list(args)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env())

    def ssh_tty(self, where, args, opts=(), timeout=30, typed=None, after=None):
        """The client as a person runs it at a terminal: ssh's standard input, output and error a
        pseudo-terminal of its own (publickey), what it wrote there, and its status; killed after
        `timeout` seconds (a session that waits for input is named so, never left). `typed` is written
        to the terminal once `after` shows there (at once when `after` is None), as a person types."""
        host, port = where
        argv = ['ssh', '-F', 'none', '-o', 'UserKnownHostsFile=%s' % self.kh, '-o', 'StrictHostKeyChecking=yes',
                '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=20', '-o', 'BatchMode=yes',
                '-o', 'PreferredAuthentications=publickey', '-i', self.key, '-p', str(port), '-l', 'pax']
        master, slave = os.openpty()
        p = subprocess.Popen([str(x) for x in argv + list(opts) + [host] + list(args)], stdin=slave, stdout=slave, stderr=slave,
                             env=dict(self.env(), TERM='xterm'), start_new_session=True)
        os.close(slave)
        out, end, waited = b'', time.monotonic() + timeout, False
        if typed is not None and after is None:
            os.write(master, typed)
            typed = None
        while True:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b''
                out += data
                if typed is not None and after is not None and after in out:
                    os.write(master, typed)
                    typed = None
                if not data and p.poll() is not None:
                    break
            elif p.poll() is not None:
                break
            if time.monotonic() > end:
                waited = True
                p.kill()
                p.wait()
                break
        os.close(master)
        text = out.replace(b'\r\n', b'\n').replace(host.encode() + b' port ' + str(port).encode(), b'HOST port PORT')
        return (None if waited else p.returncode), text


GUEST_AT = (GUEST, 22)
LINUX_AT = (HOST, SSHD_PORT)


def show(r):
    return 'exit %s, stdout %r, stderr %r' % (r[0], r[1][:120], r[2][-200:])


def held(row, what, rb, rs, stdout=True):
    """burrowd's on PAX against sshd's on Linux: status, stdout, stderr."""
    if rb[0] != rs[0] or (stdout and rb[1] != rs[1]) or rb[2] != rs[2]:
        bad(row, '%s: burrowd on PAX %s; sshd on Linux %s' % (what, show(rb), show(rs)))
        return False
    return True


# ---------------------------------------------------------------- the image

def make_shadow(work):
    for k in ('pax', 'root', 'lobo', 'wrong'):
        PASSWORDS[k] = secrets.token_urlsafe(18)
    mk = ARGS.images / 'tools' / 'mkshadow'
    shipped = run([mk], data=('pax %s\n' % PASSWORDS['pax']).encode(), timeout=600).stdout.decode()
    cheap = run([mk, '--cost', '14', '8', '1'], data=('root %s\nlobo %s\n' % (PASSWORDS['root'], PASSWORDS['lobo']))
                .encode(), timeout=600).stdout.decode()
    lines = {}
    for line in (shipped + cheap).splitlines():
        f = line.split(':')
        if len(f) == 9:
            lines[f[0]] = f
    lines['lobo'][1] = '!' + lines['lobo'][1]
    text = ''.join(':'.join(lines[n]) + '\n' for n in ('root', 'pax', 'lobo'))
    text += 'burrowd:!:%s:0:99999:7:::\n' % lines['pax'][2]
    (work / 'shadow').write_text(text)
    os.chmod(work / 'shadow', 0o600)
    return text, ':'.join(lines['pax'])


def seed_repo(work):
    src = work / 'seed'
    env = dict(PATH='/usr/bin:/bin', HOME=str(work), GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='px112',
               GIT_AUTHOR_EMAIL='px112@example.invalid', GIT_COMMITTER_NAME='px112',
               GIT_COMMITTER_EMAIL='px112@example.invalid', GIT_AUTHOR_DATE='1700000000 +0000',
               GIT_COMMITTER_DATE='1700000000 +0000')
    run(['git', 'init', '-q', '-b', 'main', src], env=env)
    (src / 'README').write_text('px112: a repository on PAX, served by den through burrowd.\n')
    run(['git', '-C', src, 'add', 'README'], env=env)
    run(['git', '-C', src, 'commit', '-q', '-m', 'seed'], env=env)
    # No template: git's sample hooks are executable files under hooks/, and den's receive-pack
    # refuses a repository with hooks it cannot run (`den: wire: Unsupported(receive-pack hooks)`,
    # the first takes' B7). A repository made on PAX (den init --bare) has none.
    run(['git', 'clone', '-q', '--bare', '--template=', src, work / 'repo.git'], env=env)
    return work / 'repo.git'


def image(work, shadow_text, client, repo):
    files = [l for l in (ARGS.images / 'files.txt').read_text().splitlines() if l]
    files.append('/etc/shadow=%s:600' % (work / 'shadow'))
    ssh = work / 'pax-ssh'
    ssh.mkdir()
    (ssh / 'authorized_keys').write_text(client.pub('pax'))
    files += ['/home/pax/.ssh/:700:1000:1000', '/home/pax/.ssh/authorized_keys=%s:600:1000:1000' % (ssh / 'authorized_keys')]
    # lobo's own key listed: refused by the lock alone.
    files += ['/srv/:755', '/srv/lobo/:755:990:990', '/srv/lobo/.ssh/:700:990:990',
              '/srv/lobo/.ssh/authorized_keys=%s:600:990:990' % (ssh / 'authorized_keys')]
    # root's own key listed: refused as root.
    files += ['/root/.ssh/:700', '/root/.ssh/authorized_keys=%s:600' % (ssh / 'authorized_keys')]
    files.append('/home/pax/repo.git/:755:1000:1000')
    for p in sorted(repo.rglob('*')):
        g = '/home/pax/repo.git/' + p.relative_to(repo).as_posix()
        if p.is_dir():
            files.append('%s/:755:1000:1000' % g)
        else:
            files.append('%s=%s:%s:1000:1000' % (g, p, '755' if os.access(p, os.X_OK) else '644'))
    run([ROOT / 'tools/mkinitramfs', work / 'image.cpio'] + files)
    run([ROOT / 'tools/mkimage', '--conf', ROOT / 'boot/limine-initramfs-quiet.conf', '--add', work / 'image.cpio',
         'initramfs.cpio', ARGS.elf, work / 'image.iso'])
    vol = work / 'keys-d'
    vol.mkdir()
    cfg = ARGS.images / 'root' / 'etc/burrowd/burrowd_config'
    if cfg.exists():
        # The rows reach the guest from the LAN whichever default ships: the
        # shipped file's one ListenAddress line is replaced by the LAN's.
        lines = cfg.read_text().splitlines()
        listen = [i for i, l in enumerate(lines) if l.split()[:1] == ['ListenAddress']]
        if len(listen) != 1:
            bad('B0', 'the shipped burrowd_config has %d ListenAddress lines, not one' % len(listen))
        else:
            lines[listen[0]] = 'ListenAddress 0.0.0.0'
        (vol / 'burrowd_config').write_text('\n'.join(lines) + '\n')
        os.chmod(vol / 'burrowd_config', 0o644)
    run(['mke2fs', '-q', '-t', 'ext2', '-L', 'px112-keys', '-E', 'root_owner=0:0', '-d', vol, work / 'keys.img', '4M'],
        env=dict(PATH='/usr/sbin:/sbin:/usr/bin:/bin', E2FSPROGS_FAKE_TIME='1700000000'))
    return work / 'image.iso', work / 'keys.img'


# ---------------------------------------------------------------- the boots

def first_boot(con, client, linux):
    # The whole line, to its newline: the serial arrives in pieces, and a pattern ending `$` matched a
    # line cut short (dev-p1: `… SHA256:… pa`).
    m = con.wait(r'^burrowd: host key (256 SHA256:[A-Za-z0-9+/]{43}) ([^\n]*)\n', 300)
    if not m and con.silent():
        bad('B1', con.silent())
        return None
    if not m or not m.group(2).endswith(b'(made at this boot)'):
        bad('B1', 'no `burrowd: host key … (made at this boot)` line on the console: %r'
            % (m.group(0) if m else con.text()[-600:]))
        return None
    fp = m.group(1).decode()
    if not con.wait(r'login: $', 120):
        bad('B1', 'no login prompt after the host key line')
        return fp
    # The key the rig is shown: the rig's ssh connects, accepts the key into a file of its own and is
    # refused (no method offered). Not ssh-keyscan: the image's ssh-keyscan offers no strict key
    # exchange, which burrowd requires of every client (measured: `strict_kex_missing`).
    seen = client.dir / 'seen_hosts'
    scan = None
    for _ in range(30):
        seen.unlink(missing_ok=True)
        subprocess.run(['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
                        '-o', 'HashKnownHosts=no', '-o', 'UserKnownHostsFile=%s' % seen, '-o', 'GlobalKnownHostsFile=/dev/null',
                        '-o', 'PubkeyAuthentication=no', '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
                        '-o', 'ConnectTimeout=5', 'nobody@' + GUEST, 'true'], capture_output=True, timeout=30)
        lines = seen.read_text().splitlines() if seen.exists() else []
        if lines and lines[0].split()[1:2] == ['ssh-ed25519']:
            scan = lines[0]
            break
        time.sleep(1)
    if not scan:
        bad('B1', 'the rig\'s ssh was shown no ed25519 key at %s:22' % GUEST)
        return fp
    client.kh.write_text(scan + '\n' + linux.known())
    pub = client.dir / 'guest.pub'
    pub.write_text(' '.join(scan.split()[1:3]) + '\n')
    got = run(['ssh-keygen', '-l', '-E', 'sha256', '-f', pub]).stdout.decode().split()
    if '256 ' + got[1] != fp:
        bad('B1', 'the console says %s; the rig is shown %s' % (fp, got[1]))
    else:
        ok('B1', 'made at this boot, %s on the console and shown to the rig\'s ssh' % fp)
    return fp


def host_rows(client):
    c = client
    cmds = (['true'], ['echo out; echo err >&2'], ['exit 1'])
    # B2 publickey.
    good = True
    for cmd in cmds:
        good &= held('B2', 'key, %r' % cmd, c.ssh(GUEST_AT, cmd), c.ssh(LINUX_AT, cmd))
    if good:
        ok('B2', 'true, both streams, exit 1: equal through burrowd on PAX and sshd on Linux')
    # B3 password.
    good = True
    for cmd in cmds:
        good &= held('B3', 'password, %r' % cmd, c.ssh(GUEST_AT, cmd, password=PASSWORDS['pax'], timeout=300),
                     c.ssh(LINUX_AT, cmd, password=PASSWORDS['pax'], timeout=300))
    if good:
        ok('B3', 'the same with pax\'s password (the shipped cost)')
    # B4 id.
    r = c.ssh(GUEST_AT, ['id -u; id -g'])
    if r[0] == 0 and r[1] == b'1000\n1000\n':
        ok('B4', 'uid 1000, gid 1000')
    else:
        bad('B4', show(r))
    # B5 refusals.
    good = True
    good &= held('B5', 'a wrong password', c.ssh(GUEST_AT, ['true'], password=PASSWORDS['wrong'], prompts=2),
                 c.ssh(LINUX_AT, ['true'], password=PASSWORDS['wrong'], prompts=2))
    rk = c.ssh(GUEST_AT, ['true'], user='root')
    rp = c.ssh(GUEST_AT, ['true'], user='root', password=PASSWORDS['root'])
    rl = c.ssh(GUEST_AT, ['true'], user='lobo')
    rlp = c.ssh(GUEST_AT, ['true'], user='lobo', password=PASSWORDS['lobo'])
    ro = c.ssh(GUEST_AT, ['true'], key='other')
    for name, r, want in (('root by key', rk, b'root@HOST: Permission denied (publickey,password).\n'),
                          ('root by password', rp, b'root@HOST: Permission denied (publickey,password).\n'),
                          ('lobo (locked) by key', rl, b'lobo@HOST: Permission denied (publickey,password).\n'),
                          ('lobo (locked) by password', rlp, b'lobo@HOST: Permission denied (publickey,password).\n'),
                          ('an unlisted key', ro, b'pax@HOST: Permission denied (publickey,password).\n')):
        if r[0] != 255 or r[2] != want:
            bad('B5', '%s: %s' % (name, show(r)))
            good = False
    sm = c.ssh(GUEST_AT, ['chmod 777 .ssh'], password=PASSWORDS['pax'], timeout=300)
    sk = c.ssh(GUEST_AT, ['true'])
    back = c.ssh(GUEST_AT, ['chmod 700 .ssh'], password=PASSWORDS['pax'], timeout=300)
    if sm[0] != 0 or sk[0] != 255 or back[0] != 0:
        bad('B5', 'StrictModes: chmod 777 %s; the key then %s; chmod 700 %s' % (show(sm), show(sk), show(back)))
        good = False
    if good:
        ok('B5', 'a wrong password, root (key, password), lobo locked (key, password), an unlisted key, ~/.ssh 0777')
    # B6 status and signal.
    r3 = c.ssh(GUEST_AT, ['exit 3'])
    rt = c.ssh(GUEST_AT, ['kill -TERM $$'])
    lt = c.ssh(LINUX_AT, ['kill -TERM $$'])
    # Held whole (status and both streams): a refused connection is 255 too, and the first takes'
    # B6 passed so with the rig's sshd down.
    if r3[0] == 3 and rt == lt and rt[0] == 255 and rt[1] == b'' and b'Connection refused' not in lt[2]:
        ok('B6', 'exit 3 is 3; kill -TERM $$ is 255, as sshd\'s on Linux')
    else:
        bad('B6', 'exit 3: %s; TERM through burrowd: %s; through sshd: %s' % (show(r3), show(rt), show(lt)))
    # B12 a session without ptys: the client at a terminal, as a person types `ssh host`, `ssh -t host`
    # and `ssh -T host` (burrow's shell, px112: the account's login shell with no pty; a pty request
    # refused by name, and burrowd's line saying so), and `ssh host COMMAND`. Into each shell, once the
    # session has answered, one line: a printf whose output its own echo cannot hold, then `exit 4`.
    line = b"printf 'shell %s %s\\n' ran \"$0\"; exit 4\n"
    refused = b'PTY allocation request failed'
    plain = c.ssh_tty(GUEST_AT, [], typed=line, after=refused, timeout=60)
    cmd = c.ssh_tty(GUEST_AT, ['echo pty=$(tty 2>/dev/null || echo none)'])
    forced = c.ssh_tty(GUEST_AT, [], opts=['-t'], typed=line, after=refused, timeout=60)
    # `ssh -T host`: a shell request with no pty request before it (B9 finds its log line).
    bare = c.ssh_tty(GUEST_AT, [], opts=['-T'], typed=line, timeout=60)
    said = lambda r: ' | '.join(l.strip() for l in r[1].decode(errors='replace').splitlines() if l.strip())
    record_b12 = ('ssh host: status %s: %s\nssh host COMMAND: status %s: %s\nssh -t host: status %s: %s\n'
                  'ssh -T host: status %s: %s\n' % (plain[0], said(plain), cmd[0], said(cmd), forced[0], said(forced),
                                                    bare[0], said(bare)))
    (c.dir / 'b12.txt').write_text(record_b12)
    no_pty = b'burrowd: no pty here: this shell runs without a terminal (no line editing, no job control)'
    ran = lambda r: r[0] == 4 and b'shell ran ' in r[1]  # the typed line's echo holds `shell %s`, never this
    with_pty = ran(plain) and refused in plain[1] and plain[1].count(no_pty) == 1 and plain[1].index(refused) < plain[1].index(no_pty)
    insisted = forced[0] == 255 and refused in forced[1] and b'shell ran ' not in forced[1]
    if (cmd[0] == 0 and b'pty=' in cmd[1] and with_pty and insisted and ran(bare) and refused not in bare[1]
            and no_pty not in bare[1]):
        ok('B12', 'no ptys, the shell served: %s' % record_b12.replace('\n', '; ').strip('; '))
    else:
        bad('B12', 'a session without ptys: %s' % record_b12.replace('\n', '; ').strip('; '))
    # B15 a bare sudo over ssh: no controlling terminal since px124 (init gives the console up before
    # the first login), so sudo refuses by name at once; burrowd answers the next connection.
    try:
        rs = c.ssh(GUEST_AT, ['sudo cat /etc/hostname'], timeout=15)
    except subprocess.TimeoutExpired:
        rs = None
    try:
        r2 = c.ssh(GUEST_AT, ['echo second'], timeout=30)
    except subprocess.TimeoutExpired:
        r2 = (None, b'', b'[row: timed out]')
    (c.dir / 'b15.txt').write_text('sudo: %s\nsecond: %s\n' % ('waited, killed after 15 s' if rs is None else show(rs), show(r2)))
    if rs is not None and rs[0] == 1 and b'a terminal is required to read the password' in rs[2] and r2[0] == 0 and r2[1] == b'second\n':
        ok('B15', 'a bare sudo over ssh has no terminal (the console is no terminal of pid 1\'s session): refused at once by name; '
           'the next connection is answered')
    else:
        bad('B15', 'sudo over ssh: %s; the next connection: %s' % ('waited' if rs is None else show(rs), show(r2)))
    # B16 sudo over ssh as the README has it: -k -S remembers nothing; a plain -S's record is keyed by
    # its parent, each session's own shell, since px124 (measured, not held).
    line = (PASSWORDS['pax'] + '\n').encode()
    try:
        k1 = c.ssh(GUEST_AT, ["sudo -k -S -p '' id -u"], data=line, timeout=120)
        k2 = c.ssh(GUEST_AT, ['sudo -n id -u'], timeout=60)
        p1 = c.ssh(GUEST_AT, ["sudo -S -p '' id -u"], data=line, timeout=120)
        p2 = c.ssh(GUEST_AT, ['sudo -n id -u'], timeout=60)
        kk = c.ssh(GUEST_AT, ['sudo -K'], timeout=60)
    except subprocess.TimeoutExpired as e:
        k1 = k2 = p1 = p2 = kk = (None, b'', ('[row: timed out: %s]' % e.cmd[-1]).encode())
    (c.dir / 'b16.txt').write_text('sudo -k -S: %s\nthen sudo -n: %s\nsudo -S: %s\nthen sudo -n: %s\nsudo -K: %s\n'
                                   % (show(k1), show(k2), show(p1), show(p2), show(kk)))
    shared = ('a second session\'s sudo -n ran as root (the console\'s record, shared)' if p2[:2] == (0, b'0\n')
              else 'a second session\'s sudo -n was asked (%s)' % show(p2))
    if k1[:2] == (0, b'0\n') and k2[0] not in (0, None) and k2[1] == b'' and p1[:2] == (0, b'0\n') and kk[0] == 0:
        ok('B16', 'sudo -k -S ran as root and a second session\'s sudo -n was asked; after a plain sudo -S, %s' % shared)
    else:
        bad('B16', 'sudo -k -S: %s; then sudo -n: %s; sudo -S: %s; then: %s; sudo -K: %s'
            % (show(k1), show(k2), show(p1), show(p2), show(kk)))
    # B17 the stack segment after a system call, and after interrupts taken in ring 3 (pax#340).
    try:
        rq = c.ssh(GUEST_AT, ['/bin/sysret-ss'], timeout=60)
    except subprocess.TimeoutExpired:
        rq = (None, b'', b'[row: timed out]')
    (c.dir / 'b17.txt').write_text('sysret-ss: %s\n' % show(rq))
    if rq[0] == 0 and rq[1].startswith(b'ok: ss 0x1b cs 0x23 after a system call; ss 0x1b cs 0x23 after '):
        ok('B17', rq[1].decode(errors='replace').strip()[4:])
    else:
        bad('B17', 'sysret-ss: %s' % show(rq))


def image_exports():
    """The variables the image's /etc/shrc exports for the console, every one but PATH, in order
    (tools/system-env writes the configuration's SetEnv line from the same lines)."""
    shrc = ARGS.images / 'root' / 'etc/shrc'
    out = []
    for line in shrc.read_text().splitlines() if shrc.exists() else []:
        m = re.match(r'^export ([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
        if m and m.group(1) != 'PATH':
            out.append((m.group(1), m.group(2)))
    return out


def image_setenv():
    """The image's burrowd_config's SetEnv line, '' when it has none."""
    cfg = ARGS.images / 'root' / 'etc/burrowd/burrowd_config'
    lines = [l for l in cfg.read_text().splitlines() if l.startswith('SetEnv ')] if cfg.exists() else []
    return lines[0] if len(lines) == 1 else ''


def env_rows(client):
    """B18 (px116, pax#334): the console's variables over ssh, and wolf building with no prefix."""
    c = client
    want = dict(image_exports())
    names = ('WOLF_STD', 'LUPIN_STD', 'DEN_TLS_ROOTS')
    missing = [n for n in names if n not in want]
    probe = ['printf "%s\\n" ' + ' '.join('"${%s-unset}"' % n for n in names)]
    rb, rs = c.ssh(GUEST_AT, probe), c.ssh(LINUX_AT, probe)
    expect = ''.join('%s\n' % want.get(n, 'unset') for n in names).encode()
    # The program calls std.fs.write_text, which pax#334's failed build named (`module fs has no item
    # named write_text`): it compiles against the compiler's own std, not against lupin's.
    prog = ('use std.fs\\nfn main() {\\n    fs.write_text(\"px116.txt\", \"px116\\\\n\") else {}\\n'
            '    print(\"px116: built over ssh\")\\n}\\n')
    # Held: wolf's own status, 0 (without WOLF_STD it is 2, E0301, as pax#334 found). Recorded: what
    # the build left in pax's home (for a program that imports std, measured, no px116.o).
    build = ("cd && rm -f px116.o && printf '%s' > px116.lu && wolf build --no-cache --emit=obj px116.lu -o px116.o; "
             "s=$?; ls -la; echo wolf=$s" % prog)
    rbuild = c.ssh(GUEST_AT, [build], timeout=600)
    # Recorded, not held: the same build with WOLF_STD taken away, as a command had it before px116.
    rbare = c.ssh(GUEST_AT, ['cd && rm -f px116.o && env -u WOLF_STD wolf build --no-cache --emit=obj px116.lu '
                             '-o px116.o; echo status=$?'], timeout=600)
    record = ('the image\'s /etc/shrc exports %r\nthe image\'s SetEnv line %r\nprintf over ssh, burrowd on PAX: %s\n'
              'the same, the rig\'s sshd with that line: %s\nwolf build over ssh, no prefix: %s\n'
              'the same, WOLF_STD taken away (recorded): %s\n'
              % (sorted(want.items()), image_setenv(), show(rb), show(rs), show(rbuild), show(rbare)))
    (c.dir / 'b18.txt').write_text(record)
    if missing:
        bad('B18', 'the image\'s /etc/shrc exports no %s' % ', '.join(missing))
    elif rb[0] != 0 or rb[1] != expect:
        bad('B18', 'over ssh the variables are %r, the console\'s %r (%s)' % (rb[1], expect, show(rb)))
    elif not held('B18', 'the variables, against the rig\'s sshd given the same SetEnv line', rb, rs):
        pass
    elif rbuild[0] != 0 or not rbuild[1].endswith(b'wolf=0\n'):
        bad('B18', 'wolf build over ssh with no prefix: %s' % show(rbuild))
    else:
        tail = rbare[1].decode(errors='replace').strip().splitlines()[-1:] or ['-']
        ok('B18', '%s over ssh as the console has them (sshd\'s answer too); wolf build of a program calling std.fs, no prefix: '
           'status 0; without WOLF_STD: %s' % (', '.join('%s=%s' % (n, want[n]) for n in names), tail[0]))


def git_rows(client, work):
    """B7: the same git steps through burrowd on PAX and sshd on Linux."""
    results = {}
    for side, (host, port) in (('pax', GUEST_AT), ('linux', LINUX_AT)):
        d = work / ('git-' + side)
        d.mkdir()
        env = dict(PATH='/usr/bin:/bin', HOME=str(d), LC_ALL='C', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0',
                   GIT_AUTHOR_NAME='px112', GIT_AUTHOR_EMAIL='px112@example.invalid', GIT_COMMITTER_NAME='px112',
                   GIT_COMMITTER_EMAIL='px112@example.invalid', GIT_AUTHOR_DATE='1700000100 +0000',
                   GIT_COMMITTER_DATE='1700000100 +0000',
                   GIT_SSH_COMMAND='ssh -F none -o UserKnownHostsFile=%s -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes '
                                   '-o BatchMode=yes -i %s -p %d' % (client.kh, client.key, port))
        url = 'pax@%s:repo.git' % host
        steps = []

        def g(*a, cwd=None, trace=False):
            e = dict(env)
            if trace:
                e['GIT_TRACE_PACKET'] = '1'
            r = subprocess.run(['git', '-c', 'protocol.version=2'] + list(a), cwd=cwd, env=e, capture_output=True,
                               timeout=300)
            steps.append((a[0], r.returncode))
            # Each step's standard error kept beside the run (the evidence of a red step).
            (d / ('%02d-%s.err' % (len(steps), a[0]))).write_bytes(r.stderr)
            return r
        c1 = g('clone', '-q', url, d / 'one', trace=True)
        if c1.returncode == 0:
            (d / 'one' / 'NEW').write_text('pushed through ssh\n')
            g('add', 'NEW', cwd=d / 'one')
            g('commit', '-q', '-m', 'px112: a push', cwd=d / 'one')
            g('push', '-q', 'origin', 'main', cwd=d / 'one')
            g('clone', '-q', url, d / 'two')
            # The metal target's first push: a bare repository made over ssh
            # (den's on PAX, git's on Linux), then git push into it.
            # git's own initial branch is `master` unless told; den's is `main`: the same step on Linux names it.
            made = client.ssh((host, port), ['den init -q --bare fresh.git' if side == 'pax'
                                             else 'git init -q --bare --initial-branch=main fresh.git'])
            steps.append(('init --bare', made[0]))
            g('push', '-q', 'pax@%s:fresh.git' % host, 'main', cwd=d / 'one')
            g('clone', '-q', 'pax@%s:fresh.git' % host, d / 'three')
        heads = subprocess.run(['git', '-C', d / 'two', 'rev-parse', 'HEAD', 'HEAD^{tree}'], capture_output=True,
                               env=env).stdout.decode()
        heads += subprocess.run(['git', '-C', d / 'three', 'rev-parse', 'HEAD'], capture_output=True,
                                env=env).stdout.decode()
        objs = subprocess.run(['git', '-C', d / 'two', 'cat-file', '--batch-all-objects', '--batch-check'],
                              capture_output=True, env=env).stdout.decode()
        fsck = subprocess.run(['git', '-C', d / 'two', 'fsck', '--full'], capture_output=True, env=env).returncode
        v2 = b'version 2' in c1.stderr
        results[side] = (steps, heads, objs, fsck, v2)
    p, l = results['pax'], results['linux']
    if p[0] == l[0] and all(rc == 0 for _, rc in p[0]) and p[1] == l[1] and p[2] == l[2] and p[3] == 0 and p[4]:
        ok('B7', 'clone, commit, push, clone: %d objects, HEAD %s, as through sshd and git; fsck clean; protocol v2'
           % (len(p[2].splitlines()), p[1].split()[0][:12] if p[1] else '-'))
    else:
        bad('B7', 'steps %s / %s; heads %r / %r; objects %d / %d; fsck %s; v2 %s'
            % (p[0], l[0], p[1], l[1], len(p[2].splitlines()), len(l[2].splitlines()), p[3], p[4]))


def console_rows(con, client):
    """B8 and B9 at the console, as root (its password, typed, never
    echoed or written)."""
    # A fresh login prompt first: login ends an exchange 60 s after its prompt, and a password
    # typed after that would be read, and echoed, as the next login's name (a probe saw it, and
    # B9's scan caught it).
    con.type('')
    if not con.wait(r'login: $', 30):
        bad('B8', 'no fresh login prompt at the console: %r' % con.text()[-200:])
        return
    con.type('root')
    if not con.wait(r'Password: $', 10):
        bad('B8', 'no Password: prompt for root')
        return
    con.type(PASSWORDS['root'], secret=True)
    # pelt's prompt is `$ ` for root too (the first takes waited for `# `, which PAX never prints).
    if not con.wait(r'[$#] $', 60):
        bad('B8', 'root did not log in at the console: %r' % con.text()[-300:])
        return
    before = con.command('cat /var/run/burrowd.pid', 1)
    con.command('kill $(cat /var/run/burrowd.pid)', 2)
    t0 = time.monotonic()
    r = None
    while time.monotonic() - t0 < 5:
        r = client.ssh(GUEST_AT, ['cat /var/run/burrowd.pid'], timeout=30)
        if r[0] == 0:
            break
        time.sleep(0.25)
    dt = time.monotonic() - t0
    if r and r[0] == 0 and before and r[1].decode().strip() != before.strip():
        ok('B8', 'a login again %.1f s after the kill, burrowd pid %s then %s' % (dt, before.strip(), r[1].decode().strip()))
    else:
        bad('B8', 'after the kill of %r: %s after %.1f s' % (before, show(r) if r else 'nothing', dt))
    mode = con.command('ls -l /var/log/burrowd.log', 3) or ''
    log = con.command('cat /var/log/burrowd.log', 4) or ''
    want = ['key SHA256:', 'key password', 'outcome auth_password_bad', 'outcome auth_root_refused',
            'outcome auth_account_locked', 'outcome auth_key_unlisted', 'outcome auth_strict_modes', 'signal TERM',
            'refused pty_refused']
    # B12's shells: a line ending with the pty refused (`ssh host`, `ssh -t host`), one ending at the status (-T's).
    ends = ['outcome ok status 4 refused pty_refused', 'outcome ok status 4']
    lines = [l.rstrip() for l in log.splitlines()]
    missing = ([w for w in want if w not in log] + [e for e in ends if not any(l.endswith(e) for l in lines)]
               + (['no shell_refused'] if 'shell_refused' in log else []))
    if not mode.startswith('-rw-------') or ' root ' not in mode or missing:
        bad('B9', 'the log: %r; missing %s' % (mode.strip(), missing))
    else:
        ok('B9', 'the log at the console, root\'s 0600, every kind of line (%d lines)' % len(log.splitlines()))
    logout_rows(con, client)


def logout_rows(con, client):
    """B30 and B31 (px124): the console's logout with an ssh command running, and the runtime
    directory over ssh."""
    before = client.ssh(GUEST_AT, ['cat /var/run/burrowd.pid'], timeout=30)
    p = client.ssh_start(GUEST_AT, ['echo begun; sleep 12; echo still'])
    time.sleep(4)
    con.type('exit')
    back = con.wait(r'login: $', 20)
    try:
        out, err = p.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        err += b'[row: killed after 90 s]'
    after = client.ssh(GUEST_AT, ['cat /var/run/burrowd.pid'], timeout=30)
    (client.dir / 'b30.txt').write_text('ssh across the logout: %s %r %r\nburrowd before %s, after %s\nconsole: %s\n'
                                        % (p.returncode, out, err, show(before), show(after), 'login: again' if back else 'no login:'))
    if (back and p.returncode == 0 and out == b'begun\nstill\n' and before[0] == 0 and after[0] == 0
            and before[1] == after[1]):
        ok('B30', 'root\'s `exit` at the console gave `login:` again while an ssh command ran on: it ended 0 with both '
           'lines; burrowd kept pid %s' % before[1].decode().strip())
    else:
        bad('B30', 'console %s; the ssh command %s %r %r; burrowd %s then %s'
            % ('login: again' if back else 'no login: (%r)' % con.text()[-200:], p.returncode, out, err[-200:], show(before), show(after)))
    r = client.ssh(GUEST_AT, ['ls -ldn /run/user/1000; echo X=$XDG_RUNTIME_DIR'], timeout=60)
    (client.dir / 'b31.txt').write_text('%s\n' % show(r))
    f = r[1].decode(errors='replace').split()
    if r[0] == 0 and len(f) > 4 and f[0].startswith('drwx------') and f[2:4] == ['1000', '1000']:
        ok('B31', 'pax\'s runtime directory over ssh: %s; XDG_RUNTIME_DIR over ssh %r (measured: burrowd sets no '
           'per-account variable)' % (' '.join(f[:4]), r[1].decode(errors='replace').split('X=', 1)[-1].strip()))
    else:
        bad('B31', 'the runtime directory over ssh: %s' % show(r))


def second_boot(con, client, fp):
    m = con.wait(r'^burrowd: host key (256 SHA256:[A-Za-z0-9+/]{43}) ([^\n]*)\n', 300)
    if not m:
        bad('B10', con.silent() or 'no host key line on the second boot')
        return
    line = m.group(0).decode().rstrip('\n')
    if not con.wait(r'login: $', 120):
        bad('B10', 'no login prompt on the second boot')
        return
    r = None
    for _ in range(20):
        r = client.ssh(GUEST_AT, ['true'])
        if r[0] == 0:
            break
        time.sleep(1)
    if m.group(1).decode() == fp and 'made at this boot' not in line and r and r[0] == 0:
        ok('B10', 'the same key, %s, kept; boot 1\'s known_hosts verifies it' % fp)
    else:
        bad('B10', 'boot 2 says %r (boot 1: %s); ssh %s' % (line, fp, show(r) if r else '-'))


def poweroff_row(con, client):
    """B32 (px124): `sudo -k -S poweroff` over ssh ends the machine."""
    line = (PASSWORDS['pax'] + '\n').encode()
    try:
        r = client.ssh(GUEST_AT, ["sudo -k -S -p '' /bin/poweroff"], data=line, timeout=120)
    except subprocess.TimeoutExpired:
        r = (None, b'', b'[row: timed out]')
    end = con.wait(r'^user: poweroff pid \d+ reboot\(2\): the volumes written and marked clean[^\n]*$', 60)
    try:
        rc = con.q.wait(timeout=120)
    except subprocess.TimeoutExpired:
        rc = None
    (client.dir / 'b32.txt').write_text('ssh: %s\nend: %r\nQEMU: %s\n' % (show(r), end.group(0) if end else None, rc))
    if end and rc == 0:
        ok('B32', 'sudo -k -S poweroff over ssh: %s; QEMU 0' % end.group(0).decode())
    else:
        bad('B32', 'poweroff over ssh: %s; the end line %r; QEMU %s' % (show(r), end.group(0) if end else None, rc))


def live_image(work):
    """The stick's shape: the live entry as pid 1, the shipped configuration,
    no /etc/shadow, no keys volume."""
    files = [l for l in (ARGS.images / 'files.txt').read_text().splitlines()
             if l and not l.startswith(('/etc/pax-run=', '/etc/fstab='))]
    (work / 'live.run').write_text('/bin/pelt /etc/pax-live-login\n')
    files += ['/etc/pax-run=%s:644' % (work / 'live.run'), '/etc/pax-live-login=%s:644' % (ROOT / 'user/usb-login.sh')]
    run([ROOT / 'tools/mkinitramfs', work / 'live.cpio'] + files)
    run([ROOT / 'tools/mkimage', '--conf', ROOT / 'boot/limine-initramfs-quiet.conf', '--add', work / 'live.cpio',
         'initramfs.cpio', ARGS.elf, work / 'live.iso'])
    return work / 'live.iso'


def stick_rows(con, client):
    m = con.wait(r'^burrowd: host key (256 SHA256:[A-Za-z0-9+/]{43}) [^\n]*\(made at this boot\)\n', 300)
    if not m or not con.wait(r'login: $', 120):
        bad('B11', con.silent() or 'the stick shape: no host key line made at boot, or no login prompt: %r' % con.text()[-500:])
        return
    r = None
    for _ in range(10):
        r = client.ssh(GUEST_AT, ['true'], timeout=30)
        if b'Connection refused' in r[2]:
            break
        time.sleep(1)
    # client.ssh writes the address and port it dialled (GUEST_AT: the guest's port 22) as HOST port PORT.
    lan = r is not None and r[0] == 255 and b'ssh: connect to host HOST port PORT: Connection refused' in r[2]
    con.type('root')
    con.command('true', 1, 60)
    out = con.command("burrow-keygen -q -t ed25519 -N '' -f /tmp/px112-k && ssh -i /tmp/px112-k -o BatchMode=yes "
                      "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/px112-kh pax@127.0.0.1 true; "
                      "echo ssh=$?", 2, 120) or ''
    log = con.command('cat /var/log/burrowd.log', 3) or ''
    con.type('exit')
    here = 'pax@127.0.0.1: Permission denied (publickey,password).' in out and 'ssh=255' in out
    listen = 'listening on 127.0.0.1:22' in log and ' user pax ' in log
    if lan and here and listen:
        ok('B11', 'the stick: refused from the LAN at connect, answered on loopback (%s), its log names both' % m.group(1).decode())
    else:
        bad('B11', 'the stick: from the LAN %s; at the console %r; the log %r' % (show(r) if r else '-', out[-200:], log[-300:]))


def main():
    global ARGS
    a = argparse.ArgumentParser()
    for k in ('images', 'elf', 'tier', 'leg', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    ARGS = a.parse_args()
    ARGS.images = pathlib.Path(ARGS.images)
    out = pathlib.Path(ARGS.out)
    why = rig_missing()
    if why:
        say('SKIP the rig: %s' % ', '.join(why))
        return 3
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    os.chmod(out, 0o711)
    work = out / 'work'
    work.mkdir()
    missing = (ARGS.images / 'missing.txt').read_text().strip() if (ARGS.images / 'missing.txt').exists() else ''
    if missing:
        bad('B0', 'the tree builds no %s' % missing)
    client = Client(out)
    shadow_text, pax_line = make_shadow(work)
    repo = seed_repo(work)
    iso, vol = image(work, shadow_text, client, repo)
    ok('B0', 'the image (%d bytes), its /etc/shadow (pax at the shipped cost), the keys volume' % iso.stat().st_size)
    net = Net(out)
    linux = LinuxSide(out, pax_line, client.pub('pax'), repo, image_setenv())
    fp = None
    try:
        b1 = out / 'boot1'
        b1.mkdir()
        con = Console(b1, iso, vol)
        try:
            fp = first_boot(con, client, linux)
            if fp:
                host_rows(client)
                env_rows(client)
                git_rows(client, work)
                console_rows(con, client)
        finally:
            con.quit(5)  # px124: the console asks `login:` again after its logout; nothing halts
        b2 = out / 'boot2'
        b2.mkdir()
        con2 = Console(b2, iso, vol)
        try:
            if fp:
                second_boot(con2, client, fp)
            poweroff_row(con2, client)
        finally:
            con2.quit(5)
        b3 = out / 'boot3-stick'
        b3.mkdir()
        con3 = Console(b3, live_image(work), None)
        try:
            stick_rows(con3, client)
        finally:
            con3.quit(120)
    finally:
        linux.close()
        net.close()
    places = []
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.stat().st_size < 64 * 1024 * 1024 and p.suffix not in ('.iso', '.img', '.cpio'):
            places.append((str(p.relative_to(out)), p.read_bytes()))
    hits = leaks(places)
    if hits:
        bad('B9', 'a password reached %s' % ', '.join(hits))
    else:
        ok('B9-scan', 'no password in %d records (the serial transcripts, the logs, the rows\' output)' % len(places))
    say('mpx5-burrowd %s %s: %s' % (ARGS.tier, ARGS.leg, 'FAIL ' + ' '.join(FAILS) if FAILS else 'PASS'))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
