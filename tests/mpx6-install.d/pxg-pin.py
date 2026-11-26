#!/usr/bin/env python3
"""Check the reviewed reader pin and the actual image installation helper."""
from pathlib import Path
import hashlib
import importlib.machinery
import importlib.util
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
REV = 'c9344fce472df7be05efd1b631c99d2a232b61a9'


def check():
    spec = importlib.util.spec_from_file_location('pxg_rows', Path(__file__).with_name('pxg-rows.py'))
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    assert guest.EXPECTED['VERSION'][1].startswith('paxage 0.2.1 (pxg;'), 'I-pxg-version'
    pin = dict(line.split('=', 1) for line in (ROOT / 'user/pxg.pin').read_text().splitlines()
               if line and not line.startswith('#'))
    assert pin['PXG_REV'] == REV, 'I-pxg-version-pin'
    assert pin['PXG_REPO'] == 'https://github.com/wolffe-lang/paxage', 'I-pxg-source-origin'
    assert re.fullmatch('[0-9a-f]{64}', pin.get('PXG_SOURCE_SHA256', '')), 'I-pxg-source-digest'
    if len(sys.argv) == 3 and sys.argv[1] == '--source':
        source = Path(sys.argv[2]).resolve()
        archive = subprocess.run(['git', '-C', str(source), 'archive', '--format=tar', REV],
                                 check=True, capture_output=True).stdout
        assert hashlib.sha256(archive).hexdigest() == pin['PXG_SOURCE_SHA256'], 'I-pxg-source-digest'
        main = subprocess.run(['git', '-C', str(source), 'show', REV + ':src/paxage.lu'],
                              check=True, capture_output=True, text=True).stdout
        assert guest.EXPECTED['VERSION'][1] in main, 'I-pxg-source-version'
        print('PASS I-pxg-source-version')
    else:
        assert len(sys.argv) == 1, 'I-pxg-pin-usage'
    loader = importlib.machinery.SourceFileLoader('distribution_root', str(ROOT / 'tools/distribution-root'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        inputs = Path(temp)
        (inputs / 'pxg').mkdir()
        data = b'production executable fixture\n'
        (inputs / 'pxg/pxg').write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        (inputs / 'pxg/sums.txt').write_text(f'pxg {digest} {len(data)}\n')
        rows = {}
        module.install_pxg(rows, inputs)
        assert rows == {'bin/pxg': (0o100755, 0, 0, data)}, 'I-pxg-image-mode'
    print('PASS I-pxg-version')
    print('PASS I-pxg-version-pin')
    print('PASS I-pxg-source-digest')
    print('PASS I-pxg-image-mode')


if __name__ == '__main__':
    try:
        check()
    except AssertionError as error:
        print(f'FAIL {error}', flush=True)
        sys.exit(1)
