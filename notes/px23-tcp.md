# px23 — TCP

Contract: px23's, `sprints/pax/23-tcp/px23-tcp.md` in wolffe-lang/wolf
(planning trunk, read 2026-10-11). Branch `px23` in pax, cut from pax
trunk `638ecaa` (px22 merged). §1–§3 are committed before the first
change to the kernel, the tools, the tests or `user/`.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22):
  not Linux, a BSD, lwIP, picoTCP, smoltcp, iPXE, SeaBIOS, OVMF, QEMU,
  the user-mode network library QEMU links, or glibc, and none found
  by a search; the refs clone's sparse checkout is never widened. Read
  or relied on: RFC 9293 (TCP), RFC 793 where 9293 defers to it,
  RFC 1122 §4.2, RFC 6298 (the retransmission timer), RFC 5681 (slow
  start, congestion avoidance, fast retransmit and fast recovery, as
  far as §3 argues), RFC 6528 (initial sequence numbers), RFC 5961 as
  RFC 9293 takes it in (a reset or a SYN inside the window), RFC 7323
  and RFC 2018 only to name the options refused, RFC 1071, RFC 791,
  RFC 792, RFC 862 (the echo service of the witnesses); the SipHash
  paper (Aumasson and Bernstein, 2012) for the keyed function RFC 6528
  asks for; the Linux man pages `tcp(7)`, `ip(7)`, `socket(7)`,
  `listen(2)`, `accept(2)`, `connect(2)`, `shutdown(2)`, `send(2)`,
  `recv(2)`, `bind(2)`, `getsockopt(2)`, `ioctl_tty(2)`/`ioctl(2)`
  for FIONBIO's number; the uapi headers already in the refs clone
  (`linux/in.h`, `linux/tcp.h`, `linux/socket.h`, `linux/net.h`,
  `asm-generic/socket.h`, `asm-generic/errno.h`,
  `asm-generic/ioctls.h`) and `Documentation/networking/ip-sysctl.rst`
  (the local port range; what Linux does with more time-wait sockets
  than it keeps); wolf's own `spec/11-os.md` (the `net_*` builtins);
  QEMU's documented options; and black-box runs: the witnesses under
  `strace` on Linux, and segments put on a netdev or a tap device and
  what comes back.
- No `poll`, `epoll` or `select`; no `sendfile`; no non-blocking
  descriptor beyond what px17 reads (`O_NONBLOCK`, `MSG_DONTWAIT`) and
  what the wolf-built witness's strace asks for (§2: `ioctl(FIONBIO)`
  on a socket and `accept4` with `SOCK_CLOEXEC|SOCK_NONBLOCK`), which
  answer `EAGAIN` and never wait. No window scaling, selective
  acknowledgement, timestamps, fast open or urgent data: each option
  is skipped by name with a counter, never sent, and the urgent
  pointer is not read. No fragmentation: the MSS comes from the MTU
  and is announced.
- No `region` is held open across a yield, a switch or a return to
  user mode (pax is on wolf 0.2.26 at `638ecaa` and has not adopted
  s223), and nothing here opens one at all. Nothing on the segment
  path allocates from the heap: a connection's buffers are frames from
  `kernel/frames`, bounded, counted and given back; state is words in
  `.bss`.
- No test binary is built with kasumi's glibc: the witnesses are built
  in the `px13-ubuntu` container (Ubuntu 24.04, glibc 2.39) or on the
  CI runner. No build on nomad-1.
- Nothing in pax names any use of the image beyond running it (the
  contract's word list). "Capture" means QEMU's `filter-dump` object
  writing a netdev's frames to a pcap file a test reads, or the
  reference side writing the frames that crossed its tap device.
- No `rm` outside `~/lanes/px23/` and this lane's private clones, on
  any host, `/tmp` included; no `git add -A`; nothing under
  `~/.claude`; no merge; no attribution trailers; no "seen red"
  without a run id, sha, path or digest. A planted break fails fast:
  the suite has a deadline of its own before any plant is pushed.

## 2. Inputs, verified (2026-10-11, from origin)

| input | found |
|---|---|
| pax trunk | `638ecaa` (px22 merged, PR #25), as the contract says; its trunk CI run 38110409863 is green. No sibling lane has landed: `kernel/wolf.pin` is 0.2.26, there is no `capabilities` line in `kernel/wolf.pkg`, no `/dev/tty0` |
| the descriptor shape | `kernel/files`: kind `K_INET` (8), an open file whose node is `T_INET << T_SHIFT` or'd with kernel/udp's socket number; `sock_kind(a, fd)` answers NOT_OPEN, NOT_SOCKET, UNIX or INET; `inet_open(a, s, flags)`; `nonblocking(a, fd)`; the last reference to the open file runs `pipe_ends(…, false)`, which calls `udp.close`. `kernel/files` imports `udp`, so the module that owns stream sockets is imported there too |
| the lines this lane replaces | `kernel/socket`'s `socket()` refuses every type but `SOCK_DGRAM` (`R_TYPE`, `ESOCKTNOSUPPORT` for type 1) and a protocol that is not 0 or 17; `no_connections` answers `listen`, `accept` and `accept4` with `EOPNOTSUPP`; `kernel/user` sends 43, 50 and 288 there; `shutdown` (48), `sendmsg` and `recvmsg` are -ENOSYS |
| waiting in a system call | a call answers `files.WAIT`; `kernel/user` rewinds the frame and `sched.block_pipe` (or `block_pipe_until(f, tick)`, by the process area's word 14) parks the thread until `sched.wake_pipes()`, which makes every such thread ready to run its call again. A pipe write keeps what it has written across waits in word 13. A system call runs with IF clear on its thread's kernel stack and may call `ip.send` |
| UDP's ports | `kernel/udp`'s 16 sockets are its port table and `pax_udp_state` word 1 its ephemeral cursor: both UDP's own |
| loopback | none below UDP: `udp.send_locked` hands a datagram for the station's address, 127/8 or 0.0.0.0 to `push` itself and never calls `ip.send`; `ip.send` to the station's own address goes to `arp.send`; `ip.input` drops a source in 127/8 or its own (`source`) and a destination in 127/8 (`other`); `ip.send` answers DOWN with no device |
| received ICMP errors | `icmp.input` counts a type-3 message `type` and drops it |
| locks | `sync` words 0–6 (console, heap, net, arp, ip, icmp, udp) of the eight in `boot/sched.S`; order `udp` → `ip` → `arp` → `net`; word 7 is free |
| modules | cannot import each other (E0303, px22's measurement); `kernel/netd` makes the calls between `ip`, `icmp` and `udp` |
| the clock and the timers | the PIT at 11932 counts: a tick is 10.000151 ms (`kernel/timer`, `timer.ticks()`); `sched.sleep(n)` and `sleep_current` wake at a tick; `block_pipe_until` gives a waiting call a deadline. The network's clock is `kernel/netd`'s second thread, `pax_net_clock`: `sched.sleep(10)` then `arp.tick()`, ten times a second. The time-stamp counter is read (`pax_rdtsc`) and calibrated per boot by `kmain_sockets` only for its own stamps. There is no timer wheel and no per-socket timer: TCP's are this lane's |
| threads | 16 slots (`sched.SLOTS`): the main thread, the idle thread, the network's two, and at most 12 processes |
| the reference side | `tools/linux-net` (a network namespace addressed as PAX is, a tap device, `tools/net-peer`'s `Peer` not strict at its other end, each command under strace) and `tools/pcap-net` over `tools/paxnet.py`'s model: both know ICMP and UDP only; `tests/mpx4-udp` stops a boot 20 s after its other end says FAIL |
| what the witnesses ask of Linux | written first (`user/net/tcp*.c`, `tcpwolf.lu`, `tcpwolfd.lu`, in the first commit after this one), built static in `px13-ubuntu` (gcc 13.3.0, glibc 2.39; the wolf ones by wolf 0.2.26 `--release`) and run under `strace -f` on kasumi's Linux 7.2.8 in a network namespace whose loopback also holds 10.0.2.15 and 10.0.2.2, ordinary sockets at the other end (`notes/px23/first-strace/`: `quick.py` the stand-in, `outputs.txt` what they printed). Beyond what px12–px22 answer, the C witnesses call **`listen`, `accept`, `shutdown`** and, on a stream socket, `socket`, `bind`, `connect`, `sendto`, `recvfrom`, `read`, `write`, `getsockname`, `getpeername`, `setsockopt` (`SO_REUSEADDR`; `TCP_NODELAY`, `TCP_SYNCNT`, `TCP_USER_TIMEOUT` at level 6), `getsockopt` (those, `SO_TYPE`, `SO_ERROR`), `close`, `dup`, `clone` (a fork), `wait4`, `rt_sigaction` (SIGPIPE ignored and restored). glibc 2.39's `send` and `recv` are `sendto` and `recvfrom`; **no `sendmsg`, `recvmsg`, `poll` or `accept4` in the C ones** |
| what wolf's runtime asks | `tcpwolf.strace`: `socket(AF_INET, SOCK_STREAM\|SOCK_CLOEXEC, 0)`, `setsockopt(SO_REUSEADDR)`, `bind`, `listen(fd, 128)`, **`ioctl(fd, FIONBIO, [1])`** on the listener and on every connected socket, `getsockname` with a 128-byte buffer, a blocking `connect` (the ioctl comes after it), `sendto(…, MSG_NOSIGNAL)`, **`accept4(fd, NULL, NULL, SOCK_CLOEXEC\|SOCK_NONBLOCK)`**, `recvfrom`. A call that finds nothing ready (`EAGAIN`) goes on to `epoll_create1`, `eventfd2`, a `clone3` thread, `futex` and `epoll_wait` (seen in a first version of the witness that accepted before its client had connected): none of that is here, so the wolf witnesses are written so that every accept and read finds what it asks for already there |
| what Linux answers, measured | `outputs.txt`. A stream socket of protocol 17 `EPROTONOSUPPORT`, of 9999 `EINVAL`; not connected: `getpeername` and `recv` `ENOTCONN`, `send` `EPIPE`, `accept` `EINVAL`, `shutdown` `ENOTCONN` (and the socket is marked shut all the same, a mark an accepted connection then inherits: the witness does it on a socket of its own); `bind` twice `EINVAL`, a held port `EADDRINUSE` **with or without `SO_REUSEADDR` when the holder has not set it**; a datagram socket may hold the same port; `listen` twice is allowed; `listen` with no port takes an ephemeral one; `connect` on a listener `EISCONN`; a connect to a port nobody listens on `ECONNREFUSED`, `SO_ERROR` then 0, and the same socket may connect again; connected: `connect` `EISCONN`, `listen`, `bind` and `accept` `EINVAL`; reads take bytes, not messages; `send` after `shutdown(SHUT_WR)` `EPIPE`, the other end reads 0 and may still send; `shutdown` twice is allowed; after the peer's close a first `send` succeeds and the next is `EPIPE` with `recv` still 0 (**a reset after the peer's FIN leaves `EPIPE`, not `ECONNRESET`**); a peer that closes with bytes unread resets: `recv` `ECONNRESET` once, then 0; a plain `write` after the reset is SIGPIPE (status 13), `EPIPE` when ignored; `TCP_SYNCNT` over 255 `EINVAL`; an unknown option at either level `ENOPROTOOPT`; a 2-byte `SO_REUSEADDR` `EINVAL`; **a port whose connection closed first on this side: `bind` `EADDRINUSE` (time-wait), allowed with `SO_REUSEADDR`, and `EADDRINUSE` again once another socket listens there**; **a backlog of 2 lets 3 clients in**, the others' SYNs go unanswered (`ETIMEDOUT` after `TCP_SYNCNT` 1: 3 s) |
| hosts | kasumi: QEMU 11.1.1, TCG only, podman with `px13-ubuntu`, `/home` 96% (44 GB free), no `tcpdump`. hasu: QEMU through `nix-shell -p qemu`, KVM. nomad-1: TCG. CI: QEMU 8.2.2 |
| wolf-lang#653, #675 | both open: the literal in `kernel/net` stays; wolf has no datagram builtins |

Drift from the contract's inputs line: none in the kernel. One thing it
did not say: wolf's runtime sets every socket non-blocking and waits
with epoll, a thread and a futex, so "a small wolf program that serves
one request" can run on PAX today only if it never has to wait.

## 3. Prediction (before the first change)

**Module layout.**

- `kernel/ip`: **loopback below IP.** `send_from(src, dst, protocol,
  payload, len)` (and `send`, which chooses the source): a destination
  that is this station's address or in 127/8 is composed as any
  datagram is and put on a queue of 64 frames (`loop`; a full queue is
  the named drop `loop-full`), never given to `kernel/arp`, with or
  without a device. `loop_take()` hands the oldest back; `input` takes
  a flag for a frame that came that way: its source may then be 127/8
  or the station's own and its destination 127/8, which from the wire
  stay `source` and `other`. Every protocol's checksum is made and
  verified over loopback as over the wire.
- `kernel/netd`: `deliver(frame, len, looped)`, the one place a
  datagram goes to its protocol (protocol 6 to `tcp.input`), and
  `drain()`, which delivers what waits on the loopback queue until it
  is empty, each frame with IF clear. Called at the end of every
  system call that may have sent (so a datagram or a segment sent to
  this machine has arrived before the call returns, as px22's did),
  and by the clock as a backstop. A call that answered "wait" is run
  again when the drain delivered anything. The clock thread now turns
  every tick: `arp.tick` every tenth turn, `tcp.tick` every turn.
- `kernel/udp`: **its own loopback retires onto IP's**: `send` always
  calls `ip.send_from`; the `loopback` counters go, and a looped
  datagram is counted as any received one. A looped datagram nobody
  takes now draws a port unreachable, to this machine itself.
- `kernel/tcp` (new): the control blocks, the listen queues, the
  time-wait table, the segments each way, the timers, the counters.
  It imports `ip`, `arp`, `frames`, `sched`, `sync`, `timer`,
  `uaccess`, `log`.
- `kernel/socket`: the stream calls beside the datagram ones;
  `kernel/files`: a kind for a stream socket (`K_TCP`) whose node is
  the control block's number, `tcp.close` at the open file's last
  close, `FIONBIO`; `kernel/user`: 43, 48, 50, 288 dispatched, the
  drain, `EPIPE` to SIGPIPE as px17's; `kernel/icmp`: a destination
  unreachable is parsed and handed back to `netd` for the protocol it
  quotes; `kernel/sync`: word 7, `tcp()`; `boot/net.S`: storage;
  `kernel/kmain_sockets.lu`: TCP started, the books, a wait for
  closing connections after each line.
- `user/net/`: `tcperr`, `tcpecho`, `tcpclient`, `tcploop`, `tcpbulk`,
  `tcpsoak`, `tcpend`, `tcpfull` (C, static glibc), `tcpwolf` and
  `tcpwolfd` (wolf). Tools: `tools/net-peer --tcp` (a TCP of its own
  at the other end of the cable, written from the RFCs, with the
  faults), `tools/tcp-host` (the host's end of `hostfwd=tcp`),
  `tools/linux-net` (the TCP script on the tap; a capture of the tap),
  `tools/paxnet.py` and `tools/pcap-net` (TCP in the model),
  `tools/mknet`. Tests: `tests/mpx4-tcp` (new) and its CI job;
  `tests/mpx4-udp` and `tests/mpx4-net` move (below). Predicted
  unchanged: `kernel/net`, `kernel/virtio`, `kernel/pci`,
  `kernel/arp`, `kernel/process`, `kernel/vm`, `kernel/sched`, every
  `mpx1`–`mpx3` suite's assertions.

**The control block.** 64 blocks of 64 words (`pax_tcp_conns`), one
table for everything that has TCP state: a socket a descriptor names
(closed, bound, listening, connecting, connected), a connection a
listener has not handed over yet, and a connection its process has
closed that is still finishing. A block holds the four addresses and
ports; the state; SND.UNA, SND.NXT, SND.WND, SND.WL1, SND.WL2, ISS,
the greatest window the peer ever gave; RCV.NXT, IRS, the window last
advertised; the peer's MSS; SRTT, RTTVAR, RTO, the segment being timed
and when it left, the backoff, the retransmissions so far and the
timer's tick; cwnd, ssthresh, the duplicate-ACK count and the recovery
point; the persist timer; up to four out-of-order intervals; the
pending error; the options a program set; its listener and the listen
queue's counts; and the frames of its two rings. **Buffers: 65,536
bytes to send and 65,536 received, 16 frames each**, taken when a
connection is established (or begun, for the end that connects) and
given back when the block is freed; a block that is only bound,
listening or half-open holds none. At most 64 × 32 = 2,048 frames
(8 MiB); a connection that cannot have its 32 frames is refused
(`ENOBUFS` to `connect`; a reset to a peer's handshake).

**The state machine.** The states are RFC 9293's: CLOSED (a block not
in use, or a socket not yet connected), LISTEN, SYN-SENT,
SYN-RECEIVED, ESTABLISHED, FIN-WAIT-1, FIN-WAIT-2, CLOSE-WAIT,
CLOSING, LAST-ACK, and TIME-WAIT — the last not in a block but in a
table of its own (below). Taken: active and passive open, the
three-way handshake, **simultaneous open** (a SYN in SYN-SENT moves to
SYN-RECEIVED and is answered SYN-ACK: accepted), simultaneous close,
half-close both ways. **Refused, by name:** data on a SYN (the SYN is
taken, its data is not: `syn-data`, RFC 9293 allows queueing it and
fast open is not here); a segment for LISTEN with ACK set (reset) or
with neither SYN nor RST (dropped); the urgent pointer (not read; the
byte stays in line, counted `urgent`); `MSG_OOB` (`EOPNOTSUPP`). A
reset is accepted only at exactly RCV.NXT; elsewhere in the window it
draws an ACK (RFC 9293 §3.10.7.4, RFC 5961), outside it nothing. A
SYN on a synchronized connection draws an ACK. Options: MSS read on a
SYN and announced on every SYN PAX sends (1460); end-of-list and
no-operation walked; window scale (3), SACK-permitted (4), SACK (5),
timestamps (8), fast open (34) and any other kind skipped, each with
a counter; a length under 2 or past the header drops the segment
(`option`).

**Out of order.** A segment that starts after RCV.NXT inside the
window is **queued**: its bytes go into the receive ring where they
belong and its range into a list of at most four intervals, merged as
they touch; one that would make a fifth is dropped (`ooo-dropped`).
Argued: dropping them all is correct too, but makes every loss cost
its sender a whole window; the ring is already there and the list is
28 words. Every out-of-order or duplicate segment is acknowledged at
once.

**The listen queue.** `listen(fd, n)`: a listener may have at most
min(n, 32) + 1 connections that are half-open or established and not
yet accepted, together (Linux measured: a backlog of 2 lets 3 in; its
split into two queues is not copied). **A full queue drops the SYN**
and counts it (`listen-full`); nothing is sent, so the client's
retransmitted SYN may find room: what Linux was seen to do. A
half-open connection holds a block and no frames; its SYN-ACK is
retransmitted 5 times (1, 2, 4, 8, 16 s; `tcp(7)`'s
`tcp_synack_retries`) and then it is freed. No SYN cookies.

**Sequence numbers.** RFC 6528: ISS = M + F(local address, local
port, remote address, remote port, key), M the tick counter in 4 µs
units (a tick is 2,500 of them), F SipHash-2-4 under a 128-bit key
drawn at start-up (RDRAND where the CPU has it, else the time-stamp
counter's mix `getrandom` uses).

**Retransmission** (RFC 6298). One timer a connection. RTO starts at
1 s; the first sample sets SRTT = R, RTTVAR = R/2; later ones RTTVAR =
3/4 RTTVAR + 1/4 |SRTT − R|, SRTT = 7/8 SRTT + 1/8 R; RTO = SRTT +
max(G, 4 RTTVAR) with G one tick (10 ms). One segment is timed at a
time and **Karn's rule** holds: no sample from a segment that was
retransmitted. A timeout retransmits the earliest unacknowledged
segment, doubles RTO (to at most 60 s, §2.5) and restarts the timer;
the backoff is kept until a new sample. **Departure, named:** the
floor on RTO is 200 ms, not §2.4's 1 s (a SHOULD): the link is a
virtual one whose round trip is under a tick, and a spurious
retransmission costs a duplicate, never correctness. **Giving up:** a
SYN after 6 retransmissions (`tcp(7)`'s default; 127 s) or
`TCP_SYNCNT`'s; data after 15 (`tcp_retries2`'s default) or when
`TCP_USER_TIMEOUT` milliseconds pass with data unacknowledged: the
connection is reset and its calls answer `ETIMEDOUT`. A zero window is
probed (one byte) from the persist timer, RTO first and doubling to
60 s, for as long as the peer answers.

**Congestion control: RFC 5681's, whole.** Slow start and congestion
avoidance (IW 3 × 1460 = 4,380 bytes, cwnd + min(acked, MSS) per ACK
under ssthresh and MSS²/cwnd per ACK above it), fast retransmit on the
third duplicate ACK and fast recovery (§3.2), cwnd back to one segment
after a timeout. Argued: "a link PAX shares with nothing" is true of
`-netdev socket` and false of the next one, RFC 9293 makes it a MUST,
and without fast retransmit every loss is a timeout. Named debts:
NewReno's partial-ACK rule (RFC 6582), SACK, window scaling (the
window is 65,535 at most), path MTU discovery, timestamps and PAWS,
keep-alives, a delayed ACK. **No delayed ACK**: every segment that
carries data, a SYN or a FIN is acknowledged at once (RFC 1122
§4.2.3.2's is a SHOULD); Nagle's algorithm is on by default and
`TCP_NODELAY` turns it off; both silly-window rules of RFC 1122
§4.2.3.3–4 are kept.

**The window** advertised is the room in the receive ring, 65,535 at
most, never shrunk; an update is sent when a read opens it by two
segments or half the ring.

**Time-wait.** 2 × MSL = 60 s, MSL taken as 30 s. The end that closes
first leaves, not a block, but an entry in a table of 16,384 (4,096
rows of four, 128 frames taken at start-up): the four addresses and
ports, SND.NXT, RCV.NXT and the tick it ends at. A segment for it is
answered as RFC 9293's TIME-WAIT says (a FIN again: ACK and the wait
restarts; a SYN above RCV.NXT: the entry goes and the SYN is taken,
RFC 1122 §4.2.2.13's MAY). A row that is full gives up its oldest
entry (`time-wait-evicted`: what Linux does past its own bound,
`ip-sysctl.rst`'s `tcp_max_tw_buckets`). **`bind` meanwhile**, as
Linux answered: `EADDRINUSE` for a port a time-wait entry, a
connection or another socket holds on a conflicting address; with
`SO_REUSEADDR` on the binder, allowed unless a socket listens there
or a socket that never set the option holds it.

**ICMP.** A destination unreachable of code 2 or 3 that quotes the SYN
of a connection in SYN-SENT ends the connect (`ECONNREFUSED`, RFC 1122
§4.2.3.9's hard errors); codes 0, 1 and 5, and any error for a
synchronized connection, are counted and change nothing. UDP's
sockets still see none (px22's debt, not paid here).

**The system calls**, each as Linux answered the witness (§2): `socket`
(type 1, protocol 0 or 6), `bind`, `listen`, `accept`, `accept4`
(flags `SOCK_CLOEXEC`, `SOCK_NONBLOCK`; others `EINVAL`), `connect`
(blocking; `ECONNREFUSED`, `ETIMEDOUT`, `EISCONN`, `ENOBUFS`),
`sendto`/`write` (blocks until every byte is in the send ring; `EPIPE`
and SIGPIPE; `MSG_NOSIGNAL`, `MSG_DONTWAIT`), `recvfrom`/`read`
(`MSG_PEEK`, `MSG_DONTWAIT`; 0 at the end of the stream), `shutdown`
(0, 1, 2), `getsockname`, `getpeername`, `setsockopt` and `getsockopt`
(`SO_REUSEADDR`, `SO_TYPE`, `SO_ERROR`; `TCP_NODELAY`, `TCP_SYNCNT`,
`TCP_USER_TIMEOUT`; every other `ENOPROTOOPT`, by name, once a
process), `ioctl(FIONBIO)`, `close`. `close` with bytes unread resets
the connection; with bytes unsent it returns at once and the block
finishes on its own (FIN after the data, 60 s at most in FIN-WAIT-2).
A blocked reader or acceptor cannot have its descriptor closed under
it (one thread a process; another process's copy holds the open
file): px22's argument, unchanged. `sendmsg`, `recvmsg`: still
-ENOSYS (no witness's libc calls them).

**Locking.** One lock, `sync.tcp()`, word 7, the last: every block,
the listen queues, the time-wait table and the composing frame are
under it; it is taken before `ip`, `arp` and `net` and never with
`udp`. The loopback queue is `ip`'s, under `ip`'s lock. No eighth is
needed until something must hold TCP's state across a call that takes
TCP's lock again, which the drain's shape (send, return, then
deliver) avoids.

**Bytes a second**, a 16 MiB transfer (the kernel's stamp around the
run-list line; `peer` is `tools/net-peer`'s Python TCP at the other
end, `user` the host's sockets through QEMU's network):

| | out of PAX | into PAX | loopback, both ends PAX |
|---|---|---|---|
| TCG, kasumi, native / release | 3 / 5 MB/s | 3 / 5 MB/s | 2 / 4 MB/s |
| TCG, CI, native / release | 1.2 / 2 MB/s | 1.2 / 2 MB/s | 0.8 / 1.5 MB/s |
| KVM, hasu, `peer` | 8 MB/s (the script's end is the slower) | 8 MB/s | 30 MB/s |
| KVM, hasu, `user` | 20 MB/s | 20 MB/s | |

Wrong by more than 2× either way is wrong.

**Under loss** (`net-peer` drops each frame, either way, with the
stated probability; 1 MiB each way at 1% and 5%, 256 KiB at 20%; TCG
on kasumi, native):

| loss | throughput | retransmissions by PAX (sending) |
|---|---|---|
| 1% | 300 KB/s to 1.5 MB/s | 8 to 40 a MiB |
| 5% | 60 to 300 KB/s | 40 to 150 a MiB |
| 20% | 3 to 15 KB/s | 80 to 250 for 256 KiB |

Every transfer digest-exact; none ends in `ETIMEDOUT`.

**Existing tests that move.** `tests/mpx4-udp`: U1 (kernel/udp's line
loses "loopback here"; kernel/tcp's line is new), U3 (the books gain
TCP's fields and `stack frames` grows by the loopback queue's 64, the
time-wait table's 128 and TCP's composing frame: 12 becomes 205), U4
(the refusal's text for a type that is neither a datagram nor a
stream socket), U7 (the `loopback` counters go: its 219 looped
datagrams are counted as received — 83 queued, 135 `full`, 1 `no-port`
whose port unreachable is now sent to this machine and counted by
`kernel/icmp` as received). `tools/pcap-net`'s counter lines follow.
`tests/mpx4-net`: the books' `stack frames`; `kmain_net` gains a ping
of the station's own address and of 127.0.0.1, answered without a
frame on the wire. No `mpx1`–`mpx3` assertion moves.

**The planted breaks, predicted red, and fast:** an acknowledgement
off by one (PAX acknowledges RCV.NXT + 1): the first data either way
stalls, `net-peer` says FAIL within its own 20 s deadline, and
`tools/pcap-net` fails the first segment whose acknowledgement names a
byte never sent: `tests/mpx4-tcp` red on every leg with a wire, and
its loopback lines too. A retransmission timer that never fires: the
handshakes and the clean transfers pass, the scripted faults (a
dropped SYN, a dropped segment) and the loss matrix stall, and the
other end's deadline stops each boot: red on the `peer` legs, green
on `none`. Each plant's run is over in under 25 minutes.

## What was built

1. **Loopback below IP** (`kernel/ip`, `kernel/netd`). A datagram of
   any protocol for the station's own address or for 127/8 is composed
   as any other and put on a queue of 64 frames; `netd.drain` delivers
   what waits there through the one path a frame from the wire takes
   (`netd.deliver`), each datagram with IF clear, and what a delivery
   sends in turn joins the queue. `kernel/user` drains after every
   system call (and runs a call again that had answered "wait" while
   its answer was on the queue), the clock every tick. No device is
   needed. `kernel/udp`'s own loopback retired onto it; the kernel
   pings 127.0.0.1 and its own address at start-up and both answer
   with no frame on the wire. Looped traffic is counted apart in
   `ip`, `icmp`, `udp` and `tcp`, so the counters a capture is held to
   stay the wire's.
2. **TCP** (`kernel/tcp`, 2,876 lines): what §3 predicted, with the
   differences the table below names.
3. **The calls** (`kernel/socket`, `kernel/files`, `kernel/user`):
   the stream forms of `socket`, `bind`, `connect`, `sendto`,
   `recvfrom`, `read`, `write`, `getsockname`, `getpeername`,
   `setsockopt`, `getsockopt`; `listen`, `accept`, `accept4`,
   `shutdown`; `ioctl(FIONBIO)`.
4. **Witnesses** (`user/net/`): `tcperr` (101 lines of errnos and
   behaviour over loopback), `tcploop`, `tcpecho` (and `fork`),
   `tcpclient`, `tcpbulk` (`send`, `recv`, `recv … nap`, `leave`,
   `loop`), `tcpsoak` (`to`, `loop`), `tcpend`, `tcpfull`, and in wolf
   `tcpwolf` (a listener, a client and one request in one process) and
   `tcpwolfd` (one request served to another machine): **the first
   wolf programs to speak TCP on PAX**. wolf's runtime waits with
   `epoll`, `eventfd`, a thread and `futex`, none of which PAX has, so
   both are written never to wait: `tcpwolfd` makes a second connect
   that the other end answers only once the request is in its listen
   queue.
5. **The other ends.** `tools/paxtcp.py`, a TCP of the tools' own
   (written from the RFCs), with faults that are a function of the
   frame — which way, where its bytes lie from the connection's first
   sequence numbers, which time through — so a run meets the same
   faults every time; `tools/net-peer --tcp`, its script (T1–T12);
   `tools/tcp-host`, ordinary sockets behind QEMU's user-mode network,
   whose TCP is a third implementation; `tools/linux-net --tcp`, the
   same script against Linux on a tap device, the reference every
   output is held to; `tools/pcap-net --tcp`, which rebuilds every
   segment PAX sent and holds it to its connection.
6. **Tests**: `tests/mpx4-tcp` (T0–T9; three ways, two tiers, two
   firmwares: 12 boots) and its CI job.

**Found on the way.**

- `tools/linux-net` started each program with SIGPIPE ignored (Python
  ignores it and `execve` hands that on), so on the reference side a
  write to a reset connection answered `EPIPE` where a program started
  by PAX, or by a shell, is killed. Fixed: the default is restored
  before the exec. px22's witnesses never wrote to a broken pipe.
- `tools/pcap-net`, first run over a TCP capture, said PAX "moves the
  window's right edge back": a time-wait entry's acknowledgement
  advertises a window of zero. Nothing can be sent to a connection
  whose FIN has been acknowledged, so the rule now stops there; the
  zero stays.
- The first `tcpbulk loop` printed its two lines in either order on
  Linux itself (the receiver said its line after sending the sender's):
  the witness was racing, not the kernel. The receiver now prints
  first.
- On nomad-1 (macOS) the `user` way's second soak ended at connection
  6,343 with `ENETUNREACH`: QEMU's network there answers a SYN with an
  ICMP net unreachable once the host has no local port left for its
  own connect (20,000 connections inside the host's time-wait), and
  PAX reported it as that. The limit is the host's; the `peer` way on
  the same host passed whole.
- A connection closed after a transfer at 20% loss was still
  retransmitting its FIN when `kmain_sockets` printed its books three
  seconds later (`tcp blocks 1`): the wait is thirty seconds now.

- A boot of `tests/mpx4-tcp` on kasumi lost one UDP datagram between
  QEMU's socket and `tools/net-peer` (the host's loss, not the
  cable's), and the script called PAX's next frame wrong because its
  IP identification had skipped one. The tools now rebuild a frame
  with the identification it carries and count the gap; the capture's
  check (`ident-gaps=0` in every capture kept) still holds PAX to
  consecutive numbers.
- **wolf's release tier took eight minutes over one kernel** (0.2.27
  measured; 0.2.26 was as slow, below).
  CI's `mpx2-heap` (twelve kernels) ran into its 60-minute limit twice
  (runs 38116208986 and 38120289555, cancelled there). Two functions
  of `kernel/tcp` did it, and nothing in their output was wrong: the
  keyed function behind the sequence numbers (two nested loops over
  six words, called from several places: `kmain_frames` 516 s where
  trunk takes 23 s) and `counters` (about 150 calls of `log.put` and
  `log.dec`, a loop each, inlined into one function: `kmain_sockets`
  503 s where trunk takes 66 s). Rewritten, the first without loops
  (`7158f92`) and the second as one function a line (`fae970d`):
  32 s and 18 s, the kernel's lines byte for byte the same. `perf`
  puts the time in the range pass (`wolf_wir::midend::rangeopt`). No
  standalone file reproduced it; wolf-lang#711 carries the two pax
  commits as its witness.
- `tests/mpx4-tcp`'s own check of a running boot read the serial log
  while QEMU was writing it and once took half a line, `ru` of
  `run 13:`, for output of command 12: a green boot stopped as red (on
  kasumi, once in some sixty boots). Replayed over every prefix of
  that log: 7 prefixes of 945 are read wrong. The check now leaves the
  last line out (`2cbab51`); the same replay finds none.

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| modules: `ip` (loopback), `netd` (`deliver`, `drain`), `udp` (its loopback retired), `tcp` new, `socket`, `files`, `user`, `icmp`, `sync`, `boot/net.S`, `kmain_sockets`; `sched` unchanged | so. `kernel/sched` is unchanged. Not predicted: `kernel/kmain_net` changed (its frame count); `kernel/icmp` and `kernel/udp` keep loopback counters of their own so the wire's stay exact; `tools/paxtcp.py` as a module of its own |
| 64 control blocks of 64 words | 64 blocks of **128** words (the 32 frame addresses of the two rings did not fit beside the rest) |
| buffers 65,536 each way, taken at establishment, given back at the end | so; every command's books end at `tcp blocks 0` and the frames it started with |
| the states; simultaneous open accepted; data on a SYN not taken; RFC 5961's reset and SYN rules | so, each exercised: `SYNs that cross` (port 9220: `1 simultaneous`), `1 syn-data`, `1 reset-challenged 1 syn-challenged 1 ack-ahead 1 no-ack` in every `peer` boot |
| out-of-order segments queued in at most four intervals | so (`out-of-order queued` in every `peer` boot; `out-of-order-dropped` 0: no test makes a fifth interval — **not exercised**) |
| listen queue min(n, 32) + 1; a full queue drops the SYN | so: `tcpfull` lets 3 of 6 in with a backlog of 2, as Linux does (`6 listen-full`) |
| ISS per RFC 6528 with SipHash-2-4 | per RFC 6528, with a keyed function **in HalfSipHash-2-4's shape** (32-bit words fit wolf's checked 64-bit arithmetic), written from memory and not checked against a test vector |
| RTO 1 s, then RFC 6298's with a 200 ms floor and a 60 s ceiling; Karn; SYN given up after 6, data after 15 or `TCP_USER_TIMEOUT` | so. Exercised: a SYN given up after `TCP_SYNCNT` 1 (`ETIMEDOUT` in 3 s), `TCP_USER_TIMEOUT` 3000 (`ETIMEDOUT`). **Not exercised:** the defaults 6 and 15 (minutes each), the 60 s ceiling |
| RFC 5681 whole | so (`fast retransmits` counted in every `peer` boot) |
| no delayed ACK; Nagle on, `TCP_NODELAY` off | so |
| time-wait 60 s in a table of 16,384 (4,096 rows of four) | 60 s in a table of **32,768**, an entry looked for in 16 consecutive slots: two soaks of 10,000 inside a minute would have filled the smaller one. `0 evicted` in every boot so far |
| `bind` in time-wait `EADDRINUSE`, allowed with `SO_REUSEADDR` unless a socket listens | so (`tcperr`) |
| ICMP: codes 2 and 3 for a SYN end the connect `ECONNREFUSED`; codes 0, 1, 5 counted and ignored | codes 2 and 3 so. **Code 1 wrong**: Linux ends the connect at once with `EHOSTUNREACH` (measured: `tcpend 10.0.2.2 9004`), and PAX now does the same (code 0: `ENETUNREACH`, by analogy, not measured against Linux) |
| one lock, word 7 | so |
| `stack frames` 12 becomes 205 | **333** (76 after loopback alone: 64 queue frames; then TCP's composing frame and 256 for the larger time-wait table) |
| `tests/mpx4-udp` moves: U1, U3, U4, U7 (the `loopback` counters go; a looped no-port draws a port unreachable) | U1, U3 and U4 moved. **U7 did not**: the `loopback` counters stayed, fed by `ip`'s queue instead of `udp`'s own push, and its numbers are the same. The looped port unreachable is sent (and counted by `kernel/icmp`'s loopback line), unlimited |
| `tests/mpx4-net`: the books' frames; a ping of itself in `kmain_net` | the frames (12 to 76). The self-ping went into `kmain_sockets` instead, where every way of two suites holds it |
| 16 MiB out of PAX / into PAX / over loopback: kasumi TCG native 3 / 3 / 2 MB/s, release 5 / 5 / 4; CI 1.2 / 1.2 / 0.8 and 2 / 2 / 1.5; hasu KVM `peer` 8 / 8 / 30, `user` 20 / 20 | **wrong, too low, by more than the 2× bar almost everywhere** (table below): kasumi native 7.0 / 10.6 / 15.4, release 6.9 / 11.2 / 33; CI native 5.0 / 7.4 / 12.9, release 4.7 / 8.0 / 26; hasu `peer` 7.0 / 11 / 117 (native) and 164 (release). Inside the bar: hasu `peer` out and in, hasu `user` (10–16 each way), kasumi release out |
| under loss: 1% 0.3–1.5 MB/s, 5% 60–300 KB/s, 20% 3–15 KB/s; PAX's retransmissions 8–40 a MiB, 40–150 a MiB, 80–250 for 256 KiB | out of PAX: 1% **2.6 MB/s** (above the range) with **7** retransmissions (just under it); 5% **0.34 MB/s** (just above) with 49 (inside); 20% 7 KB/s (inside) with 8 for 65,536 bytes, which is 32 for 256 KiB (**under** the range). The 20% transfer is 65,536 bytes, not 262,144: RFC 6298 keeps the backed-off RTO until a segment gets through at its first sending, which at 20% each way fails more often than not, so RTO climbs to seconds and a quarter-megabyte took four minutes. Every transfer exact; none ended in `ETIMEDOUT` |
| plant 1 (ACK + 1) red on every leg with a wire and on the loopback lines; plant 2 (no retransmission timer) red on `peer` legs, green on `none`; under 25 minutes each | both red in CI, the job over in **8 min 10 s** and **8 min 53 s** (§4). Each run shows the first boot only: once a boot fails no other is started, so "every leg" and "green on `none`" are **not shown** by CI. Plant 1 stalled `tcperr`, the first command, over loopback (no frame on the wire is needed to see it); plant 2 passed commands 1–5 (loopback, where nothing is lost) and stalled at `tcpfull`, the first that needs a retransmitted SYN |

### Measured: 16,777,216 bytes, and 10,000 connections

Bytes a second by the kernel's time-stamp counter around each program
(MB = 10^6 bytes), the range over the BIOS and UEFI boots; connections
a second likewise. `peer` is `tools/net-peer`'s Python TCP at the other
end, `user` the host's sockets behind QEMU's network.

| host, QEMU | tier | `peer` out / in | `user` out / in | loopback | connections `peer` out / in | loopback |
|---|---|---|---|---|---|---|
| kasumi, 11.1.1 TCG | native | 7.0–7.1 / 10.6 | 7.8 / 7.1–7.2 | 15.1–15.8 | 1,458–1,479 / 1,539–1,543 | 1,618–1,640 |
| | release | 6.8–7.0 / 11.1–11.2 | 15.2–15.8 / 10.3–10.8 | 32.6–35.1 | 3,199–3,225 / 3,111–3,195 | 8,343–8,467 |
| CI, 8.2.2 TCG | native | 5.0 / 7.3–7.6 | 6.5 / 7.5–7.6 | 12.7–13.2 | 973–1,006 / 1,051–1,102 | 1,588–1,613 |
| | release | 4.6–4.7 / 8.0 | 9.2–9.6 / 10.1–10.4 | 25.4–26.4 | 1,892–1,910 / 1,866–1,888 | 8,590–8,735 |
| hasu, 11.1.0 KVM | native | 4.7–7.0 / 7.4–11.1 | 13.4–16.3 / 10.4–16.2 | 74–117 | 992–4,360 / 612–4,578 | 29,898–39,158 |
| | release | 6.7–7.1 / 10.5–10.8 | 10.1–16.3 / 10.0–16.3 | 159–165 | 3,855–4,566 / 3,906–4,547 | 116,563–139,727 |
| nomad-1, 11.1.1 TCG | native | 12.9–13.2 / 14.9–15.2 | (host limit, above) | 12.5–13.3 | 1,603–1,636 / 1,713–1,743 | 2,012–2,105 |
| | release | 12.3–12.9 / 18.8–19.6 | | 26.3–27.7 | 3,348–3,442 / 3,338–3,397 | 10,999–11,624 |

kasumi: the gauntlet at `2cbab51`. CI: run 38127729228. hasu: `k5`'s
two rounds (the host was serving other work during the first, whose
native UEFI boots are the low ends). Against the peer the script's end is the
slower on every host (hasu's KVM gains nothing there); over loopback
both ends are PAX and KVM is 7 to 15 times TCG. A soak leaves 10,010
to 10,032 time-wait entries behind and evicts none.

### Measured: under loss

`tools/net-peer` drops (duplicates, delays, corrupts) each frame either
way by a function of the frame, so every boot meets the same faults in
a transfer out of PAX; into PAX the script's own retransmissions move
with its timing. kasumi, TCG, the gauntlet at `2cbab51`, four boots:

| | bytes | out of PAX | PAX retransmitted | into PAX | the script retransmitted |
|---|---|---|---|---|---|
| 1% dropped | 1,048,576 | 2,563–2,578 KB/s | 7 of 730 segments | 907–2,792 KB/s | 10–15 |
| 5% dropped | 1,048,576 | 337–338 KB/s | 49 of 772 | 224–396 KB/s | 58–69 |
| 20% dropped | 65,536 | 7 KB/s | 8 of 60 | 62–64 KB/s | 14–15 |
| 1% dropped, 5% duplicated, 5% reordered, 2% corrupted | 1,048,576 | 6,395–6,683 KB/s | 8 of 731 | 353–754 KB/s | 26–54 |

Every transfer is held to its length and CRC-32 at both ends. With
duplicates on the wire PAX is faster than with loss alone: a
duplicated segment's two acknowledgements feed fast retransmit.

## What moved at the rebase (trunk `0cc43be`: wolf 0.2.27, lupin 0.1.50)

- **The merge.** One conflict, `docs/SOURCES.md` (px21a's section and
  this lane's: both kept). `ci.yml`, `CHANGELOG.md`, `README.md`,
  `boot/net.S`, `kernel/README.md`, `kernel/files/files.lu` (px21a's
  `/dev/tty0` and `/dev/console` beside the stream socket's kind) and
  `kernel/user/user.lu` merged by themselves.
- **No line of the kernel had to change for 0.2.27's language.** No
  region is opened anywhere in this lane's code, so the new region
  rule changes nothing here; no package of this lane declares C.
- **The compiler's time did not move with the toolchain**; it was
  found after the rebase, in CI, and cost two rewrites (above,
  wolf-lang#711). The gauntlet before the rebase, under 0.2.26, was
  already as slow and this lane had not asked why: `mpx1` 2,049 s and
  `tests/mpx4-tcp`'s build 652 s at `a299fbe`, 316 s and 105 s at
  `2cbab51`. No CI run of this branch finished before the rebase.
- **The wolf-built witnesses** are built by 0.2.27's hosted runtime
  now. Re-taken on Linux at the head (`linux/3.strace`,
  `linux/43.strace`): `tcpwolf` makes the same 23 calls it made built
  by 0.2.26, none of `poll`, `epoll`, `eventfd`, `futex` or `clone3`,
  because neither program ever waits. On PAX the -ENOSYS census of all 43 commands is
  what it was: 273 (`set_robust_list`) and 334 (`rseq`), once a
  process, nothing else. Neither witness has the shapes of
  wolf-lang#660 or #665 in it as far as this lane can tell from their
  titles (**not verified** against the issues' own witnesses).
- **Sizes and pins.** Every kernel is bigger (the heap and the
  freestanding runtime are linked into each); the pins this lane
  holds did not move for it: `stack frames 333` in `kmain_sockets`
  and 76 in `kmain_net` before and after. The initramfs sizes are
  measured per build, not pinned.
- **Throughput against the toolchain**, kasumi TCG, the same suite at
  `a299fbe` (0.2.26) and at `2cbab51` (0.2.27): native out 6.7–6.9
  then 7.0–7.1 MB/s, in 10.6–10.9 then 10.6, loopback 15–16 then
  15.1–15.8; release loopback 31–35 then 32.6–35.1: inside the
  boot-to-boot spread, no movement to report.
- **Found after the rebase, not caused by it:** the books' patience
  (three seconds to thirty), the host's lost datagram, the live
  check's half line (all above).

## 4. Evidence index

Files are under `notes/px23/`. Verified means this lane ran it and
read the result; a digest cut short carries `…`.

- **The straces of the witnesses on Linux.** Before the design:
  `first-strace/` (`quick.py` at the other end, `outputs.txt`). At the
  head, by `tools/linux-net --tcp` against the real script on a tap
  device, in `px13-ubuntu` on kasumi: `linux/<k>.strace`, `.out` and
  `.rc` for the 43 commands of `user/mpx4-tcp.run` (what
  `tests/mpx4-tcp` holds PAX to; long straces cut by the tool),
  `linux/linux.txt` (each command's set of calls), `linux/peer.txt`
  (the script's account of Linux), `linux/net.txt` (the programs'
  digests). The tap's capture is not kept (`linux/tap.txt` has its
  frame count and digest). What wolf's runtime
  asks of Linux once a call must wait: `probes/wolfnet.strace`.
- **The captures and the checker's verdicts.** A run of
  `tests/mpx4-tcp` is 8 captures (2 tiers × 2 firmwares × `peer`,
  `user`). Against the peer about 302,000 frames (151,280 from PAX in
  the one kept in part), against QEMU's network about 297,000; every
  frame PAX sent is rebuilt from its meaning and equal byte for byte,
  every IP and TCP checksum recomputed (906,102 in one capture), every
  segment held to its connection (sequence and acknowledgement
  arithmetic, the window's right edge, what may follow a FIN or a
  reset), and the kernel's 77 counters held to the capture's:
  `kasumi-g3-mpx4-tcp.checks.txt`; the digests in
  `kasumi-g3-mpx4-tcp-runs.txt`. A capture is 57–66 MB, so the
  repository carries one head, `kasumi-g3-native-bios-peer.head.pcap`
  (the first 4,000 frames of `314759a79e08…`; `tools/pcap-net --tcp`
  passes it as it is: run on nomad-1). CI's are in each run's
  artifact.
- **Counters.** Every boot's eight `tcp:` lines, held to the capture
  (T6) and to exact numbers where the script fixes them (T7):
  `kasumi-g3-mpx4-tcp.out`. Whole transcripts:
  `kasumi-g3-native-bios-peer.transcript.txt` (with the script's
  account, `…peer.net-peer.txt`), `…user.transcript.txt` (and
  `…user.tcp-host.txt`), `…none.transcript.txt`.
- **The soaks.** 10,000 connections into PAX and 10,000 out on every
  `peer` and `user` boot, 10,000 over loopback on every boot (T8);
  after every run-list line the frames free equal to before and the
  books `heap pages 0, live blocks 0, net frames 66, stack frames
  333, open files 0, pipes 0, sockets 0, datagrams waiting 0, tcp
  blocks 0` (T3): every block, port, buffer and frame came back. The
  time-wait entries a soak leaves are counted in the books and are
  gone 60 s later.
- **Under loss.** `kasumi-g3-mpx4-tcp-loss.txt` (32 lines: 8 transfers
  × 4 boots), hasu's `hasu-kvm-k5-mpx4-tcp-*.loss.txt`. The scripted
  single faults (a dropped SYN, SYN-ACK, final ACK, data segment, FIN;
  a duplicate; a reset out of window and one in it; SYNs that cross)
  are steps T9 and T10 of the script's account, the malformed and
  stray segments among T10's, how a connection ends its T8 and the
  loss matrix its T11, in `…peer.net-peer.txt`.
- **Planted breaks, red in CI, failing fast.**
  - an acknowledgement off by one (`8f5b150`): run **38128347823** —
    `mpx4-tcp` alone red, every other job green; the job took 8 min
    10 s, 305 s of it the boot (`qemu-halt: NOT HALTED: stopped by
    tests/mpx4-tcp: the serial log had not grown for 300 s (after
    command 0 of the list)`): `ci-38128347823-mpx4-tcp-plant-8f5b150.txt`.
    Reverted in `2cb2034`.
  - a retransmission timer that never fires (`a7eeeb3`): run
    **38128979822** — `mpx4-tcp` red in 8 min 53 s (`… not grown for
    300 s (after command 5 of the list)`):
    `ci-38128979822-mpx4-tcp-plant-a7eeeb3.txt`. Reverted in `9523d7f`.
  - Both were rehearsed on kasumi first (native, BIOS, small sizes):
    red after 304 s of boots each. The rehearsals' logs are not kept.
- **Boots.** `tests/mpx4-tcp` is 12 (2 tiers × 2 firmwares × `peer`,
  `user`, `none`):
  - kasumi, QEMU 11.1.1, TCG: 12 in the gauntlet at `2cbab51` (100
    PASS), 12 in the gauntlet at `a299fbe` before the rebase (100
    PASS), and some sixty more in partial runs while the test was
    written;
  - hasu, QEMU 11.1.0, **KVM**: 24 at `2cbab51`'s images in two rounds
    (`hasu-kvm-k5.log`, 100 PASS and 0 FAIL each; the images' digests
    in its `runs.txt` are the gauntlet's — the log's own `sha:` line
    names that clone's stale checkout, the head before the rebase, and
    is to be ignored); before that 36 on the
    rebased kernel (`hasu-kvm-k3.log`) and 36 before the rebase, with
    36 of `mpx4-udp` and 60 of `mpx4-net` (`k2`), and 24 and 40 of
    those two after it (`hasu-kvm-k4.log`: 97 and 125 PASS a round);
  - nomad-1, QEMU 11.1.1, TCG on macOS arm64: 12 at `2cbab51`'s
    images: the 4 `peer` and 4 `none` boots pass whole (80 PASS); the
    4 `user` boots fail at the host's limit named above
    (`nomad-1-tcg-mpx4-tcp.out`);
  - CI, QEMU 8.2.2, TCG: 12 a run.
- **The gauntlet** on kasumi at `2cbab51` (strict env, QEMU 11.1.1
  TCG, wolf 0.2.27, clang 23.1.1; user programs built in
  `px13-ubuntu`): `kasumi-g3.summary`, `kasumi-g3.versions`. The head
  differs from `2cbab51` by the two plants, their reverts and these
  notes.
- **CI green**: run 38121599881 at `5fb1724` and run 38127729228 at
  `2cbab51` (21 jobs each; `mpx4-tcp` 102 PASS in 11 min 36 s,
  `ci-38127729228-mpx4-tcp-2cbab51.txt`); at the head, the PR names
  the run.

**Not verified, plainly.**

- The keyed function behind the initial sequence numbers is written
  from memory in HalfSipHash-2-4's shape and was never held to a test
  vector. It is keyed and takes all four addresses and ports; that it is
  HalfSipHash is not claimed, and how well it mixes was not measured.
- Not exercised by any test: a fifth out-of-order interval
  (`out-of-order-dropped`), giving up a SYN after the default 6
  retransmissions or data after 15, RTO's 60 s ceiling, a time-wait
  eviction, a time-wait entry's own expiry seen from outside (the
  books count the entries; no test waits the minute and looks),
  `ENETUNREACH` from an ICMP code 0, the keep-going path of a block
  that cannot have its frames (`no-frames`).
- Each plant is shown red on the first boot only (native, BIOS,
  `peer`). The prediction's "green on `none`" for plant 2 was not run.
- The `user` way never passed on nomad-1 (macOS): the host runs out of
  local ports under QEMU's network. It passes on kasumi, hasu and CI.
- Congestion control is held to its counters and to transfers that
  end exact; no test checks cwnd's value step by step against
  RFC 5681.
- hasu's rounds ran images built on kasumi; nothing was built on hasu
  or nomad-1.
- wolf-lang#711 has no reduced witness.

**What the next lane inherits (px24: `poll` and the rest).**

- What wolf's hosted runtime asks for as soon as a call must wait
  (`probes/wolfnet.strace`), all refused here with -ENOSYS:
  `epoll_create1`, `epoll_ctl`, `epoll_wait`, `eventfd2`, `poll`,
  `clone3` (a thread), `futex`; it also calls `prctl` and `getrandom`
  with `GRND_INSECURE` (what PAX answers those two was not run). Until they exist a wolf program
  on PAX speaks TCP only if it never waits, which is how `tcpwolf`
  and `tcpwolfd` are written; lobo's runtime will wait.
- Also asked by that runtime and not here: `SO_REUSEPORT` (any option
  this lane does not name answers `ENOPROTOOPT`, by name, once a
  process) and `writev` (no dispatch for it in `kernel/user`: -ENOSYS
  for any descriptor). `sendmsg` and `recvmsg` are still -ENOSYS.
- Here already, beyond the contract's letter, because the wolf
  witnesses' strace shows them: `ioctl(FIONBIO)`, `accept4` with
  `SOCK_NONBLOCK` and `SOCK_CLOEXEC`, `MSG_DONTWAIT`: a non-blocking
  call answers `EAGAIN`. Nothing waits on readiness.
- TCP's debts, named in §3: NewReno's partial acknowledgements, SACK,
  window scaling (so 65,535 bytes of window and the throughput
  above), timestamps and PAWS, keep-alives, a delayed ACK, path MTU
  discovery, SYN cookies; one thread a process, so a descriptor is
  never closed under a blocked call.
- UDP's sockets still see no ICMP error (px22's debt, not paid here).
- 64 connections at once, 65,536 bytes each way: a server with more
  clients than that refuses the 65th (`no-block`).

**To close or correct when this merges.** No issue in pax names this
work. wolf-lang#711 (opened by this lane) stays open: it is the
compiler's. To correct: this note's §3 said `tests/mpx4-udp`'s U7
would move (it did not), ICMP code 1 would be ignored (Linux ends the
connect), the time-wait table would hold 16,384 (it holds 32,768) and
every throughput figure (too low).

## 5. Done-when

Branch `px23`; PR pax#27 open, unmerged, five sections by name, commit
shas as bullets, a test checklist. CI green at the head (the PR names
the run). `wolf/tools/lane-audit.sh pax px23 27` run by this lane, its
exit status in the PR. The lane's clones, images and scratch on
kasumi, hasu and nomad-1 are removed and no process of the lane is
left. Nothing is merged and nothing is closed.
