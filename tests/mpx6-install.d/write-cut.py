#!/usr/bin/env python3
"""Cut inside ext2.wspan for the real installer's burrowd.pax-tmp.

Capture the exact volume/inode from ext2.add, then break at a multi-MiB
write offset, never on serial output or a timer. Resume the same put_file
operation after reboot. All filesystem inspection before the resume is
read-only. Repair is tested only afterwards, on a separate scratch copy.
"""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

repo, work = map(Path, sys.argv[1:3])
firmware = sys.argv[3]
assert firmware in ('bios', 'uefi')
leg = work / ('cut-' + firmware)
leg.mkdir(exist_ok=False)
failed = []


def run(args, **kw):
    return subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, **kw)


def row(name, ok, detail):
    print(('PASS ' if ok else 'FAIL ') + name + ': ' + detail, flush=True)
    if not ok:
        failed.append(name)


def debug(image, command, write=False):
    p = run(['debugfs', *(['-w'] if write else []), '-R', command, image])
    assert p.returncode == 0, p.stdout
    return p.stdout


def fsck(image, name):
    p = run(['e2fsck', '-fn', image])
    (leg / (name + '.fsck')).write_text(p.stdout)
    # Fail closed: every substantive diagnostic must be a leak or an
    # allocation/free-count discrepancy. In particular no directory-entry,
    # duplicate-name, link-count, i_blocks, or multiply-claimed-block errors.
    allowed = [r'e2fsck .*', r'Pass [1-5]: .*',
               r'\S+: \d+/\d+ files .*', r'\S+: \d+/\d+ files, .*',
               r'.*: \*+ WARNING: Filesystem still has errors \*+',
               r'(Block|Inode) bitmap differences: [ +()\-0-9]+',
               r'Free (blocks|inodes) count wrong( for group #\d+)? \(\d+, counted=\d+\)\.',
               r'Fix\? no', r'Unattached( zero-length)? inode \d+',
               r'Connect to /lost\+found\? no', r'Clear\? no']
    unexpected = [l for l in p.stdout.splitlines() if l.strip() and
                  not any(re.fullmatch(a, l) for a in allowed)]
    row('write-cut-' + name + '-leaks-only', p.returncode in (0, 4) and not unexpected,
        'e2fsck exit %d; unexpected=%r' % (p.returncode, unexpected))


def names(image, name, require_tmp=False):
    listing = debug(image, 'ls -l /bin')
    (leg / (name + '.directory')).write_text(listing)
    entries = re.findall(r'^\s*(\d+)\s+(\d+)\s+\([^)]*\).*?\s(\S+)\s*$', listing, re.M)
    seen = set()
    good = bool(entries)
    found_tmp = False
    for ino, mode, filename in entries:
        if filename in ('.', '..'):
            continue
        if filename in seen:
            good = False
        seen.add(filename)
        st = debug(image, 'stat <' + ino + '>')
        bit = debug(image, 'testi <' + ino + '>')
        (leg / (name + '.inode-' + ino)).write_text(st + bit)
        good = good and int(mode, 8) != 0 and 'is marked in use' in bit
        good = good and bool(re.search(r'Links:\s+[1-9]\d*', st))
        if filename == 'burrowd.pax-tmp':
            found_tmp = True
            size = re.search(r'Size:\s+(\d+)', st)
            good = good and size is not None and int(size[1]) < 16777216
    row('write-cut-' + name + '-names', good and (found_tmp or not require_tmp),
        'no duplicate, zero or unused inode names; temporary present=' + str(found_tmp))


image = leg / 'root.img'
with image.open('wb') as f:
    f.truncate(64 * 1024 * 1024)
p = run(['mke2fs', '-q', '-F', '-t', 'ext2', '-b', '4096', '-I', '256',
         '-O', 'filetype,sparse_super,large_file,^resize_inode,^dir_index,^ext_attr', image])
assert p.returncode == 0, p.stdout
old = leg / 'old'
old.write_text('previous burrowd\n')
debug(image, 'mkdir /bin', True)
debug(image, 'write %s /bin/burrowd' % old, True)
assert run(['e2fsck', '-fn', image]).returncode == 0
symbols = run(['nm', work / 'kernel.elf'], check=True).stdout

def symbol(stem):
    found = re.findall(r'^([0-9a-f]+) T _Wext2\.' + stem + r'\$\S+$', symbols, re.M)
    assert len(found) == 1, (stem, found)
    return int(found[0], 16)

# An ephemeral loopback port, not a shared service or a fixed pool port.
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
serial = leg / 'cut.serial'
pidfile = leg / 'qemu.pid'
args = [repo / 'tools/qemu-run', '--firmware', firmware, '--serial', serial,
        '--timeout', '240', work / 'write-cut.iso', '--', '-m', '1G',
        '-drive', 'file=%s,if=none,id=d0,format=raw' % image,
        '-device', 'virtio-blk-pci,drive=d0', '-gdb', 'tcp:127.0.0.1:%d' % port,
        '-S', '-pidfile', pidfile]
(leg / 'command.json').write_text(json.dumps([str(x) for x in args], indent=2))
trigger = leg / 'trigger.json'
done = leg / 'cut.done'
script = leg / 'cut.gdb'
script.write_text('''set confirm off
set pagination off
set architecture i386:x86-64
file %s
target remote 127.0.0.1:%d
python
import gdb, json, time
from pathlib import Path
wanted = b'burrowd.pax-tmp'
captured = {}
def reg(name): return int(gdb.parse_and_eval('$' + name)) & ((1 << 64) - 1)
class Write(gdb.Breakpoint):
    def stop(self):
        # wspan returns a tuple: rdi is its hidden result pointer.
        if captured and reg('rsi') == captured['volume'] and reg('rdx') == captured['inode'] and reg('rcx') >= 4 * 1024 * 1024:
            captured['offset'] = reg('rcx')
            captured['pc'] = reg('rip')
            Path(%r).write_text(json.dumps(captured))
            return True
        return False
class Add(gdb.Breakpoint):
    def stop(self):
        if reg('rcx') == len(wanted) and bytes(gdb.selected_inferior().read_memory(reg('rdx'), len(wanted))) == wanted:
            captured.update(volume=reg('rdi'), inode=reg('r8'), name=wanted.decode())
            self.enabled = False
        return False
Write('*0x%x', type=gdb.BP_HARDWARE_BREAKPOINT)
Add('*0x%x', type=gdb.BP_HARDWARE_BREAKPOINT)
end
continue
python
# Remain stopped. Exiting/detaching here could resume the guest before
# the harness cuts power and would turn this into a timing-based row.
while not Path(%r).exists(): time.sleep(.1)
end
quit
''' % (work / 'kernel.elf', port, str(trigger), symbol('wspan'), symbol('add'), str(done)))
qlog = (leg / 'runner.log').open('wb')
glog = (leg / 'gdb.log').open('wb')
q = subprocess.Popen([str(x) for x in args], stdout=qlog, stderr=subprocess.STDOUT)
(leg / 'runner.pid').write_text(str(q.pid) + '\n')
g = None
try:
    deadline = time.monotonic() + 220
    while not pidfile.exists():
        assert q.poll() is None, 'QEMU runner stopped before startup'
        assert time.monotonic() < deadline, 'QEMU pidfile timeout'
        time.sleep(.1)
    g = subprocess.Popen(['gdb', '-q', '-nx', '-batch', '-x', str(script)], stdout=glog, stderr=subprocess.STDOUT)
    (leg / 'gdb.pid').write_text(str(g.pid) + '\n')
    next_note = time.monotonic()
    while not trigger.exists():
        assert q.poll() is None and g.poll() is None, 'runner/debugger stopped before the write trigger'
        assert time.monotonic() < deadline, 'write breakpoint timeout'
        if time.monotonic() >= next_note:
            print('write-cut: waiting for burrowd.pax-tmp ext2.wspan at 4 MiB', flush=True)
            next_note = time.monotonic() + 20
        time.sleep(.1)
    observed = json.loads(trigger.read_text())
    assert observed['name'] == 'burrowd.pax-tmp' and observed['offset'] >= 4194304
    # Only this row's QEMU, recorded in its own pidfile at launch.
    qemu_pid = int(pidfile.read_text())
    os.kill(qemu_pid, signal.SIGKILL)
    q.wait(timeout=15)
    done.write_text('power cut while stopped inside ext2.wspan\n')
    g.wait(timeout=15)
    row('write-cut-trigger', True, json.dumps(observed, sort_keys=True))
finally:
    done.touch()
    if q.poll() is None:
        # Our wrapper owns its QEMU and handles TERM by ending and waiting
        # on that one child; no search through the host process table.
        q.terminate()
        q.wait(timeout=15)
    if g is not None and g.poll() is None:
        g.terminate()
        g.wait(timeout=15)
    qlog.close()
    glog.close()

names(image, 'cut', require_tmp=True)
fsck(image, 'cut')
# No repair or image mutation between the cut and this reboot.
resume = leg / 'resume.serial'
p = run([repo / 'tools/qemu-halt', '--firmware', firmware, '--serial', resume,
         '--timeout', '240', '--elf', work / 'kernel.elf', '--marker', 'halt|PANIC .*',
         '--qemu', '-m', '--qemu', '1G', '--qemu', '-drive',
         '--qemu', 'file=%s,if=none,id=d0,format=raw' % image,
         '--qemu', '-device', '--qemu', 'virtio-blk-pci,drive=d0', work / 'write-cut.iso'])
(leg / 'resume.verdict').write_text(p.stdout)
text = resume.read_text(errors='replace')
finished = 'PASS upgrade-replace: /bin/burrowd digest ' in text
stopped = ('pax-install: cannot inspect temporary path /mnt/bin/burrowd.pax-tmp: filesystem damage or I/O error; stop retrying, power off, boot recovery media, leave the target root partition unmounted and run e2fsck -f on it, then retry the upgrade' in text)
row('write-cut-resume', p.returncode == 0 and (finished or stopped),
    'finished=' + str(finished) + ' exact-stop=' + str(stopped))
if finished:
    out = leg / 'burrowd'
    debug(image, 'dump /bin/burrowd %s' % out)
    row('write-cut-replaced-bytes', out.read_bytes() == (work / 'source').read_bytes(), 'replaced file equals source')
names(image, 'resumed')
fsck(image, 'resumed')
# Verify repairability without laundering the cut or resumed verdict.
repaired = leg / 'repair-copy.img'
shutil.copyfile(image, repaired)
p = run(['e2fsck', '-fy', repaired])
(leg / 'repair.fsck').write_text(p.stdout)
check = run(['e2fsck', '-fn', repaired])
(leg / 'repaired.fsck').write_text(check.stdout)
row('write-cut-repair-clean', p.returncode in (0, 1) and check.returncode == 0,
    'repair copy: -fy exit %d, -fn exit %d' % (p.returncode, check.returncode))
stats = debug(image, 'stats')
row('write-cut-unclean-preserved', bool(re.search(r'Filesystem state:\s+not clean', stats)),
    'unclean cut root was not marked clean on resumed unmount')
sys.exit(1 if failed else 0)
