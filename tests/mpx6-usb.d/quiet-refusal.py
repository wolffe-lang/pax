#!/usr/bin/env python3
"""Refuse one composite HID interface without overwriting a real login prompt.

QEMU's hubs form usb1-9 -> usb1-9.1 -> usb1-9.1.1. The small USB-redir
fixture reuses tools/hotplug-session's protocol implementation, not a driver.
Interface 0 is a report-protocol keyboard; interface 1 a boot mouse with zero
endpoints. The latter displaces the former as a pointer candidate, and cannot
be driven. These synthetic bytes reproduce the refusal, not the real KVM's
unknown descriptors. A separate QEMU keyboard and pointer remain usable.

COM1 intentionally retains even quiet kernel lines. The prompt assertion is
byte-for-byte framebuffer equality, never absence from the serial transcript.
The log assertions read real sudo /bin/dmesg -r -t after real /bin/login.
"""
import argparse
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
loader = SourceFileLoader('hotplug_session', str(ROOT / 'tools/hotplug-session'))
hs = module_from_spec(spec_from_loader(loader.name, loader))
loader.exec_module(hs)
REFUSAL = 'xhci: mouse usb1-9.1.1 refused: no interrupt IN endpoint'
SHAPE = dict(name='endpointless second HID interface', device=hs._device(0x0003),
             interfaces=[(0, 3, 0, 0, hs.KEYBOARD_REPORT, 0x81, 8, 1),
                         (1, 3, 1, 2, hs.MOUSE_REPORT, None, 0, 0)],
             mouse_ep=None, keyboard_ep=None)


def configuration():
    body = b''
    for number, cls, sub, proto, report, ep, mps, interval in SHAPE['interfaces']:
        body += bytes([9, 4, number, 0, int(ep is not None), cls, sub, proto, 0]) + hs._hid(report)
        if ep is not None:
            body += bytes([7, 5, ep, 3]) + struct.pack('<H', mps) + bytes([interval])
    return bytes([9, 2]) + struct.pack('<H', 9 + len(body)) + bytes([2, 1, 0, 0xa0, 50]) + body


class Fixture(hs.Redir):
    def __init__(self, path, trace, broken=False):
        self.broken = broken
        super().__init__(SHAPE, path, trace)

    def infos(self):
        types, intervals, ifaces, mps = [255] * 32, [0] * 32, [0] * 32, [0] * 32
        types[0] = types[16] = 0
        mps[0] = mps[16] = 64
        # EP0 and interface 0's IN endpoint; interface 1 genuinely has none.
        types[17], intervals[17], ifaces[17], mps[17] = 3, 1, 0, 8
        body = bytes(types) + bytes(intervals) + bytes(ifaces)
        if self.both & (1 << hs.CAP_EP_MPS):
            body += struct.pack('<32H', *mps)
        self.send(hs.EP_INFO, body)
        cols = [[i[k] for i in SHAPE['interfaces']] + [0] * 30 for k in (0, 1, 2, 3)]
        self.send(hs.IFACE_INFO, struct.pack('<I', 2) + b''.join(bytes(c) for c in cols))

    def answer(self, rtype, request, value, index, length, data):
        if (rtype, request, value) == (0x80, 6, 0x200):
            conf = configuration()
            if self.broken:
                conf = conf[:2] + b'\x05\x00' + conf[4:]  # wTotalLength below the header's size
            return 0, conf
        return super().answer(rtype, request, value, index, length, data)


def verdict(kind, text, before, after):
    """Pure judge, also exercised with deliberately wrong levels and pictures."""
    logs = re.findall(r'REFUSAL-LOG-BEGIN\r?\n(.*?)REFUSAL-LOG-END status=0', text, re.S)
    log = logs[-1].replace('\r', '') if logs else ''
    meaningful = before.startswith(b'P6\n') and len(before) > 1000 and len(set(before[100:])) > 1
    # PPM headers may differ only if the display changed; that is also a failure.
    if kind == 'spare':
        return [('R1-refusal-log-info', log.splitlines().count('<6>' + REFUSAL) == 1),
                ('R2-login-prompt-clean', meaningful and before == after)]
    if kind == 'enumeration':
        found = re.findall(r'^<3>xhci 1: device enumeration failed 0x[0-9a-f]{16}$', log, re.M)
        return [('R4-enumeration-error', len(found) == 1 and meaningful and before != after)]
    name = 'R3-only-pointer-error' if kind == 'sole' else 'R5-detached-pointer-error'
    return [(name, log.splitlines().count('<3>' + REFUSAL) == 1 and meaningful and before != after)]


def selftest():
    conf = configuration()
    assert len(conf) == struct.unpack_from('<H', conf, 2)[0]
    interfaces, endpoints, at = [], [], 0
    while at < len(conf):
        n, typ = conf[at:at + 2]
        assert n >= 2 and at + n <= len(conf)
        if typ == 4:
            interfaces.append(tuple(conf[at + 2:at + 8]))
        if typ == 5:
            endpoints.append(conf[at + 2])
        at += n
    assert interfaces == [(0, 0, 1, 3, 0, 0), (1, 0, 0, 3, 1, 2)] and endpoints == [0x81]
    pic = b'P6\n32 32\n255\n' + bytes(range(256)) * 12
    altered = pic[:-1] + bytes([pic[-1] ^ 1])
    def transcript(level, msg=REFUSAL):
        return f'REFUSAL-LOG-BEGIN\n<{level}>{msg}\nREFUSAL-LOG-END status=0\n'
    good = transcript(6)
    assert all(ok for _, ok in verdict('spare', good, pic, pic))
    assert not dict(verdict('spare', transcript(4), pic, pic))['R1-refusal-log-info']
    assert not dict(verdict('spare', good, pic, altered))['R2-login-prompt-clean']
    assert not any(ok for _, ok in verdict('spare', '', b'', b''))
    for kind in ('sole', 'detached'):
        assert all(ok for _, ok in verdict(kind, transcript(3), pic, altered))
        assert not all(ok for _, ok in verdict(kind, transcript(6), pic, altered))
        assert not all(ok for _, ok in verdict(kind, transcript(3), pic, pic))
    err = 'xhci 1: device enumeration failed 0x0000000000000003'
    assert all(ok for _, ok in verdict('enumeration', transcript(3, err), pic, altered))
    assert not all(ok for _, ok in verdict('enumeration', transcript(4, err), pic, altered))
    socket_paths_selftest()
    print('PASS refusal-judge-selftest descriptor shape, levels, blank log, framebuffer and error visibility')


def socket_paths_selftest():
    """Session construction must not put sockets under a long output path."""
    import tempfile as paths_tempfile
    from unittest.mock import patch

    errors = []
    with paths_tempfile.TemporaryDirectory(prefix='quiet-refusal-paths-') as temporary:
        root = Path(temporary)
        args = argparse.Namespace(output=str(root / ('output-' + 'x' * 100)))
        # A path-only stand-in: Session construction opens no socket there.
        short = Path('/quiet-refusal-test-sockets')
        cases = [('unset', None, False), ('empty', '', False),
                 ('explicit-short', str(short), False),
                 ('explicit-long', str(root / ('tmp-' + 'x' * 100)), True)]
        for name, override, refused in cases:
            with patch.dict(os.environ):
                if override is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = override
                with patch.object(paths_tempfile, 'gettempdir', return_value=str(short)):
                    try:
                        session = Session(args, 'spare')
                    except RuntimeError as exc:
                        ok = refused and str(exc) == 'set TMPDIR to a short lane-owned socket directory'
                    else:
                        ok = not refused and session.base.parent == short
            print(f'{"PASS" if ok else "FAIL"} refusal-socket-{name}', flush=True)
            if not ok:
                errors.append(name)
    assert not errors, f'socket directory selection: {errors}'


class Session:
    def __init__(self, args, kind):
        self.args, self.kind = args, kind
        self.out = Path(args.output).resolve() / kind
        self.out.mkdir(parents=True, exist_ok=True)
        self.serial = self.out / 'serial.log'
        self.base = Path(os.environ.get('TMPDIR', str(self.out))) / f'qr{os.getpid()}'
        self.sock = Path(str(self.base) + '.qmp')
        if len(str(self.base).encode()) > 85:
            raise RuntimeError('set TMPDIR to a short lane-owned socket directory')
        self.fixture = None
        self.conn = self.reader = self.proc = None

    def text(self):
        return self.serial.read_text(errors='replace') if self.serial.exists() else ''

    def execute(self, command, arguments=None):
        payload = {'execute': command}
        if arguments is not None:
            payload['arguments'] = arguments
        self.conn.sendall(json.dumps(payload).encode() + b'\n')
        while True:
            line = self.reader.readline()
            if not line:
                raise RuntimeError('QMP closed')
            reply = json.loads(line)
            if 'error' in reply:
                raise RuntimeError(str(reply))
            if 'return' in reply:
                return reply['return']

    def wait(self, pattern, count=1, timeout=20):
        until = time.monotonic() + timeout
        while len(re.findall(pattern, self.text())) < count:
            if self.proc.poll() is not None or time.monotonic() > until:
                raise RuntimeError(f'{self.kind}: waited for {count} x {pattern!r}')
            time.sleep(.03)

    def type(self, text):
        for ch in text:
            qcode = 'ret' if ch == '\n' else ch
            for down in (True, False):
                self.execute('input-send-event', {'events': [{'type': 'key', 'data': {
                    'down': down, 'key': {'type': 'qcode', 'data': qcode}}}]})
                time.sleep(.04)

    def dump(self, name):
        path = self.out / (name + '.ppm')
        self.execute('screendump', {'filename': str(path)})
        return path.read_bytes()

    def run(self):
        self.serial.unlink(missing_ok=True)
        self.sock.unlink(missing_ok=True)
        trace = self.out / 'redir.log'
        trace.unlink(missing_ok=True)
        cmd = [str(ROOT / 'tools/qemu-run'), '--firmware', self.args.firmware, '--accel', self.args.accel,
               '--serial', str(self.serial), '--timeout', '240', str(Path(self.args.image).resolve()), '--',
               '-qmp', f'unix:{self.sock},server=on,wait=off', '-m', '512M',
               '-device', 'qemu-xhci,id=test-usb,p2=8,p3=4',
               '-device', 'usb-kbd,id=keyboard,bus=test-usb.0,port=1',
               '-device', 'usb-hub,id=hub1,bus=test-usb.0,port=5',
               '-device', 'usb-hub,id=hub2,bus=test-usb.0,port=5.1',
               '-device', 'nec-usb-xhci,id=other-usb,p2=8,p3=4']
        working = self.kind != 'sole'
        if working:
            cmd += ['-device', 'usb-mouse,id=working-mouse,bus=other-usb.0,port=1']
        with (self.out / 'runner.log').open('wb') as output:
            self.proc = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT)
            try:
                until = time.monotonic() + 20
                while not self.sock.exists():
                    if self.proc.poll() is not None or time.monotonic() > until:
                        raise RuntimeError('QMP did not start')
                    time.sleep(.03)
                self.conn = socket.socket(socket.AF_UNIX)
                self.conn.settimeout(20)
                self.conn.connect(str(self.sock))
                self.reader = self.conn.makefile('rb')
                json.loads(self.reader.readline())
                self.execute('qmp_capabilities')
                self.wait(r' login: ', timeout=90)
                identity = f'kernel: {self.args.kernel_commit} sha256 {self.args.kernel_sha},'
                if identity not in self.text():
                    raise RuntimeError('booted kernel identity does not match the supplied ELF and commit')
                if working:
                    self.wait(r'xhci: mouse usb2-5 .*; pointer')
                    self.type('root\n')
                    self.wait(r'REFUSAL-SHELL uid=0 mouse=1')
                    # This pointer is on another controller: classification is system-wide.
                    self.execute('input-send-event', {'events': [{'type': 'rel', 'data': {'axis': 'x', 'value': 7}}]})
                    time.sleep(.2)
                    self.type('mouse\n')
                    self.wait(r'REFUSAL-MOUSE moved=1')
                    if self.kind == 'detached':
                        self.execute('device_del', {'id': 'working-mouse'})
                        self.wait(r'xhci: mouse usb2-5 removed; pointer .* gone')
                    self.type('again\n')
                    self.wait(r' login: ', count=2)
                time.sleep(.3)
                before = self.dump('prompt-before')
                time.sleep(.15)
                if before != self.dump('prompt-stable'):
                    raise RuntimeError('login framebuffer did not settle')
                path = str(self.base) + '.usb'
                self.fixture = Fixture(path, trace, self.kind == 'enumeration')
                self.execute('chardev-add', {'id': 'fixture-c', 'backend': {'type': 'socket', 'data': {
                    'addr': {'type': 'unix', 'data': {'path': path}}, 'server': False}}})
                self.execute('device_add', {'driver': 'usb-redir', 'id': 'fixture', 'chardev': 'fixture-c',
                                            'bus': 'test-usb.0', 'port': '5.1.1'})
                self.wait(r'xhci 1: device enumeration failed' if self.kind == 'enumeration' else re.escape(REFUSAL))
                time.sleep(.4)
                after = self.dump('prompt-after')
                self.type('root\n')
                self.wait(r'REFUSAL-SHELL uid=0', count=2 if working else 1)
                self.type('log\n')
                self.wait(r'REFUSAL-LOG-END status=0')
                if self.fixture.error:
                    raise RuntimeError(f'USB fixture: {self.fixture.error}')
                text = self.text()
                if 'PANIC' in text or 'REFUSAL-BAD-COMMAND' in text:
                    raise RuntimeError('guest panic or incorrect shell command')
                result = verdict(self.kind, text, before, after)
                for name, ok in result:
                    print(f'{"PASS" if ok else "FAIL"} {name} {self.args.firmware} {self.args.accel}', flush=True)
                return all(ok for _, ok in result)
            finally:
                if self.conn is not None:
                    try:
                        self.execute('quit')
                    except (OSError, RuntimeError, ValueError):
                        pass
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.proc.terminate()
                    self.proc.wait(timeout=10)
                if self.reader:
                    self.reader.close()
                if self.conn:
                    self.conn.close()
                if self.fixture:
                    self.fixture.listener.close()
                    if self.fixture.conn:
                        self.fixture.conn.close()
                    Path(str(self.base) + '.usb').unlink(missing_ok=True)
                self.sock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selftest', action='store_true')
    parser.add_argument('--image')
    parser.add_argument('--output')
    parser.add_argument('--kernel-sha')
    parser.add_argument('--kernel-commit')
    parser.add_argument('--firmware', choices=('bios', 'uefi'), default='bios')
    parser.add_argument('--accel', choices=('auto', 'kvm', 'tcg'), default='auto')
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return 0
    if not args.image or not args.output:
        parser.error('--image and --output are required')
    if not re.fullmatch('[0-9a-f]{64}', args.kernel_sha or '') or not re.fullmatch('[0-9a-f]{40}', args.kernel_commit or ''):
        parser.error('--kernel-sha and --kernel-commit must name the tested ELF and exact clean head')
    good = True
    for kind in ('spare', 'sole', 'detached', 'enumeration'):
        try:
            good = Session(args, kind).run() and good
        except Exception as exc:
            print(f'FAIL refusal-{kind}-session {exc}', flush=True)
            good = False
    return 0 if good else 1


if __name__ == '__main__':
    sys.exit(main())
