"""px115 probe P2: how an upgrade image travels into PAX over burrowd today, and how sudo answers with no terminal.

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

DISK, OUT, IMAGE = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
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


def main():
    cdir = OUT/'client'
    if cdir.exists():
        shutil.rmtree(cdir)
    cdir.mkdir(mode=0o700)
    key, kh = cdir/'id_ed25519', cdir/'known_hosts'
    run([SSH/'ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'px115-p2', '-f', key])
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
             '-display', 'none', '-serial', f'file:{OUT}/serial.log', '-monitor', 'none']
        q = subprocess.Popen(a, stdin=subprocess.DEVNULL, stdout=open(OUT/'qemu.out', 'wb'), stderr=subprocess.STDOUT)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 180:
            if re.search(rf'DHCPACK\({TAP}\) {re.escape(GUEST)}', net.log.read_text(errors='replace')):
                break
            time.sleep(.5)
        log(f'lease after {time.monotonic() - t0:.1f} s')
        while time.monotonic() - t0 < 240:
            try:
                s = socket.create_connection((GUEST, 22), timeout=3)
                b = s.recv(64)
                s.close()
                break
            except OSError:
                time.sleep(1)
        log(f'port 22 after {time.monotonic() - t0:.1f} s: {b!r}')
        r = run(base + ['id; cat /proc/meminfo; nproc; cat /proc/cpuinfo | head -5'], env=env(), check=False)
        log('first command: ' + r.stdout.decode(errors='replace').replace('\n', ' | '))
        res['meminfo_idle'] = r.stdout.decode(errors='replace')

        # The sampler: sudo -S over ssh, its password the first line of its standard input.
        samp_out = open(OUT/'sampler.txt', 'wb')
        loop = ('i=0; while [ $i -lt 100000 ]; do echo "@@ $(date +%s.%N)"; cat /proc/meminfo; '
                'for f in /proc/[0-9]*/status; do echo "== $f"; cat $f 2>/dev/null; done; i=$((i+1)); sleep 2; done')
        sp = subprocess.Popen([str(x) for x in base + [f"sudo -S -p '' /bin/pelt -c '{loop}'"]], stdin=subprocess.PIPE,
                              stdout=samp_out, stderr=subprocess.STDOUT, env=env())
        sp.stdin.write((PW + '\n').encode())
        sp.stdin.flush()
        time.sleep(4)

        def send(path, name, extra=()):
            n = path.stat().st_size
            hh = hashlib.sha256()
            with open(path, 'rb') as f:
                for blk in iter(lambda: f.read(1 << 20), b''):
                    hh.update(blk)
            want = hh.hexdigest()
            t = time.monotonic()
            with open(path, 'rb') as f:
                r = subprocess.run([str(x) for x in ssh_argv(key, kh, extra) + [f'cat > /home/wolf/{name}']], stdin=f,
                                   capture_output=True, env=env(), timeout=3600)
            secs = time.monotonic() - t
            t = time.monotonic()
            h = run(base + [f'sha256sum /home/wolf/{name}; date +%s.%N'], env=env(), timeout=3600)
            hsecs = time.monotonic() - t
            got = h.stdout.decode(errors='replace').split()[0] if h.stdout else ''
            rate = n / secs / 1e6
            out = dict(bytes=n, secs=round(secs, 2), mb_s=round(rate, 2), exit=r.returncode,
                       stderr=r.stderr.decode(errors='replace')[-300:], sha_ok=got == want, sha256sum_secs=round(hsecs, 2),
                       sha256sum_mb_s=round(n / hsecs / 1e6, 2))
            log(f'send {name}: {json.dumps(out)}')
            run(base + [f'rm -f /home/wolf/{name}'], env=env())
            return out

        mode = sys.argv[4] if len(sys.argv) > 4 else 'all'
        if mode == 'all':
            small = OUT/'r16.bin'
            small.write_bytes(os.urandom(16 << 20))
            res['r16'] = send(small, 'r16')
            big = OUT/'r256.bin'
            with open(big, 'wb') as f:
                for _ in range(256):
                    f.write(os.urandom(1 << 20))
            res['r256'] = send(big, 'r256')
            res['image'] = send(IMAGE, 'image.img')
        mid = OUT/'r64.bin'
        mid.write_bytes(os.urandom(64 << 20))
        for ms in (2, 10, 30):
            net.netem(ms)
            rtts = []
            for _ in range(5):
                t = time.monotonic()
                c = socket.create_connection((GUEST, 22), timeout=10)
                rtts.append(round((time.monotonic() - t) * 1000, 2))
                c.close()
                time.sleep(.2)
            log(f'netem {ms} ms: TCP connect round trips {rtts} ms')
            res[f'r64_rtt{ms}'] = send(mid, f'r64-{ms}')
        net.netem(0)

        # sudo -S with no terminal: the password's line, then data the command reads.
        one = OUT/'r1.bin'
        one.write_bytes(os.urandom(1 << 20))
        want = hashlib.sha256(one.read_bytes()).hexdigest()
        cmd = "sudo -S -p '' /bin/pelt -c 'id -u; wc -c; echo st=$?'"
        r = run(base + [cmd], data=(PW + '\n').encode() + one.read_bytes(), env=env(), check=False)
        res['sudo_S_data'] = dict(exit=r.returncode, out=r.stdout.decode(errors='replace'), err=r.stderr.decode(errors='replace')[-300:])
        log(f'sudo -S then 1 MiB: {json.dumps(res["sudo_S_data"])}')
        cmd = "sudo -S -p '' /bin/pelt -c 'cat > /root/px115-r1; sha256sum /root/px115-r1; rm /root/px115-r1'"
        r = run(base + [cmd], data=(PW + '\n').encode() + one.read_bytes(), env=env(), check=False)
        ok = want in r.stdout.decode(errors='replace')
        res['sudo_S_sha'] = dict(exit=r.returncode, sha_ok=ok, err=r.stderr.decode(errors='replace')[-300:])
        log(f'sudo -S then 1 MiB into root\'s file: {json.dumps(res["sudo_S_sha"])}')
        t = time.monotonic()
        r = run(base + ["sudo -S -p '' /bin/id"], data=b'not-the-password\n' + one.read_bytes()[:4096], env=env(), check=False)
        res['sudo_S_wrong'] = dict(exit=r.returncode, secs=round(time.monotonic() - t, 1), out=r.stdout.decode(errors='replace'),
                                   err=r.stderr.decode(errors='replace')[-400:])
        log(f'sudo -S with a wrong password and data after it: {json.dumps(res["sudo_S_wrong"])}')
        r = run(base + ['sudo /bin/id'], env=env(), check=False)
        res['sudo_no_S'] = dict(exit=r.returncode, err=r.stderr.decode(errors='replace')[-400:])
        log(f'sudo with no -S and no terminal: {json.dumps(res["sudo_no_S"])}')
        r = run([SSH/'ssh', '-F', 'none', '-o', f'UserKnownHostsFile={kh}', '-o', 'BatchMode=yes', '-o', 'WarnWeakCrypto=no',
                 '-o', 'IdentitiesOnly=yes', '-i', key, f'root@{GUEST}', 'id'], env=env(), check=False)
        res['root_by_key'] = dict(exit=r.returncode, err=r.stderr.decode(errors='replace')[-200:])
        log(f'root by the same key: {json.dumps(res["root_by_key"])}')

        sp.terminate()
        sp.wait(timeout=20)
        samp_out.close()
        r = run(base + [f"sudo -S -p '' /bin/pelt -c 'tail -n 5 /var/log/burrowd.log; poweroff'"],
                data=(PW + '\n').encode(), env=env(), check=False, timeout=120)
        q.wait(timeout=120)
        log(f'powered off: qemu exit {q.returncode}')
    finally:
        if q and q.poll() is None:
            q.kill()
            q.wait()
        net.close()
        (OUT/'results.json').write_text(json.dumps(res, indent=1))
        (OUT/'record.txt').write_text('\n'.join(REC) + '\n')


main()
