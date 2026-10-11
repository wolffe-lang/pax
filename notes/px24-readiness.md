# px24 — Readiness (poll, epoll, eventfd and the rest lobo's runtime asks for)

Contract: px24's, `sprints/pax/24-readiness/` in wolffe-lang/wolf (read
2026-10-11, its addendum included). Branch `px24` in pax, cut from pax
trunk `5afb903` (px26 merged). §1–§3 are committed before the first
change to the kernel, the tools, the tests or `user/`; §2's straces
were taken first, as the contract's first act.

One deliverable: a wolf program that waits — it accepts several TCP
connections at once and serves them through wolf's hosted runtime,
unmodified — runs on PAX byte-identical to Linux, and lobo's own list
of system calls (straced on Linux at its pin) has no line PAX answers
`-ENOSYS` or wrongly, short of what other lanes own. Running lobo
itself is px25's.

## 1. Forbidden, absolutely

- No kernel's, libc's, event library's or network stack's source is
  read (ruling #22), and none is searched for: not Linux, a BSD,
  libevent, libuv, mio, glibc, or wolf's own runtime for behaviour PAX
  must match. The refs clone's sparse checkout is never widened. Facts
  come from the Linux man pages (`poll(2)`, `select(2)` only to leave
  it refused, `epoll(7)`, `epoll_create1(2)`, `epoll_ctl(2)`,
  `epoll_wait(2)`, `eventfd(2)`, `fcntl(2)`, `readv(2)`, `send(2)`,
  `recv(2)`, `sendfile(2)`, `socket(7)`, `tcp(7)`, `getrandom(2)`,
  `prctl(2)`, `sigaltstack(2)`, `sched_setaffinity(2)`, `signal(7)`,
  `pipe(7)`), the uapi headers the sparse checkout holds, wolf's
  `spec/11-os.md` for what the `net_*` builtins promise a program, and
  black-box runs: `strace` of the real binaries on Linux and static C
  probes that print what Linux answers.
- No vDSO trick, no `ptrace` launcher, no injection: `strace` of this
  lane's own binaries in the container is the whole toolset. What
  clocks a program reads is taken from what PAX is asked at run time.
- No thread, futex or signal-delivery redesign (px26's, merged): this
  lane adds to `kernel/sched` only a bound, a wait's deadline and a
  thread's alternate signal stack, each named in §3. No TCP feature
  from px23's debt list (window scaling, SACK, timestamps, delayed
  ACK, keep-alives, SYN cookies). No SMP. No lobo in any image.
- Not this lane's, a sibling's (px27, the writable tree): the file
  tree, `openat`'s flags, `mkdir`, `unlink`, `rename` and their
  tests. AF_UNIX path sockets are a later lane's.
- No system call added on a guess: each one is in a strace this lane
  took, with the flags that strace shows; every flag or operation not
  shown is refused with Linux's errno, by name, and counted.
- Nothing in pax names any use of an image beyond running it (the
  contract's word list).
- Test binaries only from the `px13-ubuntu` container (Ubuntu 24.04,
  glibc 2.39) or the CI runner, never kasumi's own glibc. The
  toolchain is the release archive by digest; nothing is built from
  wolf-lang's trunk; no build on nomad-1; nothing installed anywhere.
- No `rm` outside `~/lanes/px24/` and this lane's private clones, on
  any host, `/tmp` included; no scratch in `/tmp`; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no `2>/dev/null` on a
  checkout; no trailer of any kind on a commit or the PR. No "seen
  red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, full output kept, SKIP
  counted; `wolf build` exit 2 is a compile error; the readiness and
  concurrency rows also under `taskset -c 0-3` on kasumi.
- kasumi and hasu: remote commands wrapped in `bash`, jobs under
  `setsid` with a pid file, ended by that pid only; containers
  stopped by this lane's own container id.
- A planted break fails fast: the suite it reddens has a deadline of
  its own before the break is pushed.

## 2. Inputs, verified (2026-10-11, from origin)

| input | found |
|---|---|
| pax trunk | `5afb903` (px26 merged, PR #28), later than the contract's `641e18d`; trunk CI green at it (run 38145632760). Open PRs: none of this lane's; px27 runs beside it in the file tree |
| the kernel's pin | wolf 0.2.27 (`5e17eebe…`, its `wolf` `6f5713a2…`, `libwolf_rt.a` `ab575b27…`) / lupin 0.1.50, by archive digest (`kernel/wolf.pin`) |
| lobo | trunk `b256d2e`, as the contract says; it pins wolf 0.2.27 and wolf-std `14f0ab2`. Built `--release` by the pinned wolf in `px13-ubuntu` through a `cc` that adds `-static` (ET_EXEC, no PT_INTERP): `bf1f6c6f…`, 14,697,920 bytes, `lobo/0.1.2+dev` |
| the hosts | kasumi: QEMU 11.1.1, TCG only, 16 cpus, `px13-ubuntu` (`ad896450…`, gcc 13.3.0, glibc 2.39-0ubuntu8.9, strace 6.8), Linux 7.2.8, `/home` 96% (45 GB free). hasu: KVM through `nix-shell -p qemu`. CI: QEMU 8.2.2 |
| waiting in a system call | a call answers `files.WAIT`; `kernel/user` rewinds the frame and `sched.block_pipe` (or `block_pipe_until(f, tick)`) parks the thread in state PIPE until `sched.wake_pipes()`, which makes **every** such thread ready to run its call again; sixteen call sites wake (five in `kernel/files`, one in `kernel/udp`, ten in `kernel/tcp`). A system call runs with IF clear from entry to the switch, on one CPU, and the network's thread is a kernel thread that runs only when scheduled: nothing can change a socket between a call's look and its wait **except** the call's own traffic still on the loopback queue, which `kernel/user` delivers after the call and then runs the call again (px23). A signal makes a PIPE thread ready; a rewound wait runs again under SA_RESTART unless it carried a deadline (`W_TIMED_REWOUND`: -EINTR always) |
| what is per process and should be per thread | the receive deadline (the area's word 14) and px23's count of bytes a waiting stream send has queued (word 13): two threads of one process each waiting would share them. px26 moved a pipe write's count to the thread (`sched.self_done`) and named the stream send's as this lane's |
| locks | `sync` words 0–7: console, heap, net, arp, ip, icmp, udp, tcp. **None is free.** Order `tcp` → `udp` → `ip` → `arp` → `net` |
| bounds | 16 thread slots (main, idle, the network's two, 12 for every process's threads together); 32 descriptors a process (four words each in the 512-word process area, whose words 256–511 are the signal actions); 64 open files; 16 pipe buffers; 16 UDP sockets; 64 TCP blocks of 65,536 bytes each way; a listen queue of at most 32 + 1; `mmap` backs every readable page with a zeroed frame at the call (a `PROT_NONE` mapping reserves, px26); 256 MiB, 64,080 frames free at a process's start |
| the dispatch at trunk (`kernel/user`'s `dispatch`, read) | no case for `poll` (7), `readv` (19), `writev` (20), `select` (23), `sendmsg` (46), `recvmsg` (47), `sigaltstack` (131), `sched_getaffinity` (204), `epoll_wait` (232), `epoll_ctl` (233), `ppoll` (271), `set_robust_list` (273), `epoll_pwait` (281), `eventfd2` (290), `epoll_create1` (291), `rseq` (334): each -ENOSYS, logged once a process. `getrandom` reads no flag. `fcntl` takes F_DUPFD, F_DUPFD_CLOEXEC, F_GETFD, F_SETFD, F_GETFL, F_SETFL, F_GETPIPE_SZ; F_SETFL on a console descriptor a process started with is dropped (it has no open file to hold the flag). `getsockopt` knows SO_TYPE, SO_ERROR, SO_REUSEADDR, three TCP options; anything else -ENOPROTOOPT |
| release-tier compile time (wolf-lang#711) | to be watched per kernel against trunk's (§4): trunk's `kmain_sockets` and `kmain_console`, native and release, timed on kasumi by `time-kernels.sh` before any change |
| wolf-lang#713 | open: a wolf program that parks a task a connection stalls past about max(16, 8 × cpus) parked tasks. Re-measured here with the witness on Linux (`notes/px24/linux/713.txt`): on one CPU (`taskset -c 0`) both ends in one process hold 7 connections and stall at 8; a server and a client in two processes hold 16 and stall at 17; on four CPUs 15 and 32. PAX has one CPU: **the wolf witness is sized 12 connections between two processes and 6 inside one**, under the stall, and nothing here tries to fix the runtime |

### The lists, re-taken (`notes/px24/linux/`)

Both under `strace -f -s 96` (strace 6.8) in `px13-ubuntu` on kasumi's
Linux 7.2.8.

**lobo** (`lobo-w1/`, `lobo-w4/`: one worker and four; `strace-lobo.sh`
is the request set): three requests on one connection, `Connection:
close`, HTTP/1.0, a 300,000-byte file, a range, a HEAD, a 404, a
conditional GET, a proxied GET and POST and two proxied on one
connection (the upstream a Python server on 127.0.0.1:9000), eight
requests at once, `status`, `-s reload`, a request after it, an idle
second, `-s stop`. Every request answered as expected (`requests.out`).

**The wolf witness** (`waitwolf`, drafted before the design and
committed with the first change to `user/`; `7b86d2f9…` as straced):
`loop 6` (both ends in one process, also under `taskset -c 0`),
`serve 12` with `call 12`, and `push 4 4000000` with `pull … 400`
(four connections whose reader naps, so the writer must wait to write).

Every distinct call with its flags, option levels and names, `fcntl`
commands and `ioctl` requests is a line of `lobo.shapes.tsv` (99
lines) and `wolf.shapes.tsv`; counted by `shapes.py`. What they say:

- **The runtime waits with `epoll`, level-triggered, one-shot, a
  registration a wait.** `epoll_create1(EPOLL_CLOEXEC)` once a
  process; `eventfd2(0, EFD_CLOEXEC|EFD_NONBLOCK)` registered
  `EPOLL_CTL_ADD {EPOLLIN, data=-1}` for good (the way a thread stirs
  the one that waits); a thread named `wolf-reactor` in
  `epoll_wait(ep, events, 64, -1)` (lobo's also with a timeout in
  milliseconds: 4 and 5 seen). A task whose `accept4` or `recvfrom`
  answered `EAGAIN` does `EPOLL_CTL_ADD {EPOLLIN|EPOLLRDHUP|EPOLLONESHOT,
  data=<a number>}` from its own thread **while the reactor is already
  inside `epoll_wait`**; the reactor returns the event and does
  `EPOLL_CTL_DEL`. A task whose `sendto` answered `EAGAIN` adds
  `{EPOLLOUT|EPOLLRDHUP|EPOLLONESHOT}` the same way. Events seen back:
  `EPOLLIN`, `EPOLLIN|EPOLLRDHUP`, `EPOLLIN|EPOLLHUP|EPOLLRDHUP`.
  **Not in either list:** `EPOLLET`, `EPOLL_CTL_MOD`, `EPOLLEXCLUSIVE`,
  `epoll_pwait`, `epoll_pwait2`.
- **lobo's own loop uses `poll`:** `poll([{fd, POLLIN}…], n, 250)` over
  its listening sockets, its control socket and its workers'
  socketpairs (n from 1 to 5), and `poll([{fd, POLLIN}], 1, 0)`; only
  `POLLIN` ever comes back. No `ppoll`, `select` or `pselect6`.
- **Sockets:** `socket(AF_INET, SOCK_STREAM|SOCK_CLOEXEC, 0)`,
  `setsockopt(SO_REUSEADDR)`, `setsockopt(SOL_TCP, TCP_NODELAY, [1])`,
  `bind`, `listen`, `accept4(fd, NULL, NULL, SOCK_CLOEXEC|SOCK_NONBLOCK)`,
  `ioctl(FIONBIO)`, a blocking `connect`, `sendto(…, MSG_NOSIGNAL)`,
  `recvfrom(…, 0)`, `writev` of two parts to a stream socket (a
  response's head and body), `getsockname` and `getpeername` with a
  128-byte buffer, `getsockopt(SOL_SOCKET, SO_TYPE)` and `SO_ACCEPTCONN`.
  **Not in either list:** `sendmsg`, `recvmsg`, `readv`, `sendfile`,
  `copy_file_range`, `splice`, `SO_REUSEPORT`, `SO_KEEPALIVE`,
  `SO_LINGER`, `SO_SNDBUF`, `SO_RCVBUF`, `shutdown`, `MSG_DONTWAIT`,
  `timerfd`, `signalfd`, `inotify`.
- **The rest:** `fcntl` F_GETFL, F_SETFL with O_NONBLOCK (a pipe's
  ends), F_SETFD FD_CLOEXEC, F_DUPFD; `getrandom(16, GRND_INSECURE)`
  and `getrandom(8, GRND_NONBLOCK)`; `prctl(PR_SET_NAME)`;
  `prlimit64(RLIMIT_STACK)` read; `sched_getaffinity(0, 128, mask)`
  (answered 8, sixteen CPUs set); `sigaltstack({ss_sp, 0, 32768}, NULL)`
  on every thread, with `rt_sigaction(SIGSEGV, SA_ONSTACK|SA_SIGINFO)`;
  `mmap(NULL, 8486912, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE)`
  a task (its stack), `mprotect(PROT_NONE)` of its first 65,536 bytes
  and `madvise(…, 8314880, MADV_FREE)` when it parks;
  `openat` of `/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max` and
  `/sys/devices/system/cpu/online`; `statx`, `lseek(SEEK_CUR)`,
  `readlinkat("/proc/self/exe")`, `set_robust_list`, `rseq`, `clone3`
  threads, `futex` (`FUTEX_WAIT_BITSET_PRIVATE`, `FUTEX_WAKE_PRIVATE`,
  and once `FUTEX_WAIT_PRIVATE`). No clock call appears in a strace: a
  static glibc reads the clocks through the vDSO, and PAX has none, so
  on PAX each is a `clock_gettime` (228), which the kernel's own
  `-ENOSYS` log and a probe will show (§3).
- **Threads at once:** 17 in `loop 6` on one CPU, 31 on sixteen; 30 in
  `serve 12`; lobo with one worker 25, with four 112 (sixteen CPUs).
- **lobo only, and not this lane's:** `socket(AF_UNIX,
  SOCK_STREAM|SOCK_CLOEXEC)` with `bind`, `listen`, `connect` (and
  `ENOENT`) on a path, `unlink` of it; `openat(O_WRONLY|O_CREAT|O_APPEND)`
  and `O_WRONLY|O_CREAT|O_TRUNC`, `rename`, `mkdir`, `write` to those
  files; `socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC)`, `clone`
  (a fork) and `execve` of itself for a worker, `dup2`, `wait4`,
  `kill(pid, SIGUSR2)` and `SIGKILL`, handlers for HUP, QUIT, TERM,
  USR2.

### The marked list (lobo's 99 lines, by call)

Marked from the dispatch at `5afb903` as read; the probes of item 1
run on the trunk kernel are the measurement (§4, red first).

| mark | calls |
|---|---|
| present and right, as far as px12–px26 measured | `arch_prctl`, `brk`, `mmap` (the three shapes: `MAP_NORESERVE` and `MAP_STACK` are bits `mmap` does not read), `mprotect`, `munmap`, `madvise(MADV_FREE)` (a hint: 0), `clone` (fork), `clone3` (thread), `execve`, `exit`, `exit_group`, `wait4`, `futex` (both operations), `getpid`, `kill`, `rt_sigaction`, `rt_sigprocmask`, `rt_sigreturn`, `set_tid_address`, `prctl(PR_SET_NAME)`, `prlimit64` (read), `close`, `dup2`, `read`, `write` (console, pipe), `lseek`, `pipe2(O_CLOEXEC)`, `openat` read-only, `statx`, `readlink`, `readlinkat`, `socket(AF_INET, SOCK_STREAM)`, `bind` and `connect` AF_INET, `listen`, `accept4`, `ioctl(FIONBIO)`, `sendto(MSG_NOSIGNAL)`, `recvfrom`, `getsockname`, `getpeername`, `setsockopt` SO_REUSEADDR and TCP_NODELAY, `getsockopt(SO_TYPE)`, `socketpair` (its record boundaries not kept: px17's named drift) |
| present and wrong | `getrandom`: flags are not read, so a flag Linux refuses is taken (the two the lists ask are answered). `fcntl(F_SETFL)` on descriptors 0–2 as a process starts with them: the flag is dropped. `accept4`, `recvfrom`, `sendto`, `connect`: right alone, but **nothing waits on readiness**, so the caller that got `EAGAIN` has nowhere to wait. A waiting stream `send` and a receive's deadline are per process |
| absent and this lane's | `poll`, `epoll_create1`, `epoll_ctl`, `epoll_wait`, `eventfd2`, `writev`, `getsockopt(SO_ACCEPTCONN)`, `sched_getaffinity`, `sigaltstack` (px26 left it -ENOSYS and has merged; the list asks it on every thread) |
| absent, and left so by name | `set_robust_list` (273) and `rseq` (334): -ENOSYS, which glibc tolerates (px09–px26) and which eight suites' assertions pin as the whole -ENOSYS set; px27's branch holds `tests/mpx3-shell` |
| absent and px27's (the writable tree) | `openat` with `O_CREAT`, `O_APPEND`, `O_TRUNC`; `write` to a file; `rename`, `unlink`, `mkdir` |
| absent and a later lane's (AF_UNIX path sockets) | `socket(AF_UNIX, SOCK_STREAM)`, `bind`, `listen`, `connect`, `accept4` on a path |
| absent and px26's | none: px26 merged threads, futex and signal delivery |

Drift from the contract's inputs line: the trunk is later (px26 in);
`sigaltstack` and `sched_getaffinity` are in both lists and were in no
lane's contract; a task's stack is 8 MiB of memory `mmap` backs at the
call (2,072 frames), so the wolf witness's boots need more than 256 MiB
(§3); the runtime's thread count needs more than 12 slots.

## 3. Prediction (committed before the first change)

**P1. Which of `poll` and `epoll`, and in which mode.** Both, as §2
measured: the runtime `epoll`, **level-triggered with `EPOLLONESHOT`
and `EPOLLRDHUP`**, add-then-delete around every wait, an `eventfd`
level-triggered beside them; lobo's loop `poll(POLLIN)`. No edge
trigger, no `EPOLL_CTL_MOD`, no `EPOLLEXCLUSIVE` in either list. The
contract's own C witnesses (an echo server on `epoll`, the storm and
the edge plant) use `EPOLLET` and `EPOLL_CTL_MOD`, so those two are
taken too, as far as the probe proves them against Linux;
`EPOLLEXCLUSIVE` and `EPOLLWAKEUP` are refused by name.

**P2. How readiness is kept, and what wakes a waiter.** **Computed at
the wait; nothing is pushed.** Every descriptor kind answers one
question — which of IN, OUT, HUP, ERR, RDHUP hold now, and two counts
that move when something new came to read and when room to write
came back — and `poll` and `epoll_wait` ask it of each descriptor they
were given and answer or wait. A wait is `files.WAIT`: the thread
parks in state PIPE and **every change anywhere wakes every waiter**
(`sched.wake_pipes`), which runs its call again. It can sit on that:
no object keeps a queue of waiters and no ready list exists, so there
is no lock to take (none is free) and no wake to lose between a look
and a wait beyond the one px23 already closes (the loopback queue's
drain, after which a call that said "wait" runs again).
`epoll_ctl` wakes the waiters too, since the runtime adds a
descriptor while its reactor is inside `epoll_wait`. The cost is
measured: the kernel counts waits, calls run again and calls run again
that found nothing. **Predicted:** in the echo server's soak fewer
than 4 runs of `epoll_wait` for each one that answers; in the
64-connection storm fewer than 3. Past about a hundred waiting threads
this needs queues; with 60 thread slots it does not.
Edge-triggered registrations keep the two counts they last answered
with: an event is answered again only when a count has moved.
A timeout is a deadline in the thread's own words (new), so two
threads of a process may each wait with one; `poll` and `epoll_wait`
answer -EINTR to any handled signal, with or without SA_RESTART
(`signal(7)`).

**P3. The epoll object.** At most **16** at once, each of **254
registrations** in 4 frames taken at `epoll_create1` and given back at
its last close; a 17th is -ENFILE (Linux has no such bound: named), a
255th registration -ENOSPC. A registration is the open file and the
descriptor number it was added by, the events, the 64 data bits, the
two counts, and whether one-shot has spent it. **A closed descriptor:**
a registration lasts as long as its open file (epoll(7)): closing the
last descriptor of the file drops it from every epoll object; closing
one of two duplicates drops nothing, and the events go on naming the
data given. **Across `fork`** the child's descriptor names the same
object: both see every registration. `epoll_ctl`'s errnos: a duplicate
-EEXIST, a missing entry -ENOENT, the object in itself -EINVAL, a
descriptor that is not an epoll object as `epfd` -EINVAL, a regular
file or a directory -EPERM, a closed descriptor -EBADF, an unknown
operation -EINVAL. An epoll object inside another is refused by name,
-EINVAL (Linux nests them; nothing in the lists does).

**P4. An `eventfd` in the descriptor table** is a descriptor of a kind
of its own on an open file whose node names one of 64 eight-byte
counters: `dup`, `fork` and `fcntl` share it as any open file; `read`
takes the counter (8 bytes; fewer asked is -EINVAL; zero waits, or
-EAGAIN under O_NONBLOCK), `write` adds (0xffffffffffffffff is -EINVAL;
a sum past 0xfffffffffffffffe waits or -EAGAIN); readable while it is
not zero, writable while 1 can be added. `EFD_SEMAPHORE` is refused by
name, -EINVAL: no list asks it. No `timerfd`: no strace shows one.

**P5. The calls added, and each refusal's errno.** Eight numbers:
`poll` (7), `writev` (20), `sigaltstack` (131), `sched_getaffinity`
(204), `epoll_wait` (232), `epoll_ctl` (233), `eventfd2` (290),
`epoll_create1` (291). Changed: `getrandom` reads its flags
(`GRND_NONBLOCK`, `GRND_RANDOM`, `GRND_INSECURE`; an unknown bit, or
`GRND_RANDOM|GRND_INSECURE`, -EINVAL); `getsockopt` takes
`SO_ACCEPTCONN`; `fcntl(F_SETFL)` keeps O_NONBLOCK on every kind, the
console's descriptors included; a `connect` that is under way answers
-EALREADY to a second call; a stream send's progress and a wait's
deadline are the thread's. Refused, each with a line once a process
and a count in the kernel's books: `epoll_create1` flags but
`EPOLL_CLOEXEC` -EINVAL; `epoll_ctl` with `EPOLLEXCLUSIVE`,
`EPOLLWAKEUP` or an event bit PAX never raises (`EPOLLMSG`, the band
bits) -EINVAL, an epoll object as the target -EINVAL; `eventfd2` with
`EFD_SEMAPHORE` or an unknown flag -EINVAL; `poll` of more descriptors
than a process may have -EINVAL; `writev` of more than 1024 parts, or
of lengths that overflow, -EINVAL; `sigaltstack` with a flag but
`SS_DISABLE` -EINVAL, a stack under 2048 bytes -ENOMEM, a change while
running on it -EPERM; `sched_getaffinity` of a mask under 8 bytes
-EINVAL, of another process -ESRCH. **Not added, because no strace
shows them** (each stays -ENOSYS, logged once a process): `ppoll`,
`select`, `pselect6`, `epoll_pwait`, `epoll_pwait2`, `epoll_create`,
`eventfd`, `readv`, `preadv`, `pwritev`, `sendmsg`, `recvmsg`,
`sendmmsg`, `recvmmsg`, `timerfd_*`, `signalfd4`, `accept` flags
beyond the two. `sendfile` and `copy_file_range` stay px26's (a file
of the initramfs to a pipe or the console; -EINVAL): no list asks
either of a socket. The options asked (`SO_REUSEADDR`, `TCP_NODELAY`,
`SO_TYPE`, `SO_ACCEPTCONN`) are honoured; `SO_REUSEPORT`,
`SO_KEEPALIVE`, `SO_LINGER`, `SO_SNDBUF` and `SO_RCVBUF` are in no
strace and stay -ENOPROTOOPT by name.
`sigaltstack` is per thread: a handler installed with `SA_ONSTACK`
runs on it unless the thread is already there, the `ucontext`'s stack
triple says so, and `rt_sigreturn` goes back.
`sched_getaffinity` answers 8 and CPU 0.
**The clocks:** predicted `clock_gettime` with `CLOCK_MONOTONIC` (1)
and `CLOCK_REALTIME` (0) only, both there since px12 and px26;
resolution one tick (10 ms), which a 4 ms `epoll_wait` timeout rounds
up to (a wait never ends early).

**P6. Lines of lobo's list left to others.** To px26: none. To px27:
`openat` with `O_CREAT|O_APPEND` or `O_CREAT|O_TRUNC`, `write` to a
file, `rename`, `unlink`, `mkdir`. To the AF_UNIX lane: `socket`,
`bind`, `listen`, `connect`, `accept4` on a path socket. To px25,
named: `set_robust_list` and `rseq` (-ENOSYS, tolerated);
`socketpair(SOCK_SEQPACKET)`'s boundaries; whatever the three `/proc`
and `/sys` files answer (-ENOENT here); memory `mmap` backs at the
call, 2,072 frames a task; whether lobo's `worker_connections 1024`
fits the bounds below.

**P7. Bounds, and whether the 64-connection bound rises.** It does.
**TCP blocks 64 → 256** (the echo server holds 64 connections and a
listener, and over loopback both ends are PAX's: 129 blocks); buffers
stay 65,536 bytes each way, taken when a connection is established, so
256 connections hold at most 8,192 frames (32 MiB) and the block table
is 256 KiB of `.bss`. **A listen queue at most 128 + 1** (was 32 + 1:
64 connections made at once should not wait out a retransmitted SYN).
**Descriptors 32 → 128 a process**, the process area 4,096 → 8,192
bytes a slot; **open files 64 → 512**; **pipe buffers 16 → 64**;
**thread slots 16 → 64** (60 for every process's threads). `.bss`
grows by about 1.1 MiB (the areas 448 KiB, the blocks 192 KiB, thread
words and signal words 250 KiB, open files 28 KiB, the rest small), so
every pinned count of free frames falls by about 280.
The wolf witness's boots take **1 GiB**: 17 to 30 threads, each task's
stack 2,072 frames at its `mmap`.

**P8. Numbers.** The wolf witness, requests answered a second and
connections opened, served and closed a second, the kernel's stamp
around the run-list line (`serve 12` and `call 12` over loopback, both
PAX; over the wire the other end is the tool's and slower):

| | requests a second | connections a second |
|---|---|---|
| TCG, kasumi, native / release kernel | 300 / 500 | 120 / 200 |
| TCG, CI | 200 / 350 | 80 / 140 |
| KVM, hasu | 5,000 | 2,000 |

The C echo server on `epoll`, 64 connections, over loopback: 2,000
requests a second on kasumi's TCG (native), 30,000 under KVM; its soak
of 10,000 connections 800 a second on TCG. Wrong by more than 3× either
way is wrong. Kernel build time: each tier within 20% of trunk's for
the same kernel; no function is written as one long straight line or a
nest of loops (wolf-lang#711's two shapes).

**P9. Which existing tests move.** Every kernel's bytes. Every pinned
frame count that reads the allocator at boot (`tests/tour`,
`tests/mpx2-frames`' totals if pinned, the books' `stack frames` if the
slot count reaches them: predicted 333 unchanged, the kernel stacks
being taken a thread at a time). `prlimit64(RLIMIT_NOFILE)` answers
128: any probe that prints it. `tests/mpx4-tcp` and `tests/mpx4-udp`:
the books line gains nothing (the new counts go on a line of their
own, `ready: …`), their -ENOSYS sets stay `273 334`, `tcpfull`'s "a
backlog of 2 lets 3 in" stays. `tests/mpx3-threads`: its probe asks
neither `sigaltstack` nor `poll`; unchanged. No `mpx3-shell` file is
touched (px27's). New: `tests/mpx4-ready` and its CI job.

**P10. What fails first.** The witness on trunk's kernel: `waitwolf`
stops at its first `epoll_create1` (-ENOSYS) — predicted to end with a
message of the runtime's own and a status that is not 0, having asked
`sched_getaffinity` and `sigaltstack` before it. The probes on trunk's
kernel: every `poll`, `epoll` and `eventfd` line differs from Linux's.

**P11. The planted breaks, predicted red and fast.** (a) An
edge-triggered registration that answers again without a count having
moved: the probe's edge lines differ from Linux's on the first boot
and the storm counts more than 64 events; red inside one boot's
deadline, nothing else red. (b) A wake lost between the look and the
wait — the call that said "wait" is not run again after the loopback
queue's drain: the first loopback exchange that waits in `epoll_wait`
or `poll` for its own process's traffic never returns; the suite's
stall check (the serial log not growing) stops the boot in about 300 s
and no later boot is started.

## What was built

1. **Readiness** (`kernel/ready`, `kernel/event`, `kernel/files`):
   `poll` (7); `epoll_create1` (291), `epoll_ctl` (233), `epoll_wait`
   (232) with level-triggered, edge-triggered and one-shot
   registrations; `eventfd2` (290). Every kind of descriptor answers
   which of POLLIN, POLLOUT, POLLERR, POLLHUP and POLLRDHUP hold now
   and two counts (something new came; room came back); a call that
   finds nothing parks and looks again at the next change anywhere.
   16 epoll objects of 256 registrations (four frames an object, given
   back at its last close), 64 eventfd counters.
2. **The rest of the two lists** (`kernel/user`, `kernel/signal`,
   `kernel/socket`, `kernel/sched`): `writev` (20), `sigaltstack` (131)
   with SA_ONSTACK honoured, `sched_getaffinity` (204), `getrandom`'s
   flags, `getsockopt(SO_ACCEPTCONN)`, -EALREADY, `F_SETFL` on the
   console's three descriptors; a waiting send's progress and a wait's
   deadline in the thread's own words.
3. **Bounds**: 64 thread slots, 128 descriptors a process (the process
   area is 8,192 bytes), 512 open files, 64 pipe buffers, 256 TCP
   blocks, a listen queue of at most 129.
4. **Three things in others' modules, each because a witness was wrong
   without it.** `kernel/tcp`: a connection that is reset keeps the
   bytes it had received in order for its reader (Linux hands them over
   and then the error: `pollprobe`'s "its read: the 6 bytes"; px23 threw
   them away). `kernel/net`: `send` looks again, up to 200,000 times
   with a PAUSE between, for a transmit buffer the device has returned
   before it answers `full` (under KVM 64 connections answered together
   filled the 64 buffers once: `net: tx … 1 full`, hasu, the first
   round). `kernel/sched`: the page table for the upper thread slots'
   stacks is taken at start (the first process with more than thirty
   threads left the count of free frames one short for good).
5. **Witnesses** (`user/net/`, built by `tools/mknet`): the probes
   `nbprobe`, `pollprobe`, `epollprobe`, `evprobe`, `restprobe`;
   `epollecho` (a server on epoll, its driver, the storm, the soak);
   `pair` (a server and a client as one line of a run list);
   `waitwolf.lu`.
6. **The other ends**: `tools/net-peer --ready` (the script's own TCP:
   64 handshakes begun at once, the storms, the soak, the wolf witness
   asked and answered), `tools/ready-host` (ordinary sockets behind
   QEMU's user-mode network), `tools/linux-net --ready` (the same
   script against Linux on a tap device: the reference every output is
   held to).
7. **Tests**: `tests/mpx4-ready` (T0–T9; three ways, two tiers, two
   firmwares: 12 boots) and its CI job.

**Found on the way.**

- **A wolf task's stack is 8 MiB that PAX backs at its `mmap`.** With
  the 19 MiB initramfs in a 256 MiB machine the two-process witness
  ran out: `syscall 9: refused: out of frames, -12`, then a thread
  could not be made (`failed to spawn thread … WouldBlock`) and the
  runtime gave up. The suite boots with 1 GiB. Memory taken when a page
  is first touched is the fix, and it is not here.
- **QEMU's forwarded port has a short queue of its own.** Of 64
  connections this host began at once to a `hostfwd=tcp` port, some
  never reached the guest (one capture: 52 SYNs of 65, every one
  answered by PAX); held to four CPUs the forward refused a connect
  outright. `tools/ready-host` makes its connections one after another
  and makes a refused one again (counted: 0 in every run kept).
  Through the forward the soak runs at about 60 connections a second
  on every host, KVM too: the pace is QEMU's.
- **`kernel/arp` drops the kernel's own frames when an entry ages
  under load.** An entry is good for 60 s; the next send after that
  asks again and keeps two frames for the address, pushing out the
  rest. With one connection at a time that costs nothing; with 64
  sending, or a window of a bulk transfer going out, it costs the
  frames (CI run 38151712372: `pending 9 queued, 3 sent, 6 pushed out`
  in `mpx4-ready`'s user boot and `14 pushed out` in `mpx4-tcp`'s
  native UEFI peer boot, each red in `tools/pcap-net`: the kernel had
  counted as sent what never reached the wire). TCP retransmits and
  every transfer stays exact. `tools/pcap-net` now holds such segments
  to the gaps in the IP identifications and to the kernel's own count
  of what it pushed out, and reads a gap in a connection's bytes at
  such a place as bytes not yet seen. The cache itself is not changed:
  pax#32.
- **`writev` to a pipe is one write.** Written a part at a time it
  answered 3000 where Linux answers 4096 (3000 and 3000 into room for
  4096), and wrote the first part of a call whose second was a bad
  pointer. The sum now decides PIPE_BUF's all-or-nothing rule and every
  part is checked before a byte is taken.
- **The release tier's time over `kmain_sockets` grew threefold**
  (below, wolf-lang#711's shape again). One call, `ready.report()` from
  the function that prints the books, is 20 s of it; writing it a
  function a count did not help.
- A probe's first form hung on Linux itself (a blocking read of an
  empty pipe) and another printed two waits in the order the compiler
  chose to evaluate a call's arguments: both were the probes' faults,
  found by running them on Linux before PAX.
- `eventfd`'s `write` of nine bytes is -EINVAL on kasumi's Linux 7.2.8,
  where eventfd(2) says only "less than 8"; the line is not in the
  probe (the CI runner's kernel is another), and PAX follows the man
  page.

## 3. The prediction against the measurement

| predicted | measured |
|---|---|
| P1: the runtime `epoll`, level-triggered, one-shot, `EPOLLRDHUP`, an `eventfd`; lobo's loop `poll(POLLIN)`; `EPOLLET` and `EPOLL_CTL_MOD` only for the C witnesses | so. Not predicted: a write that must wait registers `EPOLLOUT\|EPOLLRDHUP\|EPOLLONESHOT` (found by making the witness's reader nap, before the design) |
| P2: computed at the wait; every waiter woken at every change; no queue, no lock; `epoll_ctl` wakes; two counts for edge triggering | so (`kernel/ready`'s header). Console input wakes the waiters too (`sched.wake_input`), which the prediction did not say |
| P2: fewer than 4 runs of `epoll_wait` for each that answers in the soak, fewer than 3 in the storm | **right on kasumi's native kernel and in every `none` and `user` boot** (8 to 24 calls that found nothing for each hundred waits). **Wrong on the release kernel against the script** (`peer`): 176 to 197 for each hundred waits — a call run again finds nothing about twice for each time a thread parks (8,423 answers, 5,949 waits, 10,588 empty: 2.3 runs an answer, still under 4). Over the wire each arriving segment wakes every waiter and the echo's own answer is another change. The storm alone was not counted apart |
| P3: 16 objects of 254 registrations | 16 of **256** (four frames hold 256 eight-word registrations; 254 was a slip of arithmetic) |
| P3: the errnos; a registration lasts as long as its open file; shared across `fork`; nesting refused -EINVAL | each as Linux answered `epollprobe` (112 lines identical); nesting and `EPOLLEXCLUSIVE` refused -EINVAL by name (the probe's two `~` lines). Not predicted: the console or `/dev/null` in an epoll object is refused by name, -EPERM (they keep no open file); `lseek` on an epoll descriptor answers 0 on Linux, and on an eventfd too |
| P4: an eventfd is a descriptor kind on an open file over one of 64 counters; no semaphore mode | so; its mode is 0600 with no type (measured) |
| P5: eight numbers: 7, 20, 131, 204, 232, 233, 290, 291 | **those eight** |
| P5: the refusals and their errnos | as built. **Not exercised by any probe:** -EALREADY (the probe's second `connect` comes after the handshake, where Linux and PAX answer 0), `SS_AUTODISARM`, `EPOLLWAKEUP`, an event bit PAX never raises, a 17th epoll object, a 257th registration, `sigaltstack`'s -EPERM from the stack itself is exercised |
| P5: the clocks: `CLOCK_MONOTONIC` and `CLOCK_REALTIME`, a tick's resolution | the wolf witness asks **`CLOCK_MONOTONIC` alone** (`notes/px24/pax/clocks.txt`: a scratch kernel that logged each clock id once a process); 4 or 5 distinct readings in 2,000 reads (`~clock`); `clock_getres` was asked by nothing and stays -ENOSYS |
| P6: the lines left to others | as listed below ("What px25 inherits") |
| P7: 256 blocks, a listen queue of 129, 128 descriptors, 512 open files, 64 pipes, 64 slots | so |
| P7: `.bss` grows by about 1.1 MiB, every free-frame count falls by about 280 | **752 KiB**: `kmain_sockets` 462,904 to 1,232,952 bytes of `.bss` (188 frames), and 48 more for the FPU areas of 48 more slots |
| P7: the wolf witness's boots take 1 GiB | so, and measured to be needed (above) |
| P8: the wolf witness on kasumi's TCG, native / release: 300 / 500 requests and 120 / 200 connections a second | **553 to 939 / 3,936 to 4,882 requests; 27 to 46 / 196 to 244 connections** (two gauntlets, 8 boots each; the low ends are boots that shared the host with a copy to hasu). Native requests inside the 3× bar, release requests eight times the prediction: wrong. Connections: native a third of the prediction (the run is 120 connections in 2.6 s, of which two process starts are most), release right |
| P8: CI: 200 / 350 requests | native 430 (run 38151712372, the one boot read); the head's run is in the PR |
| P8: KVM, hasu: 5,000 requests and 2,000 connections a second | KVMWOLF |
| P8: the echo server's soak 800 connections a second on TCG, 30,000 requests a second under KVM | kasumi native **753 to 1,598** connections a second over loopback and 1,205 to 1,971 against the script; release 9,070 to 10,172 and 4,031 to 4,846; KVMECHO. Through QEMU's forward 57 to 71 on every host |
| P8: each kernel's build within 20% of trunk's | **wrong for `kmain_sockets`**: `wolf build --release --no-cache`, trunk and head by turns on a quiet kasumi: 18.5 and 20.1 s at trunk, 58.1 to 66.5 s at head; `kmain_console` 55.1 and 55.2 s at trunk, **33.5 and 36.3 s at head** (faster, unexplained). Without the call of `ready.report()` the head's `kmain_sockets` takes 41 s. `tools/build-kernel` (cached, with its IR pass) took 70 to 240 s for the same kernel at the head across this lane's runs and 126 and 135 s in CI. No timeout was raised |
| P9: every kernel's bytes; pinned frame counts; `stack frames` 333 unchanged; `mpx4-tcp` and `mpx4-udp` books unchanged; -ENOSYS sets `273 334` | bytes: so; 333: so; -ENOSYS sets: so. **Not predicted, and moved:** `tests/tour`'s `sched: … 16 slots` line (64) and `tests/mpx4-tcp` T1's `tcp: 64 blocks` (256): both found red, the first in CI run 38151712372 (job tour), the second before the first push; `tools/pcap-net`'s two rules (above). No frame count was pinned anywhere |
| P10: `waitwolf` on trunk's kernel stops at `epoll_create1` with a message of the runtime's and a status that is not 0 | **right**: -ENOSYS for 204, 131 and 291, the runtime's `epoll_create1 failed`, then `killed: general protection` (`notes/px24/red/trunk-kernel.wolf-and-probes.serial.txt`); every `poll` and `epoll` line of the probes -ENOSYS, and `pollprobe` never ends (its wait for a child's write is a `poll` that answers at once) |
| P11 (a): an edge-triggered registration that answers again: the probe's edge lines differ on the first boot | **right**: `edge: asked again, nothing new: 1; [1] EPOLLIN` where Linux says 0; the boot is stopped the moment command 3 has printed it. The storm was never reached, so "the storm counts more than 64" is **not shown** |
| P11 (b): the call that said "wait" is not run again after the loopback queue's drain | **planted otherwise.** `poll` and `epoll_wait` send nothing, so the drain after them delivers nothing and that rerun never applies to them: the plant as predicted would have been green. The wake a waiter can lose here is `epoll_ctl`'s: a descriptor that became ready between its owner's failed read and its registration, with the waiter already inside `epoll_wait`. That wake was removed, and a probe case added for it first (a child adds a readable pipe while the parent waits): red in the first boot, in seconds, not at a 300 s stall |

## 4. Evidence index

Files are under `notes/px24/`. A digest cut short carries `…`.
Measured means this lane ran it and read the result.

- **The lists on Linux**: `linux/` — lobo's and the wolf witness's
  straces, `lobo.shapes.tsv` (99 lines) and `wolf.shapes.tsv`, the
  scripts, `713.txt` (wolf-lang#713's bound, re-measured), `threads.txt`.
  The marked list is §2's table.
- **The probes' verdicts on both.** The same eight binaries
  (`programs.sums.txt`) on Linux (`linux-side/<k>.linux.out`, by
  `tools/linux-net --ready` on a tap device with the script at the
  other end; `linux-side/linux.txt` is each command's set of calls,
  `peer.txt` the script's account of Linux) and on PAX
  (`pax/<k>.pax.out`, kasumi, native, BIOS, `peer`): the 13 commands'
  outputs equal but for five `~` lines. `tests/mpx4-ready` T2 holds
  every boot to it.
- **The captures and the checker's verdicts**: `kasumi/kasumi-native-bios-peer.head.pcap`
  and `…-user.head.pcap` (the first 4,000 frames of each), with
  `…pcap.check.txt` for the whole captures: 111,485 frames against the
  script (50,711 from PAX, each rebuilt and equal byte for byte;
  334,448 checksums recomputed; the kernel's 77 counters the
  capture's). CI's are in each run's artifact.
- **Counters, the soak and the storm**: `kasumi/kasumi-tcg-mpx4-ready.out`
  (the head's kernel, 100 PASS, 0 FAIL, 0 SKIP; 12 boots,
  `…runs.txt`): after each command every frame back and `epolls 0,
  registrations 0, eventfds 0`, `open files 0`, `tcp blocks 0`, `heap
  pages 0` (T3); the storm twice in every boot that runs the server:
  `storm 2 waits, 64 events, 64 distinct, 0 repeated` with room for
  all and `storm 5 waits, …` with room for 16 (T8, and the script's
  own check, T5); 10,064 connections through the server over loopback
  and again over the wire. A whole transcript:
  `kasumi/native-bios-peer.transcript.txt`, with the script's account
  (`native-bios-peer.net-peer.txt`) and the host tool's
  (`native-bios-user.ready-host.txt`).
- **Under `taskset -c 0-3`**: `kasumi/kasumi-taskset-0-3-mpx4-ready.out`,
  the whole suite, rc 0 (the kernel of `6108a51`, before `kernel/net`'s
  change). Its first try was red in one boot, on the host's side: the
  forward refused a connect (above); `tools/ready-host` was changed and
  the suite run again.
- **Planted breaks, red in CI, failing fast.**
  - (a) an edge-triggered registration answers again without a count
    having moved (`e76a483`): run **38154755767**, job 114515323479
    (mpx4-ready) the only failing job of 23: `ci/ci-38154755767-mpx4-ready-plant-a.txt`.
    Reverted in `cd7ab48`. On kasumi first: `red/kasumi-plant-a.mpx4-ready.out`.
  - (b) a registration added or modified wakes nobody (`b286189`):
    run **38154873744**, job 114515671715 (mpx4-ready) the only
    failing job of 23: `ci/ci-38154873744-mpx4-ready-plant-b.txt`.
    Reverted in `6108a51`. On kasumi first: `red/kasumi-plant-b.mpx4-ready.out`.
  - Each job was red at its first boot (native, BIOS, no device),
    stopped when command 3 had printed other than Linux did; no later
    boot was started, so neither plant is shown on any other leg.
- **Red first, on the trunk's kernel** (`5afb903`, kasumi):
  `red/trunk-kernel.wolf-and-probes.serial.txt` and
  `red/trunk-kernel.none.serial.head.txt`.
- **Kernel build times**: `kasumi/kernel-build-times.raw.txt` (the
  cached `tools/build-kernel` figures; the first block was taken with
  the host loaded) and the table's uncached figures
  (`kasumi/kernel-build-times.no-cache.txt`).
- **Boot counts.**
  - kasumi, QEMU 11.1.1, TCG: `tests/mpx4-ready` whole (12 boots)
    four times green — at `86c8a60` (its output was overwritten by a
    later run; the PASS lines were read), under `taskset -c 0-3` and
    plain at `6108a51`'s kernel, and at the head's kernel
    (`kasumi-tcg-mpx4-ready.out`); some thirty single boots more while
    the suite was written.
  - hasu, QEMU 11.1.0, **KVM**: KVMBOOTS
  - CI, QEMU 8.2.2, TCG: 12 a green run of the job; every other suite
    in the same runs (23 jobs).
- **CI**: run 38153375026 at `86c8a60`, green, 23 jobs. Run
  38151712372 before it was red in three jobs, each explained above
  (tour's line; `pcap-net` twice). The head's run is in the PR.

**Not verified, plainly.**

- **The console.** `fcntl(F_SETFL, O_NONBLOCK)` on descriptors 0–2 now
  keeps the flag and `poll` answers POLLIN for the console when a
  `read` would answer; no probe runs with a terminal on both sides
  (`tests/mpx4-ready`'s Linux side gives every program `/dev/null`), so
  neither was run against Linux, and the second was not run at all.
- The refusals no probe asks (above, P5), and -EALREADY.
- `poll` on an epoll descriptor (POLLIN while it has an event to hand
  out): written, never called.
- Edge-triggered `EPOLLOUT` after a full send buffer drains (the count
  that moves when an acknowledgement makes room): `epollecho` asks for
  it when a send answers -EAGAIN, which no run made it do; the wolf
  witness's writer waits with a level-triggered one-shot registration,
  which is exercised (`push` and `pull`).
- More than 64 connections at once; a 65th to 256th TCP block; a
  listen queue past 64 waiting.
- The storm's count in the planted run; either plant on any leg but
  the first.
- lobo on PAX: nothing of it ran here (px25). Which clocks lobo reads.
- wolf-lang#713 on PAX: the witness is sized under the bound measured
  on Linux; whether PAX's one CPU stalls at the same count was not
  tried.
- Nothing was built on hasu or nomad-1; hasu ran kasumi's images.
- Real hardware; any Linux but kasumi's 7.2.8 and the CI runner's.

**Filed.** pax#32 (`kernel/arp` pushes the kernel's own frames out
when an entry ages under load). Nothing upstream: wolf-lang#713 and
#711 were open already; #711's shape is seen again and measured above.

**To close when this merges.** Nothing in pax names this work.

**What px25 inherits** (every line of lobo's list still unanswered or
answered otherwise than Linux, by call and flag):

- `socket(AF_UNIX, SOCK_STREAM|SOCK_CLOEXEC, 0)` with `bind`, `listen`,
  `accept4`, `connect` on a path (and `ENOENT` for a path nobody
  listens on) and `unlink` of the path: -EAFNOSUPPORT by name today.
  lobo's control socket and its workers' sockets.
- `openat(…, O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC)` and
  `O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC`, `write` to those files,
  `rename`, `unlink`, `mkdir` (`EEXIST`): px27's.
- `set_robust_list` (273) and `rseq` (334): -ENOSYS, once a thread;
  glibc goes on.
- `socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC)`: there, a
  one-frame buffer each way, record boundaries not kept (px17).
- `openat` of `/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`,
  `/sys/devices/system/cpu/online`: -ENOENT; `statx` of
  `/sys/fs/cgroup/cgroup.controllers`: -ENOENT. The runtime went on
  with `sched_getaffinity`'s one CPU.
- `mmap(…, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE)`
  of 8,486,912 bytes a task: backed at the call, 2,072 frames; and
  `madvise(MADV_FREE)` gives none back. lobo with one worker ran 25
  threads on sixteen CPUs. A thread that cannot have its kernel stack
  is a kernel panic (`sched: no frame for a stack`), not -EAGAIN.
- `worker_connections 1024` against 128 descriptors a process and 256
  TCP blocks in the machine.
- Not in lobo's request set here and not on PAX: `sendmsg`, `recvmsg`,
  `readv`, `sendfile` to a socket, `SO_REUSEPORT`, `SO_KEEPALIVE`,
  `SO_LINGER`, `SO_SNDBUF`, `SO_RCVBUF`, `ppoll`, `epoll_pwait`,
  `timerfd`, `signalfd`, `clock_getres`. A larger request set (TLS, a
  resolver, access-log rotation) may ask them.
- `kill(pid, SIGUSR2)`, `SIGKILL`, handlers for HUP, QUIT, TERM, USR2,
  `clone` (fork) with `execve` of itself, `dup2`, `wait4`: px14's and
  px26's, not run with lobo.
- `kernel/arp`'s two-frame queue (pax#32) and the virtio driver's 64
  transmit buffers under 64 connections; one wake for every waiter
  (`kernel/ready`'s cost above) past about a hundred waiting threads.

## 5. Done-when

- Branch `px24` on origin; PR wolffe-lang/pax#31, open, unmerged, the
  five sections by name, commit shas as bullets, a test checklist.
- CI green at the head (the PR names the run).
- `wolf/tools/lane-audit.sh pax px24 31` run by this lane from the org
  directory, its exit status read directly (in the PR).
- Trees: kasumi `~/lanes/px24/` and hasu `~/lanes/px24/` keep the
  evidence with build directories pruned; no worktree anywhere; no
  process of the lane left.
- Nothing merged, nothing tagged, nothing closed.
