"""J4: read the runtime's disposition only after its task has joined.

POSIX.1-2024 exec DESCRIPTION preserves SIG_IGN across exec; sigaction
DESCRIPTION permits the new program to replace that disposition. A wolf
entry point is not an observation made before runtime initialization.
https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html
https://pubs.opengroup.org/onlinepubs/9799919799/functions/sigaction.html
"""
from pathlib import Path
import re
import subprocess
import sys

READY = '~X: runtime task joined'
MASK = '~X: after a joined runtime task: SigIgn: 0000000000000000'


def check(text):
    rows = [line for line in text.splitlines() if line.startswith('~X:')]
    if rows != [READY, MASK]:
        return 'J4 SigIgn ordered probe: require task-joined event before exactly one zero-mask read; got ' + repr(rows)
    return None


def check_fault(text, symbols):
    # Code layout changes when the probe changes. Judge the fault against
    # this executable's recursive function, not an old recording's address.
    spans = []
    for line in symbols.splitlines():
        words = line.split()
        if len(words) >= 8 and words[3] == 'FUNC' and words[7].startswith('_Wdeep$'):
            spans.append((int(words[1], 16), int(words[2])))
    pcs = re.findall(r'^  at pc=0x([0-9a-f]+)$', text, re.M)
    if len(spans) != 1 or len(pcs) != 1:
        return 'J4 overflow PC: require one deep symbol and one fault PC'
    start, size = spans[0]
    if not start <= int(pcs[0], 16) < start + size:
        return 'J4 overflow PC: fault is outside this binary\'s deep function'
    return None


if __name__ == '__main__':
    text = Path(sys.argv[1]).read_text()
    error = check(text)
    if not error:
        symbols = subprocess.check_output(['readelf', '-sW', sys.argv[2]], text=True)
        error = check_fault(text, symbols)
    if error:
        print(error)
        sys.exit(1)
    print('J4 SigIgn ordered probe and overflow PC: PASS')
