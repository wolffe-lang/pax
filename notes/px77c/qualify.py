#!/usr/bin/env python3
"""px77c: px77b's qualify.py on the install stick and, for the spelling, on px77b's smoke stick.

  qualify.py MACHINE

Machines (every one: OVMF with a fresh variable store, -serial none, TCG, the
stick read-only as usb-storage, the USB keyboard on an xHCI of its own, root
and every command typed through it by QMP key events, screens read from PAX's
own exported cells, the kernel's in-memory transcript read at the login):

  s-old, s-new  the spelling machine (the coordinator's addition): px77b's
     machine a (q35, 2 GiB, qemu-xhci) with four SATA disks on q35's AHCI,
     each a model and serial chosen to show how the two inventories spell
     them: a model longer than 16 bytes cut at a space, one under 16, one
     cut inside a word, a serial of all 20 bytes and one with leading
     spaces. s-old boots 101e7761's smoke stick (px77b's, as staged),
     s-new this lane's install stick. `pax-install --inventory` on both,
     `pax-install --check` on the new one.
  b-old, b-new  kasumi's shape tonight (the maintainer, 2026-10-29: every
     drive out but the target SATA SSD): px76's F8 machine (q35,pit=off,
     8 GiB, both xHCIs nec-usb-xhci msi=on,msix=off, BARs above 4 GiB, a
     VGA offering 3840x2160) with ONE SATA disk, 2 GiB of known content,
     model "Samsung SSD 870 EVO 500GB". b-old is the photo the maintainer
     takes tonight; b-new is the install stick's first boot before its line
     is written. b-new ends `reboot -p` (px78): ACPI S5, QEMU exit 0, no
     debugger; b-old ends as px77b's checklist asks (`reboot -h`, the halt
     summary, QMP quit as the power button).
  c-new  b-new's machine with Limine's editor adding `resolution: 3840x2160`
     for that boot only (px77b's c): the 4K GOP, glyphs at 2x. Ends `reboot`.

Every writable disk is hashed over every byte before QEMU starts and after
it ends: identical, or STOP.
"""
from pathlib import Path
import hashlib, json, os, re, select, shutil, socket, struct, subprocess, sys, time, zlib
M = sys.argv[1]
assert M in ('s-old', 's-new', 'b-old', 'b-new', 'c-new'), M
L = Path('/home/mfwolffe/lanes/px77c'); O = L/f'qualify-{M}'; O.mkdir(exist_ok=False)
NEW = M.endswith('-new')
IMG = L/'out/pax-install-56b9f554.img' if NEW else L/'old/pax-stick-101e7761.img'
SYMS = L/'out/kernel.symbols' if NEW else L/'old/kernel.symbols'
assert IMG.is_file() and SYMS.is_file()

def log(s): print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), M, s, flush=True)
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def disk(name, tag, mib):
    p = O/name
    # Fully materialized, nonzero known content, distinct per disk. No sparse holes.
    block = hashlib.shake_256(tag).digest(1048576)
    with p.open('wb') as f:
        for _ in range(mib): f.write(block)
        f.flush(); os.fsync(f.fileno())
    assert p.stat().st_size == mib*1024**2
    return p

# The disks: (file, model, serial). QEMU's ide-hd takes model up to 40
# bytes and serial up to 20, space-padded on the right as ATA's IDENTIFY
# strings are; a leading space is kept as given.
TARGET = ('Samsung SSD 870 EVO 500GB', 'S6PXNM0T612345A')
if M.startswith('s-'):
    SATA = [('Samsung SSD 870 EVO 500GB', 'S6PXNM0T612345A'),
            ('CT500MX500SSD1', 'ABCDEFGHIJ0123456789'),
            ('WDC WDS500G2B0A-00SM50', '   21021X801234'),
            ('SanDisk SDSSDH3 512G', '2104AB401234')]
    disks = [disk(f'sata{k}.img', f'px77c {M[0]} SATA {k} v1'.encode(), 64) for k in range(len(SATA))]
else:
    SATA = [TARGET]
    disks = [disk('sata0.img', b'px77c kasumi target known content v1', 2048)]
before = {p.name: sha(p) for p in disks}
(O/'before.json').write_text(json.dumps(before, indent=2)+'\n'); log('before '+json.dumps(before))
code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd'); var = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
assert code.is_file() and var.is_file()
shutil.copyfile(var, O/'vars.fd')
symbols = {p[2]: int(p[0], 16) for line in SYMS.read_text().splitlines() if len(p := line.split()) == 3}
sata_args = []
for k, ((model, serial), img) in enumerate(zip(SATA, disks)):
    sata_args += ['-drive', f'file={img},if=none,id=sa{k},format=raw',
                  '-device', f'ide-hd,bus=ide.{k},drive=sa{k},model={model},serial={serial}']

if M.startswith('s-'):
    cmd = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', '2048M', '-accel', 'tcg',
           '-display', 'none', '-serial', 'none', '-parallel', 'none', '-nic', 'none', '-no-reboot',
           '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
           '-drive', f'if=pflash,format=raw,unit=1,file={O}/vars.fd',
           '-device', 'qemu-xhci,id=xhci',
           '-drive', f'file={IMG},if=none,id=stick,format=raw,readonly=on',
           '-device', 'usb-storage,bus=xhci.0,drive=stick,bootindex=0',
           '-device', 'qemu-xhci,id=pax-usb', '-device', 'usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1'] + sata_args
else:  # b and c: kasumi's shape, its one SATA disk
    props = subprocess.run(['qemu-system-x86_64', '-device', 'nec-usb-xhci,help'], capture_output=True, text=True).stdout
    assert re.search(r'^\s+msi=', props, re.M) and re.search(r'^\s+msix=', props, re.M), props
    cmd = ['qemu-system-x86_64', '-machine', 'q35,pit=off', '-cpu', 'max', '-m', '8G', '-accel', 'tcg',
           '-display', 'none', '-vga', 'none', '-device', 'VGA,vgamem_mb=64,xres=3840,yres=2160',
           '-serial', 'none', '-parallel', 'none', '-nic', 'none', '-no-reboot',
           '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
           '-drive', f'if=pflash,format=raw,unit=1,file={O}/vars.fd',
           '-device', 'nec-usb-xhci,id=xhci,msi=on,msix=off',
           '-drive', f'file={IMG},if=none,id=stick,format=raw,readonly=on',
           '-device', 'usb-storage,bus=xhci.0,drive=stick,bootindex=0',
           '-device', 'nec-usb-xhci,id=pax-usb,msi=on,msix=off',
           '-device', 'usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1'] + sata_args + [
           '-fw_cfg', 'name=opt/ovmf/X-PciMmio64Mb,string=65536']
cmd += ['-qmp', f'unix:{O}/qmp.sock,server=on,wait=off', '-gdb', f'unix:{O}/gdb.sock,server=on,wait=off', '-S']
(O/'command.json').write_text(json.dumps(cmd, indent=2)+'\n')
(O/'versions.txt').write_text(subprocess.check_output([cmd[0], '--version'], text=True) +
    subprocess.check_output(['sha256sum', str(code), str(var), str(IMG)], text=True) +
    subprocess.check_output(['taskset', '-pc', str(os.getpid())], text=True))
qlog = (O/'qemu.log').open('wb'); proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=qlog, stderr=subprocess.STDOUT)
(O/'qemu.pid').write_text(str(proc.pid)+'\n')
class QMP:
    def __init__(self):
        self.s = socket.socket(socket.AF_UNIX); self.s.connect(str(O/'qmp.sock')); self.f = self.s.makefile('rb'); self.f.readline(); self.i = 0; self.call('qmp_capabilities')
    def call(self, name, args=None):
        self.i += 1; ident = self.i
        self.s.sendall((json.dumps({'execute': name, 'arguments': args or {}, 'id': ident})+'\n').encode())
        while True:
            r = json.loads(self.f.readline())
            if r.get('id') == ident:
                if 'error' in r: raise RuntimeError(r)
                return r.get('return')
    def hmp(self, s): return self.call('human-monitor-command', {'command-line': s})
def ppm_raw(ppm):
    data = ppm.read_bytes(); match = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data); assert match
    w, h = map(int, match.groups()); raw = data[match.end():]; assert len(raw) == w*h*3
    return w, h, raw
def png(ppm, dest):
    # QEMU P6 PPM to truecolor PNG, no external decoder or synthetic screen.
    w, h, raw = ppm_raw(ppm)
    def chunk(k, b): return struct.pack('>I', len(b))+k+b+struct.pack('>I', zlib.crc32(k+b))
    filtered = b''.join(b'\0'+raw[y*w*3:(y+1)*w*3] for y in range(h))
    dest.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(filtered, 6))+chunk(b'IEND', b''))
    return w, h, hashlib.sha256(raw).hexdigest()
def shot(name):
    p = O/'screen.ppm'; q.call('screendump', {'filename': str(p)}); w, h, d = png(p, O/name)
    log(f'screendump {name} {w}x{h} pixels-sha256 {d}'); return d
STATE_WORDS = 69
def screen(name=None, resume=True):
    # Read PAX's own exported terminal state/cells, not UART output.
    q.call('stop')
    a = symbols['pax_screen_state']; b = symbols['pax_screen_cells']
    r = q.hmp(f'memsave 0x{a:x} {STATE_WORDS*8} "{O}/state.bin"'); assert not r, r
    state = struct.unpack(f'<{STATE_WORDS}Q', (O/'state.bin').read_bytes())
    cols, rows = state[5:7]
    if not (state[0] and 1 <= cols <= 256 and 1 <= rows <= 128):
        if resume: q.call('cont')
        return '', state
    offset = (256*128*4 if state[60] else 0)
    r = q.hmp(f'memsave 0x{b+offset:x} {cols*rows*4} "{O}/cells.bin"'); assert not r, r
    cells = struct.unpack('<'+str(cols*rows)+'I', (O/'cells.bin').read_bytes())
    text = '\n'.join(''.join(chr(v & 255) if 32 <= v & 255 < 127 else ' ' for v in cells[y*cols:(y+1)*cols]).rstrip() for y in range(rows)).rstrip()+'\n'
    if name:
        (O/(name+'.txt')).write_text(text); (O/(name+'.state.json')).write_text(json.dumps(list(state))+'\n')
    if resume: q.call('cont')
    return text, state
def transcript(name, resume=True):
    # px76: the bounded in-memory transcript a UART-less kernel keeps (boot/io.S).
    q.call('stop')
    r = q.hmp(f'memsave 0x{symbols["pax_serial_log_count"]:x} 8 "{O}/count.bin"'); assert not r, r
    n = int.from_bytes((O/'count.bin').read_bytes(), 'little')
    data = b''
    if n:
        r = q.hmp(f'memsave 0x{symbols["pax_serial_log"]:x} {min(n, 65536)} "{O}/log.bin"'); assert not r, r
        data = (O/'log.bin').read_bytes()
    if resume: q.call('cont')
    (O/(name+'.transcript.log')).write_bytes(data)
    log(f'transcript {name}: {n} bytes counted{" (OVERFLOW: 64 KiB kept)" if n > 65536 else ""}')
    return data.decode('latin-1')
def wait_text(needle, name, timeout=180, last=False):
    # last: the needle is held to the screen's last line only (a fresh prompt
    # after a command's output, never the line the command was typed on).
    start = time.monotonic(); text = ''
    while time.monotonic()-start < timeout:
        if proc.poll() is not None: raise RuntimeError('QEMU exited before '+name)
        text, state = screen()
        look = text.rstrip('\n').split('\n')[-1] if last else text
        if re.search(needle, look):
            (O/(name+'.txt')).write_text(text); (O/(name+'.state.json')).write_text(json.dumps(list(state))+'\n'); return text, state
        time.sleep(.25)
    shot('failure.png'); raise RuntimeError('timeout waiting for '+name+'; '+text)
def key(k, down): q.call('input-send-event', {'events': [{'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': k}}}]})
def type_text(s):
    codes = {' ': 'spc', '-': 'minus', '/': 'slash', '.': 'dot', '=': 'equal', '\n': 'ret', ';': 'semicolon', ':': 'semicolon', '$': '4', '\'': 'apostrophe', '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'}
    for c in s:
        shift = c in ':$' or c.isupper()
        k = codes.get(c, c.lower())
        if shift: key('shift', True)
        key(k, True); time.sleep(.025); key(k, False)
        if shift: key('shift', False)
        time.sleep(.025)
# GDB remote protocol: QMP stop/cont make the stub send T02 stop replies, so
# every read skips stop replies that are not the one waited for.
def rsp_send(s):
    b = s.encode(); g.sendall(b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode())
def rsp_packet():
    while g.recv(1) != b'$': pass
    data = b''
    while (c := g.recv(1)) != b'#': data += c
    g.recv(2); g.sendall(b'+'); return data.decode()
def rsp_call(s):
    rsp_send(s)
    while True:
        r = rsp_packet()
        if not re.match(r'^[TS][0-9a-f]{2}', r): return r
def bottom_green(ppm):
    # Limine's countdown line ("Booting automatically in N...") is green, at the
    # screen's foot; OVMF's screens have nothing green there.
    w, h, raw = ppm_raw(ppm)
    for y in range(h-60, h-8, 2):
        row = raw[y*w*3:(y+1)*w*3]
        for x in range(0, w*3, 6):
            if row[x+1] > 150 and row[x] < 80 and row[x+2] < 80: return True
    return False
PROMPT = r'^.*[$#] *$'
rc = 1; result = {'machine': M, 'image': str(IMG), 'sata': SATA}
try:
    for _ in range(100):
        if (O/'qmp.sock').exists() and (O/'gdb.sock').exists(): break
        if proc.poll() is not None: raise RuntimeError('QEMU launch failed')
        time.sleep(.1)
    q = QMP(); g = socket.socket(socket.AF_UNIX); g.connect(str(O/'gdb.sock')); g.settimeout(300)
    user_entry = symbols['pax_user_thread']
    assert rsp_call(f'Z1,{user_entry:x},1') == 'OK'
    rsp_send('c'); log('UEFI starts; sample the screen until first user entry')
    last = ''; kept = []; start = time.monotonic(); n = 0; edited = False
    while time.monotonic()-start < 900:
        if select.select([g], [], [], 0)[0]:
            peek = g.recv(1, socket.MSG_PEEK)
            if peek == b'+': g.recv(1); continue
            elif peek == b'$': break
        p = O/f'frame-{n:04}.ppm'; n += 1
        q.call('screendump', {'filename': str(p)})
        if M == 'c-new' and not edited and bottom_green(p):
            edited = True
            log('Limine menu seen; E opens the editor')
            key('e', True); time.sleep(.05); key('e', False); time.sleep(1.5)
            shot('editor-0.png')
            # The editor opens at the entry's first line (protocol:); its third is
            # module_path:. A new line after it, unindented (px77b's c-run1).
            for k in ['down', 'down', 'end', 'ret']:
                key(k, True); time.sleep(.05); key(k, False); time.sleep(.1)
            type_text('resolution: 3840x2160'); time.sleep(.5)
            shot('editor-1.png')
            log('F10 boots the edited entry'); key('f10', True); time.sleep(.05); key('f10', False)
            continue
        # px77c keeps no frames (px77b kept 48 per boot for its video stand-in):
        # each sample is read for Limine's menu and dropped.
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != last: kept.append((p.name, round(time.monotonic()-start, 2))); last = h
        p.unlink()
        time.sleep(.2)
    else: raise RuntimeError('first user entry not reached')
    stop = rsp_packet(); assert stop.startswith('T05') or stop.startswith('S05'), stop
    log('first user entry stopped '+stop)
    (O/'frames.json').write_text(json.dumps(kept)+'\n')
    shot('02-last-boot-line.png')
    assert rsp_call(f'z1,{user_entry:x},1') == 'OK'
    text, state = screen('02-last-boot-line')
    transcript('02-last-boot-line')
    text, state = wait_text(r'(?m)^login: *$', '03-login', 600)
    shot('03-login.png')
    t = transcript('03-login')
    lines = text.splitlines(); login = next(i for i, l in enumerate(lines) if l.startswith('login:'))
    tl = t.replace('\r', '').split('\n')
    tlogin = next((i for i, l in enumerate(tl) if l.startswith('login:')), None)
    result['screen'] = {'cols': state[5], 'rows': state[6], 'scale': state[67], 'scrolls': state[30], 'login_row': login, 'replayed': state[51]}
    result['transcript_lines_before_login'] = tlogin
    result['boot_identity_lines'] = [l for l in tl if re.search(r'ahci\d: .* model "', l)]
    (O/'boot-line-count.txt').write_text(
        f'{state[30]+login} = scroll count {state[30]} + visible rows {login} at {state[5]}x{state[6]} cells (scale {state[67]}); '
        f'{state[51]} early bytes replayed at attach; transcript: '
        + (f'{tlogin} newline-terminated lines before login:\n' if tlogin is not None else 'no login: line in the kernel transcript\n'))
    log((O/'boot-line-count.txt').read_text().strip())
    if M == 'c-new': assert re.search(r'^screen: 3840x2160 ', t, re.M), 'the edited entry did not give 3840x2160'
    type_text('root\n'); wait_text(PROMPT, 'root-shell', last=True)
    if M.startswith('s-'):
        commands = ['pax-install --inventory'] + (['pax-install --check'] if NEW else [])
    else:
        commands = ['uname -a', 'cat /etc/pax-release', 'ls /dev', 'pax-install --inventory'] + (['pax-install --check'] if NEW else [])
    transcript_rows = []
    for i, c in enumerate(commands, 1):
        log('USB keyboard '+c); type_text(c+'\n'); time.sleep(1)
        text, state = wait_text(PROMPT, f'command-{i}', 300, last=True)
        transcript_rows.append('COMMAND '+c+'\n'+text)
        if c == 'ls /dev': shot('04-after-commands.png')
        if c == 'pax-install --inventory':
            shot('05-disk-listing.png')
            for model, serial in SATA:
                shown = model[:16].rstrip() if NEW else model
                want = f'model={shown} serial={serial.strip()}'
                assert want in text, f'inventory: missing {want!r}'
            result.setdefault('inventory_lines', [l.strip() for l in text.splitlines() if l.strip().startswith('model=')])
        if c == 'pax-install --check':
            shot('06-check.png')
            result['check_lines'] = [l.rstrip() for l in text.splitlines() if 'refused' in l or 'allow-list' in l or l.startswith('/dev/')]
    (O/'transcript.txt').write_text('\n'.join(transcript_rows))
    transcript('after-commands')
    if M in ('s-old', 'c-new'):
        log('USB keyboard reboot'); type_text('reboot\n')
        proc.wait(timeout=180); assert proc.returncode == 0, proc.returncode
        log('QEMU ended through reboot, exit 0'); result['end'] = 'reboot: QEMU exit 0 (-no-reboot)'
    elif M == 'b-old':
        log('USB keyboard reboot -h (CMD_HALT), the smoke checklist\'s end'); type_text('reboot -h\n')
        wait_text(r'(?m)^halt$', '07-halt', 180)
        shot('07-halt.png'); transcript('07-halt')
        time.sleep(5); text2, _ = screen()
        assert text2 == (O/'07-halt.txt').read_text(), 'the halted screen changed'
        st = q.call('query-status')['status']; log('run state after halt: '+st)
        q.call('quit'); proc.wait(timeout=60)
        log(f'QEMU quit by QMP (the power button), exit {proc.returncode}')
        result['end'] = f'reboot -h: halt line, screen unchanged 5 s later, run state {st}; QMP quit, QEMU exit {proc.returncode}'
    else:
        # px78's `reboot -p`: reboot(2) asked for POWER_OFF; the kernel's S5
        # ends QEMU with exit 0. The screen is sampled until QEMU is gone and
        # the last one kept: the end summary the maintainer will see.
        log('USB keyboard reboot -p (POWER_OFF, px78)'); type_text('reboot -p\n')
        seen = ''
        end = time.monotonic() + 180
        while proc.poll() is None and time.monotonic() < end:
            try:
                s, _ = screen()
                if s: seen = s
            except Exception:
                break
            time.sleep(.2)
        proc.wait(timeout=60); assert proc.returncode == 0, proc.returncode
        (O/'07-poweroff-last-screen.txt').write_text(seen)
        log('QEMU ended at S5 through reboot -p, exit 0'); result['end'] = 'reboot -p: ACPI S5, QEMU exit 0 (no debugger)'
    rc = 0
finally:
    if proc.poll() is None:
        try: shot('failure.png')
        except Exception as e: log('no failure screen: '+repr(e))
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    qlog.close()
    after = {p.name: sha(p) for p in disks}
    (O/'after.json').write_text(json.dumps(after, indent=2)+'\n'); log('after '+json.dumps(after))
    if before != after:
        (O/'STOP-DISK-CHANGED').write_text('DO NOT STAGE\n'); raise RuntimeError('STOP disk image changed')
    log('PASS every writable disk unchanged')
    result.update({'exit': rc, 'qemu_exit': proc.returncode, 'no_write': True, 'before': before, 'after': after})
    (O/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    for p in disks: p.unlink()
if rc: raise SystemExit(rc)
