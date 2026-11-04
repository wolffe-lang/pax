# px96 — the quiet console: `quiet` covers a program's errno lines

On a developer install the console showed `user: den pid 11 write fd 2: -EBADF` after every prompt. The
writes were pelt's probes on a closed stderr, fixed in pelt itself (sh36); the kernel's part is that
`write` logged every write to a closed or bad descriptor whatever the command line said, while `quiet`,
which the installed system boots with (`user/install/prepare.lu`'s `cmdline: quiet …`), covered only a
program's exec, its exit, its first -ENOSYS and the frames count (px15). A program's ordinary errno is its
own business: under `quiet` the two write lines now go, the program still gets its errno, and without
`quiet` every line is as it was. Refusals by name, faults that kill a process and panics still print.

Contract: px96's (crawl 54, 2026-11-04), under the lane rules of 2026-10-31 and their additions.

Footprint: module (`kernel/user`, `user/programs.S`, `tests/mpx3-user` and its `.d`, `kernel/kmain_user.lu`,
`kernel/README.md`, `docs/BOOT.md`, `docs/SOURCES.md`, notes; nothing under `boot/`, `.github/` or a pin).

## 1. Forbidden, and what was read

- **Clean room.** No kernel's, firmware's, bootloader's or driver's source was read. QEMU, OVMF and Limine
  ran as black boxes. `docs/SOURCES.md` has px96's row: nothing new was consulted (the numbers are px09's,
  the `cmdline` key px15's).
- **Read in PAX's tree:** `kernel/user/user.lu` (the write path, `writev` through it, and every line it
  prints), `kernel/process/process.lu` and `kernel/signal/signal.lu` (every `user: <name> pid <n>` line,
  through `process.who`), `kernel/log` (the `quiet` word), `kernel/files/files.lu` (read only: which
  descriptors `write_target` calls closed; it prints no line of its own), the network, block, ext2 and
  sound modules' lines (device lines, not a program's), `user/install/prepare.lu`'s `config_text`, the
  quiet Limine configurations, `user/programs.S`, `kernel/kmain_user.lu`, and every test that asserts a
  kernel line (`grep` of `tests/` for `write fd`, `-EBADF`, `-EFAULT`, `-ENOSYS`, `refused:`, `killed:` and
  `quiet`).
- **Not touched:** `kernel/files/` (px98's) and the pins (px97's). kasumi was never touched. On satoyama
  every run held both locks, A outside and then B, on slot A's CPUs `0-3,8-11` (taskset inside the
  container), one job at a time. Nothing in `/tmp` or `/var/folders`. No label, merge, tag, issue or
  release; no attribution trailers.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `44b44435` (px92's note, the head at the launch) | `git log` at the clone |
| wolf | 0.2.35, `kernel/wolf.pin`'s archive `4cc4045b…` (`tools/fetch-wolf` by digest, in the container) | the pin's digest and version line, by `tools/fetch-wolf` |
| Limine | 12.9.1, `boot/limine.pin`'s `5cdebc51…` (`tools/fetch-limine` by digest) | by `tools/fetch-limine` |
| the container | `localhost/px75-ubuntu:2` (Ubuntu 24.04, clang, lld 18, QEMU 8.2.2, OVMF, xorriso), `--memory 12g`, KVM | the gauntlet's `tools` step prints each tool's path and QEMU's version |
| a type check on nomad | wolf 0.2.36 (the Mac's), `wolf build --emit=wir --target x86_64-unknown-none` of kmain_user and kmain_console at `45856d0e`, behind the Mac build lock: exit 0, 0 errors | a smoke check only; the pinned 0.2.35 builds on satoyama are the evidence |

## 3. Prediction, scored

The prediction is `notes/px96/prediction.txt`, committed first (`d4b1ae8a`).

| predicted | measured | verdict |
|---|---|---|
| the census: the two write lines printed whatever `quiet` says; -ENOSYS already gated; refusals printed by px15's design; `killed:` and panics not errno lines | as predicted (§4.1), the exec refusal (`kernel/process`) among the refusals; `writev` reaches the -EBADF line through `write` | held |
| at the rows' commit, before the gate: U0-U8 and U10 PASS, U9 FAILs naming the -EFAULT and -EBADF lines | the red run at `ae7e2454` (§4.3; its rows in the PR's body) | see the PR |
| after the gate, U9 PASSes and nothing else moves | the gauntlet at the head (the PR's body: every `END` line) | see the PR |
| the plant (`errno_lines()` answers true): U9 red by name, U4 and U10 still PASS | the plant's record (the PR's body) | see the PR |
| one more boot per tier and firmware in mpx3-user | four images a tier and firmware instead of three; the times are in the records | held |

## 4. Evidence index

### 4.1 The census: every per-program line for a call that failed

Every line the kernel prints for a program goes through `process.who` (`user: <name> pid <n>`), from
`kernel/user`, `kernel/process` and `kernel/signal`; `kernel/files` prints none. Line numbers are trunk
`44b44435`'s.

| line | where | when | with `quiet`, before px96 | a test that depends on it | px96 |
|---|---|---|---|---|---|
| `… write fd <F>: -EBADF` | `kernel/user/user.lu:707-713`, `write` (and `writev`, which writes each part through it) | a write to a closed descriptor, or one opened only to read | printed | none asserts it; on a quiet image a leaked one would break mpx3-shell's S2 (the quiet sessions held to Linux's transcript) | **gated**: U4 without `quiet`, U9 with it |
| `… write fd <F> buf 0x<b> len <L>: -EFAULT` | `user.lu:741-751`, `write` | a console write whose buffer is not all readable user memory | printed | mpx3-user U4 (three, booted without `quiet`) | **gated**: U4, U9 |
| `… syscall <n>: -ENOSYS` | `user.lu:1090-1107`, `unknown` | once a process and number (every time past 511) | not printed (px15) | mpx3-user U2, mpx3-shell S1 and S4, and every suite's -ENOSYS census | unchanged |
| `… syscall <n>: refused: <why>, -<errno>` | `user.lu:1112-1133`, `refusal_line` (the reasons kernel/vm, files, socket, ready, cred and process leave) | a call PAX refuses for what it lacks | printed (px15's design) | mpx4-udp (six by name), mpx5-users, mpx5-forks, mpx3-shell S4 on both images; and "no refusal" rows on quiet boots: mpx3-shell S2, mpx4-session E1, mpx4-lobo L2 | unchanged (R-px96-1) |
| `… syscall 16: refused: tty ioctl 0x<r>, -ENOTTY` | `user.lu:2055-2061`, `ioctl` | a terminal request the console refuses | printed | mpx3-console (ask's one tty ioctl) | unchanged (R-px96-1) |
| `user: exec <path>: refused: <why>` | `kernel/process/process.lu:733-739`, `refuse_line` | an exec PAX refuses (not ELF64, a PIE, PT_INTERP, no frames) | printed | mpx3-loader L4 | unchanged (R-px96-1) |
| `… killed: <exception> vector …` and `… killed: <SIG…> after <r> runs` | `user.lu:2489`, `kill`; `kernel/signal/signal.lu:603`, `die` | a fault or a signal ends the process | printed | mpx3-user U3, mpx3-shell S1 (the quiet image too), and most session suites | unchanged: not an errno; px96's U10 holds it on the quiet image |

Not per program, and unchanged: the device lines that carry an errno (`block: refused: a mount of … -EBUSY`,
`… BLKRRPART while … -EBUSY`, `block: refused: a write to … -EIO`, `ext2: …`, `nvme…`), each said once a
device, and every panic.

### 4.2 The change

- `user/programs.S` (`34b6cec9`): badptr, after its three bad buffers, closes fd 2 (0) and writes to it
  (-9, EBADF); when all five answers are Linux's it writes `badptr: -EFAULT three times, -EBADF on a closed
  fd 2` on fd 1 and exits 14, as before; otherwise it exits 1 to 4 with no line. Every instruction form it
  adds is one the file already had, so `tests/kernel-as`'s clef row (the same bytes as GNU as) has nothing
  new to assemble.
- `tests/mpx3-user.d/limine-quiet.conf` (`3b328aeb`): `boot/limine.conf` with `cmdline: quiet`.
- `tests/mpx3-user` (`ae7e2454`): U4 takes the `write fd 2: -EBADF` line and badptr's own line; a fourth
  image, kmain_user with the quiet configuration, gives U9 (badptr's line there once, no `write fd` line at
  all) and U10 (one `user: quiet` line, the five faults' `killed:` lines as U3 has them, no -ENOSYS or exit
  line, halted). The rows were committed before the gate.
- `kernel/user/user.lu` (`45856d0e`): the two lines behind `errno_lines()`, which is false when the console
  is quiet, as the exec and exit lines are; the errno is returned either way. The `user: quiet` line now
  reads `no exec, exit, -ENOSYS, write -EBADF or -EFAULT, or frames line for a program` (tests read only its
  prefix).
- `kernel/README.md` (`57ab25bd`), `docs/BOOT.md` (`6bfebc27`), `kernel/kmain_user.lu` (`fcbcfa5d`) and
  `docs/SOURCES.md` (`0d3408ae`): the quiet table, the live entry's paragraph, the test kernel's header, and
  the sources row.

### 4.3 Red first

The rows went in at `ae7e2454`, before the gate (`45856d0e`). At that commit, on satoyama, `tests/mpx3-user
--tier native --firmware bios` must show U9 red by name, `FAIL U9 native kmain_user-quiet bios: …` with the
three -EFAULT lines and the -EBADF line on the quiet image counted, and every other row green: U4 (the lines
without `quiet`, badptr's own line, exit 14) and U10 (what `quiet` keeps). The run's rows are in the PR's body.

### 4.4 The gauntlet and the plant

The gauntlet runs at this branch's head, after this note's last commit, in a clean checkout on satoyama
through the org's record writer: `tools` (the container's tools), `ci-plan` (`tests/ci-plan`, the planner's
own proof, the new `tests/mpx3-user.d/` path derived as mpx3-user's), `mpx3-user` (both tiers, both
firmware: U0-U10), and `kmain_console` built at both tiers (the kernel the installed system runs). It stops
at its first nonzero step. Its `END` lines are in the PR's body.

The plant is one hunk off the head, on `px96-plant-gate`, pushed without a PR: `errno_lines()` answers
`true`, so both lines come back on a quiet console. Its record runs mpx3-user on native BIOS and must hold a
`FAIL U9` line; U4 and U10 stay green. Its `END` line and the `FAIL U9` line are in the PR's body.

Not run locally: the other 38 of the 39 suites `tools/ci-plan` selects for `kernel/user/*` and
`user/programs.S` (the PR tier's, on native BIOS); they run in the PR's `tier pr` and in trunk's `tier all`
(R-px96-4).

### 4.5 Rulings (each recommended and implemented, none decided)

- **R-px96-1, the refusal lines under `quiet`.** (A) Keep them: a refusal names what PAX lacks, which is PAX's
  business rather than the program's; px15 kept them on purpose, and four quiet rows (mpx3-shell S2 and S4,
  mpx4-session E1, mpx4-lobo L2) mean something only while they print. (B) Gate them too, and move those rows
  to narrating boots. **A**, implemented: a refusal on the installed console in ordinary use is a gap to close
  in PAX, not a line to hide.
- **R-px96-2, two comments under `boot/` and one in CI.** `boot/limine-initramfs-quiet.conf` (line 7) and
  `boot/limine-usb.conf` (line 5) still say "a refusal, a fault and a bad buffer still print", and
  `.github/workflows/ci.yml`'s mpx3-user comment lists U0-U8. A change under `boot/` or `.github/` makes a PR
  `cross-cutting`. (A) Leave them to the next cross-cutting lane that touches those files, with the text
  "a refusal and a fault still print" and "… U9 and U10, a program's errno on a quiet console"; (B) make this
  PR cross-cutting for three comment lines. **A.**
- **R-px96-3, where the row lives.** (A) mpx3-user: kmain_user booted quiet, badptr writing to a closed fd and
  to bad buffers, the kernel alone, about one more boot a leg; (B) mpx3-shell's procs-quiet, an ELF session
  with a Linux transcript, which needs pelt and a privileged Linux side. **A**, implemented; the quiet
  sessions of mpx3-shell and mpx4-session already fail on any leaked line.
- **R-px96-4, the local gauntlet's scope.** (A) The rows' suite on every leg, the planner's proof and the
  installed kernel's build, with the PR's `tier pr` and trunk's `tier all` for the rest; (B) more suites
  locally, hours of satoyama's one slot. **A.**

## 5. Done-when

- [x] 1. The census (§4.1), each line with the tests that depend on it.
- [x] 2. The rows, red first (§4.3): under `quiet` badptr's closed-fd and bad-buffer writes print nothing and
  it gets its errnos (U9); without `quiet` the lines appear as before (U4).
- [x] 3. The gate (`45856d0e`): exactly the exec and exit lines' gate; -ENOSYS, refusals, faults and panics as
  they were.
- 4. One plant, local, `px96-plant-gate`, red by name: its record's `END` line and `FAIL U9` lines are in the
  PR's body (§4.4).
- 5. This note; the PR with its Footprint line; the gauntlet at the head (its `END` lines in the PR's body);
  the audit once (the hand-back).

README read, current: its USB paragraph says the live entry prints "no line for a program's ordinary life",
which px96 makes truer and does not move. Issues for the coordinator to file (none filed by this lane): none.
Nothing to close.
