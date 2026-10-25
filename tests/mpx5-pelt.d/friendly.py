"""px81: generate identical editor actions for PS/2 and serial; assert raw styles."""
from pathlib import Path
import re
import sys


def actions(resize=False):
    rows = [('line', 'winsize')]
    if resize:
        rows += [('line', 'stty cols 80 rows 24'), ('line', 'winsize')]
    rows += [
        ('line', 'set -o friendly -o suggest -o histsearch'),
        ('line', 'echo prefix_suffix'),
        ('type', 'echo prefix'), ('dump', 'default-shadow'), ('cancel', ''),
        ('line', "PELT_COLORS='command=green:shadow=brblack+dim'"),
        ('type', 'echo prefix'), ('dump', 'dim-shadow'), ('cancel', ''),
        ('type', 'echo'), ('dump', 'command'), ('cancel', ''),
        ('type', 'px81_missing'), ('dump', 'unknown'), ('cancel', ''),
        ('type', "echo '"), ('dump', 'open-quote'), ('cancel', ''),
        ('line', "abbr add zz 'echo PX81-ABBR'"),
        ('type', 'zz '), ('dump', 'abbr-space'), ('enter', ''),
        ('line', 'echo PX81-EVENT'), ('line', '!!'), ('line', 'echo !$'),
        ('type', 'echo '), ('alt', '.'), ('dump', 'last-arg'), ('enter', ''),
        ('line', 'set +o friendly'), ('line', 'echo PX81-DONE'), ('line', 'exit 0'),
    ]
    return rows


def generate(out, mode):
    rows = actions(mode == 'serial-sized')
    ps2 = ['#!ps2-session', 'prompt 1 $\\x20']
    serial = []
    for op, text in rows:
        if op == 'dump':
            ps2 += ['dump ' + text + ' 1']
            continue
        if op in ('line', 'type'):
            ps2 += ['type ' + text]
            if op == 'line':
                ps2 += ['enter']
            raw = text + ('^.' if op == 'type' else '')
        elif op == 'cancel':
            ps2 += ['key ctrl-c']; raw = '^C^.'
        elif op == 'enter':
            ps2 += ['enter']; raw = ''
        else:
            ps2 += ['key alt-dot']; raw = '\x1b.^.'
        ps2 += ['quiet 1']
        serial += [('^~' if serial else '') + raw]
    (out / 'friendly.ps2.keys').write_text('\n'.join(ps2) + '\n')
    (out / 'friendly.serial.keys').write_text('\n'.join(serial) + '\n')


def styles(raw):
    """Printable runs with their foreground and dim state; no guessed SGR order."""
    fg, dim, buf = 39, False, bytearray()
    runs = []
    for token in re.split(rb'(\x1b\[[0-9;?]*[A-Za-z])', raw):
        if token.startswith(b'\x1b['):
            if buf:
                runs.append((fg, dim, bytes(buf))); buf.clear()
            if token.endswith(b'm'):
                for n in map(int, (token[2:-1] or b'0').split(b';')):
                    if n == 0: fg, dim = 39, False
                    elif n == 2: dim = True
                    elif n == 22: dim = False
                    elif 30 <= n <= 37 or 90 <= n <= 97 or n == 39: fg = n
        else:
            buf.extend(token)
    runs.append((fg, dim, bytes(buf)))
    return runs


def check(raw, mode):
    runs = styles(raw)
    def has(text, fg, dim=None):
        return any(text in t and c == fg and (dim is None or d == dim) for c, d, t in runs)
    clean = re.sub(rb'\x1b\[[0-9;?]*[A-Za-z]', b'', raw).replace(b'\r', b'')
    want = {
        'default shadow SGR90': has(b'_suffix', 90, False),
        'configured shadow SGR2': has(b'_suffix', 90, True),
        'shadow erased': b'\x1b[K' in raw[raw.find(b'_suffix') + len(b'_suffix'):],
        'default resolving command foreground': has(b'echo', 39),
        'configured resolving command green': has(b'echo', 32),
        'unknown command red': has(b'px81_missing', 91),
        'open quote red': has(b"'", 91),
        'Space abbreviation executed': b'\nPX81-ABBR\n' in clean,
        'history events and Alt-dot executed': clean.count(b'\nPX81-EVENT\n') == 4,
        'friendly-off completion': b'\nPX81-DONE\n' in clean,
        'init ended zero': b'PAX: init /bin/env ended with status 0; nothing left to run' in clean,
    }
    size = b'50 160' if mode == 'framebuffer' else b'0 0'
    want['initial window size'] = b'\n' + size + b'\n' in clean
    if mode == 'serial-sized':
        want['explicit resized window'] = b'\n24 80\n' in clean
    for name, ok in want.items():
        print(('PASS' if ok else 'FAIL') + ' F4 ' + mode + ': ' + name)
    return all(want.values())


if __name__ == '__main__':
    if sys.argv[1] == 'generate':
        generate(Path(sys.argv[2]), sys.argv[3])
    elif sys.argv[1] == 'check':
        raise SystemExit(0 if check(Path(sys.argv[2]).read_bytes(), sys.argv[3]) else 1)
    else:
        raise SystemExit('usage: friendly.py generate DIR MODE | check LOG MODE')
