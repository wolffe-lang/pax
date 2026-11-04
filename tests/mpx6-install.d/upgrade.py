#!/usr/bin/env python3
"""px93: `pax-install --upgrade` on an 860-shaped disk under QEMU (contract item 5).

    upgrade.py REPO WORK OLD_STICK NEW_STICK [ROWS]

OLD_STICK is a staged install stick (pax-install-kasumi-9c88ec8a.img, its
line naming the target already); NEW_STICK the upgrade stick built from
the head (the dev variant, R-px93-D; its line written the same). Both are
copied into WORK first and never written. PAX_UPGRADE_SERIAL is the
target's serial (the one both lists name). The machine is metal.py's
kasumi: q35, OVMF, no serial port, the stick and the USB keyboard on one
xHCI, an NVMe and two SATA disks that are never targets (their allocated
extents hashed before and after every boot), and the target, an ide-hd
"Samsung SSD 860 EVO 1TB" of 1,000,204,886,016 sparse bytes. Screens are
read from PAX's exported cells by QMP memsave at the booted kernel's own
symbols; Limine's menu is seen by its green countdown line and the upgrade
entry chosen with Down and Enter, as a person at F8 would.

Rows (ROWS a comma list; all by default), in order, each PASS or FAIL by
name:
  U1 install   the old stick installs onto the target (user wolf, no games)
  U2 state     the installed system given a user's state, typed at its
               console: files in /home/wolf (one a 16 MB binary), a den
               repository with three commits, /etc/shrc edited, /etc/mine.conf,
               /usr/local/bin/hello, /etc/motd deleted
  U0 default   the new stick's default entry: nothing mounted at /mnt, the
               target byte-identical over the boot
  U8 refusals  a copy of the new stick whose list names a wrong serial: the
               kernel mounts nothing and pax-install refuses by name; on the
               right stick, an install with no matching baseline (its
               /etc/pax-release changed for the run and put back) refused by
               name, then the confirmation mistyped: cancelled, nothing written
  U3 upgrade   the upgrade entry, pax-install --upgrade, the line typed
  U4 after     every user file byte-identical, `den log` the same, /etc/shrc
               the user's with /etc/shrc.pax-new the new image's, every
               shipped path the new image's, the dropped ones gone, the
               manifest the host tool's, e2fsck -fn clean; the installed
               system boots with `kernel: <new commit>`
  U5 compiler  on the upgraded system, /usr/bin/wolf builds a program that
               prints env_args() and it prints what the same program built
               by wolf on Linux prints (R-px93-D; given as PAX_UPGRADE_LINUX)
  U6 again     a second upgrade with the same stick: nothing to change, no
               file changed
  U7 cut       on a copy of U2's target: QEMU killed after 100 steps, the
               stick booted again and the upgrade re-run: it completes, and
               U4's file checks hold
Every boot: the NVMe, Steam and SanDisk images byte-identical.
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

repo, work, old_src, new_src = map(Path, sys.argv[1:5])
ROWS = sys.argv[5].split(',') if len(sys.argv) > 5 else ['U1', 'U2', 'U0', 'U8', 'U3', 'U4', 'U5', 'U6', 'U7',
                                                        'U1d', 'U2d', 'U3d', 'U4d', 'U6d', 'U9', 'U10', 'U11', 'U12']
DEV_SRC = Path(os.environ['PAX_UPGRADE_DEV_STICK']) if os.environ.get('PAX_UPGRADE_DEV_STICK') else None
work.mkdir(parents=True, exist_ok=True)
SERIAL = os.environ['PAX_UPGRADE_SERIAL']
LINUX_ARGS = os.environ.get('PAX_UPGRADE_LINUX', '')
result = {'leg': 'px93 upgrade', 'rows': {}}
t_leg = time.monotonic()


def log(s):
    print(time.strftime('%H:%M:%S ') + s, flush=True)


def save():
    (work/'result.json').write_text(json.dumps(result, indent=2) + '\n')


def fail(row, why):
    print(f'FAIL {row}: {why}', flush=True)
    result['failed'] = row
    save()
    sys.exit(1)


def passed(row, what):
    result['rows'][row] = what
    save()
    print(f'PASS {row}: {what}', flush=True)


def run(args, ok=True, row='U0-setup', **kw):
    p = subprocess.run([str(a) for a in args], capture_output=True, **kw)
    if ok and p.returncode != 0:
        fail(row, f'{args[0]} exited {p.returncode}: {p.stdout[-2000:]!r} {p.stderr[-2000:]!r}')
    return p


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def extents_sha(p):
    h = hashlib.sha256()
    size = p.stat().st_size
    h.update(b'size %d\n' % size)
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
            at = hole
    return h.hexdigest()


def esp_range(img):
    with open(img, 'rb') as f:
        f.seek(512)
        h = f.read(92)
        f.seek(struct.unpack_from('<Q', h, 72)[0] * 512)
        e = f.read(128)
    first, last = struct.unpack_from('<QQ', e, 32)
    return first * 512, (last - first + 1) * 512


def esp_get(img, path, out):
    off, _n = esp_range(img)
    run(['mcopy', '-n', '-i', f'{img}@@{off}', '::' + path, out], env={'MTOOLS_SKIP_CHECK': '1', 'PATH': '/usr/bin:/bin'})
    return Path(out)


def symbols(elf):
    out = run(['nm', elf]).stdout.decode()
    return {p[2]: int(p[0], 16) for p in (l.split() for l in out.splitlines()) if len(p) == 3}


# --- the disks (metal.py's kasumi, px86's 860) ---------------------------------

TARGET = {'model': 'Samsung SSD 860 EVO 1TB', 'serial': SERIAL, 'bytes': 1000204886016, 'size': '1.0 TB'}
TARGET_MODEL = TARGET['model'][:16].rstrip()
STEAM = {'model': 'Samsung SSD 870 EVO 4TB', 'serial': 'S6PXNM0T700001', 'bytes': 4000787030016}
SANDISK = {'model': 'SanDisk SDSSDH3 512G', 'serial': '2104AB401234', 'bytes': 512110190592}
NVME = {'serial': 'S6Z1NJ0W000001', 'bytes': 1000204886016}
ROOT_START = 69206016


def foreign_disk(path, spec, parts):
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


DISKS = work/'disks'


def make_disks(size=None, used=None):
    if DISKS.exists():
        shutil.rmtree(DISKS)
    DISKS.mkdir()
    gib = 2097152
    foreign_disk(DISKS/'nvme.img', NVME, [('esp', 2048, 2048 + gib - 1), ('linux', 2048 + gib, None)])
    foreign_disk(DISKS/'steam.img', STEAM, [('linux', 2048, None)])
    q = SANDISK['bytes'] // 512 // 4
    foreign_disk(DISKS/'sandisk.img', SANDISK, [('linux', 2048, q - 1), ('linux', q, 2 * q - 1), ('linux', 2 * q, 3 * q - 1), ('linux', 3 * q, None)])
    with open(DISKS/'target.img', 'wb') as f:
        f.truncate(size or TARGET['bytes'])
    if used:
        log(run([repo/'tools/used-disk', 'make', DISKS/'target.img', used]).stdout.decode().strip())


def witnesses():
    return {n: extents_sha(DISKS/(n + '.img')) for n in ('nvme', 'steam', 'sandisk')}


WITNESS = {}


def check_witnesses(row):
    now = witnesses()
    if now != WITNESS:
        fail(row, f'a disk that is never a target changed: {now} vs {WITNESS}')


# --- QEMU (metal.py's Machine, the symbols per boot) ----------------------------

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
STOPPED = r'^(pax-install: (stopped|refused|cancelled|upgrade (stopped|refused|cancelled))|install log: stopped|target log:|usage: pax-install)'
USAGE = r'^usage: pax-install'
PROMPT = r'^.*[$#] *$'


class Machine:
    def __init__(self, name, sym, stick):
        self.name = name
        self.sym = sym
        self.dir = work/name
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir()
        self.sock = self.dir/'qmp.sock'
        code = os.environ.get('PAX_OVMF_CODE', '/usr/share/OVMF/OVMF_CODE_4M.fd')
        vars_fd = self.dir/'vars.fd'
        shutil.copyfile(os.environ.get('PAX_OVMF_VARS', '/usr/share/OVMF/OVMF_VARS_4M.fd'), vars_fd)
        a = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', '4096M', '-accel', 'kvm',
             '-display', 'none', '-serial', 'none', '-parallel', 'none', '-nic', 'none', '-no-reboot',
             '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
             '-drive', f'if=pflash,format=raw,unit=1,file={vars_fd}', '-device', 'qemu-xhci,id=xhci']
        if stick:
            a += ['-drive', f'file={stick},if=none,id=stick,format=raw',
                  '-device', 'usb-storage,bus=xhci.0,drive=stick,removable=on,bootindex=0']
        a += ['-device', 'usb-kbd,bus=xhci.0',
              '-drive', f'file={DISKS/"nvme.img"},if=none,id=nv,format=raw', '-device', f'nvme,serial={NVME["serial"]},drive=nv',
              '-drive', f'file={DISKS/"steam.img"},if=none,id=sa,format=raw',
              '-device', f'ide-hd,bus=ide.0,drive=sa,model={STEAM["model"]},serial={STEAM["serial"]}',
              '-drive', f'file={DISKS/"sandisk.img"},if=none,id=sb,format=raw',
              '-device', f'ide-hd,bus=ide.1,drive=sb,model={SANDISK["model"]},serial={SANDISK["serial"]}',
              '-drive', f'file={DISKS/"target.img"},if=none,id=sc,format=raw,discard=unmap,detect-zeroes=unmap',
              '-device', f'ide-hd,bus=ide.2,drive=sc,model={TARGET["model"]},serial={TARGET["serial"]}' + ('' if stick else ',bootindex=0'),
              '-qmp', f'unix:{self.sock},server=on,wait=off']
        (self.dir/'command.json').write_text(json.dumps([str(x) for x in a], indent=2) + '\n')
        self.qlog = (self.dir/'qemu.log').open('wb')
        self.t0 = time.monotonic()
        self.p = subprocess.Popen([str(x) for x in a], stdin=subprocess.DEVNULL, stdout=self.qlog, stderr=subprocess.STDOUT)
        for _ in range(200):
            if self.sock.exists():
                break
            if self.p.poll() is not None:
                fail(name, 'QEMU did not start: ' + (self.dir/'qemu.log').read_text(errors='replace')[-2000:])
            time.sleep(.05)
        self.q = QMP(self.sock)
        self.shots = 0
        self.cols = 0
        self.since = ''

    def run(self, cmd):
        """Type a command whose output the next waits read alone."""
        self.since = '$ ' + cmd
        self.type(cmd + '\n')

    def screen(self):
        self.q.call('stop')
        try:
            st = self.dir/'state.bin'
            if self.q.hmp(f'memsave 0x{self.sym["pax_screen_state"]:x} 552 "{st}"'):
                return ''
            state = struct.unpack('<69Q', st.read_bytes())
            cols, rows = state[5], state[6]
            if not (state[0] and 1 <= cols <= 256 and 1 <= rows <= 128):
                return ''
            at = self.sym['pax_screen_cells'] + (256 * 128 * 4 if state[60] else 0)
            cf = self.dir/'cells.bin'
            if self.q.hmp(f'memsave 0x{at:x} {cols * rows * 4} "{cf}"'):
                return ''
            cells = struct.unpack('<' + str(cols * rows) + 'I', cf.read_bytes())
            lines = [''.join(chr(v & 255) if 32 <= v & 255 < 127 else ' ' for v in cells[y * cols:(y + 1) * cols]) for y in range(rows)]
            self.cols = cols
            return '\n'.join(l.rstrip() for l in lines).rstrip() + '\n'
        finally:
            self.q.call('cont')

    def unwrapped(self, text):
        out = []
        full = False
        for line in text.split('\n'):
            if out and full:
                out[-1] += line
            else:
                out.append(line)
            full = self.cols > 0 and len(line) == self.cols
        return '\n'.join(out)

    def wait(self, pattern, row, timeout=300, last=False, bad=None):
        end = time.monotonic() + timeout
        text = ''
        while time.monotonic() < end:
            if self.p.poll() is not None:
                fail(row, f'QEMU ended (exit {self.p.returncode}) before /{pattern}/; screen:\n{text}')
            text = self.screen()
            flat = self.unwrapped(text)
            # After a command typed by run(), only what follows its last echo counts: a
            # previous run's lines may still be on the screen.
            if self.since and self.since in flat:
                flat = flat[flat.rindex(self.since):]
                text = flat
            look = text.rstrip('\n').split('\n')[-1] if last else flat
            if re.search(pattern, look, re.M):
                return text
            if bad and re.search(bad, flat, re.M):
                self.shot('bad')
                fail(row, f'/{bad}/ on the screen before /{pattern}/; screen:\n{text}')
            time.sleep(.3)
        self.shot('timeout')
        fail(row, f'no /{pattern}/ on the screen in {timeout} s; screen:\n{text}')

    def ppm(self, name):
        p = self.dir/f'{name}.ppm'
        self.q.call('screendump', {'filename': str(p)})
        data = p.read_bytes()
        m = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
        w, h = map(int, m.groups())
        return w, h, data[m.end():]

    def shot(self, name):
        self.shots += 1
        (self.dir/f'{self.shots:02d}-{name}.txt').write_text(self.screen())

    def key(self, k, down):
        self.q.call('input-send-event', {'events': [{'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': k}}}]})

    def tap(self, k):
        self.key(k, True)
        time.sleep(.05)
        self.key(k, False)
        time.sleep(.05)

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
        self.since = '$ ' + line
        self.type(line + '\n')
        time.sleep(.5)
        return self.wait(PROMPT, row, timeout, last=True)

    def upgrade_entry(self, row):
        """Limine's menu (its green countdown line at the screen's foot,
        px77c's sign), then Down and Enter: the second entry."""
        end = time.monotonic() + 300
        while time.monotonic() < end:
            if self.p.poll() is not None:
                fail(row, 'QEMU ended before Limine\'s menu')
            w, h, raw = self.ppm('menu')
            for y in range(h - 60, h - 8, 2):
                r = raw[y * w * 3:(y + 1) * w * 3]
                if any(r[x + 1] > 150 and r[x] < 80 and r[x + 2] < 80 for x in range(0, w * 3, 6)):
                    self.tap('down')
                    time.sleep(.3)
                    self.tap('ret')
                    return
            time.sleep(.2)
        fail(row, 'no Limine menu in 300 s')

    def ended(self, row, timeout=300):
        try:
            self.p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.shot('no-poweroff')
            fail(row, 'QEMU did not end (no ACPI power-off)')
        self.qlog.close()
        return self.p.returncode

    def cut(self):
        self.p.kill()
        self.p.wait()
        self.qlog.close()

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


def need(text, needle, row):
    if needle not in text:
        fail(row, f'missing {needle!r} on the screen:\n{text}')


def login(m, row, timeout=900):
    s = m.wait(r'^login: *$', row, timeout)
    m.type('root\n')
    m.wait(PROMPT, row, 120, last=True)
    return s


def poweroff(m, row):
    m.type('poweroff\n')
    if m.ended(row) != 0:
        fail(row, 'QEMU did not exit 0 at power-off')


# --- the target's root, read on the host ----------------------------------------

def root_image(out):
    rb = min((TARGET['bytes'] - 33 * 512) // 4096 * 4096 - ROOT_START, 17592186040320)
    with open(DISKS/'target.img', 'rb') as f, open(out, 'wb') as o:
        o.truncate(rb)
        at, end = ROOT_START, ROOT_START + rb
        while at < end:
            try:
                data = os.lseek(f.fileno(), at, os.SEEK_DATA)
            except OSError:
                break
            if data >= end:
                break
            hole = min(os.lseek(f.fileno(), data, os.SEEK_HOLE), end)
            f.seek(data)
            o.seek(data - ROOT_START)
            left = hole - data
            while left:
                b = f.read(min(left, 1 << 20))
                o.write(b)
                left -= len(b)
            at = hole
    return out


def tree(name, row):
    """The target root's every path: kind, mode and sha256 (rdump by
    debugfs, a black box), and e2fsck -fn's verdict."""
    img = root_image(work/f'{name}-root.img')
    out = work/f'{name}-tree'
    if out.exists():
        run(['chmod', '-R', 'u+w', out], row=row)  # the root's 0555 directories, dumped as they are
        shutil.rmtree(out)
    out.mkdir()
    run(['debugfs', '-R', f'rdump / {out}', img], row=row)
    fsck = run(['e2fsck', '-fn', img], ok=False)
    (work/f'{name}-e2fsck.txt').write_bytes(fsck.stdout + fsck.stderr)
    # The modes and owners debugfs knows, path by path (ls -l per directory).
    rows = {}
    kids = list(out.iterdir())
    top = kids[0] if len(kids) == 1 and not (out/'etc').exists() else out
    for p in sorted(top.rglob('*')):
        rel = '/' + p.relative_to(top).as_posix()
        if p.is_symlink():
            t = os.readlink(p).encode()
            rows[rel] = ('l', 0, hashlib.sha256(t).hexdigest())
        elif p.is_dir():
            rows[rel] = ('d', p.stat().st_mode & 0o7777, '-')
        else:
            rows[rel] = ('f', p.stat().st_mode & 0o7777, sha(p))
    img.unlink()
    (work/f'{name}-tree.json').write_text(json.dumps(rows, indent=1, sort_keys=True) + '\n')
    return rows, fsck.returncode, (fsck.stdout + fsck.stderr).decode(errors='replace')


def manifest_rows(text):
    rows = {}
    for line in text.splitlines()[6:]:
        k, mode, uid, gid, size, digest, path = line.split(' ', 6)
        rows[path] = (k, int(mode, 8), digest)
    return rows


def user_paths(rows):
    return {p: v for p, v in rows.items() if p == '/home' or p.startswith('/home/') or p.startswith('/usr/local') or p == '/etc/mine.conf'}


# --- the leg ---------------------------------------------------------------------


C = {}


def sticks():
    """The sticks copied in and checked; the new stick's manifest by the host tool."""
    pairs = [('old', old_src), ('new', new_src)] + ([('dev', DEV_SRC)] if DEV_SRC else [])
    for name, src in pairs:
        d = work/f'{name}-stick.img'
        shutil.copyfile(src, d)
        d.chmod(0o644)
        if sha(d) != sha(src):
            fail('U0-setup', f'the copy of {src} differs')
        result[f'{name}_stick'] = sha(src)
        C[name] = d
        C['sym_' + name] = symbols(esp_get(d, '/boot/pax', work/f'{name}-kernel.elf'))
        listed = run(['mtype', '-i', f'{d}@@{esp_range(d)[0]}', '::/pax/install-targets'], env={'MTOOLS_SKIP_CHECK': '1', 'PATH': '/usr/bin:/bin'}).stdout.decode()
        if listed.splitlines().count(f'model={TARGET_MODEL} serial={SERIAL}') != 1:
            fail('U0-setup', f'{d.name} does not list the target exactly once')
    cpio = esp_get(C['new'], '/boot/initramfs.cpio', work/'new-initramfs.cpio')
    text = run(['python3', '-I', repo/'tools/install-manifest', '--cpio', cpio, work/'new-kernel.elf', 'the new stick']).stdout.decode()
    cpio.unlink()
    (work/'new-stick.manifest').write_text(text)
    C['new_rows'] = manifest_rows(text)
    C['new_commit'] = text.splitlines()[1].split()[1]
    log(f'new commit {C["new_commit"]}; {len(C["new_rows"])} rows in its manifest')


def disks(size=None, used=None):
    make_disks(size, used)
    WITNESS.clear()
    WITNESS.update(witnesses())
    result.setdefault('witnesses', []).append(dict(WITNESS))


def install_from(stick, sym, name, row):
    """The stick's guided install onto /dev/sdc: user wolf, no games, yes."""
    m = Machine(name, sym, stick)
    try:
        login(m, row)
        m.type('pax-install\n')
        page = m.wait(r'pax-install> *$', row, 600, bad=STOPPED)
        num = re.search(r'^[> ] (\d+)\. /dev/sdc ', m.unwrapped(page), re.M)
        if not num:
            fail(row, 'the target is not on the page:\n' + page)
        m.type(num.group(1) + '\n')
        m.wait(r'New user name', row, 120, bad=STOPPED)
        m.type('wolf\n')
        m.wait(r'Install the lair', row, 120, bad=STOPPED)
        m.type('n\n')
        m.wait(r'Type yes to install; anything else cancels: pax-install> *$', row, 300, bad=STOPPED)
        m.type('yes\n')
        t = time.monotonic()
        m.wait(r'^Installation complete', row, 3600, bad=STOPPED)
        secs = round(time.monotonic() - t, 2)
        m.wait(r'poweroff to power off', row, 120)
        poweroff(m, row)
    finally:
        m.kill()
    check_witnesses(row)
    return secs


STATE = ['mkdir -p /home/wolf/notes /usr/local/bin',
         "printf '%s\\n' '{nonce} notes' > /home/wolf/notes/a.txt",
         "printf 'line one\\nline two\\n' > /home/wolf/notes/b.txt",
         'cp /bin/den /home/wolf/den-copy',
         "printf '# px93: the user changed this file\\nexport PX93=yes\\n' >> /etc/shrc",
         "printf 'mine {nonce}\\n' > /etc/mine.conf",
         "printf '#!/bin/sh\\necho hello from /usr/local\\n' > /usr/local/bin/hello",
         'chmod 755 /usr/local/bin/hello',
         'rm /etc/motd',
         'cd /home/wolf',
         'export GIT_AUTHOR_NAME=Wolf GIT_AUTHOR_EMAIL=wolf@pax.invalid GIT_COMMITTER_NAME=Wolf GIT_COMMITTER_EMAIL=wolf@pax.invalid TZ=UTC',
         'den init repo', 'cd repo',
         "printf 'one\\n' > a.txt", 'den add a.txt', "den commit -m 'first'",
         "printf 'two\\n' >> a.txt", 'den add a.txt', "den commit -m 'second'",
         "printf 'three\\n' > b.txt", 'den add b.txt', "den commit -m 'third'",
         'den log > /root/den-log-before.txt; echo den-log=$?']
ARGS_SRC = "printf 'fn main() {\\n    for a in env_args() { print(\"arg: {a}\") }\\n}\\n' > main.lu"
ARGS_OUT = b'arg: one\narg: two words\n'


def state(sym, name, row, wolf_program=False):
    """A user's state, typed at the installed console (and, on a dev install, a
    program built there by /usr/bin/wolf, its source, binary and output under
    /home/wolf/args); the root's tree read on the host."""
    nonce = 'px93-' + secrets.token_hex(6)
    m = Machine(name, sym, None)
    try:
        login(m, row)
        if wolf_program:
            for c in ['mkdir -p /home/wolf/args', 'cd /home/wolf/args', ARGS_SRC,
                      'wolf build --no-cache main.lu -o args; echo build=$?']:
                s = m.command(c, row, 900)
            need(m.unwrapped(s), 'build=0', row)
            s = m.command("./args one 'two words' > out.txt; echo run=$?; cd /", row)
            need(m.unwrapped(s), 'run=0', row)
        for c in STATE:
            s = m.command(c.replace('{nonce}', nonce), row, 300)
        need(m.unwrapped(s), 'den-log=0', row)
        m.command('cd /', row)
        poweroff(m, row)
    finally:
        m.kill()
    check_witnesses(row)
    before, rc, text = tree(name, row)
    if rc != 0:
        fail(row, 'e2fsck -fn after the user state: ' + text[-2000:])
    den = (work/f'{name}-tree/root/den-log-before.txt').read_text()
    if den.count('\ncommit ') + den.startswith('commit ') != 3:
        fail(row, 'den log does not show three commits:\n' + den)
    for p in ('/home/wolf/notes/a.txt', '/home/wolf/den-copy', '/etc/mine.conf', '/usr/local/bin/hello', '/home/wolf/repo/.git') + \
            (('/home/wolf/args/main.lu', '/home/wolf/args/args', '/home/wolf/args/out.txt') if wolf_program else ()):
        if p not in before:
            fail(row, f'{p} is not on the target')
    if wolf_program and (work/f'{name}-tree/home/wolf/args/out.txt').read_bytes() != ARGS_OUT:
        fail(row, 'the program built on the target printed ' + repr((work/f'{name}-tree/home/wolf/args/out.txt').read_bytes()))
    if '/etc/motd' in before:
        fail(row, '/etc/motd is still there')
    return before, den


def token_of(flat, row):
    t = re.search(r'^(UPGRADE /dev/sdc .*\S)\s*$', flat, re.M)
    if not t:
        fail(row, 'no UPGRADE line:\n' + flat)
    return t.group(1)


def upgrade(m, row, needles):
    """pax-install --upgrade in a booted upgrade entry: the plan, its needles,
    the line typed, complete."""
    m.run('pax-install --upgrade')
    s = m.wait(r'^UPGRADE /dev/sdc .*$', row, 900, bad=STOPPED)
    flat = m.unwrapped(s)
    (work/f'{row}-plan.txt').write_text(flat)
    for n in needles:
        need(flat, n, row)
    token = token_of(flat, row)
    if not token.startswith(f'UPGRADE /dev/sdc {TARGET_MODEL} {SERIAL} '):
        fail(row, 'the line does not name the disk: ' + token)
    m.wait(r'pax-install> *$', row, 60, last=True)
    m.type(token + '\n')
    t = time.monotonic()
    m.wait(r'^Upgrade complete', row, 3600, bad=STOPPED)
    secs = round(time.monotonic() - t, 2)
    m.wait(r'poweroff to power off', row, 120)
    m.shot('complete')
    return secs


def after(name, row, before, base_name, fsck_required=True):
    new_rows = C['new_rows']
    rows, rc, text = tree(name, row)
    for p, v in user_paths(before).items():
        if rows.get(p) != v:
            fail(row, f'the user path {p} changed: {before.get(p)} -> {rows.get(p)}')
    if rows.get('/etc/shrc') != before['/etc/shrc']:
        fail(row, '/etc/shrc is not the user\'s')
    if rows.get('/etc/shrc.pax-new', ('',))[2:] != (new_rows['/etc/shrc'][2],):
        fail(row, f'/etc/shrc.pax-new is not the new image\'s: {rows.get("/etc/shrc.pax-new")}')
    wrong_rows = []
    for p, (k, mode, digest) in new_rows.items():
        if k == 'g' or p == '/etc/shrc':
            continue
        got = rows.get(p)
        if got is None or (k == 'd' and got[0] != 'd') or (k != 'd' and (got[0], got[2]) != (k, digest)) or (k == 'f' and got[1] != mode):
            wrong_rows.append((p, got, (k, mode, digest)))
    if wrong_rows:
        fail(row, f'{len(wrong_rows)} shipped path(s) not the new image\'s: {wrong_rows[:8]}')
    base = manifest_rows((repo/f'user/install/baselines/{base_name}.manifest').read_text())
    left = [p for p in base if p not in new_rows and base[p][0] in 'fl' and p in rows]
    if left:
        fail(row, f'dropped shipped paths still there: {left[:8]}')
    mtext = (work/f'{name}-tree/etc/pax-install/manifest').read_text()
    # Files by kind, mode and sha256; a link by its target; a directory by its kind (PAX's lstat and the
    # archive's header may spell a link's or a directory's mode differently: never a file's).
    def key(v):
        return v if v[0] == 'f' else (v[0], v[2]) if v[0] == 'l' else (v[0],)
    mine = {p: key(v) for p, v in manifest_rows(mtext).items() if v[0] != 'g'}
    host = {p: key(v) for p, v in new_rows.items() if v[0] != 'g'}
    if mine != host:
        diff = sorted(set(mine.items()) ^ set(host.items()))[:8]
        fail(row, f'the target\'s manifest differs from tools/install-manifest\'s: {diff}')
    if rc != 0 and fsck_required:
        fail(row, 'e2fsck -fn: ' + text[-3000:])
    return rows, rc


def again(name, row, prev, expect='Nothing to change: /dev/sdc already holds this image', needles=()):
    """The upgrade entry once more: nothing to change, and no path changed."""
    m = Machine(name, C['sym_new'], C['new'])
    try:
        m.upgrade_entry(row)
        login(m, row)
        m.run('pax-install --upgrade')
        s = m.wait('^' + re.escape(expect), row, 900, bad=r'^UPGRADE /dev/sdc|' + STOPPED)
        for n in needles:
            need(m.unwrapped(s), n, row)
        m.wait(PROMPT, row, 60, last=True)
        poweroff(m, row)
    finally:
        m.kill()
    check_witnesses(row)
    rows, rc, text = tree(name, row)
    if prev is not None and rows != prev:
        diff = sorted(set(rows.items()) ^ set(prev.items()))[:8]
        fail(row, f'the run changed paths: {diff}')
    return rows


def boot_after(name, row, den_before, extra=()):
    """The upgraded disk booted alone: its kernel line names the new commit,
    den log is the same, and `extra` commands' outputs saved under /root."""
    m = Machine(name, C['sym_new'], None)
    try:
        s = login(m, row)
        need(m.unwrapped(s), f'kernel: {C["new_commit"]}', row)
        s = m.command('cd /home/wolf/repo && den log > /root/den-log-after.txt; echo den-log=$?; cd /', row)
        need(m.unwrapped(s), 'den-log=0', row)
        for c, want in extra:
            s = m.command(c, row, 900)
            need(m.unwrapped(s), want, row)
        poweroff(m, row)
    finally:
        m.kill()
    check_witnesses(row)
    rows, rc, text = tree(name, row)
    if (work/f'{name}-tree/root/den-log-after.txt').read_text() != den_before:
        fail(row, 'den log differs after the upgrade')
    return rows


def track_a():
    """The 860 as px92's 9c88ec8a stick left it, upgraded (U1-U8)."""
    old, new, new_rows, new_commit = C['old'], C['new'], C['new_rows'], C['new_commit']
    sym_old, sym_new = C['sym_old'], C['sym_new']
    disks()
    result['install_seconds'] = install_from(old, sym_old, 'u1-install', 'U1-install')
    passed('U1-install', f'the old stick installed the target in {result["install_seconds"]} s')
    before, den_before = state(sym_old, 'u2', 'U2-state')
    run(['cp', '--sparse=always', DISKS/'target.img', work/'u2-target.img'], row='U2-state')
    passed('U2-state', f'{len(user_paths(before))} user paths, den log with three commits, /etc/shrc edited, /etc/motd deleted; e2fsck -fn clean')
    # U0: the new stick's default entry mounts nothing and writes nothing.
    t0 = extents_sha(DISKS/'target.img')
    m = Machine('u0-default', sym_new, new)
    try:
        login(m, 'U0-default')
        s = m.command('[ -e /mnt ]; echo mnt=$?', 'U0-default')
        flat = m.unwrapped(s)
        need(flat, 'mnt=1', 'U0-default')
        if 'upgrade: ' in flat:
            fail('U0-default', 'an upgrade: line under the default entry')
        poweroff(m, 'U0-default')
    finally:
        m.kill()
    check_witnesses('U0-default')
    if extents_sha(DISKS/'target.img') != t0:
        fail('U0-default', 'the target changed under the default entry')
    passed('U0-default', 'the live entry: no /mnt, the target byte-identical over the boot')

    # U8: the refusals.
    wrong = work/'wrong-serial-stick.img'
    shutil.copyfile(new, wrong)
    off = esp_range(wrong)[0]
    lst = work/'wrong-list'
    lst.write_text(run(['mtype', '-i', f'{wrong}@@{off}', '::/pax/install-targets'], env={'MTOOLS_SKIP_CHECK': '1', 'PATH': '/usr/bin:/bin'}).stdout.decode()
                   .replace(f'serial={SERIAL}', 'serial=S599NZFNB00000X'))
    run(['mcopy', '-o', '-i', f'{wrong}@@{off}', lst, '::/pax/install-targets'], env={'MTOOLS_SKIP_CHECK': '1', 'PATH': '/usr/bin:/bin'})
    t0 = extents_sha(DISKS/'target.img')
    m = Machine('u8-wrong-serial', sym_new, wrong)
    try:
        m.upgrade_entry('U8-wrong-serial')
        login(m, 'U8-wrong-serial')
        m.run('pax-install --upgrade')
        s = m.wait(r'^pax-install: upgrade refused: ', 'U8-wrong-serial', 600, bad=USAGE)
        need(m.unwrapped(s), 'pax-install: upgrade refused: no disk here is on the install allow-list', 'U8-wrong-serial')
        m.wait(PROMPT, 'U8-wrong-serial', 60, last=True)
        s = m.command('[ -e /mnt/target ]; echo t=$?', 'U8-wrong-serial')
        need(m.unwrapped(s), 't=1', 'U8-wrong-serial')
        poweroff(m, 'U8-wrong-serial')
    finally:
        m.kill()
    check_witnesses('U8-wrong-serial')
    if extents_sha(DISKS/'target.img') != t0:
        fail('U8-wrong-serial', 'the target changed')
    wrong.unlink()
    passed('U8-wrong-serial', 'the list naming another serial: nothing mounted, pax-install refused by name, the target byte-identical')

    # U3 (with U8's two in-guest refusals first): the upgrade.
    m = Machine('u3-upgrade', sym_new, new)
    try:
        m.upgrade_entry('U3-upgrade')
        login(m, 'U3-upgrade')
        s = m.command('cat /proc/self/mounts; echo end', 'U3-upgrade')
        need(m.unwrapped(s), '/mnt/target ext2', 'U3-upgrade')
        # No baseline: the target's /etc/pax-release changed for one run.
        m.command('cp /mnt/target/etc/pax-release /root/pr; echo changed >> /mnt/target/etc/pax-release', 'U8-no-baseline')
        m.run('pax-install --upgrade')
        s = m.wait(r'^pax-install: upgrade refused: ', 'U8-no-baseline', 900, bad=USAGE)
        need(m.unwrapped(s), 'has no manifest and matches no baseline this stick carries', 'U8-no-baseline')
        m.wait(PROMPT, 'U8-no-baseline', 60, last=True)
        s = m.command('cat /root/pr > /mnt/target/etc/pax-release; [ -e /mnt/target/etc/pax-install ]; echo p=$?', 'U8-no-baseline')
        need(m.unwrapped(s), 'p=1', 'U8-no-baseline')
        passed('U8-no-baseline', 'an install matching no baseline refused by name, before any write')
        # The confirmation mistyped.
        m.run('pax-install --upgrade')
        s = m.wait(r'^UPGRADE /dev/sdc .*$', 'U8-mistyped', 900, bad=STOPPED)
        token = token_of(m.unwrapped(s), 'U8-mistyped')
        m.wait(r'pax-install> *$', 'U8-mistyped', 60, last=True)
        m.type(token[:-1] + ('0' if token[-1] != '0' else '1') + '\n')
        s = m.wait(r'^pax-install: upgrade cancelled before writes', 'U8-mistyped', 120)
        m.wait(PROMPT, 'U8-mistyped', 60, last=True)
        s = m.command('[ -e /mnt/target/etc/pax-install ]; echo p=$?', 'U8-mistyped')
        need(m.unwrapped(s), 'p=1', 'U8-mistyped')
        passed('U8-mistyped', 'the line mistyped by one character: cancelled by name; /etc/pax-install not made')
        result['upgrade_seconds'] = upgrade(m, 'U3-upgrade', ['Installed: ', 'from the baseline 9c88ec8a.manifest', 'beside /etc/shrc.pax-new'])
        poweroff(m, 'U3-upgrade')
    finally:
        m.kill()
    check_witnesses('U3-upgrade')
    passed('U3-upgrade', f'the upgrade entry, the plan from the 9c88ec8a baseline, the line typed; complete in {result["upgrade_seconds"]} s')
    after('u4', 'U4-after', before, '9c88ec8a')
    extra = []
    if 'U5' in ROWS:
        extra = [('mkdir -p /root/args && cd /root/args', ''), (ARGS_SRC, ''),
                 ('env PATH=/usr/bin:/bin WOLF_STD=/usr/share/wolf/compiler-std wolf build --no-cache main.lu -o args; echo build=$?', 'build=0'),
                 ("./args one 'two words' > out.txt; echo run=$?; cd /", 'run=0')]
    rows5 = boot_after('u5', 'U4-after', den_before, extra)
    passed('U4-after', f'every user path byte-identical ({len(user_paths(before))}), den log the same, /etc/shrc yours and /etc/shrc.pax-new the new image\'s, '
           f'{len(new_rows)} shipped rows the new image\'s, the dropped gone, the manifest the host tool\'s, e2fsck -fn clean; booted with kernel: {new_commit[:8]}')
    if 'U5' in ROWS:
        got = (work/'u5-tree/root/args/out.txt').read_bytes()
        want = Path(LINUX_ARGS).read_bytes() if LINUX_ARGS else ARGS_OUT
        if got != want:
            fail('U5-compiler', f'PAX printed {got!r}, Linux {want!r}')
        passed('U5-compiler', f'/usr/bin/wolf built env_args() on PAX; it printed {got!r}, the same bytes as on Linux')
    again('u6', 'U6-again', rows5)
    passed('U6-again', 'the second upgrade: "Nothing to change", every path as it was')
    # U7: a power cut mid-upgrade on a copy of U2's target.
    if 'U7' in ROWS:
        run(['cp', '--sparse=always', work/'u2-target.img', DISKS/'target.img'], row='U7-cut')
        m = Machine('u7-cut', sym_new, new)
        try:
            m.upgrade_entry('U7-cut')
            login(m, 'U7-cut')
            m.run('pax-install --upgrade')
            s = m.wait(r'^UPGRADE /dev/sdc .*$', 'U7-cut', 900, bad=STOPPED)
            token = re.search(r'^(UPGRADE /dev/sdc .*\S)\s*$', m.unwrapped(s), re.M).group(1)
            m.wait(r'pax-install> *$', 'U7-cut', 60, last=True)
            m.type(token + '\n')
            m.wait(r'^upgrade: 100 of ', 'U7-cut', 1800, bad=STOPPED)
            m.shot('before-cut')
            m.cut()
        finally:
            m.kill()
        log('QEMU killed at 100 steps')
        m = Machine('u7-again', sym_new, new)
        try:
            m.upgrade_entry('U7-again')
            login(m, 'U7-again')
            m.run('pax-install --upgrade')
            s = m.wait(r'^UPGRADE /dev/sdc .*$', 'U7-again', 900, bad=STOPPED)
            flat = m.unwrapped(s)
            (work/'u7-plan.txt').write_text(flat)
            need(flat, "from the cut upgrade's record", 'U7-again')
            token = re.search(r'^(UPGRADE /dev/sdc .*\S)\s*$', flat, re.M).group(1)
            m.wait(r'pax-install> *$', 'U7-again', 60, last=True)
            m.type(token + '\n')
            m.wait(r'^Upgrade complete', 'U7-again', 3600, bad=STOPPED)
            m.wait(r'poweroff to power off', 'U7-again', 120)
            poweroff(m, 'U7-again')
        finally:
            m.kill()
        check_witnesses('U7-again')
        _r, rc7 = after('u7', 'U7-cut', before, '9c88ec8a', fsck_required=False)
        verdict = 'clean' if rc7 == 0 else 'exit %d (%s)' % (rc7, ' | '.join(l for l in (work/'u7-e2fsck.txt').read_text().splitlines() if l and not l.startswith(('Pass ', 'e2fsck ')))[:600])
        result['u7_e2fsck'] = verdict
        passed('U7-cut', f'killed after 100 steps, re-run from the record: complete; every user path byte-identical, every shipped path the new image\'s; e2fsck -fn {verdict}')


def track_d():
    """The 860 as it is now: px92's dev stick 8b4e98ae's install, a user's state and
    a wolf program built on it, upgraded (U1d-U6d)."""
    if not DEV_SRC:
        fail('U1d-install', 'PAX_UPGRADE_DEV_STICK names no stick')
    disks()
    secs = install_from(C['dev'], C['sym_dev'], 'u1d-install', 'U1d-install')
    passed('U1d-install', f'the 8b4e98ae dev stick installed the target in {secs} s')
    before, den_before = state(C['sym_dev'], 'u2d', 'U2d-state', wolf_program=True)
    passed('U2d-state', f'{len(user_paths(before))} user paths, /usr/bin/wolf built /home/wolf/args/args on the target and it printed its two arguments; den log with three commits, /etc/shrc edited, /etc/motd deleted; e2fsck -fn clean')
    m = Machine('u3d-upgrade', C['sym_new'], C['new'])
    try:
        m.upgrade_entry('U3d-upgrade')
        login(m, 'U3d-upgrade')
        secs = upgrade(m, 'U3d-upgrade', ['Installed: 8b4e98ae', 'from the baseline 8b4e98ae.manifest', 'beside /etc/shrc.pax-new'])
        poweroff(m, 'U3d-upgrade')
    finally:
        m.kill()
    check_witnesses('U3d-upgrade')
    passed('U3d-upgrade', f'the plan from the 8b4e98ae baseline, the line typed; complete in {secs} s')
    after('u4d', 'U4d-after', before, '8b4e98ae')
    rows = boot_after('u4d-boot', 'U4d-after', den_before,
                      [("/home/wolf/args/args one 'two words' > /root/args-after.txt; echo run=$?", 'run=0')])
    if (work/'u4d-boot-tree/root/args-after.txt').read_bytes() != ARGS_OUT:
        fail('U4d-after', 'the program built before the upgrade prints otherwise after it')
    passed('U4d-after', f'every user path byte-identical ({len(user_paths(before))}: the program\'s source, binary and output among them), the program still prints its arguments, '
           f'/etc/shrc yours and /etc/shrc.pax-new the new image\'s, every shipped path the new image\'s, the manifest the host tool\'s, e2fsck -fn clean; booted with kernel: {C["new_commit"][:8]}')
    again('u6d', 'U6d-again', rows)
    passed('U6d-again', 'the second upgrade of the dev install: "Nothing to change", every path as it was')


def track_x():
    """A fresh install from the new stick upgraded with no baseline (U9); the
    refusals that need their own disk: not PAX's (U10), too little space (U11);
    a generated file in an earlier installer's text regenerated, the user's kept (U12)."""
    if 'U9' in ROWS:
        u9()
    if 'U10' in ROWS:
        u10()
    if 'U11' in ROWS:
        u11()
    if 'U12' in ROWS:
        u12()


def u9():
    disks()
    secs = install_from(C['new'], C['sym_new'], 'u9-install', 'U9-fresh')
    rows, rc, text = tree('u9-installed', 'U9-fresh')
    if '/etc/pax-install/manifest' not in rows or rc != 0:
        fail('U9-fresh', f'the fresh install has no /etc/pax-install/manifest, or e2fsck -fn exit {rc}')
    again('u9-again', 'U9-fresh', rows, needles=[f'Installed: {C["new_commit"]}, from its manifest'])
    passed('U9-fresh', f'the new stick installed the target in {secs} s with its own /etc/pax-install/manifest; the upgrade with the same stick read it, no baseline: "Nothing to change", every path as it was')


def u10():
    disks(used='fat32')
    t0 = extents_sha(DISKS/'target.img')
    m = Machine('u10-not-pax', C['sym_new'], C['new'])
    try:
        m.upgrade_entry('U10-not-pax')
        login(m, 'U10-not-pax')
        m.run('pax-install --upgrade')
        s = m.wait(r'^pax-install: upgrade refused: ', 'U10-not-pax', 600, bad=USAGE)
        need(m.unwrapped(s), 'pax-install: upgrade refused: /dev/sdc holds ', 'U10-not-pax')
        need(m.unwrapped(s), 'not a PAX install', 'U10-not-pax')
        m.wait(PROMPT, 'U10-not-pax', 60, last=True)
        s = m.command('[ -e /mnt/target ]; echo t=$?', 'U10-not-pax')
        need(m.unwrapped(s), 't=1', 'U10-not-pax')
        poweroff(m, 'U10-not-pax')
    finally:
        m.kill()
    check_witnesses('U10-not-pax')
    if extents_sha(DISKS/'target.img') != t0:
        fail('U10-not-pax', 'the used disk changed')
    passed('U10-not-pax', 'a listed disk holding an older system (tools/used-disk fat32): nothing mounted, pax-install refused by name (not a PAX install), the disk byte-identical')


def u11():
    disks(size=1073741824)
    install_from(C['old'], C['sym_old'], 'u11-install', 'U11-no-space')
    m = Machine('u11-no-space', C['sym_new'], C['new'])
    try:
        m.upgrade_entry('U11-no-space')
        login(m, 'U11-no-space')
        s = m.command('dd if=/dev/zero of=/mnt/target/home/wolf/fill bs=1048576 count=4000; echo dd=$?', 'U11-no-space', 900)
        m.run('pax-install --upgrade')
        s = m.wait(r'^pax-install: upgrade refused: ', 'U11-no-space', 900, bad=r'^UPGRADE /dev/sdc|' + USAGE)
        need(m.unwrapped(s), "pax-install: upgrade refused: too little space on /dev/sdc's root", 'U11-no-space')
        m.wait(PROMPT, 'U11-no-space', 60, last=True)
        s = m.command('[ -e /mnt/target/etc/pax-install ]; echo p=$?', 'U11-no-space')
        need(m.unwrapped(s), 'p=1', 'U11-no-space')
        poweroff(m, 'U11-no-space')
    finally:
        m.kill()
    check_witnesses('U11-no-space')
    passed('U11-no-space', 'a 1 GiB 860 from the old stick, its root filled by a user file: pax-install refused by name (too little space), /etc/pax-install not made')


U12_OLD = "printf '# px93 U12: an earlier installer wrote this login\\nexec /bin/pelt -i -m\\n' > /mnt/target/etc/pax-login; echo w=$?"
U12_LINE = b'# px93 U12: the user own line\n'


def u12():
    """R-px93-9: a generated file holding the text an earlier installer wrote
    (its manifest's row says so) is the installer's: regenerated, nothing
    beside it. The same file edited by its user is kept, the new text beside
    it as .pax-new; and a third run changes nothing, so the manifest the
    upgrade wrote records the installer's text, not the user's."""
    row = 'U12-installer-text'
    disks()
    install_from(C['new'], C['sym_new'], 'u12-install', row)
    rows, rc, text = tree('u12-installed', row)
    want = rows.get('/etc/pax-login', ('', 0, ''))[2]
    if rc != 0 or not want or '/etc/pax-install/manifest' not in rows:
        fail(row, f'the fresh install: e2fsck -fn exit {rc}, /etc/pax-login {want!r}')
    m = Machine('u12-upgrade', C['sym_new'], C['new'])
    try:
        m.upgrade_entry(row)
        login(m, row)
        # The earlier installer's text, and the install's manifest naming it as the installer's.
        s = m.command(U12_OLD, row)
        need(m.unwrapped(s), 'w=0', row)
        s = m.command("grep -v ' /etc/pax-login$' /mnt/target/etc/pax-install/manifest > /root/m.u12; echo g=$?", row)
        need(m.unwrapped(s), 'g=0', row)
        s = m.command("d=$(sha256sum /mnt/target/etc/pax-login | cut -d' ' -f1); printf 'g 0644 0 0 0 %s /etc/pax-login\\n' \"$d\" >> /root/m.u12; cat /root/m.u12 > /mnt/target/etc/pax-install/manifest; echo m=$?", row)
        need(m.unwrapped(s), 'm=0', row)
        upgrade(m, 'U12-old-text', ['text /etc/pax-login (the installed login: an earlier installer'])
        plan = (work/'U12-old-text-plan.txt').read_text()
        if 'keep /etc/pax-login' in plan or '/etc/pax-login.pax-new' in plan:
            fail(row, 'the earlier installer\'s text was kept as the user\'s:\n' + plan)
        m.wait(PROMPT, row, 60, last=True)
        # The user's edit.
        s = m.command("printf '# px93 U12: the user own line\\n' >> /mnt/target/etc/pax-login; echo e=$?", row)
        need(m.unwrapped(s), 'e=0', row)
        upgrade(m, 'U12-edited', ['keep /etc/pax-login (the installed login: yours kept)', 'text /etc/pax-login.pax-new (the installed login)'])
        m.wait(PROMPT, row, 60, last=True)
        # Once more: nothing to change.
        m.run('pax-install --upgrade')
        m.wait('^' + re.escape('Nothing to change: /dev/sdc already holds this image'), row, 900, bad=r'^UPGRADE /dev/sdc|' + STOPPED)
        m.wait(PROMPT, row, 60, last=True)
        poweroff(m, row)
    finally:
        m.kill()
    check_witnesses(row)
    rows, rc, text = tree('u12-after', row)
    top = work/'u12-after-tree'
    kids = list(top.iterdir())
    top = kids[0] if len(kids) == 1 and not (top/'etc').exists() else top
    login_now = (top/'etc/pax-login').read_bytes()
    beside = (top/'etc/pax-login.pax-new').read_bytes() if (top/'etc/pax-login.pax-new').exists() else b''
    if hashlib.sha256(beside).hexdigest() != want:
        fail(row, f'/etc/pax-login.pax-new is not the installer\'s text: {hashlib.sha256(beside).hexdigest()}')
    if login_now != beside + U12_LINE:
        fail(row, '/etc/pax-login is not the regenerated text with the user\'s line')
    mrow = manifest_rows((top/'etc/pax-install/manifest').read_text()).get('/etc/pax-login')
    if mrow is None or mrow[2] != want:
        fail(row, f'the manifest\'s /etc/pax-login row is not the installer\'s text: {mrow}')
    if rc != 0:
        fail(row, f'e2fsck -fn exit {rc}:\n{text}')
    passed(row, 'an earlier installer\'s /etc/pax-login (the manifest\'s row) regenerated, nothing beside it; the user\'s edit kept with /etc/pax-login.pax-new the new text; a third run "Nothing to change"; the manifest records the installer\'s text; e2fsck -fn clean')


def main():
    sticks()
    if 'U1' in ROWS:
        track_a()
    if 'U1d' in ROWS:
        track_d()
    if any(r in ROWS for r in ('U9', 'U10', 'U11', 'U12')):
        track_x()
    result['leg_seconds'] = round(time.monotonic() - t_leg, 2)
    save()
    print(f'PASS U-all: the upgrade leg ({",".join(ROWS)}) in {result["leg_seconds"]} s', flush=True)


main()
