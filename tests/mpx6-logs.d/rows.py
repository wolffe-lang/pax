#!/usr/bin/env python3
"""rows.py — px133: the system's logs on PAX, the kernel's log on disk and the login records.

    rows.py --images DIR --elf KERNEL.elf --tier T --leg bios|uefi --accel A --out DIR

DIR is tests/mpx6-logs' G0 (files.txt, tools/mkshadow, tools/last). One leg is eight boots of one
image and one ext3 volume (label px133-log) that the image's fstab mounts on /var/log, write-back:
what logd and the login records wrote is on it at the next boot, and the rig reads it with debugfs
after each clean end. The guest is on a tap in the rig's network namespace, leased 192.168.89.20 by
dnsmasq (tests/mpx5-burrowd.d/rows.py's rig: its Console, Client and Net, imported), so the rig's
OpenSSH client logs in through burrowd as a machine on the LAN would. The passwords are made here by
Python's secrets (the burrowd rows' make_shadow), never written to a file, an argument vector or a
record.

The boots: 1 the console's refused tries and root's login, ssh sessions (a logout, a dropped one, a
command), a pipeline's SIGPIPE over ssh, logd killed and started again, logd held while the ring
wraps, what pax may read, `reboot`; 2-6 a record every 100 ms and the power cut under it (QEMU quit
from its monitor, no end); 7 a clean `poweroff`, after which the volume is read for G1-G7 and G9;
8 every capped file filled past its cap, then `poweroff`, after which the volume is read for G8.

The rows, each `PASS <row> …` or `FAIL <row> …` at column 0:
  G0  the image: /bin/logd, /bin/last, /bin/lastb and /etc/pax-boot.d/logd in it
  G1  boot 1's `user: yes pid N killed: SIGPIPE` line (a pipeline over ssh) is in kern.log after
      the reboots, under boot 1's marker, with a wall time within 5 s of the rig's clock at the
      command and its time since boot; every boot has its marker, each a different identity
  G2  200 numbered records written to /dev/kmsg as root, logd SIGKILLed after the 100th and started
      again by its loop: each record in kern.log exactly once, the sequence numbers consecutive, no
      loss named, logd's `started again` line between
  G3  logd held (SIGSTOP) while 2000 records of about 110 bytes (past the ring's 128 KiB) are
      written, then let go: one `N records lost (sequence A to B)` line whose N is the gap the
      numbers around it show, the records after it whole to the last
  G4  five power cuts (a record every 100 ms, QEMU quit from its monitor at a different phase each):
      at each, the first record not on disk was written at most BOUND s before the cut (the serial
      port's arrival time of each record is when it was written); each next boot's marker names the
      cut (`ends without logd's end line`)
  G5  the login records: `last` at the console (root still logged in on the console's line, as `tty`
      names it; pax's ssh session with its logout, the dropped session, the reboot); after boot 7,
      PAX's last and util-linux's last on the same wtmp byte for byte (no options, -x, -F, -i, -w,
      -a, -R, -n 6), PAX's `last -e` naming the dropped session `dropped`; the ssh records' host is
      what burrowd's log says of the connection (on PAX the client's address is not yet known: a
      NOTE line says so)
  G6  `lastb` as root at the console shows the two refused tries (`pax`, and `UNKNOWN` for a name
      no account has); as pax over ssh it is refused as util-linux refuses (`lastb: cannot open
      /var/log/btmp: Permission denied`, status 1); PAX's lastb and util-linux's on the same btmp
      byte for byte
  G7  as pax over ssh: kern.log and btmp cannot be read (Permission denied), wtmp can (`last`), and
      `who` is shown in a NOTE line (boreutils' who reads utmp on Linux only, a follow-on)
  G8  every capped file filled past its cap: kern.log rotated with four kept (the oldest gone, the
      new file starting with the boot's marker `(continued …)`), wtmp, btmp, sudo.log, burrowd.log
      and pax-upgrade.log each at most its cap with one `.1`, their modes kept, and everything under
      /var/log within the caps' sum
  G9  a clean end: boot 1's (`reboot`) and boot 7's (`poweroff`) logs end with logd's end line, and
      wtmp has a `shutdown` record for each; util-linux's `last -x` shows them
Exit 0 when every row held, 1 otherwise, 3 when the rig cannot run here.
"""
import argparse
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
_spec = importlib.util.spec_from_file_location('burrowd_rows', ROOT / 'tests/mpx5-burrowd.d/rows.py')
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

GUEST = B.GUEST
GUEST_AT = (B.GUEST, 22)
FAILS = []
ARGS = None
MARK = 'LOGS-ROW-'
BOUND = 1.5  # seconds: logd's 1 s flush and an fsync, with the rig's 50 ms reading of the serial port
CUTS = (4.0, 4.3, 4.6, 4.9, 5.2)
CAPS = {'kern.log': 1048576, 'wtmp': 1048576, 'btmp': 1048576, 'sudo.log': 1048576, 'burrowd.log': 1048576,
        'pax-upgrade.log': 262144}
MODES = {'kern.log': 0o600, 'wtmp': 0o644, 'btmp': 0o600, 'sudo.log': 0o600, 'burrowd.log': 0o600,
         'pax-upgrade.log': 0o644}


def say(line):
    print(line, flush=True)


def ok(row, why):
    say('PASS %s %s' % (row, why))


def bad(row, why):
    FAILS.append(row)
    say('FAIL %s %s' % (row, why))


def run(argv, **kw):
    return subprocess.run([str(x) for x in argv], capture_output=True, **kw)


# ---------------------------------------------------------------- the image and the volume

def image(work, client):
    files = [l for l in (ARGS.images / 'files.txt').read_text().splitlines() if l]
    files.append('/etc/shadow=%s:600' % (work / 'shadow'))
    keys = work / 'pax-ssh'
    keys.mkdir()
    (keys / 'authorized_keys').write_text(client.pub('pax'))
    files += ['/home/pax/.ssh/:700:1000:1000',
              '/home/pax/.ssh/authorized_keys=%s:600:1000:1000' % (keys / 'authorized_keys')]
    # burrowd's configuration as the installer writes it (every address), and a host key made by the
    # image's own burrow-keygen, so every boot shows the rig the same key.
    cfg = (ARGS.images / 'burrowd_config').read_text().splitlines()
    cfg = ['ListenAddress 0.0.0.0' if l.split()[:1] == ['ListenAddress'] else l for l in cfg]
    (work / 'burrowd_config').write_text('\n'.join(cfg) + '\n')
    hk = work / 'ssh_host_ed25519_key'
    kg = ARGS.images / 'burrow' / 'burrow-keygen'
    r = run([kg, '-q', '-t', 'ed25519', '-N', '', '-C', 'px133', '-f', hk])
    if r.returncode:
        bad('G0', 'burrow-keygen made no host key: %r' % r.stderr[-200:])
    files += ['/etc/burrowd/burrowd_config=%s:644' % (work / 'burrowd_config'),
              '/etc/burrowd/ssh_host_ed25519_key=%s:600' % hk,
              '/etc/burrowd/ssh_host_ed25519_key.pub=%s:644' % (str(hk) + '.pub')]
    pub = (str(hk) + '.pub')
    client.kh.write_text('%s %s\n' % (GUEST, ' '.join(pathlib.Path(pub).read_text().split()[:2])))
    B.run([ROOT / 'tools/mkinitramfs', work / 'image.cpio'] + files)
    B.run([ROOT / 'tools/mkimage', '--conf', ROOT / 'boot/limine-initramfs-quiet.conf', '--add', work / 'image.cpio',
           'initramfs.cpio', ARGS.elf, work / 'image.iso'])
    vol = work / 'log.img'
    B.run(['mke2fs', '-q', '-t', 'ext3', '-L', 'px133-log', '-E', 'root_owner=0:0', vol, '32M'],
          env=dict(PATH='/usr/sbin:/sbin:/usr/bin:/bin', E2FSPROGS_FAKE_TIME='1700000000'))
    return work / 'image.iso', vol


def dump(vol, name, to):
    """`name` of the log volume copied out by debugfs; its bytes, or None when it is not there."""
    to.unlink(missing_ok=True)
    run(['debugfs', '-R', 'dump -p /%s %s' % (name, to), vol])
    return to.read_bytes() if to.exists() else None


def listing(vol):
    """name -> (mode, size) of the volume's root directory."""
    r = run(['debugfs', '-R', 'ls -l /', vol])
    out = {}
    for line in r.stdout.decode(errors='replace').splitlines():
        w = line.split()
        if len(w) >= 9 and w[0].isdigit():
            try:
                out[w[-1]] = (int(w[1], 8) & 0o7777, int(w[5]))
            except ValueError:
                continue
    return out


# ---------------------------------------------------------------- the console

class Boot:
    """One boot: the Console of the burrowd rows, with a log of each serial line's arrival time."""

    def __init__(self, out, name, iso, vol):
        self.dir = out / name
        self.dir.mkdir()
        self.con = B.Console(self.dir, iso, vol)
        self.n = 0
        self.closed = False

    def close(self, timeout):
        """QEMU's end, once: waited for `halt` at most `timeout` s, then quit."""
        if not self.closed:
            self.closed = True
            self.con.quit(timeout)

    def wait(self, pattern, timeout=240):
        return self.con.wait(pattern, timeout)

    def login(self, name, password):
        c = self.con
        if not c.wait(r'login: $', 300):
            return False
        c.type(name)
        if not c.wait(r'Password: $', 30):
            return False
        c.type(password, secret=True)
        return True

    def root(self):
        if not self.login('root', B.PASSWORDS['root']):
            return False
        return bool(self.con.wait(r'[$#] $', 60))

    def cmd(self, line, timeout=120):
        self.n += 1
        start = len(self.con.seen)
        self.con.type('%s; echo %s$((%d+0))' % (line, MARK, self.n))
        m = self.con.wait(r'^%s%d$' % (MARK, self.n), timeout)
        if not m:
            return None
        body = self.con.seen[start:m.start()].decode(errors='replace')
        self.con.wait(r'[$#] $', 10)
        return body.split('\n', 1)[1] if '\n' in body else ''

    def end(self, word):
        """`reboot` or `poweroff` typed, the end waited for."""
        self.con.type(word)
        self.close(180)

    def cut(self):
        """The power cut: QEMU quit from its monitor at once, no end in the guest. The cut's time."""
        t = time.monotonic()
        self.close(0)
        return t


# ---------------------------------------------------------------- kern.log, read back

LINE = re.compile(r'^(\S+) \[\s*(\d+)\.(\d{6})\] ([a-z0-9-]+\.[a-z]+) #(\d+) (.*)$')


def records(text):
    """(index, wall, mono_us, selector, seq, text) for each record line; markers and logd's own lines
    as (index, line) in a second list."""
    recs, own = [], []
    for i, line in enumerate(text.split('\n')):
        m = LINE.match(line)
        if m:
            recs.append((i, m.group(1), int(m.group(2)) * 1000000 + int(m.group(3)), m.group(4), int(m.group(5)),
                         m.group(6)))
        elif line:
            own.append((i, line))
    return recs, own


def iso_secs(w):
    t = time.strptime(w[:19], '%Y-%m-%dT%H:%M:%S')
    return int(time.mktime(t)) - time.timezone


# ---------------------------------------------------------------- the boots

def boot1(b, client, out):
    """Boot 1: refused tries and root at the console, ssh, the SIGPIPE, logd killed, the ring wrapped."""
    seen = {}
    c = b.con
    if not c.wait(r'logd: started; the kernel\'s log is /var/log/kern.log', 300):
        bad('G0', 'no `logd: started` line on the console before the login prompt: %r' % c.text()[-400:])
    # Two refused tries: pax with a wrong password, then a name no account has.
    for name, pw in (('pax', B.PASSWORDS['wrong']), ('px133-nosuch', 'x')):
        if not b.login(name, pw) or not c.wait(r'Login incorrect', 30):
            bad('G6', 'the console did not refuse %s' % name)
    if not b.root():
        bad('G5', 'root could not log in at the console')
        return seen
    # The console's line in the login records: the device `tty` names there (QEMU's serial port).
    seen['con_line'] = re.sub(r'^/dev/', '', (b.cmd('tty') or '').strip()) or 'console'
    # ssh: a terminal session with a logout, a dropped one, a command.
    t = client.terminal(GUEST_AT, 33, 97)
    m = t.expect(B.PROMPT, 30)
    at = t.type(b'tty\r')
    tty1 = t.expect(rb'^/dev/(pts/\d+)$', 10, at)
    t.expect(B.PROMPT, 10, at)
    time.sleep(1.2)
    t.type(b'exit\r')
    t.pump(2)
    t.close()
    seen['tty1'] = tty1.group(1).decode() if tty1 else None
    time.sleep(1.2)
    t = client.terminal(GUEST_AT, 33, 97)
    t.expect(B.PROMPT, 30)
    at = t.type(b'tty\r')
    tty2 = t.expect(rb'^/dev/(pts/\d+)$', 10, at)
    t.expect(B.PROMPT, 10, at)
    t.type(b'sleep 100\r')
    t.pump(2)
    t.p.kill()          # the client dropped: its process killed, as a laptop's lid shuts
    t.p.wait()
    os.close(t.master)
    seen['tty2'] = tty2.group(1).decode() if tty2 else None
    time.sleep(3)
    # G1: a pipeline's writer killed by SIGPIPE over ssh, the rig's clock beside it.
    seen['g1_at'] = time.time()
    r = client.ssh(GUEST_AT, ['yes | head -n 1'])
    seen['g1'] = r
    pid = c.wait(r'user: yes pid (\d+) killed: SIGPIPE[^\n]*\n', 30)
    seen['g1_pid'] = pid.group(1).decode() if pid else None
    # G7: what pax may read; who.
    seen['g7'] = {k: client.ssh(GUEST_AT, [cmd]) for k, cmd in (
        ('kern', 'cat /var/log/kern.log'), ('btmp', 'cat /var/log/btmp'), ('wtmp', 'last -n 3'), ('who', 'who'),
        ('lastb', 'lastb'))}
    # G5, G6 at the console: last and lastb as root.
    seen['last'] = b.cmd('last')
    seen['lastb'] = b.cmd('lastb')
    seen['who'] = b.cmd('who')
    # G2: 200 records, logd SIGKILLed between the 100th and the 101st, started again by its loop.
    b.cmd('/root/rows/records.sh px133-g2 1 100', 300)
    seen['g2_pid'] = (b.cmd('cat /var/run/logd.pid') or '').strip()
    b.cmd('kill -9 $(cat /var/run/logd.pid)')
    b.cmd('/root/rows/records.sh px133-g2 101 200', 300)
    time.sleep(3)
    seen['g2_pid2'] = (b.cmd('cat /var/run/logd.pid') or '').strip()
    # G3: logd held while the ring wraps.
    b.cmd('kill -STOP $(cat /var/run/logd.pid)')
    b.cmd('/root/rows/flood.sh 2000', 900)
    b.cmd('kill -CONT $(cat /var/run/logd.pid)')
    time.sleep(4)
    b.end('reboot')
    return seen


def cut_boot(b, k):
    """A record every 100 ms, the power cut under it: each record's arrival time on the serial port
    (the time it was written: the kernel writes a line to the port as it keeps it), and the cut's."""
    if not b.root():
        bad('G4', 'cut %d: root could not log in' % k)
        b.cut()
        return None
    c = b.con
    c.type('/root/rows/ticks.sh %d &' % k)
    arrivals = {}
    rx = re.compile(rb'px133-tick %d (\d+)\n' % k)
    t0 = time.monotonic()
    pos = len(c.seen)
    while time.monotonic() - t0 < CUTS[k - 1] + 1.0:
        c.pump(0.05)
        now = time.monotonic()
        for m in rx.finditer(c.seen, pos):
            arrivals.setdefault(int(m.group(1)), now)
        last_nl = c.seen.rfind(b'\n')
        if last_nl >= pos:
            pos = last_nl + 1
        if arrivals and now - min(arrivals.values()) >= CUTS[k - 1]:
            break
    t_cut = b.cut()
    return arrivals, t_cut


def main():
    global ARGS
    a = argparse.ArgumentParser()
    for k in ('images', 'elf', 'tier', 'leg', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    ARGS = a.parse_args()
    ARGS.images = pathlib.Path(ARGS.images)
    B.ARGS = ARGS
    out = pathlib.Path(ARGS.out)
    why = B.rig_missing()
    for t in ('debugfs', 'last', 'lastb'):
        if not shutil.which(t, path='/usr/sbin:/sbin:/usr/bin:/bin'):
            why.append('no ' + t)
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
        bad('G0', 'the tree builds no %s' % missing)
    client = B.Client(out)
    B.make_shadow(work)
    iso, vol = image(work, client)
    if 'G0' not in FAILS:
        ok('G0', 'the image (%d bytes) with logd, last, lastb and both hooks; the log volume' % iso.stat().st_size)
    net = B.Net(out)
    seen = {}
    cuts = {}
    try:
        b = Boot(out, 'boot1', iso, vol)
        try:
            seen = boot1(b, client, out)
        finally:
            b.close(180)
        for k in range(1, len(CUTS) + 1):
            b = Boot(out, 'boot%d-cut' % (k + 1), iso, vol)
            try:
                cuts[k] = cut_boot(b, k)
            finally:
                b.close(0)
        b = Boot(out, 'boot7', iso, vol)
        try:
            if b.root():
                seen['last7'] = b.cmd('last')
                b.end('poweroff')
            else:
                bad('G9', 'root could not log in at boot 7')
        finally:
            b.close(180)
        story = work / 'story.img'
        shutil.copy(vol, story)
        b = Boot(out, 'boot8', iso, vol)
        try:
            if b.root():
                seen['fill'] = b.cmd('/root/rows/fill.sh', 300)
                b.cmd('kill $(cat /var/run/logd.pid)')
                time.sleep(3)
                b.cmd('/root/rows/records.sh px133-g8 1 300', 300)
                time.sleep(3)
                seen['ls8'] = b.cmd('ls -l /var/log')
                b.end('poweroff')
            else:
                bad('G8', 'root could not log in at boot 8')
        finally:
            b.close(180)
    finally:
        net.close()
    judge(out, work, story, vol, seen, cuts)
    say('mpx6-logs %s %s: %s' % (ARGS.tier, ARGS.leg, 'FAIL ' + ' '.join(FAILS) if FAILS else 'PASS'))
    return 1 if FAILS else 0


# ---------------------------------------------------------------- the verdicts

def judge(out, work, story, vol, seen, cuts):
    kern = dump(story, 'kern.log', work / 'kern.log')
    k1 = dump(story, 'kern.log.1', work / 'kern.log.1')
    text = ((k1 or b'') + (kern or b'')).decode(errors='replace')
    (work / 'kern-all.txt').write_text(text)
    recs, own = records(text)
    markers = [l for _, l in own if ' == boot ' in l]
    g1(text, recs, own, markers, seen)
    g2(recs, own)
    g3(recs, own)
    g4(recs, own, markers, cuts)
    wtmp = dump(story, 'wtmp', work / 'wtmp')
    btmp = dump(story, 'btmp', work / 'btmp')
    g5(work, wtmp, seen)
    g6(work, btmp, seen)
    g7(seen)
    g9(own, wtmp, work)
    g8(work, vol, seen)


def g1(text, recs, own, markers, seen):
    if not text:
        bad('G1', 'no /var/log/kern.log on the volume after eight boots')
        return
    ids = [re.search(r'== (boot \S+ started \S+)', m).group(1) for m in markers]
    pid = seen.get('g1_pid')
    line = [r for r in recs if pid and r[5].startswith('user: yes pid %s killed: SIGPIPE' % pid)]
    if not line:
        bad('G1', 'kern.log has no `user: yes pid %s killed: SIGPIPE` line (the console saw pid %s); %d markers'
            % (pid, pid, len(markers)))
        return
    i, w, mono, sel, seq, t = line[0]
    before = [l for j, l in own if j < i and ' == boot ' in l]
    skew = abs(iso_secs(w) - seen['g1_at']) if w != '-' else None
    good = (len(ids) >= 7 and len(set(ids)) == len(ids) and skew is not None and skew <= 5 and sel == 'kern.info'
            and before and before[-1] == markers[0])
    (ok if good else bad)('G1', 'the SIGPIPE line `%s` at %s [%d.%06d] %s #%d, %s s from the rig\'s clock, under the '
                          'first boot\'s marker; %d boots marked, %d identities'
                          % (t[:60], w, mono // 1000000, mono % 1000000, sel, seq,
                             '%.1f' % skew if skew is not None else 'no wall time', len(ids), len(set(ids))))


def g2(recs, own):
    got = [(r[4], int(r[5].split()[1])) for r in recs if r[5].startswith('px133-g2 ')]
    nums = [n for _, n in got]
    twice = sorted({n for n in nums if nums.count(n) > 1})
    absent = sorted(set(range(1, 201)) - set(nums))
    # Every record kern.log holds from the first numbered one to the last, the kernel's own lines between
    # them too (logd's SIGKILL is one): their sequence numbers one apart, none skipped, none twice.
    at = [k for k, r in enumerate(recs) if r[5].startswith('px133-g2 ')]
    span = recs[at[0]:at[-1] + 1] if at else []
    seqs = [r[4] for r in span]
    consecutive = bool(span) and all(b2 - a2 == 1 for a2, b2 in zip(seqs, seqs[1:]))
    again = [l for i, l in own if '== logd started again in ' in l and span and span[0][0] < i < span[-1][0]]
    lostg2 = [l for i, l in own if ('records lost' in l or 'record lost' in l) and span and span[0][0] < i < span[-1][0]]
    good = not twice and not absent and consecutive and again and not lostg2
    (ok if good else bad)('G2', '%d of 200 records once each (twice: %s, absent: %s), the sequence numbers from the '
                          'first to the last %s, %d restart line(s) and %d loss line(s) between them'
                          % (len(set(nums)), twice[:5], absent[:5], 'consecutive' if consecutive else 'NOT consecutive',
                             len(again), len(lostg2)))


def g3(recs, own):
    flood = [r for r in recs if r[5].startswith('px133-flood ')]
    lost = [(i, l) for i, l in own if re.search(r'logd: \d+ records? lost \(sequence \d+ to \d+\): the ring overtook', l)]
    if not flood or not lost:
        bad('G3', '%d flood records and %d `records lost` lines in kern.log' % (len(flood), len(lost)))
        return
    li, ll = lost[-1]
    m = re.search(r'logd: (\d+) records? lost \(sequence (\d+) to (\d+)\)', ll)
    n, a, z = int(m.group(1)), int(m.group(2)), int(m.group(3))
    prev = [r for r in recs if r[0] < li]
    nxt = [r for r in recs if r[0] > li]
    gap_ok = prev and nxt and prev[-1][4] == a - 1 and nxt[0][4] == z + 1 and n == z - a + 1
    tail = [r for r in nxt if r[5].startswith('px133-flood ')]
    nums = [int(r[5].split()[1]) for r in tail]
    whole = nums and nums[-1] == 2000 and all(b2 - a2 == 1 for a2, b2 in zip(nums, nums[1:]))
    (ok if gap_ok and whole else bad)('G3', '`%s`; before it #%s, after it #%s; then floods %s to %s whole'
                                      % (ll.split(' logd: ')[-1], prev[-1][4] if prev else '-',
                                         nxt[0][4] if nxt else '-', nums[0] if nums else '-', nums[-1] if nums else '-'))


def g4(recs, own, markers, cuts):
    lines = []
    good = True
    for k, got in sorted(cuts.items()):
        if not got:
            good = False
            lines.append('cut %d: no run' % k)
            continue
        arrivals, t_cut = got
        on_disk = [int(r[5].split()[2]) for r in recs if r[5].startswith('px133-tick %d ' % k)]
        kd = max(on_disk) if on_disk else -1
        first_lost = kd + 1
        if first_lost in arrivals:
            loss = t_cut - arrivals[first_lost]
        else:
            loss = 0.0
        last_seen = max(arrivals) if arrivals else -1
        lines.append('cut %d: %d ticks seen, %d on disk, loss %.2f s' % (k, last_seen + 1, kd + 1, loss))
        if loss > BOUND or not arrivals:
            good = False
    named = [m for m in markers if "ends without logd's end line" in m]
    if len(named) != len(cuts):
        good = False
    (ok if good else bad)('G4', '%s; %d markers name a cut (want %d); the bound %.1f s'
                          % ('; '.join(lines), len(named), len(cuts), BOUND))


def last_both(work, path, prog, opts):
    env = dict(PATH='/usr/bin:/bin', TZ='UTC', LC_ALL='C')
    pax = ARGS.images / 'tools' / 'last'
    argv0 = work / prog
    if not argv0.exists():
        argv0.symlink_to(pax)
    rp = run([argv0] + opts + ['-f', path], env=env)
    rl = run([prog] + opts + ['-f', path], env=env)
    return rp, rl


def g5(work, wtmp, seen):
    if wtmp is None:
        bad('G5', 'no /var/log/wtmp on the volume')
        return
    con = seen.get('last') or ''
    sess = [l for l in con.splitlines() if l.startswith('pax ')]
    line = re.escape(seen.get('con_line') or 'console')
    want_console = re.search(r'^root\s+%s\s.*still logged in' % line, con, re.M)
    want_boot = re.search(r'^reboot\s+system boot\s', con, re.M)
    lines_ok = bool(want_console and want_boot and len(sess) >= 2)
    diffs = []
    for opts in ([], ['-x'], ['-F'], ['-i'], ['-w'], ['-a'], ['-R'], ['-n', '6']):
        rp, rl = last_both(work, work / 'wtmp', 'last', opts)
        if (rp.returncode, rp.stdout, rp.stderr) != (rl.returncode, rl.stdout, rl.stderr):
            diffs.append(' '.join(opts) or '(none)')
            (work / ('last%s.pax' % '_'.join(opts))).write_bytes(rp.stdout + rp.stderr)
            (work / ('last%s.linux' % '_'.join(opts))).write_bytes(rl.stdout + rl.stderr)
    rp, _ = last_both(work, work / 'wtmp', 'last', ['-e'])
    ended = rp.stdout.decode(errors='replace')
    dropped = re.search(r'^pax\s+%s\s.*dropped' % re.escape(seen.get('tty2') or 'pts/?'), ended, re.M)
    good = lines_ok and not diffs and dropped
    (ok if good else bad)('G5', 'at the console: root on the console %s, %d ssh session(s) of pax, the reboot %s; '
                          'PAX\'s last against util-linux\'s on the same wtmp: %s; last -e names the dropped session: %s'
                          % ('still logged in' if want_console else 'MISSING', len(sess),
                             'shown' if want_boot else 'MISSING', 'equal' if not diffs else 'DIFFER at ' + ', '.join(diffs),
                             'yes' if dropped else 'no'))
    hosts = sorted({l.split()[2] for l in sess if len(l.split()) > 2 and re.match(r'^[0-9.:a-f]+$', l.split()[2])})
    say('NOTE G5 the ssh records\' host: %s (on PAX the client\'s address is not yet known to burrowd: a follow-on '
        'gives PAX /proc/net/tcp)' % (', '.join(hosts) or 'none'))


def g6(work, btmp, seen):
    con = seen.get('lastb') or ''
    line = re.escape(seen.get('con_line') or 'console')
    tries = re.search(r'^pax\s+%s\s' % line, con, re.M) and re.search(r'^UNKNOWN\s+%s\s' % line, con, re.M)
    r = seen.get('g7', {}).get('lastb')
    refused = r and r[0] == 1 and b'lastb: cannot open /var/log/btmp: Permission denied' in r[2]
    same = False
    if btmp is not None:
        rp, rl = last_both(work, work / 'btmp', 'lastb', [])
        same = (rp.returncode, rp.stdout, rp.stderr) == (rl.returncode, rl.stdout, rl.stderr)
        if not same:
            (work / 'lastb.pax').write_bytes(rp.stdout + rp.stderr)
            (work / 'lastb.linux').write_bytes(rl.stdout + rl.stderr)
    (ok if tries and refused and same else bad)('G6', 'root\'s lastb shows pax and UNKNOWN on the console: %s; pax\'s '
                                                'lastb %s; PAX\'s lastb and util-linux\'s on the same btmp: %s'
                                                % ('yes' if tries else 'no', B.show(r) if r else '-',
                                                   'equal' if same else 'DIFFER'))


def g7(seen):
    g = seen.get('g7', {})
    k, bt, w, who = (g.get(x) for x in ('kern', 'btmp', 'wtmp', 'who'))
    good = (k and k[0] != 0 and b'Permission denied' in k[2] and bt and bt[0] != 0 and b'Permission denied' in bt[2]
            and w and w[0] == 0 and b'reboot' in w[1])
    (ok if good else bad)('G7', 'as pax: kern.log %s; btmp %s; last %s'
                          % tuple(B.show(x) if x else '-' for x in (k, bt, w)))
    # boreutils' who reads utmp on Linux alone (its login ABI check names linux/x86_64); PAX's utmp is the
    # same x86-64 layout, so who waits on boreutils taking PAX's name: said, not held.
    say('NOTE G7 who as pax: %s (boreutils\' who reads utmp on Linux only: a boreutils follow-on)'
        % (B.show(who) if who else '-'))


def g8(work, vol, seen):
    ls = listing(vol)
    over = []
    for name, cap in CAPS.items():
        mode, size = ls.get(name, (None, None))
        if size is None or size > cap + 65536 or mode != MODES[name]:
            over.append('%s %s %s' % (name, size, oct(mode) if mode is not None else '-'))
        one = ls.get(name + '.1')
        if not one:
            over.append(name + '.1 missing')
    k = {n: (dump(vol, n, work / ('g8-' + n)) or b'') for n in ('kern.log', 'kern.log.1', 'kern.log.2', 'kern.log.3',
                                                               'kern.log.4')}
    kept = (k['kern.log.2'].startswith(b'px133-fill kern.log.1') and k['kern.log.3'].startswith(b'px133-fill kern.log.2')
            and k['kern.log.4'].startswith(b'px133-fill kern.log.3') and b'px133-fill kern.log line' in k['kern.log.1']
            and not any(b'px133-fill kern.log.4' in v for v in k.values()) and b'(continued from kern.log.1)' in k['kern.log'])
    total = sum(s for n, (_, s) in ls.items() if n not in ('.', '..', 'lost+found'))
    budget = sum(CAPS.values()) * 2 + 3 * CAPS['kern.log'] + 262144 * 5 + 65536
    good = not over and kept and total <= budget
    (ok if good else bad)('G8', 'over or missing: %s; kern.log rotated with four kept, the oldest gone: %s; /var/log '
                          'holds %d bytes, within %d' % (over or 'none', 'yes' if kept else 'no', total, budget))


def g9(own, wtmp, work):
    ends = [l for _, l in own if "SIGTERM from the kernel's end" in l]
    downs = 0
    if wtmp:
        for i in range(0, len(wtmp) - 383, 384):
            if wtmp[i] == 1 and wtmp[i + 44:i + 52] == b'shutdown':
                downs += 1
    rl = run(['last', '-x', '-f', work / 'wtmp'], env=dict(PATH='/usr/bin:/bin', TZ='UTC', LC_ALL='C'))
    shown = len(re.findall(rb'^shutdown\s+system down', rl.stdout, re.M))
    (ok if len(ends) == 2 and downs == 2 and shown == 2 else bad)(
        'G9', '%d end lines in kern.log, %d shutdown records in wtmp, %d `shutdown system down` lines in util-linux\'s '
        'last -x (want 2 each: boot 1\'s reboot, boot 7\'s poweroff)' % (len(ends), downs, shown))


if __name__ == '__main__':
    sys.exit(main())
