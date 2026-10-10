# px17 — The pipes (PAX runs pelt's plumbing)

Contract: `sprints/pax/17-the-pipes/px17-the-pipes.md` in
wolffe-lang/wolf (planning trunk `b6e0be4`, read 2026-10-09). Branch
`px17` in pax, cut from pax trunk `ef4c3ca` (px16 merged). §1–§3 are
committed before the first change to the kernel, before pelt's 0.2.26
build is made and before the first strace of it.

One deliverable: pelt's H2 works on PAX — pipes, descriptors duplicated
into a child as pelt's spawn does it, `chdir`/`fchdir` and a real
per-process working directory with `getcwd`, offsets shared across
`dup`, redirection from initramfs files — so typed sessions with
`ls /bin | wc -l`, `cat /etc/motd > /dev/null` and `cd /etc; cat motd`
match Linux byte for byte; and the tour's closing line made honest.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22), and no shell's source (ruling #43): pelt is used as
  built from its own repository at its pin (`user/pelt.pin`,
  `tools/mkpelt`), its README read for what it claims. Allowed: the
  uapi headers and the syscall `.tbl` in the refs clone's sparse
  checkout (never widened), the ELF/psABI specs, the Intel/AMD manuals,
  man-pages sections 2, 4 and 7 (`pipe(2)`, `pipe(7)`, `dup(2)`,
  `chdir(2)`, `getcwd(3)`, `fcntl(2)`, `open(2)`, `path_resolution(7)`,
  `signal(7)`), POSIX.1-2024, and black-box runs of Linux (strace of a
  binary).
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611; pax has not adopted s223): the open-file table
  and the pipes are `.bss` words reserved in assembly and read volatile;
  a pipe's buffer is frames from `frames.alloc` reached through the
  HHDM. Nothing here allocates from wolf's heap.
- Test binaries for PAX (pelt, boreutils, procs) are built in the
  `px13-ubuntu` container (Ubuntu 24.04) on kasumi or on the CI runner,
  **never with kasumi's CachyOS glibc**.
- No `rm` outside `~/lanes/px17/` (kasumi, hasu, nomad-1) and this
  lane's private clones; no `git add -A`; nothing under `~/.claude`; no
  merge, no tag, no release; no `2>/dev/null` on a checkout; no
  attribution trailers; no "seen red" without a run id, sha, path or
  digest. No build on nomad-1 (it boots finished ISOs only).
- kasumi's `/home` is tight: one tree and one cache under
  `~/lanes/px17/`, `build/` directories pruned as the lane goes, `df`
  read before every image build.
- Strict evidence (wolf-lang#571): every suite with `PAX_REQUIRE_UEFI=1`
  and `WOLF_PAIRING_REQUIRE_SIBLING=1`, lupin fetched, full output kept,
  `SKIP` lines counted; concurrency rows (a pipeline's two children)
  also run under `taskset -c 0-3` on kasumi.
- No word implying filming anywhere in pax. Nothing in pax names any use
  of the two folders outside it. If the tour's or the shell's ISOs
  change, `~/scratch/wolf/pax-demo/` and `~/scratch/wolf/pax-shell/`
  are refreshed (images, SHA256SUMS, src/, every number their notes
  quote) and both preflights run to GO.
- A new user-visible spelling or changed meaning is a ruling owed, with
  options and a recommendation, and the recommendation implemented.

## 2. Inputs, verified (2026-10-09, from origin)

| input | found |
|---|---|
| wolf-lang trunk | `ac0ac498` (s220 merged; 0.2.26 + s220), as the contract says; nothing newer |
| wolf-interp trunk | `1c1f0968`, as the contract says; nothing newer |
| t05's triage | `sprints/triage/t05-report.md` at planning `b6e0be4`: nothing filed against pax's plumbing; pax-consumer rows are #551, #619, #611 (pax runs no region across a yield), #522 — none in this lane's path |
| pax trunk | `ef4c3ca` (px16 merged, PR #19), as the contract says; trunk CI green at `ef4c3ca` (run 37999687276); no open pax PR |
| pelt trunk | `3e7516c` (sh03 merged), as the contract says; its `wolf-toolchain.toml` pins wolf 0.2.26 (`05acdc5e…` linux x86-64, rev `89dc1394`), lupin 0.1.49, wolf-std `2f389a7`. README: pipelines, every redirection form, `cd`, `&`/`wait` and command substitutions that run programs (H2), matched against dash; "a pipeline stage pelt runs itself (a built-in, a function, a compound command) runs to the end before the next stage starts" |
| `user/pelt.pin` | `dd22a86` (sh02, wolf 0.2.24): the image's pelt refuses pipelines, redirections and `cd` by name |
| `user/boreutils.pin` | `50d8907` (bu18, wolf 0.2.25). boreutils trunk is `5da892e` (bu19: 0.2.26, `ls` on a terminal). **The contract moves pelt only**; boreutils stays `50d8907` (its `ls` prints one name a line whatever the output is, so `ls /bin` on the terminal and through a pipe agree, and the howl session is unchanged) |
| PAX today (kernel at `ef4c3ca`) | descriptors are per-process words (kind, node, position, flags) in the process area, copied whole at `clone`: a `dup` or an inherited descriptor keeps its own position (px14's named drift 6); no pipe, `pipe`/`pipe2` -ENOSYS; `getcwd` answers "/" always; `chdir`/`fchdir` -ENOSYS; relative paths start at `/`; `write` reaches the console and `/dev/null` only (a file of the initramfs is read-only, -EBADF); `fcntl` -ENOSYS; signals recorded, never delivered |
| the two folders | `~/scratch/wolf/pax-demo/` (`pax-tour.iso` `51772fe7…`, `pax-tour-b.iso` `850c4bc2…`, px16's) and `~/scratch/wolf/pax-shell/` (`pax-shell.iso` `99b34dec…`, px16's; pelt `dd22a86`) |
| the tour's closing line | `kernel/pax_tour/pax_tour.lu` `closing()`: "All in wolf. Next: Linux binaries, unmodified." (`tests/tour` R1 asserts it; the pax-demo SHOTLIST quotes it) |
| kasumi | `/home` 95% (49 GB free); QEMU 11.1.1 TCG, no `/dev/kvm`; `px13-ubuntu` image (from px13–px16) |
| hasu | KVM through `nix-shell -p qemu` (px14–px16) |

## 3. Prediction (committed before the first change and the first strace)

### P1. pelt's plumbing on Linux (strace -f of pelt `3e7516c`, static, a pseudo-terminal, chrooted in the shell's tree, PATH=/bin)

Typed: `ls /bin | wc -l`, `cat /etc/motd > /dev/null`, `cd /etc; cat
motd`, `pwd`.

- **The pipeline**: pelt's process makes **one `pipe2(…, O_CLOEXEC)`**
  and starts both stages the way px14 measured a spawn
  (`clone3(CLONE_VM|CLONE_VFORK|CLONE_CLEAR_SIGHAND)`, then `execve`),
  the first stage's child doing `dup2(write end, 1)`, the second's
  `dup2(read end, 0)`; the parent `close`s both ends after the second
  spawn (or the write end after the first) and `wait4`s each child.
  `wc -l` prints `10`. Falsified by a fork (a `clone` without CLONE_VM),
  by `fcntl(F_DUPFD…)` or `dup3` in place of `dup2`, or by a pipe made
  without O_CLOEXEC.
- **The redirection**: `openat(AT_FDCWD, "/dev/null",
  O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666)` in pelt's process, `dup2(fd,
  1)` in the child, `close(fd)` in the parent after the spawn; nothing
  printed.
- **`cd`**: `chdir("/etc")` in pelt's process, no `fchdir` and no
  `getcwd` for it (pelt keeps `PWD` itself, a named guess); `cat`
  opens `motd` relative to the working directory it inherited
  (`openat(AT_FDCWD, "motd", O_RDONLY…)`); `pwd` is a built-in and
  prints `/etc` with no system call of its own.
- pelt's process makes **2 ± 1 distinct calls** px14's 22 did not
  (`pipe2`, `chdir`, maybe one more at start-up): falsified outside 1..3.

### P2. What fails first on PAX (kernel at `ef4c3ca`, pelt `3e7516c` in the image)

- pelt `3e7516c` comes to its prompt and runs px15's six sessions as
  `dd22a86` did: every session that types no plumbing stays
  byte-identical to Linux with the new pelt and the old kernel (a named
  guess: pelt's start-up may make a new call, which would show as a new
  `-ENOSYS` line and fail S4, not S2).
- `ls /bin | wc -l`: `pipe2` -ENOSYS (293, logged once), and pelt
  prints a diagnostic of its own naming the pipe and returns to the
  prompt with a non-zero status: the session differs at that line.
- `cat /etc/motd > /dev/null`: **already byte-identical at `ef4c3ca`**
  (`/dev/null` opens for writing and swallows; a child's `dup2` onto 1
  works since px14). This witness is green at trunk, and says so; the
  redirection rows that go red at trunk are the ones that need shared
  offsets or a working directory (below).
- `cd /etc`: `chdir` -ENOSYS (80), pelt prints a diagnostic (`cd:`
  and the errno's text) and stays in `/`; `cat motd` then fails
  `cat: motd: No such file or directory` (boreutils' wording, a guess)
  where Linux prints the motd.
- **Shared offsets**: `{ head -n 1; cat; } < /etc/words` (a group
  redirected from an initramfs file, two children reading one open
  file): on Linux the second child starts where the first stopped; on
  PAX at `ef4c3ca` each child's copy keeps its own position, so `cat`
  starts at the file's first byte. Red at trunk.

### P3. The fix's shape

- **An open-file table** (Linux's open file description; `open(2)`'s
  NOTES): `openat`, `pipe2` and a `/dev/std*` open each make an entry
  (kind, node, position, status flags, a reference count); a descriptor
  names an entry plus its own close-on-exec bit; `dup`/`dup2`/`dup3`,
  `clone` (a child's copy of the table) and `fcntl(F_DUPFD…)` share it;
  `close`, `execve`'s close-on-exec and a process's end drop a
  reference. Offsets live in the entry, so they are shared.
- **Pipes** (`pipe(7)`): a pipe holds 65536 bytes (Linux's default
  capacity, `F_GETPIPE_SZ`), in 16 frames taken at `pipe2` and given
  back when both ends are gone; `read` blocks while it is empty and
  some writer is open, returns what is there (at most what was asked),
  and 0 once every writer is closed; `write` blocks while it is full and
  writes all it was given (a write of at most PIPE_BUF bytes is
  atomic); a write with no reader is `EPIPE`, and the writer dies of
  SIGPIPE (status 13) unless SIGPIPE is ignored or blocked (Linux's
  default action, the only signal PAX "delivers": it is synchronous).
  `fstat` on an end answers a FIFO (S_IFIFO|0600), `lseek` -ESPIPE,
  `ioctl` -ENOTTY. Blocking reuses px13's way: the call is rewound and
  re-run when the pipe changes (a new thread state, woken by the
  other end).
- **A working directory per process** (a node in the process area,
  copied at `clone`, kept across `execve`): `chdir` (-ENOENT,
  -ENOTDIR), `fchdir` (-EBADF, -ENOTDIR), `getcwd` the canonical path
  (-ERANGE when it does not fit), relative paths and AT_FDCWD resolved
  from it.
- **Calls added**: `pipe` (22), `pipe2` (293), `chdir` (80), `fchdir`
  (81), and `fcntl` (72: F_DUPFD, F_DUPFD_CLOEXEC, F_GETFD, F_SETFD,
  F_GETFL, F_SETFL O_NONBLOCK) only if the strace shows pelt or a
  boreutils program making it; `getcwd` (79) answers the real
  directory. 4 to 5 numbers.

### P4. What moves downstream

- Every kernel links kernel/files, so **every ISO changes**: the tour's
  two (the image size, the frame counts and ending b's `rip` move, as
  at px14–px16; the closing line moves by intent), and the shell image
  (new pelt, new kernel). The six existing sessions' transcripts do
  not move, but for whatever pelt `3e7516c` prints differently from
  `dd22a86` (a named guess: nothing in them).
- procs' transcript (`user/elf/procs.c`) changes only by the lines this
  lane adds (pipes, shared offsets, the working directory); every line
  px14 and px15 wrote is unchanged.
- At least **100 KVM boots** on hasu for the lane's suites, all green;
  boot to pelt's prompt on nomad-1 stays **2.0 s ± 0.4** (pelt grows a
  little; the initramfs gains `/etc/words`).
- Downstream repos (boreutils, lobo, wolf-std, pelt) are untouched: pax
  consumes pelt and boreutils at pins and changes neither.

### P5. Rulings owed

- **The tour's closing line** (a user-visible sentence): options (a)
  "All in wolf. Linux programs run on it unmodified: a shell, its
  pipes, its tools." (b) "All in wolf. Next: a disk, a network, and the
  installer." (c) drop the line. **Recommendation (a)**: it is what the
  kernel does after this lane, measured by mpx3-shell, and it keeps the
  sentence's place and length; implemented.
- SIGPIPE's death is Linux's documented default (`signal(7)`), not a
  new spelling: no ruling.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: one `pipe2(…, O_CLOEXEC)` for `ls /bin \| wc -l`; `wc -l` prints `10` | **right** (`notes/px17/pelt-plumb.strace` line 71: `pipe2([3, 4], O_CLOEXEC)`; the transcript's `10`) |
| P1: both stages started as px14 measured a spawn (`clone3(CLONE_VM\|CLONE_VFORK\|CLONE_CLEAR_SIGHAND)`); falsified by a fork or by `fcntl(F_DUPFD…)` | **wrong, both falsifiers hit**: wolf 0.2.26's spawn (s215's `os_spawn_fds`, which pelt `3e7516c` uses) **forks**: `clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID\|CLONE_CHILD_SETTID\|SIGCHLD)`; before it the parent makes `fcntl(0/4/2, F_DUPFD_CLOEXEC, 3)` (the child's 0-2 to be) and `socketpair(AF_UNIX, SOCK_SEQPACKET\|SOCK_CLOEXEC)`, closes its copy of the child's end and blocks in `recvfrom` until the child's `execve` closes that end (0 bytes: it ran); the child `close`s the parent's end, sets SIGPIPE to SIG_DFL, `fcntl(F_DUPFD_CLOEXEC, 3)` ×3, `dup2` onto 0, 1, 2, `close`s the copies, `execve`s (lines 71-218). The first stage's stdin is the terminal (px14's `dd22a86` gave a child /dev/null) |
| P1: the redirection `openat(AT_FDCWD, "/dev/null", O_WRONLY\|O_CREAT\|O_TRUNC\|O_CLOEXEC, 0666)`, `dup2` in the child, `close` after | **right** (line 248 onward; the `dup2` reaches 1 through the fcntl copy) |
| P1: `cd` is `chdir("/etc")` with no `getcwd`; `pwd` a built-in with no call | **half right**: `chdir("/etc")`, then **`getcwd`** (pelt sets PWD from it, line 329); `pwd` writes `/etc` with no other call. `cd ..` is `chdir("/")` (pelt makes the path itself); a failed `cd` is `chdir` -ENOENT / -ENOTDIR and `pelt: line N: cd: …: cannot change directory: cannot open` |
| P1: 2 ± 1 distinct calls pelt's process makes that px14's did not (1..3) | **wrong: 7** — `chdir`, `clone`, `fcntl`, `ioctl` (TCGETS on 0 and 2 at start: sh03 asks whether it is interactive), `pipe2`, `recvfrom`, `socketpair`; and 4 gone (`clone3`, `rt_sigprocmask`, `mmap`, `munmap`: no vfork stack). The children add `fcntl` and `dup2`; boreutils reopens `/dev/stdin`/`/dev/stdout` and moves fd 0's offset with `lseek` (the shared-offset witness, lines 472-553) |
| P2: pelt `3e7516c` on the old kernel runs px15's six sessions as `dd22a86` did (a new start-up call fails S4, not S2) | **wrong: every shell session red** (kasumi `red1`, kernel at `37a5402` = trunk's: `notes/px17/kasumi-red-37a5402-mpx3-shell.out`; CI run **38009076589**, job mpx3-shell 114084619386 the only red job): the first `fcntl` is -ENOSYS (72), so each command prints `pelt: line N: cat: cannot run: cannot open` and S1 (`fewer than two programs ran`), S2 and S4 (`-ENOSYS for '72 273 334'`) fail on shell-serial, -ps2, -howl, -howl-quiet; shell-ps2 ended 126 |
| P2: `ls /bin \| wc -l`: `pipe2` -ENOSYS and pelt's own diagnostic | **right in kind**: `pelt: line 1: cannot make a pipe` (the S2 diff) |
| P2: `cat /etc/motd > /dev/null` already byte-identical at trunk | **wrong**: at trunk every spawn fails at `fcntl` first, so this line printed `pelt: line 2: cat: cannot run: cannot open`. With the fork, the socket and `fcntl` in, it was right on the first boot (no redirection code was needed) |
| P2: `cd /etc` -ENOSYS (80) and `cat motd` fails | **right** (-ENOSYS for 80 in S4) |
| P2: `{ head -n 1; cat; } < words` prints the six words twice-overlapping at trunk | not reached at trunk (the spawn fails first); at the head it prints each word once, as Linux, which needs the shared offset (boreutils moves fd 0's offset with `lseek` and the next child starts there) |
| P3: an open-file table, pipes of 65536 bytes in 16 frames, blocking by px13's rewind, SIGPIPE's default, a working directory per process; 4-5 call numbers | **right in shape, wrong in count: 8 numbers** (`pipe` 22, `pipe2` 293, `socketpair` 53, `sendto` 44, `recvfrom` 45, `fcntl` 72, `chdir` 80, `fchdir` 81) and a **fork**, which no prediction named: `clone` without CLONE_VM on a copy of the address space (`paging.copy_user`), because wolf's spawn forks. The socketpair is two one-frame buffers on the pipes' code. SIGPIPE spares pid 1 (`kill(2)`, measured: procs as pid 1 gets -32) |
| P4: every ISO changes; the six old sessions' transcripts do not move; procs' moves only by its new lines | **right**: `notes/px17/kasumi-iso-eeb9565.sha256`; the six sessions' Linux and PAX transcripts unchanged (howl's `90c3e266…`, as px15/px16); procs' gains 22 lines, the 23 old ones unchanged |
| P4: ≥ 100 KVM boots on hasu, all green | **right: 272**, all accel=kvm, all rc 0, FAIL 0, SKIP 0 (`notes/px17/hasu-kvm-eeb9565.log`) |
| P4: boot to pelt's prompt on nomad-1 2.0 s ± 0.4 | **right: 1.7 s** in the rehearsal, 1.9 s in the preflight (the initramfs 390664 bytes larger: pelt 12753192 bytes, `etc/words`) |
| P4: downstream repos untouched | **right**: pax consumes pelt `3e7516c` and boreutils `50d8907` at their pins and changes neither |
| P5: the closing line, option (a), recommended and implemented | implemented (`fe6d867`); `tests/tour` R1 holds it (red first at `fb38197`, below) |

## 4. Evidence index

### The Linux side

- pelt `3e7516c` static, `692007c3…` (12753192 bytes), built by `tools/mkpelt` in `px13-ubuntu` on kasumi (wolf 0.2.26 `05acdc5e…` archive, wolf-std `2f389a7`); boreutils `50d8907`'s nine as px15/px16 (`notes/px17/linux-side-inputs.txt`).
- The plumbing, black-box: `notes/px17/pelt-plumb.strace` (`8a459809…`), its transcript `pelt-plumb.linux.tty`, the script `strace-plumb.sh`, the keys `plumb.keys` (= `user/console/shell-plumb.keys`).
- Every PAX transcript's reference: `tools/linux-tty --root --pid1` (as px14/px15), kept in `user/console/shell-plumb.expect` (S6) and `notes/px17/session-*.linux.txt`.

### Witnesses red at trunk, then green

| witness | red | green |
|---|---|---|
| mpx3-shell: the six old sessions with pelt `3e7516c`, and `shell-plumb` | kernel at `37a5402` (trunk's code, the new pelt and tests): kasumi `notes/px17/kasumi-red-37a5402-mpx3-shell.out` (native BIOS: S1/S2/S4 FAIL on every shell session; procs S2/S4 FAIL); CI run **38009076589**, job mpx3-shell **114084619386**, the only failing job | kasumi gauntlet at `eeb9565`: mpx3-shell 152 PASS, 0 FAIL, 0 SKIP (`notes/px17/kasumi-gauntlet-eeb9565.summary`, `kasumi-mpx3-shell-eeb9565.out`); again under `taskset -c 0-3` (152 PASS, `kasumi-taskset-0-3-mpx3-shell-eeb9565.out`); hasu KVM 5 rounds × 152; CI at the head (PR body) |
| procs' px17 lines (fork, pipes, SIGPIPE, offset, cwd, socket, fcntl) | the same runs: `wait4 fork: -10`, `pipe: -38 …`; S4 `-ENOSYS for '44 45 53 72 80 81 293'` and the fork refused by name | the same runs: `notes/px17/session-procs.{pax,linux}.txt` equal (`37483968…`, 45 lines) |
| tour R1: the closing line | `fb38197` (the test before the kernel's text): kasumi `notes/px17/kasumi-tour-fb38197.out`, R1 FAIL on all eight legs (`line 39 not found … All in wolf. Linux programs run on it unmodified: …`), 36 PASS, rc 1. (Its CI run 38009711711 was cancelled after 5 jobs to free the org's 20-job queue: its tour job had not started) | kasumi gauntlet at `eeb9565`: tour 44 PASS; the line on nomad-1 (`~/scratch/wolf/pax-demo/logs/preflight.serial.log`) |

The tiers: native and release, BIOS and UEFI, every leg (mpx3-shell boots both tiers on both firmwares). The checked machine and lupin do not concern these witnesses: the kernel is freestanding (`--target x86_64-unknown-none`), which only the compiling tiers build; lupin is fetched and paired (`WOLF_PAIRING_REQUIRE_SIBLING=1`, `notes/px17/kasumi-gauntlet-eeb9565.versions`) and runs no suite here.

### Session diffs (empty)

`notes/px17/session-shell-plumb.{pax,linux}.txt` (`7dd31190…`, 30 lines: `10`, nothing, the motd, `/etc`, alpha…foxtrot once, `1`, `motd`/`pax-run`, `77`, the two `cd` refusals, `2`, `/`) and `session-procs.{pax,linux}.txt` (`37483968…`), `cmp` equal; every leg's S2 in the gauntlet and on hasu.

### Boot counts

- kasumi TCG: the gauntlet at `eeb9565` (`kasumi-gauntlet-eeb9565.summary`: every suite rc 0, 0 FAIL, 0 SKIP; mpx3-shell 28 boots), the `taskset -c 0-3` run (28 boots), `red1` and `k1` (14 boots each, native BIOS).
- hasu KVM: **272 boots, all accel=kvm, all green** (`hasu-kvm-eeb9565.log`): mpx3-shell 5 rounds × 28 = 140, mpx3-console 20, mpx3-loader 4, mpx3-user 12, mkw 12, mpx1 12, mpx2-frames 16, mpx2-paging 4, mpx2-interrupts 20, mpx2-sched 8, mpx2-heap 24; images from the kasumi gauntlet tree at `eeb9565`, the tree a `git archive` of `eeb9565` (QEMU 11.1.0 through `nix-shell -p qemu`, i7-12700KF).

### Planted break

`1975de6` (an empty pipe with a writer open reads as end-of-file): predicted red on procs and procs-quiet S2 on all four legs each, shell-plumb wherever a reader outruns its writer, every other job green. The run id and its verdict are in the PR body; reverted after it.

### Downstream census

- Every kernel ELF and ISO pax builds moved (each links kernel/files, kernel/sched, kernel/paging): `notes/px17/kasumi-iso-eeb9565.sha256`. The tour image grew 408 → 436 KiB, its frame counts −14, ending b's `rip` `0xffffffff80027721`.
- boreutils, lobo, wolf-std and pelt: untouched (pax pins pelt `3e7516c` and boreutils `50d8907` and builds them unmodified).

### The two folders outside pax

- `~/scratch/wolf/pax-demo/`: `pax-tour.iso` `1af03fb4…`, `pax-tour-b.iso` `d596ca45…` (native, the gauntlet's `tests/tour` at `eeb9565`), `src/` at `eeb9565` (15144 lines of wolf, 1327 of boot assembly), README and SHOTLIST numbers, the closing line; `preflight.sh` **GO** in a 146×40 pseudo-terminal (the PANIC line in 29.3 s); ending b headless 28.6 s.
- `~/scratch/wolf/pax-shell/`: `pax-shell.iso` `1dfceb3a…` (the gauntlet's `native/console-shell-quiet.iso`), the Linux pane's tree on kasumi with pelt `3e7516c` and `etc/words` (`linux-root.sha256` `611fe4a8…`), README and SHOTLIST; `preflight.sh` **GO** (the prompt in 1.9 s); the whole take rehearsed (`rehearsal/rehearsal-2026-10-09-px17.times`): both panes' sessions `1934ecd0…`, 24 lines, the diff empty.

### Drift from the contract, reported

1. **pelt's spawn forks.** The contract's "descriptor duplication into a child as pelt's spawn path uses it" turned out to be a fork, a socketpair and `fcntl`, not px14's vfork: PAX gained `fork` (an address-space copy) and AF_UNIX socketpairs, neither named in the contract.
2. **boreutils stays `50d8907`** (the contract moves pelt only; boreutils trunk is `5da892e`).
3. **The shell image gains `/etc/words`**, six lines the plumb session's group reads; `ls /etc` would show it (no session lists `/etc` but plumb's `ls | head -n 2`, which shows `motd`, `pax-run`).
4. **pax had no CHANGELOG**: `CHANGELOG.md` is new, with the Unreleased paragraph the contract asks for.
5. **mpx3-shell's S1** now asks the exec pids to rise from 1, not to be 1..n: procs' fork child takes a pid and never execs.
6. **The Linux harness gives pelt SIGPIPE ignored** (inherited from `linux-tty`'s Python; the strace shows the child's `rt_sigaction` finding SIG_IGN), where PAX's pelt starts with SIG_DFL. No session reaches it (pelt as pid 1 is spared SIGPIPE on both, and its children set SIG_DFL themselves); procs sets SIGPIPE explicitly in each case.

## 5. Done-when

- Branch `px17` on origin; PR wolffe-lang/pax#20, open, unmerged; CI green at the head (run id in the PR body).
- pelt `3e7516c`'s pipelines, redirections and `cd` byte-identical to Linux on both tiers, BIOS and UEFI (`shell-plumb`), with the six earlier sessions and procs; KVM on hasu (272 boots).
- The tour's closing line honest; both folders refreshed, both preflights GO.
- Close nothing. To close: none in pax (no issue names this work).
- Worktrees: none (a private clone in this session's scratchpad); kasumi `~/lanes/px17/` and hasu `~/lanes/px17/` keep the trees and evidence, `build/` directories pruned at the end.
