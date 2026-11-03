#!/usr/bin/env python3
"""The den session's own witness (tests/mpx5-den, px90): rows that hold
whatever both sides typed, so a den or a link broken the same way on PAX
and in the Linux container (where the comparison alone stays green) is
still red here, by name.

Usage: rows.py SESSION DEN-SHA256 WORKDIR

SESSION is one session (tests/mpx5-den.d/region.py's output) typed from
user/console/den.keys; DEN-SHA256 is tools/mkden's digest of den; WORKDIR
the session's directory (/home/den-root or /home/pax). Prints one line a
failed row, `ROW: why`, and nothing when every row holds. Exit 0 either
way (the caller counts the lines), 2 on a malformed session.

The rows are den's own answers at its pin where they are fixed by the
formats (Git's porcelain words, conflict markers, the version line), and,
for `git`, sameness: each `s git VERB` block must be the `s den VERB`
block before it, byte for byte, because /bin/git is a link to den and den
reads no argv[0] (its README). Nothing here is checked against den's
source; every expected line is in the keys' inputs or den's README.
"""
import re
import sys

ROWS = [
    'link', 'binary', 'den-version', 'git-version', 'usage', 'init', 'config',
    'config-refused', 'add', 'commit', 'log', 'diff', 'merge-ff', 'merge-conflict',
    'merge-resolved', 'rebase', 'cherry-pick', 'revert', 'tag', 'blame', 'stash',
    'notes', 'reset', 'editor-false', 'editor-refused', 'git-status', 'git-log',
    'git-branch', 'git-tag', 'git-diff', 'git-cat-file', 'git-init', 'objects',
    'fsck', 'gc-refused', 'repack', 'git-fsck', 'final-log',
]
VERSION = 'den 0.0.0 (built with wolf 0.2.36)'

def parse(lines):
    """[(command, output lines)]: a command is a line after the prompt."""
    blocks = []
    for line in lines[1:]:
        if line.startswith('$ '):
            # `tick; s …` moves the dates first: the block is the `s …`.
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

def main():
    session, sha, work = sys.argv[1:4]
    lines = open(session, encoding='latin-1').read().split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    if not lines or lines[0] != 'den-session-begin' or lines[-1] != 'den-session-end':
        print('session: not one whole den session')
        return 2
    blocks = parse(lines[:-1])
    bad = []
    def fail(row, why):
        bad.append('%s: %s' % (row, why))
    def find(cmd, nth=1, row='?'):
        seen = [b for b in blocks if b[0] == cmd]
        if len(seen) < nth:
            fail(row, 'no `%s` (#%d) in the session' % (cmd, nth))
            return None
        return seen[nth - 1][1]
    def s(cmd, nth=1, row='?'):
        out = find('s ' + cmd, nth, row)
        if out is None:
            return None
        try:
            return S(out)
        except ValueError as e:
            fail(row, '`s %s`: %s' % (cmd, e))
            return None
    def ok(row, b, out=None, err=None, status=0):
        if b is None:
            return False
        why = []
        if status is not None and b.status != status:
            why.append('status %d, not %d' % (b.status, status))
        if out is not None and b.out != out:
            why.append('stdout %r, not %r' % (b.out[:6], out[:6]))
        if err is not None and b.err != err:
            why.append('stderr %r, not %r' % (b.err[:4], err[:4]))
        if why:
            fail(row, '; '.join(why))
        return not why

    # The install: den is the binary mkden built; git is a link to it.
    if find('command -v den git', row='link') != ['/bin/den', '/bin/git']:
        fail('link', 'command -v den git: %r' % find('command -v den git'))
    if find('readlink /bin/git', row='link') != ['den']:
        fail('link', 'readlink /bin/git: %r, not den' % find('readlink /bin/git'))
    if find('sha256sum /bin/den', row='binary') != [sha + '  /bin/den']:
        fail('binary', 'sha256sum /bin/den: %r, mkden built %s' % (find('sha256sum /bin/den'), sha))
    ok('den-version', s('den --version', row='den-version'), [VERSION], [])
    # git answers as den, --version included (den reads no argv[0]).
    a, b = s('den --version'), s('git --version', row='git-version')
    if a and b and (a.status, a.out, a.err) != (b.status, b.out, b.err):
        fail('git-version', '`git --version` is not den\'s: %r' % (b.out + b.err)[:3])
    u = s('den', row='usage')
    if u and (u.status == 0 or not (u.out + u.err)):
        fail('usage', 'bare `den`: status %d, %d lines' % (u.status, len(u.out + u.err)))
    ok('init', s('den init repo', row='init'), ['Initialized empty Git repository in %s/repo/.git/' % work], [])

    # config: read-only at the pin; the files written by the keys read back.
    for key, want in [('core.bare', 'false'), ('core.filemode', 'true'), ('user.name', 'Den Tester'),
                      ('init.defaultBranch', 'main'), ('core.autocrlf', 'false')]:
        ok('config', s('den config --get ' + key, row='config'), [want], [])
    c = s('den config user.name Other', row='config-refused')
    if c and c.status == 0:
        fail('config-refused', '`den config user.name Other` succeeded (the pin has no writer)')

    # add, status, commit.
    ok('add', s('den status --porcelain', 1, 'add'), ['?? a.txt', '?? b.txt'], [])
    ok('add', s('den add a.txt b.txt', row='add'), [], [])
    ok('add', s('den status --porcelain', 2, 'add'), ['A  a.txt', 'A  b.txt'], [])
    first = s("den commit -m 'first: two files'", row='commit')
    if ok('commit', first, None, []) and not re.fullmatch(r'\[main \(root-commit\) [0-9a-f]{7,}\] first: two files', first.out[0]):
        fail('commit', 'first commit line %r' % first.out[0])
    third = s("den commit -a -m 'third: commit -a'", row='commit')
    if ok('commit', third, None, []) and not re.fullmatch(r'\[main [0-9a-f]{7,}\] third: commit -a', third.out[0]):
        fail('commit', 'commit -a line %r' % third.out[0])
    lg = s('den log', 1, 'log')
    if ok('log', lg, None, []):
        ids = [l for l in lg.out if re.fullmatch(r'commit [0-9a-f]{40}', l)]
        if len(ids) != 3 or 'Author: Den Tester <den@example.invalid>' not in lg.out:
            fail('log', 'den log: %d commits, author %r' % (len(ids), [l for l in lg.out if l.startswith('Author')][:1]))
    lo = s('den log --oneline', 1, 'log')
    if ok('log', lo, None, []) and [l.split(' ', 1)[1] for l in lo.out] != ['third: commit -a', 'second: delta', 'first: two files']:
        fail('log', 'den log --oneline: %r' % lo.out)
    lp = s('den log -p -n 1', row='log')
    if ok('log', lp, None, []) and '+two' not in lp.out:
        fail('log', 'den log -p -n 1 has no +two')
    for cmd in ('den diff', 'den diff --cached'):
        d = s(cmd, row='diff')
        if ok('diff', d, None, []) and '+delta' not in d.out:
            fail('diff', '%s has no +delta: %r' % (cmd, d.out[-3:]))
    d = s('den diff HEAD~2 HEAD', row='diff')
    if ok('diff', d, None, []) and not ('+delta' in d.out and '+two' in d.out):
        fail('diff', 'den diff HEAD~2 HEAD lacks +delta/+two')

    # merge: a fast-forward, then a three-way with a conflict, resolved.
    m = s('den merge ff', row='merge-ff')
    if ok('merge-ff', m, None, []) and 'Fast-forward' not in m.out:
        fail('merge-ff', 'no Fast-forward line: %r' % m.out)
    m = s('den merge side', row='merge-conflict')
    if ok('merge-conflict', m, None, None, 1) and 'CONFLICT (content): Merge conflict in a.txt' not in m.out:
        fail('merge-conflict', 'no CONFLICT line: %r' % m.out)
    ok('merge-conflict', s('den status --porcelain', 4, 'merge-conflict'), ['UU a.txt'], [])
    if find('cat a.txt', row='merge-conflict') != ['alpha', '<<<<<<< HEAD', 'beta from main', '=======',
                                                   'beta from side', '>>>>>>> side', 'gamma', 'delta']:
        fail('merge-conflict', 'the markers: %r' % find('cat a.txt'))
    ok('merge-resolved', s("den commit -m 'merge side: resolved'", row='merge-resolved'), None, [])
    lo = s('den log --oneline', 2, 'merge-resolved')
    if ok('merge-resolved', lo, None, []) and not lo.out[0].endswith(' merge side: resolved'):
        fail('merge-resolved', 'log top %r' % lo.out[:1])

    # rebase, cherry-pick, revert.
    ok('rebase', s('den rebase main', row='rebase'), None, None)
    lo = s('den log --oneline -n 3', 1, 'rebase')
    if ok('rebase', lo, None, []) and [l.split(' ', 1)[1] for l in lo.out[:2]] != ['feat: c.txt', 'main: three']:
        fail('rebase', 'feat after the rebase: %r' % lo.out)
    ok('cherry-pick', s('den cherry-pick pick', row='cherry-pick'), None, [])
    lo = s('den log --oneline -n 2', 1, 'cherry-pick')
    if ok('cherry-pick', lo, None, []) and not lo.out[0].endswith(' pick: p.txt'):
        fail('cherry-pick', 'log top %r' % lo.out[:1])
    ok('revert', s('den revert --no-edit HEAD', row='revert'), None, [])
    lo = s('den log --oneline -n 2', 2, 'revert')
    if ok('revert', lo, None, []) and not lo.out[0].endswith(' Revert "pick: p.txt"'):
        fail('revert', 'log top %r' % lo.out[:1])

    # tags, blame, stash, notes, reset.
    ok('tag', s('den tag', 1, 'tag'), ['v1', 'v2'], [])
    ok('tag', s('den cat-file -t v2', row='tag'), ['tag'], [])
    t = s('den cat-file -p v2', row='tag')
    if ok('tag', t, None, []) and not ('tag v2' in t.out and 'annotated v2' in t.out):
        fail('tag', 'the annotated tag object: %r' % t.out)
    bl = s('den blame a.txt', row='blame')
    if ok('blame', bl, None, []) and not (len(bl.out) == 4 and bl.out[1].endswith(') beta from both')):
        fail('blame', 'den blame a.txt: %r' % bl.out)
    ok('stash', s('den stash push -m wip', row='stash'), None, [])
    ok('stash', s('den stash list', row='stash'), ['stash@{0}: On main: wip'], [])
    ok('stash', s('den status --porcelain', 6, 'stash'), [], [])
    ok('stash', s('den stash pop', row='stash'), None, None)
    ok('stash', s('den status --porcelain', 7, 'stash'), [' M b.txt'], [])
    ok('notes', s("den notes add -m 'a note on HEAD' HEAD", row='notes'), None, None)
    ok('notes', s('den notes show HEAD', row='notes'), ['a note on HEAD'], [])
    n = s('den log -n 1', row='notes')
    if ok('notes', n, None, []) and not ('Notes:' in n.out and '    a note on HEAD' in n.out):
        fail('notes', 'den log -n 1 shows no note: %r' % n.out)
    ok('reset', s('den reset --soft HEAD~1', row='reset'), [], [])
    ok('reset', s('den status --porcelain', 8, 'reset'), ['A  r.txt'], [])
    ok('reset', s('den reset --mixed HEAD', row='reset'), None, None)
    ok('reset', s('den status --porcelain', 9, 'reset'), ['?? r.txt'], [])
    r = s('den reset --hard HEAD~1', row='reset')
    if ok('reset', r, None, []) and not (len(r.out) == 1 and r.out[0].startswith('HEAD is now at ')):
        fail('reset', 'reset --hard: %r' % r.out)
    ok('reset', s('den status --porcelain', 10, 'reset'), [], [])
    lsr = s('ls r.txt', row='reset')
    if lsr and lsr.status == 0:
        fail('reset', 'r.txt is still there after reset --hard')

    # The editor: GIT_EDITOR=false fails as measured; another is never run.
    e = s('den commit --allow-empty', row='editor-false')
    if e and not (e.status == 1 and any('editor' in l for l in e.err)):
        fail('editor-false', 'status %d, stderr %r' % (e.status, e.err))
    e = s('env GIT_EDITOR=yew den commit --allow-empty', row='editor-refused')
    if e and not (e.status != 0 and e.out == [] and (e.err and any('editor' in l or 'yew' in l for l in e.err))):
        fail('editor-refused', 'status %d, stdout %r, stderr %r' % (e.status, e.out[:2], e.err[:2]))

    # git: each verb's block is den's, byte for byte.
    for row, verb in [('git-status', 'status'), ('git-log', 'log --oneline -n 3'), ('git-branch', 'branch'),
                      ('git-tag', 'tag'), ('git-diff', 'diff HEAD~1 HEAD'), ('git-cat-file', 'cat-file -p HEAD'),
                      ('git-fsck', 'fsck --full --no-dangling')]:
        dens = [b[1] for b in blocks if b[0] == 's den ' + verb]
        gits = [b[1] for b in blocks if b[0] == 's git ' + verb]
        if not gits:
            fail(row, 'no `s git %s`' % verb)
        elif not dens or dens[-1] != gits[-1]:
            fail(row, '`git %s` is not `den %s`: %r' % (verb, verb, gits[-1][:4]))
    ok('git-init', s('git init ../made-by-git', row='git-init'),
       ['Initialized empty Git repository in %s/made-by-git/.git/' % work], [])

    # The objects, then packs: fsck, gc's refusal, repack, prune, verify.
    objs = find('sha256sum .git/objects/??/*', row='objects') or []
    shaped = [l for l in objs if re.fullmatch(r'[0-9a-f]{64}  \.git/objects/[0-9a-f]{2}/[0-9a-f]{38}', l)]
    if len(shaped) != len(objs) or len(objs) < 30:
        fail('objects', '%d loose object lines, %d shaped' % (len(objs), len(shaped)))
    for nth in (1, 2):
        ok('fsck', s('den fsck --full --no-dangling', nth, 'fsck'), [], [])
    g = s('den gc', row='gc-refused')
    if g and g.status == 0:
        fail('gc-refused', '`den gc` succeeded; the pin has no gc')
    ok('repack', s('den repack -a -n -q -d', row='repack'), [], [])
    ok('repack', s('den prune-packed', row='repack'), [], [])
    packs = find('sha256sum .git/objects/pack/*', row='repack') or []
    if not (len(packs) == 2 and re.fullmatch(r'[0-9a-f]{64}  \.git/objects/pack/pack-[0-9a-f]{40}\.idx', packs[0])
            and re.fullmatch(r'[0-9a-f]{64}  \.git/objects/pack/pack-[0-9a-f]{40}\.pack', packs[1])):
        fail('repack', 'the pack directory: %r' % packs)
    v = s('den verify-pack -v .git/objects/pack/pack-*.idx', row='repack')
    if ok('repack', v, None, []) and not re.fullmatch(r'\.git/objects/pack/pack-[0-9a-f]{40}\.pack: ok', v.out[-1]):
        fail('repack', 'verify-pack ends %r' % v.out[-1:])
    lg = s('den log', 2, 'final-log')
    if ok('final-log', lg, None, []):
        ids = [l for l in lg.out if re.fullmatch(r'commit [0-9a-f]{40}', l)]
        if len(ids) < 12:
            fail('final-log', 'den log from the pack: %d commits' % len(ids))
    for line in bad:
        print(line)
    return 0

if __name__ == '__main__':
    sys.exit(main())
