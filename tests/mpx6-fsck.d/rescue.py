#!/usr/bin/env python3
"""Real ext2 power cut, explicit rescue archive, repaired-root persistence."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys

repo, work, firmwares = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].split(',')
d = Path(__file__).resolve().parent
r = work / 'rescue'
r.mkdir(parents=True, exist_ok=True)
kernel = work / 'kernel/kmain_console.elf'


def run(argv, log):
    p = subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (r / log).write_bytes(p.stdout)
    assert p.returncode == 0, (argv, p.returncode, p.stdout.decode(errors='replace'))
    return p.stdout


script = '''PATH=/bin
export PATH
check() {
    echo PX72_READBACK
    cat /etc/motd
    lope list
    cat /home/pax/notes.txt
    cat /root/note
    cat /proc/self/mounts
}
case "$(cat /root/stage)" in
crash)
    echo hello > /etc/motd
    lope add /usr/share/tunes
    echo 'written on PAX, before the reboot' > /home/pax/notes.txt
    echo 'root wrote this in /root' > /root/note
    echo first > /root/stage
    echo PX72_CRASH_READY
    while :; do :; done
    ;;
first)
    check
    if /bin/fsck.ext2 -y /dev/vda2; then echo PX72_UNSAFE_MOUNTED; else echo PX72_MOUNTED_REFUSED; fi
    echo second > /root/stage
    reboot
    ;;
second)
    check
    echo PX72_SESSION_DONE
    ;;
esac
'''
(r / 'session.sh').write_text(script)
(r / 'stage').write_text('crash\n')
(r / 'motd').write_text('initial\n')
(r / 'root.run').write_text('/bin/env HOME=/home/pax /bin/sh /etc/session.sh\n')
(r / 'rescue.run').write_text('/bin/fsck.ext2 -fy /dev/vda2\n')
(r / 'root.conf').write_text('timeout: 0\nquiet: yes\n/PAX\n    protocol: limine\n    path: boot():/boot/pax\n    cmdline: root=/dev/vda2 rw\n')
(r / 'rescue.conf').write_text('timeout: 0\nquiet: yes\n/PAX rescue\n    protocol: limine\n    path: boot():/boot/pax\n    cmdline: root=/dev/vda9\n    module_path: boot():/boot/initramfs.cpio\n')
args = ['/bin/sh=' + str(work/'pelt/pelt') + ':755',
        '/bin/lope=' + str(work/'lope/lope') + ':755',
        '/bin/reboot=' + str(work/'probe/reboot') + ':755',
        '/bin/fsck.ext2=' + str(work/'bin/fsck.ext2') + ':755']
args += ['/bin/' + n + '=' + str(work/'bore'/n) + ':755' for n in ['cat', 'env']]
args += ['/etc/pax-run=' + str(r/'root.run') + ':644',
         '/etc/session.sh=' + str(r/'session.sh') + ':644',
         '/root/stage=' + str(r/'stage') + ':644',
         '/etc/motd=' + str(r/'motd') + ':644',
         '/etc/fstab=' + str(repo/'user/fstab-root') + ':644',
         '/root/:700', '/home/pax/:755:1000:1000', '/usr/share/tunes/']
run([repo/'tools/mkinitramfs', r/'root.cpio', *args], 'root-cpio.log')
run([repo/'tools/mkinitramfs', r/'rescue.cpio',
     '/bin/fsck.ext2=' + str(work/'bin/fsck.ext2') + ':755',
     '/etc/pax-run=' + str(r/'rescue.run') + ':644'], 'rescue-cpio.log')
# Carry the rescue module but select the real root for the initial cut.
(r / 'initial.conf').write_text((r/'root.conf').read_text() + '    module_path: boot():/boot/initramfs.cpio\n')
run([repo/'tools/mkdisk', '--gpt', '--no-journal', '--kernel', kernel,
     '--root', r/'root.cpio', '--initramfs', r/'rescue.cpio', '--conf', r/'initial.conf',
     '256M', r/'base.img'], 'disk.log')


def configure(image, conf):
    # Choosing the alternate Limine entry is host-controlled for a fully
    # unattended fixture. The filesystem under repair is never mounted.
    run([repo/'tools/disktools', r, 'mcopy', '-o', '-i', str(image) + '@@2097152',
         conf, '::/boot/limine/limine.conf'], image.stem + '.select.log')


def partition(image, out):
    with image.open('rb') as src, out.open('wb') as dst:
        src.seek(135168 * 512)
        # mkdisk aligns the partition's end down to a 4 KiB boundary.
        size = ((image.stat().st_size // 512 - 34 - 135168) // 8) * 4096
        for _ in range(size // 4096):
            dst.write(src.read(4096))
    return out


for fw in firmwares:
    image = r / (fw + '.img')
    shutil.copyfile(r/'base.img', image)
    run(['python3', '-I', d/'boot.py', repo, image, r/(fw+'.cut.serial'), fw, 'cut'], fw+'.cut.log')
    before = partition(image, r/(fw+'.crashed.ext2'))
    with before.open('rb') as f:
        f.seek(1082)
        assert f.read(2) != b'\x01\x00', 'power cut must leave root dirty'
    configure(image, r/'rescue.conf')
    run(['python3', '-I', d/'boot.py', repo, image, r/(fw+'.rescue.serial'), fw, 'halt'], fw+'.rescue.log')
    text = (r/(fw+'.rescue.serial')).read_text()
    assert 'fsck.ext2 pid 1 exit_group 1' in text, text
    assert '0 uncorrected' in text and 'unsupported:' not in text, text
    repaired = partition(image, r/(fw+'.repaired.ext2'))
    with repaired.open('rb') as f:
        f.seek(1082)
        assert f.read(2) == b'\x01\x00', 'FAIL R-clean: rescue left the superblock dirty'
    run([repo/'tools/e2fs', r, 'e2fsck', '-fn', repaired], fw+'.repair-verify.log')
    configure(image, r/'root.conf')
    for phase in ['restart', 'halt']:
        serial = r/(fw+'.'+phase+'.serial')
        run(['python3', '-I', d/'boot.py', repo, image, serial, fw, phase], fw+'.'+phase+'.log')
        text = serial.read_text().replace('\r', '')
        for expected in ['PX72_READBACK', '\nhello\n', '/usr/share/tunes',
                         'written on PAX, before the reboot', 'root wrote this in /root',
                         '/dev/root / ext2 rw,relatime 0 0', 'tmpfs /tmp tmpfs']:
            assert expected in text, (phase, expected, text)
        assert 'PANIC' not in text and 'PX72_UNSAFE_MOUNTED' not in text, text
        if phase == 'restart':
            assert 'PX72_MOUNTED_REFUSED' in text, text
        else:
            assert 'PX72_SESSION_DONE' in text, text
    final = partition(image, r/(fw+'.final.ext2'))
    run([repo/'tools/e2fs', r, 'e2fsck', '-fn', final], fw+'.final-verify.log')
    with final.open('rb') as f:
        f.seek(1082)
        assert f.read(2) == b'\x01\x00'
    print('PASS rescue-' + fw + ': real cut, rescue repair, clean superblock, two persistent root boots', flush=True)
