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

## What was built

1. **IPv4 receive** (`kernel/ip`'s `input`): the one place a header is
   judged, in the order §3 gives, a counter per cause — `short`,
   `version`, `ihl`, `checksum`, `length`, `ttl`, `fragment`, `source`,
   `option`, `source-route`, `other`, `protocol`. It returns what the
   datagram is and `kernel/netd` makes the call, so `ip` imports no
   protocol above it.
2. **IPv4 send** (`ip.send`): version 4, IHL 5, DF, TTL 64, an
   identification counted from boot, the RFC 1071 sum (`ip.sum`);
   on-link or by way of the gateway from `ip.start`'s
   address/netmask/gateway; the broadcasts without resolution; a
   payload over 1480 bytes refused (`size`). The frame goes out
   through `arp.send`.
3. **The ARP cache** (`kernel/arp`, rewritten): 8 entries; a resolved
   one ages out a minute (`start`'s `age`) after the last ARP packet
   from its address; an incomplete one is asked for three times, a
   second apart, then given up (`unresolved`); two frames wait per
   address and a third pushes out the oldest (`pushed out`); a new
   address evicts the resolved entry confirmed longest ago and never an
   incomplete one (`table full`); RFC 826's learning, so a gratuitous
   announcement changes an entry that exists and creates none; a
   sender of 0.0.0.0 or the broadcast teaches nothing and one claiming
   PAX's address is a `conflict`. A second kernel thread
   (`pax_net_clock`) runs the cache's clock every ten ticks.
4. **ICMP** (`kernel/icmp`): an echo request answered in place (type
   0, the checksum made again, the data entire) and routed by its
   destination; the kernel's own echo request (`ping`, `answer`: the
   round trip by the time-stamp counter), behind `ping` on the kernel
   command line in `kmain_net` (six to the gateway); destination
   unreachable, code 2, for a protocol nothing speaks, one a second
   (`limited`), none where RFC 1122 forbids (`silent`).
5. **Tests** (`tests/mpx4-net`: G0, N0–N12, P1–P4; `tools/net-peer`,
   `tools/pcap-net`, `tools/gateway-probe`, `tools/paxnet.py`), below.

Not filed: nothing new in wolf was hit. `take` is a reserved word
(E0008, with a clear message). wolf-lang#653 stays as px20 left it.

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| `kernel/ip`, `kernel/icmp` new; `kernel/arp` rewritten; `netd` gains the demultiplexing and a clock thread; `net`'s `ipv4` cause retires; two lock words; more storage | so. One thing not predicted in the layout: `ip.input` does not call `icmp` — wolf modules would import each other — so `netd` makes the call from `input`'s answer |
| the drop causes and their order | as predicted, and each seen from outside: `tools/net-peer` sends 31 datagrams that must be dropped, the model in `tools/paxnet.py` names the cause of each, and the kernel's counters equal the model's in every boot (`short` 2, `version` 1, `ihl` 1, `checksum` 1, `length` 2, `ttl` 1, `fragment` 2, `source` 7, `option` 3, `source-route` 2, `other` 2, `protocol` 9; ICMP's `short` 1, `checksum` 1, `broadcast` 2, `type` 2, `stray` 2) |
| the cache: 8 entries, a minute, three requests a second apart, two frames kept, the oldest pushed out | so: 4 echo requests sent before the address is known give `4 queued, 2 pushed out` and the last two on the wire (identifications 2 and 3); 10.0.2.99 is asked for 3 times, 1.00 and 1.00 s apart, and given up after 300–301 ticks with 1 frame dropped; an entry aged at 2 s (the `peer` kernel's setting) is asked for again |
| the route: on-link, else the gateway; a reply routed by its destination | so: echo requests for 192.0.2.1 leave for the gateway's hardware address, and the reply to a request from 192.0.2.1 does too |
| DF, TTL 64, no fragments, a 1500-byte MTU, 1480 bytes the most `send` takes | so: 1472 data bytes go out in a 1514-byte frame and are answered; 1473 are refused by name |
| PAX asks the gateway: 25,000 echoes/s on kasumi TCG, 18,000 on CI, 55,000 under KVM | kasumi TCG **19,954–21,150** (native) and 46,440–53,466 (release); CI **13,716–16,403** and 22,718–27,179; nomad-1 TCG 12,144–16,672 and 29,096–31,552; hasu KVM **55,109–58,754** and 64,935–70,198. The KVM figure held; the TCG ones were high by a fifth on the native tier and low by half on the release tier — the prediction gave one number for two tiers that differ by 2.4 times under TCG (the byte-at-a-time sum is the native tier's cost) |
| the peer asks PAX: 4,000/s on kasumi, 3,000 on CI, 5,000 under KVM, "the script's rate" | kasumi 19,363–20,588 (native), 34,021–35,054 (release); CI 9,661–9,800, 12,136–12,485; nomad-1 12,723–13,304, 19,669–20,903; hasu KVM 31,996–36,856. **Low by 3 to 7 times**, and the stated bound was wrong: on the native tier under TCG the kernel, not the script, is the slower end (the rate equals PAX's own against the gateway) |
| the mechanism: a `socket,udp=` netdev and a host script; works on CI's QEMU 8.2.2 | so, first try (run 38093374371). Not predicted: a frame of 26 bytes reaches the guest as 26 bytes on 8.2.2 and 11.1.x alike, so `short` is exact on every host |
| CI's gateway answers echo itself | so (G0 in run 38093374371) |
| CI's gateway proxies an echo to an outside address | **wrong**: `outside=0/2`. The runner's `ping_group_range` is `1 0` (no group admitted), not Ubuntu's desktop default; kasumi, hasu and nomad-1 all proxy (2/2). Nothing in the test stands on it |
| tests that move: `tests/mpx4-net` N5, N6, N8 only | those, and N4 (the gateway is already in the cache from its own request, so `0 requests`) and N2 (kernel/ip's line); px20's ARP soak is gone (the echo soak resolves once and the cache holds). No other suite's assertions moved (the gauntlet) |
| files: as listed; `kernel/virtio`, `kernel/pci`, `kernel/sched`, `kernel/interrupts` unchanged | so. `tools/paxnet.py` was not predicted (the model the three tools share) |

Rates are by the time-stamp counter, calibrated against 20 PIT ticks
in the same boot, QEMU's capture on (kasumi: the gauntlet's suite run
and `t1`; CI: run 38093374371; hasu: three rounds; nomad-1: one run).
Round trips of the six pings (N12): median 53 µs under KVM (14–151),
77 µs on CI (36–572), 243 µs on kasumi (26–2,284: the first of a boot
is the slow one).

## 4. Evidence index

Files are under `notes/px21/`.

- **`-netdev user` and ICMP, per host** (`tools/gateway-probe`, no
  guest): `gateway-probe.{kasumi,hasu,nomad-1}.txt`; CI's is G0's line
  in `ci-38093374371-mpx4-net-991c56b.txt`, whose first line is the
  runner's `ping_group_range`.
- **The captures and the checker's verdicts.** A run is 12 captures
  (2 tiers × 2 firmwares × net, modern, peer): 45,016 frames in each
  of the eight against the gateway (35,008 from PAX, 10,008 to it) and
  20,174 to 20,186 in each of the four against the peer (how often an
  entry ages out under the 10,000 echoes varies by a few ARP
  exchanges; OVMF's own driver sends one or two frames first on some
  UEFI boots, printed as "before the kernel"): 440,861 frames in the
  gauntlet's run, every one PAX sent rebuilt and compared byte for
  byte, every one that reached it judged, 40,027 and 40,207 checksums
  recomputed per capture.
  `kasumi-g1-mpx4-net.checks.txt` has each capture's digest, size and
  verdict lines (the model's counts under the kernel's names, and
  `the kernel's counters are the capture's (52 held)`); the digests
  are also in `kasumi-g1-mpx4-net-runs.txt`. A capture is 2.3 or 11.5
  MB, so the repository carries two heads as pcap files of their own:
  `kasumi-g1-native-bios-peer.head.pcap` (the first 120 frames of
  `04bc4de9ddc6…`: all of part A and the start of part B) and
  `kasumi-g1-native-bios-net.head.pcap` (the first 24 of
  `f555ab39420d…`: the gateway's request, PAX's reply, this script's
  datagram and PAX's destination unreachable for it, the six pings,
  the soak's start). They are cut short, so `tools/pcap-net --list N`
  prints them and then says what the cut left unanswered. CI's twelve
  are in each run's `pax-mpx4-net-linux` artifact, with their digests
  in the `halt-status` lines of the CI file here.
- **Counters**: every boot's two `net:`, two `arp:`, two `ip:` and two
  `icmp:` lines, held against its capture by `tools/pcap-net --serial`
  (N8) and, for the peer way, to exact numbers (P4). Whole
  transcripts: `kasumi-g1-native-uefi-peer.transcript.txt` (with
  `tools/net-peer`'s account of the same boot,
  `kasumi-g1-native-uefi-peer.net-peer.txt`) and
  `kasumi-g1-native-bios-net.transcript.txt`.
- **The soaks**: 10,000 echoes out (N6) and 10,000 in (P3, 10,028
  with the battery's) on every leg, and the books the same before and
  after on every one — for example kasumi native BIOS: `frames free
  64694, heap pages 0, live blocks 0, net frames 66, stack frames 11`
  both times. The heap's books are flat because nothing on the frame
  path allocates from it (§1); what could leak is frames, queue slots
  and ring entries, and N8 holds those: every sent buffer reclaimed,
  every received one restocked, every queued frame sent, pushed out
  or given up, 64 of 64 transmit buffers free at the end.
- **Planted breaks, red in CI**:
  - a wrong checksum fold (`82f8e08`: `ip.sum` drops the carries
    instead of adding them back): run **38093741823**, the `mpx4-net`
    job alone red — N12, N6 on all eight gateway legs (`0 of 6 ping
    lines`; `soak: 1 echo requests, 0 replies in 301 ticks`), N5 and
    N8 on all twelve captures (`pcap-net: FAIL frame 3 of 25012: a
    destination unreachable from PAX that quotes no unanswered
    datagram of an unknown protocol, byte for byte`), P1–P4 and N9 on
    the four peer legs (`net-peer: FAIL part A: not echo request 3 …
    byte for byte`); 67 assertions still green
    (`ci-38093741823-mpx4-net-plant-82f8e08.txt`); reverted in
    `297be14`.
  - an echo reply with the two addresses unswapped (`fdb84ca`:
    `icmp.input` sends the reply to the request's destination, PAX's
    own address): run **38095372801**, the `mpx4-net` job alone red —
    P1, P3, P4, N5, N8 and N9 on the four peer legs (`net-peer: FAIL
    PAX asked for 10.0.2.15, which this script does not play`;
    `pcap-net: FAIL frame 48 of 48: the capture ends with 1 echo
    requests to PAX unanswered; the oldest is from 10.0.2.100`; the
    kernel never told to stop, so no `halt` in 180 s); the eight
    gateway legs stay green, as they must: no echo request reaches PAX
    there, which is why the peer way exists; 103 assertions still
    green (`ci-38095372801-mpx4-net-plant-fdb84ca.txt`). Reverted in
    `d1556ec`.
- **Boot counts** (`tests/mpx4-net` is 20 boots: 2 tiers × 2
  firmwares × net, modern, peer, absent, legacy):
  - kasumi, QEMU 11.1.1, TCG: 40 in two full runs (`t1` on the
    working tree and the gauntlet at `991c56b`, each 127 PASS, 0 FAIL,
    0 SKIP) and four single boots while the kernel and the plants were
    tried;
  - hasu, QEMU 11.1.0, **KVM**: 60 in three rounds (kasumi-built
    images of the same kernel source, each round 125 PASS, 0 FAIL;
    `hasu-kvm-k1.log`, `hasu-kvm-k1-round1.out`,
    `hasu-kvm-k1-round1-runs.txt`);
  - nomad-1, QEMU 11.1.1, TCG on macOS arm64: 20 (the same images,
    125 PASS, 0 FAIL; `nomad-1-tcg.out`, `nomad-1-tcg-runs.txt`);
  - CI, QEMU 8.2.2, TCG: 20 a run.
- **The gauntlet** on kasumi at `991c56b` (strict env, QEMU 11.1.1
  TCG, wolf 0.2.26, clang 23.1.1; user programs built in
  `px13-ubuntu`): every pax suite exit 0, 0 FAIL, 0 SKIP
  (`kasumi-g1.summary`, `kasumi-g1.versions`). The head differs from
  `991c56b` by the two plants, their reverts and these notes: no file
  under `kernel/`, `boot/`, `tools/` or `tests/` differs.
- **CI green**: run 38093374371 at `991c56b` (19 jobs; `mpx4-net` 127
  PASS, `ci-38093374371-mpx4-net-991c56b.txt`), and at the head (the
  PR names the run).

## 5. Done-when

Branch `px21`; PR pax#24 open, unmerged, five sections by name, commit
shas as bullets, a test checklist; CI green at the head;
`wolf/tools/lane-audit.sh pax px21 24` run by the lane. Nothing is
closed. To close at merge: nothing.

**px22 (UDP and the socket syscalls) inherits:**

- `ip.send(dst, protocol, payload, len)` (answers `arp.SENT`,
  `arp.QUEUED`, or why not) and `ip.input`'s answer in `kernel/netd`:
  add protocol 17 where `netd` now calls `icmp.unreachable` for
  `ip.NO_PROTOCOL`. `tests/mpx4-net` holds `protocol` to 9 in the peer
  way and to this script's datagrams against the gateway, and
  `tools/paxnet.py`'s `judge_ip` calls every protocol but 1 unknown:
  all three move when UDP lands (a datagram for a port nobody listens
  on is then a port unreachable, code 3, which `icmp.unreachable` does
  not send yet);
- the UDP checksum is the kernel's to compute and check (no offload);
  `ip.sum` is the RFC 1071 sum, and the pseudo-header is px22's;
- a frame's bytes are the protocol's only until `netd` gives the
  buffer back: a socket's receive queue must copy. Nothing on the
  path allocates from the heap today, and no `region` may span a
  switch until pax adopts s223;
- **no loopback**: a datagram for PAX's own address is routed like any
  other and waits on an ARP request nobody answers (seen in the
  second plant); 127/8 is refused as a source and has no interface.
  lobo binds a loopback TCP socket to itself (px04's census), so
  px23 at the latest needs one;
- the address, netmask and gateway are `kmain_net`'s constants handed
  to `ip.start`: there is no DHCP and no word on the command line for
  them; QEMU's DNS is 10.0.2.3 (it answers echo, G0);
- one echo is waited for at a time (`icmp.ping`/`answer`), kernel-only;
  a ping socket is not this;
- the MTU is 1500 and nothing fragments or reassembles: a UDP datagram
  over 1472 bytes cannot be sent and a fragmented one that arrives is
  dropped by name (QEMU's user network does not fragment toward the
  guest in anything measured here);
- received ICMP errors are counted `type` and used by nothing: a
  socket that should see ECONNREFUSED from a port unreachable needs
  them delivered;
- `tools/net-peer` and `tools/pcap-net` are rule-based: a new protocol
  is a new verdict in `tools/paxnet.py`'s model, and the peer can play
  any host. The user-mode gateway forwards UDP into the guest
  (`hostfwd=udp:…`, which the `net` way already uses to wake the
  gateway) and answers DNS;
- the ARP cache's lock order is `sync.ip()`, then `sync.arp()`, then
  `sync.net()`; `sync.icmp()` is never held across a call into `ip`;
- owed by earlier lanes and not this one's: `docs/CENSUS.md` lines 56
  and 640 and `docs/SOURCES.md` line 77 (px19's note); `/dev/tty0`
  (px18's); MSI-X, EVENT_IDX and merged buffers (px20's untaken
  levers).
