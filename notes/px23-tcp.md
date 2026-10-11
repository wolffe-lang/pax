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
