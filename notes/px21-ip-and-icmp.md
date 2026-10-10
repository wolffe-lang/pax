# px21 — IP and ICMP (PAX answers ping)

Contract: px21's, `sprints/pax/21-ip-and-icmp/px21-ip-and-icmp.md` in
wolffe-lang/wolf (planning trunk, read 2026-10-10). Branch `px21` in
pax, cut from pax trunk `46b86b0` (px20 merged). §1–§3 are committed
before the first change to the kernel, the tools or the tests.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22):
  not Linux, a BSD, lwIP, picoTCP, smoltcp, iPXE, SeaBIOS, OVMF, QEMU
  or the user-mode network library QEMU links, and none found by a
  search; the refs clone's sparse checkout is never widened. Read or
  relied on: RFC 791 (the datagram), RFC 792 (ICMP), RFC 826 (ARP),
  RFC 894 (the frame), RFC 1071 (the checksum), RFC 1122 (what a host
  must do), RFC 1812 where it makes a point of RFC 1122's plainer,
  QEMU's documented options, and black-box runs (frames put on a
  netdev and the frames that come back). Each is recorded in
  `docs/SOURCES.md` with how it was used.
- No `region` is held open across a yield, a switch or a return to
  user mode (pax has not adopted s223). Nothing on the per-frame path
  allocates from the heap: every buffer is a frame from
  `kernel/frames` taken at start-up, and state is words in `.bss`.
- Nothing in pax names any use of the image beyond running it (the
  contract's word list). "Capture" means QEMU's `filter-dump` object
  writing a netdev's frames to a pcap file a test reads.
- No socket system call, no UDP, no TCP, no user-visible interface.
  No fragmentation and no reassembly: a fragment that arrives is
  counted and dropped by name, and PAX never sends one (§3).
- No test binary is built with kasumi's glibc (this lane builds no
  user program). No build on nomad-1.
- No `rm` outside `~/lanes/px21/` and this lane's private clones, on
  any host, `/tmp` included; no `git add -A`; nothing under
  `~/.claude`; no merge; no attribution trailers; no "seen red"
  without a run id, sha, path or digest.

## 2. Inputs, verified (2026-10-10, from origin)

| input | found |
|---|---|
| pax trunk | `46b86b0` (px20 merged, PR #23), as the contract says |
| the frame interface | `net.send(src, len) -> u64 ! {down, size, full}` copies 14 to 1514 bytes into a free transmit buffer and pads to 60; `net.rx_take()`/`rx_give(buffer)`; counters in `pax_net_stats`, 17 of 32 words used, word 31 `netd`'s turns |
| the receive path | `kernel/netd`'s one thread: `net.wait()`, then every returned frame in turn, by the type at bytes 12–13: 0x0806 to `arp.input`, everything else to `net.drop_type` (0x0800 counted `ipv4`); the buffer is given back after the protocol returns, so a protocol may write in it while it has it and must copy what it keeps. Nothing wakes the thread but the device's interrupt: there is no periodic work in the network today |
| `kernel/arp` | four entries, round-robin, no ageing, retry or queue; `request(ip)` broadcasts unconditionally; `lookup(ip)`; one composing frame; lock `sync.arp()` taken before `sync.net()`. Lock words 4–7 of `pax_sched_locks` are free |
| lengths | `kernel/net` hands on anything from 14 to 1514 bytes: a protocol checks its own (QEMU 8.2.2's gateway sends 42- and 45-byte frames) |
| checksum offload | none offered or taken (px20's measurement: features `0x0000010130bf8024`) |
| the address | `kmain_net`'s constant `OWN_IP` (10.0.2.15), passed to `arp.start` |
| what moves in `tests/mpx4-net` | N8 (`r4`, the `ipv4` drop count, held to the datagrams; and the totals), N5 (`tools/pcap-net`'s conversation: each datagram will now draw an answer), N6 (the soak is ARP's) |
| wolf-lang#653 | open; the literal `WANT` in `kernel/net` stays |
| the command line | `boot_info.cmdline_has(word)`: whole words only; no word with a value is read anywhere |
| QEMU | kasumi 11.1.1, nomad-1 11.1.1, hasu 11.1.0, CI 8.2.2; `-netdev help` on the first three lists `socket`, `dgram`, `stream`, `hubport` and `user` |
| `-netdev user` and ICMP, measured | A probe with no guest (`-machine none`, a `user` netdev and a `socket,udp=` netdev on one hub; frames written to the UDP socket by a script): **kasumi, hasu and nomad-1 alike** — the gateway answers ARP for 10.0.2.2 with a 64-byte frame; an echo request to 10.0.2.2 with 0, 56 or 1472 data bytes is answered by the gateway itself (type 0, TTL 255, DF set, identification counting from 0, both checksums right, the data intact; 60, 98 and 1514 bytes); 10.0.2.3 answers the same way; an echo to an address outside (the host's own LAN address, 127.0.0.1) is answered with that address as the source — proxied — on all three (`ping_group_range` is `0 2147483647` on kasumi and hasu; macOS allows the unprivileged socket). An echo to 10.0.2.99, sent to the gateway's hardware address, is not answered in 2 s. The CI runner is measured by the same probe in CI (§4) |
| an echo from outside into a guest | not possible under `-netdev user`: `hostfwd` forwards TCP and UDP only (QEMU's documentation), and the gateway originates no ICMP of its own |

## 3. Prediction (before the first change)

**Module layout.**

- `kernel/ip` (new): `start(address, netmask, gateway)`, the boot-time
  triple; `input(frame, len)`, the one place a received header is
  validated; `send(dst, protocol, payload, len)`; `sum`, the RFC 1071
  checksum; the route; counters.
- `kernel/icmp` (new): `input` (echo request answered, echo reply
  matched to the kernel's own request), `ping(dst, seq, bytes)`,
  `unreachable` (type 3 code 2), counters.
- `kernel/arp` (rewritten): the cache, `resolve`-and-send with a
  pending queue, `tick`.
- `kernel/netd`: 0x0800 goes to `ip.input`; a second thread body runs
  the cache's clock (`arp.tick` every 10 ticks).
- `boot/net.S`: more storage; `kernel/sync`: two more lock words
  (`ip`, `icmp`); `kernel/net`: the `ipv4` drop cause retires;
  `kernel/kmain_net.lu`: the self-tests, behind command-line words
  (`ping`, `peer`); `boot/limine-net.conf` gains `ping`, a new
  `boot/limine-net-peer.conf` holds `peer`.
- Tools and tests: `tools/net-peer` (new, the other end of a socket
  netdev), `tools/gateway-probe` (new, §2's probe), `tools/pcap-net`
  (IPv4 and ICMP, every checksum recomputed), `tests/mpx4-net` (a
  fifth way to boot, `peer`), the CI job, `docs/SOURCES.md`, the
  READMEs, `CHANGELOG.md`. Predicted unchanged: `kernel/virtio`,
  `kernel/pci`, `kernel/sched`, `kernel/interrupts`, every other
  kernel and test.

**Where the header is validated, and each drop cause** (`ip.input`,
in this order, each a counter of its own): `short` (fewer than 20
bytes after the frame header, or fewer than IHL × 4); `version` (not
4); `ihl` (under 5); `checksum` (the header's sum is not 0xffff);
`length` (total length under IHL × 4 or over the bytes the frame
holds; bytes after it are padding and ignored); `ttl` (0: RFC 1122
§3.2.1.7 forbids sending it; TTL 1 is accepted, as the same section
requires); `fragment` (MF set or a non-zero offset); `source` (a
source that names no single host: 0.0.0.0, 127/8, a broadcast, class D
or E, or PAX's own address); `option` (an option list that does not
parse) and `source-route` (LSRR or SSRR: refused by name; every other
option is skipped, RFC 1122 §3.2.1.8); `other` (a destination that is
neither PAX's address, the limited broadcast nor the subnet's); then
by protocol: 1 to ICMP, anything else `protocol` (and a destination
unreachable, code 2, unless RFC 1122 §3.2.2 forbids an error: a
broadcast destination, a link-layer broadcast). ICMP's own: `short`
(under 8 bytes), `checksum`, `broadcast` (an echo request to a
broadcast address is not answered, RFC 1122 §3.2.2.6's MAY), `type`
(a type nothing here handles), `stray` (an echo reply nobody waits
for).

**The ARP cache.** 8 entries. An entry is free, incomplete or
resolved. **Ageing:** a resolved entry is good for 60 s (6000 ticks,
RFC 1122 §2.3.2.1's "on the order of a minute"; a boot-time
parameter, shortened by the `peer` test) from the last ARP packet
that named its sender; a use after that makes it incomplete and asks
again. **Retry:** an incomplete entry is asked for once a second (RFC
1122 §2.3.2.1's rate), three requests at most; after the third goes
unanswered for a second the entry is freed and what waited is dropped
by name (`unresolved`). **Pending queue:** two frames per unresolved
address (RFC 1122 §2.3.2.2 asks for at least the latest one); a third
pushes out the oldest, counted `pending-dropped`; a reply sends what
waits, oldest first. **Eviction:** a new address takes a free entry,
else the resolved entry confirmed longest ago; never an incomplete
one (then the frame is dropped, `table-full`). **Learning:** RFC 826's
algorithm as px20 has it — an ARP packet updates an entry that exists
and creates one only when its target is PAX's address; so a
gratuitous ARP for an address PAX holds no entry for creates nothing.
New: a packet whose sender is 0.0.0.0, a broadcast or PAX's own
address teaches nothing (`conflict` counted for the last). Nothing is
learned from an IP datagram's source.

**The route.** `(dst & mask) == (own & mask)`: on-link, the next hop
is `dst`; else the gateway (10.0.2.2); the limited and the subnet's
broadcast go to ff:ff:ff:ff:ff:ff without ARP. An echo reply is routed
like any datagram, by its destination: it is not sent back to the
hardware address the request came from.

**What PAX sends.** Version 4, IHL 5, no options, DF set, TTL 64,
identification a counter from boot, one datagram per frame. **The
MTU is 1500 bytes**: `ip.send` refuses a payload over 1480 bytes
(`size`); an echo reply is as long as its request, which arrived in
one frame, so it always fits; PAX never fragments, and with DF set
nothing downstream may.

**Echoes per second** (56 data bytes, a 98-byte frame, one at a time,
each waited for; by the time-stamp counter as px20's soak):

| | PAX asks the gateway | the peer asks PAX (a Python script over UDP) |
|---|---|---|
| TCG, kasumi | 25,000 | 4,000 |
| TCG, CI | 18,000 | 3,000 |
| KVM, hasu | 55,000 | 5,000 |

(px20's ARP exchange ran 28,250–66,916/s on kasumi and 63,508–72,173
under KVM; an echo adds two checksums over 84 and 64 bytes on each
side. The peer's rate is the script's, not the kernel's.)

**The test mechanism for an echo from outside.** A `-netdev
socket,udp=…,localaddr=…` netdev (each Ethernet frame one UDP datagram
on the host's loopback) with a host script, `tools/net-peer`, at the
other end: it plays an on-link host (10.0.2.100), the gateway
(10.0.2.2) and, behind the gateway, an off-link host (192.0.2.1); it
answers PAX's ARP, sends echo requests and the malformed datagrams,
and checks every reply. Argued against a second QEMU: that needs a
second guest able to ping (a Linux image, fetched and booted on every
leg), is slower, and cannot send a datagram with a wrong checksum.
Against a hub joining the user netdev and the socket: QEMU's gateway
would answer for the addresses the test wants to control. It needs no
privilege, no tap device and no ICMP socket, so it runs on the CI
runner; `socket` is in QEMU 8.2.2's documentation and in all three
pool hosts' `-netdev help`. The kernel and the script keep step
without a hook in the kernel: the script's phases are answers to
frames the kernel sends, and the kernel leaves its serving loop when
`kernel/net`'s count of frames of a type nothing speaks moves (the
script sends one frame of type 0x88b5).
**Predicted for CI's QEMU 8.2.2:** the same socket netdev works; the
gateway answers echo itself; echo to an outside address is proxied
(Ubuntu's `ping_group_range` admits every group).

**Existing tests that move:** `tests/mpx4-net` only — N5 (the
capture's conversation), N6 (the soak becomes 10,000 echoes), N8 (the
`ipv4` drop count goes; the totals), and new assertions for IP, ICMP,
the cache and the peer. No other suite's assertions move; kernels
other than `kmain_net` change only if `kernel/net`'s bytes do (it is
linked into each).
