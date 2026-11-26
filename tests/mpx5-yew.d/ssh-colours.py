#!/usr/bin/env python3
"""The editor suite's SSH leg, using the existing authenticated PTY rig."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROWS = runpy.run_path(str(HERE / 'colour.py'))
KEYS = runpy.run_path(str(HERE / 'colour-results.py'))['report_keys']
PROMPT = rb'\S+@\S+ \S+> $|[$#] $'


def run_rows(client, where):
    terminal = client.terminal(where, 50, 160)
    passed = True
    try:
        if not terminal.expect(PROMPT, 60):
            print('FAIL yew-colour-session-ssh no shell prompt', flush=True)
            return False
        at = terminal.type(b'env HOME=/home/pax TERM=linux /bin/termwolf ps2\r')
        if terminal.expect(rb'ps2> $', 30, at):
            terminal.type(b'\x1b[1;7A\x1b[1;7B.')
            if not terminal.expect(rb'P: typed: [0-9a-f ]+\n', 30, at):
                print('FAIL yew-key-probe-ssh no raw-byte report', flush=True)
                passed = False
            terminal.expect(PROMPT, 30, at)
        else:
            print('FAIL yew-key-probe-ssh no probe prompt', flush=True)
            passed = False
        sample = terminal.raw[at:]
        (client.dir / 'yew-ssh-keys.raw').write_bytes(sample)
        passed = KEYS(sample, 'ssh') and passed
        for mode in ('default', 'colour'):
            extra = b'YEW_COLORS=truecolor ' if mode == 'colour' else b''
            at = terminal.type(b'env HOME=/home/pax TERM=linux ' + extra
                               + b'/bin/yew --clean /home/pax/keyword.lu\r')
            terminal.pump(45)
            sample = terminal.raw[at:]
            (client.dir / ('yew-ssh-' + mode + '.raw')).write_bytes(sample)
            if mode == 'default':
                passed = ROWS['report_default'](sample, 'ssh') and passed
            else:
                passed = ROWS['report_colour'](sample, 'ssh') and passed
            terminal.type(b'\x1b')
            terminal.pump(1)
            quit_at = terminal.type(b':q!\r')
            if not terminal.expect(PROMPT, 45, quit_at):
                print(f'FAIL yew-colour-quit-ssh-{mode} no shell prompt', flush=True)
                return False
    finally:
        (client.dir / 'yew-ssh-session.raw').write_bytes(terminal.raw)
        terminal.close()
    return passed
