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
