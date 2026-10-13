# px39 — The credentials (P5 lane U1: a process has an identity)

Contract: px39's, `sprints/pax/39-the-credentials/` in wolffe-lang/wolf
(planning commit `c7b99e6`, read 2026-10-13), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/wave-53.md` down to `wave-45.md`. Branch `px39` in
pax, cut from pax trunk `58428ba`. §1 to §3 are committed before the
first change to the kernel.

One deliverable: a process on PAX has eight ids (real, effective,
saved and file-system; user and group) and a list of supplementary
groups, kept over `fork` and `execve` as Linux keeps them, and the
twelve calls px38 named answer by Linux's rules for root and for a
user. `/proc/<pid>/status` and the auxiliary vector say what the
record holds.

**What this lane does not do.** No permission check changes: no file,
directory, signal, port or device is refused to anyone because of who
asks. A process may now *be* a user, and nothing but the id calls' own
rules treats it differently. That is U3 to U5. Set-ID execution is not
honoured (R5): `execve` never raises an id. The ruled claim for the
campaign is "enforced for honest programs; not a boundary against an
attacker" (R6), and this lane enforces nothing yet.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read, nor that of
  `su`, `login`, shadow-utils or util-linux (ruling #22). Facts come
  from the man pages (`credentials(7)`, `capabilities(7)`,
  `setuid(2)`, `setreuid(2)`, `setresuid(2)`, `setfsuid(2)`,
  `getgroups(2)`, `getresuid(2)`, `execve(2)`, `prctl(2)` and
  `PR_SET_DUMPABLE(2const)`, `getauxval(3)`, `proc_pid_status(5)`,
  `user_namespaces(7)`), POSIX.1-2024, the uapi headers the refs
  clone's sparse checkout holds, pax's own source, px38's recorded
  Linux answers, and black-box runs made the way px38 made them.
- No syscall number is added that is not in px38's traces or probes:
  the twelve are 105, 106, 113, 114, 115, 116, 117, 118, 119, 120, 122,
  123. `capget`, `capset` and the process-group calls stay -ENOSYS.
- No permission check is added or changed. `execve` never raises an id.
- No account is made on any host; no `sudo` for a test. A Linux answer
  for **root** comes from kasumi's own kernel image booted under QEMU
  with a static program as pid 1 (**vm**); a rootless container's root
  (**ct**) is a reference for users' rules only and never for what
  root may do. Each compared row names its reference.
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's
  own glibc.
- No word implying filming. Nothing calls PAX secure.
- No build on nomad-1. kasumi: commands under `bash`, long jobs under
  `setsid` with a pid file and ended by that pid only; work under
  `~/lanes/px39/`, pruned as I go; never `/tmp`. Host ports 8080 and
  8088 are not used.
- No `rm` outside `~/lanes/px39/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR.
- px40's files (`tools/ci-tiers.map`, `tools/ci-plan`,
  `.github/workflows/ci.yml`) are touched only for the new suite's own
  lines. No run of another lane is cancelled.
- "Seen red" cites a run. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-13)

| input | found |
|---|---|
| pax trunk | `58428ba` (px37 merged), the contract's |
| planning repo | `c7b99e6`: the contract, the campaign file with R1 to R9 |
| the kernel's pin | wolf 0.2.28 (`3215f321…`, pin `f71ece8e`) / lupin 0.1.51 (`kernel/wolf.pin`) |
| px38's note and files | `notes/px38-the-users.md`; `notes/px38/probes/cred.c` and `px38.h`; `notes/px38/linux/vm.txt` (3,400 lines), whose `cred` section is lines 77 to 2,760: **2,684 lines**, the contract's count; `check-cred.py` on it: 2,640 rows, 0 wrong |
| the one line | `kernel/user/user.lu`: `getuid`, `getgid`, `geteuid`, `getegid` return 0 in one `if`; no other id call has a number |
| where identity can live | the process area (`sched.PROC_AREA`, 40,960 bytes a slot): `sched.clone_current` copies it whole for a fork and for a vfork child, `sched.exec_alone` copies it to a thread that execs, `execve` keeps it, a process's threads share their leader's. Words in use, counted from every `get`/`put` of an area in `kernel/`: 0 to 3 (`kernel/vm`, the refusal word), 4 to 11 (`kernel/user`'s logged calls), 12 (the working directory), 15, 144 and 145 (`kernel/socket`), 146 (the console's flags), 147 (`kernel/ready`), 254 (the umask), 255 (the program's entry), 256 to 511 (the signal actions), 512 to 4,607 (descriptors), 4,608 to 5,119 (reservations). **Words 16 to 143 and 148 to 253 are named by nothing** (px38 said 148 to 253, "read, not proven") |
| `/proc` | `kernel/procfs`: `status` prints `Uid:\t0\t0\t0\t0`, `Gid:` the same, `Groups:\t \n`, five capability masks of zero, `NoNewPrivs:\t0`; no `/proc/self/setgroups` |
| the auxiliary vector | `kernel/process`'s `build_stack`: AT_UID, AT_EUID, AT_GID, AT_EGID, AT_SECURE written as 0 |
| `prctl` | `kernel/user`: PR_GET_NAME and PR_SET_NAME; every other option -EINVAL |
| pax#48, pax#49 | both open; #49 is this lane's (two `prctl` answers), #48 is U2's |
| `tools/ci-tiers.map` | `kernel/user`, `kernel/process`, `kernel/procfs` are `@user`'s (18 suites on the pr leg); a new directory under `kernel/` is FULL until a rule names it |
| kasumi | Linux 7.2.8-1-cachyos, QEMU 11.1.1 (TCG), `px13-ubuntu` `ad896450…`, `/home` 32 GB free |

**Drift from the contract, found before any change.** The contract
asks for the `cred` probe "byte-identical to the real-root Linux
recording" (2,684 lines) and, by R4, for a group list "bounded at 32".
Both cannot hold for one line of the recording:

    root setgroups(65536, list) = 0, then getgroups(0, NULL) = 65536

A kernel that keeps at most 32 groups answers -EINVAL there. R4 is a
ruling and px38's own gap table gave the answer ("more than 32 groups:
-EINVAL, by name"), so the bound stands and that one line is compared
by rule, with PAX's own text held exactly. The target is **2,683 of
2,684 lines byte-identical and one line named**.

Two more things the probe's lines need that the contract's list does
not name: `prctl(PR_GET_DUMPABLE)` (every `show` line ends with it;
-EINVAL today) and the file `/proc/self/setgroups` (one line reads
it). And the probe prints the capability mask of every row, with two
values R9 does not name: `000001fef7fffde0` (effective id 0,
file-system id not 0) and `000000010800021f` (the reverse). R9's rule
("effective uid 0 for everything but files, file-system uid 0 for
files") is exactly what those two masks say, so the status lines print
them.

## 3. Prediction (committed before the first change)

**P1. The record.** Forty-two words of the process area hold it (eight
ids, a count, 32 groups, one word for "not dumpable"), all zero for a
fresh process, which is therefore root with no groups: no kernel start
path changes. No change to `kernel/sched` is needed for fork, vfork,
threads or `execve` to carry it. Falsified if `kernel/sched` or
`boot/sched.S` must change.

**P2. The model needs no correction.** `check-cred.py`'s rule,
written into the kernel as it stands, gets all 2,640 matrix rows of
the recording at the first boot that runs to the end. Falsified by any
row that needs a rule the model does not have.

**P3. As root: 2,683 of 2,684.** With the twelve calls, the status
lines, the masks, PR_GET_DUMPABLE and `/proc/self/setgroups`, `cred`
as the first program writes the recording's `cred` section but for
the `setgroups(65536, list)` line, which reads `= -22, then
getgroups(0, NULL) = 4` on PAX. Falsified by any other differing
line, on any of the four legs.

**P4. Dropped to uid 1000: 2,983 lines.** `cred` run by a process
that first became 1000:1000 with no groups writes, on Linux, 2,983
lines: of the 1,584 user rows only the 264 of state (1000 1000 1000)
can be set up (the other 1,320 are a `! state` line and a `! a row's
child failed` line each), the 528 group rows of the first group
section fail the same way, the `u1000` section and the seven
fork-and-execve cases write nothing but a header, and the groups
section writes ten lines. PAX's are byte-identical, **all** of them:
I expect Linux to refuse an unprivileged `setgroups` (-EPERM) before
it looks at the count, so the 65,536 line does not differ here.
Falsified by a different count on Linux or by any differing line.

**P5. What is not in px38's recording, to be measured on vm first.**
- *dumpable* is cleared when a call changes the effective or the
  file-system user or group id to a different value, and by nothing
  else (not by a call that leaves them as they were, not by
  `setgroups`, not by a change of the real or saved id alone); at
  `execve` it becomes 1 when real and effective ids are equal for
  user and group, else 0.
- AT_SECURE is 1 exactly when the real and effective user ids, or the
  real and effective group ids, differ at `execve`; the file-system
  id does not enter into it.
- `CapPrm` is full while any of the three user ids is 0 and zero
  otherwise; `CapInh` and `CapAmb` zero; `CapBnd` full always.
- an id argument is read as 32 bits (`setuid(0x1000003e8)` is
  `setuid(1000)`).
- `getresuid` with a bad pointer is -EFAULT; `getgroups(2, bad)` with
  two groups is -EFAULT.
- `Groups:` with no group is `Groups:\t\n`; PAX prints `Groups:\t \n`
  today (px34 copied a container's line): **one of the two is wrong
  and I expect it to be PAX's.**

Each is falsified by the measured line.

**P6. Every existing suite unchanged.** No file under `tests/` but
the new suite and `tests/ci-plan`'s new case is edited; the eighteen
`@user` suites pass as they are on kasumi, also under `taskset -c
0-3`, and in CI on four legs. The only bytes an existing program can
see move are `/proc/<pid>/status`'s `CapPrm`, `CapEff` and `CapBnd`
(zero today, Linux's root masks after) and, if P5's last line holds,
`Groups:`; no existing test reads either. Falsified by any existing
suite that needs an edit to pass.

**P7. The soak.** 100,000 id changes and 10,000 forks that each
change ids leave the frames-free count where it started (the record
is in the area: nothing is allocated). Falsified by any drift.

**P8. Plants.** With the unprivileged check of `setuid` removed, the
root run is still green for the (0 0 0) rows and red on the first row
of state (1000 1000 1000) whose answer is -EPERM; with `fork` not
carrying the record, red at `case 0 forked`. Both red in CI, one
suite each.
