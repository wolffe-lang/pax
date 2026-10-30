#!/usr/bin/env python3
"""px78: the whole install path in QEMU shaped like kasumi (contract item 5).

    metal.py REPO INPUTS WORK [build | run]

INPUTS is a finished tests/mpx6-install run's inputs/ (its build/disktools,
build/full and build/install-gate). WORK is this leg's own directory.
`build` makes the stick alone (tools/mkdisk --usb runs tools/disktools in
a container engine); `run` takes WORK/stick.img as built and runs the rest,
for a host where the engine and QEMU live apart (a lane's container);
neither (CI) does both in one run.

The machine: q35, OVMF with a fresh variable store, -serial none (kasumi has
no COM port), one xHCI controller with the boot stick (usb-storage,
removable) and the keyboard (usb-kbd) on it, as kasumi's 00:14.0 carries
both; an NVMe disk standing in for the CachyOS root (a foreign GPT and
data); q35's AHCI controller with three SATA disks: the "870 EVO 4TB"
Steam library, the "SanDisk 512G", and the install target, a sparse
500 GB "870 EVO 500GB". The target and the Steam disk show the same model
to Linux and to PAX ("Samsung SSD 870": SCSI's 16 bytes), so only the
serial on the allow-list tells them apart: the right model with the wrong
serial is refused by name.

The leg: the live stick is built (tools/mkdisk --usb) from a live tree
whose /etc/pax-run is the live login; the allow-list line is appended to
the stick's /pax/install-targets from the host by paxfat (as the
maintainer would add it from CachyOS); boot the stick, log in as root
through the USB keyboard, write a witness file, `pax-install --check`,
then the guided install to the listed disk, the confirmation read off the
screen and typed back; power off (ACPI S5); remove the stick; boot the
disk, chosen as from the firmware boot menu, with no boot entry of its own; log in; read the witness file written
before the reboot; ask --check of the running root; power off. The screens
are read from PAX's own exported terminal cells (px77a's way: QMP memsave
at the kernel's symbols, the machine stopped), never from a UART.

Witnesses: the NVMe image and the two other SATA images are hashed over
their allocated extents (SEEK_DATA/SEEK_HOLE: each extent's offset,
length and bytes) before the first boot and after each boot: identical,
or FAIL. The stick's install log is read back from its ESP and held to
the inventory, the plan, every phase's verdict and the first MiB of each
written partition, hashed again here from the target image; the stick's
ESP is checked by fsck.fat -n, the target's root by e2fsck -fn, its
table by sgdisk -v and its ESP by fsck.fat -n.
Results: WORK/result.json (the wall times, the witnesses' sha256s).
Exit 0 with PASS lines, 1 with a FAIL line naming the row.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import time
import zlib

repo, inputs, work = map(Path, sys.argv[1:4])
mode = sys.argv[4] if len(sys.argv) > 4 else 'all'
assert mode in ('all', 'build', 'run'), mode
work.mkdir(parents=True, exist_ok=True)
D = repo/'tests/mpx6-install.d'
dt = inputs/'build/disktools'
full = inputs/'build/full'
cache = Path(os.environ.get('PAX_CACHE', repo/'.pax-cache'))
kernel = Path((dt/'native.elf.path').read_text().strip())
t_leg = time.monotonic()
result = {'leg': 'px78 metal install', 'kernel': str(kernel)}


def log(s):
    print(time.strftime('%H:%M:%S ') + s, flush=True)


def fail(row, why):
    print(f'FAIL {row}: {why}', flush=True)
    (work/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    sys.exit(1)


def run(args, ok=True, **kw):
    p = subprocess.run([str(a) for a in args], capture_output=True, **kw)
    if ok and p.returncode != 0:
        fail('M0-build', f'{args[0]} exited {p.returncode}: {p.stdout[-2000:]!r} {p.stderr[-2000:]!r}')
    return p


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def extents_sha(p):
    """sha256 over the image's size and each allocated extent (SEEK_DATA,
    SEEK_HOLE): its offset, its length and its bytes. A byte written into
    a hole, or a hole punched, changes it as a changed byte does."""
    h = hashlib.sha256()
    size = p.stat().st_size
    h.update(b'size %d\n' % size)
    n = 0
    with open(p, 'rb') as f:
        at = 0
        while at < size:
            try:
                data = os.lseek(f.fileno(), at, os.SEEK_DATA)
            except OSError:
                break
            hole = os.lseek(f.fileno(), data, os.SEEK_HOLE)
            h.update(b'extent %d %d\n' % (data, hole - data))
            f.seek(data)
            left = hole - data
            while left:
                b = f.read(min(left, 1 << 20))
                if not b:
                    break
                h.update(b)
                left -= len(b)
            n += 1
            at = hole
    return h.hexdigest(), n


# --- the live stick ---------------------------------------------------------

LIVE = work/'live'
LIMINE = cache/'limine-12.9.1'


def build_stick():
    if LIVE.exists():
        shutil.rmtree(LIVE)
    for d in ['bin', 'boot/EFI/BOOT', 'boot/limine', 'etc', 'root', 'home/pax', 'dev', 'proc', 'sys', 'tmp',
              'usr/share/pax-install/games']:
        (LIVE/d).mkdir(parents=True, exist_ok=True)
    progs = {n: dt/'bore'/n for n in ['cat', 'cp', 'env', 'ls']}
    progs.update(sh=full/'pelt/pelt', pelt=full/'pelt/pelt', lope=full/'lope/lope', reboot=full/'probe/reboot')
    progs.update({n: dt/'bin'/n for n in ['paxgpt', 'paxfat', 'paxext2']})
    progs.update(limine=dt/'limine/limine', **{'pax-install': inputs/'build/install-gate/bin/pax-install'})
    for n, p in progs.items():
        if p.read_bytes()[:4] == b'\x7fELF':
            run(['strip', '-o', LIVE/'bin'/n, p])
        else:
            shutil.copyfile(p, LIVE/'bin'/n)
        (LIVE/'bin'/n).chmod(0o755)
    shutil.copyfile(kernel, LIVE/'boot/pax')
    shutil.copyfile(LIMINE/'BOOTX64.EFI', LIVE/'boot/EFI/BOOT/BOOTX64.EFI')
    shutil.copyfile(LIMINE/'limine-bios.sys', LIVE/'boot/limine/limine-bios.sys')
    (LIVE/'boot/limine/limine.conf').write_text('the live medium configuration; pax-install writes its own\n')
    (LIVE/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\n')
    (LIVE/'etc/group').write_text('root:x:0:\npax:x:1000:\n')
    (LIVE/'etc/motd').write_text('PAX px78 metal leg live medium\n')
    (LIVE/'etc/pax-release').write_text('PAX px78 metal leg (tests/mpx6-install --only metal)\n')
    shutil.copyfile(repo/'user/shrc', LIVE/'etc/shrc')
    shutil.copyfile(repo/'user/usb-login.sh', LIVE/'etc/pax-live-login')
    (LIVE/'etc/pax-run').write_text('/bin/pelt /etc/pax-live-login\n')
    pay = LIVE/'usr/share/pax-install'
    shutil.copyfile(repo/'user/install/games.txt', pay/'games.txt')
    for row in (repo/'user/install/games.txt').read_text().splitlines():
        if row.strip() and not row.startswith('#'):
            g = row.split()[0]
            for f in [g, g + '.source.tar.gz', g + '.engine.source.tar.gz']:
                shutil.copyfile(full/'games'/f, pay/'games'/f)
    shutil.copyfile(full/'games/games.sha256', pay/'games.sha256')
    (pay/'boot.sha256').write_text(''.join(sha(LIVE/p) + '  /' + p + '\n'
                                           for p in ['boot/pax', 'boot/limine/limine-bios.sys', 'boot/EFI/BOOT/BOOTX64.EFI']))
    args = []
    for p in [LIVE, *sorted(LIVE.rglob('*'))]:
        rel = '/' + p.relative_to(LIVE).as_posix() if p != LIVE else '/'
        if rel == '/':
            continue
        mode = 0o755 if p.is_dir() or rel.startswith('/bin/') or '/games/' in rel and not rel.endswith('.tar.gz') else 0o644
        uid = gid = 1000 if rel == '/home/pax' else 0
        if rel == '/root':
            mode = 0o700
        if rel == '/tmp':
            mode = 0o1777
        if rel in ['/proc', '/sys']:
            mode = 0o555
        args.append(f'{rel}/:{mode:o}:{uid}:{gid}' if p.is_dir() else f'{rel}={p}:{mode:o}:{uid}:{gid}')
    run([repo/'tools/mkinitramfs', work/'live.cpio', *args])
    stick = work/'stick.img'
    out = run([repo/'tools/mkdisk', '--usb', '--kernel', kernel, '--initramfs', work/'live.cpio',
               '--conf', repo/'boot/limine-usb.conf', stick])
    (work/'stick.build.log').write_bytes(out.stdout + out.stderr)
    exp = ['--expect', f'/boot/pax={kernel}', '--expect', f'/boot/initramfs.cpio={work/"live.cpio"}',
           '--expect', f'/EFI/BOOT/BOOTX64.EFI={LIMINE/"BOOTX64.EFI"}',
           '--expect', f'/boot/limine/limine-bios.sys={LIMINE/"limine-bios.sys"}',
           '--expect', f'/boot/limine/limine.conf={repo/"boot/limine-usb.conf"}',
           '--expect', f'/pax/install-targets={repo/"boot/install-targets"}']
    out = run([repo/'tools/check-usb', stick, *exp])
    (work/'stick.check.log').write_bytes(out.stdout)
    print(f'PASS M0-stick: tools/mkdisk --usb, tools/check-usb (the allow-list naming no disk among its files); {stick.stat().st_size} bytes sha256 {sha(stick)}', flush=True)
    return stick


def esp_range(img):
    """Partition 1's first byte and length, from the primary GPT."""
    with open(img, 'rb') as f:
        f.seek(512)
        h = f.read(92)
        array = struct.unpack_from('<Q', h, 72)[0]
        f.seek(array * 512)
        e = f.read(128)
    first, last = struct.unpack_from('<QQ', e, 32)
    return first * 512, (last - first + 1) * 512


# --- the disks --------------------------------------------------------------

TARGET = {'model': 'Samsung SSD 870 EVO 500GB', 'serial': 'PX78-TARGET-0001', 'bytes': 500107862016}
STEAM = {'model': 'Samsung SSD 870 EVO 4TB', 'serial': 'S6PXNM0T700001', 'bytes': 4000787030016}
SANDISK = {'model': 'SanDisk SDSSDH3 512G', 'serial': '2104AB401234', 'bytes': 512110190592}
NVME = {'serial': 'S6Z1NJ0W000001', 'bytes': 1000204886016}
LINUX_MODEL = 'Samsung SSD 870'  # what CachyOS's /sys/block/sdX/device/model shows (16 bytes, trimmed)


def foreign_disk(path, spec, parts):
    """A sparse disk with a GPT of `parts` (tools/mkgpt) and known data at
    a few places in each partition: a disk PAX did not write."""
    with open(path, 'wb') as f:
        f.truncate(spec['bytes'])
    sectors = spec['bytes'] // 512
    table = []
    for k, (kind, first, last) in enumerate(parts, 1):
        last = sectors - 34 if last is None else last
        table.append(f'{k}:{kind}:{first}:{last}')
    run([repo/'tools/mkgpt', '--label', path.stem, path, *table])
    with open(path, 'r+b') as f:
        for k, (kind, first, last) in enumerate(parts, 1):
            last = sectors - 34 if last is None else last
            for at in (first, (first + last) // 2, last - 2047):
                f.seek(at * 512)
                f.write(hashlib.shake_256(f'px78 {path.stem} {k} {at}'.encode()).digest(1 << 20))


def make_disks():
    d = work/'disks'
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    gib = 2097152  # sectors
    foreign_disk(d/'nvme.img', NVME, [('esp', 2048, 2048 + gib - 1), ('linux', 2048 + gib, None)])
    foreign_disk(d/'steam.img', STEAM, [('linux', 2048, None)])
    q = SANDISK['bytes'] // 512 // 4
    foreign_disk(d/'sandisk.img', SANDISK, [('linux', 2048, q - 1), ('linux', q, 2 * q - 1), ('linux', 2 * q, 3 * q - 1), ('linux', 3 * q, None)])
    with open(d/'target.img', 'wb') as f:
        f.truncate(TARGET['bytes'])
    return d


def witnesses(d):
    return {n: extents_sha(d/(n + '.img')) for n in ('nvme', 'steam', 'sandisk')}


# --- QEMU, QMP, the screen and the keyboard ----------------------------------

def symbols():
    out = run(['nm', kernel]).stdout.decode()
    return {p[2]: int(p[0], 16) for p in (l.split() for l in out.splitlines()) if len(p) == 3}


SYM = symbols()
for s in ('pax_screen_state', 'pax_screen_cells'):
    if s not in SYM:
        fail('M0-build', f'{kernel} has no {s}')


class QMP:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        self.s.connect(str(path))
        self.f = self.s.makefile('rb')
        self.f.readline()
        self.i = 0
        self.call('qmp_capabilities')

    def call(self, name, args=None):
        self.i += 1
        self.s.sendall((json.dumps({'execute': name, 'arguments': args or {}, 'id': self.i}) + '\n').encode())
        while True:
            line = self.f.readline()
            if not line:
                raise RuntimeError('QMP closed')
            r = json.loads(line)
            if r.get('id') == self.i:
                if 'error' in r:
                    raise RuntimeError(r)
                return r.get('return')

    def hmp(self, s):
        return self.call('human-monitor-command', {'command-line': s})


SHIFTED = {':': 'semicolon', '>': 'dot', '<': 'comma', '_': 'minus', '+': 'equal', '"': 'apostrophe', '!': '1',
           '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0', '?': 'slash',
           '|': 'backslash', '~': 'grave_accent', '{': 'bracket_left', '}': 'bracket_right'}
PLAIN = {' ': 'spc', '-': 'minus', '=': 'equal', '/': 'slash', '.': 'dot', ',': 'comma', ';': 'semicolon',
         "'": 'apostrophe', '\n': 'ret', '[': 'bracket_left', ']': 'bracket_right', '\\': 'backslash',
         '`': 'grave_accent'}


class Machine:
    def __init__(self, name, args):
        self.name = name
        self.dir = work/name
        self.dir.mkdir(exist_ok=True)
        self.sock = self.dir/'qmp.sock'
        if self.sock.exists():
            self.sock.unlink()
        self.cmd = args + ['-qmp', f'unix:{self.sock},server=on,wait=off']
        (self.dir/'command.json').write_text(json.dumps([str(a) for a in self.cmd], indent=2) + '\n')
        self.qlog = (self.dir/'qemu.log').open('wb')
        self.t0 = time.monotonic()
        self.p = subprocess.Popen([str(a) for a in self.cmd], stdin=subprocess.DEVNULL, stdout=self.qlog, stderr=subprocess.STDOUT)
        for _ in range(200):
            if self.sock.exists():
                break
            if self.p.poll() is not None:
                fail(name, 'QEMU did not start: ' + (self.dir/'qemu.log').read_text(errors='replace')[-2000:])
            time.sleep(.05)
        self.q = QMP(self.sock)
        self.shots = 0

    def screen(self):
        self.q.call('stop')
        try:
            st = self.dir/'state.bin'
            r = self.q.hmp(f'memsave 0x{SYM["pax_screen_state"]:x} 552 "{st}"')
            if r:
                return ''
            state = struct.unpack('<69Q', st.read_bytes())
            cols, rows = state[5], state[6]
            if not (state[0] and 1 <= cols <= 256 and 1 <= rows <= 128):
                return ''
            at = SYM['pax_screen_cells'] + (256 * 128 * 4 if state[60] else 0)
            cf = self.dir/'cells.bin'
            r = self.q.hmp(f'memsave 0x{at:x} {cols * rows * 4} "{cf}"')
            if r:
                return ''
            cells = struct.unpack('<' + str(cols * rows) + 'I', cf.read_bytes())
            lines = []
            for y in range(rows):
                row = ''.join(chr(v & 255) if 32 <= v & 255 < 127 else ' ' for v in cells[y * cols:(y + 1) * cols])
                lines.append(row)
            self.cols = cols
            return '\n'.join(l.rstrip() for l in lines).rstrip() + '\n'
        finally:
            self.q.call('cont')

    def unwrapped(self, text):
        """Rows the terminal wrapped (a row filled to the last column) joined
        to the row after them, so a long line reads as one."""
        out = []
        full = False
        cols = getattr(self, 'cols', 0)
        for line in text.split('\n'):
            if out and full:
                out[-1] += line
            else:
                out.append(line)
            full = cols > 0 and len(line) == cols
        return '\n'.join(out)

    def wait(self, pattern, row, timeout=300, last=False, bad=None):
        """The screen once /pattern/ is on it; FAIL at the timeout, when
        QEMU ends first, or at once when /bad/ shows (a refusal or a stop
        the row does not expect)."""
        end = time.monotonic() + timeout
        text = ''
        while time.monotonic() < end:
            if self.p.poll() is not None:
                fail(row, f'QEMU ended (exit {self.p.returncode}) before /{pattern}/; screen:\n{text}')
            text = self.screen()
            look = text.rstrip('\n').split('\n')[-1] if last else self.unwrapped(text)
            if re.search(pattern, look, re.M):
                return text
            if bad and re.search(bad, self.unwrapped(text), re.M):
                self.shot('bad')
                fail(row, f'/{bad}/ on the screen before /{pattern}/; screen:\n{text}')
            time.sleep(.3)
        self.shot('timeout')
        fail(row, f'no /{pattern}/ on the screen in {timeout} s; screen:\n{text}')

    def shot(self, name):
        self.shots += 1
        ppm = self.dir/'screen.ppm'
        self.q.call('screendump', {'filename': str(ppm)})
        data = ppm.read_bytes()
        m = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
        w, h = map(int, m.groups())
        raw = data[m.end():]

        def chunk(k, b):
            return struct.pack('>I', len(b)) + k + b + struct.pack('>I', zlib.crc32(k + b))
        rows = b''.join(b'\0' + raw[y * w * 3:(y + 1) * w * 3] for y in range(h))
        png = self.dir/f'{self.shots:02d}-{name}.png'
        png.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                        chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))
        (self.dir/f'{self.shots:02d}-{name}.txt').write_text(self.screen())

    def key(self, k, down):
        self.q.call('input-send-event', {'events': [{'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': k}}}]})

    def type(self, s):
        for c in s:
            shift = c in SHIFTED or c.isupper()
            k = SHIFTED.get(c) or PLAIN.get(c) or c.lower()
            if shift:
                self.key('shift', True)
            self.key(k, True)
            time.sleep(.03)
            self.key(k, False)
            if shift:
                self.key('shift', False)
            time.sleep(.03)

    def command(self, line, row, timeout=300):
        self.type(line + '\n')
        time.sleep(.5)
        return self.wait(r'^.*[$#] *$', row, timeout, last=True)

    def ended(self, row, timeout=300):
        try:
            self.p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.shot('no-poweroff')
            fail(row, 'QEMU did not end (no ACPI power-off)')
        self.qlog.close()
        return self.p.returncode, time.monotonic() - self.t0

    def kill(self):
        if self.p.poll() is None:
            try:
                self.q.call('quit')
            except Exception:
                pass
            try:
                self.p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()


def accel():
    want = os.environ.get('PAX_METAL_ACCEL', 'auto')
    if want == 'auto':
        want = 'kvm' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg'
    return want


def qemu_args(d, vars_fd, stick):
    code = os.environ.get('PAX_OVMF_CODE', '/usr/share/OVMF/OVMF_CODE_4M.fd')
    # PAX_METAL_SERIAL=DIR gives the machine a COM1 logging to DIR/com1-
    # stick.log or com1-disk.log: a debugging aid that changes kasumi's
    # shape (it has no COM port), so the leg says so; CI never sets it.
    serial = os.environ.get('PAX_METAL_SERIAL')
    com1 = f'file:{serial}/com1-{"stick" if stick else "disk"}.log' if serial else 'none'
    if serial:
        log(f'PAX_METAL_SERIAL: COM1 to {com1[5:]} (not kasumi\'s shape: debugging only)')
    a = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', '2048M', '-accel', accel(),
         '-display', 'none', '-serial', com1,
         '-parallel', 'none', '-nic', 'none', '-no-reboot',
         '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
         '-drive', f'if=pflash,format=raw,unit=1,file={vars_fd}',
         '-device', 'qemu-xhci,id=xhci']
    if stick:
        a += ['-drive', f'file={stick},if=none,id=stick,format=raw',
              '-device', 'usb-storage,bus=xhci.0,drive=stick,removable=on,bootindex=0']
    a += ['-device', 'usb-kbd,bus=xhci.0',
          '-drive', f'file={d/"nvme.img"},if=none,id=nv,format=raw', '-device', f'nvme,serial={NVME["serial"]},drive=nv',
          '-drive', f'file={d/"steam.img"},if=none,id=sa,format=raw',
          '-device', f'ide-hd,bus=ide.0,drive=sa,model={STEAM["model"]},serial={STEAM["serial"]}',
          '-drive', f'file={d/"sandisk.img"},if=none,id=sb,format=raw',
          '-device', f'ide-hd,bus=ide.1,drive=sb,model={SANDISK["model"]},serial={SANDISK["serial"]}',
          '-drive', f'file={d/"target.img"},if=none,id=sc,format=raw,discard=unmap,detect-zeroes=unmap',
          '-device', f'ide-hd,bus=ide.2,drive=sc,model={TARGET["model"]},serial={TARGET["serial"]}'
          # With the stick gone, the target is the firmware boot menu's
          # choice (F8 on kasumi; QEMU's boot order here, bootindex 0): the
          # firmware makes the option for the device and boots its
          # removable-media path; PAX writes no boot entry. Left to itself
          # with boot 1's variable store, OVMF went to its UEFI shell
          # (notes/px78/seen-red/boot2-no-bootorder-uefi-shell.png).
          + ('' if stick else ',bootindex=0')]
    return a


# A stop on the screen ends the guided rows at once, not at their timeout.
STOPPED = r'^(pax-install: (stopped|refused|cancelled)|install log: stopped)'


def need(text, needle, row):
    if needle not in text:
        fail(row, f'missing {needle!r}')


# --- the leg ------------------------------------------------------------------

def main():
    if mode == 'build':
        build_stick()
        return
    stick = work/'stick.img' if mode == 'run' else build_stick()
    esp, esp_bytes = esp_range(stick)
    paxfat = dt/'bin/paxfat'
    # The maintainer's step, from CachyOS: the target's line on the stick.
    line = work/'allow-line'
    line.write_text(f'model={LINUX_MODEL} serial={TARGET["serial"]}\n')
    # px77c: the copy already carries the line (macOS or Linux wrote it); no append here.
    listed = run([paxfat, '--offset', esp, 'cat', stick, '/pax/install-targets']).stdout.decode()
    need(listed, f'model={LINUX_MODEL} serial={TARGET["serial"]}', 'M0-stick')
    d = make_disks()
    before = witnesses(d)
    result['witness_before'] = {k: v[0] for k, v in before.items()}
    log('witnesses before: ' + json.dumps(result['witness_before']))
    vars_fd = work/'vars.fd'
    shutil.copyfile(os.environ.get('PAX_OVMF_VARS', '/usr/share/OVMF/OVMF_VARS_4M.fd'), vars_fd)
    result['accel'] = accel()
    result['qemu'] = run(['qemu-system-x86_64', '--version']).stdout.decode().splitlines()[0]
    nonce = 'px78-witness-' + secrets.token_hex(6)

    # Boot 1: the stick.
    m = Machine('boot1', qemu_args(d, vars_fd, stick))
    try:
        m.wait(r'^login: *$', 'M1-live-login', 600)
        m.shot('live-login')
        m.type('root\n')
        m.wait(r'^.*[$#] *$', 'M1-live-login', 120, last=True)
        m.command(f'echo {nonce} > /root/px78-witness', 'M1-witness-file')
        s = m.command('cat /root/px78-witness', 'M1-witness-file')
        need(s, nonce, 'M1-witness-file')
        # The live root carries its own /dev directory: listed once (the
        # first run listed `dev` twice and the install's staging stopped).
        s = m.command('ls -1 /', 'M1-root-listing')
        listing = s.split('ls -1 /\n')[-1].split('\n')
        if listing.count('dev') != 1:
            fail('M1-root-listing', f'/ lists dev {listing.count("dev")} times:\n{s}')
        print('PASS M1-live-login: the live login through the USB keyboard; the witness file written; / lists dev once', flush=True)
        check = m.command('pax-install --check', 'M2-check', 600)
        m.shot('check')
        flat = m.unwrapped(check)
        need(flat, f'refused: not on the install allow-list: /dev/sda model={LINUX_MODEL} serial={STEAM["serial"]}', 'M2-right-model-wrong-serial')
        need(flat, f'refused: not on the install allow-list: /dev/nvme0n1 model=QEMU NVMe Ctrl serial={NVME["serial"]}', 'M2-nvme-refused')
        need(flat, f'refused: not on the install allow-list: /dev/sdb model={SANDISK["model"][:16].rstrip()} serial={SANDISK["serial"]}', 'M2-sdb-refused')
        need(flat, 'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdd', 'M2-stick-refused')
        need(flat, f'/dev/sdc bytes={TARGET["bytes"]} sector=512 model={LINUX_MODEL} serial={TARGET["serial"]}', 'M2-target-listed')
        print('PASS M2-check: the target alone on the list; sda (the right model, the wrong serial), sdb and the NVMe refused by name; the stick refused before the list', flush=True)
        t_guided = time.monotonic()
        m.type('pax-install\n')
        page = m.wait(r'pax-install> *$', 'M3-guided', 600, bad=STOPPED)
        m.shot('target-page')
        num = re.search(r'^[> ] (\d+)\. /dev/sdc ', m.unwrapped(page), re.M)
        if not num:
            fail('M3-guided', 'the target is not on the page:\n' + page)
        m.type(num.group(1) + '\n')
        m.wait(r'New user name', 'M3-guided', 120, bad=STOPPED)
        m.type('wolf\n')
        m.wait(r'Install the lair', 'M3-guided', 120, bad=STOPPED)
        m.type('n\n')
        plan = m.wait(r'Type ext2-preview to continue', 'M3-guided', 300, bad=STOPPED)
        m.shot('plan')
        tok = re.search(r'^confirmation (ERASE /dev/sdc \S+ \d+ [0-9a-f]{64})$', m.unwrapped(plan), re.M)
        if not tok:
            fail('M3-guided', 'no confirmation line on the screen:\n' + plan)
        m.type('ext2-preview\n')
        m.wait(r'Type the complete confirmation line', 'M3-guided', 120, bad=STOPPED)
        m.type(tok.group(1) + '\n')
        t_confirm = time.monotonic()
        m.wait(r'^Installation complete', 'M4-install', 3600, bad=STOPPED)
        t_done = time.monotonic()
        m.wait(r'poweroff to power off', 'M4-install', 120)
        m.shot('complete')
        result['install_seconds'] = round(t_done - t_confirm, 2)
        result['guided_seconds'] = round(t_done - t_guided, 2)
        log(f'install {result["install_seconds"]} s from the confirmation; guided {result["guided_seconds"]} s')
        m.type('poweroff\n')
        rc, secs = m.ended('M4-poweroff', 300)
        result['boot1_seconds'] = round(secs, 2)
        if rc != 0:
            fail('M4-poweroff', f'QEMU exit {rc}')
    finally:
        m.kill()
    print(f'PASS M4-install: guided, to the listed /dev/sdc; installed in {result["install_seconds"]} s; ACPI power-off', flush=True)
    after1 = witnesses(d)
    if after1 != before:
        fail('M5-witness', f'a disk not the target changed in boot 1: {after1} vs {before}')

    # The stick's install log, held to the run.
    logtext = run([paxfat, '--offset', esp, 'cat', stick, '/pax/logs/install-1.txt']).stdout.decode(errors='replace')
    (work/'install-1.txt').write_text(logtext)
    for needle in ['PAX install log /pax/logs/install-1.txt', 'install allow-list /dev/sdd1:/pax/install-targets, 1 line(s)',
                   f'refused: not on the install allow-list: /dev/sda model={LINUX_MODEL} serial={STEAM["serial"]}',
                   'refused: a PAX live medium (the boot stick, or a copy of it): /dev/sdd',
                   'confirmation ERASE /dev/sdc', 'phase gpt: durable', 'phase root: durable', 'phase limine: durable',
                   'phase result: complete', 'Installation complete', 'poweroff']:
        need(logtext, needle, 'M6-stick-log')
    with open(d/'target.img', 'rb') as f:
        for k, at in ((1, 2097152), (2, 69206016), (3, 1048576)):
            f.seek(at)
            want = hashlib.sha256(f.read(1 << 20)).hexdigest()
            need(logtext, f'sha256 /dev/sdc{k} first MiB (byte {at}): {want}', 'M6-stick-log')
    espf = work/'stick-esp.img'
    with open(stick, 'rb') as f, open(espf, 'wb') as o:
        f.seek(esp)
        o.write(f.read(esp_bytes))
    r = run(['fsck.fat', '-n', espf], ok=False)
    (work/'stick-esp.fsck').write_bytes(r.stdout + r.stderr)
    if r.returncode != 0 or b'arning' in r.stdout + r.stderr:
        fail('M6-stick-log', 'fsck.fat -n of the stick ESP: ' + (r.stdout + r.stderr).decode(errors='replace'))
    espf.unlink()
    print('PASS M6-stick-log: /pax/logs/install-1.txt on the stick: the inventory, the refusals, the plan, every phase, the first MiB of each written partition (equal to the target image\'s); fsck.fat -n clean', flush=True)

    # Boot 2: the stick removed; the disk, chosen as from the boot menu,
    # with no boot entry of its own.
    m = Machine('boot2', qemu_args(d, vars_fd, None))
    try:
        s = m.wait(r'^login: *$', 'M7-disk-boot', 900)
        need(s, 'PAX: log in as root or as the user pax-install made.', 'M7-disk-boot')
        m.shot('disk-login')
        m.type('root\n')
        m.wait(r'^.*[$#] *$', 'M7-disk-login', 120, last=True)
        s = m.command('cat /root/px78-witness', 'M8-witness-read')
        need(s, nonce, 'M8-witness-read')
        s = m.command('ls /home', 'M8-witness-read')
        need(s, 'wolf', 'M8-witness-read')
        m.command(f"echo 'model={LINUX_MODEL} serial={TARGET['serial']}' > /tmp/allow", 'M9-running-root')
        s = m.command('pax-install --check --allow-list /tmp/allow', 'M9-running-root', 600)
        m.shot('disk-after')
        need(m.unwrapped(s), 'refused: the running root: /dev/sdc', 'M9-running-root')
        m.type('reboot -p\n')
        rc, secs = m.ended('M9-poweroff', 300)
        result['boot2_seconds'] = round(secs, 2)
    finally:
        m.kill()
    print('PASS M7-disk-boot: OVMF booted the AHCI disk with the stick removed, chosen as from the boot menu (no boot entry of its own); the installed login', flush=True)
    print(f'PASS M8-witness-read: the file written before the reboot reads back ({nonce}); /home/wolf there', flush=True)
    print('PASS M9-running-root: the installed disk, named on a list, refused as the running root', flush=True)
    after2 = witnesses(d)
    result['witness_after'] = {k: v[0] for k, v in after2.items()}
    result['witness_extents'] = {k: v[1] for k, v in after2.items()}
    if after2 != before:
        fail('M5-witness', f'a disk not the target changed: {after2} vs {before}')

    # The target's root, its allocated extents only, by e2fsck.
    root = work/'target-root.img'
    rb = (TARGET['bytes'] - 33 * 512) // 4096 * 4096 - 69206016
    rb = min(rb, 17592186040320)
    with open(d/'target.img', 'rb') as f, open(root, 'wb') as o:
        o.truncate(rb)
        at, end = 69206016, 69206016 + rb
        while at < end:
            try:
                data = os.lseek(f.fileno(), at, os.SEEK_DATA)
            except OSError:
                break
            if data >= end:
                break
            hole = min(os.lseek(f.fileno(), data, os.SEEK_HOLE), end)
            f.seek(data)
            o.seek(data - 69206016)
            left = hole - data
            while left:
                b = f.read(min(left, 1 << 20))
                o.write(b)
                left -= len(b)
            at = hole
    r = run(['e2fsck', '-fn', root], ok=False)
    (work/'target-root.fsck').write_bytes(r.stdout + r.stderr)
    root.unlink()
    if r.returncode != 0 or b'WARNING' in r.stdout + r.stderr:
        fail('M10-target-fsck', (r.stdout + r.stderr).decode(errors='replace')[-3000:])
    # The table and the ESP PAX wrote, by the host's own oracles (pax#139's):
    # sgdisk -v over the image (it reads the two tables, not the holes) and
    # fsck.fat -n over the ESP's 64 MiB at byte 2097152.
    r = run(['sgdisk', '-v', d/'target.img'], ok=False)
    (work/'target-gpt.log').write_bytes(r.stdout + r.stderr)
    if r.returncode != 0 or b'No problems found' not in r.stdout:
        fail('M10-target-fsck', 'sgdisk -v: ' + (r.stdout + r.stderr).decode(errors='replace')[-3000:])
    espf = work/'target-esp.img'
    with open(d/'target.img', 'rb') as f, open(espf, 'wb') as o:
        f.seek(2097152)
        o.write(f.read(67108864))
    r = run(['fsck.fat', '-n', espf], ok=False)
    (work/'target-esp.fsck').write_bytes(r.stdout + r.stderr)
    espf.unlink()
    if r.returncode != 0 or b'arning' in r.stdout + r.stderr:
        fail('M10-target-fsck', 'fsck.fat -n of the target ESP: ' + (r.stdout + r.stderr).decode(errors='replace'))
    print('PASS M10-target-fsck: the installed root e2fsck -fn clean; its GPT sgdisk -v clean; its ESP fsck.fat -n clean', flush=True)
    result['leg_seconds'] = round(time.monotonic() - t_leg, 2)
    result['stick_sha256'] = sha(stick)
    (work/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS M5-witness: the NVMe, the Steam and the SanDisk images byte-identical over their allocated extents before and after both boots: '
          + ', '.join(f'{k} {v}' for k, v in result['witness_after'].items()), flush=True)
    print(f'PASS I-metal: the whole path in {result["leg_seconds"]} s; the install {result["install_seconds"]} s ({result["accel"]})', flush=True)
    for n in ('nvme', 'steam', 'sandisk', 'target'):
        (d/(n + '.img')).unlink()


main()
