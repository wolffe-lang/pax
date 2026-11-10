"""tests/mpx6-bootlog.d/rows.py — px118's rows (tests/mpx6-bootlog's header has each).

    rows.py WORK KERNEL.elf FIRMWARE...

The archives are tools/mkinitramfs's, their first program tests/mpx6-bootlog.d/init.c (built static
here: it prints /proc/pax-boot and /proc/pax-bootlog between marker lines and exits, or restarts by
reboot(2) where asked); the images are tools/mkimage's ISOs and tools/mkdisk's installed-shape disks
(the ESP's limine.conf rewritten between boots with mtools, a black box). One QEMU process boots an
image several times: a boot ends at the kernel's `halt` (or its `pax.bootstop` stop), then the
monitor's `system_reset` starts the next, so CMOS and memory carry over as they do across a reset
button. PX118_ROWS (letters, default `B M S R L N U P`) picks the groups. Prints PASS/FAIL lines at
column 0; exits 1 when any row failed."""
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

WORK, KERNEL = Path(sys.argv[1]), Path(sys.argv[2])
LEGS = sys.argv[3:]
ROOT = Path(__file__).resolve().parents[2]
OVMF_CODE = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
OVMF_VARS = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
PIT_HZ = 1193182
HIGH, LOW = PIT_HZ / 1140, PIT_HZ / 2280  # kmain_console's BEEP_HIGH and BEEP_LOW counts
BASE = 0x78  # kernel/bootmark's BASE: the marks' eight CMOS bytes
CMOS = '0x78-0x7f'
STAGES = ['entered', 'drawn', 'memory', 'framebuffer', 'devices', 'root', 'init', 'end']
EPOCH = '1794269606'
bad = False


def say(s):
    print(s, flush=True)


def fail(row, why):
    global bad
    bad = True
    say(f'FAIL {row}: {why}')


def run(argv, **kw):
    r = subprocess.run([str(x) for x in argv], capture_output=True, **kw)
    if r.returncode:
        raise RuntimeError(f'{argv[:2]}: exit {r.returncode}: {r.stderr.decode(errors="replace")[-400:]}')
    return r


def archive_record(name, prog):
    """The archive whose run list is `pax-boot-status record` (pid 1, as /bin/login runs it on an
    installed system), then `pax-boot-status` (the show), then init.c."""
    a = WORK / 'in'
    a.mkdir(exist_ok=True)
    (a / 'pax-run-record').write_text('/bin/pax-boot-status record\n/bin/pax-boot-status\n/bin/init\n')
    out = WORK / f'{name}.cpio'
    run([ROOT / 'tools/mkinitramfs', out, '/dev/', '/proc/', '/sys/', '/tmp/:1777', '/var/', '/var/log/',
         f'/bin/init={a / "init"}', f'/bin/pax-boot-status={prog}', f'/etc/pax-run={a / "pax-run-record"}',
         f'/etc/fstab={a / "fstab-root"}'])
    return out


def archive(name, reboot=False):
    a = WORK / 'in'
    a.mkdir(exist_ok=True)
    init = a / 'init'
    if not init.exists():
        run(['cc', '-static', '-nostdlib', '-ffreestanding', '-fno-pie', '-no-pie', '-fno-stack-protector', '-O1',
             '-o', init, Path(__file__).resolve().parent / 'init.c'])
    (a / 'pax-run').write_text('/bin/init\n')
    (a / 'fstab-root').write_text('/dev/vda2 / ext2 rw 0 1\ntmpfs /tmp tmpfs nosuid,nodev 0 0\n')
    (a / 'reboot').write_text('restart once\n')
    out = WORK / f'{name}.cpio'
    extra = [f'/etc/px118-reboot={a / "reboot"}'] if reboot else []
    run([ROOT / 'tools/mkinitramfs', out, '/dev/', '/proc/', '/sys/', '/tmp/:1777', '/var/', '/var/log/',
         f'/bin/init={init}', f'/etc/pax-run={a / "pax-run"}', f'/etc/fstab={a / "fstab-root"}', *extra])
    return out


def conf_text(cmdline, head='timeout: 0\nquiet: yes\n', module=True):
    return (head + '\n/PAX\n    protocol: limine\n    path: boot():/boot/pax\n'
            + ('    module_path: boot():/boot/initramfs.cpio\n' if module else '')
            + (f'    cmdline: {cmdline}\n' if cmdline else ''))


def iso(name, cpio, cmdline):
    conf = WORK / f'{name}.conf'
    conf.write_text(conf_text(cmdline))
    out = WORK / f'{name}.iso'
    run([ROOT / 'tools/mkimage', '--conf', conf, '--add', cpio, 'initramfs.cpio', KERNEL, out])
    return out


def disk(name, cpio, cmdline, head='timeout: 0\nquiet: yes\n'):
    """An installed-shape disk: Limine and the kernel on the ESP, the archive as an ext2 root on
    partition 2 (tools/mkdisk adds `root=PARTUUID=… rw` to the entry's command line)."""
    conf = WORK / f'{name}.conf'
    conf.write_text(conf_text(cmdline or 'px118', head, module=False))
    img = WORK / f'{name}.img'
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)
    r = subprocess.run([str(ROOT / 'tools/mkdisk'), '--gpt', '--no-journal', '--kernel', str(KERNEL), '--root', str(cpio),
                        '--conf', str(conf), '--label', 'pax-root', '96M', str(img)], capture_output=True, env=env)
    if r.returncode:
        raise RuntimeError('tools/mkdisk: ' + r.stderr.decode(errors='replace')[-600:])
    return img


def part_offset(img, i):
    with open(img, 'rb') as f:
        f.seek(512)
        h = f.read(92)
        lba, size = int.from_bytes(h[72:80], 'little'), int.from_bytes(h[84:88], 'little')
        f.seek(lba * 512 + i * size)
        e = f.read(size)
        return int.from_bytes(e[32:40], 'little') * 512


def esp_conf(img, new=None):
    """The ESP's limine.conf (mtools, a black box); with NEW, written first (the guest halted)."""
    at = f'{img}@@{part_offset(img, 0)}'
    env = dict(os.environ, MTOOLS_SKIP_CHECK='1')
    if new is not None:
        f = WORK / 'esp-limine.conf'
        f.write_text(new)
        run(['mcopy', '-o', '-i', at, f, '::/boot/limine/limine.conf'], env=env)
    return run(['mtype', '-i', at, '::/boot/limine/limine.conf'], env=env).stdout.decode()


def debugfs(img, cmd):
    r = subprocess.run(['debugfs', '-R', cmd, f'{img}?offset={part_offset(img, 1)}'], capture_output=True)
    return r.stdout.decode(errors='replace')


def mode_of(img, path):
    m = re.search(r'Mode:\s+(0?[0-7]+)', debugfs(img, f'stat {path}'))
    return int(m.group(1), 8) if m else None


def disk_media(img):
    return ['-drive', f'file={img},if=none,id=d0,format=raw', '-device', 'virtio-blk-pci,drive=d0']


class Machine:
    """One QEMU process: its serial log, its monitor, its boots."""

    def __init__(self, name, fw, media, mem='512', vga=True, audio=False, reboot_exits=False, trace=False):
        self.d = WORK / name
        shutil.rmtree(self.d, ignore_errors=True)
        self.d.mkdir(parents=True)
        self.serial, self.wav, self.sock = self.d / 'serial.log', self.d / 'speaker.wav', self.d / 'monitor.sock'
        machine = 'q35,pcspk-audiodev=snd0' if audio else 'q35'
        a = ['qemu-system-x86_64', '-machine', machine, '-m', mem, '-display', 'none', '-nic', 'none',
             '-serial', f'file:{self.serial}', '-monitor', f'unix:{self.sock},server,nowait', *media]
        if audio:
            a += ['-audiodev', f'wav,id=snd0,path={self.wav}']
        if reboot_exits:
            a += ['-no-reboot']
        if not vga:
            a += ['-vga', 'none']
        if trace:
            a += ['-trace', 'cpu_out', '-D', str(self.d / 'trace.log')]
        if os.access('/dev/kvm', os.R_OK | os.W_OK):
            a += ['-enable-kvm', '-cpu', 'host']
        if fw == 'uefi':
            shutil.copy(OVMF_VARS, self.d / 'vars.fd')
            a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
                  '-drive', f'if=pflash,format=raw,unit=1,file={self.d / "vars.fd"}']
        (self.d / 'qemu.args').write_text(' '.join(str(x) for x in a) + '\n')
        self.p = subprocess.Popen([str(x) for x in a], stdin=subprocess.DEVNULL, stdout=open(self.d / 'qemu.out', 'wb'),
                                  stderr=subprocess.STDOUT)
        self.since = 0

    def text(self):
        if not self.serial.exists():
            return ''
        return re.sub(r'\x1b\[[0-9;?=]*[A-Za-z]', '', self.serial.read_bytes().decode('latin-1')).replace('\r', '')

    def boot(self, until=r'^halt$', timeout=180, quiet_secs=None):
        """Wait for this boot's end (UNTIL in the serial log since this boot began, or QUIET_SECS
        gone by); this boot's text."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            t = self.text()[self.since:]
            if self.p.poll() is not None:
                break
            if quiet_secs is None and re.search(until, t, re.M):
                time.sleep(.5)
                break
            if quiet_secs is not None and time.monotonic() - t0 >= quiet_secs:
                break
            time.sleep(.5)
        return self.text()[self.since:]

    def hmp(self, cmd):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(str(self.sock))
        s.recv(4096)
        s.sendall(cmd.encode() + b'\n')
        time.sleep(.5)
        out = b''
        try:
            out = s.recv(65536)
        except (socket.timeout, OSError):
            pass
        s.close()
        return out.decode(errors='replace')

    def reset(self):
        self.since = len(self.text())
        self.hmp('system_reset')

    def quit(self):
        if self.p.poll() is None:
            try:
                self.hmp('quit')
                self.p.wait(timeout=20)
            except (OSError, subprocess.TimeoutExpired):
                self.p.kill()
                self.p.wait()
        (self.d / 'serial.txt').write_text(self.text())


def tones(wav):
    """tools/wav-notes' tones as (hz, ms) pairs; an empty or absent capture has none."""
    if not wav.exists() or wav.stat().st_size <= 44:
        return []
    r = subprocess.run([str(ROOT / 'tools/wav-notes'), str(wav)], capture_output=True, text=True)
    (wav.parent / 'tones.txt').write_text(r.stdout + r.stderr)
    if r.returncode:
        if 'no samples' in r.stderr or 'empty' in r.stderr:
            return []
        raise RuntimeError('tools/wav-notes: ' + r.stderr.strip())
    out = []
    for line in r.stdout.splitlines():
        m = re.match(r'tone \d+ start \S+ end \S+ len (\S+) hz (\S+) edges', line)
        if m:
            out.append((float(m.group(2)), float(m.group(1))))
    return out


def booted(row, text):
    if 'px118: init ran' not in text or not re.search(r'^halt$', text, re.M):
        fail(row, 'the boot did not reach its program and the halt; its last lines: '
             + ' | '.join(text.strip().split('\n')[-5:]))
        return False
    return True


def beeps(row, got, want):
    """WANT: the pitches, in order; each tone within 2% of its pitch and 40-250 ms long."""
    if len(got) != len(want) or any(abs(h - w) > w * .02 for (h, _), w in zip(got, want)) \
            or any(not 40 <= ms <= 250 for _, ms in got):
        fail(row, 'the capture holds ' + (', '.join(f'{h:.1f} Hz for {ms:.0f} ms' for h, ms in got) or 'no tone')
             + ', not ' + (', '.join(f'{w:.1f} Hz' for w in want) or 'none'))
        return False
    return True


def marks_line(text):
    m = re.search(r'^marks: .*$', text, re.M)
    return m.group(0) if m else ''


def block(text, name):
    m = re.search(rf'^px118: BEGIN {name}\n(.*?)\npx118: END {name}$', text, re.M | re.S)
    return m.group(1) if m else None


def facts(text):
    b = block(text, 'pax-boot') or ''
    return dict((l.split(' ', 1) + [''])[:2] for l in b.splitlines() if l)


def expect_line(row, text, want):
    got = marks_line(text)
    if not re.fullmatch(want, got):
        fail(row, f'the marks line is {got!r}, not /{want}/')
        return False
    return True


def without(conf, word):
    """CONF with WORD (a whole word of an entry's cmdline) taken out."""
    return re.sub(r'(?m)^(\s*cmdline:.*?) ' + re.escape(word) + r'(?= |$)', r'\1', conf)


def rows_beeps(fw, plain, quiet):
    # B1: a plain boot: the high beep at the entry, the low one at the first line drawn, nothing else.
    m = Machine(f'{fw}-B1', fw, ['-cdrom', plain], audio=True, reboot_exits=True)
    text = m.boot()
    m.quit()
    got = tones(m.wav)
    if booted(f'B1 {fw}', text) and beeps(f'B1 {fw}', got, [HIGH, LOW]):
        say(f'PASS B1 {fw}: two beeps, ' + ', then '.join(f'{h:.1f} Hz for {ms:.0f} ms' for h, ms in got))
    # B2: `pax.nobeep`: no tone at all.
    m = Machine(f'{fw}-B2', fw, ['-cdrom', quiet], audio=True, reboot_exits=True)
    text = m.boot()
    m.quit()
    got = tones(m.wav)
    if booted(f'B2 {fw}', text) and beeps(f'B2 {fw}', got, []):
        say(f'PASS B2 {fw}: pax.nobeep, no tone')
    # B3: no display device (-vga none), so no framebuffer: the high beep alone.
    m = Machine(f'{fw}-B3', fw, ['-cdrom', plain], audio=True, reboot_exits=True, vga=False)
    text = m.boot()
    m.quit()
    got = tones(m.wav)
    if booted(f'B3 {fw}', text) and beeps(f'B3 {fw}', got, [HIGH]):
        if 'screen: off, no framebuffer' not in text:
            fail(f'B3 {fw}', 'the kernel did not say `screen: off, no framebuffer`')
        else:
            say(f'PASS B3 {fw}: no framebuffer, one beep, {got[0][0]:.1f} Hz for {got[0][1]:.0f} ms')


def rows_cmos(fw, dump_iso):
    # M1: QEMU's CMOS map on a cold start, read by `pax.nomarks pax.cmosdump` (nothing written): the
    # marks' eight bytes read zero; the bytes QEMU and its firmware set are listed.
    m = Machine(f'{fw}-M1', fw, ['-cdrom', dump_iso], reboot_exits=True)
    text = m.boot()
    m.quit()
    if not booted(f'M1 {fw}', text):
        return
    cm = {}
    for row, rest in re.findall(r'^cmos: ([0-9a-f]{2}):((?: [0-9a-f]{2}){16})$', text, re.M):
        for i, v in enumerate(rest.split()):
            cm[int(row, 16) + i] = int(v, 16)
    if len(cm) != 256:
        fail(f'M1 {fw}', f'{len(cm)} CMOS bytes dumped, not 256')
        return
    ours = [cm[BASE + i] for i in range(8)]
    used = [o for o in range(0x0e, 0x80) if cm[o] != 0]
    upper = 'absent (every byte 0xff)' if all(cm[o] == 0xff for o in range(0x80, 0x100)) else \
        'nonzero at ' + ' '.join(f'{o:02x}' for o in range(0x80, 0x100) if cm[o])
    (m.d / 'cmos-map.txt').write_text(f'{fw}: nonzero lower-bank bytes past the clock: '
                                     + ' '.join(f'{o:02x}={cm[o]:02x}' for o in used) + f'\nupper bank {upper}\n')
    if any(ours) or not re.search(rf'CMOS {CMOS} off;', marks_line(text)):
        fail(f'M1 {fw}', f'the marks\' bytes read {ours} on a cold start; the line {marks_line(text)!r}')
    else:
        say(f'PASS M1 {fw}: {CMOS} zero on a cold start; nonzero past the clock: '
            + ' '.join(f'{o:02x}' for o in used) + f'; the upper bank {upper}')


def rows_marks(fw, img):
    # M2: a cold disk boot claims the bytes; after a reset the next boot holds them and says the
    # previous boot completed, with its console kept. L1: those bytes are the previous boot's console.
    m = Machine(f'{fw}-M2', fw, disk_media(img))
    t1 = m.boot()
    ok = booted(f'M2 {fw}', t1) and expect_line(
        f'M2 {fw}', t1, rf'marks: boot 1; the previous boot: none; CMOS {CMOS} claimed; log none')
    if ok:
        f1 = facts(t1)
        if f1.get('cmos') != f'{CMOS} claimed' or f1.get('previous') != 'none' or f1.get('boot') != '1':
            fail(f'M2 {fw}', f'/proc/pax-boot at the first boot: {f1}')
            ok = False
    m.reset()
    t2 = m.boot()
    m.quit()
    if not ok:
        return
    if not booted(f'M2 {fw}', t2) or not expect_line(
            f'M2 {fw}', t2, rf'marks: boot 2; the previous boot, 1, completed \(CMOS\); CMOS {CMOS} held; log \d+ bytes kept'):
        return
    f2 = facts(t2)
    want_st = ' '.join(STAGES)
    if f2.get('previous') != '1 end' or f2.get('from') != 'cmos' or f2.get('stages') != want_st or f2.get('cmos') != f'{CMOS} held':
        fail(f'M2 {fw}', f'/proc/pax-boot at the second boot: {f2}')
        return
    say(f'PASS M2 {fw}: claimed at boot 1, held at boot 2; the previous boot completed, stages {want_st}')
    kept = block(t2, 'pax-bootlog')
    at = t1.find('PAX: the console\n')
    end = t1.find('run 1: /bin/init\n')
    want = t1[at:end + len('run 1: /bin/init\n')] if at >= 0 and end >= 0 else None
    if kept is None or want is None or kept.rstrip('\n') != want.rstrip('\n'):
        (m.d / 'L1-kept.txt').write_text(kept or '')
        (m.d / 'L1-want.txt').write_text(want or '')
        fail(f'L1 {fw}', f'/proc/pax-bootlog ({len(kept or "")} bytes) is not the first boot\'s console '
             f'from its first line through `run 1:` ({len(want or "")} bytes); both kept in {m.d}')
    else:
        say(f'PASS L1 {fw}: the previous boot\'s console kept whole across the reset ({len(want)} bytes, '
            f'/proc/pax-boot: log {f2.get("log")})')


def rows_stops(fw, cpio):
    # S1-S7: a kernel stopped at each stage by `pax.bootstop=STAGE` leaves that stage; the next boot says so.
    for i, st in enumerate(STAGES[:-1]):
        row = f'S{i + 1} {fw}'
        img = disk(f'{fw}-S{i + 1}', cpio, f'pax.bootstop={st}')
        m = Machine(f'{fw}-S{i + 1}', fw, disk_media(img))
        if st == 'entered':
            t1 = m.boot(quiet_secs=25 if fw == 'uefi' else 15)  # nothing printed: the stop is before the serial port
        else:
            t1 = m.boot(until=rf'^bootmark: stopped at {st} \(pax\.bootstop\)$')
        if (st != 'entered' and f'bootmark: stopped at {st} (pax.bootstop)' not in t1) or 'px118: init ran' in t1:
            m.quit()
            fail(row, f'the first boot did not stop at {st}; its last lines: ' + ' | '.join(t1.strip().split('\n')[-4:]))
            continue
        esp_conf(img, without(esp_conf(img), f'pax.bootstop={st}'))
        m.reset()
        t2 = m.boot()
        m.quit()
        if not booted(row, t2) or not expect_line(
                row, t2, rf'marks: boot 2; the previous boot, 1, stopped at {st} \(CMOS\); CMOS {CMOS} held; log \d+ bytes kept'):
            continue
        f2 = facts(t2)
        want_st = ' '.join(STAGES[:i + 1])
        if f2.get('previous') != f'1 {st}' or f2.get('stages') != want_st:
            fail(row, f'/proc/pax-boot says previous {f2.get("previous")!r}, stages {f2.get("stages")!r}, not 1 {st} / {want_st}')
            continue
        say(f'PASS {row}: stopped at {st}; the next boot: the previous boot stopped at {st}, stages {want_st}')
        img.unlink()


def rows_refused(fw, cpio):
    # R1: CMOS that holds another's bytes (`pax.cmosfill=5a`, test-only) is refused: nothing written,
    # the boot goes on; the next boot (`pax.nomarks pax.cmosdump`) finds the eight bytes as they were.
    img = disk(f'{fw}-R1', cpio, 'pax.cmosfill=5a')
    m = Machine(f'{fw}-R1', fw, disk_media(img))
    t1 = m.boot()
    ok = booted(f'R1 {fw}', t1) and expect_line(
        f'R1 {fw}', t1, rf'marks: boot 0; the previous boot: none; CMOS {CMOS} refused \(found 0x5a5a5a5a5a5a5a5a\); log none')
    esp_conf(img, esp_conf(img).replace('pax.cmosfill=5a', 'pax.nomarks pax.cmosdump'))
    m.reset()
    t2 = m.boot()
    m.quit()
    if not ok or not booted(f'R1 {fw}', t2):
        return
    row = re.search(r'^cmos: 70:((?: [0-9a-f]{2}){16})$', t2, re.M)
    got = row.group(1).split()[8:16] if row else []
    if got != ['5a'] * 8:
        fail(f'R1 {fw}', f'after the refused boot {CMOS} read {got}, not 5a x 8')
    else:
        say(f'PASS R1 {fw}: another\'s bytes refused, nothing written over them, the boot went on')
    img.unlink()


def rows_log(fw, cpio, cpio_reboot):
    # L2: a log area changed under its checksum (`pax.logflip`, test-only, at the kernel's end) is
    # refused at the next boot and never printed.
    img = disk(f'{fw}-L2', cpio, 'pax.logflip')
    m = Machine(f'{fw}-L2', fw, disk_media(img))
    t1 = m.boot()
    m.reset()
    t2 = m.boot()
    m.quit()
    if booted(f'L2 {fw}', t1) and booted(f'L2 {fw}', t2) and expect_line(
            f'L2 {fw}', t2, rf'marks: boot 2; the previous boot, 1, completed \(CMOS\); CMOS {CMOS} held; log refused \(checksum\)'):
        kept = block(t2, 'pax-bootlog')
        if kept is None or kept.strip() != '' or facts(t2).get('log') != 'refused':
            fail(f'L2 {fw}', f'the refused log printed {len(kept or "")} bytes; /proc/pax-boot log {facts(t2).get("log")!r}')
        else:
            say(f'PASS L2 {fw}: a log changed under its checksum refused, nothing of it printed')
    img.unlink()
    # W1: the kernel's own warm reset (reboot(2): the FADT's register, then port 0xCF9): the next boot
    # finds the previous one completed, its console kept.
    img = disk(f'{fw}-W1', cpio_reboot, '')
    m = Machine(f'{fw}-W1', fw, disk_media(img))
    t = m.boot(until=r'^halt$', timeout=240)
    m.quit()
    first = t.find('px118: reboot')
    if first < 0:
        fail(f'W1 {fw}', 'the first boot did not ask for a restart; its last lines: ' + ' | '.join(t.strip().split('\n')[-4:]))
    else:
        t2 = t[first:]
        if booted(f'W1 {fw}', t2) and expect_line(
                f'W1 {fw}', t2, rf'marks: boot 2; the previous boot, 1, completed \(CMOS\); CMOS {CMOS} held; log \d+ bytes kept'):
            say(f'PASS W1 {fw}: after the kernel\'s own reset the previous boot is completed, its console kept '
                f'(log {facts(t2).get("log")})')
    img.unlink()


def rows_absent(fw, cpio):
    # N1: no memory at the log's area (-m 64M) and `pax.nomarks`: nothing kept, the boot unchanged to its program.
    img = disk(f'{fw}-N1', cpio, 'pax.nomarks')
    m = Machine(f'{fw}-N1', fw, disk_media(img), mem='64')
    t = m.boot()
    m.quit()
    if booted(f'N1 {fw}', t) and expect_line(f'N1 {fw}', t, rf'marks: boot 0; the previous boot: none; CMOS {CMOS} off; log no area'):
        say(f'PASS N1 {fw}: no CMOS, no log area: the boot reached its program and halted')
    img.unlink()


def rows_installed(fw, cpio):
    # U1: the installed system's Limine options (a five-second menu, verbose and serial, no `quiet`):
    # Limine's own lines on the serial port before PAX's first, and the boot unattended (no key).
    head = 'timeout: 5\nverbose: yes\nserial: yes\n'
    img = disk(f'{fw}-U1', cpio, 'quiet rootfstype=ext2', head=head)
    m = Machine(f'{fw}-U1', fw, disk_media(img))
    t0 = time.monotonic()
    t = m.boot(timeout=240)
    secs = time.monotonic() - t0
    m.quit()
    if booted(f'U1 {fw}', t):
        before = t[:t.find('PAX: the console')]
        if 'limine' not in before.lower():
            fail(f'U1 {fw}', 'no line of Limine\'s on the serial port before PAX\'s first')
        else:
            say(f'PASS U1 {fw}: the installed options: Limine on the serial port first ({len(before.splitlines())} lines), '
                f'then the boot to its program unattended in {secs:.0f} s')
    img.unlink()


def rows_post(fw, plain):
    # P1: the POST codes (port 0x80) in QEMU's I/O trace: 0x11 … 0x88, the last eight such written.
    m = Machine(f'{fw}-P1', fw, ['-cdrom', plain], reboot_exits=True, trace=True)
    text = m.boot()
    m.quit()
    log = m.d / 'trace.log'
    body = log.read_text(errors='replace') if log.exists() else ''
    if 'cpu_out' not in body:
        say(f'SKIP P1-{fw} reason=QEMU wrote no cpu_out trace, so port 0x80 is not observable here (not measured)')
        return
    vals = [int(v, 0) for v in re.findall(r'cpu_out\S* addr 0x0*80\b.*?value (0x[0-9a-f]+|\d+)', body)]
    want = [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
    ours = [v for v in vals if v in want]
    if not booted(f'P1 {fw}', text):
        return
    if ours[-8:] != want:
        fail(f'P1 {fw}', 'port 0x80 saw ' + ' '.join(f'{v:02x}' for v in vals[-16:]))
    else:
        say(f'PASS P1 {fw}: port 0x80 saw ' + ' '.join(f'{v:02x}' for v in ours[-8:]))


def rows_record(fw, cpio_rec):
    # K1: the boot's first program (`pax-boot-status record`) writes /var/log/boot.log (0600) and
    # /var/log/boot.summary (0644): at a cold boot the claim of the CMOS bytes with their offsets; at the
    # next, the previous boot completed and its console between the markers; the show lists both.
    img = disk(f'{fw}-K1', cpio_rec, '')
    m = Machine(f'{fw}-K1', fw, disk_media(img))
    t1 = m.boot()
    m.reset()
    t2 = m.boot()
    m.quit()
    if booted(f'K1 {fw}', t1) and booted(f'K1 {fw}', t2):
        log, summ = debugfs(img, 'cat /var/log/boot.log'), debugfs(img, 'cat /var/log/boot.summary')
        (m.d / 'boot.log').write_text(log)
        (m.d / 'boot.summary').write_text(summ)
        why = []
        b1, b2 = log.find('== boot 1, '), log.find('== boot 2, ')
        if b1 < 0 or b2 < b1:
            why.append('no block for boot 1 then boot 2')
        else:
            one, two = log[b1:b2], log[b2:]
            if 'previous: none recorded' not in one or f'cmos: {CMOS} claimed for the marks' not in one:
                why.append('boot 1\'s block lacks `previous: none recorded` or the claim with its offsets')
            if 'previous: boot 1 completed (marks from cmos)' not in two or f'cmos: {CMOS} held' not in two:
                why.append('boot 2\'s block lacks `previous: boot 1 completed` or `held`')
            con = re.search(r'--- console of boot 1 ---\n(.*)--- end of the console of boot 1 ---', two, re.S)
            if not con or 'PAX: the console' not in con.group(1) or 'run 1: /bin/pax-boot-status record' not in con.group(1):
                why.append('boot 2\'s block holds no console of boot 1 from its first line to `run 1:`')
        lines = [l.split() for l in summ.splitlines() if l]
        if len(lines) != 2 or lines[0][0] != '1' or 'previous=none' not in lines[0] or 'cmos=claimed' not in lines[0] \
                or lines[1][0] != '2' or 'previous=1' not in lines[1] or 'ended=end' not in lines[1] or 'cmos=held' not in lines[1]:
            why.append(f'boot.summary is {summ!r}')
        if (mode_of(img, '/var/log/boot.log'), mode_of(img, '/var/log/boot.summary')) != (0o100600, 0o100644):
            why.append(f'modes {mode_of(img, "/var/log/boot.log")!r} {mode_of(img, "/var/log/boot.summary")!r}, not 0600 and 0644')
        if not re.search(r'^  boot 1: completed \(found by boot 2 at \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ, from cmos\)$', t2, re.M) \
                or not re.search(r'^  boot 2: this boot, at init$', t2, re.M):
            why.append('the show at boot 2 does not list boot 1 completed and boot 2 at init')
        if why:
            fail(f'K1 {fw}', '; '.join(why) + f' (kept in {m.d})')
        else:
            say(f'PASS K1 {fw}: boot.log 0600 (the claim at boot 1, boot 1 completed and its console at boot 2), '
                f'boot.summary 0644 two lines, the show lists them')
    img.unlink()
    # K2: a boot stopped at `devices`: the next boot's record says so, and the show.
    img = disk(f'{fw}-K2', cpio_rec, 'pax.bootstop=devices')
    m = Machine(f'{fw}-K2', fw, disk_media(img))
    t1 = m.boot(until=r'^bootmark: stopped at devices \(pax\.bootstop\)$')
    esp_conf(img, without(esp_conf(img), 'pax.bootstop=devices'))
    m.reset()
    t2 = m.boot()
    m.quit()
    if booted(f'K2 {fw}', t2):
        log = debugfs(img, 'cat /var/log/boot.log')
        if 'previous: boot 1 stopped at devices (marks from cmos)' not in log or \
                not re.search(r'^  boot 1: stopped at devices \(found by boot 2 at ', t2, re.M):
            fail(f'K2 {fw}', f'boot.log or the show does not say boot 1 stopped at devices: {log[:400]!r}')
        else:
            say(f'PASS K2 {fw}: a boot stopped at devices, so recorded at the next boot and shown')
    img.unlink()
    # K3: boot.log past 256 KiB is rotated: the old one becomes boot.log.1, the new block starts a new file.
    img = disk(f'{fw}-K3', cpio_rec, '')
    big = WORK / 'big-boot.log'
    big.write_bytes(b'x' * 262100 + b'\n')
    f = WORK / 'K3.debugfs'
    f.write_text(f'cd /var/log\nwrite {big} boot.log\nsif /var/log/boot.log mode 0100600\n')
    subprocess.run(['debugfs', '-w', '-f', str(f), f'{img}?offset={part_offset(img, 1)}'], capture_output=True)
    m = Machine(f'{fw}-K3', fw, disk_media(img))
    t = m.boot()
    m.quit()
    if booted(f'K3 {fw}', t):
        one = debugfs(img, 'cat /var/log/boot.log.1')
        new = debugfs(img, 'cat /var/log/boot.log')
        if len(one) != 262101 or not new.startswith('== boot 1, '):
            fail(f'K3 {fw}', f'boot.log.1 is {len(one)} bytes and boot.log starts {new[:30]!r}')
        else:
            say(f'PASS K3 {fw}: a boot.log past 256 KiB rotated to boot.log.1, the new block in a new boot.log')
    img.unlink()


def main():
    only = os.environ.get('PX118_ROWS', 'B M S R L N U P K').split()
    cpio = archive('init')
    cpio_reboot = archive('init-reboot', reboot=True)
    plain, quiet = iso('plain', cpio, ''), iso('nobeep', cpio, 'pax.nobeep')
    dump_iso = iso('dump', cpio, 'pax.nomarks pax.cmosdump')
    prog = os.environ.get('PX118_BOOTSTATUS', '')
    cpio_rec = archive_record('record', prog) if prog else None
    for fw in LEGS:
        if fw == 'uefi' and not OVMF_CODE.exists():
            if os.environ.get('PAX_REQUIRE_UEFI') == '1':
                fail('B0 uefi', f'no {OVMF_CODE}')
            else:
                say(f'SKIP uefi reason=no {OVMF_CODE} (SKIPPED LOUDLY)')
            continue
        steps = [('B', lambda: rows_beeps(fw, plain, quiet)), ('M', lambda: rows_cmos(fw, dump_iso)),
                 ('M', lambda: rows_marks(fw, disk(f'{fw}-M2', cpio, ''))), ('S', lambda: rows_stops(fw, cpio)),
                 ('R', lambda: rows_refused(fw, cpio)), ('L', lambda: rows_log(fw, cpio, cpio_reboot)),
                 ('N', lambda: rows_absent(fw, cpio)), ('U', lambda: rows_installed(fw, cpio)), ('P', lambda: rows_post(fw, plain)),
                 ('K', lambda: rows_record(fw, cpio_rec) if cpio_rec else fail(f'K0 {fw}', 'no pax-boot-status built (PX118_BOOTSTATUS)'))]
        for key, step in steps:
            if key not in only:
                continue
            try:
                step()
            except RuntimeError as e:
                fail(f'{key}0 {fw}', str(e))
    say('mpx6-bootlog: ' + ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


main()
