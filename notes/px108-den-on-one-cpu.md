# px108 — why den clones slowly on PAX

The console's den cloned `wolffe-lang/pelt` (12,670 objects, a 4.4 MB pack, 9,685 files in its checkout) in 85 s
over https and 86 s over ssh on the metal target, where git on another machine takes about 2 s. This lane measured
where those seconds go. Most of them are den's own work, not PAX's. Run on Linux, the same den clone takes 70 s of user
CPU against git's 0.4 s, and PAX's system time is a small share of the clone (§3, §4.3). The measurements also found
PAX rows far off Linux's. Under the same KVM on the same cores, PAX clones pelt in 0.68 of a one-vCPU Linux guest's
time (§4.4). The largest of the far-off rows, a pipe's 64 KiB round trip at 0.04 of Linux's rate, is fixed here:
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
| S3 | under KVM PAX takes 40–90 s; the guest 2–6 s | PAX 122 s on the light slot's E-cores; on one block's P-cores PAX 71 s and the guest 104 s (§4.4) | PAX reproduced; the guest's figure was wrong by far: den itself is slow on Linux, and slower in the guest than on PAX |
| P4 (a) | anonymous memory and the walk before every unmap are the first suspect | `mmap` of 256 KiB 0.125 of Linux's rate, 0.05 with 512 MiB mapped; `brk` 0.38, 0.06 | real, and not what dominates a clone |
| P5 | a pipe's round trip within 3x the guest | 64 KiB: 0.04 of Linux's (fixed here, 0.55); 1 byte: 0.33 | wrong for 64 KiB |
| P5 | TCP into PAX 10–20 MB/s under QEMU's user network; 6 MB/s polled | 38.6 MB/s (QEMU's own TCP as the peer); across a Linux peer and a 30 ms round trip, 1.63 MB/s, polled: the 64 KiB window's own limit | the window, not the poll |
| P8 | SMP is not the next lever for pelt | held: one core's den is the cost; a second core would not help a single-threaded checkout | held |

## 4. Evidence index

### 4.1 Rulings (recommended and implemented; R-px108-5 to 8 decided A)

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
| den clone https, a second take on the disk | 294.9 s | 71.8 s | 42.3 s | complete |
| den clone https into a tmpfs | 102.9 s | 66.3 s | 35.0 s | complete |
| den clone --bare https into a tmpfs (no checkout) | 3.10 s | 1.73 s | 0.14 s | complete |
| git clone https into a tmpfs | 2.16 s | 0.42 s | 0.07 s | complete |

**Why the disk row's wall is 2.5 times its CPU:** into a tmpfs the same clone's wall is its CPU (103 s against 101 s),
so the 190 s more on the disk are waits on the disk: den's 19,636 fsyncs (each checkout file, and its directory, is
synced before the next). Without a checkout (`--bare`) den's clone is 3.1 s: the transfer, the index and the closure
together cost about what git's whole clone does, and the checkout is about 100 s of the 103.

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

The series (`t4`; a take is named `t4-<what>-r<round>`) ran five rounds on 2026-11-08 between 07:28Z and 09:20Z,
on one block's six P-core threads, with its two lock names and its light lock held (nothing ran beside it). Each
round booted six takes in turn under the same KVM and QEMU 8.2.2:
- PAX at trunk (`db516c69`'s kmain_console), the Linux guest, and PAX at the fix (`221d66b0`). Each one cloned pelt with
  den `474a926` over https (den's TLS fixture), git:// and ssh (burrow against OpenSSH), removed each clone's tree, then
  ran the microbenchmarks.
- The same three, running the microbenchmarks only, with the TCP row taken across a 15 ms delay each way.
The guest is Ubuntu's 6.8 generic kernel on one vCPU with a tmpfs root. PAX's network is QEMU's igb (MSI-X), the
guest's is virtio-net. The table gives medians over the rounds that exited 0, with the range in parentheses. A ratio
is PAX's median over the guest's.

| way | PAX at trunk | PAX at the fix | the guest | trunk / guest | fix / guest |
|---|---|---|---|---|---|
| https | 71.0 s (70.7–72.8; user 63.0, sys 7.9; n=5) | 68.6 s (68.1–71.0; user 62.8, sys 5.5; n=5) | 104.4 s (101.9–108.8; user 69.2, sys 35.5; n=5) | 0.68 | 0.66 |
| git | 70.2 s (69.4–74.2; user 63.4, sys 7.9; n=5) | 67.6 s (67.1–71.8; user 63.2, sys 5.1; n=5) | 101.5 s (99.5–107.3; user 67.8, sys 33.2; n=5) | 0.69 | 0.67 |
| ssh | 70.7 s (69.2–73.6; user 63.1, sys 7.3; n=5) | 68.4 s (67.1–70.7; user 63.3, sys 5.4; n=5) | 101.0 s (96.5–108.8; user 67.5, sys 33.3; n=5) | 0.70 | 0.68 |

| row | PAX at trunk | PAX at the fix | the guest | trunk / guest | fix / guest |
|---|---|---|---|---|---|
| syscall | 3,225,951/s (n=5) | 3,098,953/s (n=5) | 11,184,826/s (n=4) | 0.29 | 0.28 |
| cpu | 787,988/s (n=5) | 787,988/s (n=5) | 792,760/s (n=4) | 0.99 | 0.99 |
| pingpong 1 | 158,142/s (n=5) | 155,454/s (n=5) | 538,462/s (n=4) | 0.29 | 0.29 |
| pingpong 65536 | 3,648/s (n=5) | 47,423/s (n=5) | 129,493/s (n=4) | 0.03 | 0.37 |
| files | 37,599/s (n=5) | 46,276/s (n=5) | 183,642/s (n=4) | 0.20 | 0.25 |
| files nosync | 54,690/s (n=5) | 60,159/s (n=5) | 253,778/s (n=4) | 0.22 | 0.24 |
| miss | 919,186/s (n=5) | 917,086/s (n=5) | 1,955,466/s (n=4) | 0.47 | 0.47 |
| mmap 256 KiB | 2,304/s (n=5) | 2,352/s (n=5) | 23,802/s (n=4) | 0.10 | 0.10 |
| mmap 256 KiB over 512 MiB | 1,248/s (n=5) | 1,264/s (n=5) | 24,321/s (n=4) | 0.05 | 0.05 |
| brk 256 KiB | 9,248/s (n=5) | 9,264/s (n=5) | 24,693/s (n=4) | 0.37 | 0.38 |
| brk 256 KiB over 512 MiB | 1,632/s (n=5) | 1,632/s (n=5) | 23,815/s (n=4) | 0.07 | 0.07 |
| malloc 256 KiB | 14,492,357/s (n=5) | 14,385,447/s (n=5) | 73,236,479/s (n=4) | 0.20 | 0.20 |
| malloc 256 KiB over 512 MiB | 14,486,645/s (n=5) | 14,438,422/s (n=5) | 73,135,685/s (n=4) | 0.20 | 0.20 |

| TCP into the machine | PAX at trunk | PAX at the fix | the guest | trunk / guest | fix / guest |
|---|---|---|---|---|---|
| QEMU's user network | 117.73 MB/s (111.85–122.01; n=5) | 129.05 MB/s (119.84–139.81; n=5) | 1667.84 MB/s (1550.49–1794.78; n=4) | 0.07 | 0.08 |
| a Linux peer, 30 ms round trip | 2.09 MB/s (2.09–2.09; n=5) | 2.09 MB/s (1.90–2.09; n=5) | 10.07 MB/s (7.33–10.99; n=5) | 0.21 | 0.21 |

- **The clone.** On the same cores PAX clones pelt in about 0.7 of the guest's time, and the ranges do not overlap.
  The user time is within a tenth of the guest's: it is den's own work, the same program on both. The difference is
  system time, 5 to 8 s on PAX against 33 to 36 s in the guest. Where the guest's system time goes was not split
  (there is no strace in the guest); on the host's Linux the same clone made about 1.05 million calls (§4.3). git in
  the same guest clones pelt in 0.50 s over git://, 0.75 s over ssh and 0.50 s over file:// (rounds 2 to 5), about
  two hundred times faster than den. So the metal target's 85 s against git's 2 s is den's, as §4.3 found. One CPU
  under this hypervisor does not make den's clone slower on PAX than on Linux.
- **The fix**: the 64 KiB pipe round trip goes from 0.03 to 0.37 of the guest's rate. Over https the clone is 2.4 s
  faster (68.6 s against 71.0 s), as much as its system time drops (5.5 s against 7.9 s).
- **The rows far off the guest** are the follow-on lanes' (§5.1): the bare system call and the 1-byte round trip about
  0.3, `mmap` 0.10 and 0.05, `brk` 0.37 and 0.07, a lookup that misses 0.47, files 0.20 to 0.25. `malloc` of
  256 KiB (0.20) is a loop that should not enter the kernel on either system. It is not split here and goes to the
  anonymous-memory lane (R-px108-7) as a question.
- **TCP.** QEMU's user network does not compare the two kernels, because the NIC models differ (igb's emulated
  registers against virtio). Across the 30 ms line PAX moves 2.09 MB/s in every round with interrupts: 65,535 bytes
  every 31 ms, which is the window's own ceiling. The I225's polled path read 1.63 MB/s (§4.3). The guest moves
  10.07 MB/s (7.33 to 10.99) on the same 16 MiB, slow start included. That is R-px108-5's lane.

**The rig changed during the series**: the guest take's script (the rig's `linux-take.py`, not in the repository;
PAX's takes were untouched). Round 1's
guest take hung on `git clone` over the https fixture (the fixture's `input timeout`). It ran out QEMU's 2,400 s
before its microbenchmarks. Between takes, with no guest take running, the script was replaced:

| takes | `linux-take.py` sha256 | its git rows |
|---|---|---|
| `t4-guest-r1` (07:33Z) | `686e71d9…add414c` | git over https, git://, ssh and file:// |
| none (live 08:15:13Z to 08:15:46Z) | `45a3f4f3…200337b9` | the same, git over https only when asked by name |
| `t4-guest-tap-r1` (08:17Z) onward: every other guest take | `f8022325…abaddc7` | the same, each git row under busybox's `timeout -s KILL 300` |

The two versions differ only in the git rows' block (one condition, one prefix, a comment). The old file was rebuilt
from the new one by reversing that diff, and it hashes to `686e71d9…`. Every guest take's run list, ports masked, has
the same three den clone lines and the same 14 microbenchmark lines (read from the series' log). So the
measured rows are the same code in both versions:
- **The guest's clone medians** mix the two versions, and that does not matter: the den rows are identical commands
  and run before the git rows in both.
- **The guest's microbenchmark medians** come from rounds 2 to 5 only (round 1 never reached them), so they use one
  version. The guest's TCP rows across the line all use one version.
- **The git rows** are not ratio rows, and none ran to completion in round 1.

### 4.5 The red row, the plant and the gauntlet

- `tests/mpx5-rates` B3 at the rows tip (`82b96af4`): `FAIL B3 native bios: a pipe's 64 KiB round trip, PAX 1569/s
  against Linux 44111/s: 0.04, under the floor 0.50`; at the fix (`221d66b0`): `PASS B3 … PAX 23232/s against Linux
  42395/s: 0.55`. The floor is a quarter since `d0a80c31` (R-px108-3).
- The plant, `px108-plant-uaccess` (one commit on the green head, one hunk: `copy_in` one byte at a time again),
  red by name at B3, and the gauntlet at the head: their records are the hand-back's.

## 5. What is left, in order of size

1. **den's own work** (den's): the checkout reads every blob with `object.read_object`, which parses the pack's index
   again each time (vc24's subject): about 100 s of the clone's 103 s on Linux in a tmpfs (66 s user, 35 s system),
   against git's 2.2 s; `--bare`, 3.1 s. On a disk, den's 19,636 fsyncs add about 190 s of waiting. And den's upload-pack's
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

### 5.1 The follow-on lanes, drafted

R-px108-5 to 8 were decided A: each is a lane of its own after this one, R-px108-5 first. Each draft gives the red row
it starts from, what this lane measured, and the files it touches.

**1. TCP's window (R-px108-5).**

- *Red row.* 64 MiB into PAX from a Linux peer across a delay of 15 ms each way: a tap in the container's own namespace
  and QEMU's dgram netdev, as this lane's takes (the relay becomes a tool under `tools/`). The I225 is polled, so the
  path matches the metal target's. The floor is 8 MB/s, almost four times what a 64 KiB window can move in 30 ms. At
  trunk the row reads 1.63 MB/s, so it starts red. A second row, the same transfer with no delay and the controller
  polled, guards the poll's own ceiling (below).
- *Measured.* Polled, 1.63 MB/s at a 30 ms round trip is 65,535 bytes every 40 ms. With interrupts (the timed series,
  §4.4) it is 2.09 MB/s in every round, 65,535 bytes every 31 ms: the window's ceiling at the line's 30 ms
  (2.18 MB/s), with the poll's tick on top on the polled path. The one-vCPU Linux guest moves 10.07 MB/s across the
  same line, so PAX moves 0.21 of what the guest does. With no delay, the same row reads 38.6 to 40.2 MB/s (QEMU's
  user network, interrupts). pelt's https clone takes 11 s longer across the line (133.8 s against 122.9 s). A 300 MB
  pack, den's own repository, would spend about three minutes on the wire.
- *Files.* `kernel/tcp/tcp.lu`:
  - the options walk reads kind 3 on a SYN and sends it back when the peer sent one (RFC 7323 §2.2), and
    `C_OPT_WSCALE` stops counting it as skipped;
  - `WND_MAX`, the advertised window and `K_MAX_WND`/`K_RCV_ADV` move to scaled units;
  - the receive buffer grows past `BUF` (65,536) and `BUF_PAGES` (16), so `F_BUFS`' 32 frames per connection
    become a size per connection, taken on demand, because `CONNS` is 1,024.

  `tests/mpx4-tcp`: T7's `skipped … window-scale` counter, and T6's byte-by-byte capture, whose SYN options change.
  `tools/paxtcp.py`: it announces 65,535 with no options, so it gains a window-scale option when a test asks for one.
  `docs/SOURCES.md`: RFC 7323. `kernel/gbe/gbe.lu`'s `RING` (64 descriptors) and the poll once a tick
  (`kernel/net` `poll`, `kernel/netd`'s clock) make a second ceiling once the window opens: 64 frames of 1,514 bytes
  a 10 ms tick is about 9.7 MB/s. That figure is computed, not measured, and is the lane's first row to take.

**2. The tree's 16,384 inodes (R-px108-6).**

- *Red row.* `tests/mpx5-rates`' files row at 20,000 objects (this lane caps it at 6,000) in PAX's memory tree,
  against Linux's tmpfs. At trunk it fails with -ENOSPC near the 16,384th inode, so it starts red. A guard row in
  `tests/mpx6-ext2` creates the same 20,000 files on an ext2 volume. Read from the source it should already pass, but
  no suite row has crossed 16,384 files on a volume yet.
- *Measured.* One pelt checkout is 10,136 inodes. A second clone beside it fails its checkout
  (`den: wire: Unsupported(clone checkout: io)`), and at trunk the bench's files rows ran out (B2 red).
- *Where the cap binds* (read from the source). `kernel/tree`'s table holds the memory tree's inodes plus the records
  of a volume's inodes in use. A volume's records are a cache: once 2,048 (`VOL_KEEP`) are live, `vrec` gives back up
  to 256 unheld ones, and if the table is full up to 2,048 more, and tries again. Only held records (an open file, a working
  directory, a mapping, a directory whose entries are loaded) and those looked up in the current call stay. The memory
  tree's own creators (`make`, `mkdir`, `symlink`, `anon`; a volume's go through `vmake` and `vrec`) evict
  nothing, so there the cap is a hard limit.
  - An installed system: the installer writes `/etc/fstab` as `PARTUUID=… / ext2 rw 0 1` and
    `tmpfs /tmp tmpfs nosuid,nodev 0 0` (`user/install/prepare.lu`'s `fstab_text`), and `/home/<user>` is a
    directory on that root. `paxext2` lays the root out with no `--inodes`, one inode per 16,384 bytes between
    512 MiB and 4 TiB (`user/disktools/paxext2/main.lu`). A 500 GB disk therefore gets about 30 million inodes.
  - Clones into `/home` are bounded by ext2's count, not by the table. Clones into `/tmp`, or into the console stick's
    memory root, meet the 16,384 cap at the second pelt.
- *Files.* `kernel/tree/tree.lu`:
  - `MAX_INODES`, and `IPF`/`iaddr`, today one frame of 512 pointers to frames of 32 inodes, which becomes a frame of
    such frames;
  - `inode_new`;
  - `SIDE_FRAMES` (32, `MAX_INODES / 512`) and the `VF_*` words after `VF_SIDE` (`VF_HASH`, `VF_CURSOR`, `VF_SEQ`
    move);
  - the scans bounded by `MAX_INODES` (`vrec`'s and `unhash`'s guards, `evict`'s walk).

  `kernel/files/files.lu`: `nr_inodes=` in the mounts table, and `statfs`' `f_files`/`f_ffree`. `tests/mpx6-root`:
  `nr_inodes=16384` in its first mounts line. `tests/mpx5-rates` and `user/elf/bench.c`: the files row's cap. Each
  inode is 128 bytes plus an 8-byte side word, so 65,536 inodes cost 8.5 MiB at most, taken a frame at a time as now.

**3. Anonymous memory (R-px108-7).**

- *Red row.* `tests/mpx5-rates`' `mmap` and `brk` rows with 512 MiB mapped, against Linux, with a floor of a quarter
  as B3 has. At trunk they read 0.05 and 0.06, so both start red. The same rows at 256 KiB (0.13, 0.38) are the second
  pair.
- *Measured.* 256 KiB mapped, touched and unmapped takes 573 µs on PAX against 72 µs (about 9 µs a page against 1.1).
  With 512 MiB already mapped it takes 1.4 ms against 71 µs. `brk` up 256 KiB, touched and down takes 191 µs against
  73 µs, and 1.2 ms with 512 MiB mapped. On Linux, den's https clone makes 195,504 `brk` calls. den's upload-pack
  spends 70.5 s of system time on PAX against 19.1 s on Linux for the same refusal. That is likely this cost, but it
  has not been split.
- *Files.* `kernel/vm/vm.lu`:
  - `note_peak`, called before every lowering (`brk`, `munmap`, a record's or a lazy range's pages, six call sites),
    walks the whole space through `kernel/paging`'s `user_pages`. Counting pages as they map and unmap removes the
    walk (px88's R-px88-3 B).
  - `map_zero` zeroes each frame with 512 volatile stores and maps it with one table walk a page. It becomes
    `pax_tree_zero`, as `kernel/uaccess` now uses, and one walk a range.
  - `unmap_range`, `pick`.

  `kernel/sched/sched.lu`'s `note_rss`. The peak's witnesses in `tests/mpx5-forks` (px88's maxrss rows) must read
  the same.
- *A question for it.* `malloc` of 256 KiB in a loop is 0.20 of the guest's rate (14.5 million a second against 73),
  though on Linux the loop does not enter the kernel once the allocator's threshold has risen. What PAX's run of the
  same static binary does differently was not split here.

**4. A context switch and a system call (R-px108-8).**

- *Red row.* `tests/mpx5-rates`' bare system call (`getppid`, 0.31 of Linux's rate), 1-byte pipe round trip (0.33)
  and missed lookup (0.35), against a floor of a half. All three start red.
- *Measured.* A system call takes 585 ns against 178 ns. A 1-byte round trip, which is two writes, two reads and two
  switches, takes 12.0 µs against 4.06 µs. A lookup that misses takes 1.98 µs against 0.68 µs. den's clone makes
  about 1.05 million calls (Linux's `strace -c`), so at about 0.4 µs more each that is under a second of a 122 s
  clone. These rows are a ratio to fix, not the clone's lever.
- *Files.*
  - `kernel/user/user.lu`'s `syscall` and `serve`: every call runs `trace.syscall_enter`/`syscall_return`,
    `sched.syscall_begins`/`syscall_ends` (two TSC reads, px88) and `tree.tick`, then a chain of compares to reach
    its number. That chain becomes a table.
  - `boot/user.S`'s `pax_syscall_entry` and `boot/isr.S`'s common path: every call goes through `pax_interrupt`.
  - `kernel/sched/sched.lu`'s `enter_space`, on every switch: a CR3 load with no PCID (the TLB emptied; PCID needs
    `kernel/paging` and CR4.PCIDE), a `WRMSR` of FS_BASE, and `boot/cpu.S`'s `pax_debug_load`, six moves to debug
    registers even for a thread with none set.
  - `run_next`'s `fpu.switch`, an eager save and restore (`kernel/fpu/fpu.lu`), and `account`.

  `tests/mpx5-trace` (its debug-register rows) must read the same.

## 6. Done-when

- [x] Item 1: the prediction committed first, revised twice before any PAX row, scored above.
- [x] Item 2: reproduced under KVM over git://, https (den's own TLS fixture) and ssh (burrow against OpenSSH), on
  QEMU's user network, polled, and across a Linux TCP peer with a 30 ms round trip. file://: den's own bound.
- [x] Item 3: the per-process split (wall, user, system, switches) on PAX by px88's accounting; the calls by name on
  Linux (`strace -c`); the microbenchmarks on both.
- [x] Item 4: what dominates is den's, routed; the PAX row far off Linux (the pipe at 64 KiB) fixed here, red first.
- [x] Item 5: before and after as ratios to the guest: the timed series (§4.4), five rounds. The stick leg's keys
  and sheet (`user/console/clone-time.keys`, `notes/px108/stick-leg.txt`) are committed; the timing waits for a
  person at the console.
- [x] Item 6: §5.
