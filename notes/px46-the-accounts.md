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
