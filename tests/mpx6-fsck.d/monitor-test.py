#!/usr/bin/env python3
"""Exercise boot.py against a bounded delayed monitor peer, no QEMU/signals."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
boot = Path(__file__).with_name('boot.py')
runner = Path(__file__).with_name('monitor-peer.py')
with tempfile.TemporaryDirectory(prefix='m-', dir=root) as tmp:
    work = Path(tmp)
    tools = work/'tools'
    tools.mkdir()
    shutil.copyfile(runner, tools/'qemu-run')
    (tools/'qemu-run').chmod(0o755)
    for fault, okay, diagnostic in [('', True, ''),
                                    ('reject', False, 'deliberate quit rejection'),
                                    ('no-ack', False, 'EOF before quit acknowledgement')]:
        serial = work/'serial'
        serial.write_text('old\nhalt\n')
        result = subprocess.run(['python3', '-I', str(boot), str(work), str(work/'disk'),
                                 str(serial), 'bios', 'halt'],
                                env={**os.environ, 'PX72_MONITOR_FAULT': fault},
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        label = fault or 'delayed-quit'
        (root/(label+'.log')).write_bytes(result.stdout)
        assert (result.returncode == 0) == okay, ('FAIL M-close: '+label, result.returncode, result.stdout.decode())
        if diagnostic:
            assert diagnostic.encode() in result.stdout, (label, result.stdout)
        assert serial.read_text() == 'new\nhalt\n', 'stale serial satisfied marker'
        print('PASS M-monitor-' + label, flush=True)
