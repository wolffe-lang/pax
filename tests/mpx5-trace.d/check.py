#!/usr/bin/env python3
"""Exact transcript gate, plus independently named tracing ABI rows.

Usage: check.py MODE TRANSCRIPT | --selftest
No filtering or normalization here. trace.c names its two normalizations
(pid equality, successful-open descriptor). The *.linux files are observed
Linux output, not output generated from the implementation being tested.
"""
import difflib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MODES = ('core', 'syscall', 'exec', 'errors', 'stops')
# Each inclusive span is a separately named red-first row. The whole-file
# comparison also covers every call result outside these spans.
ROWS = {
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
