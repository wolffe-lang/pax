#!/usr/bin/env python3
"""Boot-time tracing layout assertion: layout.py SERIAL | --selftest.
The record sizes are emitted from size_of; capacities come from assembly
start/end symbol bounds. Missing/duplicate or overflow lines are RED.
"""
from pathlib import Path
import re
import sys

PATTERN = re.compile(r'^trace-layout: Thread=(\d+) thread-capacity=(\d+) TraceState=(\d+) trace-capacity=(\d+) slots=(\d+)$', re.M)


def valid(text):
    rows = PATTERN.findall(text)
    if len(rows) != 1 or 'FAIL T-trace-layout' in text:
        return False
    thread, thread_cap, trace, trace_cap, slots = map(int, rows[0])
    return thread == thread_cap == 512 and 0 < trace <= trace_cap == 256 and trace % 8 == 0 and slots == 64


def selftest():
    good = 'trace-layout: Thread=512 thread-capacity=512 TraceState=112 trace-capacity=256 slots=64\n'
    assert valid(good)
    assert valid(good.replace('TraceState=112', 'TraceState=256'))
    for old, new in (('Thread=512', 'Thread=520'), ('TraceState=112', 'TraceState=264'),
                     ('thread-capacity=512', 'thread-capacity=520'),
                     ('trace-capacity=256', 'trace-capacity=264'), ('slots=64', 'slots=65')):
        assert not valid(good.replace(old, new)), (old, new)
    assert not valid('')
    assert not valid(good * 2)
    assert not valid(good + 'FAIL T-trace-layout\n')
    print('PASS trace-layout-selftest')


def main():
    if sys.argv[1:] == ['--selftest']:
        selftest()
        return 0
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    text = Path(sys.argv[1]).read_text(errors='replace')
    ok = valid(text)
    print(('PASS ' if ok else 'FAIL ') + 'T-trace-layout')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
