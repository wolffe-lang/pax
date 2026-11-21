#!/usr/bin/env python3
"""Run one program from this small parent and record its peak resident set.

    peak.py OUT CAP PROGRAM [ARG...]

CAP is an address-space limit in bytes (RLIMIT_AS, set in the child just
before exec; 0 sets none). OUT receives one JSON object: the program's exit
status, its peak resident set in KiB (wait4's ru_maxrss for that child
alone) and its wall seconds. The program's own output passes through.

ru_maxrss survives exec, so the figure includes the pages this parent had at
fork. Callers measure /bin/true the same way and print it as the floor.
"""
import json
import os
import resource
import sys
import time


def main():
    if len(sys.argv) < 4:
        print('usage: peak.py OUT CAP PROGRAM [ARG...]', file=sys.stderr)
        return 2
    out, cap, argv = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    start = time.monotonic()
    pid = os.fork()
    if pid == 0:
        try:
            if cap > 0:
                resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
            os.execvp(argv[0], argv)
        finally:
            os._exit(127)
    _, status, usage = os.wait4(pid, 0)
    seconds = time.monotonic() - start
    code = os.waitstatus_to_exitcode(status)
    with open(out, 'w') as f:
        json.dump({'status': code, 'maxrss_kib': usage.ru_maxrss,
                   'seconds': round(seconds, 3)}, f)
    return code if 0 <= code < 256 else 255


if __name__ == '__main__':
    raise SystemExit(main())
