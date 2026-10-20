# px55 — The small fixes, two (pax#88, #89, #91, #93, #94)

Contract: px55's, `sprints/pax/55-the-small-fixes-two/px55-the-small-fixes-two.md`
in wolffe-lang/wolf (planning trunk `560c78f`, read 2026-10-20), under
`sprints/RULES.md`. Branch `px55` in pax, cut from pax trunk `d733bf4`
(px52), to be rebased onto px53's merge (pax#92, the pins at 0.2.33)
before the final head. §1 to §3 are committed before the first change
to the kernel, a tool, a probe, a test or CI, and before the first
measurement.

Five items: **#88** `/dev/fd`, Linux's link to `/proc/self/fd`, served;
**#89** `tests/mpx4-session`'s and `tools/lobo-session`'s port pickers
moved out of the ephemeral range (#86's race); **#91** `tests/mpx4-ready`
boots every way whatever an earlier one did, each its own verdict, and a
dispatch names its ways; **#93** `prlimit64`'s `RLIMIT_CORE` soft 0, as
Linux boots; **#94** `/proc/self/limits` and
`/proc/sys/kernel/core_pattern` served as Linux serves them.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor
  any libc's, shell's, container runtime's, init system's or QEMU's
  (ruling #22; RULES.md §1). Facts come from the man pages
  (`proc(5)`'s `/proc/pid/limits` and `/proc/sys/kernel/core_pattern`,
  `proc_pid_fd(5)`, `core(5)`, `getrlimit(2)`/`prlimit(2)`,
  `symlink(7)`, `path_resolution(7)`, `readlink(2)`, `lstat(2)`,
  `open(2)`, `getdents64(2)`, `ip(7)`'s `ip_local_port_range`,
  `bind(2)`), POSIX.1-2024, the allowed uapi headers
  (`asm-generic/resource.h`: the sixteen `RLIMIT_*` numbers and
  `RLIM_INFINITY`), QEMU's documentation of `-netdev user` (`hostfwd`),
  pax's own source, px50's to px53's notes, wolf-lang `v0.2.33`'s spec
  and pelt's and boreutils' notes as the maintainer's records, and
  black-box runs: kasumi's own kernel image under QEMU with a static
  program as pid 1 (real root, px48's `vmjob` way, `notes/px52/vmjob.c`
  and `notes/px50/vmjob.c` unchanged), a rootless container on kasumi for
  a user's rows, and CI's runner. `wolf/refs/repos/linux` stays sparse
  and is not opened.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals, id changes and core dumps only inside QEMU or
  a container, never on a host; nothing in this lane signals a host
  process but the lane's own jobs, by recorded pid.
- Probe and test binaries static, built in `px13-ubuntu`, never with
  kasumi's CachyOS glibc (AVX-512). No build on nomad-1. kasumi under
  `bash`, long jobs `setsid -f` with a pid file, ended by that pid only
  (never by name, pattern or process group); work under `~/lanes/px55/`,
  pruned; never `/tmp`. Process, signal and terminal tests under
  `taskset -c 0-3`; SigBlk and SigIgn read before a signal row is
  called red. Ports 8080 and 8088 unused; nothing installed on any host;
  `~/lanes/orch-paxplay/` and every other lane's directory untouched
  (px52's and px53's read only); px54's `user/` lope work not touched.
- Toolchains as pinned: until the rebase pax trunk's (wolf 0.2.32
  `72de141f`, lupin 0.1.54, pelt `2676879`, boreutils `43ee185`), after
  it px53's (wolf 0.2.33 `85dab5d7`, lupin 0.1.54, pelt `be1a75d`,
  boreutils `cc64f68`); none moved here.
- No `rm` outside `~/lanes/px55/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or
  the PR. No other lane's run cancelled; plants by dispatch on one leg
  (`-f tier=pr -f suites=…`, mpx5-jobs with `-f jobs_boots=…`);
  `full-matrix` only once the head is final, never at open. "Seen red"
  cites a run. No assertion deleted or weakened, no timeout or retry as
  a fix. Nothing says "secure"; no word implying filming. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-20)

| input | found |
|---|---|
| pax trunk | `d733bf4` (px52, PR #87 merged); its push run 39363381486 green (mpx4-ready 776 s of its 2400 s deadline for 12 boots), nightly 39415575722 green |
| px53 | PR #92 open, head `c8b48cb`, `full-matrix` on, its `tier pr` run 39453863096 green, its full run 39467484914 in progress; adds `user/sigwolf/`, `tools/mksigwolf`, mpx5-jobs' `sigs` image and J11, and `tools/linux-tree`'s `--ulimit core=0:0` |
| planning repo | `560c78f` (the contract; crawl 54's batch 10) |
| open pax issues | #55, #56, #62, #67, #88, #89, #90, #91, #93, #94 |
| #88 | `kernel/files`' `/dev` is synthetic: `stdin`, `stdout`, `stderr` are `T_STD` nodes 0, 1, 2, links to `/proc/self/fd/N` (px52: `is_link_node`, `link_bytes` 15, `link_target`, inodes 0x1a to 0x1c, DT_LNK); `child_named` knows no `fd`. px52 measured `/dev/fd -> /proc/self/fd` (0777, root's, 13 bytes) on kasumi's host and in podman (`notes/px52/kasumi-dev-links.txt`), and devtmpfs alone has none: `notes/px52/vmjob.c` makes all four in real root's guest. `user/elf/fdtab.c`'s N section has the three; `tests/mpx5-jobs.d/linux/fds.tty` 147 lines, `fds-user.tty` 142 |
| #89 | `tests/mpx4-session`'s `free_port`: `bind(("127.0.0.1", 0))`, the port printed, the socket closed, then QEMU's `hostfwd=tcp:127.0.0.1:$port-:7070`; `tools/lobo-session`'s `free_ports(n)`: n sockets bound to port 0, held until the last is read (px41, pax#53), then closed, then QEMU's forwards; `tests/lobo-session-selftest` W1 counts a port twice in 200,000 rounds of six (mpx4-lobo's first step in CI). px52's picker (`tests/mpx4-udp`, `mpx4-net`, `mpx4-tcp`, `mpx4-ready`'s `pick_ports`): ports from 20000 (21000) to 49151 outside the host's `ip_local_port_range`, each probed by a bind. A third picker of the kind, not the contract's: `tools/gateway-probe`'s `spare` (mpx4-net's G0) |
| #91 | `tests/mpx4-ready`'s `one`: after any failed boot no further boot starts (`--keep-going` boots them all; CI does not pass it), so px52's plant B (39302273238) was red at none and the rest "not booted"; `--ways` exists, CI passes only `$PAX_LEGS`; `workflow_dispatch` has `tier`, `suites`, `jobs_boots` |
| #93 | `kernel/user`'s `prlimit`: the stack's 131,072 (32 pages), the descriptors' 1024 (`files.FDS`), every other limit `RLIM_INFINITY` soft and hard, a set -EPERM. px53 measured real root's guest: `RLIMIT_CORE` soft 0, hard unlimited, `core_pattern` `core`, root and 1000:1000 (`notes/px53/linux-limits.txt`); PAX writes no core and never sets bit 7 of a wait status |
| #94 | `kernel/procfs`: a fixed table of 40 entries (the fixed ones below PIDDIR 31; `/proc/sys` has `vm`, `fs`, `net`, no `kernel`; `/proc/self` and `/proc/<pid>` have no `limits`); px53's PAX boot: both -ENOENT. Linux's `limits` (px53's guest): a header and sixteen rows, 78 bytes a row with units and 68 without (nice, real-time priority) |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, QEMU 11.1.1, `ip_local_port_range` 32768 60999, `/home` 41 GB free, `px13-ubuntu` `ad8964505189`, load 0.8 |

## 3. Prediction (committed before the first change and measurement)

**P1. #88 on Linux, and on PAX after the change.** fdtab's N section
gains six rows, the same as root and as 1000:1000 on real root's guest
(its `/dev/fd` made at its start by `notes/px52/vmjob.c`, as a
distribution's boot makes it) and in the container: `/dev/fd`'s
`readlink` `/proc/self/fd`, `lstat` and `statx` with
AT_SYMLINK_NOFOLLOW a link 0777 of **13 bytes**, nlink 1, 0:0, DT_LNK in
`/dev`'s listing; followed, a directory 0500, the reader's own and the
very node `/proc/self/fd` is (dev, inode, mode, owner), and `/dev/fd/`
too; opened O_NOFOLLOW -ELOOP (weak: with O_DIRECTORY as well); its
listing in a child with 0 1 2 open (`ls -l /dev/fd/`): `.` `..` `0` `1`
`2` `3` (the listing's own descriptor), each entry DT_LNK and its
`readlink` the one through `/proc/self/fd/N`; with descriptor 0 a file
at offset 3 (`cat /dev/fd/0`), `stat` of `/dev/fd/0` the file's, `open`
a new open file read from 0 (`abc`), descriptor 0 still at 3;
`/dev/fd/9` (not open) and `/dev/fd/00` -ENOENT; descriptor 0 closed:
`/dev/fd/0` -ENOENT. **On PAX after the change, byte-identical at the
first boot**: `kernel/files` gives `T_STD` a fourth node, `fd`, a link
whose target is `/proc/self/fd` (13 bytes, inode 0x1d), listed after
`stderr`; the walk and px50's `/proc/self/fd` do the rest. fds 153
lines, fds-user 148. No other session moves.

**P2. #89.** In a loop of 1,000 picks on kasumi (`px13-ubuntu`, its own
network namespace, `ip_local_port_range` 32768 60999): the old picker
(a TCP socket bound to port 0, its port read, closed) lands **inside the
range 1,000 times of 1,000** (`ip(7)`: port 0 takes an ephemeral port
from that range); the new one **0 times** and never at 49152 or above.
Both pickers take px52's: `tests/mpx4-session`'s `free_port` one TCP
port, `tools/lobo-session`'s `free_ports(n)` n different ones, each
probed by a bind and held until the last is chosen, from 20000 to 49151
outside the host's range. `tests/lobo-session-selftest` W1 says it:
200,000 rounds of six, **0 with a port twice and 0 inside the range**.
mpx4-session's and mpx4-lobo's sessions unchanged otherwise (CI's runs:
their Linux sides need an engine on the host).

**P3. #91.** `tests/mpx4-ready` boots every way of every leg whatever
an earlier boot did (until its deadline, which stays), and prints each
boot's verdict (`mpx4-ready: <tier> <leg> <way>: PASS` or `FAIL (T…)`)
before its own; `--fail-fast` keeps the old way for a quick local run.
`PAX_READY_WAYS`, which ci.yml passes from a new `workflow_dispatch`
input `ways`, names a subset: an unknown way is refused (exit 2), the
run says it is a subset. On kasumi (native BIOS, TCG, `taskset -c 0-3`)
none, peer and user PASS. **Plant B**, px52's plant B again (a
semaphore's read takes the whole counter), dispatched `-f tier=pr -f
suites=mpx4-ready`: **red at none (the first way) and at peer (the
second), each at T2's evprobe semaphore read (`the value 2`, Linux's 1)
and T9 (the boot stopped there), with user booted after them and
green**, each its own verdict line. And by `-f ways=peer`: only peer
booted, red the same, the run a subset.

**P4. #93.** `prlimit64(0, RLIMIT_CORE, NULL, old)` answers soft **0**,
hard RLIM_INFINITY; every other limit as before; a set still -EPERM.
One table answers `prlimit64` and `/proc/<pid>/limits` (`kernel/procfs`'s
`rlimit`), so the two cannot part. After the rebase, `user/sigwolf`
gains two rows read from `/proc/self/limits`: `L: the core limit, soft:
0` and `L: the core limit, hard: unlimited`, the same as root and as a
user on real root's guest (pid 1's limit, px53's measure) and **on PAX
at its first boot of the image**; in the container the soft row the
same and the hard row `0` (tools/linux-tree's `--ulimit core=0:0`, px53),
left out of the container's comparison by name. No other sigwolf row
moves; the `C:` rows (no core bit) stand.

**P5. #94.** Linux (real root's guest and the container): `/proc/self/limits`
a file 0444 of size 0, the reader's own, listed by `/proc/self`; 17
lines: the header `Limit` / `Soft Limit` / `Hard Limit` / `Units` in
columns 0, 26, 47 and 68, **78 bytes** with its trailing blanks; then
the sixteen limits in `asm-generic/resource.h`'s order, each name in 25
columns and a blank, each value (`unlimited` or the number) in 20 and a
blank, the units in 10 — **78 bytes, or 68 with no units** (`Max nice
priority`, `Max realtime priority`: no blanks after the hard value's) —
and every row's values `getrlimit`'s; `/proc/<pid>/limits` the same
bytes; `/proc/sys/kernel/core_pattern` a file 0644 of size 0, one line,
listed by `/proc/sys/kernel`, `core` on the guest (a pipe in kasumi's
and CI's containers: the host's). **On PAX after the change**: the same
layout, PAX's values (stack 131072 both, open files 1024 both, core 0
and unlimited, the rest unlimited), `core_pattern` `core`. The tree
probe (`user/elf/tree.c`) gains a `proc:` section held by mpx3-tree's
T1 to the container byte for byte (the header, each row's name, units,
length, columns and agreement with `getrlimit`, the modes, the
listings), and PAX's own text as `~proc:` lines (the seventeen lines and
`core_pattern`'s word), held by T2 to `tests/mpx3-tree.d/proc.pax` as
root and in `probes-user.pax` as a user. Weak: the column numbers for a
value longer than 20 bytes (none here).

**P6. Existing suites** green as root and as a user on kasumi (native
BIOS, TCG, `taskset -c 0-3`, after the rebase: mpx5-jobs every image,
mpx3-tree, mpx4-ready none peer user, mpx3-shell, mpx3-boreutils,
mpx5-users, mpx5-accounts, `tests/ci-plan`) and in CI's `tier full`.

**P7. Plants**, each a branch never merged, one commit, by dispatch on
one leg: **A** (#88) `/dev/fd` gone again: mpx5-jobs (`jobs_boots=fds:serial`)
J8 red at the six `/dev/fd` rows as root and as `pax`, J3 at the user's;
**B** (#91) as P3; **C** (#93) the core limit's soft unlimited again in
the one table: mpx3-tree T2 red at the `~proc:` core row (probes and
probes-user), T1 green (the file still agrees with `getrlimit`), and
mpx5-jobs (`jobs_boots=sigs:serial`) J11 red at sigwolf's soft row, root
and `pax`; **D** (#94) the units column one blank wider: mpx3-tree T1
red at the header and the fourteen rows with units, probes and
probes-user; **E** (#89) `free_ports` back to port 0: mpx4-lobo's first
step, `tests/lobo-session-selftest` W1, red with every port inside the
range.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | fdtab's six `/dev/fd` rows, the same as root and as a user on the guest and in the container: a link 0777 of 13 bytes, `/proc/self/fd`, DT_LNK; followed the reader's 0500 `/proc/self/fd` node; O_NOFOLLOW -ELOOP (weak: with O_DIRECTORY too); `ls -l /dev/fd/` `.` `..` `0` `1` `2` `3`; `cat /dev/fd/0` from offset 0; `/dev/fd/9`, `/dev/fd/00` and a closed 0 -ENOENT; PAX byte-identical at the first boot; fds 153 lines, fds-user 148 | every row as predicted on real root's guest, twice, the same bytes, root and 1000:1000 (`notes/px55/kasumi-fds-recordings-twice.out`), and the container's the same (J0) — **but O_NOFOLLOW\|O_DIRECTORY is -ENOTDIR**, not -ELOOP (the weak point: the directory test answers first, as PAX's `openat` already did for every link); **PAX byte-identical at its first boot** (fds 153 lines, fds-user 148; J8, J3, J4, `notes/px55/kasumi-first-mpx5-jobs-fds.out`) | right but the weak point |
| P2 | the old picker inside 32768–60999 1,000 times of 1,000, the new ones 0 and never at 49152 or above; W1 200,000 rounds of six, 0 twice, 0 inside | **1,000 of 1,000** inside for a socket bound to port 0, and for trunk's `free_port` as the suite defined it (1,000 of 1,000, 420 of them at 49152 and up); the new `free_port` **0 of 1,000** (ports 20005 to 32755), lobo-session's 0 of 1,000 single picks and **0 twice, 0 inside in 200,000 rounds of six** (`notes/px55/kasumi-picker-loop.txt`); W1 so on kasumi (`kasumi-lobo-session-selftest.out`) | right |
| P3 | every way boots whatever an earlier one did, each its own verdict; `PAX_READY_WAYS`; kasumi none, peer, user PASS; plant B red at none and peer, each at T2's evprobe semaphore read and T9, user booted after and green; `ways=peer` only peer, red, a subset | kasumi PASS on all three ways, three verdict lines (`kasumi-first-mpx4-ready.out`, and at the head §F); plant B **red at none and at peer (the second way), user booted after them and green**, each its own verdict line (run 39481386617); `ways=peer`: only peer booted, red, the run "a subset" (run 39481421050) — red at T2's semaphore read and T9 as predicted, **and at T3, T7, T8 (and T5, T6 for peer)** besides: a boot stopped at command 4 leaves the books, counters and the soak unwritten, which those assertions read | right; more assertions red than named |
| P4 | `prlimit64`'s core limit soft 0, hard unlimited, one table for it and the file; sigwolf's two `L:` rows the guest's at PAX's first boot; the container's hard row its engine's 0, left out by name; no other row moves | the guest: **`L: the core limit, soft: 0`, `hard: unlimited`**, root and 1000:1000, twice, the same bytes, and the 24 older rows the committed bytes (`notes/px55/kasumi-sigs-recordings-twice.out`); **PAX at its first boot of the image: J11 26 lines byte-identical, root and `pax`**, J3 the container's with the hard row left out (its `0`, named), J4 both rows (§F); `prlimit64` is `procfs.rlimit` | right |
| P5 | the limits file 0444, size 0, the reader's, listed; 17 lines, the header and rows in columns 0, 26, 47, 68, 78 bytes or 68 without units, every row `getrlimit`'s; `core_pattern` 0644, size 0, one line, listed, `core` on the guest, the host's pipe in the containers; PAX the same layout with its values; T1 to the container, T2 to `proc.pax` | so on real root's guest as root and as 1000:1000 (1,323 bytes: fifteen rows of 78, two of 68; `core`; `notes/px55/linux-proc-limits.txt`), the container's `proc:` rows the same bytes (its `core_pattern` kasumi's `\|/usr/lib/systemd/systemd-coredump …`, `kasumi-container-proc.txt`); **PAX at the first boot: T1 176 lines byte-identical to the container's, root and user, T2 its 19 `~proc:` lines `proc.pax`'s** (`kasumi-first-mpx3-tree.out`) | right |
| P6 | every suite green on kasumi and in CI's full tier | kasumi: every suite PASS at the head but one pjobs run once under load (green when booted again) and mpx5-users' sig, whose 30 reader rows now read `limits` 0, Linux's answer, so `sig.pax` (PAX's own text) moved (§F); CI's `tier full`: the pull request | right on kasumi but `sig.pax`, which I did not foresee |
| P7 | plants A, C, D, E red where named (B: P3) | A red at J8, J3, J4 root and `pax` (39481292677); E red at W1, every one of 200,000 rounds in the range (39481336353); D red at T1 (the byte count, the header and the rows) **and T2**, probes only — mpx3-tree stops at its first failure, so probes-user was never booted (39482100852); C red at mpx3-tree T2's core row with T1 green, and at J11's soft row root and `pax` with J3, J4 (39484458837), probes-user again unseen | A, C, E right; D right but T2 red too; the user's mpx3-tree run unseen in C and D (mpx3-tree's own fail-fast, to file) |

## A. /dev/fd (pax#88, item 1)

Linux (real root's guest: kasumi's 7.2.8 `f4c00d5d…` under QEMU 11.1.1,
`notes/px52/vmjob.c` as pid 1, which finds no `/dev/fd` in devtmpfs and
makes it with the three `/dev/std*`, as a distribution's boot and a
container runtime do; and a rootless podman container), as root and as
1000:1000, the same rows: `/dev/fd`'s `readlink` `/proc/self/fd`;
`lstat` and `statx` with AT_SYMLINK_NOFOLLOW a link 0777 of 13 bytes,
nlink 1, 0:0; DT_LNK in `/dev`'s listing; followed, `stat` a directory
0500, the reader's own and the very node `/proc/self/fd` is (device,
inode, mode, owner), `/dev/fd/` the same; O_NOFOLLOW -ELOOP and
O_NOFOLLOW|O_DIRECTORY **-ENOTDIR**; `ls -l /dev/fd/` in a child with 0
1 2 open: `.(d) ..(d) 0(l) 1(l) 2(l) 3(l)`, four entries (3 the
listing's own), each one's `readlink` `/proc/self/fd/N`'s, `lstat` of
`/dev/fd/0` a link 0700 of 64 bytes, the reader's; `cat /dev/fd/0` with
descriptor 0 a file at offset 3: `stat` the file's, `open` a new open
file read from 0 (`abc`), descriptor 0 still at 3; `/dev/fd/9` (not
open) and `/dev/fd/00` -ENOENT; descriptor 0 closed, `/dev/fd/0` -ENOENT
for `open` and `stat`. Recorded twice on the guest, the same bytes
(`tests/mpx5-jobs.d/linux/fds.tty` 153 lines, `fds-user.tty` 148), the
container's the same (J0).

PAX: `kernel/files`' `T_STD` has a fourth node, `FD_LINK`, `/dev/fd`: a
link whose target is `/proc/self/fd` (`link_bytes` 13; `link_target`
writes its first 13 bytes), inode 0x1d, listed after `stderr`
(`dev_child`), named `fd`; the walk rewrites `/dev/fd/N` to
`/proc/self/fd/N` and px50's magic link does the rest, so every row is
`/proc/self/fd`'s with its rules. `openat` already answered -ENOTDIR
before -ELOOP for a link under O_DIRECTORY. **Byte-identical at the
first boot**, root and `pax` (J8), the user's to the container's too
(J3); J4's witness asks the link row and the read through `/dev/fd/0`.

## B. The port pickers (pax#89, item 2)

`tests/mpx4-session`'s `free_port` and `tools/lobo-session`'s
`free_ports` take px52's picker: ports from 20000 to 49151 outside the
host's `ip_local_port_range`, each probed by a bind (TCP), lobo-session's
n of them held until the last is chosen (px41's rule: all different),
the range and the span read once a run. The loop (`notes/px55/picker-loop.sh`,
`px13-ubuntu` with `--network none`, kasumi's 7.2.8, range 32768 60999):
a socket bound to port 0 lands **inside the range 1,000 times of 1,000**
(411 to 429 of them at 49152 and up), and so does trunk's `free_port`
as the suite defined it (1,000 of 1,000); the new `free_port` 0 of 1,000
(ports 20005 to 32755); lobo-session's picker 0 of 1,000 single picks
and, in 200,000 rounds of six, 0 with a port twice and 0 with a port in
the range or at 49152 and up (`notes/px55/kasumi-picker-loop.txt`).
`tests/lobo-session-selftest` W1 now counts the range as well as the
repeats (`--free-ports` prints both); on kasumi W1 to W5 PASS in 8 s.
A third picker of the kind, not the contract's: `tools/gateway-probe`'s
`spare` (mpx4-net's G0), to file.

## C. mpx4-ready's shape (pax#91, item 3)

`tests/mpx4-ready` boots every way of every leg whatever an earlier
boot did (the deadline, 2400 s from the first boot, stays the only
bound; `--fail-fast` keeps the old rule for a quick run by hand,
`--keep-going` is the default), ends each boot with its own verdict,
`mpx4-ready: <tier> <leg> <way>: PASS` or `FAIL (<the assertions that
failed>)`, and prints them together before its own. `PAX_READY_WAYS`
names a subset (a way that is not none, peer or user is refused, exit
2; the run says it is a subset); ci.yml's `workflow_dispatch` takes
`ways` and passes it. Plant B (§H): none red, **peer, the second way,
red and seen**, user booted after them and green, each its own verdict;
and by `-f ways=peer`, peer alone. On kasumi the build at the head met
pax#90 once (its Linux side's pipe held 8,192 bytes: kasumi's shared
user past `fs.pipe-user-pages-soft`), and all three ways booted and
said so, each its own red (`notes/px55/kasumi-mpx4-ready-pipe-pages.txt`);
a second build's Linux side was right and every way PASS (§F).

## D. The core limit (pax#93, item 4)

`kernel/procfs`' `rlimit` is PAX's one table of resource limits, and
`kernel/user`'s `prlimit64` reads it: the stack's 131,072 both (the 32
pages PAX gives), the descriptors' 1024 both, **the core file's soft 0
and hard unlimited** (Linux's boot, measured by px53 and again here),
every other unlimited; a set is still -EPERM. PAX writes no core and
sets no wait status's core bit, and its limit now says so.
`user/sigwolf` reads the limit as `/proc/self/limits` says it (no prelude
call reads a limit) and prints `L: the core limit, soft: 0` and `L: the
core limit, hard: unlimited`: so on real root's guest as root and as
1000:1000, recorded twice, the same bytes, its 24 older rows the
committed bytes (`notes/px55/kasumi-sigs-recordings-twice.out`); in the
container the hard row is `0` (tools/linux-tree's `--ulimit core=0:0`,
px53), left out of the container's comparisons by name, the soft row
held there too (CI's J0 for sigs-user, plant C's run).

## E. /proc/self/limits and /proc/sys/kernel/core_pattern (pax#94, item 5)

Linux (real root's guest as root and 1000:1000; the container):
`/proc/self/limits` a file 0444 of size 0, the reader's, listed by
`/proc/self`, 17 lines and 1,323 bytes: the header `Limit` / `Soft
Limit` / `Hard Limit` / `Units`, 78 bytes with its trailing blanks;
then the sixteen limits in `asm-generic/resource.h`'s order, each name
in 25 columns and a blank, each value (`unlimited`, or the number) in 20
and a blank, the units in 10: 78 bytes, or **68 with no units** (`Max
nice priority`, `Max realtime priority`: nothing after the hard value's
blank); every row's values `getrlimit`'s; `/proc/<pid>/limits` the same
bytes. `/proc/sys/kernel/core_pattern` a file 0644 of size 0, one line,
listed by `/proc/sys/kernel`: `core` on the guest (Linux's boot
default), kasumi's container's `|/usr/lib/systemd/systemd-coredump %P %u
%g %s %t %c %h %d %F %I` (the host's). The guest's values: stack 8388608
and unlimited, core 0 and unlimited, processes and pending signals 3770,
open files 1024 and 4096, locked memory 8388608, message queues 819200,
the priorities 0 (`notes/px55/linux-proc-limits.txt`); the container's
are its engine's (`kasumi-container-proc.txt`).

PAX: `kernel/procfs` has `/proc/self/limits`, `/proc/<pid>/limits` (the
process files' owner rule; ENOENT once the process is gone), and
`/proc/sys/kernel` (0555) with `core_pattern` alone (`core`, root's
0644); `kernel/files` finds them by name (the fixed entries are
`procfs.fixed`'s now, PIDDIR's and the two new ones). The limits text
is `rlimit`'s in Linux's layout. The tree probe's `proc:` section
(`user/elf/tree.c`) holds what every Linux answers — the modes, sizes,
owner and listings, the header, each row's name, units, length and
columns, and the agreement with `getrlimit` — to the container (T1,
byte for byte), and prints the values as `~proc:` lines, held to PAX's
own text, `tests/mpx3-tree.d/proc.pax` as root and `probes-user.pax` as
a user (T2), written from the prediction before the first boot. **At
the first boot: T1 176 lines byte-identical, root and user; T2 the 19
`~proc:` lines exactly** (`notes/px55/kasumi-first-mpx3-tree.out`). The
guest's and the container's `proc:` rows are the same bytes too.

Named, not changed: `RLIMIT_NICE` and `RLIMIT_RTPRIO` answer unlimited
while `setpriority` and `sched_setscheduler` already act as Linux's boot
limit of 0 does (px45); to file.

## F. Existing suites on kasumi (P6)

Native, BIOS, TCG, every build in `px13-ubuntu`, at `f045f69` (mpx5-jobs,
mpx3-tree) or `fa12ab7` (mpx4-ready and the rest: `f045f69` and the sigs
recordings): the code and tests as at the head, after the rebase onto
px53's pins (the head adds `sig.pax` and words), each boot on four cpus of its own
(`taskset -c 0-3`, `4-7`, `8-11`, `12-15`; kasumi was shared, load 8 to
78):

- **mpx5-jobs, every image** (`notes/px55/kasumi-mpx5-jobs.out`): every
  J PASS but one run of 52: **pjobs-c_jc_wait_stopped** (J9, J4) once,
  its `^Z` echoed before `sleep 30` was the foreground job (no
  `Stopped` line; `wait %1` "no such job"; st=INT), at load 20 to 28;
  the pjobs image booted again alone, at load 8 to 10, every one of the
  52 runs PASS — a typing race under the host's load, not this change
  (nothing on the job-control path moved), named, to file. **sigs: J11
  byte-identical to real root's recording at PAX's first boot of it, 26
  lines as root and as a user** (both `L:` rows), J3 the container's
  but the hard row (named), J4, J6; fds as §A.
- **mpx3-tree** (`kasumi-mpx3-tree.out`): PASS, 63 PASS lines; probes
  and probes-user T1 176 lines, T2 the 19 `~proc:` lines.
- **mpx4-ready** (`kasumi-mpx4-ready.out`): none, peer, user PASS, each
  its own verdict, 1,076 s; the first build's Linux side met pax#90
  (§C).
- **mpx3-shell, mpx3-boreutils, mpx5-accounts**: PASS
  (`kasumi-regress.out`). **mpx5-users**: U1's sig session parted from
  `tests/mpx5-users.d/sig.pax` at its 30 reader rows only, each `limits
  -2` now `limits 0` — Linux's answer on every row
  (`tests/mpx5-users.d/linux/sig.txt`): a process's `limits` is anyone's
  to read, and PAX serves it now; `sig.pax` (PAX's own text) moved with
  it (`a4f05f4`), and the suite again: §F's last line in
  `kasumi-regress.out`.
- `tests/ci-plan`: 153 PASS (px53's count; no case added).
- `tests/lobo-session-selftest`: W1 to W5 PASS (§B).
- `mpx4-session`, `mpx4-lobo` and the other network suites: CI's runs
  (their Linux sides need an engine on the host), as at px53.

## G. CI

- The pull request's runs: named in the pull request and the hand-back
  (a commit naming them would move the head). The change touches
  `.github/workflows/ci.yml`, so the pull request's own run is every
  suite on the one leg (`tier pr`); under ruling #92 the lane hands back
  once it is green at the final head and `full-matrix` is on, and the
  orchestrator holds the `tier full` run.
- The plants' runs: §H.

## H. Plants (P7)

Each a branch never to be merged, one commit, run by dispatch on one leg
(ruling #92). A, B, D and E were cut from `c11c921` (the code and tests
of their gates as at the head, before the rebase onto px53's pins, which
moved none of them); C from `fa12ab7`, the rebased head with sigwolf's
rows and recordings.

| plant | branch, commit | break | CI |
|---|---|---|---|
| A (#88) | `px55-plant-a` `d5ce72a` | `/dev/fd` gone again: its lookup and its place in `/dev`'s listing | run **39481292677**, `-f suites=mpx5-jobs -f jobs_boots=fds:serial`, mpx5-jobs job 118830401188: J8 red for fds and fds-user at the four `/dev/fd` rows that need the link (147–150 and 142–145; the two -ENOENT rows the same either way), J3 at the user's, J4 at the link row and the read through `/dev/fd/0`, root and `pax` (`notes/px55/ci-39481292677-plant-a.txt`) |
| B (#91) | `px55-plant-b` `b4a00a8` | px52's plant B again: a semaphore's read takes the whole counter | run **39481386617**, `-f suites=mpx4-ready`, job 118830808602: **none FAIL (T2 T3 T7 T8 T9), peer — the second way — FAIL (T2 T3 T5 T6 T7 T8 T9), user booted after them and PASS**, each its own verdict line, at evprobe's `semaphore: read: 8 bytes, the value 2` (Linux's 1); run **39481421050**, `-f ways=peer`, job 118830890724: peer alone, the same red, "a subset" (`ci-39481386617-39481421050-plant-b.txt`) |
| C (#93) | `px55-plant-c` `e6a9cde` | `RLIMIT_CORE` soft unlimited again in procfs's one table | run **39484458837**, `-f suites='mpx3-tree mpx5-jobs' -f jobs_boots=sigs:serial`: mpx3-tree job 118841345457 T1 green (the file still agrees with `getrlimit`), **T2 red at the `~proc:` core row**, then stopped early (probes-user not booted: mpx3-tree's own fail-fast); mpx5-jobs job 118841346051 **J11 red at `L: the core limit, soft: unlimited`** (the guest's 0) as root and `pax`, J3 and J4 with it; the container's J0 green (`ci-39484458837-plant-c.txt`) |
| D (#94) | `px55-plant-d` `f5761c7` | the limits file's units column one blank wider (the header's too) | run **39482100852**, `-f suites=mpx3-tree`, job 118833247357: **T1 red** at the byte count, the header and the rows with units (79 bytes where Linux's are 78), **T2 red** at the `~proc:` lines, then stopped early (probes-user not booted) (`ci-39482100852-plant-d.txt`) |
| E (#89) | `px55-plant-e` `a9cf9d4` | `free_ports` binds port 0 again | run **39481336353**, `-f suites=mpx4-lobo`, job 118830645209: its first step, `tests/lobo-session-selftest`, **W1 red: 200,000 rounds of six, 0 with a port twice, 200,000 with a port in the ephemeral range** (`ci-39481336353-plant-e.txt`) |

## 4. Evidence index

Shas are this branch's after its last rebase (`px55` on pax trunk
`ff0709b`, tl29's merge, which changed CI's tiers, `CLAUDE.md` and notes
only); kasumi paths are under `~/lanes/px55/`. The first measurements
were made before the rebase onto px53's merge, on the branch then (its
commits `0874251` to `c11c921`, kept on origin by plants A, B, D and E);
the runs at the head (§F) at `f045f69` and `fa12ab7`, the same code and
tests rebased onto px53's merge `c8b48cb` before tl29's (kept on origin
by plant C), which are `cb85dfe` and `b1b9ce4` here.

### What was written

- The prediction: `4f2b180` (§1 to §3, before any change or
  measurement; first pushed as `0874251`).
- #88: `16fc718` (`kernel/files`), `6af901a` (fdtab's rows), `a9cfef6`
  (the fds recordings), `256c32b` (J8's witness).
- #94: `78e8da6` (`kernel/procfs`), `369c22e` (`kernel/files`' lookups),
  `bf55132` (the tree probe), `9274bd0` (`proc.pax`, `probes-user.pax`),
  `e4f4dc0` (`tests/mpx3-tree` T2), `a4f05f4` (`sig.pax`).
- #93: `c02c627` (`kernel/user`), `a4c1b0a` (sigwolf), `cb85dfe`
  (`tests/mpx5-jobs`' sigs rows), `b1b9ce4` (the sigs recordings).
- #89: `7edc5ff` (`tests/mpx4-session`), `bbd8e0c`, `541dc9e`
  (`tools/lobo-session`), `7755252` (the selftest).
- #91: `4acfd64` (`tests/mpx4-ready`), `39c2d06` (ci.yml's `ways`).
- The words: `04c085f` (`kernel/README.md`), `6bb2a06`
  (`docs/SOURCES.md`), `dfb1a5e` (README), `8dd0443` (CHANGELOG),
  `d9ecd1a` (`CLAUDE.md`'s plant line), and this note's evidence after it.
- The scripts: `notes/px55/*.sh` (launch, build, boot, regress,
  vm-rec, vm-tree, picker-loop).

### What was measured, and where it is

- **Linux's `/dev/fd`**: `tests/mpx5-jobs.d/linux/fds*.tty` and
  `vm-fds*.meta` (real root's guest, kasumi's 7.2.8 `f4c00d5d…`, vmjob
  `2a3a7f57…` from `notes/px52/vmjob.c`, the suite build's fds archive
  `9e2eb77b…`), made twice, the same bytes
  (`notes/px55/kasumi-fds-recordings-twice.out`); px52's
  `kasumi-dev-links.txt` for kasumi's host and podman.
- **Linux's core limit, limits file and core pattern**:
  `notes/px55/linux-proc-limits.txt` (the tree probe on real root's
  guest, root and 1000:1000, the suite build's probes archives
  `2d1d32b3…`, `39816a61…`); sigwolf on the guest:
  `tests/mpx5-jobs.d/linux/sigs*.tty` (vmjob `591414317f1b…`, px53's,
  the sigs archive `80d40414…`), made twice, the same bytes
  (`kasumi-sigs-recordings-twice.out`); the container's values
  `kasumi-container-proc.txt`.
- **The pickers**: `notes/px55/kasumi-picker-loop.txt` (trunk's and the
  branch's), `kasumi-lobo-session-selftest.out`.
- **PAX's first boots of each change**: `kasumi-first-mpx5-jobs-fds.out`,
  `kasumi-first-mpx3-tree.out`, `kasumi-first-mpx4-ready.out` (before the
  rebase); sigs at the head: `kasumi-mpx5-jobs.out`.
- **PAX at the head**: `kasumi-mpx5-jobs.out`, `kasumi-mpx3-tree.out`,
  `kasumi-mpx4-ready.out`, `kasumi-regress.out`; pax#90's run:
  `kasumi-mpx4-ready-pipe-pages.txt`.
- **The plants**: `notes/px55/ci-*-plant-*.txt`.

### Measured, inferred, not verified

**Measured**: everything in §A to §H but what follows.

**Inferred**:
- That pjobs-c_jc_wait_stopped's one red at the head was the host's
  load and not the kernel: the same image's 52 runs all PASS booted
  again at a third of the load, and nothing on the job-control path
  moved; the run was not repeated under the same load.
- That a program reading its core limit through `getrlimit` sees what
  sigwolf reads from the file: on PAX both are `procfs.rlimit` (one
  function), and the tree probe's rows hold the file to `getrlimit` on
  PAX and on Linux.

**Not verified**:
- Real root was one kernel build (kasumi's 7.2.8); the boot's limits
  other than the core file's (processes, open files, memory) differ by
  machine and are not PAX's to copy.
- `/proc/<pid>/limits` of another process (PAX's rows read their own;
  the container's `/proc` is not the probe's namespace there).
- A write to `/proc/sys/kernel/core_pattern` (not asked).
- UEFI, the release tier and more than one CPU: CI's full tier only; no
  hasu (KVM) run.

### Issues

- **To close at merge**: pax#88 (served, measured, root and user;
  plant A 39481292677), pax#89 (both pickers outside the range; the
  loop 1,000 of 1,000 inside before, 0 after; plant E 39481336353),
  pax#91 (every way boots, each its own verdict, `ways`; plant B
  39481386617, 39481421050), pax#93 (soft 0, hard unlimited; sigwolf's
  rows; plant C 39484458837), pax#94 (both files, Linux's layout,
  measured; plant D 39482100852).
- **Would file (none filed)**:
  1. pax: `tests/mpx3-tree` stops at its first failed session ("stopped
     early"), so a later session's red (plants C and D: probes-user)
     is never seen in CI; the shape #91 gave mpx4-ready (every session
     its own verdict, a dispatch input naming sessions).
  2. pax: `tools/gateway-probe`'s `spare` port (mpx4-net's G0) is bound
     to port 0 and closed before QEMU binds it: #86's race a third time.
  3. pax: `RLIMIT_NICE` and `RLIMIT_RTPRIO` answer unlimited while
     `setpriority` and `sched_setscheduler` act as Linux's boot limit of
     0 does (px45): PAX's limits and its behaviour disagree, as #93's
     core limit did.
  4. pax: mpx5-jobs' pjobs-c_jc_wait_stopped can type `^Z` before
     `sleep 30` is the foreground job under the host's load (kasumi,
     load 20 to 28, once in this lane).
- pax#90 (kasumi's shared pipe pages) met again once (§C); nothing new
  to file.

## 5. Done-when

- Branch `px55` on origin, rebased onto px53's merge (`c8b48cb`); the
  pax pull request (number in the hand-back), open, unmerged;
  `full-matrix` added at the final head once its `tier pr` run is green.
- The five sections §1 to §5; the items §A to §H.
- The test checklist:
  - [x] Linux measured first: fdtab's `/dev/fd` rows on real root's
        guest (twice, the same bytes) and in a container, root and user;
        the tree probe's `proc:` section on the guest and in a
        container; sigwolf's `L:` rows on the guest (twice) and in a
        container; the pickers' loop
  - [x] PAX byte-identical at the first boot of each change: fds (J8,
        J3), mpx3-tree's probes and probes-user (T1, T2), sigs (J11, J3)
  - [x] `tests/mpx5-jobs` on kasumi, every image (pjobs once red under
        load, then every run green)
  - [x] `tests/mpx3-tree`, `mpx4-ready` (none, peer, user),
        `mpx3-shell`, `mpx3-boreutils`, `mpx5-users`, `mpx5-accounts`
        on kasumi, native BIOS
  - [x] `tests/ci-plan`, every case; `tests/lobo-session-selftest`
  - [x] plants A to E red in CI (39481292677, 39481386617 and
        39481421050, 39484458837, 39482100852, 39481336353)
  - [ ] `tier pr` green at the final head, `full-matrix` on: named in
        the pull request; `tier full` held by the orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px55 <PR>` exit status: named in the
  hand-back.
- Trees: kasumi `~/lanes/px55/` keeps `out/`, `ev/`, `vm/`, `bin/`,
  `cache/`; build directories removed at the end. Plant branches stay
  on origin, never to be merged.
