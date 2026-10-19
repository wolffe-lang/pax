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
