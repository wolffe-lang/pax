#!/usr/bin/env python3
"""bound-rows.py — the push suite's bounds and its stuck-fixture probe, on
stubs (px104, R-px104-16).

    bound-rows.py WORKDIR

No QEMU and no secret: a stub TCP server on 127.0.0.1 that accepts and
never answers (the shape of a TLS fixture stuck on an earlier connection),
and a hook that outlives its bound.
  T4 push.py's liveness probe (`liveness`, run by the https way only after a
     failed H1) names the stub as stuck: no TLS handshake within its bound
     (s_client's own exit, never a hang), with the stub's accept and the
     connection ss shows;
  T5 console.py's hook runner (`run_hook`) ends a hook that outlives its
     bound by name, `exit=timeout after N s`, and returns, so the session
     goes on;
  T6 push.py's Linux git step (`git_steps`), cloning from the stub, ends at
     its bound as status 124 named `timeout after N s`, not an exception.
PASS or FAIL per row. Exit 0, or 1 when a row failed.
"""
import importlib.util
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAILS = []


def ok(row, why):
    print('PASS %s %s' % (row, why), flush=True)


def bad(row, why):
    FAILS.append(row)
    print('FAIL %s %s' % (row, why), flush=True)


def load(name):
    spec = importlib.util.spec_from_file_location('px104_' + name, HERE / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Stub:
    """Accepts on 127.0.0.1 and never reads or writes."""
    def __init__(self):
        self.s = socket.socket()
        self.s.bind(('127.0.0.1', 0))
        self.s.listen(8)
        self.port = self.s.getsockname()[1]
        self.held = []
        self.stop = False
        self.t = threading.Thread(target=self.loop, daemon=True)
        self.t.start()

    def loop(self):
        self.s.settimeout(0.2)
        while not self.stop:
            try:
                c, _ = self.s.accept()
                self.held.append(c)
            except OSError:
                pass

    def close(self):
        self.stop = True
        self.t.join(timeout=2)
        for c in self.held:
            c.close()
        self.s.close()


def main():
    work = Path(sys.argv[1])
    work.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='bound-rows.', dir=work))
    os.chmod(d, 0o700)
    push = load('push')
    console = load('console')
    stub = Stub()
    try:
        # T4
        f = getattr(push, 'liveness', None)
        if f is None:
            bad('T4', 'push.py has no liveness probe')
        else:
            t0 = time.monotonic()
            answered, why = f(stub.port, None, os.getpid(), bound=5)
            took = time.monotonic() - t0
            if not answered and 'no TLS handshake' in why and took < 20:
                ok('T4', 'the stub that never answers, named in %.1f s: %s' % (took, why[:160]))
            else:
                bad('T4', 'the probe on the stub: answered %r, %.1f s, %r' % (answered, took, why[:160]))
        # T5
        f = getattr(console, 'run_hook', None)
        hook = d / 'hook-slow'
        hook.write_text('#!/bin/sh\necho before\nsleep 30\necho after\n')
        if f is None:
            bad('T5', 'console.py has no bounded hook runner')
        else:
            t0 = time.monotonic()
            code, text = f(str(hook), 2)
            took = time.monotonic() - t0
            if code == 'timeout' and b'timeout after 2 s' in text and took < 10:
                ok('T5', 'a hook past its 2 s bound ends by name in %.1f s: %s' % (took, text.decode(errors='replace').strip().splitlines()[-1]))
            else:
                bad('T5', 'a hook past its bound: %r after %.1f s, %r' % (code, took, text[-120:]))
        # T6
        git = shutil.which('git')
        if not git:
            bad('T6', 'no git on PATH')
        else:
            home = d / 'home'
            home.mkdir()
            env = push.base_env(home)
            cfg = d / 'gitconfig'
            cfg.write_text('[url "http://127.0.0.1:%d/remote.git"]\n\tinsteadOf = rows-stub:\n' % stub.port)
            env['GIT_CONFIG_GLOBAL'] = str(cfg)
            push.GIT_STEP_BOUND = 3
            got = {}

            def steps():
                try:
                    got['res'] = push.git_steps(git, env, 'rows-stub:', d, 'px104/stub')
                except Exception as e:
                    got['err'] = '%s: %s' % (type(e).__name__, str(e)[:120])
            t0 = time.monotonic()
            th = threading.Thread(target=steps, daemon=True)
            th.start()
            th.join(timeout=30)
            took = time.monotonic() - t0
            res = got.get('res') or []
            first = res[0] if res else None
            if th.is_alive():
                bad('T6', 'Linux git\'s clone from the stub: no bound, still running after %.0f s' % took)
            elif 'err' in got:
                bad('T6', 'Linux git\'s step on the stub raised %s' % got['err'])
            elif first and first[0] == 'clone' and first[1] == 124 and 'timeout after 3 s' in first[2]:
                ok('T6', 'Linux git\'s clone from the stub ends at its 3 s bound by name in %.1f s: %r' % (took, first))
            else:
                bad('T6', 'Linux git\'s steps on the stub: %r after %.1f s' % (res[:2], took))
    finally:
        stub.close()
        shutil.rmtree(d, ignore_errors=True)
    print('BOUND-ROWS: %d of 3 failed%s' % (len(FAILS), (': ' + ' '.join(FAILS)) if FAILS else ''), flush=True)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
