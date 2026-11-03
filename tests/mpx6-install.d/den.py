#!/usr/bin/env python3
"""px90: den's repository across a reboot of the installed system.

Usage: den.py WORK FIRMWARE DISK.img

DISK.img is a disk pax-install wrote (tests/distribution-install's
installed.img: the install from the rebuilt medium). A lane-owned sparse
copy is booted alone, as session.py boots its target: QEMU's monitor ends
it, no host signal. Boot 1, at the installed console's root shell: the
pinned environment (user/console/den.keys' first lines), `den init`,
`add`, `commit`, then `reboot`. Boot 2: `den log`, `den fsck --full`,
`git log --oneline` and `den status --porcelain`, then `exit` (every
volume written, `/` marked clean, the machine halted).

On the host, with no guest help: the root partition (GPT 2) is checked
by `e2fsck -fn`; /bin/den and the repository are read back from it with
debugfs; the same steps run on Linux with that same den binary under the
same environment, in a directory of WORK. Held:
  P1 boot 1's three den commands exit 0 and the reboot completes;
  P2 boot 2's `den log` is Linux's byte for byte and exits 0; `den fsck
     --full` exits 0 with nothing on either stream; `git log --oneline`
     is den's own `log --oneline` on Linux; the worktree is clean;
  P3 the disk is clean and mounted twice; every object file of the
     repository on the disk is byte-identical to Linux's (the same paths,
     the same bytes), and its HEAD and refs/heads/main are Linux's.
Prints PASS lines and exits 0; a failed row is `FAIL <row> …` and exit 1.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time

work, firmware, disk = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
work.mkdir(parents=True, exist_ok=True)
fails = []

def fail(row, why):
    fails.append(row)
    print(f'FAIL {row} {firmware}: {why}', flush=True)

REPO = '/root/den-persist'
# The pinned environment: den.keys' lines before its session, but the
# helper `s` and the session's directory.
KEYS = (Path(__file__).resolve().parents[2] / 'user/console/den.keys').read_text().splitlines()
SETUP = [l for l in KEYS[:KEYS.index('echo den-session-begin')] if not l.startswith(('s() ', 'W='))]
BOOT1 = ['mkdir -p ' + REPO, 'cd ' + REPO, 'den init -q . ; echo PX90-INIT=$?',
         "printf 'persisted on PAX\\n' > notes.txt", 'den add notes.txt; echo PX90-ADD=$?',
         "den commit -q -m 'written before the reboot'; echo PX90-COMMIT=$?", 'cd /', 'reboot']
# At the console den's log is written to a terminal, where den draws no
# decorations yet and says so: --no-decorate, as the README tells a user.
BOOT2 = ['cd ' + REPO, 'echo PX90-LOG-BEGIN', 'den log --no-decorate; echo PX90-LOG=$?', 'echo PX90-LOG-END',
         'den fsck --full > /tmp/f.o 2> /tmp/f.e; echo PX90-FSCK=$?', 'cat /tmp/f.o /tmp/f.e; echo PX90-FSCK-END',
         'echo PX90-ONELINE-BEGIN', 'git log --oneline --no-decorate', 'echo PX90-ONELINE-END',
         'den status --porcelain; echo PX90-STATUS=$?', 'cd /', 'exit']

image = work / f'den-{firmware}.img'
log = work / f'den-{firmware}.serial'
subprocess.run(['cp', '--sparse=always', str(disk), str(image)], check=True)
mon = str(work / f'den-{firmware}.mon')
if os.path.exists(mon):
    os.unlink(mon)
accel = 'kvm:tcg' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg'
cmd = ['qemu-system-x86_64', '-machine', 'q35,accel=' + accel, '-cpu', 'max', '-smp', '4', '-m', '1024M',
       '-display', 'none', '-serial', 'stdio', '-monitor', 'unix:' + mon + ',server=on,wait=off', '-nic', 'none',
       '-drive', f'file={image},if=none,id=d0,format=raw', '-device', 'virtio-blk-pci,drive=d0,bootindex=0']
if firmware == 'uefi':
    cmd += ['-drive', 'if=pflash,format=raw,unit=0,readonly=on,file=' + os.environ.get('PAX_OVMF_CODE', '/usr/share/OVMF/OVMF_CODE_4M.fd')]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
buf = bytearray(); lock = threading.Lock(); out = log.open('wb')

def reader():
    for b in iter(lambda: p.stdout.read1(8192), b''):
        with lock:
            buf.extend(b)
        out.write(b); out.flush()

thread = threading.Thread(target=reader, daemon=True); thread.start()

def text():
    with lock:
        return bytes(buf)

def wait(predicate, what, seconds=600):
    end = time.monotonic() + seconds
    while not predicate(text()):
        assert p.poll() is None, 'QEMU exited: ' + what
        assert time.monotonic() < end, 'timeout ' + what + '\n' + text()[-4000:].decode(errors='replace')
        time.sleep(.1)

def prompt(boot, n):
    wait(lambda s: len(s.split(b'PAX: the console')) > boot and s.split(b'PAX: the console')[boot].count(b'$ ') >= n,
         f'boot {boot} prompt {n}')

def send(s):
    for b in s.encode():
        p.stdin.write(bytes([b])); p.stdin.flush(); time.sleep(.01)
    p.stdin.write(b'\r'); p.stdin.flush()

try:
    for boot, lines in ((1, SETUP + BOOT1), (2, SETUP + BOOT2)):
        for i, line in enumerate(lines, 1):
            assert '$ ' not in line, line
            prompt(boot, i); send(line)
        if boot == 1:
            wait(lambda s: b'marked clean; restarting' in s, 'reboot completed')
    wait(lambda s: re.search(rb'\r?\nhalt\r?\n', s.split(b'PAX: the console')[-1]) is not None, 'clean halt')
except AssertionError as e:
    fail('P1', 'the sessions did not finish: ' + str(e)[:600])
finally:
    # The monitor is a control protocol of this child, not a host signal.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
        monitor.settimeout(10)
        monitor.connect(mon)
        greeting = bytearray()
        while b'(qemu)' not in greeting:
            greeting.extend(monitor.recv(4096))
        monitor.sendall(b'quit\n')
        while monitor.recv(4096):
            pass
    p.wait(timeout=10); thread.join(timeout=5); out.close()

s = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', log.read_text(errors='replace').replace('\r', ''))
boots = s.split('PAX: the console')[1:]
if len(boots) != 2:
    fail('P1', f'{len(boots)} boots in the serial log, not 2')
    boots += ['', '']
lines1, lines2 = boots[0].splitlines(), boots[1].splitlines()
for word in ('PX90-INIT=0', 'PX90-ADD=0', 'PX90-COMMIT=0'):
    if word not in lines1:
        fail('P1', f'boot 1 has no {word}')
if 'marked clean; restarting' not in boots[0]:
    fail('P1', 'boot 1 did not restart clean')
if not fails:
    print(f'PASS P1 {firmware}: den init, add and commit on the installed system, exit 0; the reboot marked / clean', flush=True)

def between(lines, a, b):
    try:
        i = lines.index(a); j = lines.index(b, i + 1)
    except ValueError:
        return None
    # The typed command line's echo follows the prompt, and the console's
    # CR-LF puts an empty line after it: drop both, keep every other line.
    out, skip = [], False
    for l in lines[i + 1:j]:
        if l.startswith('$ '):
            skip = True
            continue
        if skip and l == '':
            skip = False
            continue
        skip = False
        out.append(l)
    return out

# The same steps on Linux, with the den the disk carries.
root = work / f'den-{firmware}-root.img'
with image.open('rb') as f:
    f.seek(512); h = f.read(512)
    lba, width = struct.unpack_from('<Q', h, 72)[0], struct.unpack_from('<I', h, 84)[0]
    f.seek(lba * 512 + width); start, end = struct.unpack_from('<QQ', f.read(width), 32)
    f.seek(start * 512)
    with root.open('wb') as o:
        left = (end - start + 1) * 512
        while left:
            b = f.read(min(left, 1 << 20)); assert b; o.write(b); left -= len(b)
r = subprocess.run(['e2fsck', '-fn', str(root)], capture_output=True)
(work / f'den-{firmware}.fsck').write_bytes(r.stdout + r.stderr)
dump = work / f'den-{firmware}-disk'
shutil.rmtree(dump, ignore_errors=True); dump.mkdir()
subprocess.run(['debugfs', '-R', f'rdump {REPO} {dump}', str(root)], capture_output=True)
subprocess.run(['debugfs', '-R', f'dump -p /bin/den {dump}/den', str(root)], capture_output=True)
den = dump / 'den'
den.chmod(0o755)  # debugfs's dump keeps the owner's bits only with -p, and only as root
lin = work / f'den-{firmware}-linux'
shutil.rmtree(lin, ignore_errors=True); (lin / 'home').mkdir(parents=True); (lin / 'xdg').mkdir(); (lin / 'hooks').mkdir(); (lin / 'template').mkdir()
# The guest's config, with this side's own (empty) hooks and template.
(lin / 'gitconfig').write_text('[user]\n\tname = Den Tester\n\temail = den@example.invalid\n[color]\n\tui = never\n'
                               f'[core]\n\tpager = cat\n\thooksPath = {lin}/hooks\n[init]\n\tdefaultBranch = main\n'
                               f'\ttemplateDir = {lin}/template\n[commit]\n\tgpgsign = false\n')
env = {'LC_ALL': 'C', 'TZ': 'UTC', 'PATH': '/usr/bin:/bin', 'COLUMNS': '80', 'HOME': str(lin / 'home'),
       'XDG_CONFIG_HOME': str(lin / 'xdg'), 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(lin / 'gitconfig'),
       'GIT_EDITOR': 'false', 'GIT_PAGER': 'cat', 'PAGER': 'cat', 'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_AUTHOR_DATE': '1700000060 +0000', 'GIT_COMMITTER_DATE': '1700000060 +0000'}
repo = lin / 'den-persist'
repo.mkdir()
def den_run(*args):
    return subprocess.run([str(den), *args], cwd=repo, env=env, capture_output=True, umask=0o022)
lsteps = [den_run('init', '-q', '.')]
(repo / 'notes.txt').write_text('persisted on PAX\n')
lsteps += [den_run('add', 'notes.txt'), den_run('commit', '-q', '-m', 'written before the reboot')]
llog, lfsck, lone = den_run('log', '--no-decorate'), den_run('fsck', '--full'), den_run('log', '--oneline', '--no-decorate')
if any(x.returncode for x in lsteps) or llog.returncode or lfsck.returncode:
    fail('P2', 'the Linux side did not run clean: ' + repr([(x.returncode, x.stderr[-200:]) for x in lsteps + [llog, lfsck]]))

plog = between(lines2, 'PX90-LOG-BEGIN', 'PX90-LOG-END')
want = llog.stdout.decode().splitlines() + ['PX90-LOG=0']
if plog != want:
    fail('P2', f'den log after the reboot is not Linux\'s: {plog!r} against {want!r}')
pf = between(lines2, 'PX90-FSCK=0', 'PX90-FSCK-END')
if pf != [] or lfsck.stdout or lfsck.stderr:
    fail('P2', f'den fsck --full: PAX {pf!r} (a PX90-FSCK=0 line is wanted, then nothing), Linux {lfsck.stdout + lfsck.stderr!r}')
pone = between(lines2, 'PX90-ONELINE-BEGIN', 'PX90-ONELINE-END')
if pone != lone.stdout.decode().splitlines():
    fail('P2', f'git log --oneline {pone!r}, Linux den log --oneline {lone.stdout!r}')
if 'PX90-STATUS=0' not in lines2 or between(lines2, 'PX90-ONELINE-END', 'PX90-STATUS=0') != []:
    fail('P2', 'den status --porcelain after the reboot is not clean, status 0')
if 'P2' not in fails:
    print(f'PASS P2 {firmware}: after the reboot den log is Linux\'s byte for byte, den fsck --full is clean, git log --oneline is den\'s, the worktree clean', flush=True)

why = []
if r.returncode != 0 or b'WARNING' in r.stdout + r.stderr:
    why.append('e2fsck -fn: ' + (r.stdout + r.stderr).decode(errors='replace')[-400:])
g = subprocess.run(['dumpe2fs', '-h', str(root)], capture_output=True)
if not (re.search(rb'^Filesystem state:\s+clean$', g.stdout, re.M) and re.search(rb'^Mount count:\s+[2-9]', g.stdout, re.M)):
    why.append('the root is not clean after two mounts')
def objects(top):
    base = top / '.git' / 'objects'
    return {p.relative_to(top).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob('*')) if p.is_file()}
pobj, lobj = objects(dump / 'den-persist'), objects(repo)
if not pobj or pobj != lobj:
    why.append(f'the object files differ: PAX {len(pobj)}, Linux {len(lobj)}; only PAX {sorted(set(pobj) - set(lobj))[:3]}, '
               f'only Linux {sorted(set(lobj) - set(pobj))[:3]}, other bytes {[k for k in pobj if k in lobj and pobj[k] != lobj[k]][:3]}')
for ref in ('HEAD', 'refs/heads/main'):
    a, b = dump / 'den-persist/.git' / ref, repo / '.git' / ref
    if not a.is_file() or not b.is_file() or a.read_bytes() != b.read_bytes():
        why.append(f'.git/{ref} differs')
(work / f'den-{firmware}.objects').write_text(''.join(f'{v}  {k}\n' for k, v in pobj.items()))
if why:
    fail('P3', '; '.join(why))
else:
    print(f'PASS P3 {firmware}: the root clean after two mounts; {len(pobj)} object files on the disk byte-identical to Linux\'s '
          f'(den {hashlib.sha256(den.read_bytes()).hexdigest()[:12]}…), HEAD and main Linux\'s', flush=True)
image.unlink(); root.unlink()
sys.exit(1 if fails else 0)
