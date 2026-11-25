#!/usr/bin/env python3
"""tests/mpx5-init.d/hook-selftest.py — the hook boot's rows (I17-I21, rows.py) against a simulated console,
no QEMU: a login, a password, a shell's prompt, and the few commands the rows type, as PAX's console shows them.

Three shapes of /etc/shrc:
  trunk  sources no file of the account's: I17, I19, I20 and I21 red by name, I18 green;
  hook   sources ~/.config/pelt/shrc when it is a readable regular file: every row green;
  plant  sources ~/.config/pelt/shrc.d instead: I17 red by name, I18 green.
And one console that does not give way to 0x03 while the file waits: I21 red, saying so.
Only HOOK-SELFTEST lines are printed: the rows' own lines are kept from the output, since a simulated
shape's FAIL at column 0 would read as a red row of the suite. Exit 0 when every shape reads as written here,
1 otherwise.
"""
import contextlib
import importlib.util
import io
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rows', HERE / 'rows.py')
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)
UIDS = {'root': 0, 'pax': 1000, 'bob': 1001}
HOMES = {'root': '/root', 'pax': '/home/pax', 'bob': '/home/bob'}


def outside_quotes(text, sep):
    """text split at each sep outside single quotes, as the shell reads a list."""
    parts, cur, quoted, i = [], '', False, 0
    while i < len(text):
        if text[i] == "'":
            quoted = not quoted
        if not quoted and text.startswith(sep, i):
            parts.append(cur)
            cur, i = '', i + len(sep)
            continue
        cur += text[i]
        i += 1
    return parts + [cur]


class Sim:
    def __init__(self, hook, gives_way=True):
        self.hook, self.gives_way = hook, gives_way
        self.seen, self.cursor = b'', 0
        self.files = {}          # path -> (text, mode) ; text None for a directory
        self.stack = []          # shells: dict(user, env, pid)
        self.state = 'name'
        self.pid = 100
        self.blocked = False
        self.name = None
        self.prompt_login()

    # Console's reading side, as rows.Console has it
    def out(self, text):
        self.seen += text.encode()

    def text(self, tail=600):
        return self.seen.decode(errors='replace')[-tail:]

    def wait(self, pattern, timeout=120):
        rx = re.compile(pattern.encode() if isinstance(pattern, str) else pattern, re.M)
        m = rx.search(self.seen, self.cursor)
        if m:
            self.cursor = m.end()
        return m

    def running(self):
        return True

    def raw(self, data):
        if data == b'\x03' and self.blocked:
            self.blocked = False
            if self.gives_way:
                self.out('^C\n')
                self.prompt()
            return
        raise AssertionError('raw %r unexpected' % data)

    def type(self, line):
        if self.blocked:
            return
        if self.state == 'name':
            self.out(line + '\n')
            self.name = line
            self.state = 'password'
            self.out('Password: ')
        elif self.state == 'password':
            self.out('\n')
            if line != rows.PASSWORDS.get(self.name):
                self.out('Login incorrect\n')
                self.prompt_login()
                return
            self.state = 'shell'
            self.start(self.name, {}, new_pid=True)
        else:
            self.out(line + '\n')
            self.run(line)

    def command(self, line, n, timeout=120):
        return rows.Console.command(self, line, n, timeout)

    # the console's machine
    def prompt_login(self):
        self.state = 'name'
        self.stack = []
        self.out('pax login: ')

    def prompt(self):
        self.out('$ ')

    def start(self, user, env, new_pid):
        if new_pid:
            self.pid += 1
        self.stack.append(dict(user=user, env=dict(env), pid=self.pid))
        if self.env_file(user):
            return
        self.prompt()

    def env_file(self, user):
        """/etc/shrc's hook: True when the file ended the session, blocked, or exec'd (the caller then prompts no more)."""
        rel = {'trunk': None, 'hook': rows.HOOK_PATH, 'plant': rows.HOOK_PATH + '.d'}[self.hook]
        if rel is None:
            return False
        path = '%s/%s' % (HOMES[user], rel)
        f = self.files.get(path)
        if f is None or f[0] is None or (user != 'root' and not f[1] & 0o444):
            return False
        for stmt in [s.strip() for s in f[0].split(';')]:
            sh = self.stack[-1]
            if stmt == 'false':
                continue
            if stmt.startswith('echo '):
                self.out(stmt[5:].replace('$(id -u)', str(UIDS[sh['user']])) + '\n')
            elif stmt == 'if then fi':
                self.out('pelt: syntax error: `then\' unexpected\n')
                return False
            elif stmt == 'exit 1':
                self.prompt_login()
                return True
            elif stmt == 'sleep 600':
                self.blocked = True
                return True
            elif stmt.startswith('[ -z "$H20" ] && H20=1 exec'):
                if sh['env'].get('H20'):
                    continue
                self.stack.pop()
                self.start(user, dict(sh['env'], H20='1'), new_pid=False)
                return True
            else:
                raise AssertionError('file statement %r' % stmt)
        return False

    def run(self, line):
        sh = self.stack[-1]
        m = re.fullmatch(r'echo (\S+)B\$\(\((\d+)\+0\)\); (.*); echo \S+E\$\(\(\d+\+0\)\)', line)
        if m:
            mark, n, cmd = m.groups()
            self.out('%sB%s\n' % (mark, n))
            self.out(self.do(cmd, sh))
            self.out('%sE%s\n' % (mark, n))
            self.prompt()
            return
        if line == 'exit':
            self.stack.pop()
            if self.stack:
                self.prompt()
            else:
                self.prompt_login()
            return
        if line == 'su pax':
            self.start('pax', sh['env'], new_pid=True)
            return
        raise AssertionError('typed %r' % line)

    def do(self, cmd, sh):
        if cmd.endswith('; echo SETUP-RC=$?'):
            for part in outside_quotes(cmd[:-len('; echo SETUP-RC=$?')], ' && '):
                self.setup(part)
            return 'SETUP-RC=0\n'
        if cmd.startswith('rm -f '):
            self.files.pop(cmd[6:], None)
            return ''
        m = re.fullmatch(r'echo (I\d+[A-Z]?-OK)', cmd)
        if m:
            return m.group(1) + '\n'
        if cmd.startswith('echo H20=$H20;'):
            return 'H20=%s\nSID=%d PID=%d\n' % (sh['env'].get('H20', ''), self.stack[0]['pid'], sh['pid'])
        raise AssertionError('command %r' % cmd)

    def setup(self, part):
        if part == 'umask 022' or part.startswith('mkdir -p '):
            return
        m = re.fullmatch(r"echo '(.*)' > (\S+)", part)
        if m:
            old = self.files.get(m.group(2))
            self.files[m.group(2)] = (m.group(1), old[1] if old else 0o644)
            return
        if part.startswith('chmod 000 '):
            text = self.files[part[10:]][0]
            self.files[part[10:]] = (text, 0)
            return
        if part.startswith('rm -f ') or part.startswith('rm -rf '):
            self.files.pop(part.split(' ', 2)[2], None)
            return
        if part.startswith('mkdir '):
            self.files[part[6:]] = (None, 0o755)
            return
        raise AssertionError('setup %r' % part)


class A:
    tier, leg = 'sim', 'sim'


def take(hook, gives_way=True):
    rows.ARGS = A()
    rows.FAILS.clear()
    rows.PASSWORDS.update(root='r-pw', pax='p-pw', bob='b-pw')
    sim = Sim(hook, gives_way)
    # The rows' own PASS and FAIL lines stay here: a simulated shape's FAIL at column 0 would read as a red row.
    with contextlib.redirect_stdout(io.StringIO()):
        rows.hook_boot(sim)
    return set(rows.FAILS)


bad = 0
for name, hook, gives, want in (('trunk', 'trunk', True, {'I17', 'I19', 'I20', 'I21'}),
                                ('hook', 'hook', True, set()),
                                ('plant', 'plant', True, {'I17', 'I19', 'I20', 'I21'}),
                                ('no-give', 'hook', False, {'I21'})):
    got = take(hook, gives)
    held = got == want
    bad += not held
    print('%s HOOK-SELFTEST %s: red %s (want %s)' % ('PASS' if held else 'FAIL', name, sorted(got) or 'none', sorted(want) or 'none'),
          flush=True)
print('hook-selftest: %d of 4 shapes as written' % (4 - bad))
sys.exit(1 if bad else 0)
