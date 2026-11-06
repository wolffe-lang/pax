#!/usr/bin/env python3
"""Exact transcript gate, plus independently named tracing ABI rows.

Usage: check.py MODE TRANSCRIPT | --selftest
No filtering or normalization here. trace.c names its normalizations
(pid equality, successful-open descriptor, notification uid equality). The *.linux files are observed
Linux output, not output generated from the implementation being tested.
"""
import difflib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MODES = ('core', 'syscall', 'exec', 'errors', 'stops', 'regs', 'step', 'notify', 'notify-syscall', 'detach-exit', 'exitkill', 'fork-event', 'vfork-event', 'vfork-order', 'clone-event', 'attach', 'seize', 'replace-signal', 'seize-fork', 'fault-handler', 'untraced-db', 'fault-segv', 'fault-ill', 'fault-fpe', 'fault-pass', 'group-exit', 'group-exit-event', 'exec-thread', 'tracer-thread', 'traceme-thread', 'blocked-read', 'blocked-sleep', 'blocked-futex', 'blocked-restart', 'blocked-eintr', 'memory', 'perm', 'conc', 'tasks')
# Each inclusive span is a separately named red-first row. The whole-file
# comparison also covers every call result outside these spans.
ROWS = {
    'conc': (
        ('conc-memory', 'conc.a.poke=', 'conc.b.data='),
        ('conc-wait-any', 'conc.any.distinct=', 'conc.b.rdi='),
        ('conc-kill-one', 'conc.a.kill=', 'conc.b.reaped='),
    ),
    'tasks': (
        ('tasks-thread-mem', 'tasks.tid.distinct=', 'tasks.thread.after.value='),
        ('tasks-leader-bogus', 'tasks.leader.open=', 'tasks.tidpath.open='),
        ('tasks-thread-status', 'tasks.thread.tracer=', 'tasks.leader.tracer-is-parent='),
        ('tasks-ptrace-thread', 'tasks.thread.ptrace-peek=', 'tasks.held.pread='),
    ),
    'perm': (
        ('perm-control', 'perm.control.attach=', 'perm.control.environ='),
        ('perm-uid-changed', 'perm.uid-changed.attach=', 'perm.uid-changed.environ='),
        ('perm-same-uid-after-setuid', 'perm.same-uid-after-setuid.attach=', 'perm.same-uid-after-setuid.environ='),
        ('perm-dumpable-reset', 'perm.dumpable-reset.attach=', 'perm.dumpable-reset.environ='),
        ('perm-dumpable-off', 'perm.dumpable-off.attach=', 'perm.dumpable-off.environ='),
    ),
    'memory': (
        ('mem-cross-page', 'mem.cross.peek=', 'mem.cross.poke.high.value='),
        ('mem-prot-none', 'mem.none.peek=', 'mem.none.after.value='),
        ('mem-private-file', 'mem.ro.peek=', 'mem.private.other.value='),
        ('mem-shared', 'mem.shared.peek=', 'mem.noncanonical.peek='),
        ('mem-proc-mem', 'mem.open=', 'mem.after.ro.value='),
        ('mem-proc-self', 'mem.self.open=', 'mem.self.after='),
        ('mem-held-exec', 'mem.held.pread=', 'mem.reopen.pread='),
    ),
    'blocked-read': (
        ('read-attach-regs', 'blocked.attach.status=', 'blocked.attach.after-syscall='),
        ('read-restarted', 'blocked.entry.status=', 'blocked.end.status='),
    ),
    'blocked-sleep': (
        ('sleep-attach-regs', 'blocked.attach.status=', 'blocked.attach.after-syscall='),
        ('sleep-restart-syscall', 'blocked.entry.status=', 'blocked.end.status='),
    ),
    'blocked-futex': (
        ('futex-attach-regs', 'blocked.attach.status=', 'blocked.attach.after-syscall='),
        ('futex-restarted', 'blocked.entry.status=', 'blocked.end.status='),
    ),
    'blocked-restart': (
        ('restart-attach-regs', 'blocked.attach.status=', 'blocked.attach.after-syscall='),
        ('handler-sa-restart', 'blocked.signal.status=', 'blocked.end.status='),
    ),
    'blocked-eintr': (
        ('eintr-attach-regs', 'blocked.attach.status=', 'blocked.attach.after-syscall='),
        ('handler-eintr', 'blocked.signal.status=', 'blocked.end.status='),
    ),
    'group-exit': (('group-exit', 'group.first.status=', 'group.second.is-leader='),),
    'group-exit-event': (
        ('group-exit-event', 'group.event.distinct=', 'group.event.leader.resume='),
        ('group-exit-order', 'group.first.status=', 'group.second.is-leader='),
    ),
    'exec-thread': (
        ('exec-former-tid', 'exec.event.status=', 'exec.former-is-leader='),
        ('exec-thread-gone', 'exec.thread.getregs=', 'exec.exit.pid-is-leader='),
    ),
    'tracer-thread': (
        ('tracer-thread', 'tthread.seize=', 'tthread.leader.nohang='),
        ('tracer-thread-exit', 'tthread.detached=', 'tthread.echild='),
    ),
    'traceme-thread': (('traceme-thread', 'mthread.wait.found=', 'mthread.leader.getregs='),),
    'attach': (
        ('attach', 'control.attach=', 'control.attach-again='),
        ('inject-signal', 'control.inject-usr1=', 'control.usr2.status='),
        ('detach-suppress', 'control.detach.bad-signal=', 'control.exit.status='),
    ),
    'seize': (
        ('seize-arguments', 'control.seize.bad-addr=', 'control.interrupt='),
        ('interrupt', 'control.stop.status=', 'control.attach-again='),
        ('detach-live', 'control.detach=', 'control.mem.finish='),
    ),
    'replace-signal': (('replace-signal', 'control.self-signal=', 'control.exit.status='),),
    'seize-fork': (('seized-child', 'control.start-fork=', 'event.echild='),),
    'fault-handler': (('fault-pass-handler', 'control.fault.status=', 'control.exit.status='),),
    'untraced-db': (('untraced-db', 'control.ack.signal=', 'control.exit.status='),),
    'fault-segv': (('fault-segv', 'fault.status=', 'wait.echild='),),
    'fault-ill': (('fault-ill', 'fault.status=', 'wait.echild='),),
    'fault-fpe': (('fault-fpe', 'fault.status=', 'wait.echild='),),
    'fault-pass': (('fault-replace-signal', 'fault.status=', 'fault.passed.status='),),
    'fork-event': (
        ('fork-event', 'event.parent.status=', 'event.child.initial='),
        ('fork-real-parent', 'event.child.exit=', 'event.echild='),
    ),
    'vfork-event': (
        ('vfork-event', 'event.parent.status=', 'event.child.initial='),
        ('vfork-blocked-parent', 'event.parent.nohang=', 'event.vfork.child='),
        ('vfork-real-parent', 'event.child.exit=', 'event.echild='),
    ),
    'vfork-order': (
        ('vfork-child-first', 'event.child.exec=', 'event.vfork.child='),
        ('vfork-real-parent', 'event.child.exit=', 'event.echild='),
    ),
    'clone-event': (
        ('clone-event', 'event.parent.status=', 'event.child.initial='),
        ('traced-thread-exit', 'event.child.exit=', 'event.echild='),
    ),
    'detach-exit': (('tracer-exit-detach', 'orphan.options=', 'tracee.after-tracer.status='),),
    'exitkill': (('exitkill', 'orphan.options=', 'tracee.after-tracer.status='),),
    'notify-syscall': (
        ('sigchld-syscall-entry', 'syscall.entry.status=', 'syscall.entry.orig_rax='),
        ('sigchld-syscall-exit', 'syscall.exit.status=', 'syscall.exit.orig_rax='),
    ),
    'notify': (
        ('sigchld-exec', 'notify.options=', 'notify.exec code='),
        ('sigchld-exit', 'notify.second.status=', 'notify.exit-event code='),
        ('sigchld-final', 'notify.final.code=', 'notify.final.pid-present='),
    ),
    'regs': (
        ('selectors', 'exec.rip=', 'user.dr7.initial='),
        ('regset', 'getregset.prstatus=', 'getregset.fp.length='),
    ),
    'step': (
        ('setregs', 'setregs=', 'setregs.ss='),
        ('single-step', 'step.nop.status=', 'step.dr6='),
        ('step-syscall', 'step.syscall.status=', 'step.syscall.dr6='),
    ),
    'stops': (
        ('stop-waitid', 'waitid.nowait=', 'initial.status='),
        ('int3-stop', 'int3.status=', 'int3.second.status='),
        ('stop-exit', 'continue.exit=', 'wait.echild='),
    ),
    'core': (
        ('waitid', 'waitid.nowait=', 'initial.status='),
        ('tracer-pid', 'status.open=', 'status.tracer-is-parent='),
        ('selectors', 'exec.rip=', 'user.dr7.initial='),
        ('regset', 'getregset.prstatus=', 'getregset.fp.length='),
        ('memory', 'data.initial=', 'task.mem.open='),
        ('task-mem', 'task.mem.open=', 'int3.status='),
        ('int3', 'int3.status=', 'int3.rip='),
        ('software-breakpoint', 'break.original=', 'poketext.restore='),
        ('setregs', 'setregs=', 'setregs.ss='),
        ('single-step', 'step.nop.status=', 'step.dr6='),
        ('step-syscall', 'step.syscall.status=', 'step.syscall.dr6='),
        ('hardware-db', 'watch.dr0=', 'watch.disable='),
        ('exit', 'continue.exit=', 'wait.echild='),
    ),
    'syscall': (
        ('syscall-entry', 'syscall.entry.status=', 'syscall.entry.orig_rax='),
        ('syscall-exit', 'syscall.exit.status=', 'syscall.exit.orig_rax='),
        ('traceexit', 'event.exit.status=', 'event.exit.message='),
    ),
    'exec': (('traceexec', 'event.exec.status=', 'event.exec.rip='),),
    'errors': (
        ('bad-memory', 'error.peek.unmapped=', 'error.getsiginfo.bad-buffer='),
        ('bad-user-area', 'error.peekuser.unaligned=', 'error.peekuser.outside='),
        ('bad-regset', 'error.regset.unaligned-length=', 'error.regset.unknown='),
        ('bad-options', 'error.options.unknown=', 'error.request.unknown='),
        ('attach-refused', 'error.attach.self=', 'error.attach.traced='),
        ('dr7-validation', 'dr0.valid=', 'dr7.disabled.again='),
        ('kill', 'ptrace.kill=', 'kill.status='),
    ),
}


def span(lines, begin, end):
    starts = [i for i, line in enumerate(lines) if line.startswith(begin)]
    ends = [i for i, line in enumerate(lines) if line.startswith(end)]
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        return None
    return lines[starts[0]:ends[0] + 1]


def judge(mode, actual):
    expected = (ROOT / (mode + '.linux')).read_bytes()
    want = expected.splitlines(keepends=True)
    got = actual.splitlines(keepends=True)
    result = []
    for name, begin, end in ROWS[mode]:
        a = span(want, begin.encode(), end.encode())
        if a is None:
            raise ValueError('invalid reference row: ' + name)
        result.append(('T-' + name, span(got, begin.encode(), end.encode()) == a))
    result.append(('T-' + mode + '-transcript', actual == expected))
    return result


def selftest():
    for mode in MODES:
        source = (ROOT / (mode + '.linux')).read_bytes()
        assert all(ok for _, ok in judge(mode, source))
        assert not any(ok for _, ok in judge(mode, b''))
        for name, begin, end in ROWS[mode]:
            lines = source.splitlines(keepends=True)
            block = span(lines, begin.encode(), end.encode())
            assert block
            damaged = source.replace(block[0], block[0].rstrip(b'\n') + b'-broken\n', 1)
            verdict = dict(judge(mode, damaged))
            assert not verdict['T-' + name], name
            assert not verdict['T-' + mode + '-transcript'], name
            # Duplicate/missing a marker may not make a row pass either.
            for replacement in (b'', block[0] * 2):
                verdict = dict(judge(mode, source.replace(block[0], replacement, 1)))
                assert not verdict['T-' + name], name
        assert not dict(judge(mode, source + b'extra\n'))['T-' + mode + '-transcript']
    print('PASS trace-checker-selftest (every row changed, removed, duplicated; empty/extra transcripts)')


def main():
    if sys.argv[1:] == ['--selftest']:
        selftest()
        return 0
    if len(sys.argv) != 3 or sys.argv[1] not in MODES:
        print(__doc__, file=sys.stderr)
        return 2
    mode = sys.argv[1]
    actual = Path(sys.argv[2]).read_bytes()
    result = judge(mode, actual)
    for name, ok in result:
        print(('PASS ' if ok else 'FAIL ') + name)
    if not all(ok for _, ok in result):
        expected = (ROOT / (mode + '.linux')).read_text().splitlines(keepends=True)
        sys.stdout.writelines(difflib.unified_diff(expected, actual.decode(errors='replace').splitlines(keepends=True),
                                                fromfile=mode + '.linux', tofile=sys.argv[2]))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
