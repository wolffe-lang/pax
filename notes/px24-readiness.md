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
