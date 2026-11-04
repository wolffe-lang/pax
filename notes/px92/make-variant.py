#!/usr/bin/env python3
"""px92: a lane-local variant of the head's tests/mpx6-install.d/metal.py for the staged stick's
qualification (R-px92-3). Every edit is asserted to apply exactly once; the diff is the record.

    make-variant.py METAL.py OUT.py

What the variant adds, each behind an environment word the head's legs never set:
- PAX_METAL_USED=pax with PAX_METAL_TARGET_FROM=IMG: the target is a copy (cp --sparse=always) of IMG,
  a target an earlier leg installed, instead of a blank or tools/used-disk target.
- PAX_METAL_KEEP_TARGET=1: the installed target is kept as WORK/target-after.img (the next leg's IMG).
- PAX_METAL_PX87=COMMIT: px87's rows. Boot 0 (new) boots the stick's live entry, reads the login screen
  and the kernel's memory transcript, logs in as root and types `poweroff` at the shell; boots 1 and 2
  read the same lines at their logins; boot 2 is powered off by `poweroff` typed at the installed shell
  (the head types `reboot -p`); each power-off is read from QMP's SHUTDOWN event (guest-shutdown is
  ACPI S5; guest-reset would be a restart, which -no-reboot also turns into an exit 0).
"""
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text()

EDITS = []


def edit(old, new):
    EDITS.append((old, new))


edit("""assert USED in ('', 'fat32', 'ext4'), USED
LISTED = os.environ.get('PAX_METAL_LISTED', '') == '1'
""", """assert USED in ('', 'fat32', 'ext4', 'pax'), USED
LISTED = os.environ.get('PAX_METAL_LISTED', '') == '1'
# px92 (a lane-local variant, notes/px92/make-variant.py): PAX_METAL_USED=pax copies PAX_METAL_TARGET_FROM,
# a target an earlier leg installed and kept (PAX_METAL_KEEP_TARGET=1); PAX_METAL_PX87=COMMIT runs px87's
# rows (boot 0, the kernel and boot lines at each login, the quiet transcript, poweroff at both shells).
TARGET_FROM = os.environ.get('PAX_METAL_TARGET_FROM', '')
KEEP_TARGET = os.environ.get('PAX_METAL_KEEP_TARGET', '') == '1'
PX87 = os.environ.get('PAX_METAL_PX87', '')
assert (USED == 'pax') == bool(TARGET_FROM), (USED, TARGET_FROM)
""")

edit("""    with open(d/'target.img', 'wb') as f:
        f.truncate(TARGET['bytes'])
    if USED:
""", """    with open(d/'target.img', 'wb') as f:
        f.truncate(TARGET['bytes'])
    if USED == 'pax':
        run(['cp', '--sparse=always', TARGET_FROM, d/'target.img'])
        if (d/'target.img').stat().st_size != TARGET['bytes']:
            fail('M0-target', f'{TARGET_FROM} is {(d/"target.img").stat().st_size} bytes, not {TARGET["bytes"]}')
        h, n = extents_sha(d/'target.img')
        log(f'the target: a copy of {TARGET_FROM} (a PAX install), extents sha256 {h} ({n} extents)')
        result['used'] = 'pax'
        result['target_from'] = {'path': TARGET_FROM, 'extents_sha256': h, 'extents': n}
    elif USED:
""")

edit("""        self.f.readline()
        self.i = 0
""", """        self.f.readline()
        self.i = 0
        self.events = []
""")

edit("""            r = json.loads(line)
            if r.get('id') == self.i:
""", """            r = json.loads(line)
            if 'event' in r:
                self.events.append(r)
            if r.get('id') == self.i:
""")

edit("""# --- the leg ------------------------------------------------------------------
""", r'''# --- px92: px87's rows -------------------------------------------------------------

# notes/px87/stick/qual.py's readers, at the head: the console's escapes removed; the kernel's timing line by
# its own words (not the boot medium's `boot: /boot/...` line); a program's ordinary-life lines.
esc_re = re.compile(r'\x1b\[[0-9;?=<>]*[A-Za-z]|\x1b[()][A-Za-z0-9]|\x1b[c78DEHM=>]')
boot_re = re.compile(r"^boot: ([0-9]+) ms from the kernel's entry to its first program; the console drew for ([0-9]+) ms of it \(([0-9]+) scrolls(?: by (?:copy|redraw|none)(?: \([^)]*\))?)?, ([0-9]+) bytes\)$")
quiet_re = re.compile(r'^user: (exec pid |[^ ]+ pid [0-9]+ (exit_group|exit) [0-9]+ after )')


def want_kernel():
    return 'kernel: %s sha256 %s, %d bytes' % (PX87, sha(kernel), kernel.stat().st_size)


def transcript(m, name):
    """The kernel's memory transcript (boot/io.S's pax_serial_log, the first 64 KiB the console wrote when
    no COM1 exists), read by HMP memsave with the machine stopped, as screen() reads the cells."""
    m.q.call('stop')
    try:
        c = m.dir/'log-count.bin'
        if m.q.hmp(f'memsave 0x{SYM["pax_serial_log_count"]:x} 8 "{c}"'):
            return '', 0
        n = struct.unpack('<Q', c.read_bytes())[0]
        got = min(n, 65536)
        b = m.dir/'log.bin'
        if got == 0 or m.q.hmp(f'memsave 0x{SYM["pax_serial_log"]:x} {got} "{b}"'):
            return '', n
        t = esc_re.sub('', b.read_bytes()[:got].decode('latin-1')).replace('\r', '')
    finally:
        m.q.call('cont')
    (m.dir/f'{name}.transcript.txt').write_text(t)
    return t, n


def px87_login(m, screen, row):
    """The login screen: the kernel's line (its commit, the sha256 and size of the file it was loaded from)
    and, on the next line, the boot line (R-px87-9: repeated there because the banner scrolls off)."""
    lines = m.unwrapped(screen).split('\n')
    want = want_kernel()
    got = ''
    for k, l in enumerate(lines):
        if l != want:
            continue
        # The boot line is longer than a row at 1280x800: unwrapped() joins a row filled to the last column,
        # but a row whose last column is a space reads shorter (screen() strips the row's end), so the row
        # after is tried both ways.
        nxt = lines[k + 1:k + 3] + ['', '']
        for c in (nxt[0], nxt[0] + nxt[1], nxt[0] + ' ' + nxt[1]):
            if boot_re.match(c):
                got = c
                break
        if got:
            break
    if not got:
        fail(row + '-kernel-line', f'no {want!r} followed by the boot line on the login screen:\n{screen}')
    result[row + '_boot_line'] = got
    print(f'PASS {row}-kernel-line: the login screen reads {want!r}, then {got!r}', flush=True)


def px87_transcript(m, row, quiet=True, banner=True):
    """The memory transcript: `PAX: the console` then the kernel's line, the boot line right after the line
    again, and (quiet=True: required; quiet=None: recorded) no line of a program's ordinary life."""
    t, n = transcript(m, row)
    lines = t.split('\n')
    want = want_kernel()
    if banner:
        i = lines.index('PAX: the console') if 'PAX: the console' in lines else -1
        if i < 0 or i + 1 >= len(lines) or lines[i + 1] != want:
            fail(row + '-banner', f'the transcript ({n} bytes) has no {want!r} under `PAX: the console`')
        b = [k for k, l in enumerate(lines) if boot_re.match(l)]
        if not b or lines[b[0] - 1] != want:
            fail(row + '-boot-line', f'the transcript has no boot line right after {want!r}')
    users = [l for l in lines if l.startswith('user: ')]
    bad = [l for l in lines if quiet_re.match(l)]
    result[row + '_transcript'] = {'bytes': n, 'kept': min(n, 65536), 'user_lines': len(users), 'per_program': len(bad),
                                   'first_per_program': bad[0] if bad else ''}
    what = (f'{min(n, 65536)} of {n} bytes kept; {len(users)} `user:` line(s), {len(bad)} of a program\'s ordinary life'
            + (f', the first {bad[0]!r}' if bad else ''))
    if quiet is True and bad:
        fail(row + '-quiet', what)
    tag = 'PASS' if quiet is True else 'INFO'
    print(f'{tag} {row}-transcript: ' + ('the banner and the kernel line, the boot line after it again; ' if banner else '')
          + what, flush=True)


def shutdown_reason(m):
    """QMP's SHUTDOWN event's reason, read to the socket's end once QEMU has exited: guest-shutdown for an
    ACPI power-off, guest-reset for a restart (which -no-reboot makes an exit as well)."""
    evs = list(m.q.events)
    try:
        m.q.s.settimeout(5)
        while True:
            line = m.q.f.readline()
            if not line:
                break
            r = json.loads(line)
            if 'event' in r:
                evs.append(r)
    except Exception:
        pass
    sd = [e for e in evs if e.get('event') == 'SHUTDOWN']
    return (sd[-1].get('data') or {}).get('reason', '') if sd else ''


def boot0(d, stick):
    """The live entry alone: the stick booted, its login read, root, `poweroff` at the shell. The target
    and the three other disks byte-identical across it (the live entry writes no disk)."""
    vars0 = work/'vars0.fd'
    shutil.copyfile(os.environ.get('PAX_OVMF_VARS', '/usr/share/OVMF/OVMF_VARS_4M.fd'), vars0)
    tgt = extents_sha(d/'target.img')
    wit = witnesses(d)
    m = Machine('boot0', qemu_args(d, vars0, stick))
    try:
        s = m.wait(r'^login: *$', 'P0-live-login', 600)
        m.shot('live-login')
        px87_login(m, s, 'P0')
        px87_transcript(m, 'P0', quiet=True)
        m.type('root\n')
        m.wait(r'^.*[$#] *$', 'P0-live-login', 120, last=True)
        m.shot('root')
        m.type('poweroff\n')
        rc, secs = m.ended('P0-poweroff', 300)
        why = shutdown_reason(m)
        result['boot0_seconds'] = round(secs, 2)
        result['boot0_shutdown'] = why
        if rc != 0 or why != 'guest-shutdown':
            fail('P0-poweroff', f'QEMU exit {rc}, SHUTDOWN reason {why!r}')
    finally:
        m.kill()
    print(f'PASS P0-poweroff: `poweroff` at the live shell: ACPI power-off (QMP SHUTDOWN {why}), QEMU exit 0, {secs:.1f} s', flush=True)
    if witnesses(d) != wit or extents_sha(d/'target.img') != tgt:
        fail('P0-nowrite', 'a disk changed in boot 0')
    print('PASS P0-nowrite: the target and the three other disks byte-identical over their allocated extents across boot 0', flush=True)


# --- the leg ------------------------------------------------------------------
''')

edit("""    # Boot 1: the stick.
    m = Machine('boot1', qemu_args(d, vars_fd, stick))
    try:
        m.wait(r'^login: *$', 'M1-live-login', 600)
        m.shot('live-login')
""", """    if PX87:
        boot0(d, stick)
    # Boot 1: the stick.
    m = Machine('boot1', qemu_args(d, vars_fd, stick))
    try:
        s1 = m.wait(r'^login: *$', 'M1-live-login', 600)
        m.shot('live-login')
        if PX87:
            px87_login(m, s1, 'P1')
            px87_transcript(m, 'P1', quiet=True)
""")

edit("""        need(flat, f'/dev/sdc bytes={TARGET["bytes"]} sector=512 model={TARGET_MODEL} serial={TARGET["serial"]}', 'M2-target-listed')
""", """        need(flat, f'/dev/sdc bytes={TARGET["bytes"]} sector=512 model={TARGET_MODEL} serial={TARGET["serial"]}', 'M2-target-listed')
        if USED == 'pax':
            need(flat, "PAX's install layout; on the install allow-list", 'P-target-layout')
            print("PASS P-target-layout: --check reads the target as PAX's install layout, on the install allow-list", flush=True)
""")

edit("""        need(flat, 'The root file system is ext2 without a journal.', 'M3-summary')
""", """        need(flat, 'The root file system is ext2 without a journal.', 'M3-summary')
        if USED == 'pax':
            need(flat, "This install erases /dev/sdc's PAX's install layout.", 'P-erase-line')
            print("PASS P-erase-line: the page says `This install erases /dev/sdc's PAX's install layout.`", flush=True)
""")

edit("""        m.wait(r'poweroff to power off', 'M4-install', 120)
        m.shot('complete')
""", """        m.wait(r'poweroff to power off', 'M4-install', 120)
        m.shot('complete')
        if PX87:
            px87_transcript(m, 'P1-install', quiet=True, banner=False)
            bad = [l for l in m.unwrapped(m.screen()).split('\\n') if quiet_re.match(l)]
            if bad:
                fail('P1-install-quiet', f'on the screen at the end of the install: {bad[0]!r}')
            print('PASS P1-install-quiet: no line of a program\\'s ordinary life on the screen at the end of the install', flush=True)
""")

edit("""        m.type('poweroff\\n')
        rc, secs = m.ended('M4-poweroff', 300)
        result['boot1_seconds'] = round(secs, 2)
        if rc != 0:
            fail('M4-poweroff', f'QEMU exit {rc}')
""", """        m.type('poweroff\\n')
        rc, secs = m.ended('M4-poweroff', 300)
        result['boot1_seconds'] = round(secs, 2)
        if rc != 0:
            fail('M4-poweroff', f'QEMU exit {rc}')
        if PX87:
            why = shutdown_reason(m)
            result['boot1_shutdown'] = why
            if why != 'guest-shutdown':
                fail('P1-poweroff', f'the installer\\'s poweroff: SHUTDOWN reason {why!r}')
            print(f'PASS P1-poweroff: the installer\\'s `poweroff` answer: ACPI power-off (QMP SHUTDOWN {why})', flush=True)
""")

edit("""        need(s, 'PAX: log in as root or as the user pax-install made.', 'M7-disk-boot')
        m.shot('disk-login')
""", """        need(s, 'PAX: log in as root or as the user pax-install made.', 'M7-disk-boot')
        m.shot('disk-login')
        if PX87:
            px87_login(m, s, 'P2')
            px87_transcript(m, 'P2', quiet=None)
""")

edit("""        m.type('reboot -p\\n')
        rc, secs = m.ended('M9-poweroff', 300)
        result['boot2_seconds'] = round(secs, 2)
""", """        m.type(('poweroff' if PX87 else 'reboot -p') + '\\n')
        rc, secs = m.ended('M9-poweroff', 300)
        result['boot2_seconds'] = round(secs, 2)
        if PX87:
            why = shutdown_reason(m)
            result['boot2_shutdown'] = why
            if rc != 0 or why != 'guest-shutdown':
                fail('P2-poweroff', f'`poweroff` at the installed shell: QEMU exit {rc}, SHUTDOWN reason {why!r}')
            print(f'PASS P2-poweroff: `poweroff` at the installed shell: ACPI power-off (QMP SHUTDOWN {why}), QEMU exit 0', flush=True)
""")

edit("""    for n in ('nvme', 'steam', 'sandisk', 'target'):
        (d/(n + '.img')).unlink()
""", """    for n in ('nvme', 'steam', 'sandisk', 'target'):
        if n == 'target' and KEEP_TARGET:
            os.replace(d/'target.img', work/'target-after.img')
            h, k = extents_sha(work/'target-after.img')
            (work/'target-after.sha256').write_text(f'{h} extents {k}\\n')
            print(f'KEPT the installed target as {work/"target-after.img"}: extents sha256 {h} ({k} extents)', flush=True)
            continue
        (d/(n + '.img')).unlink()
""")

# px92 (the dev stick, the coordinator's addition): PAX_METAL_MEM sets the guest's memory (the head's 2048M by
# default); PAX_METAL_DEV=1 adds the dev rows at the installed shell: `wolf --version` says the pin's line, and a
# small program printing env_args() is built there by `wolf build` and run with two arguments.
edit("""    a = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', '2048M', '-accel', accel(),
""", """    a = ['qemu-system-x86_64', '-machine', 'q35', '-cpu', 'max', '-m', os.environ.get('PAX_METAL_MEM', '2048M'), '-accel', accel(),
""")

edit("""PX87 = os.environ.get('PAX_METAL_PX87', '')
""", """PX87 = os.environ.get('PAX_METAL_PX87', '')
DEV = os.environ.get('PAX_METAL_DEV', '') == '1'
""")

edit("""def boot0(d, stick):
""", """def dev_rows(m):
    """ + '"""' + """The dev image's compiler on the installed system, at root's shell (ENV=/etc/shrc: the dev PATH and WOLF_STD)."""
    + '"""' + """
    pin = (repo/'user/wolf.pin').read_text()
    vline = next(l.split('=', 1)[1].strip().strip('"') for l in pin.splitlines() if l.startswith('WOLF_SRC_VERSION_LINE='))
    s = m.command('wolf --version; echo PX92-V-$?', 'D1-wolf-version', 300)
    m.shot('wolf-version')
    flat = m.unwrapped(s)
    if vline not in flat or 'PX92-V-0' not in flat:
        fail('D1-wolf-version', f'want {vline!r} and status 0; screen:\\n{s}')
    print(f'PASS D1-wolf-version: `wolf --version` on the installed 860 says {vline!r}, status 0', flush=True)
    src = ['fn main() {', '    for a in env_args() {', '        print("arg {a}")', '    }', '}']
    for k, line in enumerate(src):
        m.command(f"echo '{line}' {'>' if k == 0 else '>>'} /root/px92args.lu", 'D2-source')
    s = m.command('cat /root/px92args.lu', 'D2-source')
    if any(l not in s for l in src):
        fail('D2-source', f'the source as typed is not the program; screen:\\n{s}')
    t0 = time.monotonic()
    s = m.command('cd /root; wolf build px92args.lu; echo PX92-B-$?', 'D2-build', 900)
    secs = time.monotonic() - t0
    m.shot('wolf-build')
    if 'PX92-B-0' not in m.unwrapped(s):
        fail('D2-build', f'`wolf build px92args.lu` did not exit 0; screen:\\n{s}')
    result['dev_build_seconds'] = round(secs, 2)
    print(f'PASS D2-build: `wolf build px92args.lu` on the installed 860, status 0, {secs:.1f} s', flush=True)
    s = m.command('./px92args one two; echo PX92-R-$?', 'D3-run', 300)
    m.shot('run-args')
    flat = m.unwrapped(s).split('./px92args one two; echo PX92-R-$?')[-1]
    got = [l.strip() for l in flat.split('\\n') if l.strip()]
    if got[:3] != ['arg one', 'arg two', 'PX92-R-0']:
        fail('D3-run', f'want arg one, arg two, status 0; got {got[:4]!r}; screen:\\n{s}')
    result['dev_run'] = got[:3]
    print("PASS D3-run: `./px92args one two` printed 'arg one', 'arg two', status 0", flush=True)
    # D4: the same through `wolf run` (a directory of its own: a directory's .lu files are one module).
    m.command('mkdir -p /root/px92c', 'D4-source')
    for k, line in enumerate(['fn main() {', '    let a = env_args()', '    print("count {a.len}")', '}']):
        m.command(f"echo '{line}' {'>' if k == 0 else '>>'} /root/px92c/count.lu", 'D4-source')
    s = m.command('cd /root/px92c; wolf run count.lu one two; echo PX92-W-$?; cd /root', 'D4-wolf-run', 900)
    m.shot('wolf-run-count')
    flat = m.unwrapped(s).split('wolf run count.lu one two; echo PX92-W-$?; cd /root')[-1]
    got = [l.strip() for l in flat.split('\\n') if l.strip()]
    if got[:2] != ['count 2', 'PX92-W-0']:
        fail('D4-wolf-run', f'want count 2, status 0; got {got[:3]!r}; screen:\\n{s}')
    result['dev_wolf_run'] = got[:2]
    print("PASS D4-wolf-run: `wolf run count.lu one two` printed 'count 2', status 0", flush=True)


def boot0(d, stick):
""")

edit("""        need(s, 'wolf', 'M8-witness-read')
""", """        need(s, 'wolf', 'M8-witness-read')
        if DEV:
            dev_rows(m)
""")

for old, new in EDITS:
    n = text.count(old)
    assert n == 1, (n, old[:120])
    text = text.replace(old, new)
out.write_text(text)
print(f'{out}: {len(EDITS)} edits, each applied once')
