# paxnet.py — what the network tools share (px21): the Internet checksum,
# frame builders, and a model of what PAX must do with a frame, written
# from the RFCs and not from the kernel, for tools/net-peer (the other
# end of a socket netdev), tools/pcap-net (the capture's checker) and
# tools/gateway-probe.
#
# The model (`judge_ip`, `judge_arp`) names, for a frame that reaches
# PAX, the one thing PAX must do with it, in the words of the kernel's
# counters: a drop cause (`ip.checksum`, `icmp.type`, …), or `echo` (an
# echo request to answer), `reply` (an echo reply), `unreachable` (a
# datagram of an unknown protocol whose sender may be told) or `silent`
# (one whose sender may not). The order of the checks is RFC 791's
# header order as kernel/ip's header states it.
#
# Written from RFC 791, RFC 792, RFC 826, RFC 894, RFC 1071 and RFC
# 1122 §3.2. No network stack's source.
import struct

PAX_MAC = bytes.fromhex("525400123456")
GW_MAC = bytes.fromhex("52550a000202")
PEER_MAC = bytes.fromhex("5254000000aa")
BCAST = b"\xff" * 6
ZERO6 = b"\x00" * 6
PAX_IP = bytes([10, 0, 2, 15])
GW_IP = bytes([10, 0, 2, 2])
PEER_IP = bytes([10, 0, 2, 100])
NOBODY_IP = bytes([10, 0, 2, 99])
FAR_IP = bytes([192, 0, 2, 1])
NETMASK = bytes([255, 255, 255, 0])
SUBNET_BCAST = bytes([10, 0, 2, 255])
LIMITED_BCAST = b"\xff" * 4
ECHO_IDENT = 0x5058
EXPERIMENTAL = b"\x88\xb5"
MARKER = (BCAST + PAX_MAC + EXPERIMENTAL + b"PAX").ljust(60, b"\x00")


def mac(text):
    b = bytes(int(x, 16) for x in text.split(":"))
    if len(b) != 6:
        raise ValueError(text)
    return b


def ip(text):
    b = bytes(int(x) for x in text.split("."))
    if len(b) != 4:
        raise ValueError(text)
    return b


def dotted(b):
    return ".".join(str(x) for x in b)


def csum(b):
    """RFC 1071: the one's complement of the one's-complement sum of
    16-bit big-endian words, an odd last byte a word's high byte. 0 over
    data that already holds its checksum."""
    if len(b) % 2:
        b = b + b"\x00"
    s = sum(struct.unpack(">%dH" % (len(b) // 2), b))
    while s >> 16:
        s = (s & 0xffff) + (s >> 16)
    return (~s) & 0xffff


def pattern(n):
    return bytes((k * 7) & 0xff for k in range(n))


def arp(dst, src, op, sha, spa, tha, tpa, hrd=1, pro=0x0800, hln=6, pln=4):
    return dst + src + b"\x08\x06" + struct.pack(">HHBBH", hrd, pro, hln, pln, op) + sha + spa + tha + tpa


def ipv4(src, dst, proto, payload, ttl=64, ident=0, flags=0x4000, tos=0, options=b"", total=None, version=4, ihl=None, check=None):
    """An IPv4 datagram. `total`, `ihl` and `check` override what would
    be right, for the malformed ones."""
    n = 20 + len(options)
    words = n // 4 if ihl is None else ihl
    length = n + len(payload) if total is None else total
    h = struct.pack(">BBHHHBBH4s4s", version << 4 | words, tos, length, ident, flags, ttl, proto, 0, src, dst) + options
    c = csum(h) if check is None else check
    return h[:10] + struct.pack(">H", c) + h[12:] + payload


def icmp(kind, code, rest, data, check=None):
    m = struct.pack(">BBH", kind, code, 0) + rest + data
    c = csum(m) if check is None else check
    return m[:2] + struct.pack(">H", c) + m[4:]


def echo(kind, ident, seq, data, code=0, check=None):
    return icmp(kind, code, struct.pack(">HH", ident, seq), data, check)


def frame(dst, src, datagram):
    return dst + src + b"\x08\x00" + datagram


def pad60(f):
    return f.ljust(60, b"\x00")


def be16(b, o):
    return b[o] << 8 | b[o + 1]


def is_broadcast(a):
    return a in (LIMITED_BCAST, SUBNET_BCAST)


def on_link(a):
    return bytes(x & m for x, m in zip(a, NETMASK)) == bytes(x & m for x, m in zip(PAX_IP, NETMASK))


def next_hop(dst):
    return dst if on_link(dst) else GW_IP


def source_ok(src):
    return (src != b"\x00" * 4 and src[0] != 127 and src[0] < 224 and not is_broadcast(src) and src != PAX_IP)


def options_verdict(o):
    i = 0
    while i < len(o):
        t = o[i]
        if t == 0:
            return None
        if t == 1:
            i += 1
            continue
        if i + 1 >= len(o):
            return "ip.option"
        n = o[i + 1]
        if n < 2 or i + n > len(o):
            return "ip.option"
        if t in (131, 137):
            return "ip.source-route"
        i += n
    return None


def judge_ip(f):
    """What PAX must do with the IPv4 frame `f` (which reached its
    station): (verdict, ihl, total)."""
    if len(f) < 34:
        return "ip.short", 0, 0
    h = f[14:]
    if h[0] >> 4 != 4:
        return "ip.version", 0, 0
    ihl = (h[0] & 15) * 4
    total = be16(h, 2)
    if ihl < 20:
        return "ip.ihl", ihl, total
    if len(f) < 14 + ihl:
        return "ip.short", ihl, total
    if csum(h[:ihl]) != 0:
        return "ip.checksum", ihl, total
    if total < ihl or 14 + total > len(f):
        return "ip.length", ihl, total
    if h[8] == 0:
        return "ip.ttl", ihl, total
    if be16(h, 6) & 0x3fff:
        return "ip.fragment", ihl, total
    if not source_ok(h[12:16]):
        return "ip.source", ihl, total
    v = options_verdict(h[20:ihl])
    if v:
        return v, ihl, total
    dst = h[16:20]
    if dst != PAX_IP and not is_broadcast(dst):
        return "ip.other", ihl, total
    if h[9] != 1:
        if f[0] & 1 or is_broadcast(dst):
            return "silent", ihl, total
        return "unreachable", ihl, total
    m = h[ihl:total]
    if len(m) < 8:
        return "icmp.short", ihl, total
    if csum(m) != 0:
        return "icmp.checksum", ihl, total
    if m[0] == 8 and m[1] == 0:
        return ("icmp.broadcast" if is_broadcast(dst) else "echo"), ihl, total
    if m[0] == 0 and m[1] == 0:
        return "reply", ihl, total
    return "icmp.type", ihl, total


def judge_arp(f):
    """What PAX must do with the ARP frame `f`: `bad`, `conflict`,
    `request` (for PAX: answer it), `reply` (to PAX), or `other` (for
    another address); and whether the sender may teach the cache."""
    if len(f) < 42 or f[14:20] != b"\x00\x01\x08\x00\x06\x04":
        return "bad", False
    op = be16(f, 20)
    sha, spa, tpa = f[22:28], f[28:32], f[38:42]
    if op not in (1, 2) or sha == ZERO6 or sha[0] & 1:
        return "bad", False
    if spa == PAX_IP:
        return "conflict", False
    teaches = spa != b"\x00" * 4 and spa != LIMITED_BCAST
    if tpa != PAX_IP:
        return "other", teaches
    return ("request" if op == 1 else "reply"), teaches


def echo_reply_to(f, ihl, total, ident, to_mac):
    """PAX's whole reply frame to the echo request in frame `f`."""
    h = f[14:]
    m = h[ihl:total]
    answer = icmp(0, 0, m[4:8], m[8:])
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, h[12:16], 1, answer, ident=ident)))


def unreachable_for(f, ihl, total, ident, to_mac):
    """PAX's whole protocol-unreachable frame for the datagram in `f`."""
    h = f[14:]
    quote = h[:ihl + min(8, total - ihl)]
    m = icmp(3, 2, b"\x00" * 4, quote)
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, h[12:16], 1, m, ident=ident)))


def echo_request_from_pax(dst_ip, seq, n, ident, to_mac):
    """The whole frame of PAX's echo request number `seq`, `n` data bytes."""
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, dst_ip, 1, echo(8, ECHO_IDENT, seq, pattern(n)), ident=ident)))


def pax_arp_request(target_ip):
    return pad60(arp(BCAST, PAX_MAC, 1, PAX_MAC, PAX_IP, ZERO6, target_ip))


def pax_arp_reply(to_mac, to_ip):
    return pad60(arp(to_mac, PAX_MAC, 2, PAX_MAC, PAX_IP, to_mac, to_ip))
