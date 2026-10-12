# px25 — lobo on PAX (M-PX4)

Contract: px25's, `sprints/pax/25-lobo-on-pax/` in wolffe-lang/wolf
(read 2026-10-12). Branch `px25` in pax, cut from pax trunk `0f7cd28`
(px34 merged). §1–§3 are committed before the first change to the
kernel, the tests or CI; §2's straces were taken first.

One deliverable: **M-PX4** — lobo, static and unmodified, built from
its own tree at its release `v0.1.3` and at trunk, runs as a PAX
process, master and workers, and serves `/` and static files from
PAX's tree to the host (`curl` and a browser through `hostfwd`), with
`lobo -c CONF status`, `reload` and `stop` working; lobo's
differential rows that make sense on PAX run green.

## 1. Forbidden, absolutely

- No kernel's, libc's or network stack's source is read (ruling #22),
  and none is searched for; refs/linux's sparse checkout is never
  widened. Facts come from the man pages (`proc(5)`,
  `proc_pid_status(5)`, `signal(7)`, `poll(2)`, `restart_syscall(2)`,
  `kill(2)`, `wait4(2)`), the allowed uapi headers, and black-box runs:
  strace of lobo on Linux in `px13-ubuntu`, curl against lobo on Linux
  and on PAX.
- lobo is used as built from its own repository (`tools/mklobo`, the
  toolchain its tree pins), never changed here; a lobo defect is
  reported for a ws lane, not fixed.
- No system call or flag on a guess: each is in a strace this lane took
  of lobo (§2); anything else is refused with Linux's errno, by name.
  The test's own instruments (§3 P6: `/proc/meminfo`,
  `/proc/sys/fs/file-nr`, `/proc/net/sockstat`) are files `cat` reads,
  in Linux's format, argued in P6, and no lobo line depends on them.
- **No word implying filming, recording, viewers or a demo anywhere in
  pax.** The image is the lobo image (`tests/mpx4-lobo`). Test
  binaries only from `px13-ubuntu` on kasumi or the CI runner.
- No `rm` outside `~/lanes/px25/` on any host; no scratch in `/tmp`; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag; no trailer
  on a commit or the PR. Builds on kasumi only; KVM on hasu; nomad-1
  runs QEMU only for the browser path, with no audio device, and no
  QEMU is left running on any host. Kill by recorded pid only. At most
  two CI runs of this lane at once; another lane's never cancelled.
- Strict evidence (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, full output
  kept, SKIP counted; `wolf build` exit 2 is a compile error. Every
  plant fails fast, inside the suite's own deadline.
- px32 and px33 (sound, music) are in pax beside this lane: their files
  are not touched; `.github/workflows/ci.yml` gets one job appended.

## 2. Inputs, verified (2026-10-12)

| input | found |
|---|---|
| pax trunk | `0f7cd28` (px34 merged, PR #37): AF_UNIX path sockets, `/proc/self/{status,cgroup}`, the `/sys` files lobo reads, `MAP_NORESERVE` backed on touch, 1,024 descriptors a process, 1,024 TCP blocks, 64 thread slots (px24), threads, futex and signals (px26), the writable tree (px27) |
| the kernel's pin | wolf 0.2.27 (archive `5e17eebe…`), as `kernel/wolf.pin` |
| lobo, trunk | `944edc1` (0.1.3 with the channel flipped to `+dev`), `tools/mklobo` in `px13-ubuntu`: `faa15783…`, 14,697,600 bytes, `lobo/0.1.3+dev (built with wolf 0.2.27, pin 0ddda6b)` — the same bytes px34 built |
| lobo, v0.1.3 | `d6bd15b` (the release tree: `944edc1` is it plus the channel's flip), the same tool with the pin's revision changed: `ff480eb1…`, `lobo/0.1.3 (built with wolf 0.2.27, pin 0ddda6b)` |
| the straces | lobo at both revisions under `strace -f -s 256 -yy` in `px13-ubuntu` on kasumi (Linux 7.2.8, strace 6.8), **on one CPU** (`taskset -c 0`: what PAX's `sched_getaffinity` answers): px34's request set (keepalive, close, HTTP/1.0, a 300,000-byte file, a range, a HEAD, a 404, a conditional, proxied GET/POST, eight at once, `status`, `-s reload`, `-s stop`) plus this lane's: a file written into the root while serving, `kill -HUP` at the master, `kill -KILL` at one of four workers and its replacement, and `kill -TERM` (`notes/px25/linux/strace/`, `requests.out` per run; the straces over 200 kB gzipped). Every request answered as expected at both revisions |
| the shapes | px34's `shapes.py` over the straces: 104 lines at trunk (`lobo-trunk.shapes.tsv`), the same at v0.1.3 but for glibc's one `madvise(MADV_DONTNEED)` (present in v0.1.3's run, absent in trunk's: glibc's malloc trims when it will). Against px34's 100 lines, new: **`--- SIGHUP` delivered** (the master's handler, `SA_RESTART`), **`restart_syscall`** (the master's `poll(…, 250)` interrupted by SIGHUP, `ERESTART_RESTARTBLOCK`, resumed by the kernel after the handler), **`FUTEX_WAIT_PRIVATE`** (glibc, at a thread's join), and the `kill(<worker>, SIGKILL)` the master makes at `stop` and at reaping |
| threads | **6 a process on one CPU** (the master and each worker; no strace: `/proc/<pid>/task`), against 25 and 112 in px34's sixteen-CPU runs: the runtime sizes its pool by the CPUs it is given. Four workers: 30 threads, under PAX's 64 slots with pelt (2) and the kernel's four |
| memory on Linux | VmRSS of each process 2.8–4.9 MB (one CPU) |
| what Linux does that PAX does not, from the shapes | `set_robust_list`, `rseq` -ENOSYS (px34: glibc goes on); `restart_syscall` (PAX has no restart block: what a `poll` with a timeout answers to a handled signal is P2's question); `prlimit64(RLIMIT_STACK)` 128 KiB (px34) |
| a replaced worker on Linux | comes back serving at **generation 1** while its siblings are at 3 after two reloads (`lobo-trunk/w4/requests.out`: `worker 1: … generation=1 … restarts=1`): lobo's, on Linux; a finding for the orchestrator, not a PAX row |
| the pid file | `logs/lobo.pid` holds the control endpoint (`unix:logs/control.sock`), **no pid** (wolf-lang#126): a signal to the master on PAX needs its pid from the shell (`$!`) |
| lobo's differential suites | `tests/differential/cases/` 24 static rows (4 with a `--- server` section: `max_ranges 0`, `max_ranges 1`, two `alias`), `proxy-cases/` 7 rows (a scripted backend), `proxy-https-cases/` 1 row (the pinned nginx as a TLS upstream), `tools/lobo-control-differential` rows 1–8 and deltas D1–D3, `tools/lobo-signal` (a SIGHUP reload against a control reload, one line apart), `tools/lobo-prefork` (the gap across a worker's crash). Each is lobo against the pinned nginx; on PAX the comparison is **lobo on PAX against the same lobo on Linux** with the same config and tree |
| one boot before this prediction | disclosed: **one exploratory boot** of trunk's `kmain_session` with an initramfs of pelt, six boreutils, lobo `944edc1` and a `/srv` tree, kasumi TCG, 512 MiB, BIOS, `worker_processes 1` (`notes/px25/kasumi/x1-trunk/`): at pelt's prompt `cd /srv; lobo -c conf/lobo.conf serve &`, lobo's four notice lines, then from kasumi through `hostfwd` `curl /` → `200`, 187 bytes, the page; `/big.txt` → `200 300000`; `lobo -c conf/lobo.conf status` printed the stanza; `lobo -s stop` → `stop: shutting down (generation 1)`, `$?` 0; `exit`, the session's closing lines, `halt`. Nothing below was run before it was written |

## 3. Prediction (committed before the first change)

### P1. What fails first

The single worker served on trunk's PAX (§2's one boot). In the order
the items will reach them, what fails first:

1. **`worker_processes 4` at 256 MiB runs out of frames.** Each
   process holds its loaded image (lobo's 14.7 MB), six threads'
   glibc stacks backed whole at `mprotect` (px34: 2 MiB each, 12 MiB),
   its heap and the runtime's stacks: about **30 MiB a process**. Four
   workers and a master are about 150 MiB on top of pelt's 15 MiB and
   the kernel's: at 256 MiB the fourth or fifth process's `execve` or a
   thread's stack fails (`-ENOMEM`, `-EAGAIN`). At 512 MiB, four
   workers start.
2. **`kill -HUP` from pelt**: the master's `poll(…, 250)` is
   interrupted, and where Linux restarts it (`restart_syscall`) PAX
   answers -EINTR (px26: only reads, pipe writes, `wait4`, `waitid`
   and an untimed futex restart). Predicted harmless: wolf's runtime
   loops on -EINTR, and the reload completes.
3. **The worker kill**: `kill -KILL <worker>` from pelt; the master's
   supervision (a connect to the worker's control socket every 200 ms,
   three silences) reaps it with `wait4` and spawns a replacement
   (fork, `execve` of `/proc/self/exe`, the listener inherited as
   descriptor 3). Predicted to work: every call is on px34's marked
   list as present. The replacement serves within 4 s.
4. If none of those fails, the first failure is **under load**: the
   transmit path (64 virtio buffers, `kernel/arp`'s two-frame queue,
   pax#32) dropping or stalling under many short connections through
   the forward. Predicted: no stall at the forward's own pace (px24
   measured 57–81 connections a second through it on kasumi), because
   the forward, not PAX, is the slower end.

Nothing in the kernel is predicted to need a new system call; the
changes predicted are P6's files and whatever items 1–3 find.

### P2. Signals between lobo's processes

- SIGUSR2 (the runtime's own `kill(getpid(), SIGUSR2)` to retire its
  signal forwarder), SIGCHLD (a worker's end), SIGHUP, SIGTERM,
  SIGQUIT (handlers, `SA_RESTART`) and SIGKILL are delivered as px26
  built them. `poll` with a timeout and `epoll_wait` answer -EINTR to a
  handled signal (Linux: restarts `poll` through `restart_syscall`;
  `epoll_wait` -EINTR always, `signal(7)`). Predicted: no change
  needed, and named as drift in the row.
- `kill -TERM <master>` from pelt stops lobo as `-s stop` does (the
  same code path: lobo's CONTROL.md), with the workers' `kill(…,
  SIGKILL)` at the end.

### P3. Memory

| | predicted on PAX | Linux (one CPU) |
|---|---|---|
| one worker (one process) | 30 MiB ± 10 (7,700 frames) | 3.0 MB RSS |
| four workers (five processes) | 150 MiB ± 40 | 5 × 2.8–4.9 MB |
| the image's floor (BIOS) | 256 MiB for one worker, 512 MiB for four | — |

PAX's figure is frames taken from the free count between the prompt
and lobo serving (P6's `/proc/meminfo`). The gap from Linux is the
loaded image (Linux maps it from the page cache, shared), the glibc
thread stacks backed whole, and the heap's arenas.

### P4. Requests a second through `hostfwd`

A host client, one request at a time, `/` (187 bytes):

| | a new connection each | keepalive, one connection |
|---|---|---|
| TCG kasumi, native kernel | 40–80 | 150–400 |
| TCG kasumi, release kernel | 50–100 | 300–800 |
| KVM hasu, native | 20–40 (the forward's pace there: px24 17–37) | 1,000–3,000 |

Out by more than 3× either way is wrong. The 300,000-byte file: 3–10
MB/s on TCG (px23's 7–11 MB/s out of PAX through the forward).

### P5. lobo's differential rows on PAX

Each row compared as **lobo on PAX against lobo on Linux** (same
binary, same config, same tree with every file's time at 0, as PAX's
initramfs has it), the `Date` value normalized as lobo's NORMALIZE
does:

- **static, 24 rows**: all run; the four `--- server` rows each on a
  server block of their own (one config, five ports, five forwards).
  Predicted 24/24 identical. (Against the cases' pinned `--- expect`
  the rows that carry the corpus time — `Last-Modified`, `ETag`,
  `If-Range` by date or tag — differ on both sides alike: the expect
  pins 2026-01-01, PAX's files are from 1970 and cannot be touched:
  `utimensat` has no builtin user, bu21.)
- **proxy, 7 rows**: run, the scripted backend on the host at
  10.0.2.2 for PAX and 127.0.0.1 for Linux. Predicted 6/7 identical
  and `xff` differing by exactly the client address (`10.0.2.2` on
  PAX, `127.0.0.1` on Linux): named, not a defect.
- **proxy-https, 1 row**: not applicable: its upstream is the pinned
  nginx with OpenSSL serving TLS, which the pool does not build and
  PAX's image does not carry.
- **control differential**: rows 1 (an edited root picked up by
  `reload`), 2 (no refusal across a reload under a hammer — item 3's
  reload under load), 3 (an open keepalive connection keeps its
  generation), 4 (a bad config refused, the old one serving, `-s
  reload` exit 1), 5 and 6 (relative `pid`, `control`, `root` and
  `alias` against `-p`, started from `/`): run. Rows 7 and 8
  (`worker_shutdown_timeout`, a 2 s window): run on KVM only, named on
  TCG (the window is wall-clock and TCG's guest clock lags). D1–D3 are
  nginx-against-lobo deltas, not rows: not applicable.
- **signal**: `kill -HUP` against `lobo -s reload`, the five-line
  blocks one line apart (`source=signal` / `source=control`): run.
- **prefork**: a worker killed under a request stream: run, the gap
  measured.

### P6. The census files (the test's instruments)

The load item asks for RSS, frames, descriptors and TCP blocks flat.
PAX prints none of them while a program runs. Three files of Linux's
`/proc`, in Linux's format with PAX's values, read by `cat` from pelt
between load rounds:

- `/proc/meminfo`: `MemTotal`, `MemFree`, `MemAvailable` (frames × 4
  kB), Linux's first three lines; nothing more (said so).
- `/proc/sys/fs/file-nr`: open files allocated, `0`, the maximum
  (`proc_sys_fs(5)`).
- `/proc/net/sockstat`: `sockets: used`, `TCP: inuse orphan tw alloc
  mem`, `UDP: inuse mem` (Linux's lines; `orphan` and `mem` fixed 0,
  said so).

A process's RSS is not readable from another process on PAX
(`/proc/<pid>/` is only `self`): the frames free is the measure, and
lobo's own `status` stanza (`live-region-bytes`, `mem-hw`) beside it.

### P7. The image and the test

`tests/mpx4-lobo`: `kmain_session` (unchanged) with an initramfs of
pelt, six boreutils (`cat echo ls mkdir rm sleep`), lobo, `/srv`
(`conf/lobo.conf`, `html/` with the page, `big.txt` of 300,000 bytes,
`small.txt`), booted with `-nic user,…,hostfwd=…`; COM1 typed by a
driver that also runs the host's requests. Sessions: `serve` (one
worker: every item-2 request, a file written by `echo >` and served,
`status`, `reload`, `stop`), `hands` (four workers, a worker killed and
replaced, SIGHUP, SIGTERM), `load` (item 3), `diff` (item 4). Plants:
**a worker that never gets its listener** (the inherited descriptor
closed across `execve`) and **a reload that loses the control socket**
(the listener's name unlinked at reload) — each red in CI by run id.
Deadline per boot 300 s.

### P8. What moves

Nothing existing: no kernel change is predicted beyond P6's three
files (and what P1 finds), so every other suite's transcript holds;
`kmain_*`'s bytes move with `kernel/procfs`. New: `tests/mpx4-lobo`,
its CI job, the driver.
