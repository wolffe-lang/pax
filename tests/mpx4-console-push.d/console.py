#!/usr/bin/env python3
"""console.py — a typed session at PAX's console whose transcript is scrubbed
before it is written (px104, R-px104-3).

    console.py --run DIR --log FILE --keys KEYS --prompt TEXT --iso ISO
               --leg bios|uefi --accel A --timeout SECS [--secrets DIR]
               [--drive IMG] [--hook LABEL=PROGRAM]... [-- QEMU-ARG...]

tools/qemu-run boots ISO with COM1 on two FIFOs in the 0700 directory DIR
(its output and its input) and a monitor socket beside them; nothing of
COM1 reaches a file before this program has read it. The secrets are the
files of the 0700 directory given by --secrets (`name`, `token`, `key`,
each optional; the carrier disk's own files, or their originals): every
byte the console prints goes through the scrub in memory, which replaces
  - the name (and so every URL holding it),
  - the token, its hex, the Basic credential `x-access-token:TOKEN` in
    base64 and that credential's hex,
  - each base64 line of the key file and the whole key file,
with `<scrubbed:name>`, `<scrubbed:token>` and `<scrubbed:key>`. A secret
split across two reads is caught: the last (longest secret - 1) bytes are
held back until more arrives. Only the scrubbed bytes are written, to FILE;
what was typed goes to FILE.typed after the same scrub (the keys never hold
a secret: the session reads them from /run/live by redirection), each line
with the seconds since QEMU started at which its prompt came and its
typing began and ended (so a step's wall time is the next prompt's less
this line's end), and each hook's output to FILE.hooks.

The keys are typed as tools/qemu-halt types them: one line after each new
TEXT prompt (counted from kmain_console's `run 1:` line), 0.2 s after it,
a byte every 20 ms, CR at the end. A line of the console's that is exactly
`STEP:LABEL` runs --hook LABEL's PROGRAM, a shell script read by /bin/sh
(on this host, before the next
line is typed; its stdout and stderr scrubbed into FILE.hooks with
`HOOK LABEL exit=N`). A hook still running after --hook-bound seconds (120)
is ended by name, `HOOK LABEL exit=timeout` and `timeout after N s`, and
the session goes on (run_hook). When every line is typed the session's own `exit`
ends the run list; at the kernel's `halt` line (or after 60 s more) the
monitor's `quit` ends QEMU, and so tools/qemu-run.

Prints `CONSOLE ok` (every line typed, the prompt never missed, halted) or
`CONSOLE FAIL <why>`, and `SCRUB <n> replacements: name <a>, token <b>,
key <c>`. Exit 0 or 1; 2 on a setup error.
"""
import argparse
import base64
import os
import re
import select
import socket
import stat
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Scrub:
    def __init__(self, secrets):
        self.needles = []  # (bytes, class)
        self.counts = {'name': 0, 'token': 0, 'key': 0}
        if secrets:
            def read(n):
                p = os.path.join(secrets, n)
                return open(p, 'rb').read() if os.path.isfile(p) else b''
            name = read('name').strip()
            token = read('token').strip()
            key = read('key')
            if name:
                self.needles.append((name, 'name'))
            if token:
                basic = base64.b64encode(b'x-access-token:' + token)
                for n in (token, token.hex().encode(), basic, basic.hex().encode()):
                    self.needles.append((n, 'token'))
            if key:
                self.needles.append((key.strip(), 'key'))
                for line in key.splitlines():
                    line = line.strip()
                    if len(line) >= 16 and not line.startswith(b'-----'):
                        self.needles.append((line, 'key'))
        self.needles.sort(key=lambda n: -len(n[0]))
        self.hold = max([len(n) for n, _ in self.needles] or [1]) - 1
        self.pending = b''

    def text(self, data):
        """The whole of `data`, scrubbed (for a complete block)."""
        for n, c in self.needles:
            k = data.count(n)
            if k:
                self.counts[c] += k
                data = data.replace(n, b'<scrubbed:' + c.encode() + b'>')
        return data

    def feed(self, data, final=False):
        """Scrubbed bytes ready to write; the tail that may begin a secret is kept."""
        self.pending = self.text(self.pending + data)
        if final or self.hold == 0:
            out, self.pending = self.pending, b''
            return out
        cut = max(0, len(self.pending) - self.hold)
        # Never cut inside a placeholder the scrub just wrote.
        start = self.pending.rfind(b'<scrubbed:', 0, cut)
        if start >= 0 and self.pending.find(b'>', start) >= cut:
            cut = start
        out, self.pending = self.pending[:cut], self.pending[cut:]
        return out


def say(line):
    print(line, flush=True)


def run_hook(prog, bound):
    """(exit status, or 'timeout', and its output) of /bin/sh PROG, ended at
    BOUND seconds: the hook's pid and the children it started (pid by pid,
    from /proc, never a process group) are killed, and the output so far
    ends with `timeout after BOUND s`."""
    # Read by sh, never exec'd: the carrier's tmpfs may be noexec.
    p = subprocess.Popen(['/bin/sh', prog], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    try:
        out, _ = p.communicate(timeout=bound)
        return p.returncode, out
    except subprocess.TimeoutExpired:
        pids = [p.pid]
        try:
            for t in os.listdir('/proc/%d/task' % p.pid):
                pids += [int(c) for c in open('/proc/%d/task/%s/children' % (p.pid, t)).read().split()]
        except OSError:
            pass
        for pid in pids:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
        p.wait(timeout=30)
        os.set_blocking(p.stdout.fileno(), False)
        try:
            out = p.stdout.read() or b''
        except (BlockingIOError, OSError):
            out = b''
        p.stdout.close()
        return 'timeout', out + b'timeout after %d s\n' % bound


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True)
    a.add_argument('--log', required=True)
    a.add_argument('--keys', required=True)
    a.add_argument('--prompt', required=True)
    a.add_argument('--iso', required=True)
    a.add_argument('--leg', default='bios')
    a.add_argument('--accel', default='auto')
    a.add_argument('--timeout', type=int, default=1200)
    a.add_argument('--prompt-timeout', type=int, default=600)
    a.add_argument('--secrets')
    a.add_argument('--drive')
    a.add_argument('--hook', action='append', default=[])
    a.add_argument('--hook-bound', type=int, default=120)
    a.add_argument('qemu', nargs='*')
    args = a.parse_args()
    run = args.run
    os.makedirs(run, mode=0o700, exist_ok=True)
    os.chmod(run, 0o700)
    if stat.S_IMODE(os.stat(run).st_mode) != 0o700:
        say('CONSOLE FAIL the run directory is not 0700')
        return 2
    if args.secrets and stat.S_IMODE(os.stat(args.secrets).st_mode) & 0o077:
        say('CONSOLE FAIL the secrets directory is open to others')
        return 2
    hooks = {}
    for h in args.hook:
        label, _, prog = h.partition('=')
        hooks[label] = prog
    scrub = Scrub(args.secrets)
    out_fifo, in_fifo, mon = (os.path.join(run, n) for n in ('com1.out', 'com1.in', 'monitor'))
    for f in (out_fifo, in_fifo):
        if os.path.exists(f):
            os.unlink(f)
        os.mkfifo(f, 0o600)
    # Opened read-write, so qemu-run's truncation and QEMU's open never see
    # an end of file, and neither open blocks.
    rfd = os.open(out_fifo, os.O_RDWR | os.O_NONBLOCK)
    wfd = os.open(in_fifo, os.O_RDWR)
    logf = open(args.log, 'wb')
    typed = open(args.log + '.typed', 'wb')
    hooklog = open(args.log + '.hooks', 'wb')
    keys = open(args.keys, 'rb').read().decode().splitlines()
    cmd = [os.path.join(ROOT, 'tools/qemu-run'), '--firmware', args.leg, '--accel', args.accel,
           '--timeout', str(args.timeout), '--serial', out_fifo, '--serial-input', in_fifo]
    if args.drive:
        cmd += ['--drive', args.drive + ',ro']
    cmd += [args.iso, '--', '-monitor', 'unix:%s,server=on,wait=off' % mon] + args.qemu
    q = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    seen = b''      # the scrubbed transcript written so far, CRs removed
    counted = 0     # prompts seen since `run 1:`
    typed_n = 0
    steps_done = 0  # STEP: lines whose hooks have run
    why = ''
    halted = False
    t_end = time.monotonic() + args.timeout
    t_prompt = time.monotonic()
    t0 = t_prompt
    prompt_at = 0.0
    pause_until = 0.0

    def pump(wait):
        nonlocal seen
        r, _, _ = select.select([rfd], [], [], wait)
        if not r:
            return False
        try:
            data = os.read(rfd, 65536)
        except BlockingIOError:
            return False
        if not data:
            return False
        out = scrub.feed(data)
        if out:
            logf.write(out)
            logf.flush()
            seen += out.replace(b'\r', b'')
        return True

    def view():
        # What the console has shown, scrubbed: the bytes written and the
        # tail the scrub still holds (in memory only, never written until
        # it is known to begin no secret). Prompts and STEP lines are read
        # here, so a prompt in the held tail is still seen.
        return seen + scrub.pending.replace(b'\r', b'')

    def prompts():
        v = view()
        s = v.find(b'run 1: ')
        return 0 if s < 0 else v[s:].count(args.prompt.encode())

    while time.monotonic() < t_end and q.poll() is None:
        pump(0.1)
        # STEP:LABEL lines run their hooks before anything more is typed.
        found = re.findall(rb'(?m)^STEP:([A-Za-z0-9_.-]+)\n', view())
        while steps_done < len(found):
            label = found[steps_done].decode()
            steps_done += 1
            prog = hooks.get(label)
            if prog:
                code, text = run_hook(prog, args.hook_bound)
                hooklog.write(scrub.text(b'HOOK %s exit=%s\n' % (label.encode(), str(code).encode()) + text))
                hooklog.flush()
            t_prompt = time.monotonic()
        if typed_n < len(keys):
            n = prompts()
            if n > counted:
                if not pause_until:
                    pause_until = time.monotonic() + 0.2
                    prompt_at = time.monotonic() - t0
                if time.monotonic() >= pause_until:
                    pause_until = 0.0
                    counted += 1
                    line = keys[typed_n]
                    typed_n += 1
                    began = time.monotonic() - t0
                    for ch in line.encode() + b'\r':
                        os.write(wfd, bytes([ch]))
                        time.sleep(0.02)
                    t_prompt = time.monotonic()
                    typed.write(scrub.text(('step %d: %s  [prompt %.2f s, typed %.2f-%.2f s]\n'
                                            % (typed_n, line, prompt_at, began, t_prompt - t0)).encode()))
                    typed.flush()
            elif time.monotonic() - t_prompt > args.prompt_timeout:
                why = 'prompt %d did not come within %d s (step %d)' % (counted + 1, args.prompt_timeout, typed_n + 1)
                break
        else:
            if re.search(rb'(?m)^halt$', view()):
                halted = True
                break
            if time.monotonic() - t_prompt > 60:
                why = 'no halt within 60 s of the last line'
                break
    else:
        if q.poll() is not None and not why:
            why = 'QEMU ended before the session did (qemu-run %d)' % q.returncode
        elif not why:
            why = 'the session did not end within %d s' % args.timeout
    # Ends QEMU through its monitor; qemu-run then exits on its own.
    if q.poll() is None:
        try:
            s = socket.socket(socket.AF_UNIX)
            s.connect(mon)
            s.sendall(b'quit\n')
            s.close()
        except OSError:
            pass
        try:
            q.wait(timeout=30)
        except subprocess.TimeoutExpired:
            q.terminate()
            q.wait(timeout=30)
    while pump(0.2):
        pass
    tail = scrub.feed(b'', final=True)
    logf.write(tail)
    logf.close()
    typed.close()
    # qemu-run's own files beside the FIFO: its record of the command line
    # (paths only) and QEMU's messages, scrubbed like the rest.
    for sfx in ('.meta', '.qemu.log'):
        p = out_fifo + sfx
        if os.path.isfile(p):
            hooklog.write(b'FILE com1%s\n' % sfx.encode() + scrub.text(open(p, 'rb').read()))
            os.unlink(p)
    hooklog.write(scrub.text(b'QEMU-RUN ' + (q.stdout.read() or b'')))
    hooklog.close()
    os.close(rfd)
    os.close(wfd)
    for f in (out_fifo, in_fifo, mon):
        if os.path.exists(f):
            os.unlink(f)
    c = scrub.counts
    say('SCRUB %d replacements: name %d, token %d, key %d' % (sum(c.values()), c['name'], c['token'], c['key']))
    if why:
        say('CONSOLE FAIL %s' % why)
        return 1
    if typed_n != len(keys) or not halted:
        say('CONSOLE FAIL typed %d of %d lines, halted %s' % (typed_n, len(keys), halted))
        return 1
    say('CONSOLE ok: %d lines typed, halted' % typed_n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
