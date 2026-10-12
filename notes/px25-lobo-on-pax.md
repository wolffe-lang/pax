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

## What was built

- **`kernel/procfs`, `kernel/files`, `kernel/sched`, `kernel/paging`**
  (`e53b536`, `f812ea9`, `0276c45`): `/proc/<pid>/status` for every
  process not yet reaped (`/proc` lists their numbers after its fixed
  names, Linux's order; the fields of `self`'s, the named process's
  leader's values, `State` `S (sleeping)` or `Z (zombie)` — fixed, said
  so), `VmPTE` the page tables' frames (it was 0), and the census
  files `/proc/meminfo` (MemTotal, MemFree, MemAvailable),
  `/proc/sys/fs/file-nr` and `/proc/net/sockstat` (`sockets: used`, the
  TCP and UDP lines; `/proc/net` a directory where Linux has a link to
  `self/net`: named drift). Why: pelt has no `ps`, lobo's pid file
  holds no pid (wolf-lang#126), so a worker's pid for item 1's SIGKILL
  and item 3's census (RSS, frames, descriptors, TCP blocks) had no way
  out of PAX. No lobo line uses them.
- **`kernel/tcp`** (`f1a1e01`): **a reset at RCV.NXT ends a time-wait
  entry**, as Linux does (`tools/tw-probe`, below); any other reset is
  still ignored (RFC 1337). The one kernel defect lobo tripped on (§3,
  P1 4). The counters line gains `ended by a reset` (mpx4-tcp and
  mpx4-ready's patterns follow).
- **The test kit**: `user/lobo/kill.c` and `tools/mklobokit` (kill(1)'s
  shape: pelt has no `kill`), `tools/mklobo OUT release` (lobo's v0.1.3
  tree, `d6bd15b`, and its differential data kept),
  `tools/lobo-session` (types a session at PAX's console or at `bash`
  in a Linux container, with this host's requests, a backend, held
  keepalive connections, loads, host commands, a fixed port),
  `tools/lobo-check` (PAX against Linux, reply for reply),
  `user/lobo/{srv,requests,steps}`, `tests/mpx4-lobo` and its CI job,
  `tools/tw-probe`.
- **Plants**, each its own commit, run by its own CI run on its own
  branch, reverted. A first pair was planted before the time-wait fix:
  A `f0a66be` (dup2 keeps a TCP socket's close-on-exec), reverted
  `6cdc2c6`, **never went red as planted**: its run 38222405571 held
  every hands step (the listener a worker inherits did not carry the
  flag that plant copied), and its one red row was the time-wait
  defect's (release control row 2, 2 timeouts); B `1f7abba`, reverted
  `29f105b`, was not run. Both were planted again on the head, past the
  fix: A2 `2400aae` (dup2 marks a TCP socket's copy at 3 or above
  close-on-exec: a worker never gets its listener), reverted `78b566e`;
  B2 `9b56ed7` (a Unix listener readable only until its first
  connection: the reload after `status` is never answered), reverted
  `7e31dae`. Each was red on kasumi before CI (`kasumi/plants/pa2`:
  hands, `request 1 of 20: timed out` in 38 s; `pb2`: serve, `the
  master … did not answer within 2000 ms`, `reload complete` not seen,
  66 s).

## 3. The prediction against the measurement

| | predicted | measured |
|---|---|---|
| P1 1: four workers at 256 MiB out of frames | ~30 MiB a process; the fourth or fifth fails | **wrong**: master and four workers start and serve at 256 MiB (`kasumi/x3-procfs`): 33.8 MiB of frames for the five (MemFree 140,416 → 106,624 kB), each process's VmRSS 5,848–5,852 kB, 6 threads each |
| P1 2: `kill -HUP` | poll -EINTR where Linux restarts; harmless | **right in effect**: the reload completes (`signal-received sig=reload … source=signal`, fanned out to the four); whether lobo's poll saw -EINTR was not looked at |
| P1 3: the worker kill | reaped and replaced within 4 s | **right**: `worker-exited worker=N reason=unreachable code=-1` then `worker-started … restarts=1`, as on Linux; the replacement serves (CI and every leg) |
| P1 4: under load, the transmit path | no stall at the forward's pace | **wrong in its place, right that load finds it**: at KVM's pace (500–1,500 connections a second) a client now and then waited out its 20 s timeout: QEMU's user network reuses this host's port inside PAX's 60 s time-wait; PAX answered the SYN below RCV.NXT with the old ACK, ignored the reset that came back (RFC 1337), and so on until the wait ran out (counters: `12 segments answered, 12 resets ignored`, 4 failed of 38,485). Linux ends the wait on that reset (`tools/tw-probe`). Fixed `f1a1e01`: `40 ended by a reset`, 0 failed of 48,844 and 45,766 (`hasu/tw/`). TCG's pace never reached it |
| first thing that failed | P1 1 | **the tooling, not the kernel**: pelt has no `kill`, nothing gives a worker's pid, PAX printed no census (P6, built) |
| P2 signals | as px26 built them | right: HUP (reload), TERM (stop, `source=signal`, fanned out), KILL (a worker), the runtime's own USR2, SIGCHLD to the master |
| P3 memory | 30 ± 10 MiB one process; 150 ± 40 MiB four workers; 256 MiB / 512 MiB floors | **wrong, too high five times**: ~6 MiB a process (VmRSS 5.8–6.9 MB), 32–35 MiB for five at the census's start (`lobo-rss` 32,084–34,748 kB); both shapes at 256 MiB. The loaded image is not copied whole and the runtime's stacks are backed on touch (px34) |
| P4 requests a second, TCG kasumi native | new 40–80, keepalive 150–400 | one worker: new 87–94, keepalive 157 (kasumi's load average ~14, `kasumi/conc1`); **four workers: new 30–39, keepalive 37–43** (`conc4`, `conc4b`, `k4`): four workers on one CPU are three to four times slower than one (the cause not isolated: px24's wake-every-waiter readiness is the likely one); 377 a second from two clients on a quiet host (hands, earlier) |
| P4 TCG CI native | — | hands' load 104 a second (two clients, four workers) |
| P4 KVM hasu native | new 20–40, keepalive 1,000–3,000 | new **520–1,540** a second (four workers; the forward is not the limit on hasu here); keepalive: §4 (`hasu/k2-…/*-conc*`) |
| P4 300,000-byte file | 3–10 MB/s TCG | 1.5 MB/s TCG under four clients (5.1 a second); KVM mixed with `/` 520–600 requests a second |
| P5 static rows | 24/24 identical | **right**: 24/24 byte-identical to lobo on Linux (Date normalized), every leg |
| P5 proxy rows | 6/7 and `xff` differing by the address | **right with the rule made general**: 7/7 client replies identical; the backend's records identical once 10.0.2.2 is read as 127.0.0.1 — the `Host` lobo sends upstream carries the backend's address too, not only `xff` |
| P5 proxy-https | not applicable | as predicted (its upstream is the pinned nginx serving TLS) |
| P5 control rows | 1–6 run; 7–8 KVM only | 1, 2, 3, 4, 5/6 run and pass on every leg; **7 and 8 not run** (named in §4); the signal row passes |
| P5 one server block a lobo | (not foreseen) | lobo serves its first `server` block only at this pin (lobo's docs/DRYRUN.md): the four static configs are four lobo processes, `conf/d1.conf` … `d4.conf` |
| P6 census files | as specified | built; their shape held to Linux's (R13: meminfo's three lines are Linux's first three, file-nr three numbers, sockstat Linux's three line shapes) |
| P7 the image and the test | as specified | as specified, plus `serve-release` (lobo v0.1.3), `control` and `browser` (by hand); a session that does not hold stops the boots |
| P8 what moves | nothing existing | mpx4-tcp's and mpx4-ready's counters pattern (the new `ended by a reset`); every kernel's bytes |

## lobo's differential rows on PAX (item 4)

Each row lobo on PAX against the same lobo on Linux, the same config
and tree (every file's time 0), the same requests (`tools/lobo-check`).

| suite | row | on PAX | how compared |
|---|---|---|---|
| `tests/differential/cases` | 24 static rows (`static_basic`, `head`, `cond304`, 19 `range_*`, 2 `alias_*`) | **run, 24/24 identical** | reply bytes, `Date` normalized |
| `tests/differential/proxy-cases` | 7 rows (`chunked`, `hopbyhop`, `keep`, `respheaders`, `rewrite`, `strip`, `xff`) | **run, 7/7 identical; 7/7 upstream records identical** | client reply bytes; the backend's record with 10.0.2.2 read as 127.0.0.1 (PAX reaches this host as 10.0.2.2: `Host` upstream, `X-Forwarded-For`, `X-Real-IP`) |
| `tests/differential/proxy-https-cases` | `https_upstream` | **not applicable**: its upstream is the pinned nginx serving TLS, which the pool does not build and the image does not carry | — |
| `tools/lobo-control-differential` | 1 config re-read | **run, pass** | the edited root served after `-s reload` |
| | 2 the listener survives a reload | **run, pass** (0 failed of 2,622–8,118 on TCG) | a load across the reload |
| | 3 an open keepalive connection keeps its generation | **run, pass** (identical to Linux) | a held connection, before and after |
| | 4 a bad config refused, exit 1, the old one serving | **run, pass** | `reload rejected`, `$?` 1, the old root served |
| | 5, 6 relative `pid`, `control`, `root` against `-p` | **run, pass** | started from `/` with `-p /srv` |
| | 7, 8 `worker_shutdown_timeout` (a drain, a streamed download, 2 s) | **not run**: they need a slow upstream stream and a 2 s wall-clock window this lane did not build into the sessions; nothing on PAX is known to stop them (named in "Not verified") | — |
| | D1–D3 | **not applicable**: nginx-against-lobo deltas, not rows | — |
| `tools/lobo-signal` | SIGHUP against `-s reload` | **run, pass** | the five-line event blocks differ in exactly `source` |
| `tools/lobo-prefork` | a worker killed under requests | **run, measured** | hands' `load gap`: TCG 0 failed (kasumi 9,444, CI 2,601); KVM before the time-wait fix 2 of 33,951 timed out (the time-wait cause, not the kill) |

## What moved at the rebase (trunk `6316c51`: px32, the orchestra)

px32 merged while this lane ran; it touches none of this lane's files,
no kernel file and no tool this lane uses, and `.github/workflows/ci.yml`
gained `mpx3-orchestra` beside this lane's `mpx4-lobo` (29 jobs, both
kept). The rebase moved every sha. Every sha named in this note and
every evidence directory (`k2-d71ff80`, `g4-d71ff80`) is the
pre-rebase one; the plants ran in CI on their pre-rebase shas, on their
own branches. The kernel, the images' bytes and the tests are the same
after the rebase as at `d71ff80` but for `tools/lobo-check` (its
prompt rule, `e2d9362`/`45f3602`, run against CI's artifacts before
the rebase).

| before | after |
|---|---|
| `c64f646` | `b0c7d70` |
| `e53b536` | `fe34b0d` |
| `f812ea9` | `51ca314` |
| `0276c45` | `8213abe` |
| `4603ad2` | `87c75e4` |
| `f1a1e01` | `77488a8` |
| `a97781b` | `777243e` |
| `0990452` | `f23698f` |
| `5daf2ff` | `9a20b6f` |
| `bf8630c` | `284dfa7` |
| `935fda4` | `d16502a` |
| `48724ec` | `b58dc45` |
| `86f7c63` | `39f308b` |
| `e8a2bb3` | `627e8a2` |
| `ded3a11` | `050d4eb` |
| `812a20f` | `f1e1c25` |
| `b5fb08c` | `ecacf37` |
| `605e401` | `eb0486d` |
| `732e011` | `5fe54c4` |
| `d71ff80` | `29a56a2` |
| `112d068` | `872a915` |
| `dc89031` | `e2d9362` |
| `34d3ce6` | `45f3602` |
| `2400aae` | `80f114b` |
| `78b566e` | `8f96016` |
| `9b56ed7` | `2045313` |
| `7e31dae` | `412e542` |
| `f0a66be` | `1c4855d` |
| `6cdc2c6` | `fadf6a3` |
| `1f7abba` | `0515855` |
| `29f105b` | `5dabdc6` |
| `0608c5a` | `a5de162` |
| `baba4a9` | `0f680a1` |
| `671f3b9` | `3d401d1` |
| `1af7cad` | `28784a7` |
| `0417440` | `8fc8d9e` |
| `50b68c9` | `f35a4cd` |

## M-PX4

**Met** (the CI run at the head is named in the PR): lobo, static and
unmodified, built from its own tree at its release v0.1.3 (`d6bd15b`,
`ff480eb1…`) and at trunk (`944edc1`, `faa15783…`), runs as PAX
processes — one process, and a master with four workers (fork, `execve`
of itself, the listener inherited) — started at pelt's prompt, and
serves `/` and static files from PAX's tree, and a file written at the
prompt, to the host through QEMU's `hostfwd`: curl on kasumi (TCG),
hasu (KVM), the CI runner, and nomad-1, where Safari fetched the page
too (lobo's access log at the prompt shows its request, `Version/26.4
Safari/605.1.15`). `lobo -c CONF status`, `-s reload` and `-s stop`
work, and SIGHUP, SIGTERM and a worker's SIGKILL (replaced by the
master) do. lobo's differential rows that make sense on PAX are
identical to lobo on Linux (the table above). One kernel defect was
found and fixed on the way (time-wait reuse under load, `f1a1e01`).

The page's bytes: 238 bytes, `GET /` on PAX byte-identical to
`user/lobo/srv/html/index.html` (R3, every leg; nomad-1: `cmp` of
curl's body, `nomad-1/browser-{1,2}/page.html`), and the whole reply
identical to lobo's on Linux but for `Date` (R1).

## 4. Evidence index

- **The straces**: `notes/px25/linux/strace/` (lobo at both revisions,
  one CPU, one worker and four, `strace -f -s 256 -yy`, Linux 7.2.8,
  strace 6.8; the larger straces gzipped), `lobo-{trunk,v013}.shapes.tsv`
  (104 lines), `strace-lobo.sh` (its ports are inside a container on
  kasumi). The marked list: §2.
- **Probe verdicts**: `tools/tw-probe` on Linux
  (`notes/px25/linux/tw-probe/linux-7.2.8.txt`, four runs: the SYN below
  RCV.NXT answered with the old ACK, this host's own reset, the SYN
  taken); PAX's side: `notes/px25/hasu/tw/` (the same KVM load on the
  kernel before the fix, `tw-kx1-…`: 4 of 38,485 failed, `12 segments
  answered, 12 resets ignored`; after it, `tw-kx2-…` twice: 0 failed of
  48,844 and 45,766, `40 ended by a reset`). The census files' shape
  against Linux: R13 in every load check.
- **The host's requests and the page bytes**: every session's
  `resp/` on both sides and `.check` (R1, R3, R4), kasumi
  (`kasumi/g4-d71ff80/`), hasu (`hasu/k2-d71ff80/`), CI (the run's
  artifact `pax-mpx4-lobo`); nomad-1 `nomad-1/browser-{1,2}/` (curl's
  head and body, `cmp` same, Safari's request in lobo's access log) and
  `nomad-1/maintainer-pty.txt` (the maintainer's commands below, typed
  into a pseudo-terminal: the prompt in 2.4 s, the page `cmp` same,
  stop, `exit`, `halt`; and `maintainer-pty-2.txt`, the same with
  Ctrl-A X at the end: QEMU ended by itself, status 0; no QEMU left).
- **Load figures**: `kasumi/g4-d71ff80/g4-{native,release}-load.check`
  and `hasu/k2-d71ff80/{native,release}-load.check` (the census lines,
  R10 flat, R11 every round 0 failed, R12 lobo's resident set);
  concurrency on KVM `hasu/k2-d71ff80/*-conc{1,4}/`, on TCG
  `kasumi/conc1`, `conc4`, `conc4b`, `k4`.
- **Differential table**: above.
- **Plants by run id**: A2 (`2400aae`, branch `px25-plant-a2`) run
  38227647983, `mpx4-lobo` red for the reason it names and no other:
  serve and serve-release held, then `native bios hands: … request 1 of
  20: timed out`, `stopped early` (`ci/ci-38227647983-…`); B2 (`9b56ed7`, branch `px25-plant-b2`) run 38234040400, `mpx4-lobo` red for the reason it names: `native bios serve: … '^reload complete \(generation 2\)' not seen in 60 s`, the reply after it missing, `stopped early` (`ci/ci-38234040400-…`);
  locally `kasumi/plants/`. The first A (`f0a66be`, run 38222405571) did
  not go red as planted (above).
- **Boot counts**: kasumi TCG — exploratory x1, x2 ×2, x3; development
  sessions about 20; conc ×3, k4; the head's gauntlet 15
  (`kasumi/g4-d71ff80/mpx4-lobo-runs.txt`), an earlier gauntlet at
  `29f105b` 15; the experiment kernel 0 (its runs were on hasu). hasu
  KVM — k1 (`29f105b`) 11, the time-wait experiment 4, k2 (`d71ff80`)
  15. nomad-1 TCG — 4 (two browser sessions, two typed by pty). CI —
  the runs named in the PR.
- **CI**: at `ee9bf57` (the rebased head before the probe fix) run 38232957625: `mpx4-lobo` PASS, 15 boots (`ci/ci-38232957625-…`), only mpx4-unix's race red; CI green at the final head: the run named in the PR.

## Not verified

- Control differential rows 7 and 8 (`worker_shutdown_timeout`).
- The cause of four workers being three to four times slower than one
  on one CPU (TCG and KVM alike; px24's wake-every-waiter readiness is
  the likely one, not isolated).
- Why TCG native's rate fell between rounds 1 and 2 in one gauntlet
  (44 → 19 a second; release steady at 220; kasumi's load average
  was ~14 from other work).
- Under KVM a reused port still costs a client one SYN retransmission
  (about a second: rounds of 15 s took up to 21 s); Linux avoids it with
  TCP timestamps (PAWS), which PAX does not send (px23's debt list).
- Whether lobo's `poll` saw -EINTR at SIGHUP (lobo's reload completed
  either way).
- The maintainer's commands with a browser typed by a person: Safari was
  opened by `open` from the script, and its request seen in the access
  log; no screenshot (not required).
- UEFI on hasu (KVM legs were BIOS); UEFI ran on kasumi and CI.

## Findings for the orchestrator (lobo's, not PAX's)

- lobo serves its first `server` block only (docs/DRYRUN.md says so);
  a config with servers on several ports serves one.
- A worker the master replaced comes back at `generation=1` while its
  siblings are at the current one, on Linux too.
- lobo's resident set grows under load on both sides (rounds 1→3: PAX
  +11–14 MB, Linux +144 MB), and its thread pool by a thread now and
  then; its pid file holds no pid (wolf-lang#126).
- On PAX every accept goes to worker 1 (`accepted=` in `status`); on
  Linux they spread.
- trunk's own CI run 38207077489 failed `mpx4-unix` (U1: `epoll_wait 1,
  IN` against Linux's `IN HUP RDHUP`), a timing difference not of this
  lane; this lane's run 38222398830 passed it and its run 38226927218
  (head `34d3ce6`, `45f3602` after the rebase) failed it with the same
  line while `mpx4-lobo` there passed, 15 boots: a race in px34's
  probe (whether the peer's close lands before `epoll_wait`), seen with
  and without this lane's changes. **Fixed here** (`user/unix/unixprobe.c`):
  the server closes only after the client says its `epoll_wait` is
  over, and the client waits for that close before it reads to the end,
  so both sides print `epoll_wait 1, IN` and `then the end` whatever
  runs first. mpx4-unix then passed three times on kasumi, native BIOS,
  against a fresh Linux side (`kasumi/unix-race/`); CI at the head runs
  it on every leg.

## What the next PAX lanes inherit

- `/proc/<pid>/status` for every process, `/proc/meminfo`,
  `/proc/sys/fs/file-nr`, `/proc/net/sockstat`, a real `VmPTE`: a
  census any test can read at the prompt.
- `tests/mpx4-lobo` and its tools: `tools/lobo-session` drives any PAX
  image and the same steps on Linux in a container, with requests,
  backends, held connections, loads and host commands;
  `tools/lobo-check` compares them reply for reply; `user/lobo/kill.c`.
- Time-wait ended by a reset at RCV.NXT (Linux's behaviour).
- Open: per-object wait queues (four workers' cost), TCP timestamps (the
  reused-port retransmission), lobo's one-server-block limit for any
  multi-site image, accept distribution across workers.

## For the maintainer: lobo on the Mac

The image is `build/mpx4-lobo/native/lobo-trunk.iso` from
`tests/mpx4-lobo --no-boot` (or the CI artifact's build). Host port
8380 (never 8080 or 8088 on this Mac):

```
qemu-system-x86_64 -machine q35 -m 256M -display none -serial mon:stdio \
    -no-reboot -cdrom lobo-trunk.iso \
    -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:8380-:80
```

At pelt's `$ ` prompt:

```
cd /srv
lobo -c conf/lobo.conf serve &
```

In a second terminal: `curl http://127.0.0.1:8380/` or `open
http://127.0.0.1:8380/`. Back at the prompt: `cat logs/access.log` shows
the browser's request; `lobo -s stop -c conf/lobo.conf`, `exit`; PAX
says `halt`, and Ctrl-A then X ends QEMU. No audio device is given.

## 5. Done-when

- Branch `px25` on origin; PR wolffe-lang/pax#40, open, unmerged, the
  five sections by name, commit shas as bullets, a test checklist.
- CI green at the head (the PR names the run).
- `wolf/tools/lane-audit.sh pax px25 40` run from the org directory,
  its exit status read directly (in the PR).
- Nothing merged, tagged, filed or closed. The plant branches
  `px25-plant-a`, `px25-plant-b`, `px25-plant-a2`, `px25-plant-b2` are on
  origin for the record.
