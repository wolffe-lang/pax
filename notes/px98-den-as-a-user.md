# px98 — den as an ordinary user: `fatal: denied` at the console

An ordinary user logged in at PAX's console, through the installed system's login, gets `fatal: denied` from `den
status`, in a fresh directory under `/tmp` and in their own repository, though the home directory, the repository and
every file in it are theirs and the modes are ordinary. PAX's own den rows run as root, or as a user whose standard
output is a file of their own, so nothing had exercised a user writing to the terminal.

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any other system, and no Git source. den (version control in
  wolf, pinned at `13bc2caa` in `user/den.pin`) was read read-only for its file reads and their error rows only; on
  Linux it was run as a black box under `strace`.
- **Read:** `kernel/files/files.lu` (the walk, `openat`'s class check, `may`, `changeable`, `fchmodat`,
  `fchownat`, the console's nodes), `kernel/cred/cred.lu`, `user/su/su.lu`, `user/install/prepare.lu`
  (`installed_login`), `user/usb-login.sh`, `tests/mpx5-den`, `tests/mpx5-den.d/`, `tests/mpx5-users`,
  `tests/mpx5-accounts`, `tests/mpx6-install.d/den.py`, `user/elf/as.c`.
- **References:** `open(2)`, `chown(2)`, `chmod(2)`, `proc_pid_fd(5)` (a descriptor's entry reopens the file it
  names, asked of that file's owner and mode), `login(1)` and `login.defs(5)` (`TTYGROUP`, `TTYPERM`: a login gives
  its terminal to the user, by default the user's primary group and mode 0600), `su(1)`.

## 2. Inputs, verified

- **Base:** pax trunk `44b44435`. Branch `px98`.
- **den:** `user/den.pin` at `13bc2caa46efa152ea7709da0b84180a9f350d85`. The binary the install carries,
  `/bin/den`, is sha256 `d4d3d6b85009be7dbbb7a759307261d18b3703e5c758d085a2e4d752d7858439`, read from an installed
  tree and from the copy every Linux witness ran.
- **The images run black box:** the dev install stick at `8b4e98ae`, sha256
  `665f815ab193907c007d7b431b6f833730bf1b51adbddf5ad92fb13d4d67501b` (read before each clone), booted from a clone
  of it. An 860-shaped target from the upgrade lane's leg: installed from that stick, given user state (a den
  repository with three commits), then upgraded in place to `e528bbb5`. Booted from a sparse copy.
- **The installed login's text:** an installed tree's `/etc/pax-login` is sha256
  `85a48ba8f2bc23574469f965a60400debdc9bdeea9f850eb443a5953b52be188`. That is the text the base's
  `installed_login()` gives, byte for byte (`tests/mpx5-den.d/login.py text`).
- **Hosts:** QEMU under TCG on an arm64 Mac for the first look; then x86-64 Linux hosts under KVM, each run behind
  the host's lock names and inside one slot's CPUs, in the baseline Ubuntu 24.04 container (clang, lld 18, QEMU 8.2,
  OVMF, xorriso, e2fsprogs). `strace` 7.2 and 7.3 for the black-box runs of den.

## 3. Prediction, scored

Written before the first change (2026-11-04), from black-box runs of the live medium under QEMU (§4.1):

- **P1, the call.** den's `status` writes its report by opening `/dev/stdout` by name, write, create and append
  (wolf's `fs_open_mode(path, 2)`), where every other verb writes descriptor 1. `check-ignore` does the same when it
  prints a match. On PAX, `/dev/stdout` is a link to `/proc/self/fd/1`, which reopens the console's terminal, and the
  terminal is root's, mode 0600. `openat`'s class rule answers -EACCES to any other user, den names it `denied`, and
  prints `fatal: denied` with status 128. A user's shell gets the same for `echo x > /dev/stdout` and for
  `> /dev/stderr`.
- **P2, Linux.** The same den binary on Linux, as a non-root user, opens `/dev/stdout` the same way. It gets the same
  -EACCES whenever its standard output is a terminal or a file the user may not open, as after `su` from root's
  terminal. A Linux console login does not see it, because `login` gives the terminal to the user first.
- **P3, the rows, red first.** A new image in `tests/mpx5-den` boots the installed system's login (the text
  `pax-install` writes as `/etc/pax-login`) with `su`, an account `pax` (1000:1000) and the ext2 home disk. It logs in
  as `pax` and types, on the terminal, with nothing redirected: the terminal's owner and mode; `echo > /dev/stdout` and
  `> /dev/stderr`; `den init`, `status`, `add`, `commit`, `log --no-decorate` and `status` again, in a fresh directory
  under `/tmp` and under the home directory. Then it logs in as root. At the base these rows are red by name: the
  terminal `0 0 600` where `1000 1000 600` is held, `Permission denied` for the two streams, and `fatal: denied` from
  `den status`. Every other den verb is already green.
- **P4, the kernel.** The console's terminal nodes, the console's own descriptors with `/dev/ttyS0`, `/dev/tty0` and
  `/dev/console`, each keep an owner and a mode, root's and 0600 at boot. File-system user id 0 may `chown` and
  `fchown` them, and their owner or root may `chmod` and `fchmod` them, by the rules a file of the tree has. A user's
  `chown` of one is -EPERM. `/dev/tty` and every other node of `/dev` stay fixed (-EROFS, by name). Nothing else
  moves: every suite that lists `/dev` sees the same owners and modes at boot.
- **P5, the logins.** The installed login hands the terminal to the account before `su` drops to it: the account's
  user id, its primary group, mode 0600, as `login.defs(5)`'s default. A root login hands it back to root. The live
  login (root only) hands it to root. With P4 and P5, the rows of P3 go green with den unchanged.
- **P6, the plant.** The kernel's per-terminal owner taken away (the console nodes answer root's again) turns the
  terminal row and the den row red by name, and nothing else in the suite.
- **P7, the installed disk.** On a disk `pax-install` wrote, `den init` and `den log --no-decorate` already work for
  the user at the terminal. Only `status` (and `check-ignore` with a match) fails.

**Scored** (the gauntlet's and the plant's in the PR, from the record at the head):

| | predicted | measured | |
|---|---|---|---|
| P1 | `status` opens `/dev/stdout` by name; PAX's terminal refuses it | the open in den's source and in `strace` on Linux; `> /dev/stdout` refused at the console; `status > f` and `status \| cat` fine (§4.1, §4.2) | right |
| P2 | Linux gives the same den the same open, and -EACCES on a file it may not open | the open, byte for byte; the refusal run queued (§4.2) | right on the call; the refusal in the PR |
| P3 | the rows red by name at the base, every other den verb green | L1-L5 red by name at `a41b0d8d`, D0-D4 green; `init`, `add`, `commit`, `log` status 0 (§4.4) | right |
| P4, P5 | the rows green with the kernel and the logins, den unchanged | the gauntlet (§4.6) | in the PR |
| P6 | the plant turns the terminal row and the den row red by name, nothing else in the suite | the plant record (§4.6) | in the PR |
| P7 | on an installed disk `init` and `log` work, `status` alone fails | the live medium: so (§4.1); the installed disk queued (§4.3) | right on the live medium; the disk in the PR |

## 4. Evidence index

### 4.1 The first look: the live medium, black box (`notes/px98/live-r1.txt` … `live-r5.txt`)

Five boots of a clone of the dev install stick under QEMU (TCG), its live entry. Each logged in as root, then dropped
to `pax` exactly as the installed login does: `su pax -c 'cd; exec /bin/pelt -i -m'`. The user's identity was what
the login gives (`Uid: 1000 1000 1000 1000`, `Gid` the same, `Groups: 1000`), its environment the login's
(`ENV=/etc/shrc`, `PATH=/usr/bin:/bin`, `HOME=/home/pax`).

- **r1:** `den init` in `/tmp/dentest`, then `den status`: `fatal: denied`, status 128. The same in a repository
  under the home directory. `den log --no-decorate` in the empty repository gave its own correct answer.
- **r2, the environment ruled out:** `den status` stayed `fatal: denied` with each variable of `tests/mpx5-den`'s
  pinned environment added alone, with `env -i`, and with the whole pinned environment at once. Root's `den status`
  in the same repository printed the report.
- **r3, the verbs:** as `pax`, `check-ignore` (no match), `diff`, `write-tree`, `branch`, `hash-object -w`, `add`
  answered normally; `status` alone failed. Every boreutils file operation in `.git` worked (make, rename, remove,
  link, chmod, `realpath`). `su root -c 'den status'` printed the report.
- **r4, the call:** as `pax`, `den status > out.txt`, `den status | cat` and `den status 2>&1 | cat` printed the
  report, status 0; on the terminal it failed. The shell's own `echo hello > /dev/stdout` was refused: `cannot create
  /dev/stdout: Permission denied`, and the same for `/dev/console` and `/dev/ttyS0`; `/dev/tty` (0666) took it.
  `/dev/stdout` is a link to `/proc/self/fd/1`, which names `/dev/ttyS0`, `crw------- root root`. Root's
  `chown pax /dev/ttyS0` answered `Read-only file system`.
- **r5, the sweep** (as `pax`, a repository with two commits): `init`, `add`, `commit`, `commit -a`, `log
  --no-decorate` (on the terminal and into a file), `log --oneline`, `show`, `diff`, `branch`, `checkout`, `switch`,
  `checkout -- PATH` all answered normally. boreutils' `cp` and `mv` into the home directory worked, and so did
  `wolf build` there and the program it built. Only `status` (and `status --porcelain`) failed. `poweroff` as `pax`
  was `Operation not permitted` (`reboot(2)` is root's), an EPERM and not this lane's.

So the failing call is the open of the terminal, by name, for writing.

### 4.2 den's call, and Linux's answer (`notes/px98/linux-strace.txt`)

- **den reads.** den's `status` ends with `fs_open_mode("/dev/stdout", 2)` (`src/worktree/commands.lu:77`), wolf's
  append mode, where `log`, `show`, `diff` and the rest write descriptor 1. `check-ignore` opens `/dev/stdout` the
  same way when it has output (`src/worktree/check_ignore.lu:156`), and `/dev/stdin` for `--stdin` (`:70`).
- **Linux, strace, black box.** The same binary, as a non-root user, standard output a file of its own: the only
  open of a standard stream in `status` is `openat(AT_FDCWD, "/dev/stdout",
  O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0666) = 5`. `init` and `log --no-decorate` open none. Both the plain and the
  pinned environment gave the same calls and answers.
- **Linux's refusal.** With standard output a file the user holds open for writing and has then made 0400
  (`exec 3> out; chmod 400 out; den status 1>&3`), the reopen is checked against that file's mode. That is the
  shape of a terminal another user owns. The run is queued on a Linux host with this recipe; its result goes to
  den#55 as a comment and to the PR.

### 4.3 The 860's own history (an installed ext2 disk)

An 860-shaped target from the upgrade lane's leg: installed from the `8b4e98ae` dev stick, given user state (files
under `/home/wolf` and a den repository with three commits), then upgraded in place to `e528bbb5`. That is the
installed system's own history. A sparse copy is booted alone under KVM (BIOS), and the installed login is typed on
COM1 as `wolf`:
- the terminal's owner;
- `den init`, `status` and `log --no-decorate` in a fresh `/tmp/dentest` (the ext2 root);
- `log --no-decorate`, `status` and `status | cat` in the three-commit repository;
- `echo > /dev/stdout`;
- `init` and `status` in a fresh directory under the home directory.

P7 predicts `init` and `log` answer normally and `status` alone fails. The run is queued behind the host's locks;
its transcript goes to the PR.

### 4.4 The rows, red at the base

At `a41b0d8d` (the rows committed, the fix not yet), `tests/mpx5-den --tier native --firmware bios`, one take of
the host's locks, 1108 s (`notes/px98/red-rows-a41b0d8d.txt`, the login boot's transcript
`notes/px98/red-login-a41b0d8d.txt`). D0 to D4 PASS, as at the base. The new rows red by name:

```
FAIL L1 bios:  the terminal is ['PX98-TERM 0 0 600'], not 1000 1000 600; its owner's chmod 620: ['PX98-CHMOD 0 0 600']; [native]
FAIL L2 bios:  no PX98-OUT; no PX98-STDOUT=0; no PX98-ERR; no PX98-STDERR=0; 2 lines say Permission denied ('pelt: line 6: cannot create /dev/stdout: Permission denied'); [native]
FAIL L3 bios:  tmp status1: PX98-TMP-STATUS1=128; tmp status2: PX98-TMP-STATUS2=128; home status1: PX98-HOME-STATUS1=128; home status2: PX98-HOME-STATUS2=128; 4 fatal lines ('fatal: denied'); status said On branch main 0 times, not 4; [native]
FAIL L4 bios:  the second pax login: ['PX98-AGAIN-TERM 0 0 600']; [native]
FAIL L5 bios:  2 refusals of a fixed node by chown, not 1 (root's /dev/tty); [native]
```

`den init`, `add`, both `commit`s and `log --no-decorate` were status 0 under `/tmp` and under the home directory
(the ext2 disk); only the two `status` calls in each place said `fatal: denied`.

### 4.5 The fix, green

The gauntlet (§4.6) runs `tests/mpx5-den` at the head: native under BIOS and UEFI, and release under BIOS. Its
L1 to L5 lines, and every END line, are quoted in the PR and in the lane's record. Predicted: P4 and P5.

### 4.6 The gauntlet and the plant

**The gauntlet**, at the head, recorded by the org's `gauntlet-record.sh` from a clean checkout. One take of the
host's two lock names, inside one slot's CPUs, re-taken only if a take passes 100 minutes. In order, the first
nonzero step stops it:
- `ci-plan`: `tests/ci-plan`;
- `mkinstall`: `pax-install` built with the new login text;
- `mpx5-den-native` (BIOS and UEFI) and `mpx5-den-release-bios`;
- `mpx6-nodes`: `/dev`'s nodes;
- `mpx5-accounts`: `su` and the accounts;
- `mpx3-tree`: the tree and `/dev`'s fixed answers;
- `mpx3-console`: a consumer of the live login.

`tools/ci-plan` selects 41 suites for these paths; CI's run of the PR covers the rest (`mpx5-users` among them, whose
`/dev` rows read the modes at boot, unchanged).

**The plant**, `px98-plant-kernel`: the head plus one commit, one file, one hunk. `kernel/files/files.lu`'s
`n_owner` loses its terminal branch, so the console's terminals answer root's owner again, whatever a `chown` set.
P6 predicts the terminal row (L1) and the den row (L3) red by name, from one step, `tests/mpx5-den --tier native
--firmware bios`; the record names those two. It is pushed with no PR and recorded by `gauntlet-record.sh --plant L1 L3`.

### 4.7 Rulings (recommended and implemented)

- **R-px98-1, where the fault is: both.** den asks for something it should not: it reopens a standard stream by
  name where Git writes the descriptor, and that fails on Linux too whenever the stream is a terminal or file the
  user may not open. Filed on den, with the witnesses: wolffe-lang/den#55. PAX's console login never gave the terminal to the
  user, and the kernel refused a change of a `/dev` node's owner or mode. A Linux console login gives it, so on PAX
  every console user's `> /dev/stdout` and `> /dev/stderr` failed, den or not. Options were to fix den only, PAX only,
  or both. Recommended and implemented: both, PAX's part here.
- **R-px98-2, the PAX fix.** Options:
  - (A) the kernel keeps an owner and a mode for the console's terminals, settable by root's `chown` and the owner's
    or root's `chmod`, and the logins hand the terminal over, as `login(1)` does;
  - (B) the same, with the hand-over in `su`, which would then differ from Linux's `su`;
  - (C) nothing in PAX, waiting for den.
  Recommended and implemented: A.
- **R-px98-3, an upgrade and the login's text.** The upgrade lane's `text_step` keeps a target's
  `/etc/pax-login` whenever it differs from the new image's text, and writes the new text beside it as
  `/etc/pax-login.pax-new`. That includes an installed login no one edited, whose text is only the previous
  installer's. So an upgraded install keeps the old login until it is replaced. Options:
  - (a) the upgrade regenerates a generated file that equals a known earlier installer's text;
  - (b) one line as root after the upgrade: `mv /etc/pax-login.pax-new /etc/pax-login`.
  Recommended: (a), for the upgrade lane, with (b) until then. Ruled (a) into that lane; nothing here changes
  the upgrade.

### 4.8 What an installed system needs

The kernel arrives with an upgrade (`/boot/pax` is replaced). The login's new lines arrive with `/etc/pax-login`:
by R-px98-3 (a) once the upgrade regenerates it, or by `mv /etc/pax-login.pax-new /etc/pax-login` as root after the
upgrade until then. With the new kernel and the old login, den's `status` still fails at the console: the terminal
stays root's until a login gives it away. Until both are there, `den status | cat` (or `den status > FILE`) prints
the report on any kernel.

## 5. Done-when

### 5.1 Checklist

- [x] Reproduced red first, by name: a non-root user logged in through the installed login runs `den init`,
  `status` and `log --no-decorate` in a fresh directory under `/tmp` and under the home directory
  (`tests/mpx5-den` L3, red at `a41b0d8d`).
- [x] The call and the path: `openat(AT_FDCWD, "/dev/stdout", O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0666)`, reopening
  the console's terminal through `/proc/self/fd/1`; refused by `openat`'s class check, the terminal root's 0600.
- [x] Fixed where it is wrong (R-px98-1, both): the kernel keeps the terminals' owners and modes, and the logins
  hand the terminal over (PAX); den#55 filed for den's reopen.
- [x] The sweep (§4.1 r5): no further EACCES by name. Of what was swept, only `poweroff` as a user is refused, an
  EPERM (`reboot(2)` is root's).
- [ ] The gauntlet green at the head, every END line in the PR.
- [ ] The plant `px98-plant-kernel` red by name (L1, L3) in its own record.
- [ ] The audit, once: `--local GREEN --plant-record RED pax px98 <PR>`.

### 5.2 Departures and limits

- **The rows are held to `login(1)`'s documented behaviour, not to a Linux side.** No container here reproduces a
  Linux console login's terminal ownership; den's own output in L3 is not compared byte for byte (its dates move),
  only its status, its lack of a `fatal:` line and the lines a report must hold.
- **What the change does not do:** `/dev/tty` and every other `/dev` node stay fixed, a terminal's times stay fixed,
  and a terminal's change moves no ctime. The ownership is not given back at logout: the next login takes it.
  Linux's `su` gives no terminal away, so a `su` from root's shell still leaves the user without it, as on Linux.
- **den's own fault stays den's** (den#55): with a standard output it may write but not open, den's `status` still
  says `fatal: denied`, on PAX as on Linux.
- **An upgraded install keeps its old login** until the upgrade regenerates `/etc/pax-login` (R-px98-3), or by
  `mv /etc/pax-login.pax-new /etc/pax-login` as root (§4.8).

### 5.3 Issues

- Filed: wolffe-lang/den#55 (den's `status` and `check-ignore` reopen `/dev/stdout` by name).
- For the upgrade lane: R-px98-3 (a), regenerating a generated file that holds an earlier installer's text.
- Nothing closed.
