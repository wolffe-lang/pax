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

### Corrections to §3, found after it was committed

- P4's count, "2,983 lines", is an arithmetic slip: the parts P4 lists
  (264 rows that can be set up, 1,320 and 528 rows of two lines each,
  ten lines of groups, the headers) add up to **3,983**, which is what
  Linux wrote. The slip was published, so it is scored as one.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | 42 words of the process area, zero is root; `kernel/sched` and `boot/sched.S` untouched | words 160 to 201 (`kernel/cred`); `git diff 58428ba -- kernel/sched boot/` is empty; a fork's child, a vfork's child, a thread and an `execve` all carry the record with no line of the scheduler changed (`ident`'s `vfork:`, `~thread:` and `exec` rows; `cred`'s `forked` rows) | right |
| P2 | the model needs no correction: all 2,640 matrix rows at the first boot that runs to the end | the first boot of `cred` (kasumi, native BIOS, the tree of `60f3fd3`) wrote all 2,640 matrix rows as recorded; `kernel/cred`'s four `set*` functions are `check-cred.py`'s `model` line for line and were not edited after | right |
| P3 | as root 2,683 of 2,684, the one line `= -22, then getgroups(0, NULL) = 4`; on four legs | exactly that, on native and release, BIOS and UEFI (`notes/px39/kasumi-mpx5-users-059e677.out`; CI run 38474383913's `mpx5-users` job on native BIOS). The other 43 non-matrix lines needed what §2 named: PR_GET_DUMPABLE, `/proc/self/setgroups`, the two partial masks | right |
| P4 | dropped to 1000:1000, **2,983** lines on Linux; PAX identical in all of them; Linux refuses a user's `setgroups` before it reads the count | **3,983** lines on Linux (the slip above); PAX byte-identical in all 3,983; a user's `setgroups(65537, …)`, `(-1, …)`, `(65536, …)` and `(1, NULL)` are all -EPERM on Linux, so the R4 line does not differ for a user | wrong on the count (arithmetic); right on the rest |
| P5a | dumpable cleared by a change of value of an effective or file-system id, by nothing else; at `execve` 1 when real and effective are equal | the first half as predicted (29 `dump:` rows as root, 29 as a user). **At `execve` the file-system ids count too**: 1 only when real, effective *and file-system* ids are equal, user and group (`exec 5`, `6`, `12`, `13`, `15`, `16`, `19`, `20`: 0 with only a file-system id apart) | half right |
| P5b | AT_SECURE is 1 exactly when real and effective user or group ids differ; the file-system id does not enter | true of the file-system **user** id (`exec 5`, `12`, `19`: 0). **False of the group side**: AT_SECURE is also 1 when the effective group id is neither the file-system group id nor in the supplementary list (`exec 6`, `14`, `17`, `20`: 1; `13`, `15`, `16`: 0, the effective group in the list) | wrong |
| P5c | `CapPrm` full while one of the three user ids is 0, else zero; `CapInh`, `CapAmb` zero; `CapBnd` full always | as predicted, in nine states and after every `execve` (`status` and `exec` rows) | right |
| P5d | an id is 32 bits | `setuid(0x1000003e8)` is `setuid(1000)`; `0x1ffffffff` is -1; `getgroups`' and `setgroups`' count is an int too | right |
| P5e | `getresuid` with a bad pointer -EFAULT; `getgroups(2, bad)` -EFAULT | as predicted; and the three ids are written in order, those before the bad pointer already written; `getgroups` and `setgroups` look at the count before the pointer | right |
| P5f | `Groups:` with no group is `Groups:\t\n`, and PAX's `Groups:\t \n` is wrong | **Linux prints `Groups:\t \n`**: one space when there is no group, and a space after each group when there are some. PAX's line (px34's) was right | wrong |
| P6 | every existing suite unchanged; no existing test reads the bytes that move | no file under `tests/` is edited but `tests/ci-plan` (two new cases); all 29 existing suites green on the pr leg at `ae80ea3` (run 38474383913) and on every leg at the head (the PR names that run) | right |
| P7 | 100,000 id changes and 10,000 forks leave the frames where they were | 1,000,000 calls and 10,000 children, as root and as a user: the free memory the program reads is one number at every quarter (`MemFree … 247316 247316 247316 247316 kB`), and the kernel's frames line the same before and after, on every leg | right |
| P8 | plant A red on the first -EPERM row of state (1000 1000 1000), the (0 0 0) rows green; plant B red at `case 0 forked` | A exactly (line 268, `(1000 1000 1000) setuid(0)`, 23 lines). **B is red earlier**, at line 2,117, the first `u1000` row: every row is asked by a forked child, and a child that starts as root answers the user's group rows as root (536 lines) | A right; B wrong on where |

## A. Where identity lives; what fork and execve do with it (item 1)

**The record** is 42 words of the process area (`kernel/cred`,
words 160 to 201): four user ids and four group ids (real, effective,
saved, file-system), the count of supplementary groups, one word that
is 1 when the process is not dumpable, and 32 words of groups, kept
sorted. Zero is root with no group and dumpable, so a process the
kernel starts needs no code here.

| event | what happens to the record | where |
|---|---|---|
| a fork (`clone` without CLONE_VM) | the child has a copy: the area is copied whole | `sched.clone_current`, unchanged |
| a vfork (CLONE_VM\|CLONE_VFORK) | the same: its own copy, though it borrows the address space (`ident`: a vfork child's `setresuid` leaves the parent root, as on Linux) | `sched.clone_current`, unchanged |
| a thread (CLONE_THREAD) | none of its own: every thread reads its leader's area. **Ids are a process's on PAX; Linux keeps them per thread** and glibc makes them one by signalling every thread (`nptl(7)`). Measured: a second thread's raw `setresuid(1000, 1000, 1000)` leaves the first thread's `getuid` 0 on Linux, 1000 on PAX (`~thread`). A libc that repeats the call in every thread gets the same answer each time on PAX: each `set*id` call that succeeds once succeeds again unchanged (checked against the model for all four) | `sched.proc_area`, unchanged |
| `execve` | real and effective ids and the groups are kept; **the saved and the file-system ids become the effective ids**; dumpable becomes 1 only if real, effective and file-system ids were equal; the new program is told AT_UID, AT_EUID, AT_GID, AT_EGID and AT_SECURE. **No id is raised: the file's set-ID bits are not read** (R5; `ident`: a mode-6755 root file run by 1000 leaves 1000 1000 1000 1000, AT_SECURE 0, as Linux on a nosuid mount) | `cred.exec`, `cred.at_secure`, `process.build_stack` |
| `execve` from a thread | the caller becomes the leader with a copy of the old leader's area | `sched.exec_alone`, unchanged |

## B. The twelve calls (item 2)

Privileged means effective **user** id 0, for the group calls too. An
id is 32 bits of its register; -1 leaves an id alone.

| call | rule (`kernel/cred`) | held by |
|---|---|---|
| `setuid` 105, `setgid` 106 | -EINVAL for -1; privileged: real, effective, saved; else the effective id alone, to the real or saved id, or -EPERM | 72 rows a run |
| `setreuid` 113, `setregid` 114 | unprivileged: real to real or effective, effective to real, effective or saved, else -EPERM; saved := the new effective when the real id is given or the effective id is given and is not the old real id | 432 |
| `setresuid` 117, `setresgid` 119 | unprivileged: each one of the three current ids, else -EPERM | 2,592 |
| `setfsuid` 122, `setfsgid` 123 | answers the previous file-system id always; moves when privileged or naming one of the four current ids | 72 |
| every one of those | on success the file-system id is the effective id; dumpable cleared when the effective or file-system id changed value | `dump:` rows |
| `getresuid` 118, `getresgid` 120 | three 4-byte writes in order; -EFAULT at the first bad pointer | `fault:` rows |
| `getgroups` 115 | 0: the count; below the count or negative: -EINVAL, before the pointer; -EFAULT | `fault:`, groups rows |
| `setgroups` 116 | unprivileged: -EPERM first; above 65,536: -EINVAL (Linux's); **above 32: -EINVAL, refused by name** (R4); -EFAULT; kept sorted, repeats kept | groups rows; `~bound` |
| `getuid` 102, `getgid` 104, `geteuid` 107, `getegid` 108 | from the record (they were one `return 0`) | `get` rows |

**What surprised me.**
- **AT_SECURE's group rule is not symmetric with its user rule.** A
  file-system *user* id apart from the effective one leaves AT_SECURE
  0; a file-system *group* id apart makes it 1 unless the effective
  group is also in the supplementary list. Seven `execve` rows were
  added to find the edges (`exec 12` to `20`); the rule in `at_secure`
  is what fits all 23, and it is measured, not explained: no man page
  I read says it.
- **dumpable at `execve` reads the file-system ids.** A root process
  that only called `setfsuid(1000)` is not dumpable after its next
  `execve`, though every id it then has is 0.
- **`Groups:` ends in a space even when empty.**
- **`setuid(-1)` is -EINVAL but `setfsuid(-1)` is not an error** (px38
  found the first; the second is its mirror: it answers the old id).
- **`prctl(PR_GET_NO_NEW_PRIVS, 1)` is -EINVAL** (every other argument
  must be 0), and the other three getters do not care.
- A user who is refused `setgroups` is refused before the count is
  read, so the 32-group bound is invisible to anyone but root.

## C. `/proc` and the auxiliary vector (item 3)

- `/proc/self/status` and `/proc/<pid>/status`: `Uid:` and `Gid:` the
  four ids tab-separated, `Groups:` the sorted list, each followed by a
  space (one space when empty). Read for another process too
  (`other:` rows: a parent reads its child's).
- The capability lines (R9), as Linux 7.2.8 prints them for the same
  ids: `CapBnd` `000001ffffffffff`; `CapPrm` that while one of the
  three user ids is 0, else zero; `CapEff` the permitted set cut to
  `000001fef7fffde0` when the effective id is 0 plus `000000010800021f`
  when the file-system id is 0; `CapInh`, `CapAmb` zero. A function of
  the ids alone: with no `capset` and no honoured set-ID file there is
  no other state (a process whose three ids are all non-zero can never
  get a 0 back). `capget` stays -ENOSYS.
- `/proc/self/setgroups`, `/proc/<pid>/setgroups`: `allow`, mode 0644.
- AT_UID, AT_EUID, AT_GID, AT_EGID, AT_SECURE: the process's own (23
  `execve` rows, as root; the user's start line).
- `prctl`: PR_GET_DUMPABLE from the record; PR_GET_KEEPCAPS,
  PR_GET_SECUREBITS 0; PR_GET_NO_NEW_PRIVS 0, or -EINVAL when another
  argument is not 0 (pax#49's two, and the two beside them).

## D. The programs against Linux (item 4)

Every reference is the **vm** root: kasumi's kernel image (Linux
7.2.8-1-cachyos, `f4c00d5d…`) booted under QEMU 11.1.1 with
`notes/px39/vminit.c` as pid 1, root of the initial user namespace,
`CapEff 000001ffffffffff` (`tests/mpx5-users.d/linux/vm.meta`). The
`-user` rows are the same boot after `as 1000 1000`. No row is compared
with a container's root.

| session | first program on PAX | lines | reference | identical | by rule |
|---|---|---:|---|---:|---|
| cred | `/bin/cred` (px38's binary: `72ab09fc…`, the digest px38 recorded) | 2,684 | vm, root: px38's recording, re-taken here byte for byte | 2,683 | 1: ruling R4 (`setgroups(65536, list)`) |
| cred-user | `/bin/as 1000 1000 /bin/cred` | 3,983 | vm, after `as 1000 1000` | 3,983 | 0 |
| ident | `/bin/ident /bin/ident-setid` | 225 | vm, root | 222 | 3 `~` lines: `~bound` (33 groups, R4), `~thread` (per process), `~owner` (a `/proc` file's owner: U2) |
| ident-user | `/bin/as 1000 1000 /bin/ident /bin/ident-setid` | 129 | vm, after `as 1000 1000` | 126 | the same 3 |
| ids | `/bin/ids` (px38's: `a053d49e…`) | 71 | vm, root | 59 | 12 named in `tests/mpx5-users.d/ids.pax`: five process-group calls and `capget` (-ENOSYS), SO_PEERCRED (U5), `chown` to 1000 (U2), four that are the machine's (the parent's pid, `/`'s mode, a `/bin`, `/etc/passwd`). Before px39: 29 of 71 (`notes/px38/pax/pax-ids.txt`) |
| soak, soak-user | `/bin/ident soak 100000` | 2 | vm | 1 | 1 `~soak` line (free memory) |

On all four legs (native and release, BIOS and UEFI): kasumi, TCG,
`notes/px39/kasumi-mpx5-users-059e677.out` (122 PASS, 0 FAIL, 0 SKIP,
28 boots; and the same at `ae80ea3`, before `at_secure` got its name),
and again under `taskset -c 0-3`
(`kasumi-taskset-0-3-mpx5-users-059e677.out`); hasu, KVM, kasumi's
images, BIOS, both tiers (`hasu-kvm-059e677.log`: three rounds, 42
boots; `hasu-kvm-211b095.log`: four rounds, 56 boots, the earlier
kernel); CI's runner on the pr leg and the full tier (the PR). **UEFI
under KVM on hasu is not shown**: with the firmware QEMU 11.1.0 ships
there, four native sessions passed and then Limine itself could not
open the kernel in the `ids` image (`PANIC: limine: Failed to open
executable`, before PAX runs); the same ISO boots under OVMF on kasumi.
Not chased: it is the boot loader's, on one host's firmware.

**The second witness for a user's rows**: the same three `-user`
sessions as uid 1000 of a rootless podman container
(`notes/px39/linux-ct.sh`, `notes/px39/linux/ct/`). It agrees with the
vm's in 3,980 of cred's 3,983 lines and 127 of ident's 129; the five
that differ are the two classes px38 named for a user namespace: an id
with no mapping is -EINVAL there (where the vm, and PAX, say -EPERM to
a user), and `CapBnd` is the container's. PAX has no namespace and
matches the vm.

**Repeatability of the reference**: `cred` was recorded three times
(px38's boot and two of this lane's), `cred-user`, `ident` and
`ident-user` twice each, and each is the same bytes every time; `ids`
differs in one line between boots (`setsid()` answers a pid).

## E. Existing suites unchanged; the soak (item 5)

- **No existing test is edited.** `git diff 58428ba --stat -- tests/`
  shows `tests/ci-plan` (+4 lines: two cases for the new suite) and
  the new `tests/mpx5-users` and `tests/mpx5-users.d/`; nothing else.
  No expect file, key file or recorded transcript under `user/` or
  `tests/` moves.
- **Every existing suite ran and is green**: all 29, with mpx5-users
  the thirtieth, on native BIOS at `ae80ea3` (run 38474383913, `tier
  pr`: the PR touches `.github/`, which selects every suite on the pr
  leg), and on all four legs at the head (the `tier full` run the PR
  names). On kasumi I ran only this lane's suite; the other 29 are
  CI's (as px36: their programs must not be built with kasumi's
  glibc).
- **What an existing program can see move**: `/proc/<pid>/status`'s
  `CapPrm`, `CapEff` and `CapBnd` (zeros before; `000001ffffffffff`
  for root now), and a `setgroups` entry in `/proc/self` and
  `/proc/<pid>`. `Uid:`, `Gid:` and `Groups:` are the same bytes for
  root as before. No existing test reads any of it.
- **No permission check changed.** `kernel/files`' diff is three lines
  (the name `setgroups` under `/proc/<pid>`); `kernel/tree`,
  `kernel/signal`, `kernel/socket`, `kernel/console`, `kernel/speaker`
  have no diff. A process that is 1000 opens, removes, signals and
  binds what root does: `mpx5-users` shows that the ids are kept, not
  that anything is kept from them.
- **The soak**: `ident soak 100000`, as root and as 1000:1000: a
  million id calls and 10,000 children that drop their ids for good;
  0 wrong answers; `/proc/meminfo`'s `MemFree` read at the start and at
  each quarter is one number; the kernel's frames line the same before
  the first program and after its end (U3, U4), on every leg.

## F. Plants (item 6)

| plant | break | red on kasumi | red in CI |
|---|---|---|---|
| A, branch `px39-plant-a` `958f650` | `setuid` and `setgid` by a user name any id (the unprivileged check removed) | `notes/px39/kasumi-plant-a.mpx5-users.out`: U1 at line 268, `(1000 1000 1000) setuid(0) = 0 -> 1000 0 1000 0 cap full`, 23 lines | run 38476629293, job 115568908234 (`mpx5-users`, the only suite chosen; `tier pr` red after it): `notes/px39/ci-38476629293-plant-a-mpx5-users.txt` |
| B, branch `px39-plant-b` `c6f4bc7` | a fork's child starts as root (the record zeroed in `process.fork`) | `notes/px39/kasumi-plant-b.mpx5-users.out`: U1 at line 2,117, the first `u1000` row, 536 lines | run 38476633056, job 115568897498: `notes/px39/ci-38476633056-plant-b-mpx5-users.txt` |

Both stop at the first boot (`stopped early`); U2, U3 and U5 of that
boot stay green, so each plant reddens the one assertion that names
its break.

## What U2 (owners) should know

- **The ids to stamp on a new inode are `cred.uid(a, cred.FS)` and
  `cred.gid(a, cred.FS)`**, not the effective ids: `setfsuid` moves one
  without the other, and `execve` makes them equal again.
- **Group membership is "the file-system group id or any of
  `cred.group(a, 0 .. ngroups)`"**; the list is sorted, so a search may
  stop early. `cred` has a private `in_list`; make it `pub` rather than
  write a second one.
- **Privilege for a file is file-system user id 0** (R9), not the
  effective id: `(0 1000 0)` after `setfsuid(0)` has root's file rights
  with effective id 1000, and `(1000 0 1000)` after `setfsuid(1000)`
  has none of them with effective id 0. Both states are in `ident`'s
  `status` rows with Linux's masks.
- `tests/mpx5-users.d/ids.pax` holds the `chown: to 1000:1000 -22`
  line and the kernel's `refused: an owner or a group that is not
  root` line (U2 in the test's `IDS_REFUSED`): when `R_OWNER` goes,
  that line becomes Linux's and `IDS_LINUX_LINES` goes from 59 to 60.
- `ident`'s `~owner` line holds `/proc/self/setgroups` to `0:0`; on
  Linux a process's `/proc` files are its effective ids' (measured:
  `1000:1000` for the user). When `/proc/<pid>` gets its owner the
  line loses its `~`.
- `user/elf/as.c` is the way to run anything as a user with no account
  (`/bin/as 1000 1000 PROG …` in `/etc/pax-run`); px38's `perm` probe
  drops by itself.
- An image still cannot carry a file that is not root's (pax#48); the
  set-ID copy in this suite's image is root's, mode 6755.
- Until U3 lands, every suite passes as a user whatever the checks do.

## 4. Evidence index

Shas are this branch's (`px39`). kasumi paths are under
`~/lanes/px39/`.

### What was written

- The prediction: `0d65e61` (§1 to §3, before any change).
- The programs: `b4d4c41` (px38's `cred.c`, `ids.c`, `px38.h` copied
  to `user/elf/`: `tests/mpx5-users` U0 holds them to
  `notes/px38/probes/` byte for byte), `53a9b7f` (`ident.c`, `as.c`),
  `950c358` (`tools/mkcred`).
- The recorders: `3e4d7ab` (`notes/px39/vminit.c`, `linux-vm.sh`,
  `build.sh`), `9932634` (`linux-ct.sh` and its three outputs).
- The kernel: `8f83276` (`kernel/cred`), `59f915c` (`kernel/process`),
  `e91e726` (`kernel/procfs`, `kernel/files`), `60f3fd3`
  (`kernel/user`), `059e677` (the function that answers AT_SECURE
  renamed `at_secure`: no behaviour moves, every kernel's bytes do, so
  kasumi's and hasu's runs were taken again at it).
- The suite: `022b77c` (`tests/mpx5-users`, the recordings, `ids.pax`),
  `ae80ea3` (the CI job, the map, `tests/ci-plan`).
- The words: `c793209` (`docs/SOURCES.md`), `d43ddea` (CHANGELOG),
  `c1fe39f` (`kernel/README.md`).

### What was measured, and where it is

- **Linux, real root**: `tests/mpx5-users.d/linux/` (seven sessions,
  their exit statuses, `vm.meta`: the kernel image's digest, QEMU's
  version, each program's digest). `cred.txt` is px38's
  `notes/px38/linux/vm.txt` lines 77 to 2,760 to the byte (U0 compares
  them at every run).
- **Linux, a container's uid 1000**: `notes/px39/linux/ct/`.
- **PAX**: `notes/px39/kasumi-mpx5-users-059e677.out` (four legs, 28
  boots; kernels `24f9bf0a…` native, `599c7229…` release),
  `kasumi-taskset-0-3-mpx5-users-059e677.out`, `hasu-kvm-059e677.log`;
  at the earlier kernel (`ad579536…`), `kasumi-mpx5-users-ae80ea3.out`
  and `hasu-kvm-211b095.log`; CI run 38474383913 at `ae80ea3` (`tier
  pr`, 30 suites on native BIOS, all green).
- **The plants**: §F.
- The pull request's own runs at its head (the pr tier, then the
  labelled full run) are named in the PR, since a commit naming them
  would move the head.

### Measured, inferred, not verified

**Measured**: everything in §A to §F.

**Inferred**: that a C library which repeats a `set*id` call in every
thread is unharmed by per-process ids (reasoned from the model, call
by call; no threaded program that drops privilege was run on PAX);
that the capability masks are a function of the ids alone (argued in
§C from what PAX lacks; every measured state agrees, and a state Linux
could reach only through `capset` or a set-ID file was not looked
for); that words 160 to 201 of the area are free (every `get` and
`put` of an area in `kernel/` was read; nothing mechanical holds it).

**Not verified**:

- Real root was measured on one kernel build (kasumi's CachyOS 7.2.8);
  the AT_SECURE and dumpable rules at `execve` are that build's
  answers. The CI runner's Linux was not asked.
- The other 29 suites did not run on kasumi or under KVM: CI only.
- UEFI under KVM (hasu): above.
- `PR_SET_DUMPABLE`, `PR_SET_KEEPCAPS`, `PR_SET_NO_NEW_PRIVS`,
  `PR_SET_SECUREBITS` are -EINVAL on PAX (not asked of Linux here; a
  program that sets one is told no).
- More than one thread changing ids at once; a `set*id` call racing an
  `execve` in another thread.
- The 32-group bound against a real program (`su` passes two).
- A set-ID file was run from the initramfs only (PAX runs no program
  written since boot).

### Issues

- **To close at merge**: pax#49 (`prctl(PR_GET_NO_NEW_PRIVS)` and
  `(PR_GET_SECUREBITS)` answer 0; `ident`'s and `ids`' `prctl` rows).
- **Not this lane's, still open**: pax#48 (U2).
- **Would file (none filed)**:
  1. pax: ids are per process, Linux's are per thread (named in
     `kernel/cred` and held by `~thread`): a note for whoever ports a
     program that relies on a thread having ids of its own.
  2. pax: `PR_SET_DUMPABLE` and the other three setters are -EINVAL.
- Two trunk flakes were not chased and did not occur: pax#45, pax#47.

## 5. Done-when

- Branch `px39` on origin; pax PR #52, open, unmerged.
- The five sections §1 to §5; the six items §A to §F.
- The test checklist:
  - [x] `tests/mpx5-users`, native and release, BIOS and UEFI, kasumi (TCG)
  - [x] the same under `taskset -c 0-3`
  - [x] the same images under KVM on hasu (BIOS)
  - [x] `tests/ci-plan` (two new cases)
  - [x] plant A red on kasumi and in CI; plant B the same
  - [x] all 30 suites on the pr leg in CI
  - [ ] all 30 suites on every leg (`tier full`) at the head: named in the PR
- `wolf/tools/lane-audit.sh pax px39 52` exit 0: named in the PR.
- Close pax#49 at merge; nothing filed.
- Trees: kasumi `~/lanes/px39/` keeps `out/` and `bin/`; build
  directories removed. hasu `~/lanes/px39/` keeps `out/`. Plant
  branches `px39-plant-a` and `px39-plant-b` stay on origin, never to
  be merged; their local worktrees are removed.

