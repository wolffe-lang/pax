#!/usr/bin/env python3
"""Stand-in runner: delay quit consumption and reject a disconnected client."""
from pathlib import Path
import json
import os
import socket
import sys
import time

args = sys.argv[1:]
serial = Path(args[args.index('--serial')+1])
qmp = '-qmp' in args
address = args[args.index('-qmp' if qmp else '-monitor')+1]
address = address.removeprefix('unix:').split(',')[0]
fault = os.environ.get('PX72_MONITOR_FAULT', '')
with socket.socket(socket.AF_UNIX) as server:
    server.settimeout(8)
    server.bind(address)
    server.listen(1)
    serial.write_text('new\nhalt\n')
    with server.accept()[0] as conn:
        conn.settimeout(3)
        stream = conn.makefile('rb')
        if not qmp:
            assert stream.readline() == b'quit\n'
            time.sleep(0.15)
            assert conn.recv(1) != b'', 'FAIL M-close: monitor client closed before quit was consumed'
            raise AssertionError('legacy HMP client unexpectedly stayed connected')
        greeting = json.dumps({'QMP': {'version': {}, 'capabilities': []}}).encode()+b'\r\n'
        conn.sendall(greeting[:7]); time.sleep(0.02); conn.sendall(greeting[7:])
        command = json.loads(stream.readline())
        assert command['execute'] == 'qmp_capabilities'
        conn.sendall(json.dumps({'return': {}, 'id': command['id']}).encode()+b'\n')
        command = json.loads(stream.readline())
        assert command['execute'] == 'quit'
        # Withhold the response, testing that the client does not close as
        # soon as it sends quit. A disconnect may discard unread commands.
        time.sleep(0.15)
        conn.settimeout(0.1)
        try:
            data = conn.recv(1)
            assert data != b'', 'FAIL M-close: monitor client closed before quit acknowledgement'
            raise AssertionError('unexpected command bytes')
        except socket.timeout:
            pass
        conn.settimeout(3)
        if fault == 'no-ack':
            pass
        elif fault == 'reject':
            conn.sendall(json.dumps({'error': {'class': 'GenericError', 'desc': 'deliberate quit rejection'},
                                     'id': command['id']}).encode()+b'\n')
        else:
            conn.sendall(json.dumps({'event': 'SHUTDOWN', 'data': {}}).encode()+b'\n')
            conn.sendall(json.dumps({'return': {}, 'id': command['id']}).encode()+b'\n')
            time.sleep(0.15)
        stream.close()
