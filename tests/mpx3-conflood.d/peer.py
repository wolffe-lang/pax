#!/usr/bin/env python3
"""tests/mpx3-conflood.d/peer.py (px129, R-px129-13): the other end of the machine's network cable while
user/elf/conflood floods its console, timing what the network gets.

    peer.py --listen PORT --qemu PORT --out FILE.json [--timeout SECONDS] [--every MS]

QEMU runs with `-netdev socket,udp=127.0.0.1:<listen>,localaddr=127.0.0.1:<qemu>` (tools/net-peer's way:
each Ethernet frame the guest sends is one datagram to <listen>, each datagram sent to <qemu> one frame it
receives). This script is the whole network: 10.0.2.100 (52:54:00:00:00:aa), answering ARP for itself; the
guest is 10.0.2.15 (52:54:00:12:34:56), kmain_console's fixed address. Every --every ms (50) it sends,
alternately, an ICMP echo request (answered by the kernel's network thread, kernel/netd, kernel/icmp: no
process) and a UDP datagram to port 7 (answered by conflood's echo child: a process scheduled to answer, as
an ssh server is for a keystroke), each with its sequence number, and times each answer. conflood's
datagrams to port 9 say the phase (idle, flood, after, end); a request belongs to the phase it was sent in.
At `end` (or the timeout) it writes FILE.json: per probe and phase the requests sent, answered, and the
round trips (ms) of the answered, plus the phases' times. Prints one line a phase and probe. Exit 0 when
the run reached `end`, 1 otherwise.

Written from RFC 826 (ARP), RFC 791 (IP), RFC 792 (ICMP), RFC 768 (UDP) and QEMU's documentation of its
socket netdev. No network stack's source.
"""
import argparse
import json
import select
import socket
import struct
import sys
import time

ME_MAC = bytes.fromhex("5254000000aa")
ME_IP = socket.inet_aton("10.0.2.100")
GUEST_MAC = bytes.fromhex("525400123456")
GUEST_IP = socket.inet_aton("10.0.2.15")
SPORT = 40007


def csum(b):
    if len(b) % 2:
        b += b"\0"
    s = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def ipv4(proto, payload, ident):
    h = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), ident & 0xFFFF, 0, 64, proto, 0, ME_IP, GUEST_IP)
    h = h[:10] + struct.pack("!H", csum(h)) + h[12:]
    return GUEST_MAC + ME_MAC + b"\x08\x00" + h + payload


def icmp_echo(seq, ident):
    data = struct.pack("!Q", seq) + bytes(48)
    m = struct.pack("!BBHHH", 8, 0, 0, 0x7129, seq & 0xFFFF) + data
    m = m[:2] + struct.pack("!H", csum(m)) + m[4:]
    return ipv4(1, m, ident)


def udp_echo(seq, ident):
    data = b"px129 " + struct.pack("!Q", seq) + bytes(32)
    u = struct.pack("!HHHH", SPORT, 7, 8 + len(data), 0) + data
    pseudo = ME_IP + GUEST_IP + struct.pack("!BBH", 0, 17, len(u))
    c = csum(pseudo + u) or 0xFFFF
    u = u[:6] + struct.pack("!H", c) + u[8:]
    return ipv4(17, u, ident)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int, required=True)
    ap.add_argument("--qemu", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--every", type=float, default=50)
    a = ap.parse_args()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", a.listen))
    to = ("127.0.0.1", a.qemu)
    t_start = time.monotonic()
    phase = "boot"
    phases = []  # (name, t)
    sent = {}  # (probe, seq) -> (t, phase)
    rtts = {}  # (probe, seq) -> ms
    seq = 0
    ident = 1
    nxt = t_start
    ended = False
    guest_up = False
    while time.monotonic() - t_start < a.timeout:
        now = time.monotonic()
        if guest_up and now >= nxt and phase in ("idle", "flood", "after"):
            seq += 1
            probe = "ping" if seq % 2 else "echo"
            f = icmp_echo(seq, ident) if probe == "ping" else udp_echo(seq, ident)
            ident += 1
            s.sendto(f, to)
            sent[(probe, seq)] = (now, phase)
            nxt = now + a.every / 1000.0
        wait = max(0.0, min(0.01, nxt - time.monotonic()))
        r, _, _ = select.select([s], [], [], wait)
        if not r:
            continue
        f, _ = s.recvfrom(65536)
        now = time.monotonic()
        if len(f) < 14:
            continue
        et = struct.unpack("!H", f[12:14])[0]
        if et == 0x0806 and len(f) >= 42:
            op = struct.unpack("!H", f[20:22])[0]
            tpa = f[38:42]
            if op == 1 and tpa == ME_IP:
                rep = f[6:12] + ME_MAC + b"\x08\x06" + struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2) + ME_MAC + ME_IP + f[22:28] + f[28:32]
                s.sendto(rep, to)
            continue
        if et != 0x0800 or len(f) < 34:
            continue
        ihl = (f[14] & 0x0F) * 4
        proto = f[23]
        src = f[26:30]
        body = f[14 + ihl:]
        if src != GUEST_IP:
            continue
        if proto == 1 and len(body) >= 16 and body[0] == 0:
            q = struct.unpack("!Q", body[8:16])[0]
            k = ("ping", q)
            if k in sent and k not in rtts:
                rtts[k] = (now - sent[k][0]) * 1000.0
        elif proto == 17 and len(body) >= 8:
            sp, dp = struct.unpack("!HH", body[:4])
            data = body[8:]
            if dp == 9:
                msg = data.decode("ascii", "replace").strip()
                if msg.startswith("conflood: "):
                    name = msg[len("conflood: "):].split()[0]
                    phases.append((name, round(now - t_start, 3), msg))
                    print(f"peer: {now - t_start:8.3f} s {msg}", flush=True)
                    phase = name
                    guest_up = True
                    if name == "end":
                        ended = True
                        break
            elif sp == 7 and dp == SPORT and data.startswith(b"px129 ") and len(data) >= 14:
                q = struct.unpack("!Q", data[6:14])[0]
                k = ("echo", q)
                if k in sent and k not in rtts:
                    rtts[k] = (now - sent[k][0]) * 1000.0
    res = {"ended": ended, "every_ms": a.every, "phases": phases, "probes": {}}
    for probe in ("ping", "echo"):
        for ph in ("idle", "flood", "after"):
            ks = [k for k, v in sent.items() if k[0] == probe and v[1] == ph]
            got = sorted(rtts[k] for k in ks if k in rtts)
            n = len(got)
            st = {"sent": len(ks), "answered": n}
            if n:
                st.update(median=round(got[n // 2], 3), p95=round(got[min(n - 1, int(n * 0.95))], 3), max=round(got[-1], 3))
            res["probes"][f"{probe} {ph}"] = st
            print(f"peer: {probe} {ph}: " + ", ".join(f"{k} {v}" for k, v in st.items()), flush=True)
    with open(a.out, "w") as o:
        json.dump(res, o, indent=1)
    sys.exit(0 if ended else 1)


if __name__ == "__main__":
    main()
