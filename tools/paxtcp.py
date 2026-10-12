# paxtcp.py — a TCP for the other end of PAX's cable (px23): what
# tools/net-peer --tcp speaks to kernel/tcp over a socket netdev, and to
# Linux over a tap device (tools/linux-net, the reference side).
#
# It is a test instrument, not a stack: one thread, no sockets, frames in
# and out through whoever owns the wire (a `Peer`). A `Stack` holds the
# connections between PAX and the addresses the script plays; a `Conn` is
# one of them: the handshake either way, cumulative acknowledgements, a
# go-back-N sender with a retransmission timer and a fast retransmit on
# the third duplicate ACK, a receiver that keeps what arrives out of
# order, FIN each way, a reset. It announces MSS 1460 and a window of
# 65,535 and sends no other option unless a test asks it to.
#
# **Faults** (`Faults`) are this tool's to inject, per connection, at
# stated rates. What happens to a frame is decided by what the frame is
# — which way it goes, where its bytes and its acknowledgement lie from
# the connection's first sequence numbers, and how many times that same
# frame has gone before — and the connection's seed, not by the order
# frames happen to come in: the same transfer meets the same faults in
# every run, so a run's time is the faults' and not the luck of the
# draw. `loss` (a frame
# either way is dropped: one PAX sent is not looked at, one this end
# would send is not sent), `dup` (a frame to PAX goes twice), `reorder`
# (a frame to PAX is held back until after the next), `corrupt` (a frame
# to PAX goes with one bit of its segment flipped, so its checksum is
# wrong and PAX must drop it); and scripted single faults: `drop_in` and
# `drop_out`, predicates that each lose the first frame they match.
#
# In **strict** mode (the other end is PAX) every TCP frame PAX sends is
# rebuilt from its fields — ports, numbers, flags, window, data, the
# next identification, the MSS option on a SYN and no option anywhere
# else — and held to its bytes, both checksums recomputed; what the
# segments mean in order (acknowledgements, windows, retransmissions) is
# tools/pcap-net's to judge from the capture. Not strict (Linux): what
# Linux puts in its headers and options is Linux's.
#
# Written from RFC 9293, RFC 1122 §4.2, RFC 6298 and RFC 5681. No
# network stack's source.
import random
import struct
import time

import paxnet as px

M32 = px.M32
SYN, FIN, RST, PSH, ACK, URG = px.SYN, px.FIN, px.RST, px.PSH, px.ACK, px.URG


def sadd(a, b):
    return (a + b) & M32


def ssub(a, b):
    return (a - b) & M32


class Faults:
    """What goes wrong on one connection, by rate and by script."""

    def __init__(self, seed=1, loss=0.0, dup=0.0, reorder=0.0, corrupt=0.0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.seen = {}       # what a frame is -> how many times it has gone
        self.loss, self.dup, self.reorder, self.corrupt = loss, dup, reorder, corrupt
        self.drop_in = []    # predicates on a Segment from PAX: the first match is lost
        self.drop_out = []   # predicates on (flags, seq, data) of a segment to PAX
        self.held = None     # a frame held back to go after the next
        self.held_at = 0.0
        self.n = {"lost-in": 0, "lost-out": 0, "duplicated": 0, "reordered": 0, "corrupted": 0, "in": 0, "out": 0}

    def roll(self, what):
        """A number in [0, 1) that is the same for the same frame (`what`
        says which) on its same time through, in every run."""
        k = self.seen.get(what, 0)
        self.seen[what] = k + 1
        return random.Random("%s/%r/%d" % (self.seed, what, k)).random()

    def lose_in(self, seg, what=None):
        self.n["in"] += 1
        for p in self.drop_in:
            if p(seg):
                self.drop_in.remove(p)
                self.n["lost-in"] += 1
                return True
        if self.loss and self.roll(("in",) + (what or ())) < self.loss:
            self.n["lost-in"] += 1
            return True
        return False

    def out(self, frame, flags, seq, data, send, what=None):
        self.n["out"] += 1
        for p in self.drop_out:
            if p(flags, seq, data):
                self.drop_out.remove(p)
                self.n["lost-out"] += 1
                return
        if not (self.loss or self.corrupt or self.reorder or self.dup):
            send(frame)
            return
        u = self.roll(("out",) + (what or ()))
        if u < self.loss:
            self.n["lost-out"] += 1
            return
        if u < self.loss + self.corrupt:
            b = bytearray(frame)
            at = 34 + int(u * 1e6) % (len(b) - 34)  # a byte of the segment
            b[at] ^= 1 << (int(u * 1e9) % 8)
            self.n["corrupted"] += 1
            send(bytes(b))
            return
        if self.held is None and u < self.loss + self.corrupt + self.reorder:
            self.held, self.held_at = frame, time.time()
            self.n["reordered"] += 1
            return
        send(frame)
        if self.held is not None:
            send(self.held)
            self.held = None
        if u >= 1.0 - self.dup:
            self.n["duplicated"] += 1
            send(frame)

    def flush(self, send, now):
        """A held frame does not wait for ever for a next one."""
        if self.held is not None and now - self.held_at > 0.03:
            send(self.held)
            self.held = None

    def any(self):
        return bool(self.loss or self.dup or self.reorder or self.corrupt or self.drop_in or self.drop_out)

    def text(self):
        n = self.n
        return "%d of %d frames from PAX and %d of %d to PAX dropped, %d duplicated, %d reordered, %d corrupted" % (
            n["lost-in"], n["in"], n["lost-out"], n["out"], n["duplicated"], n["reordered"], n["corrupted"])


class Conn:
    """One connection between an address this script plays (`ip`:`port`)
    and PAX's `pax_port`."""

    RTO = 0.25       # seconds; doubled on each timeout, to RTO_MAX
    RTO_MAX = 2.0
    TRIES = 14       # timeouts in a row before this end gives up

    def __init__(self, stack, ip, port, pax_port, faults=None, mss=px.MSS, window=65535, cwnd=10):
        self.stack, self.ip, self.port, self.pax_port = stack, ip, port, pax_port
        self.faults = faults if faults is not None else Faults()
        self.mss, self.window = mss, window
        self.state = "closed"
        self.iss = stack.rng.getrandbits(32)
        self.snd_una = self.snd_nxt = self.snd_max = self.iss
        self.out = bytearray()           # bytes not yet acknowledged, and not yet sent
        self.out_seq = sadd(self.iss, 1)  # the sequence number of out[0]
        self.fin_wanted = self.fin_sent = self.fin_acked = False
        self.irs = None
        self.rcv_nxt = 0
        self.inbox = bytearray()         # bytes received in order, not yet taken
        self.keep = True                 # False: count and discard what arrives
        self.received = 0                # bytes received in order, in all
        self.ooo = {}
        self.fin_in = None               # the sequence number of PAX's FIN, once seen
        self.eof = False                 # PAX's FIN came, in order
        self.reset = False               # PAX reset the connection
        self.gave_up = False
        self.peer_wnd = 0
        self.peer_mss = 536
        self.cwnd = cwnd * mss
        self.ssthresh = 1 << 30
        self.rto = self.RTO
        self.timer = None
        self.tries = 0
        self.dupacks = 0
        self.syn_options = None          # options for this end's SYN or SYN-ACK instead of MSS alone
        self.on_data = self.on_eof = self.on_open = None
        self.pax_max = None              # the end of the highest sequence number PAX has sent
        self.pax_rexmt = 0               # segments of PAX's that carried a sequence number seen before
        self.pax_segments = 0
        self.rexmt = 0                   # this end's retransmissions
        self.opened_at = self.first_at = self.last_at = None
        self.mute = False                # True: answer nothing more (a host that went away)
        self.crossed = False             # this end's SYN crossed PAX's (a simultaneous open)
        self.zero_windows = 0            # segments in which PAX advertised a window of zero
        self.probes = 0                  # bytes this end sent past a closed window

    # --- sending -------------------------------------------------------------
    def tx(self, flags, seq, data=b"", options=b"", window=None, ack=None, **kw):
        if self.mute:
            return
        p = self.stack.peer
        w = self.window if window is None else window
        a = (self.rcv_nxt if ack is None else ack) if flags & ACK else 0
        seg = px.tcp(self.port, self.pax_port, seq, a, flags, w, bytes(data), self.ip, px.PAX_IP, options=options, **kw)
        f = p.datagram(self.ip, seg, proto=6, ttl=64 if px.on_link(self.ip) else 63)
        # What this frame is, from the connection's own first numbers.
        what = (flags, ssub(seq, self.iss), len(data), ssub(a, self.irs) if flags & ACK and self.irs is not None else 0)
        self.faults.out(px.pad60(f), flags, seq, data, self.stack.wire_send, what)
        self.stack.n["out"] += 1

    def ack_now(self):
        self.tx(ACK, self.snd_max)

    def open(self):
        """An active open: this end's SYN."""
        self.state = "syn-sent"
        self.snd_nxt = self.snd_max = sadd(self.iss, 1)
        self.tx(SYN, self.iss, options=self.syn_options if self.syn_options is not None else px.mss_option(self.mss))
        self.timer = time.time() + self.rto

    def send(self, data):
        self.out += data
        self.output()

    def close(self):
        """No more bytes from this end: a FIN after what is queued."""
        if not self.fin_wanted:
            self.fin_wanted = True
            if self.state == "established":
                self.state = "fin-wait-1"
            elif self.state == "close-wait":
                self.state = "last-ack"
            self.output()

    def abort(self):
        self.tx(RST | ACK, self.snd_max)
        self.done("aborted")

    def take(self, n=None):
        n = len(self.inbox) if n is None else min(n, len(self.inbox))
        d = bytes(self.inbox[:n])
        del self.inbox[:n]
        return d

    def sending(self):
        return self.state in ("established", "close-wait", "fin-wait-1", "last-ack", "closing")

    def output(self, force=False):
        if not self.sending():
            return
        now = time.time()
        while True:
            off = ssub(self.snd_nxt, self.out_seq)
            unsent = len(self.out) - off if off <= len(self.out) else 0
            flight = ssub(self.snd_nxt, self.snd_una)
            room = max(0, min(self.cwnd, self.peer_wnd) - flight)
            n = min(unsent, room, self.peer_mss)
            probe = False
            if n == 0 and unsent and flight == 0 and force:
                n, probe = 1, True
            fin = self.fin_wanted and off <= len(self.out) and n == unsent and not probe
            if n == 0 and not fin:
                break
            flags = ACK | (PSH if n and n == unsent else 0) | (FIN if fin else 0)
            if px.seq_lt(self.snd_nxt, self.snd_max):
                self.rexmt += 1
            self.tx(flags, self.snd_nxt, self.out[off:off + n])
            if probe:
                self.probes += 1
                break
            self.snd_nxt = sadd(self.snd_nxt, n + (1 if fin else 0))
            if fin:
                self.fin_sent = True
            if px.seq_lt(self.snd_max, self.snd_nxt):
                self.snd_max = self.snd_nxt
            if self.timer is None:
                self.timer = now + self.rto
            if fin:
                break
        if self.timer is None and ssub(self.snd_nxt, self.out_seq) < len(self.out):
            self.timer = now + self.rto  # a closed window: the timer probes it

    def fin_seq(self):
        return sadd(self.out_seq, len(self.out))

    def done(self, why=None):
        self.state = "done"
        self.timer = None
        self.stack.active.discard(self)
        self.last_at = time.time()

    # --- the timer -----------------------------------------------------------
    def on_timer(self, now):
        self.timer = None
        if self.state == "done" or self.mute:
            return
        self.tries += 1
        if self.tries > self.TRIES:
            self.gave_up = True
            self.done("gave up")
            return
        self.rto = min(self.rto * 2, self.RTO_MAX)
        if self.state == "syn-sent":
            self.rexmt += 1
            self.tx(SYN, self.iss, options=self.syn_options if self.syn_options is not None else px.mss_option(self.mss))
            self.timer = now + self.rto
            return
        if self.state == "syn-received":
            self.rexmt += 1
            self.tx(SYN | ACK, self.iss, options=self.syn_options if self.syn_options is not None else px.mss_option(self.mss))
            self.timer = now + self.rto
            return
        if self.snd_una == self.snd_max and ssub(self.snd_nxt, self.out_seq) >= len(self.out) and not (self.fin_wanted and not self.fin_sent):
            return
        # Back to the first unacknowledged byte, one segment's window.
        self.ssthresh = max(ssub(self.snd_max, self.snd_una) // 2, 2 * self.mss)
        self.cwnd = self.mss
        self.dupacks = 0
        self.snd_nxt = self.snd_una
        self.output(force=True)
        if self.timer is None:
            self.timer = now + self.rto

    # --- receiving -----------------------------------------------------------
    def on_segment(self, seg):
        now = time.time()
        self.pax_segments += 1
        if seg.space:
            if self.pax_max is not None and px.seq_lt(seg.seq, self.pax_max):
                self.pax_rexmt += 1
            end = sadd(seg.seq, seg.space)
            if self.pax_max is None or px.seq_lt(self.pax_max, end):
                self.pax_max = end
        what = (seg.flags, ssub(seg.seq, self.irs) if self.irs is not None else 0, len(seg.data), ssub(seg.ack, self.iss) if seg.flags & ACK else 0)
        if self.mute or self.faults.lose_in(seg, what):
            return
        if seg.flags & RST:
            self.reset = True
            self.done("reset")
            if self.on_eof:
                self.on_eof(self)
            return
        if self.state == "done":
            # A retransmitted FIN or byte after everything was said: the
            # acknowledgement again.
            if seg.space:
                self.tx(ACK, self.snd_max)
            return
        if self.state == "syn-sent":
            if seg.flags & SYN and seg.flags & ACK and seg.ack == sadd(self.iss, 1):
                self.irs, self.rcv_nxt = seg.seq, sadd(seg.seq, 1)
                self.snd_una = seg.ack
                self.peer_wnd, self.peer_mss = seg.window, min(seg.mss() or 536, self.mss)
                self.established(now)
                self.tx(ACK, self.snd_nxt)
            elif seg.flags & SYN and not seg.flags & ACK:
                # The SYNs crossed.
                self.irs, self.rcv_nxt = seg.seq, sadd(seg.seq, 1)
                self.peer_wnd, self.peer_mss = seg.window, min(seg.mss() or 536, self.mss)
                self.state = "syn-received"
                self.tx(SYN | ACK, self.iss, options=px.mss_option(self.mss))
                self.timer = now + self.rto
            return
        if self.state == "syn-received":
            if seg.flags & SYN and not seg.flags & ACK:
                self.tx(SYN | ACK, self.iss, options=self.syn_options if self.syn_options is not None else px.mss_option(self.mss))
                return
            if seg.flags & SYN and seg.flags & ACK and self.crossed and seg.ack == sadd(self.iss, 1):
                # PAX's answer to the crossed SYN: its SYN again, with an
                # acknowledgement of this end's.
                self.snd_una = seg.ack
                self.peer_wnd = seg.window
                self.established(now)
                self.tx(ACK, self.snd_nxt)
                return
            if not (seg.flags & ACK and seg.ack == sadd(self.iss, 1)):
                return
            self.snd_una = seg.ack
            self.peer_wnd = seg.window
            self.established(now)
        if seg.flags & SYN:
            return
        # The acknowledgement.
        if seg.flags & ACK and seg.window == 0:
            self.zero_windows += 1
        if seg.flags & ACK:
            if px.seq_lt(self.snd_una, seg.ack) and px.seq_leq(seg.ack, self.snd_max):
                if px.seq_lt(self.out_seq, seg.ack):
                    gone = min(ssub(seg.ack, self.out_seq), len(self.out))
                    del self.out[:gone]
                    self.out_seq = sadd(self.out_seq, gone)
                self.snd_una = seg.ack
                if px.seq_lt(self.snd_nxt, seg.ack):
                    self.snd_nxt = seg.ack
                self.tries, self.rto, self.dupacks = 0, self.RTO, 0
                self.cwnd = min(self.cwnd + (self.mss if self.cwnd < self.ssthresh else max(1, self.mss * self.mss // self.cwnd)), 48 * self.mss)
                self.timer = None if self.snd_una == self.snd_max else now + self.rto
                self.peer_wnd = seg.window
                if self.fin_sent and seg.ack == sadd(self.fin_seq(), 1):
                    self.fin_acked = True
                    if self.state == "fin-wait-1":
                        self.state = "fin-wait-2"
                    elif self.state in ("last-ack", "closing"):
                        self.done()
            elif seg.ack == self.snd_una:
                self.peer_wnd = seg.window
                if not seg.space and self.snd_una != self.snd_max:
                    self.dupacks += 1
                    if self.dupacks == 3:
                        self.ssthresh = max(ssub(self.snd_max, self.snd_una) // 2, 2 * self.mss)
                        self.cwnd = self.ssthresh
                        # RFC 5681 §3.2: the segment that was lost goes
                        # again — never a byte past SND.MAX, which PAX's
                        # ACK of it would then answer beyond what this
                        # end counts as sent (pax#29, run 38192937184).
                        off = ssub(self.snd_una, self.out_seq)
                        n = min(len(self.out) - off, self.peer_mss, ssub(self.snd_max, self.snd_una)) if off < len(self.out) else 0
                        fin = self.fin_sent and off + n == len(self.out)
                        if n or fin:
                            self.rexmt += 1
                            self.tx(ACK | (FIN if fin else 0), self.snd_una, self.out[off:off + n])
        # A closed window takes nothing (a probe is acknowledged, not kept).
        if self.window == 0 and (seg.data or seg.flags & FIN):
            self.tx(ACK, self.snd_max)
            return
        # The data and the FIN.
        if seg.data or seg.flags & FIN:
            s, d = seg.seq, seg.data
            if seg.flags & FIN:
                self.fin_in = sadd(seg.seq, len(seg.data))
            if px.seq_lt(s, self.rcv_nxt):
                cut = ssub(self.rcv_nxt, s)
                d = d[cut:] if cut < len(d) else b""
                s = self.rcv_nxt
            fresh = False
            if d and s == self.rcv_nxt:
                self.take_in(d)
                fresh = True
                while self.rcv_nxt in self.ooo:
                    self.take_in(self.ooo.pop(self.rcv_nxt))
            elif d and ssub(s, self.rcv_nxt) < (1 << 20):
                self.ooo.setdefault(s, d)
            if self.fin_in is not None and self.fin_in == self.rcv_nxt and not self.eof:
                self.rcv_nxt = sadd(self.rcv_nxt, 1)
                self.eof = True
                if self.state == "established":
                    self.state = "close-wait"
                elif self.state == "fin-wait-1":
                    self.state = "closing"
                elif self.state == "fin-wait-2":
                    self.tx(ACK, self.snd_max)
                    self.done()
                    if self.on_eof:
                        self.on_eof(self)
                    return
            self.tx(ACK, self.snd_max)
            if fresh and self.on_data:
                self.on_data(self)
            if self.eof and self.on_eof:
                cb, self.on_eof = self.on_eof, None
                cb(self)
        if self.state != "done":
            self.output()

    def take_in(self, d):
        if self.first_at is None:
            self.first_at = time.time()
        self.last_at = time.time()
        self.received += len(d)
        if self.keep:
            self.inbox += d
        self.rcv_nxt = sadd(self.rcv_nxt, len(d))

    def established(self, now):
        self.state = "established"
        self.timer = None
        self.tries, self.rto = 0, self.RTO
        self.opened_at = now
        if self.on_open:
            self.on_open(self)

    def closed(self):
        """Both directions are over, cleanly or not."""
        return self.state == "done"


class Listener:
    """A port this script listens on: `accept(conn)` is called for each
    new connection's Conn before its SYN-ACK goes (to set its callbacks
    and faults)."""

    def __init__(self, accept):
        self.accept = accept


class Stack:
    """Every TCP connection between PAX and the addresses a Peer plays,
    and everything else that comes off the wire while they run."""

    def __init__(self, peer, seed=20231011):
        self.peer = peer
        self.rng = random.Random(seed)
        self.conns = {}       # (pax port, this end's address, this end's port) -> Conn
        self.active = set()   # those with something still to do
        self.listeners = {}   # port -> Listener
        self.silent = set()   # ports whose segments are never answered
        self.held = {}        # port -> the last SYN a silent port left unanswered
        self.unreachable = {}  # port -> the code of the ICMP destination unreachable its SYNs draw
        self.resets = []      # resets from PAX for no connection of this script's
        self.udp = []         # (source port, destination address, destination port, data) of each datagram from PAX
        self.icmp = []        # ICMP frames from PAX
        self.strays = []      # Segments for no connection (answered with a reset)
        self.n = {"in": 0, "out": 0, "resets-out": 0, "resets-in": 0, "strays": 0}
        self.made = 0

    def wire_send(self, f):
        self.peer.wire.send(f)

    # --- the wire ------------------------------------------------------------
    def frame(self, f):
        p = self.peer
        if f[6:12] != px.PAX_MAC:
            if p.strict:
                p.fail("a frame that is not from PAX's address", f)
            return
        kind = f[12:14]
        if kind == b"\x08\x06":
            p.arp_from_pax(f)
            p.started = True
            return
        if kind != b"\x08\x00" or len(f) < 34 or f[26:30] != px.PAX_IP:
            if not p.strict:
                return
            if not p.started and kind not in (b"\x08\x00", px.EXPERIMENTAL):
                p.before += 1  # the firmware's, before the kernel
                return
            p.fail("a frame from PAX that is neither ARP nor an IPv4 datagram of its own", f)
        p.started = True
        proto = f[23]
        if proto == 17:
            self.udp.append(p.udp_parse(f, "a datagram while TCP runs"))
        elif proto == 6:
            self.segment(f)
        elif proto == 1:
            if p.strict:
                p.note_ident(f)
            self.icmp.append(f)
        elif p.strict:
            p.fail("a datagram of protocol %d from PAX" % proto, f)

    def segment(self, f):
        p = self.peer
        ihl, total = (f[14] & 15) * 4, px.be16(f, 16)
        h = f[14:14 + total]
        t = h[ihl:]
        if px.csum(h[:ihl]) != 0 or len(t) < 20 or px.tcp_sum(h[12:16], h[16:20], t) != 0 or (t[12] >> 4) * 4 < 20 or (t[12] >> 4) * 4 > len(t):
            if p.strict:
                p.fail("a TCP segment from PAX with a wrong checksum or header length", f)
            return
        seg = px.Segment(f)
        self.n["in"] += 1
        if p.strict:
            hop = px.next_hop(seg.dst)
            if hop not in p.macs:
                p.fail("a segment for %s, which this script does not play" % px.dotted(seg.dst), f)
            # Rebuilt with the identification it carries: a frame of PAX's
            # that this host dropped between QEMU's socket and this
            # script's (a full receive buffer on a busy host) is a loss
            # like any other to TCP, and a gap in the numbers here;
            # `note_ident` holds them to going forward and counts the
            # gaps, and tools/pcap-net holds the capture, which loses
            # nothing, to no gap at all.
            want = px.tcp_from_pax(seg.dst, seg.sport, seg.dport, seg.seq, seg.ack, seg.flags, seg.window, seg.data, seg.ident, p.macs[hop])
            if f != want:
                p.fail("not a TCP segment as PAX builds one (%s, identification %d): 20-byte headers, DF, time to live 64, "
                       "the MSS option on a SYN alone, byte for byte" % (seg, seg.ident), f, want)
            p.note_ident(f)
        if seg.flags & RST:
            self.n["resets-in"] += 1
        key = (seg.sport, seg.dst, seg.dport)
        c = self.conns.get(key)
        if c is not None and c.state == "done" and seg.flags & SYN and not seg.flags & ACK:
            c = None  # the four values again: a new connection
        if c is not None:
            c.on_segment(seg)
            return
        if seg.dport in self.unreachable:
            # No TCP answers: an ICMP error that quotes the segment's
            # header and its first 8 bytes (RFC 792).
            if seg.flags & SYN:
                quote = f[14:14 + 20 + 8]
                m = px.icmp(3, self.unreachable[seg.dport], b"\x00" * 4, quote)
                self.peer.send(self.peer.datagram(seg.dst, m, proto=1))
                self.n["icmp-out"] = self.n.get("icmp-out", 0) + 1
            return
        if seg.dport in self.silent:
            if seg.flags & SYN and not seg.flags & (ACK | RST):
                self.held[seg.dport] = (seg, key)
            return
        l = self.listeners.get(seg.dport)
        if l is not None and seg.flags & SYN and not seg.flags & (ACK | RST):
            self.syn_in(seg, key, l)
            return
        if seg.flags & RST:
            self.resets.append(seg)
            del self.resets[:-64]
            return
        # Nobody: a reset (RFC 9293 §3.10.7.1).
        self.n["strays"] += 1
        self.strays.append(seg)
        del self.strays[:-16]
        self.reset_for(seg)

    def syn_in(self, seg, key, l):
        """PAX's SYN for a port this script listens on: a new Conn, its
        SYN-ACK."""
        c = Conn(self, seg.dst, seg.dport, seg.sport)
        self.conns[key] = c
        self.active.add(c)
        self.made += 1
        l.accept(c)
        c.pax_segments, c.pax_max = 1, sadd(seg.seq, seg.space)
        if c.faults.lose_in(seg, (seg.flags, 0, 0, 0)):
            # Lost on the way: there was no SYN, and there is no connection.
            del self.conns[key]
            self.active.discard(c)
            c.state = "lost"
            return
        c.irs, c.rcv_nxt = seg.seq, sadd(seg.seq, 1)
        c.peer_wnd, c.peer_mss = seg.window, min(seg.mss() or 536, c.mss)
        c.snd_nxt = c.snd_max = sadd(c.iss, 1)
        c.state = "syn-received"
        if c.crossed:
            # Not an answer: a SYN of this end's own, as if the two crossed.
            c.tx(SYN, c.iss, options=px.mss_option(c.mss))
        else:
            c.tx(SYN | ACK, c.iss, options=c.syn_options if c.syn_options is not None else px.mss_option(c.mss))
        c.timer = time.time() + c.rto

    def open_gate(self, port, accept):
        """A port that was silent listens from now on, and the SYN it
        left unanswered is answered."""
        self.silent.discard(port)
        self.listeners[port] = Listener(accept)
        if port in self.held:
            seg, key = self.held.pop(port)
            self.syn_in(seg, key, self.listeners[port])

    def reset_for(self, seg):
        if seg.flags & ACK:
            s = px.tcp(seg.dport, seg.sport, seg.ack, 0, RST, 0, b"", seg.dst, px.PAX_IP)
        else:
            s = px.tcp(seg.dport, seg.sport, 0, sadd(seg.seq, seg.space), RST | ACK, 0, b"", seg.dst, px.PAX_IP)
        self.peer.send(self.peer.datagram(seg.dst, s, proto=6, ttl=64 if px.on_link(seg.dst) else 63))
        self.n["resets-out"] += 1
        self.n["out"] += 1

    def raw(self, src_ip, segment, **kw):
        """Send PAX one datagram of protocol 6 with `segment` as it is
        (a segment no connection here made). Returns the frame."""
        f = self.peer.datagram(src_ip, segment, proto=6, **kw)
        self.peer.send(f)
        return f

    # --- time ----------------------------------------------------------------
    def tick(self):
        now = time.time()
        for c in list(self.active):
            if c.timer is not None and now >= c.timer:
                c.on_timer(now)
            c.faults.flush(self.wire_send, now)

    def step(self, timeout):
        """At most one frame off the wire, then the timers."""
        now = time.time()
        wait = timeout
        for c in self.active:
            if c.timer is not None:
                wait = min(wait, c.timer - now)
            if c.faults.held is not None:
                wait = min(wait, 0.03)
        f = self.peer.recv(max(wait, 0.0005))
        if f is not None:
            self.frame(f)
        self.tick()

    def until(self, pred, timeout, what):
        """Run until `pred()`; fail with `what` when it has not come
        true in `timeout` seconds."""
        end = time.time() + timeout
        while not pred():
            left = end - time.time()
            if left <= 0:
                self.peer.fail("%s: not in %.0f s" % (what, timeout))
            self.step(min(left, 0.05))

    def idle(self, seconds):
        """Run for `seconds`, answering whatever comes."""
        end = time.time() + seconds
        while time.time() < end:
            self.step(min(end - time.time(), 0.05))

    # --- for scripts -----------------------------------------------------------
    def listen(self, port, accept):
        self.listeners[port] = Listener(accept)

    def connect(self, ip, port, pax_port, faults=None, timeout=30.0, what=None, **kw):
        """An active open from `ip`:`port` to PAX's `pax_port`, waited
        for: the established Conn."""
        c = Conn(self, ip, port, pax_port, faults=faults, **kw)
        self.conns[(pax_port, ip, port)] = c
        self.active.add(c)
        self.made += 1
        return c

    def established(self, c, what, timeout=30.0):
        """Open `c` and wait for its handshake."""
        c.open()
        self.until(lambda: c.state != "syn-sent" and c.state != "syn-received", timeout, what + ": the handshake")
        if c.state == "done":
            self.peer.fail("%s: %s during the handshake" % (what, "reset" if c.reset else "given up"))
        return c

    def udp_from(self, timeout, what, accept=lambda d: True):
        """The next datagram from PAX that `accept` takes."""
        got = []

        def have():
            while self.udp:
                d = self.udp.pop(0)
                if accept(d):
                    got.append(d)
                    return True
            return False

        self.until(have, timeout, what)
        return got[0]

    def forget(self, age=1.0):
        """Drop the connections that have been over for `age` seconds
        (a script that makes thousands need not keep them; one just
        over may still be owed a retransmitted FIN's answer)."""
        now = time.time()
        for k in [k for k, c in self.conns.items() if c.state == "done" and c.last_at is not None and now - c.last_at > age]:
            del self.conns[k]
