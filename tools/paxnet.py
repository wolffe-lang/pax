# paxnet.py — what the network tools share (px21, px22, px23): the Internet checksum,
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
# px22 adds UDP: `judge_ip` names a UDP datagram's drop cause
# (`udp.short`, `udp.length`, `udp.checksum`, `udp.port-zero`) or calls
# it `udp` — a datagram a socket may take; whether one does is the
# sockets' state, which the model does not hold and the tools give or
# infer. And what the UDP witnesses (user/net/) and the scripts that
# play their other end agree on: the ports, the echo battery, the
# client's datagrams, the soak's, the DNS answer.
#
# px23 adds TCP: the segment's builder and parser, and — when the
# kernel under test speaks it (`TCP_SPOKEN`, which the TCP tools set;
# kernel/kmain_net does not start kernel/tcp, and a datagram of
# protocol 6 is to it one of an unknown protocol) — `judge_ip` names a
# segment's drop cause (`tcp.short`, `tcp.header`, `tcp.checksum`,
# `tcp.broadcast`, `tcp.port-zero`, `tcp.option`) or calls it `tcp`: a
# segment for a connection, a listener or nobody, which is the
# connections' state and tools/paxtcp.py's and tools/pcap-net's to say.
# And the stream the TCP witnesses carry (user/net/say.h's pattern).
#
# Written from RFC 768, RFC 791, RFC 792, RFC 826, RFC 862, RFC 894,
# RFC 1035, RFC 1071, RFC 1122 §3.2, §4.1 and §4.2 and RFC 9293 §3.1.
# No network stack's source.
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
DNS_IP = bytes([10, 0, 2, 3])
DNS_MAC = bytes.fromhex("52550a000203")
LOOPBACK = bytes([127, 0, 0, 1])
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
    if h[9] == 17:
        return judge_udp(h, ihl, total), ihl, total
    if h[9] == 6 and TCP_SPOKEN:
        return judge_tcp(f, h, ihl, total), ihl, total
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
    if m[0] == 3 and len(m) >= 36 and m[8] == 0x45:
        # px23: a destination unreachable that quotes a whole header and
        # 8 bytes: counted `errors received`, and its protocol's to use.
        return "icmp.error", ihl, total
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


# --- UDP (px22) ----------------------------------------------------------------

ECHO_PORT = 7          # RFC 862: user/net/udpecho's
SERVICE_PORT = 9099    # where udpecho says "ready", and the reversing server
EXTRA_PORT = 9098      # where a second udpecho says "ready" for the wider battery
HOLD_PORT = 4030       # user/net/udphold's
HOLD_READY = 9097      # where udphold says "ready"
HOLD_BURST = 60        # datagrams of DATA_MAX bytes it is then sent
ASKER_PORT = 40000     # the port the echo battery comes from
DISCARD_PORT = 9       # a port no witness binds
DNS_PORT = 53
EPHEMERAL = range(32768, 61000)  # ip(7)'s default local range, PAX's too
DATA_MAX = 1472
DNS_NAME = "pax.test"
DNS_ANSWER = bytes([192, 0, 2, 53])
DNS_TTL = 60


def udp_sum(src, dst, segment):
    """The UDP checksum of `segment` (its checksum field zero, or its
    own for a check: the result is then 0) from `src` to `dst`."""
    return csum(src + dst + struct.pack(">BBH", 0, 17, len(segment)) + segment)


def udp(sport, dport, data, src, dst, check=None, length=None):
    """A UDP datagram (an IPv4 payload). `check` and `length` override
    what would be right, for the malformed ones; `check=0` is "the
    sender made none"."""
    n = 8 + len(data) if length is None else length
    seg = struct.pack(">HHHH", sport, dport, n, 0) + data
    if check is None:
        check = udp_sum(src, dst, seg[:n] if n <= len(seg) else seg) or 0xffff
    return seg[:6] + struct.pack(">H", check) + seg[8:]


def judge_udp(h, ihl, total):
    """What PAX must do with the UDP datagram of the IPv4 datagram `h`
    (header `ihl` bytes, total length `total`), which passed the IP
    rules: a drop cause, or `udp` (for a socket, if one takes it)."""
    u = h[ihl:total]
    if len(u) < 8:
        return "udp.short"
    n = be16(u, 4)
    if n < 8 or n > len(u):
        return "udp.length"
    if be16(u, 6) != 0 and udp_sum(h[12:16], h[16:20], u[:n]) != 0:
        return "udp.checksum"
    if be16(u, 2) == 0:
        return "udp.port-zero"
    return "udp"


def udp_fields(f):
    """(source port, destination port, data, whether a checksum was made)
    of the valid UDP frame `f`."""
    ihl = (f[14] & 15) * 4
    u = f[14 + ihl:14 + be16(f, 16)]
    return be16(u, 0), be16(u, 2), u[8:be16(u, 4)], be16(u, 6) != 0


def udp_from_pax(dst_ip, sport, dport, data, ident, to_mac):
    """The whole frame of a UDP datagram PAX sends: 20-byte header, DF,
    time to live 64, a checksum made."""
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, dst_ip, 17, udp(sport, dport, data, PAX_IP, dst_ip), ident=ident)))


def port_unreachable_for(f, ihl, total, ident, to_mac):
    """PAX's whole port-unreachable frame (type 3, code 3) for the
    datagram in `f`."""
    h = f[14:]
    quote = h[:ihl + min(8, total - ihl)]
    m = icmp(3, 3, b"\x00" * 4, quote)
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, h[12:16], 1, m, ident=ident)))


def sum_zero(sport, dport, text, src, dst):
    """`text` (an even number of bytes) and two more bytes that make the
    UDP checksum of the datagram come out zero, which RFC 768 has sent
    as 0xffff."""
    assert len(text) % 2 == 0
    seg = struct.pack(">HHHH", sport, dport, 8 + len(text) + 2, 0) + text + b"\x00\x00"
    data = text + struct.pack(">H", udp_sum(src, dst, seg))
    assert udp(sport, dport, data, src, dst)[6:8] == b"\xff\xff"
    return data


def hold_datagram(i):
    """Datagram `i` of the burst udphold sleeps through."""
    return bytes([i]) + bytes((i * 3 + k) & 0xff for k in range(1, DATA_MAX))


def echo_battery():
    """What every script sends udpecho first: 1, 2, 64, 512 and 1472
    bytes."""
    return [b"a", b"bc"] + [bytes((k * 11 + n) & 0xff for k in range(n)) for n in (64, 512, DATA_MAX)]


def soak_datagram(i):
    """Datagram `i` of the soak into PAX: 56 bytes, the first four `i`."""
    return struct.pack(">I", i) + bytes((i * 7 + k * 13) & 0xff for k in range(52))


def soak_request(i):
    """Datagram `i` of user/net/udpsoak: 64 bytes, the first four `i`."""
    return struct.pack(">I", i) + bytes((i * 7 + k * 13) & 0xff for k in range(4, 64))


def client_script():
    """user/net/udpclient's datagrams, in order: four on its connected
    socket, one on a socket with no peer."""
    return [b"hello from PAX", b"x", b"the third datagram, on a connected socket",
            bytes(ord("a") + i % 23 for i in range(DATA_MAX)), b"sendto, no connect"]


def dns_question(q):
    """The (name, type, class) of the one question of the DNS query `q`
    (RFC 1035 §4.1), or None when it is not a query with one question."""
    if len(q) < 17 or q[2] & 0x80 or be16(q, 4) != 1 or be16(q, 6) or be16(q, 8) or be16(q, 10):
        return None
    o, labels = 12, []
    while o < len(q) and q[o]:
        n = q[o]
        if n > 63 or o + 1 + n > len(q):
            return None
        labels.append(q[o + 1:o + 1 + n].decode("ascii", "replace"))
        o += 1 + n
    if o + 5 != len(q):
        return None
    return ".".join(labels), be16(q, o + 1), be16(q, o + 3)


def dns_answer(q):
    """The DNS server's answer to query `q`: one A record for DNS_NAME
    (the name a pointer to the question's), NXDOMAIN for any other."""
    name, qtype, qclass = dns_question(q)
    if name == DNS_NAME and qtype == 1 and qclass == 1:
        rr = b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, DNS_TTL, 4) + DNS_ANSWER
        return q[:2] + struct.pack(">HHHHH", 0x8180, 1, 1, 0, 0) + q[12:] + rr
    return q[:2] + struct.pack(">HHHHH", 0x8183, 1, 0, 0, 0) + q[12:]


# --- TCP (px23) ----------------------------------------------------------------

TCP_SPOKEN = False     # set by the tools whose kernel starts kernel/tcp
FIN, SYN, RST, PSH, ACK, URG = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
MSS = 1460             # what PAX announces: the MTU less the two headers
M32 = 0xffffffff


def flag_names(flags):
    return "".join(n for b, n in ((SYN, "S"), (FIN, "F"), (RST, "R"), (PSH, "P"), (ACK, "."), (URG, "U")) if flags & b) or "-"


def tcp_sum(src, dst, segment):
    """The TCP checksum of `segment` (its checksum field zero, or its
    own for a check: the result is then 0) from `src` to `dst`."""
    return csum(src + dst + struct.pack(">BBH", 0, 6, len(segment)) + segment)


def mss_option(mss=MSS):
    return struct.pack(">BBH", 2, 4, mss)


def tcp(sport, dport, seq, ack, flags, window, data, src, dst, options=b"", check=None, doff=None, urgent=0):
    """A TCP segment (an IPv4 payload). `options` is padded to a
    multiple of four with zeros; `check` and `doff` override what would
    be right, for the malformed ones."""
    options = options + b"\x00" * (-len(options) % 4)
    words = (20 + len(options)) // 4 if doff is None else doff
    seg = struct.pack(">HHIIBBHHH", sport, dport, seq & M32, ack & M32, words << 4, flags, window, 0, urgent) + options + data
    c = tcp_sum(src, dst, seg) if check is None else check
    return seg[:16] + struct.pack(">H", c) + seg[18:]


def tcp_options(o):
    """The options in the bytes `o`: a list of (kind, value bytes), or
    None when they do not parse (a length under 2, or past the end; an
    MSS option that is not 4 bytes)."""
    out, i = [], 0
    while i < len(o):
        k = o[i]
        if k == 0:
            break
        if k == 1:
            i += 1
            continue
        if i + 1 >= len(o):
            return None
        n = o[i + 1]
        if n < 2 or i + n > len(o) or (k == 2 and n != 4):
            return None
        out.append((k, o[i + 2:i + n]))
        i += n
    return out


def judge_tcp(f, h, ihl, total):
    """What PAX must do with the TCP segment of the IPv4 datagram `h`
    in frame `f`, which passed the IP rules: a drop cause, or `tcp`."""
    t = h[ihl:total]
    if len(t) < 20:
        return "tcp.short"
    doff = (t[12] >> 4) * 4
    if doff < 20 or doff > len(t):
        return "tcp.header"
    if tcp_sum(h[12:16], h[16:20], t) != 0:
        return "tcp.checksum"
    if is_broadcast(h[16:20]) or f[0] & 1:
        return "tcp.broadcast"
    if be16(t, 0) == 0 or be16(t, 2) == 0:
        return "tcp.port-zero"
    if tcp_options(t[20:doff]) is None:
        return "tcp.option"
    return "tcp"


class Segment:
    """The fields of the valid TCP frame `f`."""

    def __init__(self, f):
        ihl = (f[14] & 15) * 4
        total = be16(f, 16)
        t = f[14 + ihl:14 + total]
        self.src, self.dst = f[26:30], f[30:34]
        self.sport, self.dport = be16(t, 0), be16(t, 2)
        self.seq, self.ack = struct.unpack(">II", t[4:12])
        self.doff = (t[12] >> 4) * 4
        self.flags = t[13]
        self.window = be16(t, 14)
        self.urgent = be16(t, 18)
        self.raw_options = t[20:self.doff]
        self.options = tcp_options(self.raw_options) or []
        self.data = t[self.doff:]
        self.ident = be16(f, 18)
        # What it takes of the sequence space.
        self.space = len(self.data) + (1 if self.flags & SYN else 0) + (1 if self.flags & FIN else 0)

    def mss(self):
        for k, v in self.options:
            if k == 2:
                return be16(v, 0)
        return None

    def __str__(self):
        return "%s:%d > %s:%d [%s] seq %d ack %d win %d len %d" % (
            dotted(self.src), self.sport, dotted(self.dst), self.dport, flag_names(self.flags), self.seq, self.ack, self.window, len(self.data))


def tcp_from_pax(dst_ip, sport, dport, seq, ack, flags, window, data, ident, to_mac):
    """The whole frame of a TCP segment PAX sends: 20-byte IP header,
    DF, time to live 64; a SYN carries the MSS option and nothing else
    carries any."""
    opts = mss_option() if flags & SYN else b""
    return pad60(frame(to_mac, PAX_MAC, ipv4(PAX_IP, dst_ip, 6, tcp(sport, dport, seq, ack, flags, window, data, PAX_IP, dst_ip, options=opts), ident=ident)))


def seq_lt(a, b):
    """Whether sequence number `a` comes before `b` (modulo 2^32)."""
    return a != b and ((b - a) & M32) < 0x80000000


def seq_leq(a, b):
    return ((b - a) & M32) < 0x80000000


def stream_pattern(off, n):
    """`n` bytes of the stream the bulk transfers carry, from offset
    `off` (user/net/say.h's pattern_fill): 1024-byte records, record r
    its number in 8 bytes, least significant first, then byte j = r * 31
    + j * 7 (mod 256)."""
    out = bytearray()
    while n > 0:
        r, j = off >> 10, off & 1023
        rec = bytearray((r * 31 + k * 7) & 0xff for k in range(1024))
        rec[0:8] = struct.pack("<Q", r)
        take = min(n, 1024 - j)
        out += rec[j:j + take]
        off += take
        n -= take
    return bytes(out)


# The ports the TCP witnesses and the scripts that play their other end
# agree on (user/mpx4-tcp.run).
TCP_ECHO = 7             # user/net/tcpecho's
TCP_SERVICE = 9099       # the peer's echo server; where tcpecho says "ready" (UDP)
TCP_READY_FORK = 9098    # where the forking tcpecho says "ready"
TCP_READY_FAULTS = 9096  # where the tcpecho of the fault battery says "ready"
TCP_BULK = 9100          # the peer's bulk receiver
TCP_BULK_IN = 7100       # user/net/tcpbulk recv's
TCP_READY_BULK = 9097    # where it says "ready"
TCP_CLOSED = 9           # a port nobody listens on
TCP_SILENT = 9001        # a port whose SYNs go unanswered
TCP_RESET = 9301         # a server that resets after the first bytes
TCP_MUTE = 9302          # a server that says nothing after the handshake
TCP_UNREACHABLE = 9003   # a port whose SYN draws an ICMP port unreachable (code 3)
TCP_NO_HOST = 9004       # one whose SYN draws an ICMP host unreachable (code 1)
TCP_WOLF = 7070          # user/net/tcpwolfd's
TCP_WOLF_READY = 9070    # where it says "ready" (a connection, one line)
TCP_WOLF_GATE = 9071     # answered only once its request waits in its queue
