# px34 — The Unix sockets (and the rest lobo asks of PAX before px25)

Contract: px34's, `sprints/pax/34-the-unix-sockets/` in wolffe-lang/wolf
(read 2026-10-11). Branch `px34` in pax, cut from pax trunk `7c2c70e`
(px30 merged). §1–§3 are committed before the first change to the
kernel or the tests; §2's straces were taken first, as the contract's
first act.

One deliverable: every line of lobo's straced list that px24's report
left unanswered and that is not threads or job control is answered on
PAX as Linux answers it — AF_UNIX path sockets above all — proved by
static C probes byte-identical to Linux and by lobo's own control
client talking to a lobo-shaped server on PAX.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22),
  and none is searched for; the refs clone's sparse checkout is never
  widened. Facts come from the man pages (`unix(7)`, `socket(2)`,
  `bind(2)`, `connect(2)`, `listen(2)`, `accept(2)`, `socketpair(2)`,
  `shutdown(2)`, `getsockname(2)`, `getpeername(2)`, `getsockopt(2)`,
  `send(2)`, `recv(2)`, `poll(2)`, `epoll(7)`, `mmap(2)`, `madvise(2)`,
  `getrlimit(2)`, `proc(5)`, `proc_pid_status(5)`, `cgroups(7)`,
  `sysfs(5)`; read on kasumi), the uapi headers the sparse checkout
  holds (`linux/un.h`, `linux/socket.h`, `linux/net.h`,
  `asm-generic/socket.h`, `asm-generic/errno*.h`,
  `asm-generic/mman*.h`), and black-box runs: strace of lobo and of the
  probes on Linux in `px13-ubuntu`, and the probes' own output there.
  lobo is used as built from its own repository at its pin, never read
  for how it works.
- No system call, flag or option is added on a guess: each is in a
  strace this lane took of lobo (§2), or is named by the contract's
  item 1 (then said so); anything else is refused with Linux's errno,
  by name. No `SCM_RIGHTS`/`SCM_CREDENTIALS` (no strace shows them; no
  `sendmsg`/`recvmsg` on a Unix socket in any). No SMP. No lobo
  *serving* in any image (px25): lobo appears only as item 5's client
  (`lobo status`), which is how this lane reads the contract's two
  lines that pull against each other ("No lobo in the image" and
  "lobo's own `-s status` client … on PAX"); the orchestrator may rule
  otherwise and the witness then runs without it.
- **No word implying filming, recording, viewers or a demo anywhere in
  pax.** Test binaries only from `px13-ubuntu` on kasumi or the CI
  runner, never kasumi's CachyOS glibc. The toolchain is the release
  archive by digest; lobo is built from its own tree at its pin by that
  toolchain.
- No `rm` outside `~/lanes/px34/` on any host; no scratch in `/tmp`; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag; no
  `2>/dev/null` on a checkout; no trailer of any kind on a commit or
  the PR. No build on nomad-1. Nothing installed anywhere. At most one
  CI run of this lane at a time; another lane's never cancelled.
- No "seen red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, full output kept, SKIP counted;
  `wolf build` exit 2 is a compile error; the rows with two processes
  also under `taskset -c 0-3`.
- kasumi and hasu: remote commands wrapped in `bash`, jobs under
  `setsid` with a pid file, ended by that pid only; a container is
  stopped by its own name only. kasumi's `/home` is at 97%: build
  directories are pruned as the lane goes.
- A planted break fails fast: the suite it reddens has a deadline
  before the break is planted.
- Other lanes in pax: px28 (an image), px32 (sound): their files are
  not touched.

## 2. Inputs, verified (2026-10-11)

| input | found |
|---|---|
| pax trunk | `7c2c70e` (px30 merged; px24 `2a0da26`, px26 `5afb903`, px27 `1af462d` in), as the contract says |
| the kernel's pin | wolf 0.2.27 (archive `5e17eebe…`) / lupin 0.1.50, by digest (`kernel/wolf.pin`) |
| lobo | trunk `944edc1` (0.1.3, the channel flipped to `+dev`), pinning wolf 0.2.27 (`0ddda6b`) and wolf-std `14f0ab2`: the kernel's own wolf. Built `--release` by the pinned wolf in `px13-ubuntu` through a `cc` that adds `-static` (`linux/build-lobo.sh`): `2dc94b06…`, 14,697,920 bytes, ET_EXEC, no PT_INTERP, `lobo/0.1.3+dev` |
| the hosts | kasumi: Linux 7.2.8-1-cachyos, `px13-ubuntu` (`ad896450…`, glibc 2.39, strace 6.8), QEMU 11.1.1 TCG; `/home` 97% (34 GB free). hasu: KVM via `nix-shell -p qemu`. nomad-1: no builds |
| px24's "What px25 inherits" and px27's lobo list | read (`notes/px24-readiness.md` §5, `notes/px27-the-writable-tree.md` §4): AF_UNIX path sockets; `socketpair(AF_UNIX, SOCK_SEQPACKET)` without record boundaries; `/proc/self/{status,cgroup}`, `/sys/fs/cgroup/{cgroup.controllers,cpu.max}`, `/sys/devices/system/cpu/online` -ENOENT; 8 MiB `MAP_NORESERVE` task stacks backed at the call (2,072 frames), `MADV_FREE` giving none back; a thread with no kernel stack a panic; 128 descriptors a process and 256 TCP blocks against `worker_connections 1024`; `set_robust_list`/`rseq` -ENOSYS by name; signals, fork/exec of itself, `wait4` px14's and px26's |

### The lists, re-taken (`notes/px34/linux/`)

lobo `944edc1` under `strace -f -s 256 -yy` (`-yy` names each socket's
path) in `px13-ubuntu` on kasumi, with px24's request set
(`strace-lobo.sh`, its two changes marked): three requests on one
connection, `Connection: close`, HTTP/1.0, a 300,000-byte file, a
range, a HEAD, a 404, a conditional GET, a proxied GET and POST and
two proxied on one connection, eight requests at once, `status`, `-s
status`, `-s reload`, a request after it, an idle second, `-s stop`;
one worker and four. Every request answered as expected
(`lobo-944edc1/w*/requests.out`).

**`-s status` is not lobo's spelling:** lobo 0.1.3 answers `lobo:
invalid option: "-s status"`, exit 1 (`w1/s-status.strace`); its
status client is `lobo -c CONF status` (`w1/status.strace`), and that
is the client item 5 runs. `-s reload` and `-s stop` are as the
contract says.

`lobo.shapes.tsv` (100 lines: px24's `shapes.py` over the straces with
`-yy`'s annotations stripped, `strip-yy.py`) against px24's 99: one
line more, `madvise(MADV_DONTNEED)` (glibc's, once, after it read
`/proc/sys/vm/overcommit_memory`). What lobo does with a Unix socket
(every call whose descriptor `-yy` names `UNIX`):

- **The control socket:** `socket(AF_UNIX, SOCK_STREAM|SOCK_CLOEXEC,
  0)`, `bind` to `logs/control.sock` (relative to the working
  directory; addrlen 20, the NUL counted), `listen(fd, -1)`,
  `ioctl(FIONBIO, [1])`; its path written into `logs/lobo.pid`; then
  `poll([…, {fd, POLLIN}], n, 250)` beside its TCP listeners;
  `accept4(fd, NULL, NULL, SOCK_CLOEXEC|SOCK_NONBLOCK)`; `recvfrom(c,
  buf, 512, 0, NULL, NULL)` (-EAGAIN first, then the verb); the task
  that got -EAGAIN does `epoll_ctl(ADD, c,
  EPOLLIN|EPOLLRDHUP|EPOLLONESHOT)` and the reactor `DEL`s it;
  `sendto(c, answer, n, MSG_NOSIGNAL, NULL, 0)`; `close(c)`. At stop:
  `close(listener)`, `unlink("logs/control.sock")`.
- **The client** (`status`, `-s reload`, `-s stop`): read the pid file,
  `socket`, `connect` to the path (addrlen 20), `ioctl(FIONBIO)`,
  `sendto(verb, MSG_NOSIGNAL)`, `recvfrom` (-EAGAIN), `epoll_ctl(ADD,
  EPOLLIN|EPOLLRDHUP|EPOLLONESHOT)`, the reactor's `epoll_wait`
  returning `EPOLLIN|EPOLLHUP|EPOLLRDHUP` (the server answered and
  closed), `recvfrom` of the answer, `recvfrom` 0, `close`.
- **Four workers:** each binds `logs/control.sock.wN` (addrlen 23); the
  master `connect`s to each to ask and to probe: **-ENOENT** (×7: the
  worker has not bound yet), **-ECONNREFUSED** (×1: the worker's
  listener closed and its name not yet unlinked), and a connection it
  closes at once, to which the worker's answer is **-EPIPE** (×40,
  `MSG_NOSIGNAL`: no signal). Each worker unlinks its name at stop.
- **`socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC, 0)`** ×4: the
  spawn's channel (the child's end close-on-exec; the parent's
  `recvfrom` answers 0 when the `execve` took). No message crosses it
  in the request set.
- Not called on a Unix socket in either list: `getsockname`,
  `getpeername`, `shutdown`, `getsockopt`, `setsockopt`, `sendmsg`,
  `recvmsg`, `SO_PASSCRED`, abstract names, autobind,
  `socket(AF_UNIX, SOCK_SEQPACKET)` or `SOCK_DGRAM` on a path.

The files lobo reads (`proc-sys-container.txt` has what Linux answers
in the container): `openat("/proc/self/status")` and `statx` of it
(mode `0444`, size 0) and reads of 32, 32, 64, 128, 256, 512, 1024
bytes to the end (at start and at each reload);
`openat("/proc/self/cgroup")` (`0::/`); `statx` by path of
`/sys/fs/cgroup/cgroup.controllers`; `openat`, `statx`,
`lseek(SEEK_CUR)` and reads of `/sys/fs/cgroup/cpu.max` (`max
100000`); `/sys/devices/system/cpu/online` (`0-15` there);
**`/proc/sys/vm/overcommit_memory`** (`0`, one byte read: glibc's
malloc, before its `MADV_DONTNEED`; on no earlier list).

### The marked list (lobo's 100 lines, by call)

Marked from pax trunk `7c2c70e` as read; the probes run on the trunk
kernel are the measurement (§4, red first).

| mark | calls |
|---|---|
| present and right (px12–px30) | everything px24's table marked so, and since px24: `poll`, `epoll_create1`, `epoll_ctl`, `epoll_wait`, `eventfd2`, `writev`, `sched_getaffinity`, `sigaltstack`, `getsockopt(SO_ACCEPTCONN)` on TCP (px24); `openat` with `O_CREAT`, `O_APPEND`, `O_TRUNC`, `write` to a file, `rename`, `unlink` of a file, `mkdir` (px27); `madvise(MADV_DONTNEED)` (px26: zeroes the pages) |
| present and wrong | `socketpair(AF_UNIX, SOCK_SEQPACKET)`: record boundaries not kept (px17's named drift); `ioctl(FIONBIO)` on a socketpair's end -ENOTTY (Linux takes it; not in the request set on one); `mmap(…MAP_NORESERVE)`: 2,072 frames at the call, where Linux backs what is touched; `madvise(MADV_FREE)` gives nothing back; `prlimit64(RLIMIT_STACK)` answers PAX's 128 KiB both ways where Linux answers 8 MiB and unlimited (the stack PAX gives; kept, and said so in §3) |
| absent and this lane's | `socket(AF_UNIX, SOCK_STREAM\|SOCK_CLOEXEC)`, `bind`, `listen` (backlog -1), `accept4`, `connect` (and its -ENOENT, -ECONNREFUSED), `ioctl(FIONBIO)`, `sendto(MSG_NOSIGNAL)` (and -EPIPE), `recvfrom`, `close`, `poll(POLLIN)`, `epoll_ctl(ADD/DEL)` and `epoll_wait`'s events on a path socket; `unlink` of a socket's name; `openat`/`statx`/`read`/`lseek` of `/proc/self/status`, `/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`, `/sys/devices/system/cpu/online`, `/proc/sys/vm/overcommit_memory`, `statx` of `/sys/fs/cgroup/cgroup.controllers` |
| named by the contract's item 1, in no strace | `shutdown`, `getsockname`, `getpeername`, `getsockopt(SO_ACCEPTCONN)` on a Unix socket: done on the item's word, each proved by a probe against Linux |
| absent, and left so by name | `set_robust_list` (273), `rseq` (334): -ENOSYS, which glibc tolerates |
| threads and job control (not this lane's) | `clone3` threads, `futex`, `clone` (fork) with `execve` of itself, `dup2`, `wait4`, `kill(SIGUSR2/SIGKILL)`, handlers for HUP/QUIT/TERM/USR2: px14's and px26's, not run with lobo here |

## 3. Prediction (committed before the first change)

### P1. AF_UNIX path sockets: the design

- **A Unix socket is a record of a new module, `kernel/unix`**, in a
  `.bss` table of 256 records (256 bytes each, 64 KiB): its state
  (fresh, listening, connected, or a connection queued on a listener),
  its type, the inode it is bound to, its name as bound (up to 108
  bytes, for `getsockname`), its peer, its two buffers, its backlog and
  queue, its shutdown bits. A descriptor names it as a new kind
  (`K_UNIX`, node `T_UNIX | record`) whose open file is shared by
  `dup` and `fork` as every other; the last close of the open file
  closes the record. `socketpair(AF_UNIX, …)` stays px17's (`K_SOCK`),
  given a record boundary for `SOCK_SEQPACKET` (P3).
- **A connected Unix stream** reads and writes two of kernel/files'
  pipe buffers, one each way, so every reading, writing, waiting, `poll`
  and epoll path a socketpair has is reused. Each buffer is **one
  frame** (4,096 bytes), as a socketpair's: Linux's stream buffer is
  far larger; what that changes is when a non-blocking writer meets
  -EAGAIN, which no probe prints and lobo's answers (under 1 KiB) never
  reach. The buffer records rise from 64 to 512 and a socket's node
  carries 16-bit buffer numbers (px17 packed 8).
- **The name is a node of px27's tree.** `bind` makes an inode of mode
  `S_IFSOCK | (0777 & ~umask)` (`unix(7)`: "all permissions enabled,
  other than those turned off by the process umask"; `srwxr-xr-x`
  under 022), size 0, one link, in the directory the path names; the
  socket holds the inode (an open file's hold), and the inode names the
  record while the socket lives. `stat` shows `S_IFSOCK`, `getdents64`
  `DT_SOCK` (12), `open` of it -ENXIO, `execve` -EACCES.
- **`unlink` of a bound name** removes the name only: the socket goes on
  listening and its connections go on, but nothing can reach it by the
  path again (`connect` -ENOENT), and a new `bind` of the same path
  makes a new socket's name. **The socket closed with its name still
  there** leaves the name (a stale socket file, as Linux leaves it:
  `unix(7)` NOTES): `connect` to it -ECONNREFUSED, `bind` to it
  -EADDRINUSE until it is unlinked.
- **`bind`:** the path in `sun_path`, up to `addrlen - 2` bytes, ending
  at the first NUL; `addrlen` over 110 -EINVAL; a family that is not
  AF_UNIX -EINVAL; a socket already bound -EINVAL; a name that exists
  (any kind of file) -EADDRINUSE; a missing directory -ENOENT; a file
  on the way -ENOTDIR; in `/dev` refused by name, -EROFS (px27's
  rule). An abstract name (`sun_path[0]` NUL) and autobind (`addrlen`
  2) are refused by name, -EINVAL: no strace asks them.
- **`listen(fd, backlog)`:** a negative backlog is the largest; the
  queue holds **backlog + 1** connections not yet accepted (measured,
  P9); `listen` on an unbound stream socket — Linux autobinds — is
  refused by name, -EINVAL; on a connected one -EINVAL. `listen` again
  on a listener changes the backlog.
- **`connect`:** the path resolved as `open` resolves it: missing
  -ENOENT, a component not a directory -ENOTDIR; **a name that is not a
  socket, or a socket nobody listens on (bound and not listening, or
  closed): -ECONNREFUSED**; a listener of another type -EPROTOTYPE; an
  already connected socket -EISCONN; a listening one -EINVAL. On a
  listener with room: a new record (the server's end) is connected to
  the caller's, queued on the listener, and `connect` answers 0 at once
  (before any `accept`). With the queue full: a blocking `connect`
  waits for room; a non-blocking one answers **-EAGAIN** (not
  -EINPROGRESS: a Unix connect never is in progress).
- **`accept4`:** the queue's head as a descriptor (`SOCK_CLOEXEC`,
  `SOCK_NONBLOCK`; another flag -EINVAL); an empty queue waits or
  -EAGAIN; a socket that does not listen -EINVAL; the peer's address
  when asked: the client's name, or an unnamed address (length 2).
- **Data:** `read`/`recvfrom` and `write`/`sendto`/`writev` as a
  socketpair's end, `MSG_DONTWAIT` and `O_NONBLOCK` as there;
  `sendto` with an address on a connected socket -EISCONN; on a socket
  not connected `send` -ENOTCONN and `recv` -EINVAL (measured, P9); a
  write after the peer's last close -EPIPE (SIGPIPE unless
  `MSG_NOSIGNAL`, through px17's path); a read after it 0 once the
  buffer is empty. `ioctl(FIONBIO)` on a Unix socket sets
  `O_NONBLOCK` (lobo does it to every one).
- **A listener closed with connections queued:** each queued
  connection's server end is closed with it: its client reads 0 or
  **-ECONNRESET** — the probe decides, and PAX answers what it shows.
  The same for a connection closed with bytes unread.
- **`shutdown(fd, how)`** (item 1's word): `SHUT_WR` makes the peer read
  end-of-file after what was written; `SHUT_RD` makes this end's reads
  answer 0; `how` over 2 -EINVAL; not connected -ENOTCONN.
- **`getsockname`** answers the bound name (length 2 + its length + 1,
  `unix(7)`) or an unnamed address (2); an accepted socket answers the
  listener's name; **`getpeername`** the peer's (the listener's name
  for a client), -ENOTCONN when not connected.
- **Options:** `getsockopt(SOL_SOCKET, SO_TYPE / SO_ACCEPTCONN /
  SO_ERROR)`; every other option, and every `setsockopt`, -ENOPROTOOPT
  by name.
- **Readiness** (kernel/files' `node_poll`): a listener `POLLIN` while
  a connection is queued, its edge count the connections ever queued;
  a connected socket as a socketpair's end (`POLLIN`, `POLLOUT`,
  `POLLHUP|POLLRDHUP` when the peer is gone); a fresh socket what Linux
  answers (P9). Every change wakes waiters through
  `sched.wake_pipes()`, as px24's readiness does.
- **Types:** `socket(AF_UNIX, SOCK_STREAM)` only; `SOCK_SEQPACKET` and
  `SOCK_DGRAM` on a path refused by name, -ESOCKTNOSUPPORT (px17's
  refusal for a socketpair's types); a protocol that is not 0
  -EPROTONOSUPPORT.

### P2. /proc and /sys: fixed text, said so

Two synthetic directories beside `/dev` (each its own file system, so
`rename` across is -EXDEV), holding exactly the files lobo reads, each
answered as Linux answers in a root cgroup with one CPU and no limit;
their text is **made at `open`** (a snapshot in a frame the open file
holds, given back at its last close), so a reader in small pieces never
sees it change under it; `statx` and `stat` answer `S_IFREG` with
Linux's modes (`0444`; `cpu.max` `0644`) and **size 0**, as procfs and
cgroupfs do; a write -EACCES (as root on Linux: -EACCES for `0444`,
measured, P9); `/proc/self/exe` stays px26's link.

- `/proc/self/status`: Linux 7.2.8's fields in its order and format
  (`proc-sys-container.txt`), PAX's values where PAX has them — Name
  (the thread's), Umask, State `R (running)`, Tgid, Pid, PPid, Uid and
  Gid 0, FDSize (the table: 1024 after P5), Threads, SigBlk, SigIgn,
  SigCgt (kernel/signal's), VmRSS and VmHWM the frames the space holds,
  Cpus_allowed `1`, Cpus_allowed_list `0` — and fixed values (0, or
  Linux's text for a process with no capability set and no seccomp)
  for what PAX does not keep. Fixed text where PAX has no fact, said so
  in the module.
- `/proc/self/cgroup`: `0::/` (cgroup v2, the root).
- `/sys/fs/cgroup/cgroup.controllers`: `cpu\n` — the one controller
  whose file lobo reads (Linux's root lists more; fixed, said so).
- `/sys/fs/cgroup/cpu.max`: `max 100000\n` (no limit, `cgroups(7)`).
- `/sys/devices/system/cpu/online`: `0\n` (one CPU).
- `/proc/sys/vm/overcommit_memory`: `0\n` (the heuristic, Linux's
  default).
- The directories list exactly these (`getdents64`); the root does
  **not** list `proc` and `sys` (the tree suites hold the root's
  listing to Linux's container root, which has them, but their own
  sessions never list `/`: checked, P10).

### P3. `SOCK_SEQPACKET` record boundaries (px17's drift closed)

A socketpair buffer of type `SOCK_SEQPACKET` holds each message with an
8-byte length in front of it: a write puts a message in whole or waits
(or -EAGAIN), a message larger than the buffer can ever hold (4,088
bytes) -EMSGSIZE; a read takes one message — at most what was asked,
the rest of it discarded (`MSG_TRUNC` answers the message's whole
length) — never two; a zero-length message is a read of 0 (Linux's
seqpacket answer, measured, P9). `poll` says `POLLIN` while a message
waits.

### P4. Stacks: `MAP_NORESERVE` backed on touch

`mmap(…, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE)`
reserves its range (a new kind of px26's reservation, "backed on
touch") and maps nothing; a touch from ring 3 that faults on a page of
it maps a zeroed frame there and resumes; a system call's buffer in it
is backed the same way before it is checked (kernel/uaccess), so a
`read` into an untouched page works as on Linux. `mprotect` of part of
it (the wolf runtime's 64 KiB guard, `PROT_NONE`) splits the range:
the guarded part faults for good. **`MADV_FREE` and `MADV_DONTNEED` on
it give the frames back** (the page reads zero at its next touch,
which both permit). `munmap` and `execve` end it. Mappings without
`MAP_NORESERVE` stay backed at the call (px12–px26), as no strace says
otherwise.

Measured (P8): a wolf task's stack costs the pages it touched — under
**32 frames** for the waiting wolf witness's tasks, against 2,072 —
and after the runtime's `MADV_FREE` of a parked task's stack, none
but the top page or so.

**A missing kernel stack answers -EAGAIN:** `sched`'s `make_stack`
returns false when frames run out instead of panicking; `clone` and
`clone3` answer -EAGAIN, refused by name ("no frame for a thread's
kernel stack"), as with no free slot. A kernel thread made at boot
still panics: that is the kernel's own, not a caller's.

`prlimit64(RLIMIT_STACK)` keeps answering PAX's 128 KiB main stack:
lobo's strace reads it and moves on; the runtime's task stacks are its
own `mmap`s. Not changed, said so.

### P5. Limits sized for `worker_connections 1024`

- **Descriptors: 128 → 1024 a process** (`RLIMIT_NOFILE` 1024, Linux's
  default soft limit). The process area grows from 8,192 to 40,960
  bytes a slot (512 words, then four words a descriptor): 64 slots,
  2,097,152 bytes more `.bss`.
- **Open files: 512 → 2048** (64 bytes each: 98,304 bytes more).
- **TCP blocks: 256 → 1024** (1 KiB each: 786,432 bytes more; a
  connection's 32 buffer frames are taken when it is used, not at
  boot, so 1,024 open connections cost 128 MiB only when they exist).
- **Pipe and socket buffers: 64 → 512** (256 bytes each: 114,688 bytes
  more); **Unix records 256** (65,536 bytes).
- Altogether about 3.1 MiB more kernel `.bss` (about 760 frames fewer
  free at boot). What px25 must still set: nothing for descriptors; a
  1,024-connection load needs about 4 GiB of guest memory for the TCP
  buffers alone — px25's config can keep `worker_connections 1024`
  with a guest of 512 MiB as long as the load stays near 100
  connections.

### P6. Syscalls added and refusals

No new syscall number: `socket`, `bind`, `listen`, `accept4`,
`connect`, `getsockname`, `getpeername`, `getsockopt`, `setsockopt`,
`shutdown`, `sendto`, `recvfrom` gain the AF_UNIX family; `openat` and
friends gain `/proc` and `/sys`. Refused by name (each counted on the
probe's `~refused` line): an abstract name, autobind (`bind` with
addrlen 2, `listen` unbound), `SOCK_SEQPACKET`/`SOCK_DGRAM` on a path
socket, any `setsockopt` on a Unix socket, an option other than the
three. `sendmsg`/`recvmsg` stay -ENOSYS (no strace).

### P7. Witnesses

- `user/unix/unixprobe.c` (static, `px13-ubuntu`): every item-1
  mechanism and errno above, seqpacket boundaries, the files of P2 and
  their `statx`, a `MAP_NORESERVE` region's backing (`~` lines where
  PAX's answer is its own by design); the same binary on Linux (pid 1
  in a throwaway container, tools/linux-tree) and PAX, byte-identical
  but the `~` lines.
- `user/unix/ctl.c`: a lobo-shaped control server (bind, `listen(-1)`,
  FIONBIO, the pid file, a `poll` loop of 250 ms, `accept4`, a verb, an
  answer, close) and, as its child, **`lobo -c conf/lobo.conf status`**
  (lobo `944edc1`, built by `tools/mklobo`): lobo's client prints the
  server's answer; then `stop` from a C client, the name unlinked.
- `unixprobe soak`: 10,000 connections connect, send, answer, close,
  through one listener in a second process; the kernel's census line
  every 2,500 (`unix: <n> connections since boot; sockets <s>, buffers
  <b>, frames free <f>`), flat.
- Plants, each red in CI by run id and reverted: a seqpacket read that
  takes two messages at once; an `unlink` that leaves the listener
  reachable by its old name.

### P8. Numbers

- A Unix connection costs 2 records and 2 buffer frames (8 KiB) while
  it lives; 0 after.
- The waiting wolf witness (px24's `waitwolf`): frames held by its
  tasks' stacks fall from about 2,072 a task to under 32 (P4); the
  witness boots in 256 MiB again where px24 needed 1 GiB.
- The status exchange on PAX: under 50 ms of guest time on KVM, under
  2 s on TCG.
- 10,000 Unix connections: under 30 s on KVM, under 5 minutes on TCG.

### P9. What the probe decides (Linux's answer taken as the rule)

The listen queue's length (backlog + 1 predicted); a queued
connection's client after its listener closes (-ECONNRESET predicted)
and a connection closed with bytes unread (-ECONNRESET predicted);
`recv` on an unconnected socket (-EINVAL predicted) and `send`
(-ENOTCONN); `poll` of a fresh socket (`POLLOUT|POLLHUP` predicted);
a seqpacket zero-length message (a read of 0); `getsockname`'s
length for a name bound without its NUL (2 + length + 1 predicted);
`connect` to a regular file (-ECONNREFUSED); a write to a `/proc` file
(-EACCES).

### P10. What moves

- `tests/mpx4-ready` and the other suites: `RLIMIT_NOFILE` 128 → 1024
  wherever a probe prints it (`restprobe`'s line, if it does); a
  socketpair's node encoding; the frames free at boot (fewer by the
  `.bss`). No transcript of the tree suites lists `/` (checked before
  the change).
- `user/net/waitwolf`'s boot memory (px24 used 1 GiB) can fall back.
- New: `tests/mpx4-unix` and its CI job; `tools/mklobo` and
  `user/lobo.pin`.

### P11. What fails first

The release tier's compile time (wolf-lang#711) on a longer
`kernel/files`; a uaccess path that copies into a page of a
`MAP_NORESERVE` range before backing it (a spurious -EFAULT); the
wolf runtime's reactor reading a Unix socket's `EPOLLRDHUP` at a time
PAX does not raise it.

## What was built

- **`kernel/unix`** (new; `boot/unix.S`): 256 socket records of 32
  words, a listener's queue through its queued ends, each socket's name
  as bound, the books (sockets live and made, connections, refusals)
  and the census every 2,500 connections.
- **`kernel/files`**, the calls (`unix_socket`, `unix_bind`,
  `unix_listen`, `unix_connect`, `unix_accept`, `unix_getname`,
  `unix_getsockopt`, `unix_setsockopt`, `unix_shutdown`, `unix_close`,
  `unix_poll`), reached from `kernel/socket` for AF_UNIX and for any
  descriptor that names a path socket; a connection's bytes cross two
  of the pipe buffers a socketpair uses (now 512, a node naming 16-bit
  buffer numbers), so `read`, `write`, `recvfrom`, `sendto`, `writev`,
  `poll` and epoll reach it as they reach a socketpair's end, with a
  path socket's own rules on top (not connected, shut, reset). `walk`
  split so a path already in `pax_kbuf` (a `sockaddr_un`'s) resolves
  as an `open`'s does (`walk_k`). `recv`'s MSG_PEEK and MSG_TRUNC
  read; FIONBIO taken on a socketpair's end too (Linux takes it,
  measured).
- **`socketpair(SOCK_SEQPACKET)`**: messages behind an eight-byte
  length, read one at a time, the rest of one cut off, `writev`'s parts
  one message; a message that can never fit (over 4,088 bytes)
  -EMSGSIZE.
- **`kernel/tree`**: `mksock`, an inode of mode S_IFSOCK naming its
  socket while the socket lives (`sock_of`, `sock_gone`).
- **`kernel/procfs`** (new): `/proc/self/status`, `/proc/self/cgroup`,
  `/proc/sys/vm/overcommit_memory`, `/sys/fs/cgroup/cgroup.controllers`,
  `/sys/fs/cgroup/cpu.max`, `/sys/devices/system/cpu/online` and the
  directories they sit in; text made at `open` into a frame the open
  file holds. `kernel/paging`'s `user_pages` for VmRSS.
- **`kernel/vm`**: MAP_NORESERVE read-write mappings backed on touch
  (a reservation of their own kind; `back`), from the page-fault path
  (`kernel/interrupts` → `kernel/user`'s `fault_in`) and from
  `kernel/uaccess` before a buffer is checked; MADV_DONTNEED and
  MADV_FREE give such a page's frame back; `mprotect` to PROT_NONE of
  part of one makes that part fault for good. Reservations 16 → 256 a
  process.
- **`kernel/sched`, `kernel/process`**: `make_stack` answers false
  where it panicked; `clone` and `clone3` answer -EAGAIN, refused by
  name ("no frame for a thread's kernel stack"); a kernel thread's own
  stack still panics (`make_stack_or_die`).
- **Limits**: 1,024 descriptors a process (`RLIMIT_NOFILE` 1024), 2,048
  open files, 512 buffers, 1,024 TCP blocks; the process area 8,192 →
  40,960 bytes (the descriptors, then kernel/vm's 256 reservations).
- **Tests**: `tests/mpx4-unix` and its CI job; `user/unix/unixprobe.c`,
  `user/unix/ctl.c`, `user/unix/lobo.conf`; `tools/mkunix`,
  `tools/mklobo`, `user/lobo.pin`; `tools/linux-tty` and
  `tools/linux-tree` learn `--sys` (sysfs and cgroup2 in the session's
  root, for the Linux side of `/sys`).

## 3. The prediction against the measurement

| | predicted | measured |
|---|---|---|
| P1 queue | backlog + 1 | 2 on a backlog of 1, the third -EAGAIN (Linux; PAX the same) |
| P1 `bind` | a name that exists -EADDRINUSE; a bound socket -EINVAL | as predicted, but the name is checked first: binding a socket to the name it already has is -EADDRINUSE, not -EINVAL (measured; PAX follows) |
| P1 `listen` unbound | refused by name, -EINVAL (autobind) | **wrong**: Linux answers -EINVAL itself (no autobind on `listen`): PAX answers -EINVAL with no refusal line |
| P1 `connect` | -ENOENT, -ENOTDIR; a file, a non-listener, a closed one -ECONNREFUSED | as predicted; a directory -ECONNREFUSED too; a wrong family, a length of 1 or of 111 -EINVAL |
| P1 a listener closed, a connection closed with bytes unread | -ECONNRESET predicted for both | **right**: -ECONNRESET once, then 0, `send` -EPIPE, `poll` IN OUT ERR HUP RDHUP; a queued client that sent nothing is reset too; a peer that closes with nothing unread is a clean end (data, then 0) |
| P1 `shutdown` | not connected -ENOTCONN | **wrong**: Linux answers 0 on a socket that is not connected and nothing changes (`poll` still OUT HUP); PAX the same |
| P1 types and protocol | protocol 0 only; SEQPACKET and DGRAM refused | protocol 1 (PF_UNIX) is taken too (2 -EPROTONOSUPPORT); Linux also takes SOCK_RAW (as a datagram socket): refused by name like the other two |
| P1 not connected | `send` -ENOTCONN, `recv` -EINVAL | right; `sendto` with an address on one -EOPNOTSUPP (not predicted; measured) |
| P1 `poll` | fresh OUT\|HUP | right; and a listener nothing until a connection waits, a connection by its two halves (table in `unix_poll`'s comment) |
| P2 files | text made at open; sizes 0 | right but one: `/sys/devices/system/cpu/online` is a sysfs attribute, size 4096; open for writing works as root and the write is -EINVAL (predicted -EACCES: **wrong**); `mkdir` in `/proc/self` -ENOENT |
| P3 seqpacket | boundaries, 4,088 the largest | right (Linux takes 8,000 bytes: `~seqpacket`) |
| P4 NORESERVE | backed on touch; under 32 frames a parked task | VmRSS +0 kB after the 8 MiB `mmap`, +12 kB after three pages and a `read` into a page never touched, -12 kB after MADV_DONTNEED and MADV_FREE (Linux: +0, +2,056 kB — transparent huge pages — and -4 kB); the waiting wolf witness: §4 (mpx4-ready's frames lines) |
| P4/P8 the waiting wolf witness | boots in 256 MiB where px24 needed 1 GiB | better: mpx4-ready's network-less run list (the probes, the epoll server's 10,000 connections, `waitwolf` loop, serve/call twice, push/pull) booted at **128 MiB**: every command exit 0 on this lane's kernel; on trunk's kernel `waitwolf` was killed (SIGABRT after `mmap` and `mprotect` -ENOMEM, out of frames) in run 9 and its `pair` exited 1 (`notes/px34/kasumi/{,trunk-}ready-none-128M.log`); at 256 MiB both ran all ten. The suite itself still boots at 1 GiB (not moved) |
| P4 kernel stack | -EAGAIN by name | right: `~stack: 244 MiB and 36 pages taken (no more to take); a thread then: EAGAIN`, its `refused:` line, and a thread made again once the memory came back (every leg, both hosts) |
| P5 limits | about 3.1 MiB more `.bss`, about 760 frames | `kmain_console`'s RW segment 1,249,376 → 4,411,488 bytes (+3,162,112: 772 frames), its text +45,968 bytes (12 frames), rodata +1,072 |
| P5 TCP memory | "1,024 connections need about 4 GiB" | **wrong arithmetic**: 32 frames (128 KiB) a connection in use is **128 MiB** for 1,024 |
| P6 refusals | six by name | six: SOCK_RAW, SOCK_SEQPACKET and SOCK_DGRAM on a path, `setsockopt`, an abstract name, autobind (`listen` unbound left the list, SOCK_RAW joined it) |
| P8 times | status under 50 ms KVM, 2 s TCG; 10,000 connections under 30 s KVM, 5 min TCG | KVM (hasu): lobo's client 0–30 ms by the guest's clock, the whole `ctl` boot 2–3 s; the soak 40–90 ms by the guest's clock for 10,000 connections (Linux in the container 72 ms), the whole soak boot 2–3 s. TCG: §4 |
| P10 what moves | no transcript lists `/`; RLIMIT_NOFILE nowhere printed | right for those; **missed**: mpx4-tcp's and mpx4-ready's T1 assert the `tcp: 256 blocks` line, red in the gauntlet (`g1-041a4c8/mpx4-tcp.out`, `mpx4-ready.out`); the line moved to 1024 in both suites (`b29fe25`) and both reran green on the same images (100/0, 102/0) |
| P11 what fails first | #711's compile time; a spurious -EFAULT; EPOLLRDHUP timing | none of the three: the release tier got **faster** (`kmain_console` 200 s → 54 s, `kmain_sockets` 180 s → 54 s, the same container, twice each; not investigated); what failed first was a name defined twice (`ring_put`, E0302), and the stack witness reusing a dead thread's kernel stack (`reap` runs at the next `clone`: the witness now keeps a thread parked) |

## What lobo's list now answers

Every line §2 marked "absent and this lane's" is answered as Linux
answered it, each proved by a line of `unixprobe` byte-identical to
Linux's (or, where PAX's answer is its own, by a `~` line the suite
holds to PAX's value):

- the control socket's whole life — `socket(AF_UNIX,
  SOCK_STREAM|SOCK_CLOEXEC, 0)`, `bind` to a relative path with its NUL
  counted, `listen(fd, -1)`, `ioctl(FIONBIO)`, `poll(POLLIN)` beside
  other descriptors, `accept4(…, SOCK_CLOEXEC|SOCK_NONBLOCK)`,
  `recvfrom` (-EAGAIN, then the verb), `epoll_ctl(ADD,
  EPOLLIN|EPOLLRDHUP|EPOLLONESHOT)` and the event back, `sendto(…,
  MSG_NOSIGNAL)`, `close`, `unlink` of the name — and the client's
  (`connect`, -ENOENT before the name exists, -ECONNREFUSED after its
  listener closed and before the name is unlinked, -EPIPE without a
  signal for an answer to a connection already closed); and, end to
  end, lobo's own `status` client against a server shaped as lobo's,
  its output byte-identical to Linux's (`ctl`, U1 and U6, every leg on
  both hosts);
- `socketpair(AF_UNIX, SOCK_SEQPACKET|SOCK_CLOEXEC)` with its messages
  kept (px17's drift closed);
- `/proc/self/status`, `/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`,
  `/sys/devices/system/cpu/online`, `/proc/sys/vm/overcommit_memory`
  opened, `statx`ed, `lseek(SEEK_CUR)`ed and read in glibc's growing
  pieces, and `statx` of `/sys/fs/cgroup/cgroup.controllers`;
- `mmap(…MAP_NORESERVE)` of a task's stack backed where it is touched,
  `madvise(MADV_FREE)` of it giving the frames back;
- the descriptor table at Linux's default soft limit, 1,024.

Named by item 1 and done on its word (no strace shows them on a Unix
socket): `shutdown`, `getsockname`, `getpeername`,
`getsockopt(SO_ACCEPTCONN)` (and SO_TYPE, SO_ERROR).

## What px25 still lacks

From lobo's list (§2's marks, after this lane), what PAX answers
otherwise than Linux, or what was never run with lobo:

- **lobo serving on PAX was not run** (px25's): no line of the serve
  strace beyond the control channel and the files above was exercised
  by lobo itself here; the master/worker spawn (`clone` without
  CLONE_VM, `execve` of itself, `dup2`, `wait4`, `kill(SIGUSR2)`,
  `SIGKILL`, handlers for HUP, QUIT, TERM, USR2) is px14's and px26's
  and unrun with lobo.
- `set_robust_list` (273) and `rseq` (334): -ENOSYS (glibc goes on).
- `prlimit64(RLIMIT_STACK)` answers PAX's 128 KiB main stack both ways
  (Linux: 8 MiB, unlimited).
- **glibc's thread stacks** (`mmap(PROT_NONE, MAP_STACK)` of 2 MiB and
  `mprotect` to read-write) are backed whole at the `mprotect` (px26):
  2 MiB a thread. lobo with one worker ran 25 threads on Linux, with
  four 112: about 50 MiB of thread stacks a process for one worker
  (lobo's own wolf tasks' stacks are MAP_NORESERVE and now cost what
  they touch). px25 sizes its guest for that, or a later lane backs
  those on touch too (not this lane's item: no strace marks them
  NORESERVE).
- A Unix connection's buffers are one frame each way (Linux's are far
  larger): a reply over 4 KiB waits for its reader, which lobo's
  non-blocking writes meet as -EAGAIN and an EPOLLOUT wait; never run
  with a reply that large.
- A seqpacket message is at most 4,088 bytes (Linux took 8,000; lobo's
  spawn channel sends 8 bytes, only when an `execve` fails).
- `/proc/self/status`: fixed values where PAX keeps nothing (VmPeak and
  VmSize are the resident pages, the capability sets 0);
  `cgroup.controllers` says `cpu` only.
- TCP: 1,024 blocks, but a connection in use holds 32 frames: 1,024 at
  once need 128 MiB of guest memory for TCP alone; `kernel/arp`'s
  two-frame queue (pax#32) and the virtio driver's 64 transmit buffers
  under many connections, as px24 left them.
- Not in lobo's request set and not on PAX: `sendmsg`, `recvmsg`,
  `SCM_RIGHTS`, `SO_PASSCRED`, `SO_PEERCRED`, abstract names, a
  datagram or seqpacket socket on a path, `SO_REUSEPORT`,
  `SO_KEEPALIVE`, `SO_LINGER`, `SO_SNDBUF`, `SO_RCVBUF`, `ppoll`,
  `epoll_pwait`, `timerfd`, `signalfd`.

## 4. Evidence index

- **The straces and the marked list**: `notes/px34/linux/lobo-944edc1/`
  (`w1/`, `w4/`: `serve`, `status`, `-s status`, `-s reload`, `-s stop`,
  `requests.out`; strace 6.8 `-f -s 256 -yy`, Linux 7.2.8, lobo
  `2dc94b06…`), `lobo.shapes.tsv` (100 lines), `strip-yy.py`,
  `build-lobo.sh`, `strace-lobo.sh`; the files' text:
  `proc-sys-container.txt`. The marked list: §2.
- **The probes on both**: Linux's transcripts before any kernel change,
  `notes/px34/linux/witness/{probes,soak,ctl}.linux.txt`; red first on
  the trunk kernel: `notes/px34/kasumi/red-trunk-7c2c70e.mpx4-unix.out`
  and its serial log (`cc26498c…`: AF_UNIX -EAFNOSUPPORT, seqpacket
  messages merged, the boot hung at the deadline); green: every leg of
  `tests/mpx4-unix` (probes 259 lines, soak, ctl 20 lines, each
  byte-identical to Linux's but the `~` lines U2 holds): kasumi TCG
  (`notes/px34/kasumi/g1-041a4c8/mpx4-unix.out`, 60 PASS) and hasu KVM
  (`notes/px34/hasu/k1-4dacb8d/` three rounds, `k2-35a8289/` one round
  and one under `taskset -c 0-3`, 60 PASS each).
- **The soak**: 10,000 Unix connections through one listener in a
  second process, four census lines flat (`sockets 3, buffers 2,
  frames free 62399` native BIOS; every leg flat), U4's books back to
  `unix: sockets 0, buffers 0`, frames and inodes as before.
- **lobo's client**: `lobo -c conf/lobo.conf status` (lobo `944edc1`,
  `faa15783…`, built by `tools/mklobo`) exit 0, the server's answer
  printed, byte-identical to Linux's (U6, every leg, both hosts).
- **The kernel stack**: `~stack: 244 MiB and 36 pages taken (no more to
  take); a thread then: EAGAIN` with `syscall 56: refused: no frame for
  a thread's kernel stack, -11` (U5, every leg); trunk panicked there
  (`sched: no frame for a stack`, px24's report; not re-run on trunk).
- **The wolf witness's memory**: `notes/px34/kasumi/ready-none-128M.log`
  (head, all ten commands exit 0) against
  `trunk-ready-none-128M.log` (`waitwolf` killed after -ENOMEM).
- **Planted breaks, red in CI and reverted**: A, seqpacket messages
  merged (`fc3d06a`), run **38192212617**: mpx4-unix U1 (the messages
  read as one), the boot held to its 300 s deadline; reverted
  `eae4e15`. B, an unlinked socket name kept (`67c1275`), run
  **38198179503**: mpx4-unix U1 and U4 (the inodes left), red in 3 s;
  reverted `c5bca96`. Every other job of 38198179503 green, mpx4-tcp
  and mpx4-ready with the 1024-block line among them.
- **Kernel build times** (kasumi, `px13-ubuntu`, the same container,
  twice each): `kmain_console` release trunk 200 s / 199 s, head 54 s /
  54 s; `kmain_sockets` release trunk 180 s, head 54 s; native 1–2 s
  both.
- **Boot counts**: kasumi TCG — the gauntlet: 167 boots in the twelve
  suites whose runs lists were kept (`g1-041a4c8/*-runs.txt`; mpx4-unix
  12) and the host suites' own (not counted), the reruns of
  mpx4-tcp and mpx4-ready on its images, the development runs of
  mpx4-unix (about 30), four readiness boots at 128 and 256 MiB; hasu
  KVM — mpx4-unix 60 boots (five rounds of 12, one under taskset), all
  `accel=kvm`; CI — the runs below.
- **The gauntlet** (`g1-041a4c8/summary.txt`, wolf 0.2.27 `6f5713a2…`,
  lupin 0.1.50, QEMU 11.1.1, strict env: `PAX_REQUIRE_UEFI=1`,
  `WOLF_PAIRING_REQUIRE_SIBLING=1`): every suite rc 0 but mpx4-tcp and
  mpx4-ready (T1, the `tcp: 256 blocks` line: P10's miss), both rc 0
  after `b29fe25` on the same images. 0 SKIP throughout.
- **CI green at head**: in the PR.

## 5. Done-when

- Branch `px34` on origin; PR wolffe-lang/pax#37, open, unmerged, the
  five sections by name, commit shas as bullets, a test checklist.
- CI green at the head (the PR names the run).
- `wolf/tools/lane-audit.sh pax px34 37` run from the org directory,
  its exit status read directly (in the PR).
- Trees: kasumi `~/lanes/px34/` pruned to the scripts, the evidence,
  lobo's build and the caches (build trees, gauntlet tree and trunk
  tree removed); hasu `~/lanes/px34/` the head's copy, the images and
  the evidence; no worktree; no process of the lane left. podman
  images untouched (`px13-ubuntu` is every lane's; this lane made
  none; every container ran `--rm`).
- Nothing merged, nothing tagged, nothing closed; nothing filed.
