"""J4: read the runtime's disposition only after its task has joined.

POSIX.1-2024 exec DESCRIPTION preserves SIG_IGN across exec; sigaction
DESCRIPTION permits the new program to replace that disposition. A wolf
entry point is not an observation made before runtime initialization.
https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html
https://pubs.opengroup.org/onlinepubs/9799919799/functions/sigaction.html
"""
from pathlib import Path
import sys

READY = '~X: runtime task joined'
MASK = '~X: after a joined runtime task: SigIgn: 0000000000000000'


def check(text):
    rows = [line for line in text.splitlines() if line.startswith('~X:')]
    if rows != [READY, MASK]:
        return 'J4 SigIgn ordered probe: require task-joined event before exactly one zero-mask read; got ' + repr(rows)
    return None


if __name__ == '__main__':
    error = check(Path(sys.argv[1]).read_text())
    if error:
        print(error)
        sys.exit(1)
    print('J4 SigIgn ordered probe: PASS')
