# px46 — The accounts (P5 lane U6: `pax` and `lobo`, a `su` in wolf, the pins)

Contract: px46's, `sprints/pax/46-the-accounts/px46-the-accounts.md` in
wolffe-lang/wolf (planning commit `bacf23f`, read 2026-10-15), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/crawl-54.md` and `sprints/wave-53.md` down to
`wave-45.md`. Branch `px46` in pax, cut from pax trunk `b7fb8d1`. §1 to
§3 are committed before the first change to a pin, the kernel, a tool,
a program or a test, and before the first measurement.

One deliverable: **an image with the accounts `pax` (1000) and `lobo`
(990) and a working `su`**, written in wolf under pax `user/` (R8) and
built with wolf 0.2.30, whose `os_set_ids` is whole or the process
aborts. On the ruled terms: **no passwords** (R1), **the image still
boots to a root shell** (R2), **set-ID not honoured** (R5), so `su` is
root dropping to a user, and a user's `su` to anyone is refused as
Linux refuses a user who cannot authenticate. With it: **pax's pins
move** to pelt `7dd3304` and boreutils `23ea8dd`, each its own commit,
and **the typed session** of the campaign's goal (`su`, `id`, own
files, refusals, `kill 1` refused) byte-identical to the same binaries
run on Linux. The ruled claim stays R6's: the checks are **enforced for
honest programs; not a boundary against an attacker**.

## 1. Forbidden, absolutely

- No source of `su`, `login`, shadow-utils, util-linux, PAM, coreutils,
  any shell, any libc or any kernel is read. Linux's `su` is known from
  `su(1)`, `login.defs(5)`, `passwd(5)`, `group(5)`, `credentials(7)`,
  POSIX.1-2024, px38's traced runs (`notes/px38/straces/`), and what
  this lane measures black-box: Ubuntu 24.04's own `su` (util-linux
  2.39.3) run as the container's root in a throwaway container with
  accounts made in that container, whose rows are about what a user
  sees, and real root (kasumi's own kernel image under QEMU, the program
  a child of pid 1, px38's and px45's way) for the session's root rows.
  Every Linux row names the reference it came from.
- **No password, hash or default credential anywhere** (R1): not in the
  image, not in a test, not in a recording. The accounts' password field
  is `x` with no `/etc/shadow` behind it; `su` asks no one for a
  password. The image boots to root's shell (R2); `su` gains nothing
  (R5): a set-ID bit is not honoured, so it is never set on `su`.
- No account is made on any host, no `sudo`. Accounts exist in PAX's
  image and inside throwaway containers and guests only. Signals and id
  changes go only to processes the test started, inside PAX, a
  container or a guest.
- Nothing calls PAX secure; no word implying filming.
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never against
  kasumi's own glibc. Toolchains from release archives by digest, each
  read twice.
- No build on nomad-1. kasumi and hasu: commands under `bash`, long jobs
  under `setsid` with a pid file, killed by that pid only (never by
  name, pattern or group); work under `~/lanes/px46/`, pruned as I go;
  never `/tmp`. Host ports 8080 and 8088 are not used. Nothing is
  installed anywhere. hasu's llama-server (port 9308) is not touched.
- No `rm` outside `~/lanes/px46/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled. "Seen red" cites a run. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-15)

| input | found |
|---|---|
| pax trunk | `b7fb8d1` (px45 merged), the contract's; `origin/trunk` the same at the start |
| planning repo | `bacf23f`: the contract, the campaign file (R1 to R9), crawl 54 |
| wolf 0.2.30 | tag `v0.2.30` → `1b37f368`; release 413582739; `wolf-0.2.30-x86_64-unknown-linux-gnu.tar.gz` sha256 `4e55b39e…29fe89`, read from the release API's digest and again by `sha256sum` of the download on kasumi (`~/lanes/px46/cache/`) |
| lupin 0.1.53 | tag `v0.1.53` → `7896eddc`; release 413375414; linux x86-64 archive `5db55332…edccaa`, read the same two ways. Nothing here runs lupin: `su` is built by wolf's release tier, as pelt and boreutils are |
| kernel's pin | wolf 0.2.28 / lupin 0.1.51 (`kernel/wolf.pin`), unchanged by this lane: `su` carries its own toolchain file, as pelt and boreutils do |
| pelt | pin `b32bebc` (sh05, wolf 0.2.27) → `7dd3304` (sh15, trunk): wolf 0.2.30 by the same digest, wolf-std `fd6bcdc`. 243 commits between: sh06–sh08 (census, scripts, memory), sh11 (a line editor that owns the terminal: raw mode, its own echo), sh12 (history: `$HOME/.sh_history`, read once, appended before each prompt), sh13 (`umask`), sh14 (`kill`, `trap` for every signal), sh15 (`os_term_size`, `os_term_chars`, `os_signal_wait_fd` at the prompt) |
| boreutils | pin `2ab3651` (bu22, 39 utilities, wolf 0.2.28) → `23ea8dd` (bu24, trunk): wolf 0.2.30, wolf-std `fd6bcdc`; bu23's `kill` and bu24's `id`, `whoami`, `groups`, `logname`, `chown`, `chgrp` (46). `git diff 2ab3651 23ea8dd -- src` adds files only (15 files, +2,757, no line removed): no existing utility's source moved, only its toolchain |
| wolf-std | trunk `a0d0c87` (sc62): `std.os.users` (passwd and group lines parsed from text the caller read; `user_named`, `groups_of`), `std.process.set_ids`. pelt's and boreutils' `fd6bcdc` is the std r35 released with 0.2.30 |
| the calls `su` needs | `os_set_ids(uid, gid, groups)` (`[os.proc.ids.set]`: `setgroups`, `setresgid`, `setresuid`, read back with `getresuid`, `getresgid`, `getgroups`, then the way back tried and refused); `os_exec` (`[os.proc.exec]`: argv[0] is the caller's, the environment is data); `os_euid`; `os_chdir`; `fs_read_text`. PAX answers every system call they make since px39 (the twelve id calls) and px14/px26 (`execve`, `chdir`) |
| what PAX lacks for `login` | `setsid`, `setpgid`, `TIOCSCTTY`, `TIOCSPGRP` (-ENOSYS or refused: the job-control track, ruling #79), a terminal that takes an owner (`/dev` is -EROFS for `fchown`/`fchmod`, px42's `~fixed`), a password (R1) |
| px38's traced `su` | `notes/px38/straces/23` to `28`: root's `su alice -c id` makes `setgroups(2, [1000, 2000])`, `setgid`, `setuid`, `setsid` (with `-c`), then `execve` of the shell; `su - alice` sets `HOME`, `USER`, `LOGNAME`, `SHELL`, and a `PATH` from Ubuntu's configuration, and works in the home directory; `su nosuch`: `su: user nosuch does not exist or the user entry does not contain all the required fields`, 1; a user's `su root` or `su bob` with a wrong or no password: `Password: ` then `su: Authentication failure`, 1 |
| the accounts in tests today | `tests/mpx5-users` stages `root:x:0:0:root:/:/bin/pelt`, `pax:x:1000:1000:pax:/home/pax:/bin/pelt`, `lobo:x:990:990:lobo:/srv/lobo:/bin/false` (R3); pxdemo's image the same, with `as` the way to become a user |
| suites that stage pelt or boreutils | pelt: `mpx3-console`, `mpx3-screen`, `mpx3-shell`, `mpx3-speaker`, `mpx3-tree`, `mpx4-session`, `mpx4-lobo`; boreutils: `mpx3-boreutils`, `mpx3-shell`, `mpx3-tree`, `mpx4-session`, `mpx4-lobo`, `mpx5-users` (`ls`) |
| CI | tiered (px37, px40): a pin's change runs the suites that name its tool on the PR leg; the `full-matrix` label runs every suite on every leg |
| pax#62 | open (the racy reference row in `mpx3-threads`): one re-run of that job, said so |
| the exploration image | `kasumi:~/lanes/pxdemo/`: `inner.sh` in `px13-ubuntu` (mkpelt, mkboreutils of every utility, mkcred, mkzone, mkinitramfs with owners, `kmain_console`, `boot/limine-initramfs-quiet.conf`), `run.sh` (`qemu-halt --type`, `-m 1G`); on this Mac `~/scratch/wolf/pax-trunk/pax-trunk.iso` (`44340d73…`), which is not touched |
| kasumi | `/home` 40 GB free; `px13-ubuntu` `ad896450…`; Linux 7.2.8-1-cachyos (px45's reference kernel) |

## 3. Prediction (committed before the first change and measurement)

**P1. The pins.** pelt `7dd3304` and boreutils `23ea8dd` build with
`tools/mkpelt` and `tools/mkboreutils` unchanged (both trees name wolf
0.2.30 by `4e55b39e…`), static, and **run on PAX with no kernel
change**: the editor's calls (TCGETS/TCSETS, TIOCGWINSZ answered 0 by
0 so it falls back to 80 columns, `poll` of descriptor 0 and a wake
pipe, a thread for the signal hub) are all answered since px13, px24
and px26. Every suite that stages them stays green. Expected text moves
in one place only: pelt now keeps a history file at `$HOME/.sh_history`
in every interactive session (sh12), and PAX's `HOME` is `/`, so after
a typed session the tree holds `/.sh_history` on both sides:
`mpx3-tree`'s T6 (the names left on Linux) and T4 (the frames and
inodes the tree holds after) gain that one file. boreutils' 39 old
utilities print the same bytes. **Falsified by** a kernel change, a
suite red for another reason, or a test edit outside `mpx3-tree`'s T4
and T6 (and the new suite).

**P2. Linux's `su`, measured** (Ubuntu 24.04's util-linux 2.39.3 `su`,
as the container's root with accounts made there; and again with its
configuration taken away: no `ENV_PATH`/`ENV_SUPATH` in
`/etc/login.defs`, an empty `/etc/environment`). I expect:

- `su pax` by root: no prompt; the shell runs as uid 1000, gid 1000,
  groups the primary group and every group naming `pax`
  (`setgroups(2, [1000, 2000])` in px38's trace); the environment kept
  but `HOME`, `SHELL`, `USER`, `LOGNAME` set to the target's; `PATH`
  untouched; the working directory untouched; argv[0] the shell's base
  name; the umask untouched when no `pam_umask` runs.
- `su - pax` (and `-l`, `--login`): the environment cleared but `TERM`;
  `HOME`, `SHELL`, `USER`, `LOGNAME`, `PATH` set; `PATH` from
  `ENV_PATH`, else `/usr/local/bin:/bin:/usr/bin` for a user and
  `/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin` for
  root (`su(1)`'s defaults); the working directory the home; argv[0]
  `-` and the shell's base name.
- `-c CMD`: the shell is given `-c CMD`; `-s SHELL`: that shell; `-m`
  or `-p`: the whole environment kept, nothing set.
- `su` with no name: root.
- A user's `su` to anyone (root, another user, itself), with or without
  `-c`: `Password: ` on the terminal, then `su: Authentication failure`
  and status 1; without a terminal the same message and status.
- No such user: `su: user nosuch does not exist or the user entry does
  not contain all the required fields`, status 1. An unknown option:
  `su: invalid option -- 'x'` and `Try 'su --help' for more
  information.`, status 1. A shell that is not there: `su: failed to
  execute /nope: No such file or directory`, status 127.

**PAX's `su`** follows those rows, with differences each named in the
note: no `Password: ` prompt (there is no password to ask for, R1: the
refusal is the message and the status alone, at once, with no delay);
no `setsid` (PAX has one session); the shell replaces `su` (no PAM
session to close, so no parent waits); no `/etc/login.defs` read (the
two defaults are compiled in, as `su(1)` gives them). **Falsified** row
by row by the measurement.

**P3. The typed session**, byte-identical on three sides: PAX (serial,
and the PS/2 keyboard, both tiers), the same binaries in a throwaway
container (`tools/linux-tree`, live, CI's reference), and the same
binaries under real root (kasumi's kernel under QEMU, recorded and
committed), with only the dates of files made in the session masked.
It runs: root's `id`; `su pax`; `id`, `whoami`, `groups`; a file made,
listed and `chmod`ed in `/home/pax`; root's 0600 file refused; `rm` of
a `/bin` program refused; `chmod` of root's file refused; `kill 1`
refused; `kill -l`; a file left in `/tmp` and root's file there left
alone; `su` back to root refused; `exit`; `su - pax -c id` with its
environment; `exit` back to root's `id`.

**P4. No kernel change.** `su` needs nothing PAX lacks (§2).
**Falsified** by a change under `kernel/`.

**P5. `login` is not built**: without passwords it would be a gate
that opens for everyone (R2's reasoning), and what it does beyond `su`
— a session, a controlling terminal handed over and owned — needs
`setsid`, `TIOCSCTTY`, `TIOCSPGRP` and a terminal that takes an owner,
which are the job-control track's (U9).

**P6. Plants**, each red in a CI run of its own with the new suite
alone: A, `su` keeps root's groups (`[0]` instead of the target's):
red first at the session's first `id` after `su pax` against the
recording (and NOT against the live container, which runs the same
planted binary: which is why the recording is committed); B, `su`
does not refuse a user: red first at the user's `su` line, where the
kernel's refusal of `setgroups` comes back as `os_set_ids`' `denied`.

**P7. Cost.** `su` is one static wolf program under 15 MB (boreutils'
are about 13 MB each); the session's image fits `-m 512M`; the
exploration image with every utility needs `-m 1G` as pxdemo's did.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | the pins build with the tools unchanged and run with no kernel change; expected text moves only in `mpx3-tree`'s T4 and T6 (the history file) | built unchanged (`d759070`); **a kernel change was needed** (§B: pelt's editor polls, then reads with VMIN 0 and VTIME 1; PAX's console said readable and answered 0, so pelt ended at its first prompt, seven suites red, run 38783928625); and expected text moved in four more ways (§C: the cursor query in Linux's transcripts, lobo's first-prompt pattern, one redrawn prompt in session-shell.expect, `exit`'s status); T4 and T6 as predicted | wrong |
| P2 | Linux's `su`: the environment, `-`, `-c`, `-s`, `-m`, the refusals and their words | right on HOME/SHELL/USER/LOGNAME, `-c`, `-s`, the refusal words and statuses, 127 for a missing shell; **wrong on `su -`'s default `PATH`** (`/usr/local/bin:/usr/bin`, no `/bin`), on `-m` (it runs `$SHELL`), and silent on the `-m`-with-`-` warning, words after the user, a second `-c`, an empty shell field, the missing home's warning (§A) | wrong (1), incomplete |
| P3 | the session byte-identical on PAX (serial, PS/2, both tiers), in the container and under real root | 109 lines identical on all three, four legs and both keyboards (§D); the same under `taskset -c 0-3`; KVM on hasu, BIOS, two rounds | right |
| P4 | no kernel change | the console's VMIN 0 (§B), for the pins, not for `su`: `su` needed nothing of the kernel | wrong (for the pins) |
| P5 | `login` not built, U9's | so (§E) | right |
| P6 | plant A red at A2 and not A1; plant B red at the user's `su` | B as predicted (A2, not A1); **A was green** on kasumi until the session read its `Groups:` line (§F), then as predicted | wrong (A, first form) |
| P7 | `su` under 15 MB; the session's image in 512 MB; the exploration image needs 1 GiB | `su` 13,952,552 bytes; the session at `-m 512M` on every leg; the exploration image's archive 671,586,308 bytes, booted at `-m 1G` | right |

## A. `su` (item 2)

`user/su/su.lu` (wolf, 0.2.30, `std.os.users` at wolf-std `a0d0c87`),
built by `tools/mksu` static in the Ubuntu container, 13,952,552 bytes.
Root's `su` reads `/etc/passwd` and `/etc/group` itself (no name
service), makes the groups `std.os.users.groups_of` gives (the user's own
first, then each group naming it) and drops with one `os_set_ids` —
groups, then group ids, then user ids, read back, the way back tried and
refused, or the process ends — then `os_exec`s the shell. Anyone else is
refused before any id is touched.

**Rows against Linux.** `notes/px46/su-ct.sh` runs 39 rows of Ubuntu
24.04's own `su` (util-linux 2.39.3, set-user-ID root) as a throwaway
container's root, with `pax` (1000, also in a group `pack` 2000), `lobo`
(990, shell `/bin/false`), `bob` (no home) and `nosh` (empty shell field)
made in that container, and a probe shell (`notes/px46/show.c`) that
prints its argv, working directory, the six ids, groups, umask, session,
open descriptors and environment. Three configurations: Ubuntu as
installed; `ENV_PATH`/`ENV_SUPATH` and `/etc/environment` taken away;
and the PAM lines naming `pam_env`, `pam_mail` and `pam_umask` taken out
as well, with `ENV_PATH PATH=/bin` and `ENV_SUPATH /bin` given (what
`su` itself does, with nothing else adding to it). Linux's output:
`notes/px46/linux/su-ct.txt`; the same rows with PAX's `su` put in
place of `/usr/bin/su` (mode 0755, not set-ID): `notes/px46/su-ct-pax.txt`.

In the third configuration every row is Linux's to the byte but these,
each by name:

| row | Linux's `su` | PAX's `su` | why |
|---|---|---|---|
| a user's `su` to anyone (root, lobo, itself, `-`, `-c`), five rows and two on a terminal | `Password: ` (on standard error, or the terminal), about 3.5 s, then `su: Authentication failure`, status 1 | `su: Authentication failure`, status 1, at once | R1: there is no password to ask for; asking would pretend there were. The message and the status are Linux's |
| `-c` (five rows) | the shell is a session leader (`setsid`) | not | PAX has one session (job control is ruling #79's track) |
| a shell killed by SIGTERM | `su`, still the shell's parent, says `Terminated`, status 143 | the caller's shell says it (bash, here), status 143 | PAX's `su` replaces itself with the shell (no PAM session to close) |

In the first two configurations the rows differ also by what PAM adds
(`MAIL`, `LANG`, `/etc/environment`'s `PATH`, umask 0002 from
`pam_umask`): PAX has no PAM. Measured, and corrected against §3 P2:

- `su - USER`'s `PATH` with nothing configuring it is
  **`/usr/local/bin:/usr/bin`** for a user and
  **`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`** for root (P2
  said `…:/bin:…`, from an older `su(1)`): neither names `/bin`, PAX's
  only program directory, so PAX's image carries `/etc/login.defs` with
  `ENV_PATH PATH=/bin` and `ENV_SUPATH PATH=/bin`, and its `su` reads
  them as Linux's does (both spellings, `PATH=…` and bare, measured).
- `-m`/`-p` run `$SHELL` when it is set (P2 did not say), and with `-`
  are ignored with `su: ignoring --preserve-environment, it's mutually
  exclusive with --login`.
- `su - USER` when the home is missing: `su: warning: cannot change
  directory to /home/bob: No such file or directory`, and the shell runs
  where `su` was.
- Words after the user go to the shell (`su pax -c CMD one two`,
  `su pax -`); a second `-c` replaces the first; an empty shell field is
  `/bin/sh`.
- Refusals in order: the option (`invalid option -- 'x'`,
  `unrecognized option '--bogus'`, `option requires an argument --
  'c'`, each then `Try 'su --help' for more information.`), then the
  user (`su: user nosuch does not exist or the user entry does not
  contain all the required fields`), then the caller. A missing shell:
  `su: failed to execute /nope: No such file or directory`, 127 (P2's
  guess was right).

Not built, refused by name (`su: -g: not built in PAX's su`): `-f`,
`-g`, `-G`, `-P`, `-w`, `-V` and their long forms, `--pty`,
`--session-command`, `--whitelist-environment`. Not read:
`ALWAYS_SET_PATH` and the rest of `login.defs`.

## B. What the pins needed of the kernel: the console's VMIN 0 (item 1)

The pins' first CI run (38783928625, at `d759070`, the pins alone)
was red in seven suites (`mpx3-console`, `mpx3-screen`, `mpx3-shell`,
`mpx3-speaker`, `mpx3-tree`, `mpx4-session`, `mpx4-lobo`), each the same
way: pelt drew its first prompt and ended with status 0 before a key
was typed (`console: 0 bytes from com1 … 18887 reads, 0 waited`). sh11's
editor reads the terminal with VMIN 0 and VTIME 1 after a `poll` of
descriptor 0 (wolf's `os_signal_wait_fd`): PAX's console said
"readable" whenever VMIN was 0, and answered such a read 0 at once, so
pelt saw a terminal that had hung up.

Measured with a probe of this lane (`notes/px46/vtime.c`) on a Linux
pseudo-terminal (`tools/linux-tty` in the container,
`notes/px46/linux/vtime-pty.txt`) and on PAX's console as the first
program: Linux's `poll` waits for a byte whatever VMIN is; a read with
VMIN 0 and VTIME 0 answers 0 at once; with VMIN 0 and VTIME 2 it waits
about 0.2 s and answers 0; a key typed during a VTIME 100 read ends it
with the key. PAX at trunk differed in five of the seven lines
(`notes/px46/pax-b7fb8d1-vtime.txt`). `kernel/console` now answers
`readable` only for data or a pending end of file, and a VMIN 0 /
VTIME > 0 read with nothing ready waits as a pipe's reader does (the
deadline in the thread's own word, as `poll`'s is) until a key or VTIME
tenths of a second; `kernel/files` keeps the word. All seven lines are
Linux's after it (`notes/px46/pax-fix-vtime.txt`). VTIME with VMIN above
0 (the timer between bytes) stays stored and not acted on, named.

## C. The pins, and what moved in the suites (items 1 and 4)

- `user/pelt.pin` → `7dd3304`, `user/boreutils.pin` → `23ea8dd`, each
  its own commit. Both build unchanged with `tools/mkpelt` and
  `tools/mkboreutils` (wolf 0.2.30 by `4e55b39e…`).
- Expected text that moved because the newer pelt answers differently,
  each the same on PAX and on Linux:
  1. **pelt's cursor query.** Before its first prompt the editor writes
     `ESC [ 6 n` (where is the cursor?) and waits 300 ms for a reply
     that neither a pseudo-terminal nor PAX's console gives. PAX's side
     was always read through `serial_norm` (escape sequences removed);
     the Linux sides were read with `tr -d '\r'` only. `mpx3-console`,
     `mpx3-shell`, `mpx3-tree` and `mpx4-session` now normalise Linux's
     transcript the same way. lobo's step files wait for the first
     prompt as `^(\x1b\[6n)?\$ $`.
  2. **The history file.** pelt keeps `$HOME/.sh_history` (sh12) and
     root's `HOME` is `/`: after a typed session the tree holds
     `/.sh_history` on both sides. `mpx3-tree`'s T6 counts it among the
     names left, T4 one more inode and its page (as P1 predicted).
  3. **A prompt redrawn.** In `mpx4-session`'s session-shell, after the
     trap's line and the empty Enter typed 1.5 s later, pelt draws a
     fresh prompt (`$ ` then the next): `user/console/session-shell.expect`
     gains that one line.
  4. **`exit` with no number** ends pelt with the last command's status
     (POSIX's rule): `mpx3-tree`'s shell-tree now ends 1 (its last
     command, `rm -rf /`, is refused) and shell-changes 2, on both sides;
     the suite takes the status from Linux, so nothing was edited for it.
  5. **Ctrl-C at the prompt is the editor's.** pelt's editor edits with
     the terminal's signals off (sh11) and reads Ctrl-C as a key: it
     runs a trap at once and draws a new prompt; Ctrl-\ at a prompt does
     nothing. `mpx4-session`'s E4 now counts one signal raised from the
     terminal, not two, and its E5 takes session-shell's status from
     Linux (130: the `exit` after the Ctrl-C). `mpx3-shell`'s
     `shell-sigs.keys` waited for prompts the old pelt drew and typed
     the rest at the running shell; with the editor's extra prompts it
     ran ahead (on PS/2: `ech$ echo $?`), so each step now waits for the
     prompt it is typed at, and `shell-sigs.expect` is the new pelt's
     Linux transcript.
  6. **The history page** also in `mpx3-shell`'s S1 (frames back after
     init's end, less the history file's one page).
- **A harness finding: Linux's side started pelt with SIGPIPE ignored.**
  `tools/linux-tty` is Python, which ignores SIGPIPE and SIGXFSZ, and an
  ignored signal stays ignored across `execve`; since sh14 pelt keeps
  what it was given, so on Linux `cat /bin/pelt | true` printed `cat:
  write error: Broken pipe` where PAX's `cat` (every signal at its
  default in PAX's first program) died of SIGPIPE (run 38795460271,
  `mpx3-shell` S2; measured with `notes/px46/sigstate.c`: Linux
  `SIGPIPE: ignored`, PAX `default`, and pelt's `SigIgn` 0x1001000 under
  linux-tty against 0 on PAX). `linux-tty` now gives the program both
  signals at their defaults, as PAX does.
- boreutils: no expected text moved (bu23 and bu24 only add utilities).
- **Not predicted:** the kernel change of §B. P1 said no kernel change
  was needed; the console's VMIN 0 rule was wrong for any program that
  polls before a timed read, and pelt is the first such program PAX ran.

## D. The typed session (item 3)

`user/console/accounts.keys`, run by `tests/mpx5-accounts` as root's
pelt (pid 1) on an image with `/etc/passwd` and `/etc/group` (root, pax
1000, lobo 990: R3), `/etc/login.defs` (§A), `/home/pax` 0755 pax's,
`/srv/lobo` 0750 lobo's, `/etc/secret` 0600 root's, `/tmp` 1777 with
root's 0600 `rootfile`, `/bin` holding pelt, su and ten of boreutils'
utilities. 109 lines (after `serial_norm`; two dates of files made in
the session masked), the same bytes on:

- PAX: COM1 and the PS/2 keyboard, native and release, BIOS and UEFI;
- Linux in a throwaway container (`tools/linux-tree --owners`, pelt as
  pid 1 of a fresh pid namespace in a tmpfs holding the image's tree
  with its owners and modes): the CI reference, run live;
- real root: kasumi's kernel (7.2.8-1-cachyos, `f4c00d5d…`) under QEMU
  with the suite's own archive as its root and `notes/px46/vmtty.c` as
  pid 1 typing the keys on a pseudo-terminal, the four protected
  settings on (`tests/mpx5-accounts.d/linux/accounts.tty`,
  `vm-accounts.meta`).

What it shows: root's `id`; `su pax`; `id` `uid=1000(pax) gid=1000(pax)
groups=1000(pax)`, `whoami`, `groups`, `HOME USER LOGNAME SHELL` as `su`
set them, and the `Groups:` line of `/proc/self/status` (`Groups:
1000`: `id` alone prints `groups=1000(pax)` for no supplementary group
as for `[1000]`, so it cannot catch plant A; found when plant A was
first green, §F); `cd` to the home, a file made, `chmod 600`, listed beside the
archive's; refused: root's 0600 file (`Permission denied`, 1), lobo's
0750 directory, `rm /bin/ls`, `chmod 777 /etc/motd` (`Operation not
permitted`), `kill 1` (`pelt: line 16: kill: 1: not permitted`, 1), the
user's `rm` of root's file in the sticky `/tmp`; allowed: a file of the
user's own in `/tmp`; `kill -l`; `su` and `su -s /bin/pelt lobo -c id`
as the user: `su: Authentication failure`, 1; `exit` back to root's
`id`; `su - pax -c 'id; pwd; env'` (the home, and the environment of a
login: `HOME LOGNAME PATH=/bin PWD SHELL TERM USER`); `su lobo` (its
shell `/bin/false`, 1); lobo's `id`, `whoami` and its own directory
through `-s /bin/pelt`; `su nosuch`; root removes what the session made.

## E. `login` (item 2)

Not built: it is U9's. Without passwords (R1) a `login` asks nothing
and opens for anyone, which is a gate that looks like a lock (R2's
reasoning: the image boots to root's shell instead). What `login` does
beyond `su` — measured in px38's trace: `setsid`, `TIOCSCTTY`,
`fchown`/`fchmod` of the terminal, `setpgid`, `TIOCSPGRP` — needs a
session, a controlling terminal handed over and a `/dev` node that
takes an owner (px42's `~fixed`: -EROFS), all the job-control track's
(ruling #79). A `login` without them would be `su -` under another name.

## F. Plants (item 5)

Each a branch never to be merged, cut from `bc8df17`, one commit:

| plant | branch | break | expected red |
|---|---|---|---|
| A | `px46-plant-a` | `su` drops with the groups it has (root's `[0]`) instead of the target's | A2 (the recording) at the first `id` after `su pax`; A1 (the container) NOT red, since it runs the same planted `su` |
| B | `px46-plant-b` | `su` does not refuse a user | A2 at the user's first `su`: the kernel refuses `setgroups` to a user and `su` says so, where real root's recording says `su: Authentication failure`; A1 again NOT red (the same planted `su` in the container) |

**Plant A was green at first, on kasumi.** At `bc8df17` the session
asked only `id`, which prints the effective group and then the list,
so a `su` that dropped with root's list — on PAX and in a rootless
podman container, where the first process has no supplementary group
— printed `groups=1000(pax)` exactly as a correct one: kasumi's run
of the plant passed every assertion (`notes/px46/kasumi-plant-a-first-green.out`).
In CI the same plant WAS red (run 38788946188, cancelled once
superseded, job 116613289454: A0 and A1), because Docker's root on the
runner carries the supplementary group 0, so the container printed
`groups=1000(pax),0(root)`: the plant's colour depended on the
reference host. The session now prints the `Groups:` line of
`/proc/self/status` after `groups` (`59eaf2e`, the recording again in
`d099f73`), which reads `Groups: 1000` from a correct `su` and `Groups:`
from one that kept PAX's root's empty list: red on every host.

| plant | head | on kasumi (native BIOS) | in CI (`mpx5-accounts` alone, pr leg) |
|---|---|---|---|
| A | `1399d1f` | A0 linux and A2 red at `Groups: 1000` / `Groups:`, A1 green (`notes/px46/kasumi-plant-a.out`) | run 38795489284, job 116640189792: A0 linux, A1 and A2 red (on the runner Docker's root has group 0, so the container also shows `groups=1000(pax),0(root)`), `notes/px46/ci-38795489284-plant.txt` |
| B | `6ffc0df` | A0 linux and A2 red at the user's two `su` lines (`su: cannot set user and group ids: Operation not permitted` where real root says `su: Authentication failure`), A1 green (`notes/px46/kasumi-plant-b.out`) | run 38795495464, job 116638509417: A0 linux and A2 red, A1 green, `notes/px46/ci-38795495464-plant.txt` |


## G. The exploration image

For the maintainer, pxdemo's recipe at this branch's code head `22bb7fc`
(`notes/px46/image/inner.sh`, run in `px13-ubuntu` on kasumi): pelt
`7dd3304`, all 46 boreutils at `23ea8dd`, `su`, `as`, the accounts and
files of pxdemo plus `/etc/login.defs`; `kmain_console`, the quiet
configuration, `-m 1G`. `pax-trunk-u6.iso`, 678,207,488 bytes, sha256
`f3cff6ab2b298312aeec0c8094b869cc1f00a3e904a9d4de264fe6b690b83d44`,
copied to the maintainer's Mac beside the older `pax-trunk.iso` (left as
it was) with `HOW-TO-BOOT-u6.txt`, whose command list is copied from the
typed session (`notes/px46/image/tour.keys`,
`notes/px46/image/transcript.txt`): `kill -l`, `su pax`, `id`, `kill 1`
refused as pax, `su` refused, `su - pax -c id`, `su -s /bin/pelt lobo`.
pelt is `7dd3304`, not sh16's tab completion: pelt PR #30 was open
(head d8d420c7) when the image was built.

## What U7 (every suite as a user) should know

- **`su` is the way in now**, not `as`: `su pax -c 'CMD'` from root's
  pelt runs CMD as 1000:1000 with groups `[1000]`, `HOME=/home/pax`,
  the caller's `PATH`; `su - pax -c 'CMD'` with a login's environment
  (`PATH=/bin` from the image's `/etc/login.defs`, the home as working
  directory). An image that uses it needs `/bin/su`, `/etc/passwd`,
  `/etc/group` and (for `-`) `/etc/login.defs`; `tests/mpx5-accounts`
  builds such an image and `tools/mksu` builds `su`. `as` (px39) is
  still the way for a probe that wants ids no account has.
- **A user's typed session leaves a history file** in its home
  (`/home/pax/.sh_history`; root's is `/.sh_history`), so a tree count
  (`mpx3-tree`'s T4 and T6) moves by one file per interactive shell.
- **The Linux side of a user run** can be `tools/linux-tree --owners`
  (owners and modes applied in the container, as the image's archive
  carries them) typing `su pax` first: no `as` binary, no account on any
  host. Real root's side is `notes/px46/vmtty.c` with
  `notes/px46/linux-vm.sh` (the suite's own archive as the guest's root).
- **Suites to give a user run** (px38's list): `mpx3-tree` (its probe
  takes no base directory yet: px43's note), `mpx3-shell` and
  `mpx3-boreutils` (what reads `/bin` works, what writes `/etc` does
  not), `mpx4-unix`, `mpx4-tcp` and `mpx4-udp` (a low port refused: px45),
  `mpx3-speaker` (anyone's on the console: px45's `console.controlling`),
  `mpx4-lobo` (lobo#52's drop to `lobo`, 990, now an account in the
  image's files).
- **`logname`** prints from `/proc/self/loginuid` or utmp on Linux
  (bu24); PAX has neither, so it should answer `no login name`
  (inferred, not run here): leave it out of a differential session (a
  container inherits the host's login uid).
- **pelt's terminal**: the console now honours VMIN 0 with VTIME (§B);
  VTIME with VMIN above 0 is still stored only.
- The words stay R6's: enforced for honest programs; not a boundary
  against an attacker.

## 4. Evidence index

Shas are this branch's (`px46`). kasumi paths are under `~/lanes/px46/`;
hasu's likewise.

### What was written

- The prediction: `cb0aa9c`.
- The pins: `97ddc75` (pelt `7dd3304`), `d759070` (boreutils `23ea8dd`).
- `su`: `06f7fe9` (`user/su/wolf-toolchain.toml`), `98a125e`
  (`user/su/su.lu`), `53b1f5c` (`tools/mksu`).
- The console: `4b12ceb` (`kernel/console`), `dfbebb1` (`kernel/files`).
- The suite: `7d6e0a0` (`tools/linux-tree --owners`), `1f6e5e2` and
  `59eaf2e` (`user/console/accounts.keys`), `4137436` and `d2ca5a5`
  (`notes/px46/vmtty.c`, `linux-vm.sh`), `e00ab25` and `bd90559`
  (`tests/mpx5-accounts`), `11465ad` (the CI job), `d77db23`
  (`tools/ci-tiers.map`, `tests/ci-plan`), `d099f73` (real root's
  recording).
- The suites the pins moved: `e8a8f47` (`mpx3-console`), `7e2243f`
  (`mpx3-shell`), `991fe43` (`mpx4-session`), `4855a4b`
  (`session-shell.expect`), `3a8939a` (`mpx3-tree`), `bc8df17` (lobo's
  steps).

### What was measured, and where it is

- **Linux's `su`**, three configurations: `notes/px46/linux/su-ct.txt`
  (`notes/px46/su-ct.sh`, probe `show.c` `81a1de35…`); PAX's `su` on the
  same rows: `notes/px46/su-ct-pax.txt` (`su` `4a5a4e21…`).
- **The console's VMIN 0**: `notes/px46/linux/vtime-pty.txt` (Linux),
  `notes/px46/pax-b7fb8d1-vtime.txt` (trunk), `notes/px46/pax-fix-vtime.txt`
  (fixed); the probe `notes/px46/vtime.c` (`9d9584c3…`).
- **The pins red without the fix**: CI run 38783928625 (at `d759070`),
  seven suites (§B).
- **Real root's session**: `tests/mpx5-accounts.d/linux/accounts.tty`,
  `.rc`, `vm-accounts.meta` (kernel `f4c00d5d…`, archive `002e370b…`,
  `vmtty` `f00f5189…`, keys `90c97204…`).
- **PAX**: `notes/px46/kasumi-mpx5-accounts-build-bc8df17.out` (every
  program built from scratch in the container: `su` `4a5a4e21…`, the
  same digest as the first build; pelt `57731756…`),
  `notes/px46/kasumi-mpx5-accounts-bd90559.out` (four legs, 32 boots, then
  the same images under `taskset -c 0-3`), `notes/px46/hasu-kvm-bd90559.log`
  (KVM, BIOS, both tiers, two rounds); `notes/px46/kasumi-mpx3-tree-bc8df17.out`
  and `kasumi-mpx3-screen-bc8df17.out` (the two suites the pins and the
  fix moved most, native BIOS, at `bc8df17`'s tree).
- **The plants**: §F.
- **The exploration image**: §G.
- **CI**: named in the PR.

### Measured, inferred, not verified

**Inferred**:
- PAM, not `su`, sets `MAIL`, `LANG` and the umask 0002 in Ubuntu's
  rows (they go when the three modules' lines go; no module was read).
- `logname` on PAX answers `no login name` (not run).
- A long option missing its argument (`--command`) prints `su: option
  '--command' requires an argument` (getopt's form; only the short one,
  `-c`, was measured).
- `su`'s refusal status 126 for a shell without an execute bit (only a
  missing shell, 127, was measured).

**Not verified**:
- Real root was one kernel (kasumi's CachyOS 7.2.8); Linux's `su` one
  build (Ubuntu 24.04's util-linux 2.39.3).
- `su` reached through PAM-less configuration only on Ubuntu; a
  distribution without PAM was not measured.
- The CI runner's Docker root carries supplementary group 0 (seen in
  plant A's first CI run), the rootless container's root none; the
  correct `su` sets the list whole, so the session is the same on both.
- `login` (not built, §E); VTIME with VMIN above 0 (stored only).
- More than one user logged in at once: PAX has one console.
- UEFI under KVM on hasu (pax#56): BIOS only there.
- Every suite as a user (U7's).

### Issues

- **To close at merge**: none.
- **Would file (none filed)**:
  1. pax: the console's VTIME with VMIN above 0 (Linux's timer between
     bytes) is stored and not acted on.
  2. pax: `TIOCGWINSZ` on the console answers the screen's 160 columns
     when QEMU gives the machine a display, and 0 without one; a typed
     session must keep its lines under 80 columns to read the same as
     on a pseudo-terminal (pelt wraps at the width).
  3. pax: `user/elf/as.c` and `su` now overlap; U7 decides whether the
     suites move to `su`.
- pax#62 (`mpx3-threads`' racy reference row): named in the PR if it
  reds.
- Not chased, did not occur: pax#45, #47, #53, #55, #58, #60, #63.

## 5. Done-when

- Branch `px46` on origin; pax PR #65, open, unmerged.
- The five sections §1 to §5; the items §A to §G.
- The test checklist:
  - [x] `tests/mpx5-accounts`, native and release, BIOS and UEFI, COM1 and PS/2, kasumi (TCG)
  - [x] the same images under `taskset -c 0-3`
  - [x] the same images under KVM on hasu (BIOS), two rounds
  - [x] the container's session and real root's recording identical
  - [x] `tests/mpx3-tree` and `tests/mpx3-screen`, native BIOS, kasumi
  - [x] `tests/ci-plan` (the new suite wired, `su`'s paths its alone)
  - [x] plant A and plant B red on kasumi; in CI: §F
  - [ ] the pr tier and `tier full` at the final head: named in the PR
- `wolf/tools/lane-audit.sh pax px46 <PR>` exit status: named in the PR.
- Trees: kasumi `~/lanes/px46/` keeps `out/`, `pins/`, `demo/out/`; build
  directories removed. hasu `~/lanes/px46/` keeps `out/`. Plant branches
  stay on origin, never to be merged.
