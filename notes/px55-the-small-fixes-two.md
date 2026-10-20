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
