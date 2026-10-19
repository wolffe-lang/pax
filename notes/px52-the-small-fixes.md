# px52 — The small fixes after the pins (pax#85, #82, #83, #86)

Contract: px52's, `sprints/pax/52-the-small-fixes/px52-the-small-fixes.md`
in wolffe-lang/wolf (planning trunk `b860faa`, read 2026-10-19), under
s243's "Forbidden / rules" word for word but the toolchains (pax's own
pins, none moved here), and the rules of `sprints/crawl-54.md` and
`sprints/wave-53.md` down to `wave-45.md`. Branch `px52` in pax, cut
from pax trunk `d6fbcdc` (px51). §1 to §3 are committed before the
first change to the kernel, a tool, a probe, a test or CI, and before
the first measurement.

Four items: **#85** a later image's red visible in CI; **#82**
`eventfd` with `EFD_SEMAPHORE` served as Linux serves it; **#83**
`/dev/stdin`, `/dev/stdout`, `/dev/stderr` as symbolic links to
`/proc/self/fd/0`, `1`, `2`; **#86** the one silent native-UEFI boot of
mpx4-udp's user image, its rate and its cause.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor
  any libc's, shell's, terminal driver's, container runtime's, init
  system's or device manager's (systemd, udev, crun, runc, Docker,
  podman), nor QEMU's (ruling #22). Facts come from the man pages
  (`eventfd(2)`, `read(2)`, `poll(2)`, `epoll(7)`, `proc_pid_fdinfo(5)`,
  `proc_pid_fd(5)`, `symlink(7)`, `path_resolution(7)`, `readlink(2)`,
  `lstat(2)`, `open(2)`, `getdents64(2)`, `ip(7)`'s
  `ip_local_port_range`, `udp(7)`), POSIX.1-2024, the allowed uapi
  headers (`linux/eventfd.h`'s EFD_SEMAPHORE is 1), QEMU's documentation
  of `-netdev user` (`hostfwd`), pax's own source, px24's to px51's
  notes, and black-box runs: kasumi's own kernel image under QEMU with a
  static program as pid 1 (real root, px48's `vmjob` way), a rootless
  container on kasumi for a user's rows, kasumi's own host for what a
  distribution's boot leaves in `/dev` (read only: `ls -l`, `readlink`,
  `stat`), and CI's runner. `wolf/refs/repos/linux` stays sparse and is
  not opened.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals and id changes only inside QEMU or a container,
  never on a host; nothing in this lane signals a host process but the
  lane's own jobs, by recorded pid.
- Probe and test binaries static, built in `px13-ubuntu`, never with
  kasumi's CachyOS glibc. No build on nomad-1. kasumi and hasu under
  `bash` (hasu `env bash`), long jobs `setsid` with a pid file, ended by
  that pid only (never by name, pattern or process group); work under
  `~/lanes/px52/`, pruned; never `/tmp`. Process, signal and terminal
  tests also under `taskset -c 0-3`; SigBlk and SigIgn read before a
  signal row is called red. Ports 8080 and 8088 unused; nothing
  installed on any host; `~/lanes/orch-paxplay/` and every other lane's
  directory untouched (px51's read only).
- Toolchains as pinned: wolf 0.2.32 (`72de141f`, `4c37f9c5…`), lupin
  0.1.54 (`175df238…`), pelt `2676879`, boreutils `43ee185`; none moved.
- No `rm` outside `~/lanes/px52/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or
  the PR. No other lane's run cancelled; plants by dispatch for their
  suites; `full-matrix` only once the head is final, never at open.
  "Seen red" cites a run. No assertion deleted or weakened, no timeout
  or retry as a fix. Nothing says "secure"; no word implying filming.
  If the harness refuses an action I stop and report.

## 2. Inputs, verified (2026-10-19)

| input | found |
|---|---|
| pax trunk | `d6fbcdc` (px51, PR #84 merged); its push run 39190726104 and nightly 39257426343 green; no pax PR open |
| planning repo | `b860faa` (the contract; crawl 54's batch 9) |
| pins | `kernel/wolf.pin` wolf 0.2.32 `72de141f…` / lupin 0.1.54; `user/pelt.pin` `2676879`; `user/boreutils.pin` `43ee185`: the contract's |
| open issues | pax#55, #56, #62, #67, #82, #83, #85, #86 |
| #85 | `tests/mpx5-jobs` boots `probe:serial probe:ps2 shell:serial shell-user:serial gaps:serial fds:serial pjobs:serial pjobs-user:serial groups:serial` on each leg, all from one process; `tools/qemu-halt`'s fail-fast (px26) keys its note on that process, so after one typed boot's first prompt never comes, every later typed boot of the run (every later image, every later leg) is refused at once. `PAX_JOBS_BOOTS` (px51) narrows the list, but ci.yml's `workflow_dispatch` has only `tier` and `suites`. px51's plants 39178241978 (A, `0e22d80`, TIOCSPGRP a no-op) and 39178243818 (B) were red only at J1, the rest "not booted". In the full run 39183573858 mpx5-jobs took 65 min of its 120 (build 2, the containers 11, a leg about 13); plant A's run 27 min |
| #82 | `kernel/ready`'s `eventfd2` refuses EFD_SEMAPHORE by name (-EINVAL, refusal 103); `kernel/event`'s counter takes whole (`ev_take`); `kernel/procfs`' fdinfo prints `eventfd-semaphore: 0` always; `user/net/evprobe.c` asks it once as a `~` line, which `tests/mpx4-ready` holds to PAX's -EINVAL (T2) and counts among T4's three refusals; `user/elf/fdtab.c` asks a non-blocking eventfd instead (px50) |
| #83 | `kernel/files`' `/dev` is synthetic: `stdin`, `stdout`, `stderr` are `T_STD` nodes that `open` resolves to descriptor 0, 1, 2 itself (px17; px50 made `stat` follow too, `std_target`); `readlink` -EINVAL, `lstat` the console's character device; the listing's type is not a link's. `/proc/self/fd/N` is px50's magic link (`fd_follow`). px50's guest (`notes/px50/vmjob.c`) mounts devtmpfs on `/dev` and makes no link there |
| #86 | push run 39086412018, mpx4-udp native UEFI `user`: U1–U9 red, the serial log 0 bytes. Its artifact 12120719249 (read): `.qemu.log` is QEMU's one line `-netdev user,id=n0,ipv6=off,hostfwd=udp:127.0.0.1:37606-:7: Could not set up host forwarding rule 'udp:127.0.0.1:37606-:7'`, `.meta` `elapsed: 0.103s`, `status: 1`; `.end` `udp-host: 127.0.0.1 port 9099 bound; the guest's port 7 is 127.0.0.1 port 37606`. The boot never started: QEMU refused its own arguments. `tests/mpx4-udp`'s `pick_ports` probes two ports from `20000 + (pid * 7919 + n * 16) % 20000` by binding and closing them; QEMU binds the forward later; `tools/udp-host`, started in between, binds a socket to port 0 (`ask.bind(("127.0.0.1", 0))`) after its `bound` line, just as the suite starts QEMU. The same picker is in `tests/mpx4-net`, `mpx4-tcp` and `mpx4-ready` |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, QEMU 11.1.1, OVMF `/usr/share/edk2/x64/OVMF_CODE.4m.fd`, `ip_local_port_range` 32768 60999, `/home` 24 GB free, `px13-ubuntu` `ad8964505189`, load 1.6; port 9099 free |

## 3. Prediction (committed before the first change and measurement)

**P1. #85: a dispatch chooses the images.** The choice: `PAX_JOBS_BOOTS`
as a `workflow_dispatch` input (`jobs_boots`), not every image booted
regardless. Argued: px26's fail-fast exists so a kernel whose programs
cannot start is red within one deadline, not one a boot; mpx5-jobs is
already the longest job of a full run (65 of 120 min), and booting every
image regardless would pay the 900 s prompt deadline at each image whose
first prompt never comes, on each leg: under plant A the probe at
least, and any shell that waits on the terminal, so a plant's run (and a
real break's) would reach the job's cap before the later legs, at 120
job-minutes from the org's twenty concurrent jobs. A dispatch that names
its images keeps that bound and costs only what it names; an ordinary
run stays red at its first broken image, as the merge rule needs.
mpx5-jobs refuses a boot it does not know by name (exit 2), says which
boots it runs, and runs the container sessions of the chosen images only
(a plant's run spends no 11 minutes on images it does not boot). Plant A
again (`0e22d80`'s change on this branch) by dispatch with
`jobs_boots="pjobs:serial pjobs-user:serial groups:serial"`: **red in CI
on all four legs at J9, 21 of 26 pelt sessions as root and 21 of 26 as
`pax`** (kasumi's count in px51), groups green; no probe booted. Weak:
CI's four vcpus may move one session either way.

**P2. #82 on Linux** (evprobe extended, a container on kasumi's 7.2.8,
then CI's own Linux side): `eventfd(2, EFD_SEMAPHORE|EFD_NONBLOCK)` a
descriptor, F_GETFL `O_RDWR|O_NONBLOCK` (no other bit shown); a read
takes **1** and leaves the rest (8 bytes, the value 1; then 1; then
-EAGAIN at zero); a write of 3 adds 3 (three reads of 1 each); poll
POLLIN while above zero, POLLOUT always; a blocking read at zero ended
by a child's write of 2 takes 1 and leaves 1; two children blocked at
zero, one write of 2: each takes 1; the semaphore in an epoll object
level-triggered stays ready until the last unit is taken; the same flags
a non-semaphore eventfd refuses (-EINVAL for an unknown bit, a write of
`0xffffffffffffffff`). fdinfo (fdtab, real root's guest): `flags: 02`
and **`eventfd-semaphore: 1`** (weak: the flags line). **On PAX after
the change, identical**: `kernel/event` keeps a semaphore mark per
counter (`ev_new`'s new argument), `ev_take` takes 1 for a semaphore,
`kernel/ready` takes the flag (refusal 103 retired), `kernel/procfs`
prints the mark. mpx4-ready: evprobe's semaphore line leaves the `~`
lines (T2's set four lines, not five), T4's refusals by name two (an
epoll object in another, EPOLLEXCLUSIVE), the `user: ready:` refused
count one less.

**P3. #83 on Linux.** On kasumi's host (systemd's boot) and in a
rootless podman container (and CI's Docker): `/dev/stdin`, `/dev/stdout`,
`/dev/stderr` are symbolic links, 0777, root's, size 15, nlink 1,
`readlink` `/proc/self/fd/0` (`1`, `2`), and `/dev/fd` a link to
`/proc/self/fd` beside them; **devtmpfs alone makes none** (the guest:
-ENOENT; weak), so the guest gets the four links made at its start as a
distribution's boot makes them (named, `notes/px52/vmjob.c`), and the
rows hold the kernel's answers through them. Through a link: `stat` is
descriptor N's (fstat's); `open` makes a new open file at offset 0 with
the flags asked, descriptor N's own offset unmoved; `O_TRUNC` through
`/dev/stderr` truncates the file descriptor 2 names (pelt's `>
/dev/stderr` with `2>> f`); descriptor N closed: `open` and `stat`
-ENOENT, `lstat` and `readlink` still the link; O_NOFOLLOW -ELOOP; a
trailing `/` on a file -ENOTDIR; a socket's -ENXIO, a pipe's end the
end; the listing's type DT_LNK; `readlink` with room for 5 bytes 5
`/proc`. The same as root and as 1000:1000. **On PAX after the change,
identical**, as a new `N:` section of `fdtab` (mpx5-jobs J8, fds and
fds-user, held to real root's guest and the container); `kernel/files`
makes `stdin`, `stdout`, `stderr` links whose walk rewrites the path to
`/proc/self/fd/N` (a link against the 40, then px50's magic link); the
reopen and `std_target` special cases go. `/dev/fd` is not added (the
contract names three; listed to file). No existing session moves:
bu25's `cat` reaches the same node through `/proc/self/fd/0`
(mpx3-tree's shell-inout unchanged).

**P4. #86.** The cause is the harness, not the kernel and not UEFI:
QEMU refused the forward because port 37606 was taken between
`pick_ports`'s probe and QEMU's bind, and 37606 lies inside the host's
ephemeral range (32768–60999), where any socket bound to port 0 lands —
`udp-host`'s own `ask` socket among them, bound in exactly that window.
Loops on kasumi (TCG, the native user image under OVMF, the suite's
own picker and `udp-host` order, each boot to its first serial line,
`taskset -c 0-3`): **0 silent boots in 100 plain and 0 in 100 under
load** (four busy loops on cpus 0-3); under **churn** (a process binding
UDP sockets to port 0 on 127.0.0.1 as fast as it can) a measurable rate
of boots QEMU refuses, each with the same line in `.qemu.log` and an
empty serial log, none a kernel silent after QEMU started; with the fix
(ports chosen outside the host's `ip_local_port_range`) under the same
churn, **0 in 100**. The fix goes into all four pickers (mpx4-udp,
mpx4-net, mpx4-tcp, mpx4-ready), each its own commit; a boot QEMU
refuses names QEMU's line in its verdict. #86 closable at merge. Weak:
the churn rate itself.

**P5. Existing suites** green as root and as a user, on kasumi (the
ones with a kasumi path) and in CI's `tier full`.

**P6. Plants**, each a branch never merged, one commit, run by
dispatch: A (#85) as P1; B (#82), a semaphore read takes the whole
counter: mpx4-ready red at evprobe's semaphore lines (T2) and mpx5-jobs
J8 red at fdtab's semaphore rows (dispatched with `jobs_boots=fds:serial`);
C (#83), `/dev/std*` back to a device that opens the descriptor
(readlink -EINVAL, lstat a character device): mpx5-jobs J8 red at the
`N:` rows, root and `pax` (`jobs_boots=fds:serial`).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | a dispatch names mpx5-jobs' images (`jobs_boots`); plant A again red in CI at J9, 21 of 26 pelt sessions as root and as `pax`, groups green, no probe booted | run 39301238445: **J9 red at 21 of 26 pelt sessions as root and 21 of 26 as `pax`** on native BIOS, release BIOS and native UEFI (the same 21 on each, and kasumi's px51 count), the five that ask nothing of the foreground green; groups green (J10, 73 lines, root and `pax`); no probe booted (`boots: pjobs:serial pjobs-user:serial groups:serial`). The fourth leg (release UEFI) never ran: each pjobs boot waited out qemu-halt's 900 s prompt deadline at step 177 (15.5 min a boot, 35 min a leg), so the job met its 120-minute cap there and was cancelled | right on three legs; the fourth cut by the cap |
| P2 | Linux: a semaphore read takes 1, F_GETFL `O_RDWR\|O_NONBLOCK` and nothing more, poll, the top, a blocking read, two readers, epoll as listed; fdinfo `flags: 02` (weak) and `eventfd-semaphore: 1`; PAX identical after the change; mpx4-ready's `~` lines four, refusals two | every row as predicted on kasumi's 7.2.8 in a container (root and 1000:1000, twice, one digest: `notes/px52/linux-evprobe.txt`) and on real root's guest (fdinfo `flags: 02`, `02004002` with NONBLOCK and CLOEXEC; `eventfd-semaphore: 1`; the read leaves `eventfd-count` 2 of 3); trunk's kernel red at evprobe's semaphore lines (`notes/px52/kasumi-mpx4-ready-trunk-kernel.out`); the branch's kernel byte-identical in every way on kasumi (none, peer, user; T2 four `~` lines, T4 two refusals) and in fdtab (J8) | right |
| P3 | Linux: the three links (and `/dev/fd`) on kasumi's host and in a container, 0777, root's, 15 bytes; devtmpfs alone none (weak); the rows through them as listed; PAX identical; `/dev/fd` not added; no existing session moves | so: kasumi's host and podman's `/dev` (`notes/px52/kasumi-dev-links.txt`), CI's Docker too (the plants' J0 linux fds-user); **devtmpfs has none** (the guest's meta: `No such file or directory` for all four), so the guest's links are made by `notes/px52/vmjob.c`; every N row as predicted, root and 1000:1000 (one row apart by design: root's 0644 file reopened for writing through `/dev/stdin`, 0 to root, EACCES to a user); PAX byte-identical at the first boot (fds 147 lines, fds-user 142, the container's 141 with the zombie row left out), and mpx3-tree's shell-inout (193 lines) and shell-inout-user (182) identical to the container with the three new lines; every existing session as before | right |
| P4 | the harness, not the kernel: QEMU refused the forward, the port taken in the ephemeral range; loops 0 in 100 plain and 0 in 100 under load, a measurable rate under churn, each QEMU's line with an empty serial log, 0 in 100 with the fix under churn; the fix in four pickers | **0 of 100 plain, 0 of 100 under load, 10 of 100 under churn, 0 of 100 with the fix under churn**: each of the ten refused at 0.3 s with QEMU's own line (`Could not set up host forwarding rule 'udp:127.0.0.1:39453-:7'` and nine like it), the serial log empty, the very shape of push run 39086412018; all ten on ports inside 32768–60999 (10 of the 31 such ports in that loop; 0 of its 69 outside); none silent after QEMU started, in any loop; the fixed picker's ports 20251–32734, none in the range (`notes/px52/udp-loop/`) | right |
| P5 | every suite green on kasumi and in CI's `tier full` | kasumi, native BIOS, TCG: mpx4-ready (none, peer, user), mpx5-jobs (every image), mpx3-tree, mpx3-shell, mpx3-boreutils, mpx5-users, mpx5-accounts, `tests/ci-plan` (151 PASS); CI's `tier full`: named in the pull request | right on kasumi |
| P6 | plants B and C red in CI where named | B (39302273238): mpx4-ready red at evprobe's semaphore read (`the value 2`, Linux's 1) on the first leg, its own fail-fast stopping the rest; mpx5-jobs J8, J3 and J4 red on all four legs, root and `pax`, at exactly the semaphore's read row (115c115). C (39302278191): mpx5-jobs J8, J3, J4 red on all four legs at the N link rows; mpx3-tree T1 red on all four legs in both shell-inout sessions at `readlink`'s three lines | right |

## A. A later image's red in CI (pax#85, item 1)

The choice is a dispatch that names the images (P1's argument, which
the plant's run bore out its cost argument: even with three images
named, each pjobs boot under plant A waited out the 900 s prompt deadline
once, 35 minutes a leg, and the fourth leg met the job's 120-minute cap;
every image booted regardless would have paid that again for the probe
and the shells before the pelt images). `.github/workflows/ci.yml` takes a
`workflow_dispatch` input `jobs_boots`, passed to mpx5-jobs as
`PAX_JOBS_BOOTS` (empty on every other event: every boot, as before);
`tests/mpx5-jobs` refuses a boot it does not know by name (exit 2),
prints `boots: … (PAX_JOBS_BOOTS: a subset of the suite's boots, not
its verdict)`, ends `PASS (a subset, …)` or `FAIL (a subset, …)`, and
runs the container's user sessions of the chosen images only (the
fds-only plants' container step took about a second in CI, 39302273238,
where every session's takes eleven minutes). An ordinary run
still stops at its first image whose first prompt never comes; that run
is red, which is what the merge rule needs, and a dispatch shows the
rest. Under ruling #92 a plant runs `-f tier=pr` (one leg): with
`jobs_boots` one leg shows a later image's red as well as four do, so a
plant on mpx5-jobs needs no other leg (`CLAUDE.md`'s plant line says
so). The three plants of this lane were dispatched on the full tier,
before the ruling.

## B. EFD_SEMAPHORE (pax#82, item 2)

Linux 7.2.8 (`user/net/evprobe.c`, a rootless container, root and
1000:1000): `eventfd(2, EFD_SEMAPHORE|EFD_NONBLOCK)` a descriptor,
F_GETFL `O_RDWR|O_NONBLOCK`; at 2 POLLIN|POLLOUT; a read takes 1 (8
bytes, the value 1), again 1, then -EAGAIN; at zero POLLOUT alone; a
write of 3, three reads of 1; a read into 4 bytes -EINVAL with the 1
left; `0xffffffffffffffff` -EINVAL; at the top POLLIN alone and a write
of 1 -EAGAIN; a read there takes 1; a blocking read at zero ended by a
child's write of 2 takes 1 and leaves 1; two readers waiting at zero,
one write of 2: both end at once, each with 1; level-triggered epoll
ready at 2 and 1, not at 0. fdinfo (real root's guest): `flags: 02`
(EFD_SEMAPHORE is the counter's, never a status flag: its number is
O_WRONLY's), `eventfd-semaphore: 1`. PAX now answers every row the same:
`kernel/event` marks a counter a semaphore (`ev_new`'s `sem`; the use
word 2) and `ev_take` takes 1 of it; `kernel/ready` takes the flag
(refusal 103 retired) and keeps it out of the descriptor's status flags;
`kernel/procfs` prints the mark. `tests/mpx4-ready`: evprobe's
semaphore lines are compared lines now (four `~` lines, two refusals by
name).

## C. /dev/stdin, /dev/stdout, /dev/stderr (pax#83, item 3)

Linux: kasumi's host (CachyOS, systemd's boot) and a rootless podman
container: `lrwxrwxrwx root root 15 /dev/stdin -> /proc/self/fd/0`,
`stdout`, `stderr` the same, and `/dev/fd -> /proc/self/fd` (13 bytes);
CI's Docker container too. **devtmpfs alone makes none** (the guest:
-ENOENT at all four names), so they are userspace's (a distribution's
boot, a container runtime); the guest gets them from
`notes/px52/vmjob.c` at its start, and the rows hold the kernel's
answers through them. The N rows (`user/elf/fdtab.c`, root and
1000:1000, recorded twice, the same bytes): `readlink`
`/proc/self/fd/N`, `lstat` and `statx` with AT_SYMLINK_NOFOLLOW a link
0777 of 15 bytes, nlink 1, 0:0, DT_LNK in `/dev`'s listing; `readlink`
with room for 5 bytes 5 `/proc`; O_NOFOLLOW -ELOOP; with descriptor 0 a
file at offset 3, `stat` the file's, `open` a new open file read from 0
(`abc`) and descriptor 0 still at 3, a trailing `/` -ENOTDIR; root's
0644 file as descriptor 0 reopened O_WRONLY through `/dev/stdin`: 0 to
root, EACCES to a user; descriptor 0 a directory: `stat` the
directory's, O_DIRECTORY 0, `/dev/stdin/.` 0; **descriptor 1 a file
opened O_APPEND: `open("/dev/stdout", O_WRONLY|O_CREAT|O_TRUNC)`
truncates it to 0 bytes**, `x` through the new descriptor and `y`
through descriptor 1 make `xy` (pelt's `> /dev/stderr` under `2>> f`
does the same: shell-inout's new line); descriptor 2 a pipe's write end
reopened, the byte reaches the read end; a socketpair's end -ENXIO;
descriptor 0 closed: `open` and `stat` -ENOENT, `lstat` and `readlink`
still the link. PAX's `/dev/std*` are links now (`kernel/files`:
`is_link_node`, `link_bytes`, `link_target`; the walk rewrites the path
to `/proc/self/fd/N` as for the tree's links and px50's magic link does
the rest), so every row above is `/proc/self/fd/N`'s with its rules;
px17's own reopen of descriptor N and px50's `std_target` are gone.
boreutils' `readlink` of the three, pelt's `> /dev/stderr`, and `cat
/dev/stdin < f > /dev/stdout | wc -c` join mpx3-tree's shell-inout
sessions (root and `pax`). Left: `/dev/fd` (Linux has it beside the
three; not asked; listed to file).

## D. The silent UEFI boot (pax#86, item 4)

**Cause found: the harness, not the kernel and not UEFI.** Push run
39086412018's artifact keeps QEMU's own log for the boot:
`hostfwd=udp:127.0.0.1:37606-:7: Could not set up host forwarding rule`,
QEMU ended in 0.103 s with status 1, the serial log 0 bytes
(`notes/px52/ci-39086412018/`). The suites' `pick_ports` probed a port
free and closed it; `tools/udp-host`, started next, binds a socket to
port 0 (and so does anything else on the host that sends: a resolver);
37606 lies in the host's ephemeral range, where such a socket lands; one
took it before QEMU's bind. The loops (`notes/px52/udp-loop.sh`, the
suite's own order and arguments, the native user image under OVMF,
TCG, `taskset -c 0-3`, each boot to the kernel's first line; trunk
`d6fbcdc`'s images and picker): **0 silent of 100 plain, 0 of 100 under
load** (four busy loops on cpus 0-3; 27–30 s a boot, against 1.6–2.8 s
plain); under churn (a process binding UDP sockets to port 0 as fast as
it can, the newest 8,000 held, the loop in its own network namespace so
nothing reached the host's or another lane's ports) **10 of 100**, each
QEMU's line, 0.3 s, an empty serial log, every one on a port inside
32768–60999 (10 of that loop's 31 such ports, 0 of the 69 outside);
with the fix under the same churn **0 of 100** (ports 20251–32734). The
fix: `tests/mpx4-udp`, `mpx4-net`, `mpx4-tcp` and `mpx4-ready` pick
ports outside the host's `ip_local_port_range` and IANA's dynamic range,
and a boot QEMU refuses names QEMU's line in its verdict. The natural
rate on kasumi is below 1 in 200 (0 seen); the issue is closable at
merge on the cause.

## E. Existing suites on kasumi

Native, BIOS, TCG; builds in `px13-ubuntu`: mpx4-ready (none, peer,
user) under `taskset -c 0-3`; while the loops held cpus 0-3, under
`taskset -c 8-11` with builds on 12-15: mpx3-tree, mpx5-jobs (every
image), mpx3-shell, mpx3-boreutils, mpx5-users, mpx5-accounts — every
one PASS, no FAIL line (`notes/px52/kasumi-*.out`); `tests/ci-plan` 151
PASS. Two of kasumi's own conditions, not PAX's: (1) a second build of
mpx4-ready ran its Linux side when kasumi's shared user had passed
`fs.pipe-user-pages-soft` (16,384 pages), so Linux gave new pipes 8,192
bytes and nbprobe's `writes until the pipe is full` row read 8192 there;
the boots were held to the first build's Linux side of the same binaries
(evprobe `0ea84b2b…` in both, `notes/px52/kasumi-mpx4-ready-linux-side.txt`);
(2) mpx4-udp's own build on kasumi cannot run its `none-user` container
from inside `px13-ubuntu` (no engine there), which the loops did not
need.

## F. CI

- The pull request's runs: named in the pull request (a commit naming
  them would move the head). Under ruling #92 the lane hands back once
  the `tier pr` run is green at the final head and `full-matrix` is on;
  the orchestrator holds the `tier full` run.
- The plants' runs: §G.

## G. Plants (P6)

Each a branch never to be merged, cut from the branch's head, one
commit, run by dispatch with its suites only, all four legs (dispatched
before ruling #92).

| plant | branch, commit | break | CI |
|---|---|---|---|
| A (#85) | `px52-plant-a` `359ba14` | px51's plant A (`0e22d80`) again: TIOCSPGRP answers 0 and changes nothing | run **39301238445**, `jobs_boots="pjobs:serial pjobs-user:serial groups:serial"`: J9 red at 21 of 26 sessions as root and as `pax` on native BIOS, release BIOS and native UEFI, groups (J10) green, no probe booted; the fourth leg cut by the job's 120-minute cap (each pjobs boot waited out the 900 s prompt deadline once) (`notes/px52/ci-39301238445-plant-a.txt`) |
| B (#82) | `px52-plant-b` `eeba078` | a semaphore's read takes the whole counter | run **39302273238**: mpx4-ready job 118230478698 red at evprobe's `semaphore: read: 8 bytes, the value 2` (Linux's 1), native BIOS, the later boots stopped by its own fail-fast; mpx5-jobs job 118230478315 (`jobs_boots=fds:serial`) J8, J3, J4 red on all four legs at the read row alone (`notes/px52/ci-39302273238-plant-b.txt`) |
| C (#83) | `px52-plant-c` `a51328e` | `readlink` of `/dev/std*` -EINVAL, `lstat` a character device, listed DT_CHR (the issue's own symptom; following kept) | run **39302278191**: mpx5-jobs job 118230533908 (`jobs_boots=fds:serial`) J8, J3, J4 red on all four legs at the N link rows; mpx3-tree job 118230533752 T1 red on all four legs in shell-inout and shell-inout-user at `readlink`'s three lines (`notes/px52/ci-39302278191-plant-c.txt`) |

## 4. Evidence index

Shas are this branch's (`px52`). kasumi paths are under `~/lanes/px52/`.

### What was written

- The prediction: `c77ddb8` (§1 to §3, before any change or measurement).
- #85: `752eaed` (`tests/mpx5-jobs`), `4f4cc8c` (ci.yml's `jobs_boots`).
- #82: `58c6ec9` (evprobe), `06ba38d` (`kernel/event`), `b3b6a60`
  (`kernel/ready`), `eced675` (fdinfo), `ca03b75` (`tests/mpx4-ready`).
- #83: `142c6b2` (fdtab's semaphore and N rows), `207a1eb`, `2c25e7e`
  (`kernel/files`), `63dd1aa` (`notes/px52/vmjob.c`), `5941952` (the
  recordings), `5664d46` (J8's witness), `6e45847` (shell-inout's
  lines), `dcfe0ee` (`tests/mpx3-tree`).
- #86: `e17c40b`, `ee16d15`, `d1d02ce`, `f9f2c61` (the four pickers).
- The words: `8188ec5` (`docs/SOURCES.md`), `065b9cd`
  (`kernel/README.md`), and README, CHANGELOG and `CLAUDE.md`'s plant
  line (the commits after this note's).
- The scripts: `e1aa64a`, `92f5900`, `ba16ac3`, `3f907c9`, `7d18a32`,
  `cc2f285`, `e2ef6ff` (`notes/px52/*.sh`).

### What was measured, and where it is

- **Linux's semaphore**: `notes/px52/linux-evprobe.txt` and
  `linux-evprobe.sums` (four runs, one digest; evprobe `0ea84b2b…`, the
  suite's own build's too).
- **Linux's /dev**: `notes/px52/kasumi-dev-links.txt` (kasumi's host
  and podman); the guest's devtmpfs and links in
  `tests/mpx5-jobs.d/linux/vm-fds.meta`, `vm-fds-user.meta`.
- **Real root's recordings**: `tests/mpx5-jobs.d/linux/fds.tty`,
  `fds-user.tty` (kasumi's 7.2.8 `f4c00d5d…` under QEMU 11.1.1, vmjob
  `2a3a7f57…`, the suite build's fds archive `cd622c9f…`), made twice,
  the same bytes (`notes/px52/kasumi-recordings-twice.out`).
- **PAX on kasumi**: `notes/px52/kasumi-mpx4-ready-trunk-kernel.out`
  (trunk's kernel, red at evprobe), `kasumi-mpx4-ready.out`,
  `kasumi-mpx5-jobs.out`, `kasumi-mpx3-tree.out`, `kasumi-mpx3-shell.out`,
  `kasumi-mpx3-boreutils.out`, `kasumi-mpx5-users.out`,
  `kasumi-mpx5-accounts.out`, `kasumi-regress.out`, `kasumi-ci-plan.out`.
- **#86**: `notes/px52/ci-39086412018/` (CI's artifact 12120719249),
  `notes/px52/udp-loop/` (each loop's `head.txt`, `loop.tsv`,
  `summary.txt`; one refused boot's files, `trunk-churn/b12.*`;
  `udp-chain.out`).
- **The plants**: `notes/px52/ci-39301238445-plant-a.txt`,
  `ci-39302273238-plant-b.txt`, `ci-39302278191-plant-c.txt`.

### Measured, inferred, not verified

**Measured**: everything in §A to §G but what follows.

**Inferred**:
- That `udp-host`'s own `ask` socket is what took 37606 in CI: it binds
  port 0 in that window, but so may any process on the runner; the
  churn loop shows the mechanism, not which socket it was.
- That the TCP pickers (mpx4-tcp, mpx4-ready) had the same exposure: a
  connected socket's local port is chosen from the same range; no
  refused TCP forward was seen.

**Not verified**:
- Real root was one kernel (kasumi's 7.2.8) and one terminal kind; CI's
  runner kernel answered the semaphore rows (mpx4-ready's live Linux
  side) and the container's link rows (J0) the same.
- A semaphore with more than two waiting readers; EPOLLET on a
  semaphore.
- Root's `unlink` or `rename` of `/dev/std*` (Linux's root may; not
  asked); `/dev/fd`.
- The loops' natural rate below 1 in 200 (none seen); UEFI under KVM;
  more than one CPU.

### Issues

- **To close at merge**: pax#85 (a dispatch names the images; plant A's
  later-image reds in CI, 39301238445), pax#82 (served, measured),
  pax#83 (links, measured, root and user), pax#86 (the cause found and
  fixed: QEMU's refusal, the ephemeral port; 0 of 200 natural, 10 of 100
  under churn before the fix, 0 of 100 after).
- **Would file (none filed)**:
  1. pax: `/dev/fd` (Linux's link to `/proc/self/fd` beside the three)
     is absent on PAX.
  2. pax: `tests/mpx4-session`'s `free_port` and `tools/lobo-session`'s
     `free_ports` pick a host port by binding port 0 and closing it:
     inside the ephemeral range by construction, the same race as #86
     before its fix.
  3. pax: on kasumi a build's Linux side can meet
     `fs.pipe-user-pages-soft` (the lanes share one user), so a Linux
     pipe holds 8,192 bytes and mpx4-ready's nbprobe reference moves;
     a kasumi-only condition, named here.
  4. pax: mpx4-ready's own fail-fast (no boot after a failed one)
     hides a later way's or leg's red as mpx5-jobs' did (plant B's
     run); it has `--keep-going` but no dispatch input.

## 5. Done-when

- Branch `px52` on origin; the pax pull request (number in the
  hand-back), open, unmerged.
- The five sections §1 to §5; the items §A to §G.
- The test checklist:
  - [x] Linux measured first: evprobe in a container (root, user, twice),
        `/dev` on kasumi's host and in podman, fdtab on real root's
        guest (twice, the same bytes)
  - [x] `tests/mpx4-ready` on kasumi, native BIOS, none, peer, user;
        trunk's kernel red at evprobe's semaphore lines
  - [x] `tests/mpx5-jobs` on kasumi, native BIOS, every image (J8 fds
        and fds-user byte-identical to real root and the container)
  - [x] `tests/mpx3-tree`, `mpx3-shell`, `mpx3-boreutils`, `mpx5-users`,
        `mpx5-accounts` on kasumi, native BIOS
  - [x] `tests/ci-plan`, every case
  - [x] #86's loops: 0/100 plain, 0/100 load, 10/100 churn, 0/100 fixed
  - [x] plants A, B, C red in CI (39301238445, 39302273238, 39302278191)
  - [ ] `tier pr` green at the final head, `full-matrix` on: named in
        the pull request; `tier full` held by the orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px52 <PR>` exit status: named in the
  hand-back.
- Trees: kasumi `~/lanes/px52/` keeps `out/`, `ev/`, `vm/`, `bin/`,
  `cache/`; build directories removed at the end. Plant branches stay
  on origin, never to be merged.
