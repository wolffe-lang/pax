#!/usr/bin/env python3
# echo-host — the host's end of tests/mpx6-latency's network leg (px131).
#
#   echo-host.py PORT REPORT
#
# Binds UDP 127.0.0.1:PORT (QEMU's user network delivers there what the
# guest sends to 10.0.2.2:PORT) and, until killed, sends every datagram
# back to where it came from, except one that begins `latprobe`: that is
# a line of the probe's report (latprobe -r), appended to REPORT and not
# answered. Prints `echo-host: port PORT` once bound, `echo-host: busy`
# and exit 1 when the port is taken. Written from QEMU's documentation of
# `-netdev user` and RFC 862.
import socket
import sys

port, report = int(sys.argv[1]), sys.argv[2]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.bind(('127.0.0.1', port))
except OSError:
    print('echo-host: busy', flush=True)
    sys.exit(1)
print('echo-host: port %d' % port, flush=True)
with open(report, 'ab', buffering=0) as out:
    while True:
        data, peer = s.recvfrom(65536)
        if data.startswith(b'latprobe'):
            out.write(data if data.endswith(b'\n') else data + b'\n')
        else:
            s.sendto(data, peer)
