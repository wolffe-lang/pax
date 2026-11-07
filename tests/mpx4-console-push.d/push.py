#!/usr/bin/env python3
"""tests/mpx4-console-push.d/push.py — one boot of the console's push rows (px104).

    push.py --way names|https|ssh|live --images DIR --elf KERNEL.elf --tier T
            --leg L --accel A --out DIR

DIR (--images) is what tests/mpx4-console-push built: root/ (the image's
tree), hermetic.pax-net, live.pax-net, den-src/ (den's tree at user/den.pin,
for its smart-HTTP fixture), linux/ (dgramopts and gai for this host), and
present.txt (the pieces the tree could build). Each boot gets its own
initramfs and ISO under OUT, a secrets carrier and its fixtures; the session
is typed by console.py, whose transcript is scrubbed before it is written.

The secrets carrier (R-px104-3): a 0700 directory /dev/shm/px104-<nonce>/
(the work directory when there is no /dev/shm) holding d/name, d/token and
d/key (0600) and secrets.img, an ext2 volume labelled px104-live made from
d/ by mke2fs -d, given to QEMU read-only as a virtio disk; the image's
/etc/fstab mounts it at /run/live. The session reads it only by redirection.
Hermetic ways make fake secrets (a name, a token, an ssh key from
ssh-keygen); the live way copies the three files PAX_LIVE_NAME_FILE,
PAX_LIVE_TOKEN_FILE and PAX_LIVE_KEY_FILE name. The carrier is removed after
the boot and checked gone; then tools/secret-scan, with the carrier's own
copy read first, scans everything the boot wrote: 0 files in every class.

Ways and rows (each printed `PASS <row> …` or `FAIL <row> …` at column 0):
  names  igb, a static address with this host as its DNS server (10.0.2.2:53,
         tools/dns-fixture: github.com is 10.0.2.2, everything else
         NXDOMAIN; root), /etc/hosts naming hosts.test (the C library reads it
       first, with no /etc/nsswitch.conf: measured, notes/px104/probes.txt):
    N1 dgramopts' output byte-identical to the same binary's on this host;
    N2 gai github.com hosts.test nosuch.test 10.0.2.2: the fixture's
       address, /etc/hosts' address, EAI_NONAME, the literal; the fixture
       saw the guest's A and AAAA questions for github.com and none for
       hosts.test.
  https  the same network; den's own smart-HTTP fixture (its
         tools/http-git-test.py Server: OpenSSL's s_server and
         git-http-backend, black boxes) with a leaf for DNS:github.com from a
         test root, behind Basic credentials (the carrier's token); the
         session's roots are the image's /etc/ssl/certs/ca-roots.der with the
         test root appended:
    H8 the shipped set alone: `TLS issuer_mismatch`, by the client's name;
    H1 den clone https://github.com:PORT/remote.git, its log git's;
    H2 a commit, its id the one git makes on this host for the same steps;
    H3 den push (the token from the carrier), and this host's git ls-remote
       sees the ref at that id;
    H4 den fetch of the ref into a scratch ref, den rev-parse of it: the id;
    H5 den push of the ref's deletion, and ls-remote no longer sees it;
    H6 den fetch of the ref fails, and no scratch ref is made;
    H7 this host's git, the same steps against the same fixture: the same
       statuses (zero or not) and the same ids.
  ssh    the same network; OpenSSH's sshd (a black box) on this host,
         its authorized key the carrier's (a forced command records the
         command den sends and runs it in the fixture's root with git's
         services); the guest's ~/.ssh: the carrier's key, a config naming
         Port, HostKeyAlias px104-fixture and both known_hosts files:
    S0 from a console shell (ENV=/etc/shrc), den push over ssh sends git's
       own command: `git-receive-pack 'wolffe-lang/NAME.git'`;
    S8 ssh -o HostKeyAlias=github.com: the fixture's key against the image's
       /etc/ssh/ssh_known_hosts (GitHub's published key): `host_key_changed`;
    S9 burrow-keygen -t ed25519, and -y reading it back;
    S1-S7 as H1-H7, through burrow (/bin/ssh).
  live   the fixture on GitHub (PAX_LIVE_*): skipped by name without them,
         and refused unless this run's https and ssh ways (their canaries)
         passed first. igb on QEMU's user network with its DHCP and DNS; the
         remote made by pelt's printf in .git/config (R-px104-3 (ii): the
         URL on no argv), for https and then ssh:
    L1 den fetch; L2 den switch -c onto the default branch; L3 a commit,
    the id git makes; L4 den push to refs/heads/px104-live/<nonce>/<way>
    and ls-remote sees it; L5 den fetch into a scratch ref; L6 the deletion,
    ls-remote empty; L7 den fetch fails. This host's git, the same steps on
    refs/heads/px104-live/<nonce>/git-<way>; anything of <nonce> left on
    the fixture is deleted at the end, whatever happened.
  every way:
    K1 the canary: the session prints the carrier's three files on purpose;
       the transcript holds the three placeholders there, and the scan finds
       no secret in any file the boot wrote;
    C1 the session: every line typed, halted.
Exit 0 when every row held, 1 otherwise, 2 on a setup error; 3 when the way
was skipped (named on stdout).
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GUEST_HOST = '10.0.2.2'
MAC = '52:54:00:12:34:56'
PROMPT = '$ '
ORG = 'wolffe-lang'
IDENT = dict(GIT_AUTHOR_NAME='PAX Tester', GIT_AUTHOR_EMAIL='pax@example.invalid',
             GIT_COMMITTER_NAME='PAX Tester', GIT_COMMITTER_EMAIL='pax@example.invalid',
             GIT_AUTHOR_DATE='1700000600 +0000', GIT_COMMITTER_DATE='1700000600 +0000')
SEED = dict(IDENT, GIT_AUTHOR_DATE='1700000000 +0000', GIT_COMMITTER_DATE='1700000000 +0000')
FAILS = []


def say(line):
    print(line, flush=True)


def ok(row, why):
    say('PASS %s %s' % (row, why))


def bad(row, why):
    FAILS.append(row)
    say('FAIL %s %s' % (row, why))


def run(argv, env=None, cwd=None, data=b'', timeout=300, check=True):
    r = subprocess.run([str(x) for x in argv], env=env, cwd=cwd, input=data, capture_output=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError('%s: exit %d: %s' % (' '.join(map(str, argv[:3])), r.returncode, r.stderr.decode(errors='replace')[-400:]))
    return r


def base_env(home):
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(home), LC_ALL='C', TZ='UTC0',
               GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false',
               TMPDIR=os.environ.get('TMPDIR', '/tmp'))
    env.update(IDENT)
    return env


# ---------------------------------------------------------------- the carrier

def carrier(way, work):
    """The 0700 carrier directory with d/{name,token,key} (0600)."""
    shm = Path('/dev/shm')
    parent = shm if shm.is_dir() and os.access(shm, os.W_OK) else work
    c = parent / ('px104-' + secrets.token_hex(8))
    c.mkdir(mode=0o700)
    os.chmod(c, 0o700)
    d = c / 'd'
    d.mkdir(mode=0o700)
    old = os.umask(0o077)
    try:
        if way == 'live':
            for n, v in (('name', 'PAX_LIVE_NAME_FILE'), ('token', 'PAX_LIVE_TOKEN_FILE'), ('key', 'PAX_LIVE_KEY_FILE')):
                shutil.copyfile(os.environ[v], d / n)
                os.chmod(d / n, 0o600)
            # The fixture's name and token are single lines; the copy keeps
            # exactly what the session reads (no trailing newline added).
            for n in ('name', 'token'):
                (d / n).write_bytes((d / n).read_bytes().strip())
        else:
            (d / 'name').write_bytes(b'px104-canary-' + secrets.token_hex(6).encode())
            (d / 'token').write_bytes(secrets.token_hex(20).encode())
            run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', '', '-f', d / 'key'])
            (d / 'key.pub').rename(c / 'key.pub')
        for n in ('name', 'token', 'key'):
            os.chmod(d / n, 0o600)
        run(['mke2fs', '-q', '-t', 'ext2', '-L', 'px104-live', '-d', d, c / 'secrets.img', '1M'],
            env=dict(PATH='/usr/sbin:/sbin:/usr/bin:/bin', E2FSPROGS_FAKE_TIME='1700000000'))
        os.chmod(c / 'secrets.img', 0o600)
    finally:
        os.umask(old)
    return c


def remove_carrier(c):
    shutil.rmtree(c, ignore_errors=True)
    return not c.exists()


# ---------------------------------------------------------------- the session's blocks

def blocks(log):
    """`ROW <name>` markers and each `s` block after them: name -> [ (status, out, err) ]."""
    text = log.replace('\r', '')
    rows = {}
    current = None
    lines = [l for l in text.split('\n') if not KERNEL.match(l)]
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.fullmatch(r'ROW ([A-Z][0-9]+)', line)
        if m:
            current = m.group(1)
            rows.setdefault(current, [])
        m = re.fullmatch(r'status (\d+)', line)
        if m and current:
            out, err, j = [], [], i + 1
            while j < len(lines) and lines[j] != '[stderr]':
                out.append(lines[j])
                j += 1
            j += 1
            while j < len(lines) and not lines[j].startswith(PROMPT) and not lines[j].startswith('user: ') \
                    and not re.fullmatch(r'(ROW [A-Z][0-9]+|STEP:.*|status \d+)', lines[j]):
                err.append(lines[j])
                j += 1
            rows[current].append((int(m.group(1)), out, err))
            i = j
            continue
        i += 1
    return rows


def between(log, a, b):
    t = log.replace('\r', '')
    s = t.rfind('\n' + a + '\n')
    e = t.find('\n' + b + '\n', s + 1)
    return t[s + len(a) + 2:e] if s >= 0 and e >= 0 else None


KERNEL = re.compile(r'(user|unix|net|dhcp|ip|tcp|udp|loopback|network|frames|fstab|ext2|vblk|block|PAX|refused): ')


PRELUDE = r"""export LC_ALL=C TZ=UTC GIT_CONFIG_NOSYSTEM=1 GIT_EDITOR=false GIT_PAGER=cat PAGER=cat COLUMNS=80
export GIT_AUTHOR_NAME='PAX Tester' GIT_AUTHOR_EMAIL=pax@example.invalid
export GIT_COMMITTER_NAME='PAX Tester' GIT_COMMITTER_EMAIL=pax@example.invalid
export GIT_AUTHOR_DATE='1700000600 +0000' GIT_COMMITTER_DATE='1700000600 +0000'
O=/tmp/o; mkdir -p $O; cd /tmp
s() { "$@" >$O/o 2>$O/e; echo "status $?"; cat $O/o; echo "[stderr]"; cat $O/e; }
echo "SESSION:"begin
echo "roots=$DEN_TLS_ROOTS upload=$DEN_UPLOAD_PACK receive=$DEN_RECEIVE_PACK"
ls -l /run/live
N=$(cat /run/live/name)"""

CANARY = r"""cd /tmp
echo "CANARY:"begin; cat /run/live/name; echo; cat /run/live/token; echo; cat /run/live/key; echo "CANARY:"end
echo "SESSION:"end
exit"""


def canary_row(log, secretsdir):
    body = between(log, 'CANARY:begin', 'CANARY:end')
    if body is None:
        bad('K1', 'no CANARY:begin … CANARY:end block in the transcript')
        return
    want = ['<scrubbed:name>', '<scrubbed:token>', '<scrubbed:key>']
    missing = [w for w in want if w not in body]
    if missing:
        bad('K1', 'the canary block lacks %s' % ' '.join(missing))
    else:
        ok('K1', 'the canary block holds the three placeholders')


# ---------------------------------------------------------------- images

def image(images, out, tag, extra, paxnet):
    """An initramfs and ISO of the built root (images/files.txt: tools/mkinitramfs'
    arguments, one a line) plus EXTRA (guest path -> (host file, mode)) and the
    way's /etc/pax-net."""
    files = [l for l in (images / 'files.txt').read_text().splitlines() if l]
    for g, (h, mode) in extra.items():
        files.append('%s=%s:%s' % (g, h, mode))
    files.append('/etc/pax-net=%s:644' % (images / paxnet))
    run([ROOT / 'tools/mkinitramfs', out / (tag + '.cpio')] + files)
    run([ROOT / 'tools/mkimage', '--conf', ROOT / 'boot/limine-initramfs-quiet.conf', '--add', out / (tag + '.cpio'),
         'initramfs.cpio', ARGS.elf, out / (tag + '.iso')])
    return out / (tag + '.iso')


def boot(out, iso, keys, c, qemu, hooks):
    (out / 'session.keys').write_text('\n'.join(keys) + '\n')
    cmd = [sys.executable, '-I', HERE / 'console.py', '--run', c / 'run', '--log', out / 'serial.log',
           '--keys', out / 'session.keys', '--prompt', PROMPT, '--iso', iso, '--leg', ARGS.leg,
           '--accel', ARGS.accel, '--timeout', '1500', '--secrets', c / 'd', '--drive', c / 'secrets.img']
    for label, prog in hooks.items():
        cmd += ['--hook', '%s=%s' % (label, prog)]
    cmd += ['--', '-m', '1024M'] + qemu
    r = subprocess.run([str(x) for x in cmd], capture_output=True, timeout=1800)
    text = r.stdout.decode(errors='replace')
    for line in text.splitlines():
        say('  console: ' + line)
    if r.returncode == 0:
        ok('C1', 'the session typed and halted (%s)' % ARGS.way)
    else:
        # The driver's own error, through the same scrub as the transcript.
        spec = importlib.util.spec_from_file_location('console_driver', HERE / 'console.py')
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        err = driver.Scrub(str(c / 'd')).text(r.stderr).decode(errors='replace').strip().splitlines()
        for line in err[-6:]:
            say('  console stderr: ' + line)
        bad('C1', 'the session: %s' % (text.strip().splitlines() or err[-1:] or ['no output'])[-1])
    return (out / 'serial.log').read_bytes().decode(errors='replace') if (out / 'serial.log').exists() else ''


def user_net(fwd=''):
    return ['-netdev', 'user,id=n0,ipv6=off' + fwd, '-device', 'igb,netdev=n0,mac=' + MAC]


# ---------------------------------------------------------------- the DNS fixture

class Dns:
    def __init__(self, out, names):
        self.log = out / 'dns.log'
        cmd = [sys.executable, '-I', ROOT / 'tools/dns-fixture', '--bind', '127.0.0.1:53', '--log', self.log,
               '--deadline', '3000'] + ['%s=%s' % kv for kv in names.items()]
        if os.getuid() != 0:
            cmd = ['sudo', '-n', '--preserve-env=PATH'] + cmd
        self.p = subprocess.Popen([str(x) for x in cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        line = self.p.stdout.readline().decode().strip()
        if not line.startswith('LISTENING'):
            raise RuntimeError('the DNS fixture did not start: ' + line)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)
        return self.log.read_text() if self.log.exists() else ''


def fixtures_ok():
    if os.getuid() == 0:
        return ''
    if subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0:
        return ''
    return 'the DNS fixture binds 127.0.0.1:53: root, or sudo -n'


# ---------------------------------------------------------------- names

def way_names(out, images, c):
    dns = Dns(out, {'github.com': GUEST_HOST})
    try:
        keys = PRELUDE.splitlines() + [
            'echo ROW N1; s /bin/dgramopts',
            'echo ROW N2; s /bin/gai github.com hosts.test nosuch.test 10.0.2.2',
        ] + CANARY.splitlines()
        iso = image(images, out, 'names', {}, 'hermetic.pax-net')
        log = boot(out, iso, keys, c, user_net(), {})
    finally:
        queries = dns.close()
    b = blocks(log)
    linux = run([images / 'linux/dgramopts'], check=False, timeout=60)
    want = (linux.returncode, linux.stdout.decode().splitlines(), [])
    got = (b.get('N1') or [None])[0]
    if got is None:
        bad('N1', 'no dgramopts block in the transcript')
    elif got != want:
        diff = [l for l in got[1] if l not in want[1]][:4]
        bad('N1', 'dgramopts at the console differs from this host\'s: status %d (host %d); first lines only at the console: %s; stderr %s'
            % (got[0], want[0], diff, got[2][:2]))
    else:
        ok('N1', 'dgramopts: %d lines, byte-identical to this host\'s' % len(want[1]))
    got = (b.get('N2') or [None])[0]
    want2 = ['gai github.com: inet 10.0.2.2:443', 'gai hosts.test: inet 10.0.2.2:443',
             'gai nosuch.test: EAI_NONAME', 'gai 10.0.2.2: inet 10.0.2.2:443']
    asked = [l.split(' ', 3)[3] for l in queries.splitlines() if l.startswith('QUERY ')]
    if got is None:
        bad('N2', 'no gai block in the transcript')
    elif got[1] != want2 or got[0] != 0:
        bad('N2', 'gai at the console: status %d, %s' % (got[0], got[1]))
    elif 'A github.com -> 10.0.2.2' not in asked or 'AAAA github.com -> NODATA' not in asked:
        bad('N2', 'the DNS fixture did not answer the guest\'s A and AAAA questions for github.com: %s' % asked)
    elif any('hosts.test' in q for q in asked):
        bad('N2', 'hosts.test was asked of DNS: /etc/hosts was not read first (%s)' % asked)
    else:
        ok('N2', 'github.com from the DNS fixture (%s), hosts.test from /etc/hosts alone, nosuch.test EAI_NONAME' % ', '.join(sorted(set(asked))))
    return log


# ---------------------------------------------------------------- https and ssh, hermetic

def seed_repo(work, git, env, bare):
    src = work / 'seed'
    run([git, 'init', '-q', '-b', 'main', src], env=env)
    (src / 'file').write_text('first\n')
    run([git, 'add', 'file'], env=env, cwd=src)
    run([git, 'commit', '-q', '-m', 'base'], env=dict(env, **SEED), cwd=src)
    (src / 'file').write_text('first\nsecond\n')
    run([git, 'commit', '-q', '-a', '-m', 'forward'], env=dict(env, **SEED), cwd=src)
    bare.parent.mkdir(parents=True, exist_ok=True)
    run([git, 'clone', '-q', '--bare', src, bare], env=env)
    run([git, '-C', bare, 'config', 'http.receivepack', 'true'], env=env)
    return run([git, 'log', '--oneline'], env=env, cwd=src).stdout.decode().splitlines()


def git_steps(git, env, alias, work, ref, base=None):
    """This host's git, the session's steps: [(step, status, out)]."""
    w = work / ('git-' + ref.replace('/', '-'))
    shutil.rmtree(w, ignore_errors=True)
    res = []

    def step(name, argv, cwd):
        r = run([git] + argv, env=env, cwd=cwd, check=False, timeout=300)
        res.append((name, r.returncode, r.stdout.decode().strip()))
        return r
    if base is None:
        step('clone', ['clone', '-q', alias, w], work)
    else:
        w.mkdir()
        step('init', ['init', '-q'], w)
        step('remote', ['remote', 'add', 'origin', alias], w)
        step('fetch', ['fetch', '-q', 'origin'], w)
        step('switch', ['switch', '-q', '-c', 'px104-work', 'origin/' + base], w)
    if not w.is_dir() or any(rc for _, rc, _ in res):
        return res  # the rest needs a working clone: the row names what failed
    (w / FILE).write_text('from the console\n')
    step('add', ['add', FILE], w)
    step('commit', ['commit', '-q', '-m', MESSAGE], w)
    step('rev-parse', ['rev-parse', 'HEAD'], w)
    step('push', ['push', '-q', 'origin', 'HEAD:refs/heads/' + ref], w)
    step('fetch-seen', ['fetch', '-q', 'origin', 'refs/heads/%s:refs/heads/px104-seen' % ref], w)
    step('rev-parse-seen', ['rev-parse', 'px104-seen'], w)
    step('delete', ['push', '-q', 'origin', ':refs/heads/' + ref], w)
    step('fetch-gone', ['fetch', '-q', 'origin', 'refs/heads/%s:refs/heads/px104-gone' % ref], w)
    step('rev-parse-gone', ['rev-parse', '--verify', '-q', 'px104-gone'], w)
    return res


FILE = 'px104.txt'
MESSAGE = 'px104: a commit from the console'


def den_steps(prefix, url_line, ref, clone=True, base=None):
    """The session's typed lines for one transport. Every `s` is one block."""
    k = []
    if clone:
        k += ['echo ROW %s1; s den clone -q %s c%s' % (prefix, url_line, prefix), 'cd c' + prefix,
              's den log --oneline --no-decorate']
    else:
        k += ['den init w%s >/dev/null; cd w%s' % (prefix, prefix), url_line,
              'echo ROW %s1; s den fetch -q origin' % prefix,
              'echo ROW %s2; s den switch -q -c px104-work origin/%s' % (prefix, base)]
    n = 2 if clone else 3
    k += ["printf 'from the console\\n' > %s" % FILE,
          'echo ROW %s%d; s den add %s; s den commit -q -m %s; s den rev-parse HEAD' % (prefix, n, FILE, sh_quote(MESSAGE)),
          'echo ROW %s%d; s den push -q origin HEAD:refs/heads/%s' % (prefix, n + 1, ref),
          'echo STEP:"%s-pushed"' % prefix,
          'echo ROW %s%d; s den fetch -q origin refs/heads/%s:refs/heads/px104-seen; s den rev-parse px104-seen' % (prefix, n + 2, ref),
          'echo ROW %s%d; s den push -q origin :refs/heads/%s' % (prefix, n + 3, ref),
          'echo STEP:"%s-deleted"' % prefix,
          'echo ROW %s%d; s den fetch -q origin refs/heads/%s:refs/heads/px104-gone; s den rev-parse --verify -q px104-gone' % (prefix, n + 4, ref),
          'cd /tmp']
    return k


def sh_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def hook(c, name, git, env, alias, pattern):
    """A host program the console runs at STEP:name: git ls-remote ALIAS PATTERN."""
    p = c / 'run' / ('hook-' + name)
    p.parent.mkdir(mode=0o700, exist_ok=True)
    lines = ['#!/bin/sh']
    for k, v in sorted(env.items()):
        lines.append('export %s=%s' % (k, sh_quote(v)))
    lines.append('exec %s ls-remote %s %s' % (sh_quote(str(git)), sh_quote(alias), sh_quote(pattern)))
    p.write_text('\n'.join(lines) + '\n')
    os.chmod(p, 0o700)
    return p


def hooks_seen(out):
    p = out / 'serial.log.hooks'
    t = p.read_text(errors='replace') if p.exists() else ''
    res = {}
    for part in t.split('HOOK ')[1:]:
        head, _, body = part.partition('\n')
        name, _, code = head.partition(' exit=')
        res[name] = (int(code or -1), body.split('FILE com1')[0].split('QEMU-RUN')[0].strip())
    return res


def judge(prefix, b, hooks, gitres, ref, clone_log=None, live=False):
    """H/S/L rows 1-7 from the session's blocks and the hooks' answers."""
    n0 = 0 if clone_log is not None else 1
    def blk(i):
        return b.get('%s%d' % (prefix, i)) or []
    if clone_log is not None:
        c = blk(1)
        if len(c) < 2 or c[0][0] != 0:
            bad(prefix + '1', 'den clone: %r' % ((c[0] if c else 'no block'),))
        elif c[1][1] != clone_log:
            bad(prefix + '1', 'den log after the clone %s, git\'s %s' % (c[1][1], clone_log))
        else:
            ok(prefix + '1', 'den clone exit 0 and its log is git\'s (%d commits)' % len(clone_log))
    else:
        f, s_ = blk(1), blk(2)
        if not f or f[0][0] != 0:
            bad(prefix + '1', 'den fetch: %r' % ((f[0] if f else 'no block'),))
        else:
            ok(prefix + '1', 'den fetch exit 0')
        if not s_ or s_[0][0] != 0:
            bad(prefix + '2', 'den switch: %r' % ((s_[0] if s_ else 'no block'),))
        else:
            ok(prefix + '2', 'den switch -c onto the default branch, exit 0')
    k = 2 if clone_log is not None else 3
    g = {name: (rc, o) for name, rc, o in gitres}
    commit = blk(k)
    oid = commit[2][1][0] if len(commit) == 3 and commit[2][1] else ''
    if len(commit) != 3 or any(x[0] for x in commit):
        bad(prefix + str(k), 'den add, commit, rev-parse: %s' % [x[0] for x in commit])
    elif oid != g.get('rev-parse', (1, ''))[1]:
        bad(prefix + str(k), 'den\'s commit %s, git\'s %s' % (oid, g.get('rev-parse')))
    else:
        ok(prefix + str(k), 'the commit %s, the id git makes for the same steps' % oid)
    p = blk(k + 1)
    seen = hooks.get(prefix + '-pushed', (-1, ''))
    if not p or p[0][0] != 0:
        bad(prefix + str(k + 1), 'den push: %r' % ((p[0] if p else 'no block'),))
    elif seen[0] != 0 or seen[1] != '%s\trefs/heads/%s' % (oid, ref):
        bad(prefix + str(k + 1), 'den push exit 0, but this host\'s ls-remote said %s' % (seen,))
    else:
        ok(prefix + str(k + 1), 'den push exit 0; ls-remote sees refs/heads/%s at %s' % (ref, oid[:12]))
    f = blk(k + 2)
    if len(f) != 2 or f[0][0] or f[1][0] or f[1][1] != [oid]:
        bad(prefix + str(k + 2), 'den fetch of the ref, rev-parse: %s' % [(x[0], x[1]) for x in f])
    else:
        ok(prefix + str(k + 2), 'den fetch of the pushed ref into a scratch ref: %s' % oid[:12])
    d = blk(k + 3)
    gone = hooks.get(prefix + '-deleted', (-1, 'x'))
    if not d or d[0][0] != 0:
        bad(prefix + str(k + 3), 'den push of the deletion: %r' % ((d[0] if d else 'no block'),))
    elif gone[0] not in (0, 2) or gone[1] != '':
        bad(prefix + str(k + 3), 'the deletion: this host\'s ls-remote said %s' % (gone,))
    else:
        ok(prefix + str(k + 3), 'den push of the deletion exit 0; ls-remote empty')
    f = blk(k + 4)
    if len(f) != 2 or f[0][0] == 0 or f[1][0] == 0:
        bad(prefix + str(k + 4), 'den fetch of the deleted ref: %s' % [(x[0], x[1], x[2]) for x in f])
    else:
        ok(prefix + str(k + 4), 'den fetch of the deleted ref fails (%d: %s), no scratch ref' % (f[0][0], ' '.join(f[0][2])[:80]))
    # The same steps by this host's git.
    want_zero = ['clone'] if clone_log is not None else ['init', 'remote', 'fetch', 'switch']
    want_zero += ['add', 'commit', 'rev-parse', 'push', 'fetch-seen', 'rev-parse-seen', 'delete']
    gz = [name for name in want_zero if g.get(name, (1, ''))[0] != 0]
    gr = prefix + str(k + 5)
    if gz or g.get('fetch-gone', (0, ''))[0] == 0 or g.get('rev-parse-gone', (0, ''))[0] == 0:
        bad(gr, 'this host\'s git: %s' % gitres)
    elif g['rev-parse'][1] != oid or g['rev-parse-seen'][1] != oid:
        bad(gr, 'this host\'s git made %s and fetched %s, den %s' % (g['rev-parse'][1], g['rev-parse-seen'][1], oid))
    else:
        ok(gr, 'this host\'s git, the same steps: every status den\'s (zero, then the deleted ref\'s fetch not), the same id')


def way_https(out, images, c, den_src, git):
    spec = importlib.util.spec_from_file_location('den_http_git', den_src / 'tools/http-git-test.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    work = c / 'fixture'
    work.mkdir(mode=0o700)
    home = work / 'home'
    home.mkdir()
    env = base_env(home)
    pki = work / 'pki'
    pki.mkdir()
    ossl = lambda *x: run(['/usr/bin/openssl'] + list(x), env=env)
    ossl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', '2', '-subj', '/CN=PAX console push test root',
         '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign',
         '-keyout', pki / 'ca.key', '-out', pki / 'ca.pem')
    ossl('x509', '-in', pki / 'ca.pem', '-outform', 'DER', '-out', pki / 'ca.der')
    (pki / 'leaf.cnf').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n'
                                  'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:github.com\n')
    ossl('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=github.com', '-keyout', pki / 'leaf.key', '-out', pki / 'leaf.csr')
    ossl('x509', '-req', '-in', pki / 'leaf.csr', '-CA', pki / 'ca.pem', '-CAkey', pki / 'ca.key', '-CAcreateserial',
         '-days', '1', '-sha256', '-extfile', pki / 'leaf.cnf', '-out', pki / 'leaf.pem')
    root = work / 'root'
    root.mkdir()
    log0 = seed_repo(work, git, env, root / 'remote.git')
    token = (c / 'd/token').read_text()
    shipped = images / 'root/etc/ssl/certs/ca-roots.der'
    rows_roots = work / 'rows-roots.der'
    rows_roots.write_bytes((shipped.read_bytes() if shipped.exists() else b'') + (pki / 'ca.der').read_bytes())
    server = fixture.Server(root, git, env, 'tls', pki, token, lambda data: None)
    dns = Dns(out, {'github.com': GUEST_HOST})
    try:
        port = server.port
        url = 'https://github.com:%d/remote.git' % port
        # This host's git: the same URL through an alias, its name pinned to
        # this host's loopback, its trust the test root, the token in a
        # header of a 0600 configuration in the carrier.
        cfg = c / 'gitconfig'
        basic = base64.b64encode(('x-access-token:' + token).encode()).decode()
        cfg.write_text('[url "%s"]\n\tinsteadOf = live-https:\n[http]\n\tsslCAInfo = %s\n\tcurloptResolve = github.com:%d:127.0.0.1\n'
                       '\textraHeader = Authorization: Basic %s\n[protocol]\n\tversion = 2\n' % (url, pki / 'ca.pem', port, basic))
        os.chmod(cfg, 0o600)
        genv = dict(env, GIT_CONFIG_GLOBAL=str(cfg))
        keys = PRELUDE.splitlines() + [
            'export DEN_HTTP_TOKEN="$(cat /run/live/token)"',
            'echo ROW H8; DEN_TLS_ROOTS=/etc/ssl/certs/ca-roots.der s den clone -q https://github.com:%d/remote.git c8' % port,
            'export DEN_TLS_ROOTS=/etc/ssl/rows-roots.der',
        ] + den_steps('H', 'https://github.com:%d/remote.git' % port, 'px104/pushed') + CANARY.splitlines()
        hooks = {'H-pushed': hook(c, 'H-pushed', git, genv, 'live-https:', 'refs/heads/px104/pushed'),
                 'H-deleted': hook(c, 'H-deleted', git, genv, 'live-https:', 'refs/heads/px104/*')}
        iso = image(images, out, 'https', {'/etc/ssl/rows-roots.der': (rows_roots, '644')}, 'hermetic.pax-net')
        log = boot(out, iso, keys, c, user_net(), hooks)
        gitres = git_steps(git, genv, 'live-https:', work, 'px104/git-pushed')
    finally:
        dns.close()
        server.close()
    b = blocks(log)
    h8 = (b.get('H8') or [None])[0]
    if h8 is None:
        bad('H8', 'no block')
    elif h8[0] == 0 or h8[2] != ['den: wire: Unsupported(TLS issuer_mismatch)']:
        bad('H8', 'the shipped set alone: status %d, %s' % (h8[0], h8[2][:2]))
    else:
        ok('H8', 'the shipped set alone refuses the test root\'s leaf: den: wire: Unsupported(TLS issuer_mismatch)')
    judge('H', b, hooks_seen(out), gitres, 'px104/pushed', clone_log=log0)
    if server.errors:
        bad('H0', 'the fixture\'s own errors: %s' % server.errors[:3])
    return log


SSHD = """Port {port}
ListenAddress 127.0.0.1
HostKey {d}/host_ed25519
PidFile {d}/sshd.pid
AuthorizedKeysFile {d}/authorized_keys
StrictModes no
UsePAM no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
AcceptEnv GIT_PROTOCOL
LogLevel VERBOSE
"""

RECORD = """#!/bin/sh
# The fixture's forced command: record what the client asked, then run it
# in the fixture's root with this host's git services first on PATH.
printf '%s\\n' "$SSH_ORIGINAL_COMMAND" >> {d}/commands.log
cd {root} || exit 1
exec /bin/sh -c "$SSH_ORIGINAL_COMMAND"
"""


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def way_ssh(out, images, c, git):
    work = c / 'fixture'
    work.mkdir(mode=0o700)
    home = work / 'home'
    home.mkdir()
    env = base_env(home)
    d = work / 'sshd'
    d.mkdir(mode=0o700)
    root = work / 'root'
    name = (c / 'd/name').read_text()
    log0 = seed_repo(work, git, env, root / ORG / (name + '.git'))
    user = run(['id', '-un']).stdout.decode().strip()
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', '', '-f', d / 'host_ed25519'], env=env)
    host_line = (d / 'host_ed25519.pub').read_text().split()
    pub = (c / 'key.pub').read_text().split()
    (d / 'record-command').write_text(RECORD.format(d=d, root=root))
    os.chmod(d / 'record-command', 0o755)
    (d / 'authorized_keys').write_text('command="%s",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding %s %s\n'
                                       % (d / 'record-command', pub[0], pub[1]))
    port = free_port()
    (d / 'sshd_config').write_text(SSHD.format(port=port, d=d))
    if os.getuid() == 0:
        os.makedirs('/run/sshd', mode=0o755, exist_ok=True)
    sshd = subprocess.Popen(['/usr/sbin/sshd', '-D', '-e', '-f', str(d / 'sshd_config')], stdin=subprocess.DEVNULL,
                            stdout=open(d / 'sshd.log', 'wb'), stderr=subprocess.STDOUT)
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                break
        except OSError:
            if sshd.poll() is not None:
                raise RuntimeError('sshd ended: ' + (d / 'sshd.log').read_text()[-400:])
            time.sleep(0.1)
    (work / 'known_hosts').write_text('px104-fixture %s %s\n' % (host_line[0], host_line[1]))
    (work / 'ssh_config').write_text('Host github.com\n\tHostName 127.0.0.1\n\tPort %d\n\tUser %s\n\tIdentityFile %s\n'
                                     '\tIdentitiesOnly yes\n\tUserKnownHostsFile %s\n\tHostKeyAlias px104-fixture\n'
                                     '\tStrictHostKeyChecking yes\n\tBatchMode yes\n'
                                     % (port, user, c / 'd/key', work / 'known_hosts'))
    cfg = c / 'gitconfig'
    url = '%s@github.com:%s/%s.git' % (user, ORG, name)
    cfg.write_text('[url "%s"]\n\tinsteadOf = live-ssh:\n[core]\n\tsshCommand = ssh -F %s\n[protocol]\n\tversion = 2\n'
                   % (url, work / 'ssh_config'))
    os.chmod(cfg, 0o600)
    genv = dict(env, GIT_CONFIG_GLOBAL=str(cfg))
    dns = Dns(out, {'github.com': GUEST_HOST})
    try:
        u = '%s@github.com:%s/$N.git' % (user, ORG)
        keys = PRELUDE.splitlines() + [
            'mkdir -p ~/.ssh; chmod 700 ~/.ssh; cp /run/live/key ~/.ssh/id_ed25519; chmod 600 ~/.ssh/id_ed25519',
            "printf 'Host github.com\\n\\tPort %d\\n\\tHostKeyAlias px104-fixture\\n\\tUserKnownHostsFile ~/.ssh/known_hosts /etc/ssh/ssh_known_hosts\\n' > ~/.ssh/config" % port,
            "printf 'px104-fixture %s %s\\n' > ~/.ssh/known_hosts" % (host_line[0], host_line[1]),
            'echo ROW S9; s burrow-keygen -t ed25519 -q -f /tmp/k9; s burrow-keygen -y -f /tmp/k9',
            'echo ROW S8; s ssh -o HostKeyAlias=github.com -T %s@github.com' % user,
            'den init w0 >/dev/null; cd w0; printf one > a; den add a; den commit -q -m zero',
            'echo ROW S0; s den push -q %s HEAD:refs/heads/px104-zero' % u,
            'cd /tmp',
        ] + den_steps('S', u, 'px104/pushed') + CANARY.splitlines()
        hooks = {'S-pushed': hook(c, 'S-pushed', git, genv, 'live-ssh:', 'refs/heads/px104/pushed'),
                 'S-deleted': hook(c, 'S-deleted', git, genv, 'live-ssh:', 'refs/heads/px104/*')}
        iso = image(images, out, 'ssh', {}, 'hermetic.pax-net')
        log = boot(out, iso, keys, c, user_net(), hooks)
        gitres = git_steps(git, genv, 'live-ssh:', work, 'px104/git-pushed')
    finally:
        dns.close()
        sshd.terminate()
        sshd.wait(timeout=30)
    b = blocks(log)
    cmds = (d / 'commands.log').read_text().splitlines() if (d / 'commands.log').exists() else []
    s9 = b.get('S9') or []
    if len(s9) != 2 or s9[0][0] or s9[1][0] or not (s9[1][1] and re.fullmatch(r'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI[A-Za-z0-9+/]{43}( .*)?', s9[1][1][0])):
        bad('S9', 'burrow-keygen at the console: %s' % [(x[0], x[1][:1], x[2][:1]) for x in s9])
    else:
        ok('S9', 'burrow-keygen made an ed25519 key and -y read its public line back')
    s8 = (b.get('S8') or [None])[0]
    if s8 is None:
        bad('S8', 'no block')
    elif s8[0] != 255 or not any('host_key_changed' in l for l in s8[2]):
        bad('S8', 'ssh with HostKeyAlias github.com: status %d, %s' % (s8[0], s8[2][:2]))
    else:
        ok('S8', 'the fixture\'s key against /etc/ssh/ssh_known_hosts\' GitHub line: %s' % [l for l in s8[2] if 'host_key_changed' in l][0][:100])
    want0 = "git-receive-pack '%s/%s.git'" % (ORG, name)
    s0 = (b.get('S0') or [None])[0]
    first = cmds[0] if cmds else '(no command reached the fixture)'
    if s0 is None:
        bad('S0', 'no block')
    elif first != want0 or s0[0] != 0:
        bad('S0', 'from a console shell den sent %r (status %d); git sends %r' % (first.replace(name, '<name>'), s0[0], want0.replace(name, '<name>')))
    else:
        ok('S0', 'from a console shell den sent git\'s own command: git-receive-pack \'%s/<name>.git\'' % ORG)
    judge('S', b, hooks_seen(out), gitres, 'px104/pushed', clone_log=log0)
    # Every command den sent over ssh, after S0, is git's form; and what this
    # host's git sent for the same steps.
    forms = sorted(set(re.sub(r"'.*'", "'<path>'", x) for x in cmds))
    say('  the commands the fixture was sent: %s' % forms)
    return log


# ---------------------------------------------------------------- live

def way_live(out, images, c, git):
    name = (c / 'd/name').read_text()
    token = (c / 'd/token').read_text()
    nonce = secrets.token_hex(4)
    work = c / 'fixture'
    work.mkdir(mode=0o700)
    home = work / 'home'
    home.mkdir()
    env = base_env(home)
    # This host's git reaches the fixture through two aliases in a 0600
    # configuration of the carrier: no URL on any argument vector.
    kh = c / 'known_hosts'
    kh.write_bytes((ROOT / 'user/ssh_known_hosts').read_bytes())
    sshcfg = c / 'ssh_config'
    sshcfg.write_text('Host github.com\n\tIdentityFile %s\n\tIdentitiesOnly yes\n\tUserKnownHostsFile %s\n'
                      '\tStrictHostKeyChecking yes\n\tBatchMode yes\n' % (c / 'd/key', kh))
    cfg = c / 'gitconfig'
    basic = base64.b64encode(('x-access-token:' + token).encode()).decode()
    cfg.write_text('[url "https://github.com/%s/%s.git"]\n\tinsteadOf = live-https:\n[url "git@github.com:%s/%s.git"]\n'
                   '\tinsteadOf = live-ssh:\n[http "https://github.com/"]\n\textraHeader = Authorization: Basic %s\n'
                   '[core]\n\tsshCommand = ssh -F %s\n[protocol]\n\tversion = 2\n' % (ORG, name, ORG, name, basic, sshcfg))
    os.chmod(cfg, 0o600)
    for f in (kh, sshcfg):
        os.chmod(f, 0o600)
    genv = dict(env, GIT_CONFIG_GLOBAL=str(cfg))
    head = run([git, 'ls-remote', '--symref', 'live-https:', 'HEAD'], env=genv, check=False, timeout=120)
    m = re.search(r'ref: refs/heads/(\S+)\tHEAD', head.stdout.decode())
    if head.returncode or not m:
        bad('L0', 'this host\'s git could not read the fixture\'s default branch (exit %d)' % head.returncode)
        return ''
    base = m.group(1)
    ok('L0', 'the fixture\'s default branch read by this host\'s git (exit 0)')
    refs = {'L': 'px104-live/%s/https' % nonce, 'M': 'px104-live/%s/ssh' % nonce}
    keys = PRELUDE.splitlines() + [
        'export DEN_HTTP_TOKEN="$(cat /run/live/token)"',
    ] + den_steps('L', "printf '[remote \"origin\"]\\n\\turl = https://github.com/%s/%%s.git\\n\\tfetch = +refs/heads/*:refs/remotes/origin/*\\n' \"$N\" >> .git/config" % ORG,
                  refs['L'], clone=False, base=base) + [
        'mkdir -p ~/.ssh; chmod 700 ~/.ssh; cp /run/live/key ~/.ssh/id_ed25519; chmod 600 ~/.ssh/id_ed25519',
        "printf 'Host github.com\\n\\tUserKnownHostsFile ~/.ssh/known_hosts /etc/ssh/ssh_known_hosts\\n' > ~/.ssh/config",
    ] + den_steps('M', "printf '[remote \"origin\"]\\n\\turl = git@github.com:%s/%%s.git\\n\\tfetch = +refs/heads/*:refs/remotes/origin/*\\n' \"$N\" >> .git/config" % ORG,
                  refs['M'], clone=False, base=base) + CANARY.splitlines()
    hooks = {}
    for p, alias in (('L', 'live-https:'), ('M', 'live-ssh:')):
        hooks[p + '-pushed'] = hook(c, p + '-pushed', git, genv, alias, 'refs/heads/' + refs[p])
        hooks[p + '-deleted'] = hook(c, p + '-deleted', git, genv, alias, 'refs/heads/px104-live/%s/*' % nonce)
    iso = image(images, out, 'live', {}, 'live.pax-net')
    try:
        log = boot(out, iso, keys, c, user_net(), hooks)
        res = {'L': git_steps(git, genv, 'live-https:', work, 'px104-live/%s/git-https' % nonce, base=base),
               'M': git_steps(git, genv, 'live-ssh:', work, 'px104-live/%s/git-ssh' % nonce, base=base)}
    finally:
        # Whatever happened, nothing of this nonce stays on the fixture.
        left = run([git, 'ls-remote', 'live-https:', 'refs/heads/px104-live/%s/*' % nonce], env=genv, check=False, timeout=120)
        for line in left.stdout.decode().splitlines():
            ref = line.split('\t')[1]
            run([git, 'push', '-q', 'live-https:', ':' + ref], env=genv, check=False, timeout=120)
        final = run([git, 'ls-remote', 'live-https:', 'refs/heads/px104-live/%s/*' % nonce], env=genv, check=False, timeout=120)
        if final.returncode == 0 and not final.stdout.strip():
            ok('L9', 'nothing of this run is left on the fixture (ls-remote empty for its refs)')
        else:
            bad('L9', 'refs of this run left on the fixture: exit %d, %d lines' % (final.returncode, len(final.stdout.splitlines())))
    b = blocks(log)
    seen = hooks_seen(out)
    for p in ('L', 'M'):
        judge(p, b, seen, res[p], refs[p], clone_log=None, live=True)
    return log


# ---------------------------------------------------------------- main

def main():
    global ARGS
    a = argparse.ArgumentParser()
    for k in ('way', 'images', 'elf', 'tier', 'leg', 'accel', 'out'):
        a.add_argument('--' + k, required=True)
    ARGS = a.parse_args()
    images, out = Path(ARGS.images), Path(ARGS.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    way = ARGS.way
    L = '%s %s %s' % (ARGS.tier, ARGS.leg, way)
    if way == 'live':
        missing = [v for v in ('PAX_LIVE_NAME_FILE', 'PAX_LIVE_TOKEN_FILE', 'PAX_LIVE_KEY_FILE')
                   if not os.environ.get(v) or not os.path.isfile(os.environ[v])]
        if missing:
            say('SKIP %s reason=%s not set to a readable file' % (L, ' '.join(missing)))
            return 3
        if os.environ.get('PAX_PUSH_CANARY_GREEN') != '1':
            bad('L0', 'the live way runs only after this run\'s https and ssh ways (their canaries) passed')
            return 1
    else:
        why = fixtures_ok()
        if why:
            say('SKIP %s reason=%s' % (L, why))
            return 3
    for tool in ('mke2fs', 'ssh-keygen', 'git', '/usr/bin/openssl') + (('/usr/sbin/sshd',) if way == 'ssh' else ()):
        if not shutil.which(tool):
            say('SKIP %s reason=no %s on this host' % (L, tool))
            return 3
    git = shutil.which('git')
    c = carrier(way, out)
    log = ''
    held = {}
    try:
        try:
            if way == 'names':
                log = way_names(out, images, c)
            elif way == 'https':
                log = way_https(out, images, c, images / 'den-src', git)
            elif way == 'ssh':
                log = way_ssh(out, images, c, git)
            elif way == 'live':
                log = way_live(out, images, c, git)
        except Exception as e:  # the rows below still run: the carrier's end and the scan
            bad('P0', 'the way could not run: %s: %s' % (type(e).__name__, str(e)[:300]))
        canary_row(log, c / 'd')
    finally:
        # The secrets, held in memory for the scan alone; the carrier goes.
        for n in ('name', 'token', 'key'):
            p = c / 'd' / n
            held[n] = p.read_bytes() if p.exists() else b''
        held['name'], held['token'] = held['name'].strip(), held['token'].strip()
        under_shm = str(c).startswith('/dev/shm/')
        gone = remove_carrier(c)
    if gone:
        ok('K2', 'the carrier (0700, %s) removed and gone' % ('under /dev/shm' if under_shm else 'in the work directory'))
    else:
        bad('K2', 'the carrier is still there')
    spec = importlib.util.spec_from_loader('secret_scan', loader=None)
    scanner = importlib.util.module_from_spec(spec)
    exec(compile((ROOT / 'tools/secret-scan').read_text(), str(ROOT / 'tools/secret-scan'), 'exec'), scanner.__dict__)
    head, hits, rc = scanner.scan(held['name'], held['token'], held['key'], [out])
    held.clear()
    for line in hits:
        say('  ' + line)
    if rc == 0:
        ok('K3', 'everything this boot wrote: %s' % head)
    else:
        bad('K3', head)
    say('PUSH %s: %d rows failed%s' % (L, len(set(FAILS)), (': ' + ' '.join(sorted(set(FAILS)))) if FAILS else ''))
    return 1 if FAILS else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as e:
        say('FAIL P0 setup: %s' % e)
        sys.exit(2)
