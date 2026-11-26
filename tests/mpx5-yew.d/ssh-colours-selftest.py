#!/usr/bin/env python3
"""Exercise SSH row ordering with a stand-in transport, never an SSH client."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import tempfile

HERE = Path(__file__).resolve().parent
run_rows = runpy.run_path(str(HERE / 'ssh-colours.py'))['run_rows']


def frame(coloured):
    pen = b'\x1b[1;38;2;198;120;221m' if coloured else b'\x1b[37m'
    return b'\x1b[?1049h\x1b[2J\x1b[4;5H' + pen + b'if\x1b[0;37m true { plain_word }'


class Terminal:
    def __init__(self, coloured):
        self.raw = b''
        self.coloured = coloured
        self.closed = False
        self.commands = []

    def expect(self, *args):
        return True

    def type(self, data):
        at = len(self.raw)
        self.commands.append(data)
        if data == b'\x1b[1;7A\x1b[1;7B.':
            self.raw += b'\r\nP: typed: 1b 5b 31 3b 37 41 1b 5b 31 3b 37 42 2e\r\n$ '
        elif b'/bin/yew' in data:
            self.raw += frame(self.coloured and b'YEW_COLORS=truecolor' in data)
        elif data == b':q!\r':
            self.raw += b'\x1b[?1049l$ '
        return at

    def pump(self, seconds):
        pass

    def close(self):
        self.closed = True


class Client:
    def __init__(self, directory, coloured):
        self.dir = directory
        self.tty = Terminal(coloured)

    def terminal(self, where, rows, cols):
        assert (rows, cols) == (50, 160)
        return self.tty


failures = 0
for coloured in (False, True):
    with tempfile.TemporaryDirectory(prefix='yew-ssh-fixture-', dir=os.environ['TMPDIR']) as temp:
        client = Client(Path(temp), coloured)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            passed = run_rows(client, ('fixture', 22))
        log = output.getvalue()
        good = passed == coloured and client.tty.closed
        good = good and 'OBSERVE yew-lu-default-foreground-ssh TERM=linux' in log
        good = good and 'PASS key-ctrl-alt-up-ssh' in log and 'PASS key-ctrl-alt-down-ssh' in log
        good = good and (('FAIL yew-lu-keyword-colour-ssh' in log) == (not coloured))
        good = good and client.tty.commands.count(b':q!\r') == 2
        name = 'coloured' if coloured else 'plain'
        print(('PASS ' if good else 'FAIL ') + 'yew-ssh-transport-fixture-' + name)
        failures += not good
raise SystemExit(int(bool(failures)))
