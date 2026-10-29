#!/usr/bin/env python3
"""px77b: px77a's qualify-smoke.py on two machines, regular image files only.

  a  px77a's machine, its argv unchanged but for the paths, the image and the
     NVMe serial: q35, 2 GiB, OVMF's default GOP, qemu-xhci (no MSI on 8.2.2),
     the PIT present. Ends as px77a's did: `reboot`.
  b  kasumi's shape as px76's F8 draws it, with px77a's disks: no COM1, no PIT
     (pit=off), both xHCIs nec-usb-xhci with msi=on,msix=off (R-px76-5),
     OVMF's 64 GiB window (--high-bar: 8 GiB, opt/ovmf/X-PciMmio64Mb=65536),
     a VGA whose largest mode is 3840x2160 (--display-mode), the SATA disk
     with a serial. Ends at S5: `poweroff` (the image has none: witnessed),
     then `reboot -h`, whose CMD_HALT the debugger turns into CMD_POWER_OFF at
     user.the_end, so the stick's own kernel takes the S5 path (labelled as a
     debugger's change, never as a typed command).
  c  b's machine, the GOP at a mode other than OVMF's default: the stick's
     Limine conf has no `resolution:` and Limine keeps OVMF's 1280x800 even
     when the display offers 3840x2160 (b), so at the menu the harness opens
     Limine's editor (E), adds `resolution: 3840x2160` to the entry for this
     boot only (the image is not changed) and boots it (F10). Ends `reboot`.
  d  b's machine, ended as the photo checklist asks on kasumi: `reboot -h`
     (CMD_HALT, nothing changed by a debugger), the end summary and `halt` left
     on the screen; then QMP `quit`, as a hand on the power button.
No serial port on any; root and every command typed through the USB keyboard
(QMP input events); screens read from PAX's own cells and QEMU's screendump.
"""
from pathlib import Path
import hashlib, json, os, re, select, shutil, socket, struct, subprocess, sys, time, zlib
M = sys.argv[1]
assert M in ('a', 'b', 'c', 'd'), M
L = Path('/home/mfwolffe/lanes/px77b'); O = L/f'qualify-{M}'; O.mkdir(exist_ok=False)
IMG = L/'out/pax-stick-101e7761.img'
assert IMG.is_file()

def log(s): print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), M, s, flush=True)
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def disk(name, tag):
    p = O/name
    # Fully materialized, nonzero known content, distinct per disk. No sparse holes.
    block = hashlib.shake_256(tag).digest(1048576)
    with p.open('wb') as f:
        for _ in range(2048): f.write(block)
        f.flush(); os.fsync(f.fileno())
    assert p.stat().st_size == 2*1024**3
    return p
nv = disk('nvme.img', b'px77b NVMe known content v1')
sa = disk('sata.img', b'px77b SATA known content v1')
before = {p.name: sha(p) for p in (nv, sa)}
(O/'before.json').write_text(json.dumps(before, indent=2)+'\n'); log('before '+json.dumps(before))
code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd'); var = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
assert code.is_file() and var.is_file()
shutil.copyfile(var, O/'vars.fd')
symbols = {p[2]: int(p[0], 16) for line in (L/'out/kernel.symbols').read_text().splitlines() if len(p := line.split()) == 3}
def sym(prefix):
    hits = [v for k, v in symbols.items() if k.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]

if M == 'a':
    cmd = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', '2048M', '-accel', 'tcg',
           '-display', 'none', '-serial', 'none', '-parallel', 'none', '-nic', 'none', '-no-reboot',
           '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
           '-drive', f'if=pflash,format=raw,unit=1,file={O}/vars.fd',
           '-device', 'qemu-xhci,id=xhci',
           '-drive', f'file={IMG},if=none,id=stick,format=raw,readonly=on',
           '-device', 'usb-storage,bus=xhci.0,drive=stick,bootindex=0',
           '-device', 'qemu-xhci,id=pax-usb', '-device', 'usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1',
           '-drive', f'file={nv},if=none,id=nv,format=raw', '-device', 'nvme,serial=px77b-nvme,drive=nv',
           '-drive', f'file={sa},if=none,id=sa,format=raw', '-device', 'ide-hd,bus=ide.0,drive=sa']
else:  # b and c: one machine
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
           '-device', 'usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1',
           '-drive', f'file={nv},if=none,id=nv,format=raw', '-device', 'nvme,serial=px77b-nvme,drive=nv',
           '-drive', f'file={sa},if=none,id=sa,format=raw', '-device', 'ide-hd,bus=ide.0,drive=sa,serial=px77b-sata',
           '-fw_cfg', 'name=opt/ovmf/X-PciMmio64Mb,string=65536']
cmd += ['-qmp', f'unix:{O}/qmp.sock,server=on,wait=off', '-gdb', f'unix:{O}/gdb.sock,server=on,wait=off', '-S']
(O/'command.json').write_text(json.dumps(cmd, indent=2)+'\n')
(O/'versions.txt').write_text(subprocess.check_output([cmd[0], '--version'], text=True) +
    subprocess.check_output(['sha256sum', str(code), str(var)], text=True) +
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
def wait_text(needle, name, timeout=180):
    start = time.monotonic()
    while time.monotonic()-start < timeout:
        if proc.poll() is not None: raise RuntimeError('QEMU exited before '+name)
        text, state = screen()
        if re.search(needle, text):
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
# QEMU 8.2's stub sends a stop reply only after the client's own resume, so
# after a QMP `cont` a breakpoint is seen as the run state `debug` instead.
def wait_debug(timeout):
    start = time.monotonic()
    while time.monotonic()-start < timeout:
        if proc.poll() is not None: raise RuntimeError(f'QEMU exited ({proc.returncode}) before the breakpoint')
        if q.call('query-status')['status'] == 'debug': return
        time.sleep(.1)
    raise RuntimeError('breakpoint not reached')
def rip():
    m = re.search(r'RIP=([0-9a-f]{16})', q.hmp('info registers')); assert m
    return int(m[1], 16)
def bottom_green(ppm):
    # Limine's countdown line ("Booting automatically in N...") is green, at the
    # screen's foot; OVMF's screens have nothing green there.
    w, h, raw = ppm_raw(ppm)
    for y in range(h-60, h-8, 2):
        row = raw[y*w*3:(y+1)*w*3]
        for x in range(0, w*3, 6):
            if row[x+1] > 150 and row[x] < 80 and row[x+2] < 80: return True
    return False
rc = 1; result = {'machine': M}
try:
    for _ in range(100):
        if (O/'qmp.sock').exists() and (O/'gdb.sock').exists(): break
        if proc.poll() is not None: raise RuntimeError('QEMU launch failed')
        time.sleep(.1)
    q = QMP(); g = socket.socket(socket.AF_UNIX); g.connect(str(O/'gdb.sock')); g.settimeout(300)
    user_entry = symbols['pax_user_thread']
    assert rsp_call(f'Z1,{user_entry:x},1') == 'OK'
    if M == 'b':
        the_end = sym('_Wuser.the_end$'); end_cmd = sym('_Wuser.end_cmd.')
        assert rsp_call(f'Z1,{the_end:x},1') == 'OK'
    rsp_send('c'); log('UEFI starts; sample the screen until first user entry')
    last = ''; kept = []; start = time.monotonic(); n = 0; edited = False
    while time.monotonic()-start < 900:
        if select.select([g], [], [], 0)[0]:
            peek = g.recv(1, socket.MSG_PEEK)
            if peek == b'+': g.recv(1); continue
            elif peek == b'$': break
        p = O/f'frame-{n:04}.ppm'; n += 1
        q.call('screendump', {'filename': str(p)})
        if M == 'c' and not edited and bottom_green(p):
            edited = True
            log('Limine menu seen; E opens the editor')
            key('e', True); time.sleep(.05); key('e', False); time.sleep(1.5)
            shot('editor-0.png')
            # The editor opens at the entry's first line (protocol:); its third is
            # module_path:. A new line after it, unindented (an indented key is
            # drawn red, unrecognised: the first attempt, qualify-c-run1).
            for k in ['down', 'down', 'end', 'ret']:
                key(k, True); time.sleep(.05); key(k, False); time.sleep(.1)
            type_text('resolution: 3840x2160'); time.sleep(.5)
            shot('editor-1.png')
            log('F10 boots the edited entry'); key('f10', True); time.sleep(.05); key('f10', False)
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != last and len(kept) < 48: kept.append((p.name, round(time.monotonic()-start, 2))); last = h
        else:
            last = h; p.unlink()
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
    (O/'boot-line-count.txt').write_text(
        f'{state[30]+login} = scroll count {state[30]} + visible rows {login} at {state[5]}x{state[6]} cells (scale {state[67]}); '
        f'{state[51]} early bytes replayed at attach; transcript: '
        + (f'{tlogin} newline-terminated lines before login:\n' if tlogin is not None else 'no login: line in the kernel transcript\n'))
    log((O/'boot-line-count.txt').read_text().strip())
    type_text('root\n'); wait_text(r'(?m)^.*[$#] *$', 'root-shell')
    commands = ['uname -a', 'cat /etc/pax-release', 'ls /dev', 'pax-install --inventory']
    if M == 'b': commands.append('poweroff')
    if M == 'c': assert re.search(r'^screen: 3840x2160 ', t, re.M), 'the edited entry did not give 3840x2160'

    transcript_rows = []
    for i, c in enumerate(commands, 1):
        log('USB keyboard '+c); type_text(c+'\n'); time.sleep(1)
        text, state = wait_text(r'(?m)^.*[$#] *$', f'command-{i}')
        transcript_rows.append('COMMAND '+c+'\n'+text)
        if c == 'ls /dev': shot('04-after-commands.png')
        if c == 'pax-install --inventory':
            shot('05-disk-listing.png')
            assert 'nvme0n1' in text, 'inventory must see NVMe'
            assert '/dev/sda' in text, 'inventory must see the SATA disk'
    (O/'transcript.txt').write_text('\n'.join(transcript_rows))
    transcript('after-commands')
    if M in ('a', 'c'):
        log('USB keyboard reboot'); type_text('reboot\n')
        proc.wait(timeout=120); assert proc.returncode == 0, proc.returncode
        log('QEMU ended through reboot, exit 0'); result['end'] = 'reboot: QEMU exit 0 (-no-reboot)'
    elif M == 'd':
        log('USB keyboard reboot -h (CMD_HALT), no debugger change'); type_text('reboot -h\n')
        wait_text(r'(?m)^halt$', '07-halt', 120)
        shot('07-halt.png'); transcript('07-halt')
        time.sleep(5); text2, _ = screen()
        assert text2 == (O/'07-halt.txt').read_text(), 'the halted screen changed'
        st = q.call('query-status')['status']; log('run state after halt: '+st)
        q.call('quit'); proc.wait(timeout=60)
        log(f'QEMU quit by QMP (the power button), exit {proc.returncode}')
        result['end'] = f'reboot -h: halt line, screen unchanged 5 s later, run state {st}; QMP quit, QEMU exit {proc.returncode}'
    else:
        log('USB keyboard reboot -h (CMD_HALT)'); type_text('reboot -h\n')
        wait_debug(300); at = rip()
        assert at == the_end, (hex(at), hex(the_end))
        r = q.hmp(f'memsave 0x{end_cmd:x} 8 "{O}/end_cmd.bin"'); assert not r, r
        asked = int.from_bytes((O/'end_cmd.bin').read_bytes(), 'little')
        assert asked == 0xcdef0123, hex(asked)
        log(f'user.the_end reached; end_cmd {asked:#x} (CMD_HALT, typed); the debugger writes CMD_POWER_OFF')
        assert rsp_call(f'M{end_cmd:x},8:' + (0x4321fedc).to_bytes(8, 'little').hex()) == 'OK'
        r = q.hmp(f'memsave 0x{end_cmd:x} 8 "{O}/end_cmd.bin"'); assert not r, r
        assert int.from_bytes((O/'end_cmd.bin').read_bytes(), 'little') == 0x4321fedc
        assert rsp_call(f'z1,{the_end:x},1') == 'OK'
        # kernel/power alone calls pax_outw (boot/io.S): its first call is the PM1a
        # write of SLP_TYP|SLP_EN, after the `poweroff: ACPI S5 types` line.
        outw = symbols['pax_outw']
        assert rsp_call(f'Z1,{outw:x},1') == 'OK'
        q.call('cont'); wait_debug(300); at = rip()
        assert at == outw, (hex(at), hex(outw))
        shot('06-poweroff.png'); screen('06-poweroff', resume=False); transcript('06-poweroff', resume=False)
        assert rsp_call(f'z1,{outw:x},1') == 'OK'
        log('resuming at pax_outw: the PM1a write of SLP_TYP|SLP_EN')
        q.call('cont')
        proc.wait(timeout=120); assert proc.returncode == 0, proc.returncode
        log('QEMU ended at S5, exit 0'); result['end'] = 'S5: QEMU exit 0 (end_cmd CMD_HALT typed, CMD_POWER_OFF written by the debugger at user.the_end)'
    rc = 0
finally:
    if proc.poll() is None:
        try: shot('failure.png')
        except Exception as e: log('no failure screen: '+repr(e))
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    qlog.close()
    after = {p.name: sha(p) for p in (nv, sa)}
    (O/'after.json').write_text(json.dumps(after, indent=2)+'\n'); log('after '+json.dumps(after))
    if before != after:
        (O/'STOP-DISK-CHANGED').write_text('DO NOT STAGE\n'); raise RuntimeError('STOP disk image changed')
    log('PASS both writable 2 GiB disks unchanged')
    result.update({'exit': rc, 'qemu_exit': proc.returncode, 'no_write': True, 'before': before, 'after': after})
    (O/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    # The kept frames stay PPM here; frames.py converts them once block A is released.
if rc: raise SystemExit(rc)
