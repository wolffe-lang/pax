#!/usr/bin/env python3
"""notes/px130/rig/measure.py — px130's measurement (item 1): which programs a kernel line says were ended by a
signal while someone works over ssh, and which line each command wrote.

    measure.py --images P0 --elf KERNEL.elf --extra BOREDIR --conf quiet|plain --accel A --out DIR

P0 is tests/mpx5-burrowd's tree (its files.txt, tools/mkshadow); BOREDIR holds extra boreutils (head, seq, yes,
...) put in /bin beside the suite's. The image is the suite's installed shape (/bin/login as pid 1, pelt with its
friendly prompt and lope's hook from /etc/shrc, den, burrowd on the LAN), booted with `quiet` (as an installed
system boots) or without it (`plain`: every exec and exit narrated, so each pid has a name). The machinery is
tests/mpx5-burrowd.d/rows.py's, imported, not copied: its tap and dnsmasq, its console on COM1, its ssh client.

The console is logged in as root first (typed on COM1, which the screen also draws), then ssh sessions as pax at a
pseudo-terminal of this script's own run the work below, each step timed on this host's monotonic clock; every
serial line is stamped with the time its newline arrived, and a kernel line is put to the step whose window
(typed .. prompt back, plus 1.5 s) holds it. The console's screen is read back (QEMU's screendump) after the root
login and after the sessions. Writes DIR/serial.log, DIR/serial-timed.txt, DIR/steps.txt, DIR/table.txt,
DIR/tty-*.raw and DIR/screen-*.ppm. Passwords never leave memory (rows.py's rule).
"""
import argparse
import importlib.util
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
spec = importlib.util.spec_from_file_location('rows', ROOT / 'tests/mpx5-burrowd.d/rows.py')
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)

STAMPS = []  # (monotonic time, bytes) as COM1's bytes arrived


def timed_pump(con):
    orig = con.pump

    def pump(wait=0.1):
        before = len(con.seen)
        orig(wait)
        if len(con.seen) > before:
            STAMPS.append((time.monotonic(), con.seen[before:]))
    con.pump = pump


def lines_timed():
    out, cur = [], b''
    for t, data in STAMPS:
        parts = data.split(b'\n')
        for i, p in enumerate(parts):
            if i < len(parts) - 1:
                out.append((t, (cur + p).decode(errors='replace')))
                cur = b''
            else:
                cur += p
    if cur:
        out.append((STAMPS[-1][0], cur.decode(errors='replace')))
    return out


def screendump(con, path):
    try:
        s = socket.socket(socket.AF_UNIX)
        s.connect(str(con.mon))
        s.sendall(('screendump %s\n' % path).encode())
        time.sleep(1.0)
        s.close()
    except OSError as e:
        return 'screendump: %s' % e
    end = time.monotonic() + 10
    while time.monotonic() < end and not (pathlib.Path(path).exists() and pathlib.Path(path).stat().st_size > 0):
        time.sleep(0.2)
    return ''


def image(work, conf, extra):
    files = [l for l in (rows.ARGS.images / 'files.txt').read_text().splitlines() if l]
    files.append('/etc/shadow=%s:600' % (work / 'shadow'))
    # pax's login shell /bin/pelt, as the guided installer writes an account (user/install/prepare.lu):
    # invoked by that name pelt starts friendly (its prompt runs `den status --porcelain`); as `sh`
    # (the suite's /etc/passwd) it does not.
    pw = work / 'passwd'
    pw.write_text((rows.ARGS.images / 'root/etc/passwd').read_text().replace(':/home/pax:/bin/sh', ':/home/pax:/bin/pelt'))
    files = [l for l in files if not l.startswith('/etc/passwd=')] + ['/etc/passwd=%s:644' % pw]
    ssh = work / 'pax-ssh'
    ssh.mkdir()
    (ssh / 'authorized_keys').write_text(CLIENT.pub('pax'))
    files += ['/home/pax/.ssh/:700:1000:1000', '/home/pax/.ssh/authorized_keys=%s:600:1000:1000' % (ssh / 'authorized_keys')]
    have = {l.split('=')[0] for l in files}
    for p in sorted(pathlib.Path(extra).iterdir()):
        if p.name == 'sums.txt' or not p.is_file():
            continue
        if '/bin/' + p.name not in have:
            files.append('/bin/%s=%s:755' % (p.name, p))
    big = work / 'big.txt'
    big.write_text(''.join('line %06d of a file larger than a pipe holds\n' % i for i in range(20000)))
    files.append('/home/pax/big.txt=%s:644:1000:1000' % big)
    rows.run([ROOT / 'tools/mkinitramfs', work / 'image.cpio'] + files)
    c = ROOT / ('boot/limine-initramfs-quiet.conf' if conf == 'quiet' else 'boot/limine-initramfs.conf')
    rows.run([ROOT / 'tools/mkimage', '--conf', c, '--add', work / 'image.cpio', 'initramfs.cpio', rows.ARGS.elf,
              work / 'image.iso'])
    vol = work / 'keys-d'
    vol.mkdir()
    cfg = rows.ARGS.images / 'root' / 'etc/burrowd/burrowd_config'
    lines = cfg.read_text().splitlines()
    lines = ['ListenAddress 0.0.0.0' if l.split()[:1] == ['ListenAddress'] else l for l in lines]
    (vol / 'burrowd_config').write_text('\n'.join(lines) + '\n')
    os.chmod(vol / 'burrowd_config', 0o644)
    rows.run(['mke2fs', '-q', '-t', 'ext2', '-L', 'px112-keys', '-E', 'root_owner=0:0', '-d', vol, work / 'keys.img', '4M'],
             env=dict(PATH='/usr/sbin:/sbin:/usr/bin:/bin', E2FSPROGS_FAKE_TIME='1700000000'))
    return work / 'image.iso', work / 'keys.img'


class NoLinux:
    def known(self):
        return ''


STEPS = []  # (session, name, typed, t0, t1, shown)
# A prompt: a line that ends in `> ` (pelt's friendly `user@host dir> `, its den segment before it) or in `$ `
# or `# ` (plain), at the end of what the terminal shows.
PROMPT = rb'[^\n]*(> |[$#] )$'


def session(con, name, work, out, tail=None):
    """One `ssh host` at a terminal (33 x 97): `work` is [(name, bytes typed, wait)], wait 'prompt' (the prompt
    back), a float (seconds, then the key in the next item), or 'none'. `tail` is how the session ends: 'exit'
    typed, or 'drop' (the client killed with SIGKILL, so the connection drops)."""
    t = CLIENT.terminal(rows.GUEST_AT, 33, 120) # wide enough for the friendly prompt's segments

    answered = [0]

    def answer():
        # pelt asks the terminal where its cursor is (DSR, `ESC [ 6 n`) before its friendly prompt,
        # as a terminal emulator answers it (`ESC [ row ; col R`): a pty with nobody answering
        # leaves pelt plain (`$ `), which is not what a person at a terminal gets.
        asked = t.raw.count(b'\x1b[6n')
        while answered[0] < asked:
            os.write(t.master, b'\x1b[1;1R')
            answered[0] += 1

    def wait_both(pattern, timeout, at):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            con.pump(0)
            answer()
            m = re.search(pattern, t.shown(at), re.M)
            if m:
                return m
            t.pump(0.2)
            if t.p.poll() is not None:
                t.pump(0.3)
                return re.search(pattern, t.shown(at), re.M)
        return None

    try:
        t0 = time.monotonic()
        m = wait_both(PROMPT, 40, 0)
        STEPS.append((name, 'login', '', t0, time.monotonic(), (m.group(0) if m else t.shown()[-120:]).decode(errors='replace')))
        for step, typed, wait in work:
            t0 = time.monotonic()
            at = t.type(typed)
            if wait == 'prompt':
                m = wait_both(PROMPT, 120, at)
            elif isinstance(wait, float):
                end = time.monotonic() + wait
                while time.monotonic() < end:
                    con.pump(0)
                    answer()
                    t.pump(0.2)
                m = True
            else:
                m = True
            STEPS.append((name, step, typed.decode(errors='replace').replace('\r', '\\r'), t0, time.monotonic(),
                          t.shown(at)[-200:].decode(errors='replace') if m else 'NO PROMPT: %r' % t.shown(at)[-200:]))
        t0 = time.monotonic()
        if tail == 'drop':
            t.p.kill()
            t.p.wait()
            what = 'the client killed (SIGKILL), the connection dropped'
        else:
            t.type(b'exit\r')
            end = time.monotonic() + 10
            while time.monotonic() < end and t.p.poll() is None:
                con.pump(0)
                answer()
                t.pump(0.2)
            what = 'exit typed; ssh status %s' % t.p.poll()
        end = time.monotonic() + 4
        while time.monotonic() < end:
            con.pump(0.1)
        STEPS.append((name, 'end', tail or 'exit', t0, time.monotonic(), what))
    finally:
        (out / ('tty-%s.raw' % name)).write_bytes(t.raw)
        t.close()


def main():
    global CLIENT
    a = argparse.ArgumentParser()
    for k in ('images', 'elf', 'extra', 'conf', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    args = a.parse_args()
    rows.ARGS = argparse.Namespace(images=pathlib.Path(args.images), elf=args.elf, tier='native', leg='bios',
                                   accel=args.accel, out=args.out)
    out = pathlib.Path(args.out)
    why = rows.rig_missing()
    if why:
        print('SKIP the rig: %s' % ', '.join(why))
        return 3
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    os.chmod(out, 0o711)
    work = out / 'work'
    work.mkdir()
    CLIENT = rows.Client(out)
    rows.make_shadow(work)
    iso, vol = image(work, args.conf, args.extra)
    net = rows.Net(out)
    try:
        b = out / 'boot'
        b.mkdir()
        con = rows.Console(b, iso, vol)
        timed_pump(con)
        try:
            fp = rows.first_boot(con, CLIENT, NoLinux())
            if not fp:
                print('MEASURE no boot: %r' % con.text()[-800:])
                return 1
            # The console, logged in as root, at its prompt (what a person at the machine sees).
            con.type('')
            con.wait(r'login: $', 30)
            con.type('root')
            con.wait(r'Password: $', 10)
            con.type(rows.PASSWORDS['root'], secret=True)
            if not con.wait(r'[$#] $', 60):
                print('MEASURE root did not log in at the console: %r' % con.text()[-300:])
            for _ in range(10):
                con.pump(0.1)
            screendump(con, out / 'screen-0-console-prompt.ppm')
            STEPS.append(('console', 'root logged in', '', time.monotonic(), time.monotonic(), 'prompt'))
            P = 'prompt'
            work1 = [
                ('ls', b'ls\r', P),
                ('cd /tmp', b'cd /tmp\r', P),
                ('cd ~', b'cd\r', P),
                ('autocd ../', b'../\r', P),
                ('g pax (lope jump)', b'g pax\r', P),
                ('pwd', b'pwd\r', P),
                ('yes | head -n 3', b'yes | head -n 3\r', P),
                ('seq 1 200000 | head -n 2', b'seq 1 200000 | head -n 2\r', P),
                ('cat big.txt | head -n 1', b'cat /home/pax/big.txt | head -n 1\r', P),
                ('ls /bin | head -n 3', b'ls /bin | head -n 3\r', P),
                ('ls -l /bin | head -n 2', b'ls -l /bin | head -n 2\r', P),
                ('echo x | cat', b'echo x | cat\r', P),
                ('mkdir w; cd w', b'mkdir -p /home/pax/w && cd /home/pax/w\r', P),
                ('den init', b'den init\r', P),
                ('den config', b'den config user.name px130; den config user.email px130@example.invalid\r', P),
                ('write a file', b'echo one > a.txt\r', P),
                ('den add', b'den add a.txt\r', P),
                ('den commit', b'den commit -m one\r', P),
                ('den status', b'den status\r', P),
                ('den log', b'den log\r', P),
                ('den log -n 1', b'den log -n 1\r', P),
                ('den branch', b'den branch\r', P),
                ('den init --bare remote', b'den init --bare /home/pax/remote.git\r', P),
                ('den remote add', b'den remote add origin /home/pax/remote.git\r', P),
                ('den push', b'den push origin HEAD:refs/heads/main || den push origin main || den push origin master\r', P),
                ('second commit', b'echo two >> a.txt; den add a.txt; den commit -m two\r', P),
                ('den push 2', b'den push origin HEAD:refs/heads/main\r', P),
                ('den fetch', b'den fetch origin\r', P),
                ('den log -n 1 (2)', b'den log -n 1\r', P),
                ('den clone file', b'cd /home/pax && den clone /home/pax/remote.git c2 && cd c2\r', P),
                ('den status in clone', b'den status\r', P),
                ('cd ~ (from repo)', b'cd\r', P),
                ('sleep 30 (Ctrl-C)', b'sleep 30\r', 1.5),
                ('Ctrl-C', b'\x03', P),
                ('sleep 30 (Ctrl-\\)', b'sleep 30\r', 1.5),
                ('Ctrl-\\', b'\x1c', P),
                ('cat (Ctrl-C)', b'cat\r', 1.5),
                ('Ctrl-C (cat)', b'\x03', P),
                ('yes > /dev/null (Ctrl-C)', b'yes > /dev/null\r', 1.5),
                ('Ctrl-C (yes)', b'\x03', P),
                ('sleep 30 (Ctrl-Z)', b'sleep 30\r', 1.5),
                ('Ctrl-Z', b'\x1a', P),
                ('kill %1', b'kill %1\r', P),
                ('jobs', b'jobs\r', P),
                ('a subshell pipeline', b'(yes; echo done) | head -n 1\r', P),
                ('command substitution', b'x=$(yes | head -n 1); echo $x\r', P),
            ]
            session(con, 's1', work1, out, 'exit')
            session(con, 's2', [('sleep 100 &', b'sleep 100 &\r', P), ('jobs', b'jobs\r', P)], out, 'exit')
            session(con, 's3', [('sleep 100 (foreground)', b'sleep 100\r', 1.5)], out, 'drop')
            session(con, 's4', [('cd w (den repo)', b'cd /home/pax/w\r', P), ('ls', b'ls\r', P)], out, 'drop')
            # A repository of some size: the friendly prompt's `den status --porcelain` has 50 ms (pelt's
            # docs/FRIENDLY.md) and takes longer here.
            work5 = [
                ('make 400 files', b'mkdir -p /home/pax/big && cd /home/pax/big && for i in $(seq 1 400); do echo $i > f$i; done\r', P),
                ('den init (big)', b'den init\r', P),
                ('den add (big)', b'den add .\r', P),
                ('den commit (big)', b'den commit -m many\r', P),
                ('change 60 files', b'for i in $(seq 1 60); do echo x >> f$i; done\r', P),
                ('ls | head (big)', b'ls | head -n 2\r', P),
                ('pwd (big)', b'pwd\r', P),
                ('den status (big)', b'den status\r', P),
                ('true (big)', b'true\r', P),
                ('echo (big)', b'echo hi\r', P),
                ('den diff | head (big)', b'den diff | head -n 3\r', P),
                ('den log | head (big)', b'den log | head -n 2\r', P),
            ]
            session(con, 's5', work5, out, 'exit')
            end = time.monotonic() + 5
            while time.monotonic() < end:
                con.pump(0.1)
            screendump(con, out / 'screen-1-after-ssh.ppm')
            con.type('')
            STEPS.append(('console', 'after', '', time.monotonic(), time.monotonic(), ''))
            con.type('exit')
        finally:
            con.quit(60)
    finally:
        net.close()
    timed = lines_timed()
    with open(out / 'serial-timed.txt', 'w') as f:
        t00 = STAMPS[0][0] if STAMPS else 0
        for t, l in timed:
            f.write('%10.3f %s\n' % (t - t00, l))
    with open(out / 'steps.txt', 'w') as f:
        for s in STEPS:
            f.write('%s\t%s\t%r\t%.3f\t%.3f\t%r\n' % (s[0], s[1], s[2], s[3], s[4], s[5]))
    kernel = re.compile(r'^user: (\S+) pid (\d+)( thread \d+)? (killed: .*|exit_group .*|exit .*|cr3 .*|syscall .*)$')
    with open(out / 'table.txt', 'w') as f:
        for t, l in timed:
            m = kernel.match(l.strip())
            if not m:
                continue
            # The step in progress: the last one typed before the line arrived (a step's window is
            # typed .. its prompt back, and a line can trail its prompt by the serial port's lag).
            owner = [s for s in STEPS if s[3] <= t]
            where = '%s:%s' % (owner[-1][0], owner[-1][1]) if owner else 'none (before every step)'
            f.write('%s\t%s\n' % (where, l.strip()))
    shots = [out / 'screen-0-console-prompt.ppm', out / 'screen-1-after-ssh.ppm']
    same = all(p.exists() for p in shots) and shots[0].read_bytes() == shots[1].read_bytes()
    print('MEASURE screen before and after the sessions: %s' % ('the same' if same else 'different'))
    print('MEASURE %d kernel lines put to steps (table.txt); %d serial lines' % (
        sum(1 for _ in open(out / 'table.txt')), len(timed)))
    places = [(str(p), p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.suffix not in ('.iso', '.img', '.cpio', '.ppm')]
    hits = rows.leaks(places)
    print('MEASURE password scan: %s' % ('a password reached ' + ', '.join(hits) if hits else 'none in %d files' % len(places)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
