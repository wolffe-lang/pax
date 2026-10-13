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
- None of the words the contract's §1 bars from pax. No
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

## 4. What was found, flake by flake

Trees on kasumi (Linux 7.2.8, QEMU 11.1.1 TCG, wolf 0.2.27 by digest,
test programs built in `px13-ubuntu`): `trunk` = `0f7cd28`; `w1` =
`02a07c6` (trunk's kernel and the renewal witness); `w2` = `cad6fc9`;
`w3` = `7bb705d` (every fix); `w4` = `795ad71` (`w3` rebased onto trunk
`6316c51`, px32's merge; nothing of px32's touches the network). The
branch was rebased again onto `feba3fc` (px25), dropping this lane's
probe commit (pax#39, below); the gauntlet and CI at the new head are
in the PR body. "Under
load" is 12 busy loops pinned to four CPUs with the suite or program
under `taskset` to the same four (`notes/px35/kasumi/scripts/`).

**pax#39 (mpx4-unix U1) — the probe raced, and the side that read
`IN` alone was Linux.** pax#39 says PAX read `IN`; the diff in U1 is
`diff linux pax`, so its `<` line is Linux's. Both CI reds (38207077489,
38208203649) have `session.linux` line 172 `IN, data 7` and PAX's
`IN HUP RDHUP` (the artifacts' `*.session` and `*.session.linux`). The
prediction's direction was wrong; its cause was right. Counted on
kasumi with trunk's probe:

| side, trunk probe | `IN` alone | `IN HUP RDHUP` |
|---|---|---|
| Linux (px13-ubuntu container), under load | 21 of 40 | 19 |
| Linux, no added load | 1 of 40 | 39 |
| PAX (TCG), under load | 0 of 40 | 40 |

PAX never showed it: a system call runs with IF clear on its one CPU,
so the server's console write and close are not split by a tick the
way Linux's two CPUs split them. Linux promises no order between a
woken waiter's collection and its peer's next call (`epoll(7)` reports
readiness as it is when collected); the probe asked for one. The kernel
is unchanged. This lane's probe fix (two waits ordered by a pipe:
under load Linux 40 of 40 and PAX 20 of 20 the same lines, `w3`) was
**dropped at the rebase onto `feba3fc`**: px25 fixed the same race in
the probe (`e8931f4`: the server closes only after the client's word
that its wait is over) and pax#39 is closed. What this lane's version
covered beyond it — a client more than 100 ms late to its first `recv`
meeting the answer already there — was never seen, and is listed under
§6.

**pax#29 N8 (mpx4-net) — the wire's order was not the kernel's.** The
kernel awaits the last echo it made; in the queue step that is seq 4
before either queued request leaves, so seq 3's reply is stray, always.
`tools/pcap-net` judges by the wire; when kernel/arp's flush handed
kernel/net the two queued frames one at a time, each published and
notified on its own, seq 3's reply could reach the wire before seq 4
left. Trunk under load: N8 peer red in 4 of 5 runs, each with seq 4
1,848–3,396 µs after seq 3 and the reply between; the one green had
them 47 µs apart. The fix stages both, publishes the avail index once
and notifies once (`net.send_batch`, `virtio.place`/`publish`): `w3`
under the same load, N8 peer green in 5 of 5, seq 4 18–54 µs after seq
3 and both before either reply.

**pax#29 T10 (mpx4-tcp) and pax#32 — an aged entry dropped the
kernel's own frames.** The failing capture shows the gateway's entry
aging at 60.259 s on the first of the stray segments, the four resets
queued behind the new request and the first two pushed out. The new
mpx4-net step makes four echo requests while 10.0.2.100's entry renews:
`w1` (trunk's kernel) `2 pushed out`, net-peer red at A7
(`notes/px35/kasumi/w1/net-peer-red.out`); `w2` `0 pushed out, 1
requests`, mpx4-net 32 PASS 0 FAIL (`w2/net-bios-native.out`). The
cache now keeps a stale entry in use while it asks again (three
requests a second apart, then freed); P2's own assertions (`4 queued,
2 pushed out`, the aged step, `1 unresolved`) stand unchanged. Not
reproduced as T10 itself (the 60 s boundary would have to fall on the
burst); reproduced as its mechanism. The px27 sighting on kasumi (one
TCP segment counted as an echo request, a loaded run past 60 s, before
px24's pcap-net) is read as the same mechanism, not re-run.

**px25's time-wait change (`feba3fc`) does not explain these mpx4-tcp
reds.** It ends a time-wait entry on a reset at RCV.NXT, for QEMU's
user network reusing host ports (the `user` way). Both CI reds traced
here are the `peer` way and neither capture involves a time-wait
entry: T10's two resets never left PAX (ARP, above); T11's stall is
net-peer ignoring a correct ACK (below).

**pax#29 T11 (mpx4-tcp) — net-peer's TCP, not PAX's.** PAX acknowledged
exactly what it was sent; net-peer's fast retransmission had sent 41
bytes past its SND.MAX and so ignored that ACK forever. The witness
`tests/paxtcp-selftest` (no QEMU; CI runs it first in the mpx4-tcp job)
is red at `9bcae04` before the fix (F1: 1,460 bytes retransmitted when
1,000 were sent, the ACK not taken) and green after `76a9a21`.

**Found under load, not yet seen on CI: `grep -q` under pipefail.**
Trunk under load also failed N1, N3 and N8 on the `net` and `modern`
legs with every line they look for present in the log. mpx4-net's `has`
was `serial_norm | grep -Eqx`: grep leaves at its first match and sed's
next write dies of SIGPIPE, so the pipe fails. A 205,916-byte log with
the match on line 1: the old `has` true 0 of 50, the new 50 of 50; a
4,601-byte log under load: 294 of 300 against 300 of 300
(`pipefail/result.txt`). Every `serial_norm | grep -q` in the tests
(mpx4-net six, mpx2-heap one) now reads to the end.

**Under load, beside the point:** on the fullest kasumi (other lanes'
work plus four of these load sets, load average above 30) the `net`
and `modern` legs' 10,000-echo soak ran at about 20 echoes a second and
missed the boot's 180 s deadline, on trunk's kernel and this one's
alike (`netrace2-trunk-load12`, `netrace2-w4-load12`). On CI the soak
takes about 40 s. No deadline was raised.

## 5. Evidence index

- CI reds read: 38207077489, 38198213544, 38133240315, 38192937184,
  38208203649 (logs and artifacts in `~/lanes/px35/ci/` on nomad-1).
- kasumi, `notes/px35/kasumi/`: `race-*` (pax#39 counts and lines),
  `netrace-*` (N8: the first four ICMP frames of each peer capture,
  and every FAIL line), `w1`/`w2` (the renewal witness red and green),
  `w3/summary.txt` (mpx4-unix 60/0, mpx4-tcp 100/0 at `7bb705d`),
  `pipefail/result.txt`, `scripts/` (how each was run; `race.sh` as it
  stands after its CPU set became a variable).
- The gauntlet at the rebased head and the CI runs: the PR body.

## 6. Not verified

- T10 itself red-to-green (its mechanism is; the 60 s boundary was
  not steered onto the burst).
- Linux's own behaviour when an entry ages, by capture: the cache rule
  rests on RFC 1122 §2.3.2.1; no Linux tap capture past a minute was
  taken.
- hasu KVM: nothing run there.
- `tests/mpx3-sound`'s `grep … | grep -qv` (px32's file): the same
  shape, a grep on both sides; left to its owner.
- The px27 sighting re-run.
- After px25's probe fix: a client late to its first `recv` (the answer
  already there) would still print `first recv data`; never seen.

## 7. Done-when

- [x] each flake's cause found and fixed, none by a weaker assertion,
      a retry or a longer timeout
- [x] each fix red-to-green under the load or witness that reproduced it
- [ ] CI green three times at the head (the PR body)
- [ ] `wolf/tools/lane-audit.sh pax px35 <PR>` exit 0
- To close when this merges: pax#29, pax#32 (pax#39 was closed at
  px25's merge).

## 8. The rebases, and the shas named again

The branch was rebased three times as trunk moved: onto `6316c51`
(px32), onto `feba3fc` (px25; this lane's probe commit dropped there)
and onto `c86ba5e` (px33, px33b). None of the three touched a file
this lane changes but `user/unix/unixprobe.c`. The trees kasumi ran
were cut before the last rebase, so their shas are no longer on the
branch; each is the same change as the commit beside it:

| what | as kasumi ran it | on the branch now |
|---|---|---|
| the prediction | `1cdf2c1` | `39a38ad` |
| tests/paxtcp-selftest, red | `2f9a7c3` | `9bcae04` |
| CI runs it | `e27079f` | `7174af3` |
| tools/paxtcp, the fix | `b57a758` | `76a9a21` |
| the renewal witness (`w1`) | `02a07c6` | `a200307` |
| kernel/arp, the fix | `88d8a1b` | `d54cc06` |
| kernel/net, the batch | `a01c17f` | `36b4de7` |
| the probe (`w2` = `cad6fc9`) | `cad6fc9` | dropped (px25's `e8931f4`) |
| the pipefail fix (`w3` = `7bb705d`, `w4` = `795ad71`) | `7bb705d` | `9b79510` |

After the second rebase the gauntlet ran on `w5` = `0aa5702` and after
the third on `w6` = `079f5bd` (this section's commit follows it and
changes only this note); their summaries and the CI runs are in the PR
body.
