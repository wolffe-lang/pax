#!/usr/bin/env python3
"""Offline Y8 controls. No editor, compiler, container or VM is executed."""
from pathlib import Path
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REF = runpy.run_path(str(ROOT / 'tools/screen-ref'))
FAILURES = 0


def check(name, good):
    global FAILURES
    print(('PASS ' if good else 'FAIL ') + name, flush=True)
    FAILURES += not good


def visible_fixture(base, corrupt):
    where = base / ('content-' + (corrupt or 'good'))
    where.mkdir()
    data = b'PAX: the console\r\n\x1b[?1049h'
    dumps = []
    doc = b'alpha\r\n      beta\r\n      gamma'
    for name in ('editor', 'search', 'edited', 'undo', 'fletch'):
        payload = b'42' if name == 'fletch' else doc
        data += b'\x1b[2J\x1b[2;7H' + payload
        if name == 'search':
            data += b'\x1b[50;1H/beta'
        if name == 'edited':
            data += b'\x1b[5;7Hdelta'
        if name == corrupt:
            # A real failure mode: pixels and serial agree, but a kernel
            # line overwrote alpha. Pixel equality must NOT excuse it.
            data += b'\x1b[2;7Huser: yew pid 7 exit_group 1 after 1 runs\r\n'
        term = REF['Term'](160, 50)
        for byte in data:
            term.feed(byte)
        pixels = bytes(REF['render'](term, REF['font_glyphs'](), 1280, 800))
        (where / (name + '.ppm')).write_bytes(b'P6\n1280 800\n255\n' + pixels)
        dumps.append(f'{name} {len(data)}')
    data += b'\x1b[?1049lPAX: init /bin/as ended with status 0; nothing left to run\r\n'
    (where / 'serial.log').write_bytes(data)
    (where / 'dumps.txt').write_text('\n'.join(dumps) + '\n')
    return subprocess.run([sys.executable, '-I', str(ROOT / 'tests/mpx5-yew.d/features.py'),
                           str(where / 'serial.log'), str(where)],
                          capture_output=True, text=True)


def producer_fixture(base):
    fake = base / 'producer'
    scripts = fake / 'tests/mpx5-yew.d'
    tools = fake / 'tools'
    scripts.mkdir(parents=True)
    tools.mkdir()
    shutil.copyfile(ROOT / 'tests/mpx5-yew.d/features', scripts / 'features')
    (tools / 'lib.sh').write_text('PAX_ROOT="' + str(fake) + '"\ndie() { exit 2; }\n')
    recorder = ('#!' + sys.executable + '\nimport json,os,sys\n'
                'with open(os.environ["Y8_ARGV"],"a") as f: f.write(json.dumps([os.path.basename(sys.argv[0])]+sys.argv[1:])+"\\n")\n')
    for name in ('mkimage', 'qemu-halt'):
        file = tools / name
        file.write_text(recorder)
        file.chmod(0o755)
    (tools / 'ps2-session').write_text('raise SystemExit(0)\n')
    (scripts / 'features.py').write_text('raise SystemExit(0)\n')
    capture = fake / 'argv.jsonl'
    env = dict(os.environ, Y8_ARGV=str(capture))
    result = subprocess.run(['bash', str(scripts / 'features'), '/prepared', 'native', 'bios', str(fake / 'out')],
                            env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in capture.read_text().splitlines()] if capture.exists() else []
    make = next((x for x in calls if x[0] == 'mkimage'), [])
    boot = next((x for x in calls if x[0] == 'qemu-halt'), [])
    return (result.returncode == 0 and make and boot
            and make[make.index('--conf') + 1] == str(fake / 'boot/limine-initramfs-quiet.conf')
            and '/prepared/session.cpio' in make
            and '/prepared/native/kmain_console.elf' in make
            and make[-1] == boot[-1] == str(fake / 'out/session.iso'))


with tempfile.TemporaryDirectory(prefix='yew-features-fixture-') as temp:
    base = Path(temp)
    good = visible_fixture(base, '')
    check('y8-visible-content-complete', good.returncode == 0)
    for frame in ('editor', 'undo'):
        result = visible_fixture(base, frame)
        check('y8-rejects-pixel-identical-kernel-overwrite-' + frame,
              result.returncode != 0 and 'Y8 text lost: alpha' in result.stderr
              and result.stdout.count('PASS Y8 screenshot') == 5)
    check('y8-producer-boots-quiet-copy-of-same-inputs', producer_fixture(base))
raise SystemExit(int(bool(FAILURES)))
