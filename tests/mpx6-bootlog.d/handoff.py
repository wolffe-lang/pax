"""tests/mpx6-bootlog.d/handoff.py — px118 item 9: try to make QEMU show a black hand-off in the kernel's
early window, and say what each display shape gives.

    handoff.py WORK KERNEL.elf

Each case boots tools/mkimage's ISO of the console kernel (an archive whose first program prints and exits)
under one display shape: a Limine `resolution:` (depth, size), a display device (VGA, VGA without EDID, a
4K VGA, bochs-display, ramfb, virtio-gpu, cirrus, qxl), the firmware. At the kernel's `halt` QEMU's monitor
takes a screendump of what the display scans out; the case prints the kernel's `screen:` and `marks:` lines
from the serial log, the beeps it would sound (the first always; the second when the console drew), and
how much of the picture is not black. A case whose kernel ran to its program (serial) while the picture is
black is a black hand-off seen in QEMU. Prints one `CASE` line a case; exits 0 (a probe, not a gate)."""
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

WORK, KERNEL = Path(sys.argv[1]), Path(sys.argv[2])
ROOT = Path(__file__).resolve().parents[2]
OVMF_CODE = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
OVMF_VARS = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
WORK.mkdir(parents=True, exist_ok=True)


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


def iso(name, cpio, resolution=None, head='timeout: 0\nquiet: yes\n'):
    conf = WORK / f'{name}.conf'
    conf.write_text(head + '\n/PAX\n    protocol: limine\n    path: boot():/boot/pax\n'
                    '    module_path: boot():/boot/initramfs.cpio\n'
                    + (f'    resolution: {resolution}\n' if resolution else ''))
    out = WORK / f'{name}.iso'
    run([ROOT / 'tools/mkimage', '--conf', conf, '--add', cpio, 'initramfs.cpio', KERNEL, out])
    return out


def hmp(sock, cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(str(sock))
    s.recv(4096)
    s.sendall(cmd.encode() + b'\n')
    time.sleep(1)
    try:
        s.recv(65536)
    except (socket.timeout, OSError):
        pass
    s.close()


def lit(ppm):
    """(width, height, the share of pixels that are not black) of a P6 screendump; None when unreadable."""
    try:
        b = ppm.read_bytes()
    except OSError:
        return None
    m = re.match(rb'P6\s+(\d+)\s+(\d+)\s+(\d+)\s', b)
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    px = b[m.end():]
    n = w * h
    on = sum(1 for i in range(0, min(len(px), 3 * n), 3) if px[i] or px[i + 1] or px[i + 2])
    return w, h, on / n if n else 0.0


def case(name, fw, image, devices, mem='512'):
    d = WORK / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
    serial, sock, shot = d / 'serial.log', d / 'monitor.sock', d / 'screen.ppm'
    a = ['qemu-system-x86_64', '-machine', 'q35', '-m', mem, '-display', 'none', '-nic', 'none', '-no-reboot',
         '-cdrom', image, '-serial', f'file:{serial}', '-monitor', f'unix:{sock},server,nowait', *devices]
    if os.access('/dev/kvm', os.R_OK | os.W_OK):
        a += ['-enable-kvm', '-cpu', 'host']
    if fw == 'uefi':
        shutil.copy(OVMF_VARS, d / 'vars.fd')
        a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
              '-drive', f'if=pflash,format=raw,unit=1,file={d / "vars.fd"}']
    (d / 'qemu.args').write_text(' '.join(str(x) for x in a) + '\n')
    p = subprocess.Popen([str(x) for x in a], stdin=subprocess.DEVNULL, stdout=open(d / 'qemu.out', 'wb'),
                         stderr=subprocess.STDOUT)
    text = ''
    t0 = time.monotonic()
    while time.monotonic() - t0 < 120 and p.poll() is None:
        if serial.exists():
            text = serial.read_bytes().decode('latin-1').replace('\r', '')
        if re.search(r'^halt$', text, re.M):
            break
        time.sleep(.5)
    ran = 'px118: init ran' in text
    shown = None
    if p.poll() is None:
        time.sleep(1)
        hmp(sock, f'screendump {shot}')
        shown = lit(shot)
        hmp(sock, 'quit')
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    (d / 'serial.txt').write_text(text)
    scr = re.search(r'^screen: .*$', text, re.M)
    marks = re.search(r'^marks: .*$', text, re.M)
    pic = f'{shown[0]}x{shown[1]}, {100 * shown[2]:.2f}% lit' if shown else 'no screendump'
    black = ran and shown is not None and shown[2] < 0.001
    beeps = 'high only' if scr and scr.group(0).startswith('screen: off') else 'high then low'
    out = qemu_note(d)
    print(f'CASE {name} {fw}: {"BLACK while the kernel ran" if black else ("ran" if ran else "did NOT reach its program")}; '
          f'picture {pic}; {scr.group(0) if scr else "no screen: line"}; beeps {beeps}; '
          f'{marks.group(0) if marks else "no marks line"}{"; qemu: " + out if out else ""}', flush=True)


def qemu_note(d):
    t = (d / 'qemu.out').read_text(errors='replace').strip()
    return t.splitlines()[-1][:160] if t else ''


def main():
    cpio = archive()
    plain = iso('plain', cpio)
    d16 = iso('d16', cpio, '1024x768x16')
    d24 = iso('d24', cpio, '1024x768x24')
    k4 = iso('k4', cpio, '3840x2160')
    menu = iso('menu', cpio, '3840x2160', head='timeout: 2\nverbose: yes\nserial: yes\n')
    odd = iso('odd', cpio, '1366x768')
    cases = [
        ('std', 'bios', plain, []), ('std', 'uefi', plain, []),
        ('depth16', 'bios', d16, []), ('depth16', 'uefi', d16, []),
        ('depth24', 'bios', d24, []), ('depth24', 'uefi', d24, []),
        ('noedid', 'bios', plain, ['-vga', 'none', '-device', 'VGA,edid=off']),
        ('noedid', 'uefi', plain, ['-vga', 'none', '-device', 'VGA,edid=off']),
        ('vga4k', 'uefi', k4, ['-vga', 'none', '-device', 'VGA,xres=3840,yres=2160,vgamem_mb=64']),
        ('menu-then-4k', 'uefi', menu, ['-vga', 'none', '-device', 'VGA,xres=3840,yres=2160,vgamem_mb=64']),
        ('pitch1366', 'bios', odd, []), ('pitch1366', 'uefi', odd, []),
        ('bochs-display', 'uefi', plain, ['-vga', 'none', '-device', 'bochs-display']),
        ('ramfb', 'uefi', plain, ['-vga', 'none', '-device', 'ramfb']),
        ('virtio-gpu', 'uefi', plain, ['-vga', 'none', '-device', 'virtio-gpu-pci']),
        ('virtio-gpu-8g', 'uefi', plain, ['-vga', 'none', '-device', 'virtio-gpu-pci'], '8192'),
        ('virtio-vga', 'bios', plain, ['-vga', 'none', '-device', 'virtio-vga']),
        ('cirrus', 'bios', plain, ['-vga', 'cirrus']), ('cirrus', 'uefi', plain, ['-vga', 'cirrus']),
        ('qxl', 'uefi', plain, ['-vga', 'qxl']),
    ]
    for c in cases:
        try:
            case(f'{c[0]}-{c[1]}', c[1], c[2], c[3], *(c[4:]))
        except Exception as e:  # a probe: say it and go on
            print(f'CASE {c[0]}-{c[1]}: the case could not run: {e}', flush=True)


main()
