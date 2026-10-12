# px35 — The green trunk (pax#39 and pax#29's network flakes)

Contract: px35's, `sprints/pax/35-the-green-trunk/` in wolffe-lang/wolf
(read 2026-10-12). Branch `px35` in pax, cut from pax trunk `0f7cd28`
(px34 merged). §1–§3 are committed before the first change to the
kernel, the tools or the tests.

One deliverable: pax trunk green on repeated CI runs, each network
flake's cause found and fixed in the kernel or in the test as Linux's
behaviour decides — never by loosening an assertion, adding a retry or
raising a timeout without a measured reason.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22).
  Facts come from the RFCs (791, 792, 826, 1122, 5681, 9293), the man
  pages (`epoll(7)`, `epoll_wait(2)`, `unix(7)`, `poll(2)`), the uapi
  headers, and black-box runs of Linux.
- No assertion weakened, no retry loop, no timeout raised without a
  measured reason. Where a test's expectation is wrong it is proved
  against Linux first.
- No word implying filming, recording, viewers or a demo in pax. No
  trailer of any kind on a commit or the PR; no merge, tag, issue filed
  or closed; nothing under `~/.claude`; nothing installed; no build on
  nomad-1; no `/tmp` (scratch under `~/lanes/px35/` on every host); a
  job killed by its recorded pid only; another lane's CI run never
  cancelled; at most two CI runs of this lane at once.

## 2. Inputs (re-derived)

| what | where | what it says |
|---|---|---|
| trunk | `0f7cd28` (px34) | the base |
| pax#39 | run 38207077489 (job 114672827976, push at `0f7cd28`) and 38208203649 (PR #38) | `mpx4-unix` U1 native bios probes, line 172: `client: epoll_wait 1, IN, data 7` on PAX where Linux read `IN HUP RDHUP` |
| pax#29 (1) | run 38133240315, job 114451736924 | `mpx4-net` N8 native bios peer: `icmp.matched` kernel 10, capture 11; `icmp.stray` kernel 2, capture 1 |
| pax#29 (2) | run 38198213544, job 114645543222 (push at `579ac9f`) | `mpx4-tcp` native bios peer: `net-peer: FAIL PAX's four resets for segments nobody takes: not in 10 s`; T2/T3/T6–T9 follow from the stop |
| pax#29 (3) | run 38192937184, job 114629387349 | `mpx4-tcp` release uefi peer: `net-peer: FAIL loss in 1%: the receiver said b''` |
| pax#29 (4) | px27's gauntlet on kasumi, not CI | `pcap-net` echo requests sent kernel 0, capture 1; TCP segments one fewer |
| pax#32 | open | `kernel/arp` pushes the kernel's own frames out of its two-frame queue when an entry ages under load |

What the failing captures (the jobs' artifacts) show, read before any
prediction:

- **N8** (`mpx4-net-native-bios-peer.pcap`): the queue step's two
  echo requests the ARP reply let go, seq 3 and 4, left PAX 256 µs
  apart, and net-peer's reply to seq 3 reached PAX's wire *between*
  them (240 µs). In the three other legs of the same run the two
  requests left 22–72 µs apart, both before any reply.
- **T10** (`mpx4-tcp-native-bios-peer.pcap`): of the four resets for
  segments to a closed port, only those for ports 40912 and 40914 left
  PAX — after an ARP request for 10.0.2.2 at 60.259 s, 60.259 s after
  the first one: the gateway's entry aged (60 s, `arp.AGE`) on the
  first of the six stray segments, the four resets were queued
  behind the new request, and the two-frame queue pushed the first two
  out (pax#32).
- **T11** (`mpx4-tcp-release-uefi-peer.pcap`): on port 7101 PAX's
  window closed to 1,419 bytes under the bulk receive and net-peer's
  segments shrank to fit; one was lost; three duplicate ACKs; net-peer
  fast-retransmitted a full 1,460-byte segment from SND.UNA — 41 bytes
  past anything it had sent (its SND.MAX) — PAX took them all and
  acknowledged 918602 (relative), and net-peer, holding that ACK to its
  SND.MAX, ignored it from then on: twelve retransmissions over 24 s,
  each acknowledged the same way, until the step's deadline.

## 3. Prediction (committed before the first change)

**P1, pax#39 — the probe races, Linux the same.** The probe's server
sends the answer, writes a line to the console, then closes. The send
makes the client's `epoll_wait` ready; PAX computes readiness when the
waiter runs its call again (kernel/ready, as `epoll(7)` describes it),
so the client reads `IN HUP RDHUP` only when the close comes before it
runs. On PAX's one CPU the server keeps the CPU until a tick; the
console write is long under TCG and a tick that falls in it preempts
the server on its return, before the close — more often the more the
host is starved. Linux promises no order between a woken waiter's
collection and its peer's next system call either: under load
(`taskset -c 0-3` and parallel work) the same probe on Linux reads
`IN` alone too, at a lower rate. So the kernel is right and the probe
is wrong; the fix is the probe: the client waits twice, first woken by
the answer while the server keeps the connection open until the client
has read it (then `IN`, forced), then woken by the close (then
`IN HUP RDHUP`, forced). Reproduced by running the probes session
repeatedly under load on kasumi, PAX and Linux both, and counting.

**P2, pax#29 N8 — the oracle's order is not the kernel's.** The kernel
waits for the last echo it *made*: the queue step made seq 1–4 while
10.0.2.100 was unresolved, so seq 4 is awaited before either queued
request reaches the wire and seq 3's reply is stray, always.
`tools/pcap-net` sets the awaited echo from the last request *on the
wire*; when seq 3's reply lands between the two flushed requests it
calls it matched. The window is the gap between the two frames
kernel/arp's flush hands kernel/net one at a time, each published and
notified on its own (22–72 µs unloaded; 256 µs on the red run). Fix in
the kernel: the frames an ARP reply lets go are published to the
device together and notified once, so they leave back to back and the
wire order is the kernel's order; then the oracle's rule holds.
Reproduced by repeated `mpx4-net` boots under load on kasumi, counting
captures where a reply lands between the flushed requests.

**P3, pax#29 T10 (and pax#32) — an aged entry drops the kernel's own
frames.** The reset burst is made while the gateway's entry renews;
two of four are pushed out. Linux (black-box: its traffic on the tap
continues across a renewal, with a unicast request to the cached
address) keeps using an entry while it asks again; RFC 1122 §2.3.2.1
lets a cache refresh an entry in use. Fix in the kernel: a resolved
entry past its age is still used while it is asked for again (the same
three requests a second apart); a reply confirms it; no reply after
the third frees it. mpx4-net's P2 assertions stand unchanged (its
`aged` step still counts one aged entry asked for again; its
unresolved address still pushes two out). Reproduced deterministically
by a new step in kmain_net's peer run: a burst of four echo requests
to an entry that has just aged, all four on the wire — red on trunk's
kernel (two), green after.

**P4, pax#29 T11 — net-peer's fast retransmit overruns SND.MAX.**
`tools/paxtcp.py` sends `min(unsent, MSS)` from SND.UNA on the third
duplicate ACK without bounding it by SND.MAX; when the segments it sent
were smaller than the MSS (a window closing under a slow reader, which
a loaded runner makes) the retransmission carries new bytes SND.MAX
does not count, and PAX's correct acknowledgement of them is ignored
forever. Fix in the tool: the fast retransmission is bounded by what
was sent (RFC 5681 §3.2: the lost segment is retransmitted). Reproduced
deterministically by a host witness that drives paxtcp's connection
through sub-MSS segments, a loss and three duplicate ACKs, and checks
the retransmission's end and that PAX's ACK is then taken — red before
the fix, green after.

**P5 — not predicted to be fixed here:** pax#29's kasumi-only
sighting (4) is a different shape (one frame classified differently)
and is chased only if the repeated runs show it.

Proof per flake: red under the load (or the witness) that reproduced
it, green after, the counts kept under `notes/px35/`; then CI on the
branch at least three times green.
