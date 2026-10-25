#!/usr/bin/env python3
"""QMP greeting, capability negotiation and acknowledged quit through EOF.

Protocol: QEMU's published qmp-spec, not implementation source. Retaining
this connection is essential: closing immediately after send does not prove
that QEMU consumed the command. Keep the transcript for failed CI boots.
"""
import json
import socket


def quit_qmp(address, transcript):
    with open(transcript, 'w') as log, socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(10)
        conn.connect(address)
        with conn.makefile('rb') as stream:
            def receive(closing=False):
                try:
                    line = stream.readline(65537)
                except ConnectionResetError:
                    # QEMU can reset its monitor socket while exiting. This
                    # counts as closure only AFTER the quit acknowledgement.
                    if not closing:
                        raise
                    line = b''
                if not line:
                    log.write('RX EOF\n'); log.flush()
                    return None
                if len(line) > 65536 or not line.endswith(b'\n'):
                    raise RuntimeError('invalid or oversized QMP message')
                log.write('RX ' + line.decode('utf-8')); log.flush()
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError('QMP message is not an object')
                return value

            def command(name, ident):
                line = json.dumps({'execute': name, 'id': ident}) + '\n'
                log.write('TX ' + line); log.flush()
                conn.sendall(line.encode())

            def acknowledge(ident):
                for _ in range(64):
                    message = receive()
                    if message is None:
                        raise RuntimeError('EOF before ' + ident + ' acknowledgement')
                    if 'event' in message:
                        continue
                    if message.get('id') != ident:
                        raise RuntimeError('unexpected QMP response id')
                    if 'error' in message:
                        raise RuntimeError('QMP ' + ident + ': ' + str(message['error']))
                    if 'return' not in message:
                        raise RuntimeError('QMP response has neither return nor error')
                    return
                raise RuntimeError('too many QMP events before acknowledgement')

            greeting = receive()
            if greeting is None or 'QMP' not in greeting:
                raise RuntimeError('missing QMP greeting')
            command('qmp_capabilities', 'capabilities')
            acknowledge('capabilities')
            command('quit', 'quit')
            acknowledge('quit')
            # Acknowledgement alone is not process exit. Keep the socket
            # alive until the monitor closes it; boot.py then waits for
            # the repository runner to reap QEMU with its normal timeout.
            for _ in range(64):
                message = receive(closing=True)
                if message is None:
                    return
                if 'event' not in message:
                    raise RuntimeError('unexpected QMP response after quit')
            raise RuntimeError('QMP did not close after quit')
