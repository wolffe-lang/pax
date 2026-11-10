"""px115 probe P1: what Limine 12.9.1 does with a second, default entry on an installed PAX disk.

Run inside the rig container (QEMU, OVMF, mtools) on a COPY of an installed 860-shaped disk:
    python3 -I p1-limine.py DISK OUTDIR [CASE...]
Each case rewrites the ESP's /boot/limine/limine.conf (mtools, a black box), boots the disk alone under KVM on
BIOS and on UEFI, and records Limine's serial lines, PAX's serial lines and QEMU screendumps at fixed times.
Nothing here reads Limine's source: its CONFIG.md (v12.9.1) and its behaviour as a binary only."""
import os
import re
import shutil
import socket
import json
import subprocess
import sys
import time
import zlib
import struct
from pathlib import Path

DISK, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ESP = 2097152
OVMF_CODE = '/usr/share/OVMF/OVMF_CODE_4M.fd'
OVMF_VARS = '/usr/share/OVMF/OVMF_VARS_4M.fd'


def esp_read(path):
    return subprocess.run(['mtype', '-i', f'{DISK}@@{ESP}', '::' + path], capture_output=True, check=True).stdout


def esp_write(path, data):
    f = OUT/'tmp-esp-file'
    f.write_bytes(data)
    subprocess.run(['mcopy', '-o', '-i', f'{DISK}@@{ESP}', str(f), '::' + path], check=True)
    f.unlink()
    back = esp_read(path)
    assert back == data, f'{path} read back differs'


def esp_del(path):
    subprocess.run(['mdel', '-i', f'{DISK}@@{ESP}', '::' + path], capture_output=True)


def esp_ls():
    return subprocess.run(['mdir', '-/', '-i', f'{DISK}@@{ESP}', '::/'], capture_output=True).stdout.decode(errors='replace')


ORIG = esp_read('/boot/limine/limine.conf').decode()
m = re.search(r'^    cmdline: (.*)$', ORIG, re.M)
CMDLINE = m.group(1)
ENTRY1 = ORIG[ORIG.index('/PAX'):]


def armed(second, globals_='timeout: 3\nserial: yes\n', default='default_entry: 2\n'):
    """The installed text with a second entry, as `pax-upgrade arm` would write it."""
    return default + globals_ + '\n' + ENTRY1.rstrip('\n') + '\n' + second


def entry2(path='boot():/boot/pax', extra='init=/bin/true', modules=()):
    t = '/PAX probe entry 2\n    protocol: limine\n    path: %s\n    cmdline: %s %s\n' % (path, CMDLINE, extra)
    for p in modules:
        t += '    module_path: %s\n' % p
    return t


CASES = {
    # The installed config untouched: the baseline every other case is held to.
    'baseline': lambda: ORIG,
    # default_entry 2 with a visible menu (timeout 3, serial mirrored): entry 2 boots unattended?
    'default2': lambda: armed(entry2()),
    # The installed globals (timeout 0, quiet) with default_entry 2: unattended, nothing drawn.
    'default2-quiet': lambda: 'default_entry: 2\ntimeout: 0\nquiet: yes\nserial: yes\n\n' + ENTRY1.rstrip('\n') + '\n' + entry2(),
    # The default entry's executable missing: what Limine does unattended (waits? menu? reboots?).
    'missing-kernel': lambda: armed(entry2(path='boot():/pax-upgrade/pax')),
    'missing-kernel-quiet': lambda: 'default_entry: 2\ntimeout: 0\nquiet: yes\nserial: yes\n\n' + ENTRY1.rstrip('\n') + '\n' + entry2(path='boot():/pax-upgrade/pax'),
    # A module path missing (the targets file or the archive's stand-in).
    'missing-module': lambda: armed(entry2(modules=('boot():/pax/install-targets',))),
    # The executable's path with a wrong blake2b hash (CONFIG.md: a mismatch panics unless hash_mismatch_panic: no).
    'bad-hash': lambda: armed(entry2(path='boot():/boot/pax#' + '0' * 128)),
    # The second entry's kernel from another file on the ESP (a copy of /boot/pax at /pax-upgrade/pax).
    'copy-kernel': lambda: armed(entry2(path='boot():/pax-upgrade/pax')),
    # default_entry naming an entry by title (CONFIG.md: an entry path).
    'default-title': lambda: armed(entry2(), default='default_entry: PAX probe entry 2\n'),
    # The missing kernel's panic answered with a key: what the menu does next (autoboot again or wait).
    'missing-kernel-key': lambda: armed(entry2(path='boot():/pax-upgrade/pax')),
    # The way back at the console: a key, then the installed entry chosen with the arrows and Enter.
    'missing-kernel-recover': lambda: armed(entry2(path='boot():/pax-upgrade/pax')),
}
KEYS = {'missing-kernel-key': [(10, 'spc')], 'missing-kernel-recover': [(10, 'spc'), (14, 'up'), (15, 'ret')]}


def png(ppm, out):
    data = ppm.read_bytes()
    mm = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
    w, h = map(int, mm.groups())
    px = data[mm.end():]
    raw = b''.join(b'\x00' + px[y * w * 3:(y + 1) * w * 3] for y in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    out.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                    chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


class QMP:
    def __init__(self, path):
        for _ in range(100):
            try:
                self.s = socket.socket(socket.AF_UNIX)
                self.s.connect(str(path))
                break
            except OSError:
                time.sleep(.1)
        self.f = self.s.makefile('rw')
        self.f.readline()
        self.call('qmp_capabilities')

    def call(self, cmd, args=None):
        self.f.write(json.dumps({'execute': cmd, **({'arguments': args} if args else {})}) + '\n')
        self.f.flush()
        while True:
            r = json.loads(self.f.readline())
            if 'return' in r or 'error' in r:
                return r


def boot(case, fw, secs=60):
    d = OUT/case/fw
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    a = ['qemu-system-x86_64', '-enable-kvm', '-machine', 'q35', '-cpu', 'host', '-smp', '2', '-m', '2048',
         '-drive', f'file={DISK},if=none,id=d0,format=raw',
         '-device', 'ahci,id=ahci0', '-device', 'ide-hd,drive=d0,bus=ahci0.0,model=PX115 PROBE DISK,serial=PX115P1',
         '-nic', 'none', '-display', 'none', '-vga', 'std',
         '-serial', f'file:{d}/serial.log', '-qmp', f'unix:{d}/qmp.sock,server,nowait',
         '-device', 'isa-debug-exit,iobase=0xf4,iosize=0x04']
    if fw == 'uefi':
        shutil.copy(OVMF_VARS, d/'vars.fd')
        a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
              '-drive', f'if=pflash,format=raw,unit=1,file={d}/vars.fd']
    p = subprocess.Popen(a, stdin=subprocess.DEVNULL, stdout=open(d/'qemu.out', 'wb'), stderr=subprocess.STDOUT)
    q = QMP(d/'qmp.sock')
    t0 = time.monotonic()
    shots = [3, 8, 12, 18, 30, secs - 2] if case in KEYS else [3, 8, 15, 30, secs - 2]
    keys = list(KEYS.get(case, []))
    while time.monotonic() - t0 < secs and p.poll() is None:
        el = time.monotonic() - t0
        if keys and el >= keys[0][0]:
            k = keys.pop(0)[1]
            for down in (True, False):
                q.call('input-send-event', {'events': [{'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': k}}}]})
                time.sleep(.08)
        if shots and el >= shots[0]:
            ppm = d/f'screen-{shots[0]:02d}s.ppm'
            q.call('screendump', {'filename': str(ppm)})
            time.sleep(.2)
            if ppm.exists():
                png(ppm, d/f'screen-{shots[0]:02d}s.png')
                ppm.unlink()
            shots.pop(0)
        time.sleep(.25)
    alive = p.poll() is None
    if alive:
        p.kill()
    p.wait()
    ser = (d/'serial.log').read_bytes().decode('latin-1')
    flat = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', ser).replace('\r', '')
    (d/'serial.txt').write_text(flat)
    return dict(alive_at_end=alive, qemu_exit=p.returncode, pax_console='PAX: the console' in flat,
                entry2=bool(re.search(r'PAX: init /bin/true', flat)), kernel=re.findall(r'kernel: ([0-9a-f]{8,40})', flat)[:1],
                login=bool(re.search(r'login:', flat)), boots=flat.count('PAX: the console'),
                limine_lines=[l for l in flat.split('\n') if re.search(r'(?i)limine|panic|error|fail|entry|press|boot', l)
                              and 'PAX' not in l][:12])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'orig-limine.conf').write_text(ORIG)
    (OUT/'esp-ls.txt').write_text(esp_ls())
    kern = esp_read('/boot/pax')
    cases = sys.argv[3:] or list(CASES)
    res = {}
    for c in cases:
        text = CASES[c]()
        (OUT/f'{c}.conf').write_text(text)
        esp_del('/pax-upgrade/pax')
        if c == 'copy-kernel':
            subprocess.run(['mmd', '-i', f'{DISK}@@{ESP}', '::/pax-upgrade'], capture_output=True)
            esp_write('/pax-upgrade/pax', kern)
        esp_write('/boot/limine/limine.conf', text.encode())
        for fw in ('bios', 'uefi'):
            t = time.monotonic()
            r = boot(c, fw)
            r['secs'] = round(time.monotonic() - t, 1)
            res[f'{c}/{fw}'] = r
            print(f'{time.strftime("%H:%M:%S")} {c}/{fw}: {json.dumps(r)}', flush=True)
    esp_write('/boot/limine/limine.conf', ORIG.encode())
    esp_del('/pax-upgrade/pax')
    (OUT/'results.json').write_text(json.dumps(res, indent=1))


main()
