# px22 — UDP and the socket syscalls

Contract: px22's, `sprints/pax/22-udp-and-sockets/px22-udp-and-sockets.md`
in wolffe-lang/wolf (planning trunk, read 2026-10-10). Branch `px22` in
pax, cut from pax trunk `597aff6` (px21 merged). §1–§3 are committed
before the first change to the kernel, the tools, the tests or `user/`.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22):
  not Linux, a BSD, lwIP, picoTCP, smoltcp, iPXE, SeaBIOS, OVMF, QEMU,
  the user-mode network library QEMU links, or glibc, and none found
  by a search; the refs clone's sparse checkout is never widened. Read
  or relied on: RFC 768 (UDP), RFC 791, RFC 792, RFC 862 (the echo
  service the witness and the capture's checker stand on), RFC 1035
  (the DNS message, for the resolver witness and the script that
  answers it), RFC 1071, RFC 1122 §4.1 (what a host does with UDP);
  the Linux man pages `socket(2)`, `bind(2)`, `connect(2)`,
  `sendto(2)`/`send(2)`, `recvfrom(2)`/`recv(2)`, `getsockname(2)`,
  `getpeername(2)`, `getsockopt(2)`, `listen(2)`, `accept(2)`,
  `udp(7)`, `ip(7)`, `socket(7)`, `netdevice(7)` and `tuntap` as the
  kernel's `Documentation/` gives it (the reference side's interface
  only); the uapi headers already in the refs clone (`linux/in.h`,
  `linux/socket.h`, `asm-generic/socket.h`, `asm-generic/errno.h`,
  `linux/if_tun.h`, `linux/if.h`, `linux/route.h`, `linux/sockios.h`),
  the syscall table and `Documentation/networking/ip-sysctl.rst` (the
  local port range); QEMU's documented options; and
  black-box runs: the witnesses under `strace` on Linux, and frames
  put on a netdev and what comes back.
- No TCP; no `poll`, `epoll` or `select`; no non-blocking descriptor
  beyond the `O_NONBLOCK` and `MSG_DONTWAIT` px17 already reads; no
  socket option but the ones the witnesses' strace asks for (§3 names
  them), every other refused by name and logged once a process; no
  DHCP; no fragmentation and no reassembly either way: a datagram
  over 1472 bytes is `EMSGSIZE`.
- No `region` is held open across a yield, a switch or a return to
  user mode (pax has not adopted s223), and nothing here opens one at
  all. Nothing on the datagram path allocates from the heap: a
  socket's receive queue is frames from `kernel/frames`, and state is
  words in `.bss`.
- No test binary is built with kasumi's glibc: the witnesses are built
  in the `px13-ubuntu` container (Ubuntu 24.04, glibc 2.39) or on the
  CI runner. No build on nomad-1.
- Nothing in pax names any use of the image beyond running it (the
  contract's word list). "Capture" means QEMU's `filter-dump` object
  writing a netdev's frames to a pcap file a test reads.
- No `rm` outside `~/lanes/px22/` and this lane's private clones, on
  any host, `/tmp` included; no `git add -A`; nothing under
  `~/.claude`; no merge; no attribution trailers; no "seen red"
  without a run id, sha, path or digest.

## 2. Inputs, verified (2026-10-10, from origin)

| input | found |
|---|---|
| pax trunk | `597aff6` (px21 merged, PR #24), as the contract says. Its trunk CI run 38098730026 was still queued when this was written (the org's 20 jobs); px21's PR head was green in 38097227504 |
| the seam | `ip.send(dst, protocol, payload, len)` copies `len` bytes from a kernel address into its one frame under `sync.ip()` and answers `arp.SENT`, `arp.QUEUED`, `arp.DROPPED`, `arp.FAILED`, `ip.SIZE` or `ip.DOWN`. `ip.input(frame, len)` answers `(what, ihl, total)` with `what` DROP, TO_ICMP or NO_PROTOCOL; `kernel/netd` calls `icmp.unreachable(frame, ihl, total)` for the last. Protocol 17 is today NO_PROTOCOL, counted `protocol` |
| who calls `ip.send` | only kernel threads so far (`netd`, `kmain_net`). A system call runs with IF clear on its thread's kernel stack; `ip.send`, `arp.send` and `net.send` take spinlocks with IF saved and never switch, so they can be called from one |
| the three places that pin protocol 17 | `tests/mpx4-net` P4 (`9 protocol`: five of them tools/net-peer's B7 datagrams of protocol 17 and two its silent ones) and N8 (`protocol` at least 1: this script's own UDP datagrams through `hostfwd`); `tools/paxnet.py`'s `judge_ip` (`h[9] != 1` is `unreachable` or `silent`). All three move |
| port unreachable | `icmp.unreachable` writes code 2 and has no argument for another |
| checksums | no offload taken (px20); `ip.sum(a, len)` is the RFC 1071 sum over one run of bytes: a pseudo-header needs a sum that takes a start value, or its own loop |
| loopback | none: `ip.send` to 10.0.2.15 routes on-link and `arp.send` asks for an address nobody answers; `ip.input` drops a source of 127/8 or its own address (`source`) |
| the address | `kmain_net`'s constants 10.0.2.15, 255.255.255.0, 10.0.2.2 to `ip.start`; nothing on the command line |
| locks | `sync` words 0–5 (console, heap, net, arp, ip, icmp) of eight; order `ip` → `arp` → `net`; `icmp` never held across a call into `ip` |
| **can wolf modules import each other?** | **No — tested, where px21 assumed.** Two modules that `use` each other are refused by wolf 0.2.26 with `error[E0303]: this import completes a cycle`, exit 2, on the native and release tiers, hosted and `--target x86_64-unknown-none` alike (`notes/px22/import-cycle.txt`). So the layering is one-way: what `kernel/netd` does for `ip` and `icmp` (the lower module answers, the caller above makes the next call) is the only shape there is |
| the descriptor table | `kernel/files`: 32 descriptors a process (kind, node, open file + 1, flags) in the process area; 64 open files (`pax_ofiles`: references, kind, node, offset, status flags) shared across `dup`, `fcntl(F_DUPFD)` and a child's copy of the table (`inherit`), dropped by `close`, `exec_close` (O_CLOEXEC is the descriptor's) and `close_all`; the last reference runs `pipe_ends(…, false)`, the hook a pipe's buffers are freed from. `socketpair`, `sendto` and `recvfrom` exist for AF_UNIX pairs (px17) and answer -ENOTSOCK for anything else |
| waiting in a system call | a call answers `files.WAIT`; `kernel/user` rewinds the frame to the `syscall` instruction and `sched.block_pipe` parks the thread until `sched.wake_pipes` (every waiter runs its call again). No wait has a deadline: `sleep_current` is the only timed one and it does not run the call again |
| process area words | 0–15 scalars (14 and 15 unused), 16–143 the descriptors, 256–511 the signal words; 144–255 unused |
| what the witnesses ask of Linux | written first (`user/net/` in the first commit after this one), built static in `px13-ubuntu` (gcc 13.3.0, glibc 2.39-0ubuntu8.9) and run under `strace -f` in a network namespace of their own on kasumi's Linux 7.2.8 (`notes/px22/first-strace/`: `quick.py` is the stand-in for the other end, `outputs.txt` what they printed). Beyond what px12–px17 already answer, the calls are **`socket`, `bind`, `connect`, `sendto`, `recvfrom`, `getsockname`, `getpeername`, `setsockopt`, `getsockopt`, `listen`, `accept`** and, already present, `read`, `write`, `close`, `dup`, `fcntl`, `fstat`, `lseek`, `clone` (a fork), `wait4`. glibc 2.39's `send` and `recv` are `sendto` and `recvfrom` with no address; **no `sendmsg`, `recvmsg`, `poll` or `ioctl` appears**. The one socket option set is `SO_RCVTIMEO_OLD` (level 1, option 20, a 16-byte `timeval`); the one read is `SO_TYPE` (option 3) |
| what Linux answers, measured | `outputs.txt`: unknown family `EAFNOSUPPORT`; a type AF_INET lacks (`SOCK_RDM`) `ESOCKTNOSUPPORT`; a type past the last (`77`) `EINVAL`; `SOCK_DGRAM` with `IPPROTO_TCP` `EPROTONOSUPPORT`; unknown option or level `ENOPROTOOPT`; `listen` and `accept` on a datagram socket `EOPNOTSUPP`; `bind` twice `EINVAL`, a short address `EINVAL`, a wrong family in the address `EAFNOSUPPORT`, an address that is not local `EADDRNOTAVAIL`, a port another socket holds on the same address or on 0.0.0.0 `EADDRINUSE` (a different specific address: allowed); `send` and `write` with no peer `EDESTADDRREQ`; 65508 bytes `EMSGSIZE`; destination port 0 `EINVAL`; an unconnected `getpeername` `ENOTCONN`; an empty queue with `MSG_DONTWAIT` or `O_NONBLOCK`, or when `SO_RCVTIMEO` runs out, `EAGAIN`; a datagram longer than the buffer cut to it, the rest gone, its full length returned under `MSG_TRUNC`; a connected socket hears only its peer; a first send binds 0.0.0.0 and a port in 32768–60999; `connect` to 10.0.2.2 names the local address the route gives; a datagram to 127.0.0.1 arrives from 127.0.0.1 and one to the machine's own address from that address; 200 datagrams of 1000 bytes to a socket nobody reads: 92 kept |
| wolf's `net_*` builtins and UDP | **they do not reach it.** wolf 0.2.26's `spec/11-os.md` lists nineteen: `net_listen`, `net_listen_with`, `net_listen_unix`, `net_adopt_listener`, `net_port`, `net_accept`, `net_connect`, `net_connect_unix`, `net_read`, `net_read_bytes`, `net_write`, `net_write_bytes`, `net_writev`, `net_writev_head`, `net_nodelay`, `net_wait`, `net_deadline`, `net_close`, `net_fetch` — stream sockets (TCP and AF_UNIX) only; the words "UDP" and "datagram" appear nowhere in it. Missing for a wolf witness: a datagram socket to bind, a send that names its destination, a receive that says who sent. To be filed in wolf-lang; no wolf-built witness in this lane |
| hosts | kasumi: QEMU 11.1.1, TCG only (no `/dev/kvm`), podman with `px13-ubuntu`, `/home` 96% (41 GB free). hasu: QEMU 11.1.0 through `nix-shell -p qemu`, KVM. nomad-1: QEMU 11.1.1, TCG. CI: QEMU 8.2.2. In a rootless `podman run --privileged` on kasumi a process can `unshare` a network namespace and make a tap device by `ioctl` alone (measured: no `ip` in the image, none needed) |
| wolf-lang#653 | still open; the literal in `kernel/net` stays |

Drift from the contract's inputs line: none in the kernel. One fact it
left open is settled (modules cannot import each other).

## 3. Prediction (before the first change)

**Module layout.**

- `kernel/udp` (new): `input(frame, ihl, total)` (the datagram judged,
  demultiplexed and copied to a socket's queue; its answer tells
  `kernel/netd` whether a port unreachable is due); the pseudo-header
  checksum; the sockets and their ports; `send`; loopback; counters.
  It imports `ip`, `arp`, `frames`, `sched`, `sync`, `uaccess`, `log`,
  `timer`.
- `kernel/socket` (new): the system calls — the addresses read and
  written, the errno of each refusal, the options, the wait. It
  imports `files` and `udp`.
- `kernel/files`: a descriptor kind for an AF_INET socket whose node
  is the socket's number; the last close of its open file calls
  `udp.close`. `kernel/user`: the dispatch (41, 42, 43, 44, 45, 49,
  50, 51, 52, 54, 55, 288; `read` and `write` on a socket), a
  refusal's name from `socket.why`. `kernel/sched`: a pipe wait with
  a deadline. `kernel/ip`: `TO_UDP`. `kernel/icmp`: `unreachable`
  takes the code. `kernel/netd`: protocol 17 to `udp.input`.
  `kernel/sync`: word 6, `udp()`, taken before `ip()`. `boot/net.S`:
  storage.
- `kernel/kmain_sockets.lu` (new): `kmain_boreutils`'s run list over
  the network `kmain_net` starts, the books after every line, the
  counters at the end.
- `user/net/` (new): `sockerr`, `udploop`, `udpecho`, `udpclient`,
  `udpsoak`, `udpfill`, `resolve` (C, static glibc) and `say.h`.
  Tools: `tools/mknet` (builds them); `tools/net-peer` (a UDP script:
  the echo client, the reversing server, the DNS server, the malformed
  and the unwanted; and the wire behind an interface, so the same
  script plays to QEMU's socket netdev and to a Linux tap);
  `tools/linux-net` (the reference side: the run list on Linux in a
  network namespace addressed as PAX is, with that script on a tap);
  `tools/udp-host` (the host's end of `-netdev user`: a server on
  127.0.0.1 and a client to the forwarded port); `tools/paxnet.py` and
  `tools/pcap-net` (UDP in the model); `tools/gateway-probe` (what
  QEMU's DNS answers on this host). Tests: `tests/mpx4-udp` (new) and
  its CI job; `tests/mpx4-net` (below). Predicted unchanged:
  `kernel/net`, `kernel/virtio`, `kernel/pci`, `kernel/arp`,
  `kernel/process`, `kernel/vm`, every `mpx1`–`mpx3` suite's
  assertions.

**The socket object and the descriptor table.** 16 sockets
(`pax_udp_socks`), each: its local address and port (0: not bound),
whether the address was bound by name, its peer (connected or not),
its receive timeout in ticks, and a 65,536-byte ring in 16 frames
taken at `socket` and given back when the socket goes. A socket is
what an open file's node names, so:

- `dup`, `dup2`, `dup3`, `fcntl(F_DUPFD)`: one more descriptor on the
  same open file, the same socket; `O_NONBLOCK` is the open file's
  (shared), `FD_CLOEXEC` the descriptor's;
- `fork`: the child's table names the same open files (`inherit`), so
  parent and child share the socket and its queue: a datagram is read
  by whichever reads first;
- close-on-exec: `socket(… | SOCK_CLOEXEC)` and `fcntl(F_SETFD)`;
  `execve` drops the descriptor, and the socket with the last one;
- `close`: the last reference to the open file frees the socket: its
  port is free at once, what its queue held is dropped (counted
  `closed`), its 16 frames go back. A process's end closes them all.
- **close with a blocked reader.** A process has one thread and no
  clone shares a descriptor table, so the descriptor a receive is
  blocked on cannot be closed while it is blocked: only its own
  process could. What can be closed under a blocked reader is
  *another* reference to the same socket (a parent's copy, a
  duplicate), and that frees nothing: the reader's reference holds
  the socket. So no close wakes a receive, and none needs to. What
  ends a blocked receive on a PAX with no signals: a datagram; the
  socket's receive timeout (`SO_RCVTIMEO`, the one option the
  witnesses set: the call answers `EAGAIN` at the tick after the
  deadline); and nothing else — a receive with no timeout and no
  sender waits for good, as it does on Linux with no signal sent.

**The port table** is the sockets themselves (16 at most, so 16 ports
at most): `bind` holds a port to one address or to all. `EADDRINUSE`
when another socket holds the same port on the same address, or
either of the two holds it on 0.0.0.0 (measured on Linux: 127.0.0.1
and 10.0.2.15 may share a port; no `SO_REUSEADDR`, which no witness
sets). Addresses a socket may bind: 0.0.0.0, the station's own,
anything in 127/8; any other `EADDRNOTAVAIL`. **Ephemeral ports:**
32768 to 60999 (`ip(7)`'s default range, which the witnesses print as
"ephemeral"), taken by a first send or a `connect` on a socket with
no port, or `bind` to port 0: the first is 32768 plus the time-stamp
counter at start-up modulo 28232, each next one the number after
(wrapping), any port in use skipped.

**The receive queue.** 65,536 bytes a socket; a datagram takes 8
bytes (its length, its source port and address) and its data rounded
up to 8. One that does not fit is dropped whole and counted `full`;
nothing is sent about it. Predicted for `udpfill` (200 datagrams of
1000 bytes over loopback, nobody reading): **65 kept on PAX** (65 ×
1008 = 65,520), where Linux kept 92 — a named difference, held to a
file of PAX's own and not to Linux's output.

**Receiving** (`udp.input`, in this order, a counter each): `short`
(fewer than 8 bytes), `length` (the header's length under 8 or over
the IP payload; less than the payload is taken at its word, the rest
ignored), `checksum` (a checksum that is not zero and does not make
the pseudo-header, header and data sum to 0xffff; zero means the
sender made none: accepted and counted `unchecked`), `port zero` (a
destination port of 0: dropped, nothing sent); then the socket bound
to the destination port on the destination address or on all — one
connected elsewhere does not count — or `no port`: a destination
unreachable, code 3, through px21's limiter (one error a second,
`limited`) and its silence for broadcasts (`silent`).

**The system calls and their errnos** (each as Linux answered the
witness):

| call | refusals |
|---|---|
| `socket` (41) | family not AF_INET `EAFNOSUPPORT` (AF_UNIX: px17's `socketpair` only; AF_INET6 too, where Linux has it: named); type `SOCK_STREAM`, `SOCK_RAW`, `SOCK_RDM`, `SOCK_SEQPACKET`, `SOCK_DCCP`, `SOCK_PACKET` `ESOCKTNOSUPPORT` (Linux has the first two: named, logged); another type `EINVAL`; a protocol that is not 0 or 17 `EPROTONOSUPPORT`; no free socket or no frames `ENOBUFS`; `EMFILE`, `ENFILE` |
| `bind` (49) | `EBADF`, `ENOTSOCK`; under 16 bytes `EINVAL`; family not AF_INET `EAFNOSUPPORT`; bound already `EINVAL`; `EADDRNOTAVAIL`; `EADDRINUSE`; `EFAULT` |
| `connect` (42) | AF_UNSPEC: the peer forgotten; else as `bind`'s address checks; a socket with no port gets one and the local address the route gives (127.0.0.1 for 127/8, else the station's) |
| `sendto` (44), `write` | no destination and no peer `EDESTADDRREQ`; over 65507 bytes `EMSGSIZE`; **over 1472 `EMSGSIZE` (PAX's, named and logged: Linux fragments)**; port 0 `EINVAL`; short address `EINVAL`; wrong family `EAFNOSUPPORT`; the device down `ENETDOWN`; no cache entry or transmit buffer to be had `ENOBUFS`; `EFAULT`. A datagram whose next hop is not resolved yet waits in px21's two-frame queue and the call succeeds, as Linux's does |
| `recvfrom` (45), `read` | nothing queued: `EAGAIN` under `MSG_DONTWAIT`, `O_NONBLOCK` or at the timeout, else wait; `MSG_PEEK` and `MSG_TRUNC` taken; any other flag ignored as Linux ignores it |
| `getsockname` (51), `getpeername` (52) | `ENOTCONN` for the second without a peer; the length written is 16, the address cut to the caller's |
| `setsockopt` (54), `getsockopt` (55) | level 1: `SO_RCVTIMEO_OLD` (20) set and read, `SO_TYPE` (3) and `SO_ERROR` (4) read; every other option and level `ENOPROTOOPT`, by name, once a process |
| `listen` (50), `accept` (43), `accept4` (288) | `EOPNOTSUPP` on a datagram socket |
| `sendmsg` (46), `recvmsg` (47), `shutdown` (48) | not asked for by the witnesses' libc: `-ENOSYS`, logged once, as every unknown call |

**Loopback lands here**, in `kernel/udp`: a datagram for the station's
own address or for 127/8 is handed straight to the receiving side —
the same demultiplexing, the same queue — in the sender's system
call, with its source the address it was sent to reach (127.0.0.1, or
the station's), and never reaches `kernel/ip`, the cache or the wire
(`ip: tx` does not count it; `udp: loop` does). One with no socket to
take it is counted and dropped; nothing is sent. **Not here, for px23:
loopback below UDP** — `icmp.ping` to the station's own address still
asks the wire for it, and TCP to itself will need the same door.

**Datagrams a second**, one at a time, each waited for (the kernel's
own stamp around each run-list line):

| | into PAX (`udpecho`, the peer or the host asks) | out of PAX (`udpsoak` asks) |
|---|---|---|
| TCG, kasumi, native / release | 6,000 / 9,000 | 6,000 / 9,000 |
| TCG, CI, native / release | 3,500 / 5,000 | 3,500 / 5,000 |
| KVM, hasu, native / release | 15,000 / 15,000 | 15,000 / 15,000 |

(px21's echo ran 20,000–21,000 a second on kasumi's native tier and
55,000–59,000 under KVM in the kernel alone; a datagram here adds two
system calls, a copy each way, a switch to the reader and the other
end's script. Wrong by more than 2× either way is wrong.)

**Existing tests that move:** `tests/mpx4-net` only — the books'
`stack frames 11` becomes 12 (`kernel/udp`'s frame); N8: this
script's datagrams through `hostfwd` are now UDP for a port nobody
holds (`no port`, a destination unreachable of code 3 for the first),
`protocol` 0; P4: `9 protocol` becomes 2 (B7's protocol 253 and 6) and
`kernel/udp` counts 7 `no port` (2 of them silent); P1's B7 expects
code 3 where the datagram is UDP; `tools/pcap-net`'s 52 held counters
grow. No `mpx1`–`mpx3` assertion moves.

**The planted breaks, predicted red:** a pseudo-header that omits the
length — every datagram PAX sends is wrong on the wire and every one
it receives is dropped `checksum`: `tests/mpx4-udp` red on every leg
(the capture, the peer, the witnesses' output), and `tests/mpx4-net`
N8 (the pokes are no longer `no port`). A receive that delivers to
the first bound socket whatever its port — `sockerr`'s "a,
MSG_DONTWAIT" line reads a datagram where Linux reads `EAGAIN`:
`tests/mpx4-udp`'s comparison red on every leg; the capture's checker
green (nothing on the wire is wrong), which is why the comparison
with Linux exists.

## What was built

1. **UDP** (`kernel/udp`): `input` judges a datagram in §3's order —
   `short`, `length`, `checksum` (zero is "none made", counted and
   taken), `port-zero` — and hands it to the socket that takes it, or
   answers `NO_PORT`, on which `kernel/netd` asks `kernel/icmp` for a
   destination unreachable of code 3 through px21's limiter and its
   silence for broadcasts, and `kernel/udp` counts what became of it.
   `send` puts a header and a checksum (a computed zero sent as
   0xffff) before the caller's bytes and gives the datagram to
   `ip.send`. Counters by cause, four lines.
2. **The socket calls** (`kernel/socket`; the descriptor in
   `kernel/files`; the dispatch in `kernel/user`): `socket`, `bind`,
   `connect` (and AF_UNSPEC), `sendto`, `recvfrom` (`MSG_DONTWAIT`,
   `MSG_PEEK`, `MSG_TRUNC`), `getsockname`, `getpeername`,
   `setsockopt` and `getsockopt` (`SO_RCVTIMEO_OLD`; `SO_TYPE`,
   `SO_ERROR`), `read` and `write` on a socket, `listen`, `accept` and
   `accept4` answered `EOPNOTSUPP`. A receive with nothing queued
   parks the thread until a datagram or the timeout
   (`sched.block_pipe_until`). Six refusals are named and logged once
   a process: a family, a type, a protocol, an option, a broadcast
   destination, a datagram over 1472 bytes. glibc's `send` and `recv`
   are `sendto` and `recvfrom`; `sendmsg` and `recvmsg` are not there
   (no witness's libc calls them).
3. **Loopback** landed, in `kernel/udp`: a datagram for the station's
   own address, for 127/8 or for 0.0.0.0 (which Linux takes as
   127.0.0.1: measured) is put on the receiving socket's queue in the
   sender's call. A third way of the test boots with **no network
   device at all** and the loopback programs print the same.
4. **Witnesses** (`user/net/`, C, static glibc, built by
   `tools/mknet`): `sockerr`, `udploop`, `udpecho`, `udpclient`,
   `udpsoak`, `resolve`, each byte-identical to Linux in output and
   exit status on both tiers, BIOS and UEFI; `udpfill` and `udphold`,
   whose answers are the receiving kernel's bounds, held to files of
   PAX's own. The echo server on PAX answers `tools/net-peer` (the
   `peer` way) and the host through `hostfwd=udp` (the `user` way);
   the client talks to `net-peer`'s server and to a host server at
   10.0.2.2; client and server both on PAX over loopback; the resolver
   asks `net-peer`'s DNS server for `pax.test` (the `peer` way: the
   name every host answers alike, because the script answers it) and
   **QEMU's own DNS server for `dns.google`** (the `user` way), where
   PAX's answer is held to what `tools/gateway-probe --dns` got from
   the same server on the same host moments before. On CI the runner
   resolved it (rcode 0, 8.8.4.4 and 8.8.8.8), as kasumi, hasu and
   nomad-1 did; a host that resolves nothing would have to see PAX
   time out the same way, a branch that never ran.
   **No wolf-built witness**: wolf's `net_*` builtins are stream
   sockets only; filed as wolffe-lang/wolf-lang#675.
5. **Tests** (`tests/mpx4-udp`: G1, U0–U9; `tools/net-peer --udp`,
   `tools/linux-net`, `tools/udp-host`, `tools/pcap-net`,
   `tools/paxnet.py`, `tools/gateway-probe --dns`), below.

**The reference side.** `tools/linux-net` runs the peer's run list on
Linux in a network namespace of its own, addressed as PAX is, with a
tap device whose other end is the same `net-peer` script that plays
to PAX — so every line a witness prints on Linux is Linux's answer to
the datagrams PAX is sent, the malformed ones included. The namespace
and the tap are made with `unshare` and `ioctl` alone; nothing is
installed and nothing outside the namespace changes.

**Found on the way, and fixed:** `tools/qemu-halt` measured the serial
log the moment the marker's text was there, which can be between the
line's CR and its LF; the LF then read as "a byte written after the
halt" (`mpx3-shell` S5, once in this lane's first gauntlet:
`notes/px22/kasumi-g1-qemu-halt-race.txt`). The marker's line must
now be whole. Every gauntlet before this one ran with that window
open.

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| `kernel/udp` and `kernel/socket` new; `files`, `user`, `sched`, `ip`, `icmp`, `netd`, `sync`, `boot/net.S` touched; `kmain_sockets` new; `net`, `virtio`, `pci`, `arp`, `process`, `vm` unchanged | so. Not predicted: `kernel/socket` imports `arp` (for a refusal line's address) and `kernel/udp` does not import `timer`; `kmain_net` starts `kernel/udp`; `tools/qemu-halt` changed (above); a third run list and way (`none`); an eighth witness (`udphold`) |
| the socket as an open file's node: shared by `dup` and `fork`, `FD_CLOEXEC` the descriptor's, freed at the last close | so: `sockerr` reads through a duplicate after the first descriptor is closed and finds the port held until the last one goes; `udploop`'s child closes its copy and the parent's socket stays bound. **Not exercised by any witness:** `execve` closing a socket marked close-on-exec, and two processes reading one socket |
| no close can reach a socket a receive is parked on; a receive ends by a datagram or `SO_RCVTIMEO` | so, by construction; the timeout ends `sockerr`'s receive on an idle socket with `EAGAIN` |
| 16 sockets are the port table; `EADDRINUSE` on the same address or on 0.0.0.0; ephemeral 32768–60999 from a start the time-stamp counter picks, then sequential | so (`sockerr`; every boot's `udp:` line names its start, a different one each boot; `tools/net-peer` holds `udpclient`'s two ports to the range). **Not exercised:** the seventeenth socket, and the range wrapping or skipping a held port |
| 65,536 bytes a queue; `udpfill` keeps **65** of 200 (Linux 92) | **65**, on every leg. Linux kept 92 in the container on kasumi and all 200 on the CI runner (its receive buffer is larger), which is why the line is held to PAX's own file. Added: from the wire, `udphold` keeps **44** of 60 datagrams of 1472 bytes (44 × 1480 = 65,120) and `kernel/udp` counts 16 `full` |
| the drop causes and their order | so, each from the wire and counted exactly in every `peer` boot: 1 `short`, 2 `length`, 1 `checksum`, 1 `port-zero`, 7 `no-port`, 16 `full`; 1 datagram with no checksum taken |
| the errnos, as Linux answered | every line of `sockerr` is Linux's, 93 lines. Three answers were measured after the prediction and PAX made to match: a broadcast destination is `EACCES` (PAX names it); a socket bound in 127/8 sending off the machine is `EINVAL`; **a destination of 0.0.0.0 is 127.0.0.1** — PAX first answered `ENETUNREACH` (`notes/px22/probes/`). **Not exercised:** `ENETDOWN`, `ENOBUFS`, `EMFILE`, every `EFAULT`, `getsockopt(SO_RCVTIMEO)`, `SO_ERROR`, `accept4` |
| loopback in `kernel/udp`, never below it | so: `tools/pcap-net` fails any datagram for 10.0.2.15 or 127/8 on the wire and found none in the gauntlet's 8 captures or in CI's; the `none` way has no wire at all |
| datagrams a second, into PAX and out — kasumi TCG native / release: 6,000 / 9,000 | into PAX **6,207–6,867** / 13,012–16,133; out **7,410–8,370** / 14,493–17,729. The native tier as predicted; the release tier 1.4 to 2.0 times the number |
| CI TCG: 3,500 / 5,000 | in 2,580–2,865 / 4,223–4,759; out 2,989–3,276 / 4,380–5,077: within a third |
| hasu KVM: 15,000 / 15,000 | in 17,350–28,134 / 21,018–32,008; out 19,388–29,989 / 20,473–33,571. **Low**: by up to 2.2 times against the host's sockets (the `user` way), which is past the bar this prediction set itself; within it against `net-peer` (17,350–22,879), whose script is the slower end |
| `tests/mpx4-net` moves: 12 stack frames; N8's pokes are `no-port` with a port unreachable; P4's `9 protocol` is 2 with 7 `no-port` (2 silent); B7 expects code 3; the held counters grow | so (66 held, from 52). Its `3 broadcast` did not move, as it should not |
| plant 1 (the pseudo-header omits the length): `mpx4-udp` red on every leg, `mpx4-net` N8 red | so, for every leg with a wire: 8 of 8 `peer` and `user` boots red on U2–U9, and `mpx4-net` N8 red on its 8 gateway legs (the pokes counted `checksum`). The 4 `none` boots stayed green, as they must: loopback sums nothing. (The `none` way did not exist when the prediction was written) |
| plant 2 (a datagram to the first bound socket): `sockerr`'s "a, MSG_DONTWAIT" line differs; the capture's checker green; `mpx4-net` green | red on all 12 boots and `mpx4-net` green, but **not by that line being printed wrong**: the datagram for `b` went to `a`, so `sockerr`'s next receive on `b` waited for good and the boot never reached a program that uses the wire. The capture was empty, which U6 counts a failure: the checker was not green, it had nothing to check |

Rates are from the kernel's time-stamp counter around each run-list
line (calibrated against 20 PIT ticks in the same boot), so they
include the program's start and, for the echo server, the battery
before the soak; 10,006 and 10,000 datagrams. One boot on kasumi while
other lanes loaded it measured 1,914 and 2,766 on the release tier's
`peer` way (the script's end starved); the ranges above are the
gauntlet's.

## 4. Evidence index

Files are under `notes/px22/`.

- **The straces of the witnesses on Linux.** Before the design:
  `first-strace/` (each witness under `strace -f`, a stand-in at the
  other end; `outputs.txt`). At the head, by `tools/linux-net`
  against the real script on a tap: `linux/<k>.strace` for the nine
  commands of `user/mpx4-udp.run` (the two soaks' cut to their first
  120 and last 20 lines: 5.3 and 4.3 MB whole), `linux/<k>.out` and
  `.rc` (what `tests/mpx4-udp` holds PAX to), `linux/peer.txt` (the
  script's account of Linux) and `linux/linux.txt` (each command's
  set of calls). What Linux answers the three sends measured late:
  `probes/linux-answers.kasumi.txt`.
- **The captures, their digests and the checker's verdicts.** A run of
  `tests/mpx4-udp` is 8 captures (2 tiers × 2 firmwares × `peer`,
  `user`): 40,128 frames in each against the peer and 40,029–40,031
  against QEMU's network, every frame PAX sent rebuilt from its
  meaning and equal byte for byte, both checksums of every datagram
  recomputed (80,244 and 80,050 a capture), the kernel's 66 counters
  held to the capture's. `kasumi-g2-mpx4-udp.checks.txt` has each
  capture's verdict lines; the digests are in
  `kasumi-g2-mpx4-udp-runs.txt`. A capture is 4.7–4.8 MB, so the
  repository carries one head as a pcap file of its own,
  `kasumi-g2-native-bios-peer.head.pcap` (the first 60 frames of
  `7f4f07e0d224…`: the ARP exchange, "ready", the battery and the
  soak's start; `tools/pcap-net` passes it as it is). CI's eight are in each run's `pax-mpx4-udp-linux`
  artifact.
- **Counters.** Every boot's four `udp:` lines, held to the capture
  by `tools/pcap-net --serial` (U6) and to exact numbers (U7):
  `kasumi-g2-mpx4-udp.out` (its build and the Linux side:
  `kasumi-g2-mpx4-udp-build.out`). Whole transcripts:
  `kasumi-g2-native-bios-peer.transcript.txt` (with the script's
  account, `kasumi-g2-native-bios-peer.net-peer.txt`),
  `kasumi-g2-native-bios-user.transcript.txt` (and
  `kasumi-g2-native-bios-user.udp-host.txt`),
  `kasumi-g2-native-bios-none.transcript.txt`.
- **The soaks.** 10,000 datagrams into PAX and 10,000 out on every
  `peer` and `user` boot (U8), and after every run-list line the
  frames free equal to before and the books `heap pages 0, live
  blocks 0, net frames 66, stack frames 12, open files 0, pipes 0,
  sockets 0, datagrams waiting 0` (U3): every frame, descriptor and
  socket came back.
- **Planted breaks, red in CI.**
  - the pseudo-header checksum without the length (`47bf338`): run
    **38104145909** at `3fa7dc9` — `mpx4-udp` red (77 FAIL lines: U2–
    U9 on all 8 boots with a wire; `net-peer: FAIL udpecho's "ready"
    to port 9099: a UDP datagram from PAX with a wrong length or
    checksum`; `pcap-net: FAIL frame 2 … byte for byte`) and
    `mpx4-net` red (N8 on 8 legs: `udp.checksum: the kernel says 1,
    the capture 0`), every other job green:
    `ci-38104145909-mpx4-udp-plant-47bf338.txt`,
    `ci-38104145909-mpx4-net-plant-47bf338.txt`. The plant's own
    commit ran first as run 38103264988, where `mpx4-net` went red the
    same way (`ci-38103264988-mpx4-net-plant-47bf338.txt`) and
    `mpx4-udp` was waiting out eight 420-second timeouts: the lane
    cancelled its own run and made a failed boot stop early
    (`3fa7dc9`). Reverted in `eac85c0`.
  - a datagram delivered to the first bound socket whatever its port
    (`19a859c`): run **38104977671** — `mpx4-udp` alone red (97 FAIL
    lines, all 12 boots), `mpx4-net` and every other job green:
    `ci-38104977671-mpx4-udp-plant-19a859c.txt`. Reverted in `d018400`.
- **Boots.** `tests/mpx4-udp` is 12 (2 tiers × 2 firmwares × `peer`,
  `user`, `none`), `tests/mpx4-net` 20:
  - kasumi, QEMU 11.1.1, TCG: 12 + 20 in the gauntlet at `a31e7a5`
    (97 and 127 PASS), 12 + 20 in the first gauntlet at `9a74fd9`, and
    23 of `mpx4-udp`'s in five partial runs while the test was
    written (one of them with the first plant in);
  - hasu, QEMU 11.1.0, **KVM**: 36 + 60 in three rounds (97 and 125
    PASS each, 0 FAIL: `hasu-kvm-k1.log`, the `*.runs.txt`), and 12
    once before (`9a74fd9`'s images);
  - nomad-1, QEMU 11.1.1, TCG on macOS arm64: 12 + 20 (97 and 125
    PASS: `nomad-1-tcg-*.out`), and 12 once before;
  - CI, QEMU 8.2.2, TCG: 12 + 20 a run.
- **What QEMU's DNS server answers, per host** (no guest):
  `probes/dns-probe.{kasumi,hasu,nomad-1}.txt`; CI's is G1's line in
  `ci-38102613365-mpx4-udp-5b29a81.txt`.
- **Modules cannot import each other:** `import-cycle.txt`.
- **The gauntlet** on kasumi at `a31e7a5` (strict env, QEMU 11.1.1
  TCG, wolf 0.2.26, clang 23.1.1; user programs built in
  `px13-ubuntu`): `kasumi-g2.summary`, `kasumi-g2.versions`. The head
  differs from `a31e7a5` by these notes only.
- **CI green**: run 38102109238 at `9a74fd9` and run 38102613365 at
  `5b29a81` (20 jobs each; `mpx4-udp` 98 PASS,
  `ci-38102613365-mpx4-udp-5b29a81.txt`); at the head, the PR names
  the run.

## 5. Done-when

Branch `px22`; PR pax#25 open, unmerged, five sections by name, commit
shas as bullets, a test checklist; CI green at the head;
`wolf/tools/lane-audit.sh pax px22 25` run by the lane. Nothing is
closed. To close at merge: nothing in pax. Filed:
wolffe-lang/wolf-lang#675 (no datagram surface in wolf's `net_*`
builtins). wolf-lang#653 is as it was.

**Not verified, plainly:** the paths the table above names as not
exercised; `ENETDOWN` for a send off the machine with no device (the
`none` way sends nothing off it); what a host without a working
resolver makes of the `user` way's outside name; anything on more
than one CPU; KVM anywhere but hasu.

**px23 (TCP) inherits:**

- the descriptor shape: a kind in `kernel/files` whose node is the
  protocol's socket number, freed from `pipe_ends` at the open
  file's last close; `files.sock_kind`, `inet_open`, `nonblocking`.
  `kernel/socket`'s `sock()` answers `ENOTSOCK`/`EBADF` and its
  address helpers read and write `struct sockaddr_in`; `socket()`
  refuses `SOCK_STREAM` by name (`ESOCKTNOSUPPORT`): that line and
  `listen`/`accept`'s `EOPNOTSUPP` are TCP's to replace;
- waiting: `files.WAIT` reruns the call on `sched.wake_pipes`, and
  `sched.block_pipe_until` adds a deadline (the process area's word
  14). Every waiter wakes on every change: fine for a few sockets,
  not for many;
- `kernel/udp`'s port table is its own 16 sockets: TCP needs its own
  or a shared one, and the ephemeral range's cursor is in
  `pax_udp_state`;
- regions (updated by px21a): `kernel/sched` now carries each thread's
  ambient region across its switches, so a kernel thread (the network
  thread among them) may hold a `region` open across a yield, a
  preemption or a wait. Still refused: an allocation in an interrupt
  handler, and a `region` left open where a system call gives up its
  kernel stack (`files.WAIT`'s rerun, `block_pipe_until`, an exit);
- **no loopback below UDP.** `ip.send` to the station's own address
  or 127/8 still goes to the cache and the wire, and `ip.input` drops
  a source of 127/8 or its own. lobo binds a loopback TCP socket to
  itself: px23 needs a door at the IP layer (and `icmp.ping` to
  itself would then work too);
- received ICMP errors still reach nothing: a connected UDP socket
  never sees `ECONNREFUSED`, over the wire or over loopback;
- `sendmsg`, `recvmsg`, `shutdown`, `poll` and every option but
  `SO_RCVTIMEO`, `SO_TYPE`, `SO_ERROR` are absent; `SO_REUSEADDR` is
  the first one a server will ask for;
- a system call may call `ip.send` (IF clear, no switch on the path);
  the lock order is `udp` → `ip` → `arp` → `net`, and lock word 7
  is the last free one of eight;
- the reference side for anything on the network: `tools/linux-net`
  (a namespace and a tap, the same script both ends see) and
  `tools/net-peer`'s `Peer` over a wire with `send` and `recv`;
  `tests/mpx4-udp` stops a boot 20 s after its other end says FAIL;
- wolf modules cannot import each other (E0303): TCP sits beside
  `udp` under `socket`, and `netd` makes the calls between them and
  `icmp`;
- owed by earlier lanes and not this one's: `docs/CENSUS.md` lines 56
  and 640 and `docs/SOURCES.md` line 77 (px19's note); `/dev/tty0`
  (px18's); MSI-X, EVENT_IDX and merged buffers (px20's).
