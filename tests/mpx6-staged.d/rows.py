"""tests/mpx6-staged.d/rows.py — px115's staged-boot rows (tests/mpx6-staged's header has each).

    rows.py WORK KERNEL.elf PELT CAT FIRMWARE...

The archives are tools/mkinitramfs's, the disks tools/mkdisk's, edited by debugfs and mtools (black boxes);
each disk boots alone under QEMU with -no-reboot, its serial log read to its end (QEMU's exit: a reboot) or to
the kernel's `halt`. Prints PASS/FAIL lines at column 0; exits 1 when any row failed."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

WORK, KERNEL, PELT, CAT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
LEGS = sys.argv[5:]
ROOT = Path(__file__).resolve().parents[2]
OVMF_CODE = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
OVMF_VARS = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
MARKER = 'px115-staged-archive-marker'
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


def script(path, lines):
    path.write_text('#!/bin/pelt\n' + ''.join(l + '\n' for l in lines))
    path.chmod(0o755)
    return path


def archives():
    a = WORK / 'in'
    a.mkdir(exist_ok=True)
    (a / 'marker').write_text(MARKER + '\n')
    (a / 'fstab-staged').write_text('tmpfs /tmp tmpfs nosuid,nodev 0 0\n')
    (a / 'fstab-root').write_text('/dev/vda2 / ext2 rw 0 1\ntmpfs /tmp tmpfs nosuid,nodev 0 0\n')
    (a / 'pax-run').write_text('/bin/installed-init\n')
    staged_init = script(a / 'staged-init', ['echo "px115-staged: init ran"', 'cat /etc/px115-staged'])
    installed_init = script(a / 'installed-init', ['echo "px115-installed: init ran"'])
    common = [f'/bin/pelt={PELT}', f'/bin/cat={CAT}', '/dev/', '/proc/', '/sys/', '/tmp/:1777', '/mnt/']
    staged = WORK / 'staged.cpio'
    run([ROOT / 'tools/mkinitramfs', staged, *common, f'/bin/staged-init={staged_init}',
         f'/etc/px115-staged={a / "marker"}', f'/etc/fstab={a / "fstab-staged"}'])
    root = WORK / 'root.cpio'
    run([ROOT / 'tools/mkinitramfs', root, *common, f'/bin/installed-init={installed_init}',
         f'/etc/pax-run={a / "pax-run"}', f'/etc/fstab={a / "fstab-root"}', '/var/', '/var/lib/'])
    return staged, root


def make_disk(name, staged, root, digest, with_archive=True):
    conf = WORK / f'{name}.conf'
    conf.write_text('timeout: 0\nserial: yes\n\n'
                    '/staged\n    protocol: limine\n    path: boot():/boot/pax\n'
                    f'    cmdline: pax.staged={digest} init=/bin/staged-init\n'
                    '/installed\n    protocol: limine\n    path: boot():/boot/pax\n    cmdline: quiet\n')
    img = WORK / f'{name}.img'
    env = dict(os.environ, SOURCE_DATE_EPOCH='1794269606')
    r = subprocess.run([str(ROOT / 'tools/mkdisk'), '--gpt', '--no-journal', '--kernel', str(KERNEL), '--root', str(root),
                        '--conf', str(conf), '--label', 'pax-root', '256M', str(img)], capture_output=True, env=env)
    if r.returncode:
        raise RuntimeError('tools/mkdisk: ' + r.stderr.decode(errors='replace')[-600:])
    at = root_offset(img)
    zeros = WORK / 'attempts'
    zeros.write_bytes(b'00000000')
    cmds = ['mkdir /var/lib/pax-upgrade', 'mkdir /var/lib/pax-upgrade/staged', 'cd /var/lib/pax-upgrade',
            f'write {zeros} attempts']
    if with_archive:
        cmds += ['cd /var/lib/pax-upgrade/staged', f'write {staged} archive']
    f = WORK / f'{name}.debugfs'
    f.write_text('\n'.join(cmds) + '\n')
    r = run(['debugfs', '-w', '-f', f, f'{img}?offset={at}'])
    if b'Could not' in r.stderr or b'not found' in r.stderr:
        raise RuntimeError('debugfs: ' + r.stderr.decode(errors='replace')[-400:])
    return img


def root_offset(img):
    with open(img, 'rb') as f:
        f.seek(512)
        h = f.read(92)
        lba, n, size = int.from_bytes(h[72:80], 'little'), int.from_bytes(h[80:84], 'little'), int.from_bytes(h[84:88], 'little')
        f.seek(lba * 512)
        for i in range(n):
            e = f.read(size)
            if i == 1:
                return int.from_bytes(e[32:40], 'little') * 512
    raise RuntimeError('no partition 2')


def attempts(img):
    r = run(['debugfs', '-R', 'cat /var/lib/pax-upgrade/attempts', f'{img}?offset={root_offset(img)}'])
    return r.stdout.decode(errors='replace')


def boot(img, fw, name, timeout=180):
    d = WORK / name
    d.mkdir(exist_ok=True)
    serial = d / 'serial.log'
    a = ['qemu-system-x86_64', '-machine', 'q35', '-m', '2048', '-no-reboot', '-display', 'none', '-nic', 'none',
         '-drive', f'file={img},if=none,id=d0,format=raw', '-device', 'virtio-blk-pci,drive=d0',
         '-serial', f'file:{serial}']
    if os.access('/dev/kvm', os.R_OK | os.W_OK):
        a += ['-enable-kvm', '-cpu', 'host']
    if fw == 'uefi':
        shutil.copy(OVMF_VARS, d / 'vars.fd')
        a += ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={OVMF_CODE}',
              '-drive', f'if=pflash,format=raw,unit=1,file={d / "vars.fd"}']
    p = subprocess.Popen(a, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    t0 = time.monotonic()
    text = ''
    while time.monotonic() - t0 < timeout:
        if serial.exists():
            text = re.sub(r'\x1b\[[0-9;?=]*[A-Za-z]', '', serial.read_bytes().decode('latin-1')).replace('\r', '')
        if p.poll() is not None:
            break
        if re.search(r'^halt$', text, re.M):
            time.sleep(1)
            break
        time.sleep(.5)
    exited = p.poll() is not None
    if not exited:
        p.kill()
        p.wait()
    (d / 'serial.txt').write_text(text)
    return text, exited


def need(row, text, words):
    missing = [w for w in words if w not in text]
    if missing:
        fail(row, f'missing {missing[0]!r} on the serial log; its last lines: ' + ' | '.join(text.strip().split('\n')[-6:]))
        return False
    return True


def staged_ok(row, text, exited, n):
    if not need(row, text, [f'staged: attempt {n} of 2', 'staged: / is the staged archive', 'px115-staged: init ran', MARKER,
                            'staged: the staged program ended; reboot']):
        return False
    if not exited:
        fail(row, 'QEMU still ran: the staged program\'s end was not a reboot')
        return False
    return True


def installed_ok(row, text, why):
    if not need(row, text, [why, '/ is the installed root (root=)', 'px115-installed: init ran']):
        return False
    if 'px115-staged: init ran' in text:
        fail(row, 'the staged program ran on the installed root')
        return False
    return True


def main():
    staged, root = archives()
    digest = hashlib.sha256(staged.read_bytes()).hexdigest()
    say(f'mpx6-staged: the staged archive {staged.stat().st_size} bytes, sha256 {digest}')
    for fw in LEGS:
        if fw == 'uefi' and not OVMF_CODE.exists():
            if os.environ.get('PAX_REQUIRE_UEFI') == '1':
                fail('T0 uefi', f'no {OVMF_CODE}')
            else:
                say(f'SKIP uefi: no {OVMF_CODE} (SKIPPED LOUDLY)')
            continue
        img = make_disk(f'{fw}-a', staged, root, digest)
        for n, row in ((1, 'T1'), (2, 'T2')):
            text, exited = boot(img, fw, f'{fw}-{row}')
            want = '1' * n + '0' * (8 - n)
            got = attempts(img)
            if staged_ok(f'{row} {fw}', text, exited, n):
                if got != want:
                    fail(f'{row} {fw}', f'the attempts file reads {got!r}, not {want!r}')
                else:
                    say(f'PASS {row} {fw}: staged boot {n} of 2: / the staged archive (its marker read by its own init), '
                        f'the end a reboot, the attempts file {got}')
        text, _ = boot(img, fw, f'{fw}-T3')
        got = attempts(img)
        if installed_ok(f'T3 {fw}', text, 'staged: two staged boots began already'):
            if got != '11000000':
                fail(f'T3 {fw}', f'the attempts file reads {got!r}, not \'11000000\'')
            else:
                say(f'PASS T3 {fw}: the third staged boot refused by name; / the installed root, its own program run; the file {got}')
        img = make_disk(f'{fw}-b', staged, root, '0' * 64)
        text, _ = boot(img, fw, f'{fw}-T4')
        got = attempts(img)
        if installed_ok(f'T4 {fw}', text, "staged: the archive's sha256 is not pax.staged='s"):
            if got != '10000000':
                fail(f'T4 {fw}', f'the attempts file reads {got!r}, not \'10000000\'')
            else:
                say(f'PASS T4 {fw}: another digest refused by name after the attempt was counted ({got}); the installed root')
        img = make_disk(f'{fw}-c', staged, root, digest, with_archive=False)
        text, _ = boot(img, fw, f'{fw}-T5')
        if installed_ok(f'T5 {fw}', text, 'staged: no /var/lib/pax-upgrade/staged/archive'):
            say(f'PASS T5 {fw}: no archive, refused by name; the installed root')
    say('mpx6-staged: ' + ('FAIL' if bad else 'PASS'))
    sys.exit(1 if bad else 0)


main()
