#!/usr/bin/env python3
"""An installed ext3 root cut by power mid-write, replayed by PAX and by Linux's e2fsck.

  powercut.py WORK FIRMWARE [IMAGE] [--flushcut]

On a lane-owned copy of the installed disk (session.py's way: the target
alone, QEMU's monitor, no host signals): the first boot starts a shell loop
that creates files in /root, and after COMMITS seconds (the flusher commits
every 5 s) QEMU is stopped by its monitor's `quit`, mid-loop: a power cut,
nothing flushed by the guest. Rows (each failure is one `FAIL` line; every
row runs whatever an earlier one said, and the exit is 1 if any failed):

  I-ext3-powercut-<firmware>  The cut root needs recovery (needs_recovery,
      a nonzero journal start: committed transactions in the log). The
      second boot says PAX recovered them, then halts cleanly; Linux's
      `e2fsck -fn` finds the root clean, and dumpe2fs says it is clean with
      the log empty.
  I-ext3-powercut-e2fsck-<firmware>  On two copies of the same cut root,
      Linux replays the log itself: `e2fsck -fy -E journal_only` replays it
      and nothing more, and `e2fsck -fy` replays it and checks everything.
      Both exit 0 or 1, `e2fsck -fn` is clean after, and the two roots are
      byte-identical apart from the primary superblock's write and check
      times, mount count, state, free counts and kbytes written, and the
      backup superblock and descriptor copies: the full check found nothing
      to change beyond the journal's own recovery.
  I-ext3-flushcut-<firmware> (with --flushcut)  A boot on a disk that keeps
      only what the guest flushed (flushdisk.py: QEMU reaches a copy through
      an NBD server that holds every write until a FLUSH and records each
      FLUSH's writes): the shell creates FILES files in /root and exits, so
      the root is unmounted (the last commit and the checkpoint) and the
      machine halts. Every durable point of that boot is then a power cut
      that lost everything not yet flushed: the root as it was, plus the
      flushes up to that point. Each such root must need no more than the
      log: `e2fsck -fn` clean where the log is empty, and where it is not,
      Linux's replay pair above. PAX's own replay boot then runs on the last
      of them whose log holds committed transactions (journal start nonzero). And what a cut kept, every later cut
      keeps: the loop's files in /root (debugfs, after Linux's replay) never
      fall from one durable point to the next, and all FILES are there at
      the end; a log emptied before its blocks reached home loses them. A
      monitor `quit` loses nothing QEMU
      already wrote; these cuts lose everything the guest had not flushed,
      so a missing or misplaced flush shows.
"""
from pathlib import Path
import json
import os
import re
import runpy
import socket
import subprocess
import sys
import threading
import time

args = [a for a in sys.argv[1:] if a != '--flushcut']
flushcut = '--flushcut' in sys.argv[1:]
work = Path(args[0])
firmware = args[1]
source = Path(args[2]) if len(args) > 2 else work / 'target.img'
ROOT_START = 69206016
COMMITS = 12  # seconds of the loop before the cut: two flusher turns at least
LOOP = 'n=0; while :; do echo "cut $n" > /root/cut-$n; n=$((n+1)); done'
FILES = 3000  # the flush cut's files: a few commits under TCG, then the unmount's checkpoint
# Primary superblock fields a full check may write that a journal-only
# replay does not (ext2-doc table 3.3): free blocks and inodes, write time,
# mount count, state, last check, kbytes written.
SB_ALLOWED = [(12, 4, 'free blocks'), (16, 4, 'free inodes'), (48, 4, 'write time'), (52, 2, 'mount count'),
              (58, 2, 'state'), (64, 4, 'last check'), (376, 8, 'kbytes written')]
failed = []


class RowFail(Exception):
    pass


def fail(why):
    raise RowFail(why)


def verdict(row, body):
    try:
        text = body()
        print(f'PASS {row}: {text}', flush=True)
    except RowFail as e:
        failed.append(row)
        print(f'FAIL {row}: {e}', flush=True)


def copy(src, dst):
    subprocess.run(['cp', '--sparse=always', str(src), str(dst)], check=True)
    return dst


def root_bytes(disk):
    # The installed root's length: the GPT's partition 2 (sfdisk --json's sectors).
    out = subprocess.run(['sfdisk', '--json', str(disk)], capture_output=True, check=True).stdout
    parts = [x for x in json.loads(out)['partitiontable']['partitions'] if int(x['start']) == ROOT_START // 512]
    if len(parts) != 1:
        fail(f'no partition 2 at byte {ROOT_START}: ' + out.decode(errors='replace')[-400:])
    return int(parts[0]['size']) * 512


def extract(disk, name):
    out = work / name
    left = root_bytes(disk)
    with disk.open('rb') as f, out.open('wb') as o:
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


def file_drive(disk):
    return ['-drive', f'file={disk},if=none,id=d0,format=raw',
            '-device', 'virtio-blk-pci,drive=d0,bootindex=0,serial=PX71-ROOT']


def boot(tag, drive, steps, until, seconds, cut=None):
    """Boot the disk alone; steps: (prompt count, line) typed at the shell's
    `$ `; then wait for `until` (bytes regex), or `seconds` and then `cut()`
    (which returns an error or None); then quit by the monitor."""
    log = work / f'powercut-{firmware}-{tag}.serial'
    mon = str(work / f'powercut-{firmware}-{tag}.mon')
    if os.path.exists(mon):
        os.unlink(mon)
    cmd = ['qemu-system-x86_64', '-machine', 'q35,accel=tcg', '-cpu', 'max', '-smp', '4', '-m', '512M',
           '-display', 'none', '-serial', 'stdio', '-monitor', 'unix:' + mon + ',server=on,wait=off', '-nic', 'none', *drive]
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
            if cut is not None:
                err = cut()
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


def mounted_ext3(first):
    if not re.search(r'^root: PARTUUID=[0-9a-fA-F-]+ \(vda2\) on /: ext3, read-write, data=ordered$', first, re.M):
        fail('the first boot did not mount an ext3 root read-write:\n' + first[-2000:])


def cut_state(root, tag):
    """dumpe2fs and an unreplayed e2fsck -fn of the cut root: (needs recovery, journal start, e2fsck's exit)."""
    h = subprocess.run(['dumpe2fs', '-h', str(root)], capture_output=True)
    (work / f'powercut-{firmware}-{tag}.dumpe2fs').write_bytes(h.stdout + h.stderr)
    features = re.search(rb'^Filesystem features:(.*)$', h.stdout, re.M)
    start = re.search(rb'^Journal start:\s+(\d+)$', h.stdout, re.M)
    if not features or not start:
        fail('dumpe2fs names no features or journal start: ' + h.stdout.decode(errors='replace')[-1500:])
    before = subprocess.run(['e2fsck', '-fn', str(root)], capture_output=True)
    (work / f'powercut-{firmware}-{tag}.fsck').write_bytes(before.stdout + before.stderr)
    return b'needs_recovery' in features[1], int(start[1]), before.returncode


def has_super(g, sparse):
    if not sparse or g in (0, 1):
        return True
    for p in (3, 5, 7):
        n = g
        while n % p == 0:
            n //= p
        if n == 1:
            return True
    return False


def compare(a, b):
    """(byte, block) pairs where two roots differ outside the allowed primary
    superblock fields and the backup superblock and descriptor copies; and
    the allowed fields that do differ."""
    with a.open('rb') as f:
        f.seek(1024)
        sb = f.read(1024)
    u = lambda at, w=4: int.from_bytes(sb[at:at + w], 'little')
    bs, blocks, first, bpg = 1024 << u(24), u(4), u(20), u(32)
    groups = (blocks - first + bpg - 1) // bpg
    gdt = (groups * 32 + bs - 1) // bs
    skip = [((first + g * bpg) * bs, (first + g * bpg + 1 + gdt) * bs)
            for g in range(1, groups) if has_super(g, u(100) & 1)]
    allowed = [(1024 + at, 1024 + at + width, name) for at, width, name in SB_ALLOWED]
    unexpected, fields = [], set()
    with a.open('rb') as fa, b.open('rb') as fb:
        offset = 0
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if not x and not y:
                break
            if len(x) != len(y):
                unexpected.append(('length', offset + min(len(x), len(y))))
                break
            if x != y:
                for i in range(len(x)):
                    if x[i] == y[i]:
                        continue
                    at = offset + i
                    if any(lo <= at < hi for lo, hi in skip):
                        continue
                    hit = [name for lo, hi, name in allowed if lo <= at < hi]
                    if hit:
                        fields.add(hit[0])
                    elif len(unexpected) < 16:
                        unexpected.append((at, at // bs))
            offset += len(x)
    return unexpected, sorted(fields)


def files_in_root(img):
    """The loop's files in /root, as debugfs (read-only) lists them."""
    r = subprocess.run(['debugfs', '-R', 'ls -p /root', str(img)], capture_output=True)
    if r.returncode != 0:
        fail(f'debugfs ls /root exit {r.returncode}: ' + (r.stdout + r.stderr).decode(errors='replace')[-600:])
    return sum(1 for line in r.stdout.decode(errors='replace').splitlines()
               if re.match(r'^/\d+/\d+/\d+/\d+/cut-\d+/', line))


def linux_replay(root, tag, inspect=None):
    """Linux's journal-only replay against its full repair, on copies of the cut root;
    inspect(the journal-only root), when given, is returned beside the summary."""
    only = copy(root, work / f'powercut-{firmware}-{tag}-journal-only.img')
    full = copy(root, work / f'powercut-{firmware}-{tag}-e2fsck-y.img')
    try:
        j = subprocess.run(['e2fsck', '-fy', '-E', 'journal_only', str(only)], capture_output=True)
        y = subprocess.run(['e2fsck', '-fy', str(full)], capture_output=True)
        n = subprocess.run(['e2fsck', '-fn', str(full)], capture_output=True)
        for name, r in [('journal-only', j), ('e2fsck-y', y), ('e2fsck-n', n)]:
            (work / f'powercut-{firmware}-{tag}-{name}.log').write_bytes(r.stdout + r.stderr)
        if j.returncode not in (0, 1):
            fail(f'e2fsck -fy -E journal_only exit {j.returncode}: ' + (j.stdout + j.stderr).decode(errors='replace')[-1500:])
        if y.returncode not in (0, 1):
            fail(f'e2fsck -fy exit {y.returncode}: ' + (y.stdout + y.stderr).decode(errors='replace')[-1500:])
        if n.returncode != 0 or b'WARNING' in n.stdout + n.stderr:
            fail(f'e2fsck -fn after e2fsck -fy: exit {n.returncode}\n' + (n.stdout + n.stderr).decode(errors='replace')[-1500:])
        unexpected, fields = compare(only, full)
        if unexpected:
            fail(f'e2fsck -fy changed more than the journal-only replay, at (byte, block) {unexpected}; its output:\n'
                 + (y.stdout + y.stderr).decode(errors='replace')[-1500:])
        recovered = b'recovering journal' in j.stdout + j.stderr
        text = (f'e2fsck -fy -E journal_only exit {j.returncode} ({"replayed the log" if recovered else "nothing to replay"}), '
                f'e2fsck -fy exit {y.returncode}, e2fsck -fn clean; the full check changed only {fields or "nothing"} '
                f'beyond the replay')
        return (text, inspect(only)) if inspect else text
    finally:
        only.unlink(missing_ok=True)
        full.unlink(missing_ok=True)


def pax_replay(disk, tag, recovery):
    """PAX's next boot mounts the cut root (recovering the log when it must), then halts; e2fsck -fn clean, log empty."""
    second = boot(tag, file_drive(disk), [(1, 'cat /proc/self/mounts'), (2, 'exit')], rb'\r?\nhalt\r?\n', None)
    m = re.search(r'ext2: vda2: recovering the journal: (\d+) transactions? (?:\(sequence (\d+) to (\d+)\), )?(\d+) blocks written home, (\d+) revoked; recovery complete', second)
    if recovery and (not m or int(m[1]) < 1):
        fail('the second boot did not recover the journal:\n' + second[-3000:])
    if '/dev/root / ext3 rw,relatime 0 0' not in second:
        fail('the replayed root is not mounted ext3:\n' + second[-2000:])
    after = extract(disk, f'powercut-{firmware}-{tag}-root.img')
    try:
        check = subprocess.run(['e2fsck', '-fn', str(after)], capture_output=True)
        (work / f'powercut-{firmware}-{tag}.fsck').write_bytes(check.stdout + check.stderr)
        h = subprocess.run(['dumpe2fs', '-h', str(after)], capture_output=True)
        (work / f'powercut-{firmware}-{tag}.dumpe2fs').write_bytes(h.stdout + h.stderr)
        if check.returncode != 0 or b'WARNING' in check.stdout + check.stderr:
            fail(f'e2fsck -fn after the replay: exit {check.returncode}\n' + (check.stdout + check.stderr).decode(errors='replace')[-2000:])
        if not re.search(rb'^Filesystem state:\s+clean$', h.stdout, re.M) or not re.search(rb'^Journal start:\s+0$', h.stdout, re.M) \
                or b'needs_recovery' in (re.search(rb'^Filesystem features:(.*)$', h.stdout, re.M) or [b'', b''])[1]:
            fail('after the replay and halt the root is not clean with an empty log:\n' + h.stdout.decode(errors='replace')[-1500:])
    finally:
        after.unlink(missing_ok=True)
    return (f'PAX recovered {m[1]} transaction(s), {m[4]} blocks home' if m else 'PAX mounted it with nothing to recover') + \
        '; halted; e2fsck -fn clean, the log empty'


# The monitor cut: a loop of file creations in /root (each an inode, a directory
# entry and both bitmaps: journalled metadata), stopped COMMITS seconds in.
image = copy(source, work / f'powercut-{firmware}.img')
state = {}


def monitor_cut_linux():
    first = boot('cut', file_drive(image), [(1, LOOP)], None, COMMITS)
    mounted_ext3(first)
    root = extract(image, f'powercut-{firmware}-cut-root.img')
    try:
        state['needs'], state['start'], state['before'] = cut_state(root, 'cut')
        return linux_replay(root, 'cut')
    finally:
        root.unlink(missing_ok=True)


def monitor_cut_pax():
    if 'needs' not in state:
        fail('no cut root to replay (the e2fsck row says why)')
    if not state['needs'] or state['start'] == 0:
        fail(f'the cut root holds no committed transaction to replay (needs_recovery {state["needs"]}, '
             f'journal start {state["start"]})')
    text = pax_replay(image, 'replay', True)
    return (f'cut {COMMITS} s into a file-creating loop: needs_recovery, journal start {state["start"]}; '
            f'e2fsck -fn on the cut root exit {state["before"]} (unreplayed); ' + text)


verdict(f'I-ext3-powercut-e2fsck-{firmware}', monitor_cut_linux)
verdict(f'I-ext3-powercut-{firmware}', monitor_cut_pax)
image.unlink(missing_ok=True)


def flush_cut():
    disk = copy(source, work / f'flushcut-{firmware}.img')
    sock = work / f'flushcut-{firmware}.sock'
    root = work / f'flushcut-{firmware}-root.img'
    full = work / f'flushcut-{firmware}-replay.img'
    try:
        held = runpy.run_path(str(Path(__file__).resolve().with_name('flushdisk.py')))['FlushDisk'](disk, sock)
        held.start()
        drive = ['-blockdev', f'driver=nbd,node-name=n0,server.type=unix,server.path={sock}',
                 '-blockdev', 'driver=raw,node-name=d0,file=n0',
                 '-device', 'virtio-blk-pci,drive=d0,write-cache=on,bootindex=0,serial=PX71-ROOT']
        create = f'n=0; while [ $n -lt {FILES} ]; do echo "cut $n" > /root/cut-$n; n=$((n+1)); done; exit'
        first = boot('flushcut', drive, [(1, create)], rb'\r?\nhalt\r?\n', None)
        held.join(timeout=30)
        if held.error:
            fail('the flush-keeping disk failed: ' + held.error)
        mounted_ext3(first)
        s = held.stats
        if s['flushes_with_data'] < 1:
            fail(f'no FLUSH carried a write: {s}')
        # Every durable point, oldest first, on the root as it was before the boot.
        extract(source, root.name)
        size = root.stat().st_size
        checked = recovering = 0
        last_logged = None
        kept, kept_at = None, None
        with root.open('r+b') as f:
            for k, epoch in enumerate(held.epochs):
                touched = False
                for sector, data in epoch:
                    at = sector * 512 - ROOT_START
                    if 0 <= at < size:
                        f.seek(at)
                        f.write(data)
                        touched = True
                if not touched:
                    continue
                f.flush()
                needs, start, plain = cut_state(root, f'flushcut-{k}')
                checked += 1
                try:
                    if needs:
                        recovering += 1
                        if start != 0:
                            last_logged = k  # committed transactions in the log, not only the flag
                        _, count = linux_replay(root, f'flushcut-{k}', files_in_root)
                    elif plain != 0:
                        fail(f'e2fsck -fn exit {plain} on a root whose log is empty; see powercut-{firmware}-flushcut-{k}.fsck')
                    else:
                        count = files_in_root(root)
                    # What a cut kept, a later cut keeps: a commit made durable stays.
                    if kept is not None and count < kept:
                        fail(f'it keeps {count} of the loop\'s files; the cut after durable point {kept_at} kept {kept}')
                    kept, kept_at = count, k
                except RowFail as e:
                    fail(f'the cut after durable point {k} of {len(held.epochs)} '
                         f'(needs_recovery {needs}, journal start {start}): {e}')
        if last_logged is None:
            fail(f'no durable point left committed transactions in the log ({checked} roots checked): {s}')
        if kept != FILES:
            fail(f'after the halt the root holds {kept} of the {FILES} files the shell made')
        # PAX's replay of the last root whose log holds transactions (a root may carry
        # needs_recovery with the log already empty, between the checkpoint's FLUSH and
        # the flag's: its replay is 0 transactions), booted from the whole disk as it was then.
        copy(source, full)
        with full.open('r+b') as f:
            for epoch in held.epochs[:last_logged + 1]:
                for sector, data in epoch:
                    f.seek(sector * 512)
                    f.write(data)
        pax = pax_replay(full, 'flushcut-replay', True)
        return (f'{s["writes"]} writes, {s["flushes"]} flushes ({s["flushes_with_data"]} with data), '
                f'{s["fua_writes"]} FUA, {s["held_at_close"]} sectors held at the close; {checked} cut roots checked, '
                f'{recovering} needing the log (Linux replayed each and changed nothing else), the rest e2fsck -fn clean; '
                f'the files kept never fell, {FILES} at the end; '
                f'PAX at durable point {last_logged}: {pax}')
    finally:
        for path in (disk, sock, root, full):
            path.unlink(missing_ok=True)


if flushcut:
    verdict(f'I-ext3-flushcut-{firmware}', flush_cut)
sys.exit(1 if failed else 0)
