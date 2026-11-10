#!/usr/bin/env python3
"""px115: the upgrade over ssh on an 860-shaped installed disk under QEMU (the contract's leg).

    ssh-upgrade.py REPO WORK DISK STICK BUILD FIRMWARE [ROWS]

DISK is an installed 860-shaped disk on the burrowd image (its burrowd and its /etc/pax-boot.d hooks are that
image's), STICK the stick of that image; both are copied and never written. BUILD holds the head's
tools/mkinstall output (pax-install, pax-upgrade) and kernel.elf (tools/build-kernel's). FIRMWARE is bios or uefi.
Run inside the net rig container (QEMU, OVMF, the tap, dnsmasq, OpenSSH; PAX_SSH its bin directory). Offline first
(debugfs and mtools, black boxes): the head's pax-upgrade, pax-install, boot hook and entry onto the disk's root and
its kernel at the ESP's /boot/pax (the installed system that has pax-upgrade); wolf (uid 1000, group sudo) a
password made at run time (never written to a file, an argument vector or a log) and the client's key. The archive
sent is the stick's own, repacked: the head's kernel and tools, a marker, and an /etc/pax-release one second newer
than the disk's. The disk boots on ahci (a test model and serial) and igb on the tap; dnsmasq leases it an address.

Rows (ROWS a comma list; all by default), each PASS or FAIL by name, on FIRMWARE:
  S1 upgrade   receive over ssh, status, arm over ssh (sudo -k -S, --reboot); the staged boot (attempt 1 of 2,
               the root at /mnt/target by the arm's targets line, / the archive), apply, the reboot; burrowd answers;
               status says upgraded, then cleaned; the marker on the root, wolf's file kept, the staged files gone
  S2 fallback  received and armed, powered off; the staged archive changed on the host: the staged kernel refuses
               it (its sha256), the installed root boots, its hook disarms and reboots into its own kernel; status
               says why; no marker; the ESP's configuration the installer's again
  S3 cut-send  QEMU killed while the archive is being received: booted again, nothing received, the system as it
               was; sent again whole, received
  S4 cut-apply QEMU killed once the staged upgrade has begun writing: booted again, the second attempt finishes it
"""
import warnings
warnings.simplefilter('ignore', DeprecationWarning)
import crypt
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO, WORK, DISK, STICK, BUILD = map(Path, sys.argv[1:6])
FW = sys.argv[6]
ROWS = sys.argv[7].split(',') if len(sys.argv) > 7 else ['S1', 'S2', 'S3', 'S4']
ROOT_AT, ESP_AT = 69206016, 2097152
TAP, HOST, GUEST, MAC = 'pxup0', '192.168.93.1', '192.168.93.20', '52:54:00:12:93:20'
MODEL, SERIAL = 'PX115 UPGRADE DISK', 'PX115-SSH-0001'
SSH = Path(os.environ.get('PAX_SSH', '/opt/openssh-10.2p1/bin'))
PW = secrets.token_hex(8)
OVMF_CODE = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
OVMF_VARS = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
MARKER = 'px115-ssh-upgrade-marker'
os.environ['MTOOLS_SKIP_CHECK'] = '1'
WORK.mkdir(parents=True, exist_ok=True)
bad = []
result = {'leg': 'px115 upgrade over ssh', 'firmware': FW, 'rows': {}}


def log(msg):
    line = f'{time.strftime("%H:%M:%S")} {msg}'
    assert PW not in line
    print(line, flush=True)


def row(name, ok, what):
    result['rows'][name] = {'ok': ok, 'what': what}
    if ok:
        print(f'PASS {name} {FW}: {what}', flush=True)
    else:
        bad.append(name)
        print(f'FAIL {name} {FW}: {what}', flush=True)
    (WORK / f'result-{FW}.json').write_text(json.dumps(result, indent=1))


def run(argv, data=None, check=True, timeout=900, **kw):
    r = subprocess.run([str(x) for x in argv], input=data, capture_output=True, timeout=timeout, **kw)
    if check and r.returncode:
        raise RuntimeError(f'{argv[:3]}: exit {r.returncode}: {r.stderr.decode(errors="replace")[-400:]}')
    return r


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


# --- the archive -----------------------------------------------------------------------------------------------

def read_newc(blob):
    rows, off = [], 0
    while True:
        h = blob[off:off + 110]
        assert h[:6] == b'070701', 'not newc'
        f = [int(h[i:i + 8], 16) for i in range(6, 110, 8)]
        name = blob[off + 110:off + 110 + f[11] - 1].decode()
        start = (off + 110 + f[11] + 3) & ~3
        data = blob[start:start + f[6]]
        off = (start + f[6] + 3) & ~3
        if name == 'TRAILER!!!':
            return rows
        rows.append([name, f[1], f[2], f[3], data])


def write_newc(rows, out):
    with open(out, 'wb') as o:
        for ino, (name, mode, uid, gid, data) in enumerate(rows + [['TRAILER!!!', 0, 0, 0, b'']], 1):
            enc = name.encode() + b'\0'
            fields = [ino, mode, uid, gid, 2 if mode & 0o170000 == 0o040000 else 1, 0, len(data), 0, 0, 0, 0, len(enc), 0]
            o.write(b'070701' + b''.join(f'{n:08x}'.encode() for n in fields) + enc)
            o.write(b'\0' * (-o.tell() % 4))
            o.write(data)
            o.write(b'\0' * (-o.tell() % 4))


def make_archive(epoch):
    """The stick's own archive with the head's kernel, pax-install, pax-upgrade, hook and entry, the marker, and
    a pax-release one second newer than the disk's."""
    src = WORK / 'stick-initramfs.cpio'
    if not src.exists():
        run(['mcopy', '-n', '-i', f'{STICK}@@{ESP_AT}', '::/boot/initramfs.cpio', src])
    rows = read_newc(src.read_bytes())
    by = {r[0].lstrip('./'): r for r in rows}
    kernel = (BUILD / 'kernel.elf').read_bytes()
    commit = run(['git', '-C', REPO, 'rev-parse', 'HEAD']).stdout.decode().strip()
    rel = by['etc/pax-release'][4].decode().splitlines()
    rel = [f'kernel {commit} {hashlib.sha256(kernel).hexdigest()}' if l.startswith('kernel ') else
           f'source-date-epoch {epoch} -' if l.startswith('source-date-epoch ') else l for l in rel]
    put = {'boot/pax': (0o100644, kernel), 'bin/pax-install': (0o100755, (BUILD / 'pax-install').read_bytes()),
           'bin/pax-upgrade': (0o100755, (BUILD / 'pax-upgrade').read_bytes()),
           'etc/pax-boot.d/pax-upgrade': (0o100755, (REPO / 'user/install/pax-upgrade/boot-hook').read_bytes()),
           'usr/share/pax-upgrade/entry': (0o100644, (REPO / 'user/install/pax-upgrade/entry').read_bytes()),
           'etc/px115-marker': (0o100644, (MARKER + '\n').encode()),
           'etc/pax-release': (0o100644, ('\n'.join(rel) + '\n').encode())}
    for d in ('usr/share/pax-upgrade', 'etc/pax-boot.d'):
        if d not in by:
            rows.append([d, 0o40755, 0, 0, b''])
            by[d] = rows[-1]
    for name, (mode, data) in put.items():
        if name in by:
            by[name][1], by[name][4] = mode, data
        else:
            rows.append([name, mode, 0, 0, data])
    out = WORK / 'sent.cpio'
    write_newc(rows, out)
    return out, sha_file(out), commit


# --- the disk --------------------------------------------------------------------------------------------------

def debugfs(img, cmds, write=True):
    f = WORK / 'debugfs.cmds'
    f.write_text('\n'.join(cmds) + '\n')
    r = run(['debugfs'] + (['-w'] if write else []) + ['-f', f, f'{img}?offset={ROOT_AT}'])
    f.unlink()
    err = r.stderr.decode(errors='replace')
    if write and ('Could not' in err or 'not found' in err.replace('File not found by ext2_lookup', '')):
        raise RuntimeError('debugfs: ' + err[-600:])
    return r.stdout.decode(errors='replace')


def cat(img, path):
    return run(['debugfs', '-R', f'cat {path}', f'{img}?offset={ROOT_AT}']).stdout


def exists(img, path):
    return 'File not found' not in run(['debugfs', '-R', f'stat {path}', f'{img}?offset={ROOT_AT}'], check=False).stderr.decode(errors='replace')


def esp_text(img, path):
    r = run(['mtype', '-i', f'{img}@@{ESP_AT}', f'::{path}'], check=False)
    return r.stdout.decode(errors='replace') if r.returncode == 0 else None


def prepare(name, pub):
    """A copy of DISK with the head's tools, wolf's password and the client's key, and a file of wolf's."""
    img = WORK / f'{name}.img'
    if img.exists():
        img.unlink()
    run(['cp', '--sparse=always', DISK, img], timeout=1800)
    t = WORK / 'plant'
    t.mkdir(exist_ok=True)
    shutil.copy(BUILD / 'pax-upgrade', t / 'pax-upgrade')
    shutil.copy(BUILD / 'pax-install', t / 'pax-install')
    shutil.copy(REPO / 'user/install/pax-upgrade/boot-hook', t / 'hook')
    shutil.copy(REPO / 'user/install/pax-upgrade/entry', t / 'entry')
    (t / 'notes').write_text(f'wolf\'s own file {name}\n')
    shadow = cat(img, '/etc/shadow').decode()
    salt = ''.join(secrets.choice('./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for _ in range(16))
    h = crypt.crypt(PW, '$7$F6..../....' + salt + '$')
    assert h and h.startswith('$7$F6..../....'), 'the C library made no $7$ hash'
    lines = [':'.join([f[0], h] + f[2:]) if f[0] == 'wolf' else l for l in shadow.splitlines() for f in [l.split(':')]]
    fd = os.open(t / 'shadow', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, ('\n'.join(lines) + '\n').encode())
    os.close(fd)
    (t / 'keys').write_text(pub)
    cmds = ['rm /etc/shadow', 'cd /etc', f'write {t / "shadow"} shadow', 'sif /etc/shadow mode 0100600',
            'rm /bin/pax-install', 'cd /bin', f'write {t / "pax-install"} pax-install', 'sif /bin/pax-install mode 0100755',
            f'write {t / "pax-upgrade"} pax-upgrade', 'sif /bin/pax-upgrade mode 0100755',
            'mkdir /etc/pax-boot.d', 'cd /etc/pax-boot.d', f'write {t / "hook"} pax-upgrade',
            'sif /etc/pax-boot.d/pax-upgrade mode 0100755', 'mkdir /usr/share/pax-upgrade', 'cd /usr/share/pax-upgrade',
            f'write {t / "entry"} entry', 'mkdir /home/wolf/.ssh', 'sif /home/wolf/.ssh mode 040700',
            'sif /home/wolf/.ssh uid 1000', 'sif /home/wolf/.ssh gid 1000', 'cd /home/wolf/.ssh',
            f'write {t / "keys"} authorized_keys', 'sif /home/wolf/.ssh/authorized_keys mode 0100600',
            'sif /home/wolf/.ssh/authorized_keys uid 1000', 'sif /home/wolf/.ssh/authorized_keys gid 1000',
            'cd /home/wolf', f'write {t / "notes"} px115-notes.txt', 'sif /home/wolf/px115-notes.txt uid 1000',
            'sif /home/wolf/px115-notes.txt gid 1000']
    debugfs(img, cmds)
    (t / 'shadow').unlink()
    run(['mcopy', '-o', '-i', f'{img}@@{ESP_AT}', BUILD / 'kernel.elf', '::/boot/pax'])
    return img


# --- the machine -----------------------------------------------------------------------------------------------

class Net:
    def __init__(self):
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)
        run(['ip', 'tuntap', 'add', 'dev', TAP, 'mode', 'tap'])
        run(['ip', 'addr', 'add', HOST + '/24', 'dev', TAP])
        run(['ip', 'link', 'set', TAP, 'up'])
        self.log = WORK / 'dnsmasq.log'
        self.log.write_text('')
        self.p = subprocess.Popen(['dnsmasq', '--no-daemon', '--user=root', '--port=0', '--interface=' + TAP,
                                   '--bind-interfaces', '--dhcp-authoritative', '--leasefile-ro',
                                   f'--dhcp-range={GUEST},{GUEST},255.255.255.0,2m', f'--dhcp-host={MAC},{GUEST}',
                                   '--dhcp-option=3,' + HOST, '--log-dhcp', '--log-facility=' + str(self.log)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self):
        self.p.terminate()
        self.p.wait(timeout=10)
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)


class Machine:
    """The disk alone on ahci, igb on the tap, the serial port to a file; QEMU runs across the guest's reboots."""

    def __init__(self, img, name):
        self.serial = WORK / f'{name}.serial'
        self.serial.write_bytes(b'')
        a = ['qemu-system-x86_64', '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '2', '-m', '4096',
             '-drive', f'file={img},if=none,id=d0,format=raw,cache=unsafe',
             '-device', 'ahci,id=ahci0', '-device', f'ide-hd,drive=d0,bus=ahci0.0,model={MODEL},serial={SERIAL}',
             '-netdev', f'tap,id=n0,ifname={TAP},script=no,downscript=no', '-device', f'igb,netdev=n0,mac={MAC}',
             '-display', 'none', '-serial', f'file:{self.serial}', '-monitor', 'none']
        if FW == 'uefi':
            vars_fd = WORK / f'{name}-vars.fd'
            shutil.copy(OVMF_VARS, vars_fd)
            a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
                  '-drive', f'if=pflash,format=raw,unit=1,file={vars_fd}']
        self.q = subprocess.Popen(a, stdin=subprocess.DEVNULL, stdout=open(WORK / f'{name}.qemu', 'wb'),
                                  stderr=subprocess.STDOUT)

    def text(self):
        return re.sub(r'\x1b\[[0-9;?=]*[A-Za-z]', '', self.serial.read_bytes().decode('latin-1')).replace('\r', '')

    def wait(self, pattern, timeout, after=0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            m = re.search(pattern, self.text()[after:], re.M)
            if m:
                return True
            if self.q.poll() is not None:
                return False
            time.sleep(1)
        return False

    def kill(self):
        if self.q.poll() is None:
            self.q.kill()
        self.q.wait()


def ssh_base(key, kh):
    return [SSH / 'ssh', '-F', 'none', '-o', f'UserKnownHostsFile={kh}', '-o', 'StrictHostKeyChecking=no',
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'PreferredAuthentications=publickey',
            '-o', 'ConnectTimeout=20', '-o', 'WarnWeakCrypto=no', '-i', key, f'wolf@{GUEST}']


def env():
    return dict(PATH='/usr/bin:/bin', HOME=str(WORK / 'client'), LC_ALL='C')


def ssh(base, cmd, data=None, timeout=900):
    return subprocess.run([str(x) for x in base + [cmd]], input=data, capture_output=True, env=env(), timeout=timeout)


def answers(timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            s = socket.create_connection((GUEST, 22), timeout=3)
            b = s.recv(64)
            s.close()
            if b.startswith(b'SSH-'):
                return True
        except OSError:
            pass
        time.sleep(2)
    return False


def send(base, archive, digest, timeout=1800):
    with open(archive, 'rb') as f:
        return subprocess.run([str(x) for x in base + [f'pax-upgrade receive --sha256 {digest}']], stdin=f,
                              capture_output=True, env=env(), timeout=timeout)


def root(base, cmd):
    return ssh(base, f"sudo -k -S -p '' {cmd}", data=(PW + '\n').encode())


# --- the rows --------------------------------------------------------------------------------------------------

def main():
    cdir = WORK / 'client'
    if cdir.exists():
        shutil.rmtree(cdir)
    cdir.mkdir(mode=0o700)
    key, kh = cdir / 'id_ed25519', cdir / 'known_hosts'
    run([SSH / 'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'px115-leg', '-f', key])
    pub = Path(str(key) + '.pub').read_text()
    base = ssh_base(key, kh)
    old_rel = cat(DISK, '/etc/pax-release').decode()
    old_epoch = int(next(l.split()[1] for l in old_rel.splitlines() if l.startswith('source-date-epoch ')))
    archive, digest, commit = make_archive(old_epoch + 1)
    log(f'the archive sent: {archive.stat().st_size} bytes, sha256 {digest}, kernel {commit}')
    result.update(archive_sha256=digest, archive_bytes=archive.stat().st_size, commit=commit)
    net = Net()
    try:
        for r in ROWS:
            t0 = time.monotonic()
            try:
                {'S1': s1, 'S2': s2, 'S3': s3, 'S4': s4}[r](base, pub, archive, digest, commit)
            except Exception as e:
                row(r, False, f'stopped: {e!r}')
            log(f'{r} took {time.monotonic() - t0:.0f} s')
    finally:
        net.close()
    print(f'ssh-upgrade {FW}: ' + ('FAIL ' + ','.join(bad) if bad else 'PASS'), flush=True)
    return 1 if bad else 0


def boot(img, name):
    m = Machine(img, name)
    if not answers(300):
        m.kill()
        raise RuntimeError('burrowd never answered on port 22; the serial log\'s last lines: ' +
                           ' | '.join(m.text().strip().split('\n')[-6:]))
    return m


def finish(m, base):
    root(base, '/bin/pelt -c poweroff')
    t0 = time.monotonic()
    while m.q.poll() is None and time.monotonic() - t0 < 120:
        time.sleep(1)
    m.kill()


def s1(base, pub, archive, digest, commit, name='S1'):
    img = prepare(f's1-{FW}', pub)
    m = boot(img, f's1-{FW}')
    try:
        t = time.monotonic()
        r = send(base, archive, digest)
        secs = time.monotonic() - t
        st = ssh(base, 'pax-upgrade status').stdout.decode(errors='replace')
        if r.returncode != 0 or f'sha256 {digest}' not in st:
            return row(name, False, f'receive exit {r.returncode}: {r.stderr.decode(errors="replace")[-300:]} | {st}')
        mark = len(m.text())
        # The arm's own lines may not reach this side before its reboot; the serial log decides.
        a = root(base, 'pax-upgrade arm --reboot')
        armed = a.stdout.decode(errors='replace') + a.stderr.decode(errors='replace')
        # The kernel's line shows the model cut short; the serial names the disk.
        steps = [r'staged: attempt 1 of 2', r'staged: / is the staged archive',
                 r'upgrade: /pax/install-targets names .*serial "' + re.escape(SERIAL) + '"',
                 r'upgrade: PARTUUID=\S+ \(\w+\) on /mnt/target: ext2, read-write', r'pax-upgrade apply: upgraded to ' + commit,
                 r'pax-upgrade: the upgrade is done; removed']
        for s in steps:
            if not m.wait(s, 1800, after=mark):
                return row(name, False, f'no {s!r} on the serial log (the arm said {armed[-300:]!r}); its last lines: ' +
                           ' | '.join(m.text().strip().split('\n')[-8:]))
        if not answers(600):
            return row(name, False, 'burrowd never answered after the upgrade')
        time.sleep(3)
        st = ssh(base, 'pax-upgrade status; cat /etc/px115-marker; cat /home/wolf/px115-notes.txt').stdout.decode(errors='replace')
        ls = root(base, '/bin/pelt -c "ls /var/lib/pax-upgrade /var/lib/pax-upgrade/staged"').stdout.decode(errors='replace')
        ok = (' upgraded to ' + commit in st and ' cleaned after the upgrade' in st and MARKER in st and
              f"wolf's own file s1-{FW}" in st and 'archive' not in ls)
        row(name, ok, f'{archive.stat().st_size} bytes received in {secs:.0f} s, armed, the staged boot upgraded the root '
                      f'and rebooted into it, burrowd answered; status: {st.strip().splitlines()[-4:]}; stage: {ls.split()}')
    finally:
        finish(m, base)
        img.unlink()


def s2(base, pub, archive, digest, commit):
    img = prepare(f's2-{FW}', pub)
    m = boot(img, f's2-{FW}')
    try:
        r = send(base, archive, digest)
        a = root(base, 'pax-upgrade arm')
        if r.returncode != 0 or 'pax-upgrade: armed' not in a.stdout.decode(errors='replace'):
            return row('S2', False, f'receive {r.returncode} / arm: {a.stdout.decode(errors="replace")}{a.stderr.decode(errors="replace")}')
    finally:
        finish(m, base)
    # The staged archive changed while the machine was off: one byte of its first file's name, in place.
    staged = WORK / 'staged-copy'
    debugfs(img, [f'dump /var/lib/pax-upgrade/staged/archive {staged}'], write=False)
    b = bytearray(staged.read_bytes())
    b[200] ^= 1
    staged.write_bytes(bytes(b))
    debugfs(img, ['cd /var/lib/pax-upgrade/staged', 'rm archive', f'write {staged} archive',
                  'sif /var/lib/pax-upgrade/staged/archive mode 0100600'])
    staged.unlink()
    m = Machine(img, f's2b-{FW}')
    try:
        # The fallback boot starts burrowd before its hook reboots: the second boot's burrowd is the one asked.
        m.wait(r"pax-upgrade: rebooting into the installed system's own kernel", 900)
        mark = len(m.text())
        m.wait(r'burrowd: started', 900, after=mark)
        if not answers(300):
            raise RuntimeError('burrowd never answered after the fallback')
        text = m.text()
        st = ssh(base, 'pax-upgrade status; ls /etc/px115-marker').stdout.decode(errors='replace')
        ok = ("staged: the archive's sha256 is not pax.staged='s" in text and
              "pax-upgrade: rebooting into the installed system's own kernel" in text and
              " not-applied the staged archive's sha256 was not the armed one; disarmed" in st and
              '/etc/px115-marker' not in st)
        row('S2', ok, f'the staged kernel refused the changed archive, the installed system disarmed and rebooted; status: '
                      f'{st.strip().splitlines()[:2]}')
    finally:
        finish(m, base)
    conf = esp_text(img, '/boot/limine/limine.conf') or ''
    if 'pax.staged=' in conf or exists(img, '/etc/px115-marker'):
        row('S2', False, 'after it: the ESP still armed, or the marker on the root')
    img.unlink()


def s3(base, pub, archive, digest, commit):
    img = prepare(f's3-{FW}', pub)
    m = boot(img, f's3-{FW}')
    with open(archive, 'rb') as f:
        p = subprocess.Popen([str(x) for x in base + [f'pax-upgrade receive --sha256 {digest}']], stdin=f,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env())
        time.sleep(20)
        m.kill()
        p.kill()
        p.wait()
    m = boot(img, f's3b-{FW}')
    try:
        st = ssh(base, 'pax-upgrade status').stdout.decode(errors='replace')
        before = 'received: nothing' in st
        r = send(base, archive, digest)
        st2 = ssh(base, 'pax-upgrade status').stdout.decode(errors='replace')
        row('S3', before and r.returncode == 0 and f'sha256 {digest}' in st2,
            f'the power cut 20 s into the send left nothing received ({st.strip().splitlines()[:1]}); sent again: '
            f'{st2.strip().splitlines()[:1]}')
    finally:
        finish(m, base)
        img.unlink()


def s4(base, pub, archive, digest, commit):
    img = prepare(f's4-{FW}', pub)
    m = boot(img, f's4-{FW}')
    r = send(base, archive, digest)
    mark = len(m.text())
    root(base, 'pax-upgrade arm --reboot')
    if r.returncode != 0:
        m.kill()
        return row('S4', False, 'the receive failed')
    cut = m.wait(r'phase record: durable', 1800, after=mark)
    time.sleep(3)
    m.kill()
    if not cut:
        return row('S4', False, 'the staged upgrade never began writing')
    m = Machine(img, f's4b-{FW}')
    try:
        steps = [r'staged: attempt 2 of 2', r'pax-upgrade apply: upgraded to ' + commit,
                 r'pax-upgrade: the upgrade is done; removed']
        for s in steps:
            if not m.wait(s, 1800):
                return row('S4', False, f'no {s!r} after the cut; its last lines: ' + ' | '.join(m.text().strip().split('\n')[-8:]))
        if not answers(600):
            return row('S4', False, 'burrowd never answered after the second attempt')
        time.sleep(5)
        st = ssh(base, 'pax-upgrade status; cat /etc/px115-marker').stdout.decode(errors='replace')
        row('S4', ' upgraded to ' + commit in st and MARKER in st,
            f'cut once the upgrade had written its record; the second staged boot finished it; {st.strip().splitlines()[-3:]}')
    finally:
        finish(m, base)
        img.unlink()


if __name__ == '__main__':
    sys.exit(main())
