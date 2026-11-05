#!/usr/bin/env python3
"""The remote session's own witness (tests/mpx5-den, px100): rows that
hold whatever both sides typed, so a wrapper, a variable or a transport
broken the same way on PAX and in the Linux container (where the
comparison alone stays green) is still red here, by name.

Usage: remote.py SESSION WORKDIR UID

SESSION is one session (tests/mpx5-den.d/region.py's output) typed from
user/console/den-remote.keys; WORKDIR the session's ext2 directory
(/home/den-root or /home/pax) and UID its user id (0 or 1000), from which
the keys derive the /tmp directory and the daemon's port. Prints one line
a failed row, `ROW: why`, and nothing when every row holds. Exit 0 either
way (the caller counts the lines), 2 on a malformed session.

The session has two places, each opened by its marker line: `den-place-tmp`
(the in-memory /tmp, the wrappers typed at the console) and `den-place-home`
(the ext2 disk, the wrappers the image installs, named by /etc/shrc). The
rows hold den's answers at its pin where they are fixed by Git's documented
words and den's README (the push and fetch reports, `branch ... set up to
track`, the fast-forward), the session's own ids (each commit's short id as
`commit` printed it, carried through every later report), and den's named
refusals (no service without the variables, `status` with an upstream, a
fetch with no daemon). Nothing here is checked against den's source.
"""
import re
import sys

PLACES = ('tmp', 'home')
ROWS = ['remote-shrc', 'remote-wrappers', 'remote-no-variable', 'remote-config', 'remote-status-limit'] + [
    'remote-%s-%s' % (r, p) for p in PLACES for r in (
        'clone-bare', 'add', 'push-u', 'push', 'clone', 'clone-push', 'fetch', 'pull', 'daemon-clone',
        'daemon-push', 'one-session', 'final-pull', 'refs', 'fsck')]
WRAP = {'upload-pack': ['#!/bin/sh', 'exec /bin/den upload-pack "$1"'],
        'receive-pack': ['#!/bin/sh', 'exec /bin/den receive-pack "$1"']}
LIBEXEC = '/usr/libexec/den'


def parse(lines):
    """[(command, output lines)]: a command is the text after a prompt."""
    blocks = []
    for line in lines:
        if line.startswith('$ '):
            cmd = line[2:]
            blocks.append([cmd[6:] if cmd.startswith('tick; ') else cmd, []])
        elif blocks:
            blocks[-1][1].append(line)
    return blocks


class S:
    """An `s CMD` block: its status, its stdout and its stderr."""
    def __init__(self, out):
        if not out or not re.fullmatch(r'status \d+', out[0]) or '[stderr]' not in out:
            raise ValueError('not an s block: %r' % out[:3])
        self.status = int(out[0].split()[1])
        k = out.index('[stderr]')
        self.out, self.err = out[1:k], out[k + 1:]


class Place:
    def __init__(self, name, blocks, bad):
        self.name, self.blocks, self.bad = name, blocks, bad

    def fail(self, row, why):
        self.bad.append('%s: %s' % (row, why))

    def raw(self, cmd, nth=1, row='?'):
        seen = [b for b in self.blocks if b[0] == cmd]
        if len(seen) < nth:
            self.fail(row, 'no `%s` (#%d) in the %s place' % (cmd, nth, self.name))
            return None
        return seen[nth - 1][1]

    def s(self, cmd, nth=1, row='?'):
        out = self.raw('s ' + cmd, nth, row)
        if out is None:
            return None
        try:
            return S(out)
        except ValueError as e:
            self.fail(row, str(e))
            return None

    def quiet(self, row, cmd, nth=1):
        """An `s CMD` that must say nothing and end 0; the block or None."""
        b = self.s(cmd, nth, row)
        if b is not None and (b.status != 0 or b.out or b.err):
            self.fail(row, '`%s`: status %d, %r, %r (want 0 and nothing)' % (cmd, b.status, b.out[:3], b.err[:3]))
            return None
        return b


def short_id(place, row, cmd, subject):
    """The short id `commit` printed for SUBJECT ([branch ID] subject)."""
    b = place.s(cmd, 1, row)
    if b is None:
        return None
    m = re.fullmatch(r'\[main (?:\(root-commit\) )?([0-9a-f]{7})\] ' + re.escape(subject), b.out[0] if b.out else '')
    if b.status != 0 or m is None:
        place.fail(row, '`%s`: status %d, %r' % (cmd, b.status, b.out[:1]))
        return None
    return m[1]


def place_rows(p, root, url, tmp, port):
    first = short_id(p, 'remote-push-u-' + p.name, "den commit -m 'first: a.txt'", 'first: a.txt')
    second = short_id(p, 'remote-push-u-' + p.name, "den commit -a -m 'second: two'", 'second: two')
    third = short_id(p, 'remote-push-' + p.name, "den commit -a -m 'third: three'", 'third: three')
    fourth = short_id(p, 'remote-clone-push-' + p.name, "den commit -m 'c2: c.txt'", 'c2: c.txt')
    fifth = short_id(p, 'remote-daemon-push-' + p.name, "den commit -m 'c3: d.txt'", 'c3: d.txt')
    hub = '%s/hub.git' % url
    r = 'remote-clone-bare-' + p.name
    p.quiet(r, 'den clone -q --bare %s/src hub.git' % url)
    if tmp:
        b = p.s('ls hub.git', 1, r)
        if b is not None and (b.status, b.out) != (0, ['HEAD', 'config', 'hooks', 'objects', 'refs']):
            p.fail(r, '`ls hub.git`: %d %r (a bare repository: HEAD config hooks objects refs)' % (b.status, b.out))
    r = 'remote-add-' + p.name
    p.quiet(r, 'den remote add origin %s' % hub)
    b = p.s('den remote -v', 1, r)
    want = ['origin\t%s (fetch)' % hub, 'origin\t%s (push)' % hub]
    if b is not None and (b.status, b.out, b.err) != (0, want, []):
        p.fail(r, '`remote -v`: %d %r %r, not %r' % (b.status, b.out, b.err, want))

    def report(row, cmd, old, new, nth=1, to=hub, out=()):
        b = p.s(cmd, nth, row)
        if b is None or None in (old, new):
            return
        want = ['To %s' % to, '   %s..%s  main -> main' % (old, new)]
        if (b.status, b.out, b.err) != (0, list(out), want):
            p.fail(row, '`%s`: %d %r %r, not %r' % (cmd, b.status, b.out, b.err, want))

    report('remote-push-u-' + p.name, 'den push -u origin main', first, second,
           out=["branch 'main' set up to track 'origin/main'."])
    r = 'remote-refs-' + p.name
    b = p.s('cat ../hub.git/refs/heads/main', 1, r)
    if b is not None and second and not (b.status == 0 and len(b.out) == 1 and re.fullmatch('%s[0-9a-f]{33}' % second, b.out[0])):
        p.fail(r, "hub.git's main after push -u: %d %r (want %s...)" % (b.status, b.out, second))
    report('remote-push-' + p.name, 'den push', second, third)
    r = 'remote-clone-' + p.name
    p.quiet(r, 'den clone -q %s c2' % hub)
    b = p.s('den log --oneline', 1, r)
    want = ['%s third: three' % third, '%s second: two' % second, '%s first: a.txt' % first]
    if b is not None and (b.status, b.out, b.err) != (0, want, []):
        p.fail(r, "the clone's log: %d %r, not the source's %r" % (b.status, b.out, want))
    report('remote-clone-push-' + p.name, 'den push', third, fourth, nth=2)
    r = 'remote-fetch-' + p.name
    b = p.s('den fetch', 1, r)
    want = ['From %s/hub' % url, '   %s..%s  main       -> origin/main' % (third, fourth)]
    if b is not None and (b.status, b.out, b.err) != (0, [], want):
        p.fail(r, '`fetch`: %d %r %r, not %r' % (b.status, b.out, b.err, want))
    b = p.s('den log --oneline origin/main', 1, r)
    if b is not None and (b.status != 0 or not b.out or b.out[0] != '%s c2: c.txt' % fourth):
        p.fail(r, '`log --oneline origin/main`: %d %r (want %s c2: c.txt first)' % (b.status, b.out[:1], fourth))
    r = 'remote-pull-' + p.name
    b = p.s('den pull --no-rebase', 1, r)
    if b is not None and (b.status != 0 or b.out[:2] != ['Updating %s..%s' % (third, fourth), 'Fast-forward'] or b.err):
        p.fail(r, '`pull --no-rebase`: %d %r %r (want a fast-forward %s..%s)' % (b.status, b.out[:2], b.err, third, fourth))
    b = p.s('den log --oneline', 2, r)
    if b is not None and (b.status != 0 or len(b.out) != 4 or b.out[0] != '%s c2: c.txt' % fourth):
        p.fail(r, "the source's log after the pull: %d %r" % (b.status, b.out))

    def daemon(row, nth, inner):
        out = p.raw('dm | dc %s' % inner, 1, row)
        if out is None:
            return None
        if len(out) < 4 or out[0] != 'port %d' % port or out[-1] != 'daemon 0':
            p.fail(row, 'the daemon said %r ... %r (want port %d first and daemon 0 last)' % (out[:1], out[-1:], port))
            return None
        try:
            b = S(out[1:-1])
        except ValueError as e:
            p.fail(row, str(e))
            return None
        d = p.raw('cat $O/d', nth, row)
        if d:
            p.fail(row, "the daemon's standard error: %r" % d[:3])
        return b

    git = 'git://127.0.0.1:%d/hub.git' % port
    r = 'remote-daemon-clone-' + p.name
    b = daemon(r, 1, 'den clone -q %s c3' % git.replace(str(port), '$Q'))
    if b is not None and (b.status, b.out, b.err) != (0, [], []):
        p.fail(r, 'the clone over git://: %d %r %r' % (b.status, b.out, b.err))
    b = p.s('den log --oneline', 3, r)
    if b is not None and (b.status != 0 or not b.out or b.out[0] != '%s c2: c.txt' % fourth):
        p.fail(r, "the git:// clone's log: %d %r" % (b.status, b.out[:1]))
    r = 'remote-daemon-push-' + p.name
    b = daemon(r, 2, 'den push')
    want = ['To %s' % git, '   %s..%s  main -> main' % (fourth, fifth)]
    if b is not None and None not in (fourth, fifth) and (b.status, b.out, b.err) != (0, [], want):
        p.fail(r, 'the push over git://: %d %r %r, not %r' % (b.status, b.out, b.err, want))
    r = 'remote-one-session-' + p.name
    b = p.s('den fetch', 2, r)
    if b is not None and (b.status, b.out, b.err) != (2, [], ['den: wire: io']):
        p.fail(r, 'a fetch with no daemon: %d %r %r (want 2 and den: wire: io)' % (b.status, b.out, b.err))
    r = 'remote-final-pull-' + p.name
    b = p.s('den pull --no-rebase', 2, r)
    if b is not None and (b.status != 0 or b.out[:2] != ['Updating %s..%s' % (fourth, fifth), 'Fast-forward']):
        p.fail(r, 'the last pull: %d %r %r' % (b.status, b.out[:2], b.err))
    b = p.s('den log --oneline', 4, r)
    want = [fifth, fourth, third, second, first]
    if b is not None and None not in want and [l.split()[0] for l in b.out] != want:
        p.fail(r, "the source's log at the end: %r, not %r" % (b.out, want))
    r = 'remote-refs-' + p.name
    b = p.s('cat hub.git/refs/heads/main', 1, r)
    if b is not None and fifth and not (b.status == 0 and len(b.out) == 1 and re.fullmatch('%s[0-9a-f]{33}' % fifth, b.out[0])):
        p.fail(r, "hub.git's main at the end: %d %r (want %s...)" % (b.status, b.out, fifth))
    r = 'remote-fsck-' + p.name
    for k in range(1, 5):
        p.quiet(r, 'den fsck --full', k)


def main():
    session, work, uid = sys.argv[1], sys.argv[2], int(sys.argv[3])
    lines = open(session, encoding='latin-1').read().split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines or lines[0] != 'den-session-begin' or lines[-1] != 'den-session-end':
        print('session: not one whole den session')
        return 2
    if lines.count('den-place-tmp') != 1 or lines.count('den-place-home') != 1:
        print('session: not one den-place-tmp and one den-place-home marker')
        return 2
    a, h = lines.index('den-place-tmp'), lines.index('den-place-home')
    bad = []
    head = Place('head', parse(lines[1:a]), bad)
    tmp = Place('tmp', parse(lines[a + 1:h]), bad)
    home = Place('home', parse(lines[h + 1:-1]), bad)
    d = '/tmp/den-%d' % uid
    port = 9418 if uid == 0 else 9428
    # /etc/shrc names the installed pair; the pair typed at the console is
    # the same bytes (the image installs exactly these two lines each).
    out = head.raw('echo "upload=$DEN_UPLOAD_PACK receive=$DEN_RECEIVE_PACK"', 1, 'remote-shrc')
    want = ['upload=%s/upload-pack receive=%s/receive-pack' % (LIBEXEC, LIBEXEC)]
    if out is not None and out != want:
        head.fail('remote-shrc', '/etc/shrc gave %r, not %r' % (out, want))
    out = head.raw('cat %s/upload-pack %s/receive-pack' % (LIBEXEC, LIBEXEC), 1, 'remote-wrappers')
    if out is not None and out != WRAP['upload-pack'] + WRAP['receive-pack']:
        head.fail('remote-wrappers', 'the installed wrappers read %r' % out)
    inst = head.raw('sha256sum %s/upload-pack %s/receive-pack' % (LIBEXEC, LIBEXEC), 1, 'remote-wrappers')
    typed = head.raw('sha256sum $B/upload-pack $B/receive-pack', 1, 'remote-wrappers')
    if inst is not None and typed is not None:
        si = [l.split()[0] for l in inst if re.fullmatch(r'[0-9a-f]{64}  \S+', l)]
        st = [l.split()[0] for l in typed if re.fullmatch(r'[0-9a-f]{64}  \S+', l)]
        if len(si) != 2 or si != st:
            head.fail('remote-wrappers', 'the typed pair %r is not the installed pair %r' % (st, si))
    b = tmp.s('den clone -q --bare file://$P/src none.git', 1, 'remote-no-variable')
    if b is not None and (b.status, b.out, b.err) != (2, [], ['den: wire: io']):
        tmp.fail('remote-no-variable', 'with no DEN_UPLOAD_PACK: %d %r %r (want 2 and den: wire: io: no git-upload-pack on PATH)' % (b.status, b.out, b.err))
    b = tmp.s('cat .git/config', 1, 'remote-config')
    if b is not None:
        want = ['[remote "origin"]', '\turl = file://%s/r/hub.git' % d, '\tfetch = +refs/heads/*:refs/remotes/origin/*',
                '[branch "main"]', '\tremote = origin', '\tmerge = refs/heads/main']
        if b.status != 0 or b.out[-6:] != want:
            tmp.fail('remote-config', '.git/config ends %r, not %r' % (b.out[-6:], want))
    b = tmp.s('den status', 1, 'remote-status-limit')
    if b is not None and (b.status, b.out, b.err) != (2, [], ['den: not yet implemented: status upstream tracking']):
        tmp.fail('remote-status-limit', '`status` with an upstream: %d %r %r (den names it not yet implemented at its pin)' % (b.status, b.out, b.err))
    # The places' blocks are typed with $P; the rows name what $P is.
    for place, root, port_ in ((tmp, d + '/r', port), (home, work + '/r', port + 1)):
        place.blocks = [[c.replace('$P', root) if not c.startswith('dm | dc ') else c, o] for c, o in place.blocks]
        place_rows(place, root, 'file://' + root, place is tmp, port_)
    for line in bad:
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
