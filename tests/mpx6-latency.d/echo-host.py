#!/usr/bin/env python3
# echo-host — the host's end of tests/mpx6-latency's network leg (px131).
#
#   echo-host.py PORT FWD REPORT
#
# Binds UDP 127.0.0.1:PORT, where QEMU's user network delivers what the
# guest sends to 10.0.2.2:PORT: the probe's report (latprobe -r), each
# datagram one line, appended to REPORT. Once the probe's first line has
# come (its echoes are up), it is the client of the guest's network echo
# (latprobe -e, reached through `hostfwd=udp:127.0.0.1:FWD-:<port>`): a
# datagram due every 5 ms, each round trip counted from when it was due
# (this host is never late, so that is when it was sent), as a person's
# keystrokes over ssh would be. A `latprobe-begin LOAD` line opens a load's
# window and the load's own line closes it; after that line it writes
#
#   hostnet LOAD: n N p50 U p99 U max U lost K
#
# (U in microseconds; lost: no answer within 10 s, 1 s in a flood; one still in flight at
# the window's end is neither). In the window of a load named `flood` it
# pings as fast as the guest answers, FLIGHT datagrams in flight at once
# (the CPU-bound process's share under a stream of device wake-ups is the
# row's; each round trip is counted from when it was sent): the saturating
# flood, whose rate this host's CPUs set. In the window of `flood:R` it
# offers R datagrams a second, each on its own schedule whatever the
# answers (px131: the offered flood); one this host could not send within
# LATE of when it was due is not sent at all, so a stalled host offers less
# rather than a burst. After either flood's window the line also says
# `sent S secs D` (the datagrams sent in the window and its seconds), so
# the rows can tell a host that did not offer R from a guest that did not
# keep up. Prints `echo-host: port PORT` once bound, `echo-host: busy` and
# exit 1 when the port is taken; runs until killed. Written from QEMU's
# documentation of `-netdev user` and RFC 862.
import selectors
import socket
import struct
import sys
import time

port, fwd, report = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
rep = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    rep.bind(('127.0.0.1', port))
except OSError:
    print('echo-host: busy', flush=True)
    sys.exit(1)
cli.connect(('127.0.0.1', fwd))
print('echo-host: port %d' % port, flush=True)
sel = selectors.DefaultSelector()
sel.register(rep, selectors.EVENT_READ, 'rep')
sel.register(cli, selectors.EVENT_READ, 'cli')
STEP = 0.005
FLIGHT = 16
LATE = 0.005    # a paced datagram this late is not sent
flood = False
pace = 0        # the offered flood's datagrams a second (`flood:R`), else 0
pdue = 0.0      # when its next datagram is due
fsent = 0       # datagrams the flood sent in the window
pinging = False
due = 0.0
seq = 0
sent = {}       # seq -> when it was due
done = []       # (due, rtt or None)
window = None   # (load, when it began)


def summary(load, t0, t1, extra=''):
    rtts = sorted(r for d, r in done if t0 <= d < t1 and r is not None)
    lost = sum(1 for d, r in done if t0 <= d < t1 and r is None)
    if not rtts:
        return 'hostnet %s: n 0 p50 0 p99 0 max 0 lost %d%s\n' % (load, lost, extra)
    us = lambda v: int(v * 1e6)
    return 'hostnet %s: n %d p50 %d p99 %d max %d lost %d%s\n' % (
        load, len(rtts), us(rtts[len(rtts) // 2]), us(rtts[len(rtts) * 99 // 100]), us(rtts[-1]), lost, extra)


with open(report, 'ab', buffering=0) as out:
    while True:
        now = time.monotonic()
        timeout = max(0.0, due - now) if pinging else None
        if flood and len(sent) < FLIGHT:
            timeout = 0.0
        if pace:
            wait = max(0.0, pdue - now)
            timeout = wait if timeout is None else min(timeout, wait)
        for key, _ in sel.select(timeout):
            if key.data == 'rep':
                data, _peer = rep.recvfrom(65536)
                line = data.decode(errors='replace')
                if not line.endswith('\n'):
                    line += '\n'
                out.write(line.encode())
                t = time.monotonic()
                if line.startswith('latprobe: tsc') and not pinging:
                    pinging, due = True, t
                elif line.startswith('latprobe-begin '):
                    window = (line.split()[1], t)
                    flood = window[0] == 'flood'
                    pace = int(window[0][6:]) if window[0].startswith('flood:') and window[0][6:].isdigit() else 0
                    pdue, fsent = t, 0
                elif window and line.startswith('latprobe %s:' % window[0]):
                    extra = ' sent %d secs %.3f' % (fsent, t - window[1]) if flood or pace else ''
                    out.write(summary(window[0], window[1], t, extra).encode())
                    window = None
                    flood = False
                    pace = 0
                    done = [x for x in done if x[0] >= t - 1]
            else:
                try:
                    data = cli.recv(64)
                except OSError:
                    continue
                if len(data) == 8:
                    (k,) = struct.unpack('<Q', data)
                    d = sent.pop(k, None)
                    if d is not None:
                        done.append((d, time.monotonic() - d))
        now = time.monotonic()
        while flood and len(sent) < FLIGHT:
            seq += 1
            sent[seq] = now
            fsent += 1
            try:
                cli.send(struct.pack('<Q', seq))
            except OSError:
                pass
        while pace and now >= pdue:
            if now - pdue <= LATE:
                seq += 1
                sent[seq] = pdue
                fsent += 1
                try:
                    cli.send(struct.pack('<Q', seq))
                except OSError:
                    pass
            pdue += 1.0 / pace
        if pinging and now >= due:
            seq += 1
            sent[seq] = due
            try:
                cli.send(struct.pack('<Q', seq))
            except OSError:
                pass
            due += STEP
            if due < now:
                due = now + STEP
            for k in [k for k, d in sent.items() if now - d > (1 if flood or pace else 10)]:
                done.append((sent.pop(k), None))
