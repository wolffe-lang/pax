# px103 — set-ID execution and `sudo` (P5 U8, the first half)

Base: pax trunk `a9f5b6f1`. The claim, here and wherever this lane writes:
**enforced for honest programs; not a boundary against an attacker**
(ruling #75 R6). The kernel has never been fuzzed or audited and loads
programs at fixed addresses. R1 stands: no passwords, hashes or prompts.

## 1. What this lane does

- The kernel honours set-user-ID and set-group-ID as `execve(2)` and
  `credentials(7)` say (`kernel/README.md`, "Set-ID execution (px103)"),
  and `PR_SET_NO_NEW_PRIVS` is real.
- `sudo`, in wolf, in `user/sudo/`, installed set-user-ID root, reading a
  subset of `sudoers(5)`; no password, no prompt; every use logged.
- `tests/mpx5-sudo`: the set-ID witness (`user/elf/sid.c`) held to a real
  Linux 7.2.4's recording, 49 lines, byte for byte; `sudo`'s rows as
  `pax`, `lobo` and root on PAX; and PAX's `sudo` run in Ubuntu 24.04's
  container through `notes/px103/sudo-ct.sh`, 300 of 360 rows the same as
  Ubuntu's own `sudo`, the other 60 differing by name.

## 2. The prediction, and what it got wrong

`notes/px103/prediction.txt` was committed before any code. The red run on
trunk showed 22 of 49 witness lines equal (the plain, root-actor and
no-effect rows); after the kernel work all 49. Mispredicted:

- Linux's `/proc/self` directory itself is owned by the effective ids even
  when the process is not dumpable (only the files under it turn root's);
  the witness prints both.
- Linux 7.2.4 under a container on the build host reports dumpable 2
  (`fs.suid_dumpable` 2 on that host), where the kernel's default and PAX's
  fixed value are 0. The recording is therefore made by booting the host's
  kernel image under QEMU with the witness as init (`notes/px103/record-sid.sh`),
  which reads 0 (printed first).
- `sudo` does not ask for a password when the target user is the caller
  (`sudo -u pax` as pax): measured, implemented.
- The sudo file check ("must be owned by uid 0 and have the setuid bit set")
  is made only when `sudo` did not become root; root running an unmarked
  copy is fine.

## 3. Commits

- `6dc27563` notes/px103/sudo-ct.sh: the black-box script for Ubuntu's sudo
- `f36dc37e` notes/px103/prediction.txt: set-ID execution and sudo, before code
- `d7931487` user/elf/sid.c: the set-ID execution witness
- `d99ff7a7` user/elf/sid.c: init mode for a real Linux's recording
- `37ef9c9c` user/elf/sid.c: the owner of a file under /proc/self too
- `c6e4be9a` tools/mkcred: build sid
- `35b35aff` notes/px103/record-sid.sh: sid on a real Linux under QEMU
- `35336c56` tests/mpx5-sudo: the set-ID witness against a real Linux's recording, red on trunk
- `d2ea42e5` tests/mpx5-sudo.d/linux/sid.txt: a real Linux 7.2.4's recording of sid
- `4a8891f1` kernel: honour set-ID bits at execve, no_new_privs, nosuid lookup
- `dfe44df9` user/sudo: sudo in wolf, and tools/mksudo
- `9fe21fc0` notes/px103: show.c and Ubuntu sudo's recorded output
- `73c251d6` user/sudo: a symbolic link in a rule matches by its own path
- `888de764` user/sudo: -ll, tags as sudo prints them, the host name trimmed
- `faac0868` user/sudo: the kernel's environment order, -E, -g alone
- `b728d5ae` user/sudo: a run-as list's commas do not split a spec
- `72d3f9d5` user/sudo: real-path rule match, env_keep replaces, -v with a command, numeric ids must exist
- `cfa35d4e` user/sudo: the file check first, a caller as itself needs no password, !loglinelen
- `c3d513af` user/sudo: a sudoers.d directory that is not root's is skipped with a warning
- `1bd46f6a` tests/mpx5-users.d/setid.pax: set-ID execution honoured, every execve row Linux's
- `0a36262f` tests/mpx5-sudo: the sudo session, red (no expectations yet)
- `07e89f27` sudo: the log is root's; sid: the sudo rows
- `11c800cc` tests/mpx5-sudo.d/sudo.pax: PAX's sudo rows
- `1d3256fc` user/sudo: sudo's own file is checked only when it did not make us root
- `68df3077` notes/px103: ctdiff with the named differences
- `bc66fd54` user/sudo: -V with a command is a usage error
- `977961d3` tests/mpx5-sudo: PAX's sudo against Ubuntu's recorded rows, the differences by name
- `7521db07` tests/mpx5-sudo: show is built with the programs
- `9a5819af` tests/mpx5-users: sig and ident's set-ID rows are honoured ones (R5 amended)
- `fb6f49a1` CI: the mpx5-sudo job, its tier-map rules; sid is built by its own suite
- `34c70e75` docs/SOURCES.md: px103's sources, the man pages' digests
- `95b13f04` kernel/README: set-ID execution (px103)
- `1856675a` user/su: the header says set-ID is honoured and su is not installed set-ID

## 4. Rows that moved from PAX's to Linux's (ruling R5 amended)

- `mpx5-users` **setid**: every `execve` row of the set-ID copies is Linux's
  now (the recording's 74 lines against PAX's 72: the two mount lines and the
  one `nosuid` row differ, nothing else); `tests/mpx5-users.d/setid.pax`
  holds the new text.
- `mpx5-users` **sig**: the set-ID target's rows (its three sender rows with
  `kill`, and its five reader rows, whose `/proc/<pid>` files follow the new
  effective user): all 102 sender rows are the recording's now
  (`SIG_LINUX_ROWS` 99 to 102); `sig.pax` holds the rest.
- `mpx5-users` **ident**, **ident-user**: the one row each that ran the
  set-ID copy. The recording was made with the copy on a `nosuid` mount
  (not honoured); the honoured text is `tests/mpx5-users.d/ident.setid` and
  `ident-user.setid`, and the suite substitutes it for that one line.
- Not run yet: a traced exec of a set-ID file (it stays unprivileged on
  Linux) and an owner's attach after a set-ID exec (refused). The kernel's
  traced-exec hook is not done: the exec path consults no tracer when it asks
  `cred.exec_ids` which ids a program gets. `tests/mpx5-sudo` prints
  `SKIP traced-exec-setid` and `SKIP attach-after-setid` by name, with the
  reason. The hook, a tracer driver in `user/elf/sid.c` and a Linux re-record
  of `sid.txt` are a follow-on. `cred.exec_ids`' `ignored` argument is where
  the first plugs in.

## 5. Rulings

- **R-px103-1** (accepted as C): the shipped policy is `root ALL=(ALL:ALL)
  ALL` and `#1000 ALL=(ALL:ALL) NOPASSWD: ALL`; the second names uid 1000,
  not a user name (README says so); `lobo` gets nothing. `user/sudo/sudoers`.
- **R-px103-2 (accepted; a named choice), a command that is a symbolic link in the policy**: the
  contract asked for a refusal by name. Linux accepts it and matches the file
  (device and inode), and its own rows (`bob-idlink`, `bob-id-bin`) rely on
  it. Recommend (implemented): a rule's path matches a command when the
  paths are equal or name the same real file (`fs_realpath`); a relative path,
  `..` or `//` in a rule is refused by name. Option B: refuse links, which
  breaks `/bin/id` against a `/usr/bin/id` rule.
- **R-px103-3 (accepted), the log's time**: PAX keeps no zone, so the stamp is UTC.
  Recommend keeping it; the format is sudo's, wrapped at 80 columns with
  `!loglinelen` honoured.
- **R-px103-4 (ruled: done in this lane, not a follow-on; done, section 9), the distribution build**: adding
  `sudo` to the images needs a build input (`tools/mksudo`), `distribution-root`
  rows (`bin/sudo` mode 04755, `etc/sudoers` 0440, `var/log`), `tests/distribution`'s
  inventory, and a check that the installer's ext2 writer and upgrade keep the
  04755 mode and write the absent `etc/sudoers`. Recommend one follow-on lane
  after the rebase, with a real-disk witness (`mpx6-install` installs, boots, and
  runs `sudo` as `pax`).
- **R-px103-5 (accepted), the Linux reference for set-ID**: a real Linux booted under
  QEMU with the build host's kernel image (7.2.4) rather than the campaign's
  usual reference machine. Recommend keeping it: reproducible by
  `notes/px103/record-sid.sh`, and the same program is init.

## 6. Named differences (sudo against Ubuntu's, `notes/px103/ctnamed.txt`)

- Linux asks for a password before it says no, or yes to a rule without
  `NOPASSWD`; PAX never prompts. Rows ending in "a password is required" or
  "a terminal is required" differ here (PAX says `no password database yet
  (R1): ...` or the final words at once).
- A syntax error: Linux reports file:line:column with a caret and goes on;
  PAX names the file and line and denies every command. Likewise a relative
  command, `Cmnd_Alias`, a command with arguments, a host other than `ALL`
  and a line over 1,024 bytes.
- `-V`'s text; `-h HOST`; the PAM-installed configuration's `umask` (PAX has no
  PAM); the argument-size bound of the long-argument rows.
- `-ll` prints Linux's long format only as far as the subset goes.

## 7. What is not done

- Typed `pelt` sessions on the accounts image of `mpx5-accounts` (the earlier
  plan): replaced by section 9's sessions at the installed console.
- The plant, the final gauntlet record, the PR and the audit: taken at the
  orchestrator's word, after one rebase onto the trunk that carries px102.
  The leg runs below are at the stick's head (named there), not the final one.
- Every log line's text has been compared to Ubuntu's for the rows in
  `sudo-ct.sh`; the over-long-argument limits are not.

## 9. The image, the install-and-upgrade witness and the typed sessions

**The image.** `tools/distribution-root` takes `INPUTS/sudo/` (`tools/mksudo`'s
`sudo` and `sums.txt`, held to the sums) and writes `bin/sudo` (mode 04755,
root:root: `put` writes `0o100000|mode` whole, so the set-ID bit stays),
`etc/sudoers` (0440, root:root, the bytes of `user/sudo/sudoers`) and the
directories `var` and `var/log`. `etc/pax-files.sha256` is generated from the
rows, so it lists both files. `tests/distribution` checks all of it by name
(`image-sudo-missing`, `-mode`, `-bytes`, `-sums`, `image-sudoers-mode`,
`-bytes`, `image-var-log`, `image-no-sudo-log`). Red first: at the tests-only
head the real `tools/mkdistribution` stopped at `image-sudo-missing`.

**The witness**, `tests/mpx6-install.d/upgrade.py`'s rows U13f, U13d and U13a:
the installed disk is booted alone, `/bin/su wolf -c '/bin/sudo /bin/id'` is
typed at the root console (uid 1000 runs sudo) and must print `uid=0(root)`;
then, on the shut-down disk, debugfs's `stat` must give `/bin/sudo` 04755 0:0,
`/etc/sudoers` 0440 0:0 with the shipped bytes, `/var/log` a root directory,
`/var/log/sudo.log` 0600 0:0 with the line for `wolf : ... COMMAND=/bin/id`.
U13f follows a fresh install from the new stick (U9), U13d the upgrade of the
8b4e98ae dev install (the 860's own history), U13a the upgrade of the
9c88ec8a install. The installer's ext2 writer and `pax-install --upgrade`
kept 04755 and 0440 in all three; the upgrade wrote the absent `etc/sudoers`,
`bin/sudo` and `var/log` with no hand edit and left `/etc/passwd`, `/etc/group`
and the user's files alone (the leg's existing user-path checks). One test
fix: `rdump` run as the host's user drops set-ID bits, so a set-ID path's
mode in `tree()` is `debugfs stat`'s (U4d failed by name on `/bin/sudo` before).

**The sessions**, row U14: `tests/mpx6-install.d/sudo-session.txt`'s lines are
typed at the installed console as root, as uid 1000 (`su wolf`, interactive)
and as lobo (`sudo -n -u lobo /bin/sudo -n ...` from the root console, since
lobo's shell is /bin/false); each line's output is appended to a capture file
and read from the disk. The same lines run on Linux in the Ubuntu 24.04
container (`sudo-linux.sh`, no network, the same accounts and the same
`/etc/sudoers` plus one Linux-only line, `Defaults logfile`), and
`sudo-compare.py` holds the two: root's and uid 1000's captures byte for byte
with no normalisation; lobo's differ by name N1 (Linux asks for a password
before it says no), and the log by N2 (time stamp and PWD masked, U13's own
line dropped, PAX's two logged refusals of lobo are PAX's alone). The session
caught a real difference at its first run: a log line showed `sh -c exit 7`
where sudo shows `sh -c 'exit 7'`; measured on Ubuntu's sudo (a blank puts
single quotes round the word, `\` and `'` are backslash-escaped, a control
byte is `#0` and its octal value), fixed in `user/sudo` (`log_word`).

**Records (hasu block A, KVM, the stick built at `04b219ac`; the later
commits touch tests and docs only).** Red: `END red-build exit=1` with
`image-sudo-missing` (tests-only head `8d402cc5`); the session's first run
(`13b6f41f`) was red by name on the log's quoting of `sh -c 'exit 7'`.
Green at `04b219ac`: `END sbuild exit=0`, `END sstick exit=0`,
`END legs-x exit=0` (U9, U13f, U14, U10, U11, U12), `END legs-d exit=0`
(U1d-U6d, U13d), `END legs-a exit=0` (U1-U4, U6, U7, U13a; U5 is not run:
the wolf pin is past 0.2.35 and the row's twin is not built here),
`END sudo-compare exit=0` (the typed session held to Ubuntu's, run by
`tests/mpx6-install.d/sudo-compare.py`); at `afab5d4a`: `END mpx5-sudo
exit=0`, `END mpx5-users exit=0` (`mpx5-accounts` exits 2 there at A0,
`tools/linux-tree`: no container engine inside the build container, not
this lane's change). Two harness flakes met and handled: a keystroke the USB
keyboard dropped under host load (`su wof`), now caught by `vcommand`, which
reads the typed line back before Enter, with keys 50 ms apart; and
`rdump` dropping set-ID bits (above). The two ptrace rows still SKIP by name.

**On the live image** `/etc/passwd` and `/etc/group` list root, `pax` (1000) and
`lobo` (990), as the base archive has them; the live login accepts root. So
`sudo` works there for root (`root ALL=(ALL:ALL) ALL`), and `su pax` (root
dropping to the user) then `sudo` matches the `#1000` rule. The installer
rewrites both files with the installing user's account (U13's `wolf`).

## 8. For the second half: passwords (R1)

What a password lane needs:

1. **The hash**: a memory-hard function in wolf-std, with test vectors from
   its specification, run on PAX's allocator and a 4-core budget; a salt from
   `getrandom`; no default password in any published image.
2. **`/etc/shadow`**, root's, 0600 (or 0640 with a `shadow` group), one line
   a user, locked by default (`!`); the installer asks for the first
   password and writes it, and an upgrade never touches it.
3. **`login`** (U9's cousin; waits on job control): a prompt, no echo
   (`termios`), three tries and a delay, a session leader.
4. **`su` and `sudo` prompting**: both read the password from the terminal
   (`/dev/tty`, no echo), `sudo -S` from standard input, `-n` refuses, and
   `sudo` stops printing "no password database yet (R1)": a rule without
   `NOPASSWD:` asks, Linux's three-try loop and its messages.
5. **A timestamp**: `/var/run/sudo/ts/USER`, root's, per terminal and
   caller, 5 minutes, `-v` refreshes it and `-k`/`-K` remove it (today
   accepted and doing nothing).
6. **Rate limiting** and the log lines for failures (`N incorrect password
   attempts`).

Draft lane `px1NN`: "passwords: the hash, shadow, login, su and sudo
prompting", needs the hash in wolf-std first (a `wolf-std` lane with vectors),
then `tests/mpx5-accounts` gaining a typed password session held to Ubuntu's
`su` and `sudo`.
