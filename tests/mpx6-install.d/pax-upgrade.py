#!/usr/bin/env python3
"""px115: pax-upgrade's commands and refusals on Linux (tests/mpx6-install --only pax-upgrade).

    pax-upgrade.py PAX_UPGRADE WORK DISKTOOLS PAX_INSTALL REPO

PAX_UPGRADE and PAX_INSTALL are tools/mkinstall's (modes upgrade and install), DISKTOOLS holds
tools/mkdisktools' paxgpt and paxfat. The installed disk is an image made here as pax-install
makes one (paxgpt's three partitions, paxfat's ESP holding the installer's limine.conf, mke2fs's
ext2 at the root's offset), and the installed root a directory beside it (`--root`, `--disk`,
`--model`, `--serial`: the program's own options for these rows). The archives are newc files
made here. The ESP is read back with mtools (a black box). pax-install and reboot are stand-ins in
the tool directory, so `apply` and the boot hook are seen to call them. The rows run as root (run as
a user, this starts itself again under `sudo -n`), the user's commands as uid 1000 (setpriv), all in
a directory of their own under /var/tmp that uid 1000 can reach (removed at the end; WORK keeps
rows.txt).

Rows, each PASS or FAIL by name:
  P1 receive         the archive received, read back, renamed beside its digest
  P2 receive-digest  a digest that differs: refused, nothing kept, the earlier one intact
  P3 receive-word    a digest that is not 64 hex digits: refused
  P4 receive-cut     half the bytes: refused as a digest that differs
  P5 arm-user        arm as uid 1000: refused, it needs root
  P6 arm-edited      an ESP limine.conf that is not the installer's text: refused
  P7 arm-serial      a disk with no serial: refused
  P8 arm-space       a root with too little space: refused
  P9 arm-digest      the received file changed after its receive: refused, removed
  P10 arm-older      an image built before the installed one: refused
  P11 arm-same       the image already installed: refused
  P12 arm-entry      an archive with no /usr/share/pax-upgrade/entry: refused
  P13 arm-newc       bytes that are no newc archive: refused
  P14 arm            armed: the archive root's 0600 and its digest, the record, the attempts
                     file, the ESP's kernel and targets line, the armed configuration exactly
  P15 arm-second     a second arm: refused
  P16 clean-armed    clean while armed: refused
  P17 status         status as the user: the armed line
  P18 disarm         the ESP's configuration byte for byte the installer's again
  P19 arm-staged     armed again from the archive left staged
  P20 boot-refused   the hook under a staged kernel's refusal (its letter planted): disarmed, the
                     reason by name, a reboot
  P21 boot-chosen    the hook with no letter: disarmed, no reboot
  P22 apply-refused  pax-install refusing before any write: disarmed, the record gone
  P23 apply-stopped  pax-install stopping after its record: still armed
  P24 boot-rearm     an upgrade cut after its ESP phase: armed again, a reboot
  P25 apply          pax-install done: the verdict, the record gone, the configuration put back
  P26 boot-clean     the first boot after: the staged files removed, the ESP's kernel emptied
  P27 boot-verdict   the verdict cut: written at the first boot, then the files removed
  P28 install-armed  pax-install's --armed with a typed line, a seed, or without --upgrade: usage
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

PROG, WORK, DISKTOOLS, INSTALL, REPO = map(Path, sys.argv[1:6])
ROOT_START, ESP_START, ESP_BYTES, MIB = 69206016, 2097152, 67108864, 1 << 20
MODEL, SERIAL = 'PX115 test disk', 'PX115-0001'
STAGE = 'var/lib/pax-upgrade'
bad = []
os.environ['MTOOLS_SKIP_CHECK'] = '1'


def say(s):
    print(s, flush=True)


def row(name, ok, why=''):
    if ok:
        say(f'PASS {name}')
    else:
        bad.append(name)
        say(f'FAIL {name}: {why}')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rb(p):
    """A file's bytes, or None when it is not there (a red take reads what was never written)."""
    try:
        return Path(p).read_bytes()
    except OSError:
        return None


def rt(p):
    b = rb(p)
    return '' if b is None else b.decode(errors='replace')


def run(argv, **kw):
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, **kw)


def must(argv, **kw):
    r = run(argv, **kw)
    if r.returncode:
        raise RuntimeError(f'{argv[:3]}: exit {r.returncode}: {r.stderr[-600:]}')
    return r


def as_root(argv, env):
    return ['env', '-i'] + [f'{k}={v}' for k, v in env.items()] + [str(a) for a in argv]


def as_user(argv, env):
    return ['setpriv', '--reuid=1000', '--regid=1000', '--clear-groups', 'env', '-i'] + \
        [f'{k}={v}' for k, v in env.items()] + [str(a) for a in argv]


def newc(rows):
    out = bytearray()
    for ino, (name, data) in enumerate(sorted(rows.items()) + [('TRAILER!!!', b'')], 1):
        mode = 0o40755 if data is None else 0o100644
        data = data or b''
        enc = name.encode() + b'\0'
        fields = [ino, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(enc), 0]
        out += b'070701' + b''.join(f'{n:08x}'.encode() for n in fields) + enc
        out += b'\0' * (-len(out) % 4)
        out += data
        out += b'\0' * (-len(out) % 4)
    return bytes(out)


def config_text(uuid):
    return ('timeout: 5\nverbose: yes\nserial: yes\n\n/PAX ext2 developer preview\n    protocol: limine\n'
            f'    path: boot():/boot/pax\n    cmdline: quiet root=PARTUUID={uuid} rootfstype=ext2 rw\n')


def make_disk(img, root_mib, seed):
    last = (ROOT_START + root_mib * MIB) // 512 - 1
    with open(img, 'wb') as f:
        f.truncate(ROOT_START + root_mib * MIB + MIB)
    must([DISKTOOLS / 'paxgpt', '--seed', seed, img, '1:esp:4096:135167:esp', f'2:linux:135168:{last}:root',
          '3:bios:2048:4095:bios'])
    must([DISKTOOLS / 'paxfat', '--offset', ESP_START, '--seed', seed, 'mkfs', img, ESP_BYTES])
    for d in ('/boot', '/boot/limine'):
        must([DISKTOOLS / 'paxfat', '--offset', ESP_START, 'mkdir', img, d])
    dump = must([DISKTOOLS / 'paxgpt', '--dump', img]).stdout
    uuid = next(w.split('=', 1)[1].lower() for line in dump.splitlines() if line.startswith(f'{img}2 :')
                for w in (x.strip() for x in line.split(',')) if w.startswith('uuid='))
    conf = T / f'{img.stem}.conf'
    conf.write_text(config_text(uuid))
    must([DISKTOOLS / 'paxfat', '--offset', ESP_START, 'copy', img, conf, '/boot/limine/limine.conf'])
    must(['mke2fs', '-q', '-F', '-t', 'ext2', '-b', '4096', '-L', 'pax-root', '-E', f'offset={ROOT_START}', img,
          str(root_mib * 256)])
    return uuid


def esp(img, path):
    r = subprocess.run(['mtype', '-i', f'{img}@@{ESP_START}', f'::{path}'], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def esp_bytes(img, path):
    out = T / 'esp-read'
    if out.exists():
        out.unlink()
    r = run(['mcopy', '-n', '-i', f'{img}@@{ESP_START}', f'::{path}', out])
    return out.read_bytes() if r.returncode == 0 else None


T = Path('/nonexistent')


def main():
    global T
    T = Path(tempfile.mkdtemp(prefix='pax-upgrade-rows-', dir='/var/tmp'))
    T.chmod(0o755)
    try:
        return rows()
    finally:
        WORK.mkdir(parents=True, exist_ok=True)
        (T / 'rows.txt').write_text(''.join(f'FAIL {b}\n' for b in bad) or 'every row held\n')
        shutil.rmtree(T, ignore_errors=True)


def rows():
    # The tool directory: the real paxgpt and paxfat; pax-install and reboot stand-ins.
    tools = T / 'tools'
    tools.mkdir()
    for t in ('paxgpt', 'paxfat'):
        shutil.copy(DISKTOOLS / t, tools / t)
    (tools / 'reboot').write_text('#!/bin/sh\necho reboot >> "$(dirname "$0")/reboots"\n')
    (tools / 'pax-install').write_text(
        '#!/bin/sh\nd=$(dirname "$0")\necho "$@" >> "$d/pax-install.args"\nmode=$(cat "$d/pax-install.mode")\n'
        'case $mode in ok) exit 0 ;; refuse) exit 1 ;; stop) mkdir -p "$(cat "$d/target")/etc/pax-install"; '
        ': > "$(cat "$d/target")/etc/pax-install/upgrading"; exit 1 ;; esac\nexit 3\n')
    for t in ('reboot', 'pax-install'):
        (tools / t).chmod(0o755)
    # The installed root and its disk.
    R = T / 'root'
    for d in ('etc', 'home/wolf', 'var/log', 'var/lib', 'mnt'):
        (R / d).mkdir(parents=True, exist_ok=True)
    disk = T / 'disk.img'
    uuid = make_disk(disk, 64, 'px115-rows')
    (R / 'etc/fstab').write_text(f'PARTUUID={uuid} / ext2 rw 0 1\ntmpfs /tmp tmpfs nosuid,nodev 0 0\n')
    old_rel = 'kernel ' + 'a' * 40 + ' ' + 'b' * 64 + '\nsource-date-epoch 1000 -\n'
    (R / 'etc/pax-release').write_text(old_rel)
    (R / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\nwolf:x:1000:1000:wolf:/home/wolf:/bin/sh\n')
    os.chown(R / 'home/wolf', 1000, 1000)
    shutil.copy(PROG, T / 'pax-upgrade')
    small = T / 'small.img'
    make_disk(small, 8, 'px115-rows')  # the same seed: the same PARTUUID, the same fstab line
    edited = T / 'edited.img'
    shutil.copy(disk, edited)
    mine = T / 'mine.conf'
    mine.write_text(config_text(uuid) + '# mine\n')
    must([DISKTOOLS / 'paxfat', '--offset', ESP_START, 'replace', edited, mine, '/boot/limine/limine.conf'])
    installer_conf = esp(disk, '/boot/limine/limine.conf')
    # The archives.
    kernel = os.urandom(200000)
    entry = (REPO / 'user/install/pax-upgrade/entry').read_bytes()
    new_rel = 'kernel ' + 'c' * 40 + ' ' + 'd' * 64 + '\nsource-date-epoch 2000 -\n'
    base = {'boot': None, 'boot/pax': kernel, 'etc': None, 'usr/share/pax-upgrade': None,
            'usr/share/pax-upgrade/entry': entry, 'var': None, 'var/filler': os.urandom(1 << 20)}
    arch = {}
    for name, rel, with_entry in (('new', new_rel, True), ('older', old_rel.replace('1000', '500').replace('a' * 40, 'e' * 40), True),
                                  ('same', old_rel, True), ('noentry', new_rel, False)):
        rows = dict(base, **{'etc/pax-release': rel.encode()})
        if not with_entry:
            del rows['usr/share/pax-upgrade/entry']
        arch[name] = T / f'{name}.cpio'
        arch[name].write_bytes(newc(rows))
    arch['big'] = T / 'big.cpio'
    arch['big'].write_bytes(newc(dict(base, **{'etc/pax-release': new_rel.encode(), 'var/pad': os.urandom(12 * MIB)})))
    arch['junk'] = T / 'junk.cpio'
    arch['junk'].write_bytes(os.urandom(300000))
    for p in list(arch.values()) + [tools, R, T]:
        p.chmod(0o755) if p.is_dir() else p.chmod(0o644)
    home = R / 'home/wolf'
    rdir = home / '.pax-upgrade'
    uenv = {'HOME': home, 'PATH': '/usr/bin:/bin'}
    renv = {'HOME': '/root', 'SUDO_USER': 'wolf', 'PATH': '/usr/bin:/bin'}
    opts = ['--root', R, '--disk', disk, '--model', MODEL, '--serial', SERIAL, '--tool-dir', tools]

    def up(cmd, disk_=None, serial=SERIAL, user=False, stdin=None, root=None):
        o = ['--root', root or R, '--disk', disk_ or disk, '--model', MODEL, '--serial', serial, '--tool-dir', tools]
        argv = [T / 'pax-upgrade'] + o + cmd
        argv = as_user(argv, uenv) if user else as_root(argv, renv)
        with open(stdin, 'rb') if stdin else open(os.devnull, 'rb') as f:
            return subprocess.run(argv, stdin=f, capture_output=True, text=True)

    def receive(name, digest=None, data=None):
        src = arch[name]
        if data is not None:
            src = T / 'part.cpio'
            src.write_bytes(data)
            src.chmod(0o644)
        return up(['receive', '--sha256', digest or sha(arch[name].read_bytes())], user=True, stdin=src)

    def says(r, text):
        return text in r.stdout + r.stderr

    def log():
        p = R / 'var/log/pax-upgrade.log'
        return p.read_text() if p.exists() else ''

    def reboots():
        p = tools / 'reboots'
        n = len(p.read_text().splitlines()) if p.exists() else 0
        return n

    new_sha = sha(arch['new'].read_bytes())
    # P1-P4: receive.
    r = receive('new')
    got = rb(rdir / 'received') or b''
    row('P1 receive', r.returncode == 0 and got == arch['new'].read_bytes() and
        rt(rdir / 'received.sha256') == f'{new_sha} {len(got)}\n' and not (rdir / 'incoming').exists(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    r = receive('older', digest=new_sha)
    row('P2 receive-digest', r.returncode == 1 and says(r, f'not {new_sha}; nothing kept') and
        rb(rdir / 'received') == arch['new'].read_bytes() and not (rdir / 'incoming').exists(),
        f'exit {r.returncode}: {r.stderr}')
    r = up(['receive', '--sha256', 'abc'], user=True, stdin=arch['new'])
    row('P3 receive-word', r.returncode == 1 and says(r, '64 lowercase hex digits'), f'exit {r.returncode}: {r.stderr}')
    half = arch['new'].read_bytes()[:150000]
    r = receive('new', data=half)
    row('P4 receive-cut', r.returncode == 1 and says(r, f'the {len(half)} bytes that arrived have sha256 {sha(half)}') and
        rb(rdir / 'received') == arch['new'].read_bytes(), f'exit {r.returncode}: {r.stderr}')
    # P5-P13: arm's refusals, each before the configuration is touched.
    r = up(['arm'], user=True)
    row('P5 arm-user', r.returncode == 1 and says(r, 'arm refused: it needs root'), f'exit {r.returncode}: {r.stderr}')
    r = up(['arm'], disk_=edited)
    row('P6 arm-edited', r.returncode == 1 and says(r, "limine.conf is not the installer's text") and
        esp(edited, '/boot/limine/limine.conf') == mine.read_bytes(), f'exit {r.returncode}: {r.stderr}')
    r = up(['arm'], serial='')
    row('P7 arm-serial', r.returncode == 1 and says(r, 'reports no model or no serial'), f'exit {r.returncode}: {r.stderr}')
    r = up(['arm'], disk_=small)
    row('P8 arm-space', r.returncode == 1 and says(r, 'too little space') and (rdir / 'received').exists(),
        f'exit {r.returncode}: {r.stderr}')
    # One byte changed in place after the receive (an x where the archive's last file ends).
    at = len(arch['new'].read_bytes()) - 200
    ch = 'y' if arch['new'].read_bytes()[at] == ord('x') else 'x'
    subprocess.run(as_root(['sh', '-c', f'printf {ch} | dd of={rdir / "received"} bs=1 seek={at} conv=notrunc 2>/dev/null'], renv))
    r = up(['arm'])
    row('P9 arm-digest', r.returncode == 1 and says(r, f'not the {new_sha} it was received with; removed') and
        not (R / STAGE / 'staged/archive').exists(), f'exit {r.returncode}: {r.stderr}')
    for name, rid, text in (('older', 'P10 arm-older', 'an older image'), ('same', 'P11 arm-same', 'the image already installed'),
                            ('noentry', 'P12 arm-entry', 'carries no /usr/share/pax-upgrade/entry'),
                            ('junk', 'P13 arm-newc', 'not a newc archive')):
        rr = receive(name)
        r = up(['arm'])
        row(rid, rr.returncode == 0 and r.returncode == 1 and says(r, text) and not (R / STAGE / 'staged/archive').exists() and
            esp(disk, '/boot/limine/limine.conf') == installer_conf, f'exit {r.returncode}: {r.stdout}{r.stderr}')
        # A refusal that did not happen leaves an arm; taken back, so each row stands alone (a plant is red at its own).
        if (R / STAGE / 'armed').exists():
            up(['disarm'])
            up(['clean'])
    # P14: armed.
    receive('new')
    r = up(['arm'])
    st = R / STAGE
    staged = st / 'staged/archive'
    s = os.stat(staged) if staged.exists() else None
    conf = esp(disk, '/boot/limine/limine.conf') or b''
    want = ('timeout: 5\ndefault_entry: 1\n\n' +
            entry.decode().replace('@PARTUUID@', uuid).replace('@SHA256@', new_sha) + '\n' +
            config_text(uuid).split('\n\n', 1)[1]).encode()
    rec = rt(st / 'armed')
    checks = {
        'exit 0': r.returncode == 0,
        'the archive root\'s 0600 and its digest': s is not None and s.st_uid == 0 and s.st_mode & 0o777 == 0o600 and sha(staged.read_bytes()) == new_sha,
        'the stage 0700': st.exists() and (st.stat().st_mode & 0o777) == 0o700,
        'nothing left received': not (rdir / 'received').exists(),
        'the attempts file': rb(st / 'attempts') == b'00000000',
        'the record': rec.startswith(f'pax-upgrade armed v1\nsha256 {new_sha}\n') and f'\npartuuid {uuid}\n' in rec and
                      f'\nmodel {MODEL}\nserial {SERIAL}\n' in rec and f'\nrelease {sha(new_rel.encode())}\n' in rec and
                      '\nto ' + 'c' * 40 + '\n' in rec and '\nbuilt 2000\n' in rec,
        'the ESP kernel': esp_bytes(disk, '/pax-upgrade/pax') == kernel,
        'the targets line': esp(disk, '/pax/install-targets') == f'model={MODEL} serial={SERIAL}\n'.encode(),
        'the armed configuration': conf == want,
        'the log': ' armed to ' + 'c' * 40 in log(),
    }
    row('P14 arm', all(checks.values()), f'{[k for k, v in checks.items() if not v]}: {r.stdout}{r.stderr}\n{conf.decode(errors="replace")}')
    receive('new')
    r = up(['arm'])
    row('P15 arm-second', r.returncode == 1 and says(r, 'an upgrade is armed already'), f'exit {r.returncode}: {r.stderr}')
    r = up(['clean'])
    row('P16 clean-armed', r.returncode == 1 and says(r, 'clean refused: an upgrade is armed') and staged.exists(),
        f'exit {r.returncode}: {r.stderr}')
    r = up(['status'], user=True)
    row('P17 status', r.returncode == 0 and 'state: ' in r.stdout and ' armed to ' in r.stdout and
        f'received: {rdir}/received' in r.stdout, f'exit {r.returncode}: {r.stdout}{r.stderr}')
    r = up(['disarm'])
    row('P18 disarm', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == installer_conf and
        not (st / 'armed').exists() and not (st / 'attempts').exists() and staged.exists() and ' disarmed ' in log(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    subprocess.run(as_root(['rm', '-f', rdir / 'received', rdir / 'received.sha256'], renv))
    r = up(['arm'])
    row('P19 arm-staged', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == want and (st / 'armed').exists(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    # P20, P21: the boot hook under the installed root while armed.
    subprocess.run(as_root(['sh', '-c', f'printf 1000000D > {st / "attempts"}'], renv))
    n = reboots()
    r = up(['boot'])
    row('P20 boot-refused', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == installer_conf and
        not (st / 'armed').exists() and reboots() == n + 1 and " not-applied the staged archive's sha256 was not the armed one; disarmed" in log(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    up(['arm'])
    n = reboots()
    r = up(['boot'])
    row('P21 boot-chosen', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == installer_conf and
        reboots() == n and 'chosen at the menu' in (log().splitlines() or [''])[-1], f'exit {r.returncode}: {r.stdout}{r.stderr}')
    # P22-P27: apply (its root at --root A, A/mnt/target the installed root) and the hook after it.
    A = T / 'applyroot'
    (A / 'mnt').mkdir(parents=True)
    (A / 'mnt/target').symlink_to(R)
    (tools / 'target').write_text(str(R))

    def apply(mode):
        (tools / 'pax-install.mode').write_text(mode)
        return up(['apply'], root=A)

    up(['arm'])
    r = apply('refuse')
    row('P22 apply-refused', r.returncode == 1 and esp(disk, '/boot/limine/limine.conf') == installer_conf and
        not (st / 'armed').exists() and ' refused pax-install --upgrade exited 1 before any write' in log() and
        rt(tools / 'pax-install.args').splitlines()[-1:] == [f'--upgrade --armed {A}/mnt/target/{STAGE}/armed'],
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    up(['arm'])
    r = apply('stop')
    row('P23 apply-stopped', r.returncode == 1 and esp(disk, '/boot/limine/limine.conf') == want and
        (st / 'armed').exists() and ' stopped pax-install --upgrade exited 1 after its writes began' in log(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    # The upgrade's ESP phase wrote the installer's configuration, and then the power went.
    conf_file = T / 'installer.conf'
    conf_file.write_bytes(installer_conf)
    must(as_root([DISKTOOLS / 'paxfat', '--offset', ESP_START, 'replace', disk, conf_file, '/boot/limine/limine.conf'], renv))
    n = reboots()
    r = up(['boot'])
    row('P24 boot-rearm', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == want and reboots() == n + 1 and
        ' re-armed ' in log(), f'exit {r.returncode}: {r.stdout}{r.stderr}')
    subprocess.run(as_root(['rm', '-f', R / 'etc/pax-install/upgrading'], renv))
    r = apply('ok')
    row('P25 apply', r.returncode == 0 and esp(disk, '/boot/limine/limine.conf') == installer_conf and
        not (st / 'armed').exists() and ' upgraded to ' in (log().splitlines() or [''])[-1], f'exit {r.returncode}: {r.stdout}{r.stderr}')
    r = up(['boot'])
    row('P26 boot-clean', r.returncode == 0 and not staged.exists() and esp_bytes(disk, '/pax-upgrade/pax') == b'' and
        ' cleaned after the upgrade' in log(), f'exit {r.returncode}: {r.stdout}{r.stderr}')
    receive('new')
    up(['arm'])
    must(as_root([DISKTOOLS / 'paxfat', '--offset', ESP_START, 'replace', disk, conf_file, '/boot/limine/limine.conf'], renv))
    (R / 'etc/pax-release').write_text(new_rel)
    r = up(['boot'])
    lines = [''] * 2 + log().splitlines()
    row('P27 boot-verdict', r.returncode == 0 and 'the verdict written at its first boot' in lines[-2] and
        ' cleaned after the upgrade' in lines[-1] and not (st / 'armed').exists() and not staged.exists(),
        f'exit {r.returncode}: {r.stdout}{r.stderr}')
    (R / 'etc/pax-release').write_text(old_rel)
    ok = True
    for argv in (['--upgrade', '--armed', 'R', '--seed', 's', '--confirm', 'c'], ['--armed', 'R'],
                 ['--upgrade', '--armed', 'R', '--allow-list', 'L']):
        r = run([INSTALL] + argv)
        ok = ok and r.returncode == 2 and 'usage: pax-install' in r.stderr
    row('P28 install-armed', ok, 'a usage refusal was not exit 2')
    say(f'pax-upgrade rows: {28 - len(bad)} of 28 held' + (f'; failed: {", ".join(bad)}' if bad else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    if os.geteuid() != 0:
        os.execvp('sudo', ['sudo', '-n', sys.executable, '-I', *sys.argv])
    sys.exit(main())
