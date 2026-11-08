# px108 — why den clones slowly on PAX

The console's den cloned `wolffe-lang/pelt` (12,670 objects, a 4.4 MB pack, 9,685 files in its checkout) in 85 s
over https and 86 s over ssh on the metal target, where git on another machine takes about 2 s. This lane measured
where those seconds go. Most of them are den's own work, not PAX's. Run on Linux, the same den clone takes 70 s of user
CPU against git's 0.4 s, and PAX's system time is a small share of the clone (§3, §4.3). The measurements also found
PAX rows far off Linux's. The largest of them, a pipe's 64 KiB round trip at 0.04 of Linux's rate, is fixed here:
`kernel/uaccess` moved every byte between a process and the kernel one at a time, and now moves a page's part at a
time with the string instructions the file tree already used. The other rows are listed in order of size in §5.

Footprint: cross-cutting (`.github/workflows/ci.yml` gains the `mpx5-rates` job; `tools/ci-tiers.map`, `tests/ci-plan`;
`kernel/uaccess`, which every system call that moves bytes uses).

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any OS; no Git source. The sources are in `docs/SOURCES.md`
  (px108): the Intel SDM's string instructions, the man pages of the calls the probes make, black-box Linux (natively
  on the lane's Linux host, and as a guest of one vCPU under the same QEMU and KVM: Ubuntu's generic kernel, its binary
  package only), and den's and wolf-std's trees (the org's own) to read what a clone does.
- **Hosts.** An x86-64 Linux workstation with KVM (Intel Core i7-12700KF, three blocks of six CPUs, two lock names to
  a block, light slots of two CPUs) for every row, the build Mac for git and compile checks. The metal target was never
  touched; its numbers came from the orchestrator.
- One scratch file went to the build Mac's `/tmp` by mistake (a check's output), and was removed at once.
- **Not done:** no label, merge, tag, release or deploy; no issue filed or closed; no attribution trailer.

## 2. Inputs, verified

| input | identity | read |
|---|---|---|
| pax base | trunk `db516c69` (px104's head) | `git log` |
| wolf (the kernel's) | 0.2.35, `kernel/wolf.pin`'s archive, `tools/fetch-wolf` by digest | every build |
| den at the metal target's stick | `474a926` (den trunk at vc23's merge), static `070cc093…`, 17,758,672 bytes, `tools/mkden` with this lane's pin file (`notes/px108/rig/den-trunk.pin`) | four builds, one digest |
| den at `user/den.pin` | `ac2332b`, static `cc00cd9a…`, 17,696,760 bytes (px104's digest) | four builds, one digest |
| burrow | `user/burrow.pin`'s `0d98ce9`, static `ae0e800f…` (the pin's digest) | `tools/mkburrow` |
| pelt (the cloned repository) | `https://github.com/wolffe-lang/pelt.git`, a bare mirror taken once: 83 refs (`refs.txt` sha256 `ed7fbbc4…`), 12,670 objects in one pack | `git count-objects -v` |
| the Linux guest's kernel | Ubuntu's `linux-image-6.8.0-147-generic`, vmlinuz sha256 `41ba36d8…` | binary package only |
| the lane's container | Ubuntu 24.04 with QEMU 8.2.2, OVMF, clang, lld 18, gcc 13.3, strace, dnsmasq, iproute2, openssl, git 2.43, OpenSSH | its package list |

The metal target's stick was built by `tools/mkdistribution --latest`: it carries den `474a926`, not `user/den.pin`'s
`ac2332b`. The rows below use `474a926` unless they say otherwise.

## 3. Prediction, scored

`notes/px108/prediction.txt`: committed first (`bed81808`), revised twice before any measurement on PAX: once after
the first Linux measurement (`e6ac5f45`), once after the orchestrator's correction that the stick's den is `474a926`
(`04bb6437`).

| | predicted | measured | |
|---|---|---|---|
| P1 | den's per-object work dominates, through PAX's system calls and memory | den's own user CPU dominates (70 s on Linux, 110 s on PAX's slower cores); PAX's system time is 13 s of 122 s | right on den, wrong on "through PAX" |
| P2 | the pinned den (`ac2332b`) clones pelt on no kernel | right: its pack stream refuses more than 10,000 objects (`den: wire: limit`, Linux, 1–3 s) | held, at the stream's bound, not closure's |
| S1 | file:// at `474a926`: den's own upload-pack refuses pelt on any kernel | right: Linux, `den: wire: limit` then `den: wire: invalid` after 54.5 s; PAX, the same after 124 s (filed by the orchestrator as den#73) | held |
| S2 | the 85 s is den's file work through PAX's calls, 100 µs to several ms a call | den's CPU, mostly user; PAX's per-call costs are real but small in the total (§4.3) | wrong in mechanism |
| S3 | under KVM PAX takes 40–90 s; the guest 2–6 s | PAX 122 s on the light slot's E-cores; the guest: the timed series (§4.4) | PAX reproduced; the guest's figure was wrong by far: den itself is slow on Linux |
| P4 (a) | anonymous memory and the walk before every unmap are the first suspect | `mmap` of 256 KiB 0.125 of Linux's rate, 0.05 with 512 MiB mapped; `brk` 0.38, 0.06 | real, and not what dominates a clone |
| P5 | a pipe's round trip within 3x the guest | 64 KiB: 0.04 of Linux's (fixed here, 0.55); 1 byte: 0.33 | wrong for 64 KiB |
| P5 | TCP into PAX 10–20 MB/s under QEMU's user network; 6 MB/s polled | 38.6 MB/s (QEMU's own TCP as the peer); across a Linux peer and a 30 ms round trip, 1.63 MB/s, polled: the 64 KiB window's own limit | the window, not the poll |
| P8 | SMP is not the next lever for pelt | held: one core's den is the cost; a second core would not help a single-threaded checkout | held |

## 4. Evidence index

### 4.1 Rulings (recommended and implemented, not decided)

- **R-px108-1, what dominates (A).** (A) den's own work: route it to den with the numbers (done: den#73 for the
  10,000-object bounds, vc24 for the index parsed again for every blob read); (B) a PAX fix for the clone's time.
  A: on Linux the same clone costs 70 s of user CPU and git 0.4 s.
- **R-px108-2, the copy (A).** (A) `kernel/uaccess` calls `boot/tree.S`'s `pax_tree_copy` and `pax_tree_zero` (REP
  MOVSQ/MOVSB, STOSQ/STOSB) a page's part at a time; (B) an assembly routine of uaccess's own; (C) leave it. A: the
  routines are on every kernel's roster and already carry the tree's reads and writes.
- **R-px108-3, B3's floor (A).** (A) a quarter of Linux's rate: trunk 0.04 is six times under it, the fix 0.55 more
  than twice over it, room both ways on a shared runner; (B) a half, the fix 1.1 times over it. A.
- **R-px108-4, mpx5-rates' Linux side (A).** (A) the same binary on the host, in a tmpfs, each row pinned to one CPU;
  (B) a Linux guest. A for the suite (CI has no guest kernel to boot); the lane's timed series runs the guest.
- **R-px108-5, TCP's window (A).** (A) a follow-on lane: RFC 7323's window scale and a receive buffer larger than
  64 KiB, red first on this lane's delay-line row (1.63 MB/s at a 30 ms round trip: a 300 MB repository's pack takes
  three minutes on the wire alone); (B) here. A: a cross-cutting change to `kernel/tcp` whose option counters
  `tests/mpx4-tcp` holds, beside a fix that stands alone.
- **R-px108-6, the tree's 16,384 inodes (A).** One pelt checkout is 10,136 inodes, so a second clone beside the first
  fails its checkout with -ENOSPC (`den: wire: Unsupported(clone checkout: io)`). (A) a follow-on lane: a two-level
  inode table, red first on a 20,000-file row against tmpfs; (B) here. A.
- **R-px108-7, anonymous memory (A).** (A) a follow-on lane: the peak counted as pages map and unmap (px88's R-px88-3
  B), the per-page checks of `brk` and `mmap` made per range; (B) here. A.
- **R-px108-8, the switch and the system-call path (A).** A 1-byte pipe round trip is 0.33 of Linux's rate and a bare
  system call 0.30. (A) the scheduler's lane: debug registers loaded only when a thread has them, the FPU state saved
  lazily, PCID; (B) here. A.
- **R-px108-9, the stick leg (A).** (A) `user/console/clone-time.keys` and `notes/px108/stick-leg.txt`, typed by a
  person at the console; (B) a suite booting the distribution's ISOs against fixtures. A: the leg is a timing, not
  a verdict.

### 4.2 The change

- `kernel/uaccess`: `copy_out`, `copy_in` and `zero` move each page's part with `pax_tree_copy` and `pax_tree_zero`
  (`221d66b0`). The checks are unchanged: every page walked and checked first, so all or nothing, SMAP never relaxed.
- `user/elf/bench.c` and `user/elf/ptime.c` (`tools/mkbench`), `tests/mpx5-rates`, its CI job, its place in
  `@user`, and `tests/ci-plan`'s rows for them.

### 4.3 The measurements

**Linux, natively** (the lane host, a container on two P-cores, the work directory on the host's disk; den `474a926`):

| row | wall | user | sys | result |
|---|---|---|---|---|
| den clone https (GitHub) | 286.7 s | 70.2 s | 44.9 s | complete |
| git clone https (GitHub) | 1.37 s | 0.40 s | 0.12 s | complete |
| den clone file://, git's upload-pack | 255.2 s | 67.2 s | 37.7 s | complete |
| den clone file://, den's upload-pack | 54.5 s | 35.3 s | 19.1 s | `wire: limit`, `wire: invalid` |
| git clone file:// | 0.54 s | 0.43 s | 0.11 s | complete |

`strace -f -c` of den's https clone: about 1.05 million calls, of them `brk` 195,504, `pread64` 257,259, `statx`
216,264, `openat` 119,164, `close` 103,366, `getdents64` 39,086, `fsync` 19,636, `read` 19,604, `rename` 9,774,
`unlink` 9,687. `strace -ttt`: the pack's file opened at 0.6 s; the checkout's 9,685 files written from 65 s to
292 s. At the old pin, `ac2332b`, den refuses pelt's pack outright (`den: wire: limit`, 3.35 s over https and 1.15 s
over file://), so it is no measure of the stick.

**PAX under KVM** (one CPU, kmain_console at `db516c69`, igb, a light slot's E-cores, so not comparable with the P-core
rows):

| take | way | wall | user | sys | result |
|---|---|---|---|---|---|
| QEMU's user network, igb by MSI-X | git:// | 122.2 s | 110.3 s | 13.0 s | complete |
| | ssh (burrow: 3.1 s, 0.2 s of CPU) | 99.2 s | 91.1 s | 9.2 s | checkout -ENOSPC: the tree's inodes, beside the first clone (R-px108-6) |
| | file://, den's upload-pack | 124.3 s | 58.4 s | 70.5 s | `wire: limit`, `wire: invalid` |
| the same, igb polled (`netpoll`, the metal I225's path) | https | 122.9 s | 108.6 s | 12.8 s | complete |
| a Linux TCP peer across a 15 ms delay line each way, polled | https | 133.8 s | 119.5 s | 12.0 s | complete |
| | git:// | 134.6 s | 121.6 s | 12.5 s | complete |
| | ssh (burrow 6.2 s) | 134.5 s | 121.1 s | 12.6 s | complete |

https, git:// and ssh agree to a few seconds on PAX as on the metal target: the transport is not the cost. A clone's
tree goes in 0.3 s (`rm -rf`).

**The microbenchmarks** (`tests/mpx5-rates`, PAX under KVM against the host's Linux on one CPU, the same cores):

| row | PAX at trunk | PAX at the fix | Linux | ratio at trunk | ratio at the fix |
|---|---|---|---|---|---|
| bare system call | 1,676,975/s | 1,708,974/s | 5,603,146/s | 0.30 | 0.31 |
| user-mode loop | 444,993/s | 443,993/s | 448,033/s | 0.99 | 0.99 |
| pipe round trip, 1 byte | 82,751/s | 83,391/s | 246,467/s | 0.34 | 0.33 |
| pipe round trip, 64 KiB | 1,569/s | 23,232/s | 44,111/s | 0.04 | 0.55 |
| a lookup that misses | 504,392/s | 505,792/s | 1,461,761/s | 0.35 | 0.35 |
| mmap 256 KiB, touch, munmap | 1,744/s | 1,744/s | 13,925/s | 0.13 | 0.13 |
| the same with 512 MiB mapped | 713/s | 713/s | 14,106/s | 0.05 | 0.05 |
| brk up 256 KiB, touch, down | 5,216/s | 5,248/s | 13,734/s | 0.38 | 0.38 |
| the same with 512 MiB mapped | 816/s | 832/s | 13,727/s | 0.06 | 0.06 |
| TCP into PAX, QEMU's user network | 38.6 MB/s | 40.2 MB/s | | | |
| TCP into PAX, a Linux peer, 30 ms round trip | 1.63 MB/s | | | | |

The files rows ran into the tree's 16,384 inodes at trunk (B2 red): they now stop at 6,000 objects a row.

### 4.4 The timed series

PAX at trunk, PAX at the fix and the Linux guest (one vCPU, virtio-net, a tmpfs root), interleaved, five rounds, on
one block's P-cores with its two lock names and its light lock: git://, https and ssh, each clone's tree removed after
it, then the microbenchmarks; and the TCP row across the delay line for each. Its record is the hand-back's; this
section takes its table when it is in.

### 4.5 The red row, the plant and the gauntlet

- `tests/mpx5-rates` B3 at the rows tip (`82b96af4`): `FAIL B3 native bios: a pipe's 64 KiB round trip, PAX 1569/s
  against Linux 44111/s: 0.04, under the floor 0.50`; at the fix (`221d66b0`): `PASS B3 … PAX 23232/s against Linux
  42395/s: 0.55`. The floor is a quarter since `d0a80c31` (R-px108-3).
- The plant, `px108-plant-uaccess` (one commit on the green head, one hunk: `copy_in` one byte at a time again),
  red by name at B3, and the gauntlet at the head: their records are the hand-back's.

## 5. What is left, in order of size

1. **den's own work** (den's): the checkout reads every blob with `object.read_object`, which parses the pack's index
   again each time (vc24's subject). 70 s of user CPU on Linux for pelt, against git's 0.4 s. And den's upload-pack's
   10,000-object closure bound (den#73).
2. **TCP's 64 KiB window** (R-px108-5): no window scaling, so a connection moves at most 64 KiB a round trip. 1.63 MB/s
   at 30 ms, and the I225 is polled once a tick on top. A 300 MB pack, den's own repository, spends about three minutes
   on the wire alone.
3. **Anonymous memory** (R-px108-7): mapping and unmapping cost 5 to 20 times Linux's, and more as the space grows (the
   whole-space walk before every unmap). It is the likely bulk of den's upload-pack's 70 s of system time on PAX
   (19 s on Linux for the same refusal).
4. **The tree's 16,384 inodes** (R-px108-6): a second pelt checkout beside the first fails.
5. **A context switch and a system call** (R-px108-8): about three times Linux's cost each.
6. **One CPU (SMP).** It is not the lever for pelt: den's clone is one thread's work. It becomes one when den or
   git-style tools resolve deltas on several threads.

## 6. Done-when

- [x] Item 1: the prediction committed first, revised twice before any PAX row, scored above.
- [x] Item 2: reproduced under KVM over git://, https (den's own TLS fixture) and ssh (burrow against OpenSSH), on
  QEMU's user network, polled, and across a Linux TCP peer with a 30 ms round trip. file://: den's own bound.
- [x] Item 3: the per-process split (wall, user, system, switches) on PAX by px88's accounting; the calls by name on
  Linux (`strace -c`); the microbenchmarks on both.
- [x] Item 4: what dominates is den's, routed; the PAX row far off Linux (the pipe at 64 KiB) fixed here, red first.
- [ ] Item 5: before and after as ratios to the guest: the timed series (§4.4). The stick leg:
  `user/console/clone-time.keys`, `notes/px108/stick-leg.txt`.
- [x] Item 6: §5.
