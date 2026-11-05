#!/usr/bin/env python3
# px89 probe (black box): what QEMU's user-mode network answers a DHCP
# client. QEMU joins its user netdev and a socket netdev on one hub; this
# script is the client at the socket's end: it sends RFC 2131 messages as
# whole Ethernet frames (RFC 894, RFC 791, RFC 768, RFC 951's BOOTP body,
# RFC 2132's options) and prints every frame that comes back, decoded.
#   slirp-dhcp.py QEMU_PORT MY_PORT
import socket, struct, sys, time

QPORT, MYPORT = int(sys.argv[1]), int(sys.argv[2])
MAC = bytes.fromhex("525400123456")
XID = 0x50415889

def csum(b):
    if len(b) % 2:
        b += b"\0"
    s = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    while s >> 16:
        s = (s & 0xffff) + (s >> 16)
    return (~s) & 0xffff

def ip4(a):
    return socket.inet_aton(a)

def frame(src, dst, payload, sport=68, dport=67, dmac=b"\xff" * 6):
    udp = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    ph = src + dst + struct.pack("!BBH", 0, 17, len(udp))
    c = csum(ph + udp) or 0xffff
    udp = udp[:6] + struct.pack("!H", c) + udp[8:]
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 1, 0, 64, 17, 0, src, dst)
    hdr = hdr[:10] + struct.pack("!H", csum(hdr)) + hdr[12:]
    return dmac + MAC + b"\x08\x00" + hdr + udp

def bootp(mtype, flags=0x8000, ciaddr=b"\0" * 4, opts=b""):
    b = struct.pack("!BBBBIHH4s4s4s4s", 1, 1, 6, 0, XID, 0, flags, ciaddr, b"\0" * 4, b"\0" * 4, b"\0" * 4)
    b += MAC + b"\0" * 10 + b"\0" * 64 + b"\0" * 128
    b += b"\x63\x82\x53\x63" + bytes([53, 1, mtype]) + opts + bytes([55, 6, 1, 3, 6, 51, 58, 59]) + b"\xff"
    return b

def decode(f):
    out = "len=%d dst=%s src=%s type=%s" % (len(f), f[0:6].hex(":"), f[6:12].hex(":"), f[12:14].hex())
    if f[12:14] == b"\x08\x06":
        op = struct.unpack("!H", f[20:22])[0]
        return out + " ARP op=%d sender=%s target=%s" % (op, socket.inet_ntoa(f[28:32]), socket.inet_ntoa(f[38:42]))
    if f[12:14] != b"\x08\x00":
        return out
    h = f[14:]
    ihl = (h[0] & 15) * 4
    proto = h[9]
    out += " IP src=%s dst=%s proto=%d ttl=%d id=%d flags=%#x" % (socket.inet_ntoa(h[12:16]), socket.inet_ntoa(h[16:20]), proto, h[8], struct.unpack("!H", h[4:6])[0], struct.unpack("!H", h[6:8])[0])
    if proto != 17:
        return out
    u = h[ihl:]
    sp, dp, ul, uc = struct.unpack("!HHHH", u[:8])
    out += " UDP %d->%d len=%d csum=%#x" % (sp, dp, ul, uc)
    b = u[8:]
    if len(b) >= 240 and b[236:240] == b"\x63\x82\x53\x63":
        op, htype, hlen, hops, xid, secs, flags = struct.unpack("!BBBBIHH", b[:12])
        ci, yi, si, gi = (socket.inet_ntoa(b[i:i + 4]) for i in (12, 16, 20, 24))
        out += "\n    BOOTP op=%d xid=%#x secs=%d flags=%#x ciaddr=%s yiaddr=%s siaddr=%s giaddr=%s chaddr=%s sname=%r file=%r" % (
            op, xid, secs, flags, ci, yi, si, gi, b[28:34].hex(":"), b[44:108].rstrip(b"\0"), b[108:236].rstrip(b"\0"))
        o = b[240:]
        i = 0
        while i < len(o):
            t = o[i]
            if t == 0:
                i += 1
                continue
            if t == 255:
                out += "\n    option 255 (end) at %d; %d bytes after" % (i, len(o) - i - 1)
                break
            l = o[i + 1]
            v = o[i + 2:i + 2 + l]
            out += "\n    option %d len %d: %s" % (t, l, v.hex())
            i += 2 + l
    return out

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", MYPORT))
s.settimeout(2.0)
dst = ("127.0.0.1", QPORT)

def exchange(name, f, wait=2.0):
    print("== sent %s: %s" % (name, decode(f)))
    s.sendto(f, dst)
    got = []
    end = time.time() + wait
    while time.time() < end:
        try:
            d, _ = s.recvfrom(4096)
        except socket.timeout:
            break
        print("<= " + decode(d))
        got.append(d)
    return got

zero, bcast = ip4("0.0.0.0"), ip4("255.255.255.255")
offers = exchange("DISCOVER broadcast-flag", frame(zero, bcast, bootp(1)))
exchange("DISCOVER no-broadcast-flag", frame(zero, bcast, bootp(1, flags=0)))
yi = server = None
for d in offers:
    b = d[14 + 20 + 8:]
    if len(b) > 240:
        yi = b[16:20]
        o = b[240:]
        i = 0
        while i < len(o) and o[i] != 255:
            if o[i] == 0:
                i += 1
                continue
            if o[i] == 54:
                server = o[i + 2:i + 6]
            i += 2 + o[i + 1]
if yi:
    req = bootp(3, opts=bytes([50, 4]) + yi + bytes([54, 4]) + (server or b"\0" * 4))
    exchange("REQUEST selecting", frame(zero, bcast, req))
    # a renewal: unicast to the server, ciaddr set, no 50/54 (RFC 2131 4.3.2)
    sm = bytes.fromhex("525400123502")
    exchange("REQUEST renewing (unicast to the server)", frame(yi, server or ip4("10.0.2.2"), bootp(3, flags=0, ciaddr=yi), dmac=sm))
    exchange("REQUEST rebinding (broadcast, ciaddr)", frame(yi, bcast, bootp(3, flags=0, ciaddr=yi)))
    exchange("REQUEST for another address (selecting, wrong 50)", frame(zero, bcast, bootp(3, opts=bytes([50, 4]) + ip4("10.0.2.99") + bytes([54, 4]) + (server or b"\0" * 4))))
    exchange("RELEASE", frame(yi, server or ip4("10.0.2.2"), bootp(7, flags=0, ciaddr=yi, opts=bytes([54, 4]) + (server or b"\0" * 4)), dmac=sm))
