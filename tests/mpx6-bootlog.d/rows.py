"""tests/mpx6-bootlog.d/rows.py — px118's rows (tests/mpx6-bootlog's header has each).

    rows.py WORK KERNEL.elf FIRMWARE...

The archive is tools/mkinitramfs's (tests/mpx6-bootlog.d/init.c, built static here, as its first program),
the image tools/mkimage's with a Limine configuration written here; each boots under QEMU with the PC speaker
on QEMU's `wav` audio backend, its serial log read to the kernel's `halt`, then QEMU told to quit through its
monitor (so the capture is written out), and the capture measured by tools/wav-notes. Prints PASS/FAIL lines at
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


def archive():
    a = WORK / 'in'
    a.mkdir(exist_ok=True)
    init = a / 'init'
    run(['cc', '-static', '-nostdlib', '-ffreestanding', '-fno-pie', '-no-pie', '-fno-stack-protector', '-O1',
         '-o', init, Path(__file__).resolve().parent / 'init.c'])
    (a / 'pax-run').write_text('/bin/init\n')
    out = WORK / 'init.cpio'
    run([ROOT / 'tools/mkinitramfs', out, '/dev/', '/proc/', '/sys/', '/tmp/:1777', f'/bin/init={init}',
         f'/etc/pax-run={a / "pax-run"}'])
    return out


def iso(name, cpio, cmdline):
    conf = WORK / f'{name}.conf'
    conf.write_text('timeout: 0\nquiet: yes\n\n/PAX\n    protocol: limine\n    path: boot():/boot/pax\n'
                    '    module_path: boot():/boot/initramfs.cpio\n' + (f'    cmdline: {cmdline}\n' if cmdline else ''))
    out = WORK / f'{name}.iso'
    run([ROOT / 'tools/mkimage', '--conf', conf, '--add', cpio, 'initramfs.cpio', KERNEL, out])
    return out


def monitor(sock, cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(str(sock))
    s.recv(4096)  # the banner and the first prompt
    s.sendall(cmd.encode() + b'\n')
    time.sleep(.5)
    try:
        s.recv(4096)
    except (socket.timeout, OSError):
        pass
    s.close()


def boot(image, fw, name, vga=True, timeout=180):
    """Boot IMAGE (an ISO) under FW to the kernel's `halt`; the serial text and the capture's path."""
    d = WORK / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
    serial, wav, sock = d / 'serial.log', d / 'speaker.wav', d / 'monitor.sock'
    a = ['qemu-system-x86_64', '-machine', 'q35,pcspk-audiodev=snd0', '-m', '512', '-display', 'none', '-nic', 'none',
         '-cdrom', image, '-serial', f'file:{serial}', '-audiodev', f'wav,id=snd0,path={wav}',
         '-monitor', f'unix:{sock},server,nowait', '-no-reboot']
    if not vga:
        a += ['-vga', 'none']
    if os.access('/dev/kvm', os.R_OK | os.W_OK):
        a += ['-enable-kvm', '-cpu', 'host']
    if fw == 'uefi':
        shutil.copy(OVMF_VARS, d / 'vars.fd')
        a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
              '-drive', f'if=pflash,format=raw,unit=1,file={d / "vars.fd"}']
    p = subprocess.Popen([str(x) for x in a], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.STDOUT)
    t0 = time.monotonic()
    text = ''
    while time.monotonic() - t0 < timeout:
        if serial.exists():
            text = re.sub(r'\x1b\[[0-9;?=]*[A-Za-z]', '', serial.read_bytes().decode('latin-1')).replace('\r', '')
        if p.poll() is not None or re.search(r'^halt$', text, re.M):
            break
        time.sleep(.5)
    if p.poll() is None:
        time.sleep(.5)
        try:
            monitor(sock, 'quit')
            p.wait(timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            p.kill()
            p.wait()
    (d / 'serial.txt').write_text(text)
    return text, wav


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


def near(hz, want):
    return abs(hz - want) <= want * 0.02


def beeps(row, got, want):
    """WANT: the pitches, in order; each tone within 2% of its pitch and 40-250 ms long."""
    if len(got) != len(want) or any(not near(h, w) for (h, _), w in zip(got, want)) \
            or any(not 40 <= ms <= 250 for _, ms in got):
        fail(row, 'the capture holds ' + (', '.join(f'{h:.1f} Hz for {ms:.0f} ms' for h, ms in got) or 'no tone')
             + ', not ' + (', '.join(f'{w:.1f} Hz' for w in want) or 'none'))
        return False
    return True


def main():
    cpio = archive()
    plain, quiet = iso('plain', cpio, ''), iso('nobeep', cpio, 'pax.nobeep')
    for fw in LEGS:
        if fw == 'uefi' and not OVMF_CODE.exists():
            if os.environ.get('PAX_REQUIRE_UEFI') == '1':
                fail('B0 uefi', f'no {OVMF_CODE}')
            else:
                say(f'SKIP uefi: no {OVMF_CODE} (SKIPPED LOUDLY)')
            continue
        # B1: a plain boot: the high beep at the entry, the low one at the first line drawn, nothing else.
        text, wav = boot(plain, fw, f'{fw}-B1')
        got = tones(wav)
        if booted(f'B1 {fw}', text) and beeps(f'B1 {fw}', got, [HIGH, LOW]):
            say(f'PASS B1 {fw}: two beeps, ' + ', then '.join(f'{h:.1f} Hz for {ms:.0f} ms' for h, ms in got))
        # B2: `pax.nobeep`: no tone at all.
        text, wav = boot(quiet, fw, f'{fw}-B2')
        got = tones(wav)
        if booted(f'B2 {fw}', text) and beeps(f'B2 {fw}', got, []):
            say(f'PASS B2 {fw}: pax.nobeep, no tone')
        # B3: no display device (-vga none), so no framebuffer: the high beep alone.
        text, wav = boot(plain, fw, f'{fw}-B3', vga=False)
        got = tones(wav)
        if booted(f'B3 {fw}', text) and beeps(f'B3 {fw}', got, [HIGH]):
            if 'screen: off, no framebuffer' not in text:
                fail(f'B3 {fw}', 'the kernel did not say `screen: off, no framebuffer`')
            else:
                say(f'PASS B3 {fw}: no framebuffer, one beep, {got[0][0]:.1f} Hz for {got[0][1]:.0f} ms')
    say('mpx6-bootlog: ' + ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


main()
