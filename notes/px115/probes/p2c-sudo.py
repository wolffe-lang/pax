"""px115 probe P2c (P2's rig): sudo over ssh with no terminal: the session, the controlling terminal and the timestamp.

P2: how an upgrade image travels into PAX over burrowd today, and how sudo answers with no terminal.

Run inside the rig container (QEMU, the tap, dnsmasq, OpenSSH 10.2p1) on a COPY of an installed 860-shaped disk:
    python3 -I p2-transfer.py DISK OUTDIR IMAGE [MIB_256_FILE]
Offline first (debugfs, a black box): the user wolf (uid 1000, group sudo) gets a password made here at run time
(Python's secrets, hashed by the C library's crypt at the shipped $7$ cost; never written to a file, an argument
vector or a log) and the client's key in ~/.ssh/authorized_keys. Then the disk boots alone on igb on the rig's tap,
dnsmasq leases it 192.168.91.20, and stock OpenSSH sends files with `ssh wolf@HOST 'cat > FILE' < FILE`, timed on
the host, each read back by PAX's own sha256sum. A sampler (sudo -S over ssh) reads /proc/meminfo and every
process's /proc/PID/status each 2 s. Then the round trip is lengthened with netem on the tap, and sudo -S is held
to a password line followed by data."""
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
import threading
import time
from pathlib import Path

DISK, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ROOT_AT = 69206016
DEV = f'{DISK}?offset={ROOT_AT}'
TAP, HOST, GUEST, MAC = 'pxmf0', '192.168.91.1', '192.168.91.20', '52:54:00:12:91:20'
SSH = Path('/opt/openssh-10.2p1/bin')
PW = secrets.token_hex(8)
OUT.mkdir(parents=True, exist_ok=True)
REC = []


def log(msg):
    line = f'{time.strftime("%H:%M:%S")} {msg}'
    assert PW not in line
    print(line, flush=True)
    REC.append(line)


def run(argv, data=None, check=True, timeout=600, **kw):
    r = subprocess.run([str(x) for x in argv], input=data, capture_output=True, timeout=timeout, **kw)
    if check and r.returncode:
        raise RuntimeError(f'{argv[:3]}: exit {r.returncode}: {r.stderr.decode(errors="replace")[-400:]}')
    return r


def debugfs_w(cmds):
    f = OUT/'debugfs.cmds'
    f.write_text('\n'.join(cmds) + '\n')
    r = run(['debugfs', '-w', '-f', f, DEV])
    f.unlink()
    err = r.stderr.decode(errors='replace')
    if 'Could not' in err or 'not found' in err:
        raise RuntimeError('debugfs: ' + err[-600:])


def prepare(pub):
    shadow = run(['debugfs', '-R', 'cat /etc/shadow', DEV]).stdout.decode()
    salt = ''.join(secrets.choice('./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for _ in range(16))
    h = crypt.crypt(PW, '$7$F6..../....' + salt + '$')
    assert h and h.startswith('$7$F6..../....'), 'the C library made no $7$ hash'
    lines = []
    for l in shadow.splitlines():
        f = l.split(':')
        if f[0] == 'wolf':
            f[1] = h
        lines.append(':'.join(f))
    sf = OUT/'shadow.new'
    fd = os.open(sf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.write(fd, ('\n'.join(lines) + '\n').encode())
    os.close(fd)
    kf = OUT/'authorized_keys'
    kf.write_text(pub)
    debugfs_w(['rm /etc/shadow', 'cd /etc', f'write {sf} shadow', 'sif /etc/shadow mode 0100600', 'sif /etc/shadow uid 0',
               'sif /etc/shadow gid 0', 'mkdir /home/wolf/.ssh', 'sif /home/wolf/.ssh mode 040700',
               'sif /home/wolf/.ssh uid 1000', 'sif /home/wolf/.ssh gid 1000', 'cd /home/wolf/.ssh',
               f'write {kf} authorized_keys', 'sif /home/wolf/.ssh/authorized_keys mode 0100600',
               'sif /home/wolf/.ssh/authorized_keys uid 1000', 'sif /home/wolf/.ssh/authorized_keys gid 1000'])
    sf.unlink()
    log('offline: wolf\'s $7$ line replaced (a password made at run time), the client key in /home/wolf/.ssh/authorized_keys')


class Net:
    def __init__(self):
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)
        run(['ip', 'tuntap', 'add', 'dev', TAP, 'mode', 'tap'])
        run(['ip', 'addr', 'add', HOST + '/24', 'dev', TAP])
        run(['ip', 'link', 'set', TAP, 'up'])
        self.log = OUT/'dnsmasq.log'
        self.log.write_text('')
        self.p = subprocess.Popen(['dnsmasq', '--no-daemon', '--user=root', '--port=0', '--interface=' + TAP,
                                   '--bind-interfaces', '--dhcp-authoritative', '--leasefile-ro',
                                   f'--dhcp-range={GUEST},{GUEST},255.255.255.0,2m', f'--dhcp-host={MAC},{GUEST}',
                                   '--dhcp-option=3,' + HOST, '--log-dhcp', '--log-facility=' + str(self.log)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def netem(self, ms):
        subprocess.run(['tc', 'qdisc', 'del', 'dev', TAP, 'root'], capture_output=True)
        if ms:
            run(['tc', 'qdisc', 'add', 'dev', TAP, 'root', 'netem', 'delay', f'{ms}ms'])

    def close(self):
        self.p.terminate()
        self.p.wait(timeout=10)
        subprocess.run(['ip', 'link', 'del', TAP], capture_output=True)


def ssh_argv(key, kh, extra=()):
    return [SSH/'ssh', '-F', 'none', '-o', f'UserKnownHostsFile={kh}', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'PreferredAuthentications=publickey',
            '-o', 'ConnectTimeout=20', '-o', 'WarnWeakCrypto=no', '-i', key, *extra, f'wolf@{GUEST}']


def env():
    return dict(PATH='/usr/bin:/bin', HOME=str(OUT/'client'), LC_ALL='C')



def png(ppm, out):
    import struct, zlib
    data = ppm.read_bytes()
    mm = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
    w, h = map(int, mm.groups())
    px = data[mm.end():]
    raw = b''.join(b'\x00' + px[y * w * 3:(y + 1) * w * 3] for y in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    out.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                    chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def qmp(path):
    s = socket.socket(socket.AF_UNIX)
    for _ in range(100):
        try:
            s.connect(str(path))
            break
        except OSError:
            time.sleep(.1)
    f = s.makefile('rw')
    f.readline()
    def call(cmd, args=None):
        f.write(json.dumps({'execute': cmd, **({'arguments': args} if args else {})}) + '\n')
        f.flush()
        while True:
            r = json.loads(f.readline())
            if 'return' in r or 'error' in r:
                return r
    call('qmp_capabilities')
    return call


def main():
    cdir = OUT/'client'
    if cdir.exists():
        shutil.rmtree(cdir)
    cdir.mkdir(mode=0o700, parents=True)
    key, kh = cdir/'id_ed25519', cdir/'known_hosts'
    run([SSH/'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'px115-p2c', '-f', key])
    prepare(Path(str(key) + '.pub').read_text())
    base = ssh_argv(key, kh)
    net = Net()
    q = None
    res = {}
    try:
        a = ['qemu-system-x86_64', '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '2', '-m', '4096',
             '-drive', f'file={DISK},if=none,id=d0,format=raw,cache=unsafe',
             '-device', 'ahci,id=ahci0', '-device', 'ide-hd,drive=d0,bus=ahci0.0,model=PX115 PROBE DISK,serial=PX115P2',
             '-netdev', f'tap,id=n0,ifname={TAP},script=no,downscript=no', '-device', f'igb,netdev=n0,mac={MAC}',
             '-display', 'none', '-vga', 'std', '-serial', f'file:{OUT}/serial.log', '-qmp', f'unix:{OUT}/qmp.sock,server,nowait']
        q = subprocess.Popen(a, stdin=subprocess.DEVNULL, stdout=open(OUT/'qemu.out', 'wb'), stderr=subprocess.STDOUT)
        call = qmp(OUT/'qmp.sock')
        t0 = time.monotonic()
        while time.monotonic() - t0 < 240:
            try:
                s = socket.create_connection((GUEST, 22), timeout=3)
                s.recv(64)
                s.close()
                break
            except OSError:
                time.sleep(1)
        log(f'port 22 after {time.monotonic() - t0:.1f} s')

        def ssh(cmd, data=b'', what=''):
            r = run(base + [cmd], data=data, env=env(), check=False, timeout=120)
            out = dict(exit=r.returncode, out=r.stdout.decode(errors='replace')[-600:], err=r.stderr.decode(errors='replace')[-600:])
            log(f'{what or cmd}: {json.dumps(out)}')
            return out

        res['who'] = ssh('tty; echo; cat /proc/self/stat; echo; ls -l /proc/self/fd', what='the session: tty, /proc/self/stat (pid comm state ppid pgrp session tty_nr), fds')
        res['K'] = ssh('sudo -K; echo K=$?', what='sudo -K (no record)')
        res['n1'] = ssh('sudo -n /bin/id', what='sudo -n with no record')
        res['wrong'] = ssh("sudo -S -p '' /bin/id", data=b'not-the-password\n', what='sudo -S, a wrong password alone')
        res['right'] = ssh("sudo -S -p '' /bin/pelt -c 'id -u; cat /var/run/sudo/ts/1000 | sed s/time.*/time.../'", data=(PW + '\n').encode(), what='sudo -S, the password: then the timestamp file (times elided)')
        res['n2'] = ssh('sudo -n /bin/id', what='a NEW ssh session, sudo -n, no password')
        res['data'] = ssh("sudo -S -p '' /bin/pelt -c 'wc -c'", data=(PW + '\n').encode() + b'x' * 1000, what='a NEW session, sudo -S with the password line then 1000 bytes: wc -c')
        res['K2'] = ssh('sudo -K; echo K=$?', what='sudo -K again')
        # sudo with no -S and no record: where does it ask? Screens of the console at 3 s and 8 s.
        p = subprocess.Popen([str(x) for x in base + ['sudo /bin/id; echo st=$?']], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env())
        for t in (3, 8):
            time.sleep(t - (0 if t == 3 else 3))
            ppm = OUT/f'console-{t}s.ppm'
            call('screendump', {'filename': str(ppm)})
            time.sleep(.3)
            png(ppm, OUT/f'console-{t}s.png')
            ppm.unlink()
        try:
            so, se = p.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            p.kill()
            so, se = p.communicate()
        res['no_S'] = dict(exit=p.returncode, out=so.decode(errors='replace')[-400:], err=se.decode(errors='replace')[-400:])
        log(f'sudo with no -S, no record, no terminal of ssh\'s: {json.dumps(res["no_S"])}')
        ssh("sudo -S -p '' poweroff", data=(PW + '\n').encode(), what='poweroff')
        q.wait(timeout=120)
    finally:
        if q and q.poll() is None:
            q.kill()
            q.wait()
        net.close()
        (OUT/'results.json').write_text(json.dumps(res, indent=1))
        (OUT/'record.txt').write_text('\n'.join(REC) + '\n')


main()
