#!/usr/bin/env python3
"""An installed ext3 root cut by power mid-write, replayed by PAX, held to Linux's e2fsck.

  powercut.py WORK FIRMWARE [IMAGE]

On a lane-owned copy of the installed disk (session.py's way: the target
alone, QEMU's monitor, no host signals): the first boot starts a shell loop
that creates files in /root, and after COMMITS seconds (the flusher commits
every 5 s) QEMU is stopped by its monitor's `quit`, mid-loop: a power cut,
nothing flushed by the guest. The cut root must need recovery (needs_recovery,
a nonzero journal start: committed transactions in the log). The second boot
must say PAX recovered them, then halt cleanly; Linux's `e2fsck -fn` then
finds the root clean, and dumpe2fs says it is clean with the log empty.
Rows: I-ext3-powercut-<firmware>; each failure is one `FAIL` line.
"""
from pathlib import Path
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

work = Path(sys.argv[1])
firmware = sys.argv[2]
source = Path(sys.argv[3]) if len(sys.argv) > 3 else work / 'target.img'
row = f'I-ext3-powercut-{firmware}'
ROOT_START = 69206016
COMMITS = 12  # seconds of the loop before the cut: two flusher turns at least
image = work / f'powercut-{firmware}.img'
subprocess.run(['cp', '--sparse=always', str(source), str(image)], check=True)


def fail(why):
    print(f'FAIL {row}: {why}', flush=True)
    sys.exit(1)


def root_bytes():
    # The installed root's length: the GPT's partition 2 (sfdisk --json's sectors).
    out = subprocess.run(['sfdisk', '--json', str(image)], capture_output=True, check=True).stdout
    parts = [x for x in json.loads(out)['partitiontable']['partitions'] if int(x['start']) == ROOT_START // 512]
    if len(parts) != 1:
        fail(f'no partition 2 at byte {ROOT_START}: ' + out.decode(errors='replace')[-400:])
    return int(parts[0]['size']) * 512


def extract(name):
    out = work / name
    left = root_bytes()
    with image.open('rb') as f, out.open('wb') as o:
        f.seek(ROOT_START)
        o.truncate(left)
        offset = 0
        while left:
            b = f.read(min(left, 1048576))
            if not b:
                fail('short read of the root partition')
            if b.count(0) != len(b):
                o.seek(offset)
                o.write(b)
            offset += len(b)
            left -= len(b)
    return out


def boot(tag, steps, until, seconds):
    """Boot the disk alone; steps: (prompt count, line) typed at the shell's
    `$ `; then wait for `until` (bytes regex) or `seconds`; then quit by the monitor."""
    log = work / f'powercut-{firmware}-{tag}.serial'
    mon = str(work / f'powercut-{firmware}-{tag}.mon')
    if os.path.exists(mon):
        os.unlink(mon)
    cmd = ['qemu-system-x86_64', '-machine', 'q35,accel=tcg', '-cpu', 'max', '-smp', '4', '-m', '512M',
           '-display', 'none', '-serial', 'stdio', '-monitor', 'unix:' + mon + ',server=on,wait=off', '-nic', 'none',
           '-drive', f'file={image},if=none,id=d0,format=raw', '-device', 'virtio-blk-pci,drive=d0,bootindex=0,serial=PX71-ROOT']
    if firmware == 'uefi':
        cmd += ['-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=' + os.environ.get('PAX_OVMF_CODE', '/usr/share/OVMF/OVMF_CODE_4M.fd')]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    buf = bytearray()
    lock = threading.Lock()
    out = log.open('wb')

    def reader():
        for b in iter(lambda: p.stdout.read1(8192), b''):
            with lock:
                buf.extend(b)
            out.write(b)
            out.flush()
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def text():
        with lock:
            return bytes(buf)

    def wait(predicate, what, limit=300):
        end = time.monotonic() + limit
        while not predicate(text()):
            if p.poll() is not None:
                raise RuntimeError('QEMU exited: ' + what)
            if time.monotonic() > end:
                raise RuntimeError('timeout: ' + what + '\n' + text()[-3000:].decode(errors='replace'))
            time.sleep(.1)
    err = None
    try:
        for n, line in steps:
            wait(lambda s: s.split(b'PAX: the console')[-1].count(b'$ ') >= n and b'PAX: the console' in s, f'{tag} prompt {n}')
            for ch in line.encode():
                p.stdin.write(bytes([ch]))
                p.stdin.flush()
                time.sleep(.01)
            p.stdin.write(b'\r')
            p.stdin.flush()
        if until is not None:
            wait(lambda s: re.search(until, s.split(b'PAX: the console')[-1]) is not None, f'{tag} end')
        else:
            time.sleep(seconds)
    except RuntimeError as e:
        err = str(e)
    finally:
        # The monitor's quit stops the machine where it is: no guest flush, a power cut.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
            monitor.settimeout(10)
            monitor.connect(mon)
            greeting = bytearray()
            while b'(qemu)' not in greeting:
                greeting.extend(monitor.recv(4096))
            monitor.sendall(b'quit\n')
            while monitor.recv(4096):
                pass
        p.wait(timeout=10)
        thread.join(timeout=5)
        out.close()
    if err:
        fail(err)
    s = log.read_text(errors='replace').replace('\r', '')
    return re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', s)


# The cut: a loop of file creations in /root (each an inode, a directory entry and
# both bitmaps: journalled metadata), stopped COMMITS seconds in.
first = boot('cut', [(1, 'n=0; while :; do echo "cut $n" > /root/cut-$n; n=$((n+1)); done')], None, COMMITS)
if not re.search(r'^root: PARTUUID=[0-9a-fA-F-]+ \(vda2\) on /: ext3, read-write, data=ordered$', first, re.M):
    fail('the first boot did not mount an ext3 root read-write:\n' + first[-2000:])
cut = extract(f'powercut-{firmware}-cut-root.img')
h = subprocess.run(['dumpe2fs', '-h', str(cut)], capture_output=True)
(work / f'powercut-{firmware}-cut.dumpe2fs').write_bytes(h.stdout + h.stderr)
features = re.search(rb'^Filesystem features:(.*)$', h.stdout, re.M)
start = re.search(rb'^Journal start:\s+(\d+)$', h.stdout, re.M)
if not features or b'needs_recovery' not in features[1] or not start or int(start[1]) == 0:
    fail('the cut root holds no committed transaction to replay (needs_recovery and a nonzero journal start): '
         + h.stdout.decode(errors='replace')[-1500:])
before = subprocess.run(['e2fsck', '-fn', str(cut)], capture_output=True)
(work / f'powercut-{firmware}-cut.fsck').write_bytes(before.stdout + before.stderr)
cut.unlink()
# The replay: PAX's own mount recovers the journal, then the shell's exit halts cleanly.
second = boot('replay', [(1, 'cat /proc/self/mounts'), (2, 'exit')], rb'\r?\nhalt\r?\n', None)
m = re.search(r'ext2: vda2: recovering the journal: (\d+) transactions? (?:\(sequence (\d+) to (\d+)\), )?(\d+) blocks written home, (\d+) revoked; recovery complete', second)
if not m or int(m[1]) < 1:
    fail('the second boot did not recover the journal:\n' + second[-3000:])
if '/dev/root / ext3 rw,relatime 0 0' not in second:
    fail('the replayed root is not mounted ext3:\n' + second[-2000:])
after = extract(f'powercut-{firmware}-after-root.img')
check = subprocess.run(['e2fsck', '-fn', str(after)], capture_output=True)
(work / f'powercut-{firmware}-after.fsck').write_bytes(check.stdout + check.stderr)
h = subprocess.run(['dumpe2fs', '-h', str(after)], capture_output=True)
(work / f'powercut-{firmware}-after.dumpe2fs').write_bytes(h.stdout + h.stderr)
if check.returncode != 0 or b'WARNING' in check.stdout + check.stderr:
    fail(f'e2fsck -fn after the replay: exit {check.returncode}\n' + (check.stdout + check.stderr).decode(errors='replace')[-2000:])
if not re.search(rb'^Filesystem state:\s+clean$', h.stdout, re.M) or not re.search(rb'^Journal start:\s+0$', h.stdout, re.M) \
        or b'needs_recovery' in (re.search(rb'^Filesystem features:(.*)$', h.stdout, re.M) or [b'', b''])[1]:
    fail('after the replay and halt the root is not clean with an empty log:\n' + h.stdout.decode(errors='replace')[-1500:])
after.unlink()
image.unlink()
print(f'PASS {row}: cut {COMMITS} s into a file-creating loop: needs_recovery, journal start {int(start[1])}; '
      f'e2fsck -fn on the cut root exit {before.returncode} (unreplayed); PAX recovered {m[1]} transaction(s), '
      f'{m[4]} blocks home; halted; e2fsck -fn clean, the log empty', flush=True)
