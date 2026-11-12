# px124 — pid 1 stays: a logout at the console, and a runtime directory for each account (pax#352)

Base: trunk `309036ec`. Queued ahead of this branch, fast-forward only: pax#349, pax#347, pax#350 (sudo: no
record with no terminal when the parent is pid 1 or cannot be read) and a pin bump that moves burrow to sessions of
its own per program. Expect one rebase; it is delivered as a new branch and pull request.

## 0. The prediction (written before the first change)

**What is pid 1.** An installed PAX boots `/etc/pax-run`'s one command as pid 1; since px106 that is `/bin/login`,
which execs the account's shell, so the shell is pid 1 and its `exit` ends the boot (`PAX: init /bin/login ended
with status 0; nothing left to run`, `halt`). After this lane pid 1 is a new program, `/bin/init` (`user/init`, in
wolf, about 400 lines with a 100-line assembly membrane): it does once a boot what login did as pid 1, then stays.

- **What moves out of login:** the three boot duties login had as pid 1 (sudo's records emptied, px106; `pax-boot-status
  record`, px118; the hooks of `/etc/pax-boot.d`, px112). login keeps the console's prompts, the password, the
  first-boot rule and the session's environment, and gains `XDG_RUNTIME_DIR`. As pid 1 (a run list that still
  names it) login execs `/bin/init` when it is there, so `/etc/pax-run`'s text does not change: the installer
  writes `/bin/login` as before, an upgrade has nothing to regenerate, and a run list an owner kept still gets
  init. Without `/bin/init` (an archive from before this lane, a suite's own tree) login as pid 1 logs one
  session in after another exactly as before, and runs no hook.
- **init's loop:** `/run` a fresh tmpfs, the runtime directories, the boot duties, the console handed out of pid
  1's session (TIOCNOTTY); then, for ever: the console's modes put back as the boot left them and the console
  root's 0600 again, login started in a child that leads a new session with the console as its controlling
  terminal (setsid, TIOCSCTTY), every child handed to init reaped as it ends, and, when the session's leader
  ends, the session hung up: SIGHUP and SIGCONT to every process still in it, SIGKILL 2000 ms later to any still
  there, nothing to a process that left it (setsid), nothing to pid 1's own session (the hooks' services:
  burrowd is neither restarted nor ended). Then `HOST login:` again.
- **Shutdown stays the kernel's.** `reboot`, `reboot -h` and `poweroff` are reboot(2): kernel/user's end sends
  SIGTERM and SIGCONT to every process, init included, then SIGKILL after 2000 ms, writes the volumes and resets,
  halts or powers off. init adds nothing to it.
- **The runtime directory:** `/run/user/UID`, the account's, 0700, on `/run`'s tmpfs (empty at every boot), made
  by init at boot for every account whose shell is not `…/false` or `…/nologin`, and by login at a login when it is
  missing; login sets `XDG_RUNTIME_DIR`. An ssh session finds the directory there; burrowd cannot set the variable
  per account (its `SetEnv` line is one text for every account), so over ssh the variable is not set.
- **What does not change:** the dev and release images (pid 1 `/bin/env ENV=/etc/shrc /bin/sh -i -m`, so pelt)
  and the live stick (pid 1 `/bin/pelt /etc/pax-live-login`, the live login script, which runs the hooks itself)
  boot as before and still halt at `exit`; the upgrade's texts and the staged boot.

**What each row should show** (a new suite, `tests/mpx5-init`, unless named):

| row | at the rows' commit (login pid 1, no init) | after the change |
|---|---|---|
| I1 pid 1 is `/bin/init`; the console shell's parent is 1, it leads its session, the console is its terminal; pid 1 has none | red: pid 1 is the shell | green |
| I2 `/run` a tmpfs 0755, `/run/user` 0755 root's, `/run/user/1000` 0700 pax's, `XDG_RUNTIME_DIR` names it, none for a `/bin/false` account | red: no `/run` mount, no variable | green |
| I3 a typed `sudo` remembered inside its session (its parent the shell, not pid 1) | green (pid 1's shell is sudo's parent; the terminal's key) | green |
| I4 `exit` gives `pax login:` again | red: the machine halts | green, within 3 s |
| I5 the session's background job ends at the hangup; one that ignores SIGHUP is killed 2000 ms later and init says so | red (halt) | green |
| I6 a process that called setsid survives, is pid 1's child, and is reaped when it ends (no zombie) | red (halt) | green |
| I7 the console's modes are back (`stty -echo` before `exit`, `echo` after) and the console is root's 0600 between sessions | red (halt) | green |
| I8 a second account (bob) logs in after pax's logout, with its own runtime directory | red (halt) | green |
| I9 `logout` and Ctrl-D at an empty prompt log out too | red | green |
| I10 sudo across a logout: pax's record from the first session is void in pax's next one (`sudo -n` asked) | red (halt) | green |
| I11 a hook's service keeps its pid and pid 1's session across every logout | red (halt) | green |
| I12 `reboot -h` as root: the kernel's end, init among the processes ended, `halt` | red (no session to type it) | green |
| I13 `/` on a disk: a file left in the runtime directory is gone after `sudo reboot`, the directory pax's 0700 again, a file in pax's home kept; `sudo poweroff` ends the machine (ACPI off) | red | green |
| mpx5-burrowd: an ssh command running across a console logout ends with its own output and status 0; burrowd keeps its pid; the runtime directory is there over ssh | red (at boot 1's `exit` the machine halts) | green |
| mpx5-sudo, mpx5-den, the distribution, stick and upgrade suites | green | green, unchanged |

The plant: init with no SIGKILL after the hangup's bound (the SIGHUP-ignoring job survives): I5 red by name.

## 1. What this lane does

### 1.1 pid 1 (`user/init`, `tools/mkinit`)

`/bin/init` is a wolf program built as the installer is: kernel/wolf.pin's wolf with the std its archive bundles,
the package directory `user/init` (`init.lu`; `init.S`, nine system calls the builtins do not reach: setsid, the
console's ioctls, wait4 on any child, kill, and /run's mount), `--release --deny-warnings`, linked static, stripped
(`tools/mkinit`; `tools/mkdistribution` builds it and `tools/distribution-root` puts it in both images, held to its
sums). It refuses any pid but 1. Its children are made with the runtime's own fork (`os_fork`), which parks the
runtime's threads before the fork and remakes its tables in the child (a raw fork would copy a lock another thread
holds); every child, its own and the orphans handed to it, is reaped with wait4(-1) in the membrane, so nothing is
waited for through the runtime's table but `pax-boot-status record`.

Once a boot, in order: `/run` (a tmpfs mounted over it unless `/proc/self/mounts` already has one there, 0755;
`/run/user` 0755 root's; `/run/user/UID` 0700 the account's for every `/etc/passwd` line whose shell does not end
`/false` or `/nologin`); sudo's records emptied; `pax-boot-status record`; the hooks, each a process group of its
own with standard input /dev/null, waited for at most 10 s (px112's rule, its lines now `init: …`). Then
TIOCNOTTY: the console leaves pid 1's session, whose foreground group (init's own) hears SIGHUP and SIGCONT, which
the kernel spares pid 1 (kernel/signal: a default action is nothing for pid 1).

Then for ever: the boot's termios put back (TCSETSW of what TCGETS read at the start), the console's descriptors'
record root's 0600 (kernel/files' boot values; login gave it to the account); a child that calls setsid, takes the
console with TIOCSCTTY (arg 1, so a session that opened the console after leaving the last one loses it) and execs
`/bin/login` with init's environment; init blocks in wait4(-1), reaping orphans as they end, until that child
ends. The hangup then: the processes whose `/proc/PID/stat` session field is the leader's pid (a zombie left out)
get SIGHUP and SIGCONT; init reaps and reads again every 20 ms, and any still in the session 2000 ms later gets
SIGKILL and one line: `init: the session of pid N: SIGKILL to K of M still there 2000 ms after its SIGHUP`. A session
that ends within 2 s of its start makes the next start wait (1 s, doubling to 60 s, one line each time).

The kernel already did its part of a logout before this lane (px48, px111): when the leader ends, the console's
foreground group hears SIGHUP and the console leaves the session; a group the end orphans with a stopped member
hears SIGHUP and SIGCONT; the leader's children go to pid 1. init adds the rest of the session (its background jobs,
which Linux's terminal rule leaves alone and logind's session scope ends) and the reaping.

### 1.2 login (`user/login/login.lu`)

The three boot duties are gone from it (init's now). As pid 1 it execs `/bin/init` when that file is there, so the
installed run list (`/bin/login`, every installer's text since px106) gives init with nothing on the disk rewritten;
without it (a suite's own tree, an archive from before this lane) it logs one session in after another as before,
the shell as pid 1, and runs no hook. It sets `XDG_RUNTIME_DIR=/run/user/UID` when `/run/user` is a directory,
making the account's directory when it is missing and setting its owner and mode either way, as root before the ids
change. Nothing else in it moved: its prompts, the first-boot rule and the five tries are px106's.

### 1.3 `logout` (`user/shrc`)

pelt has no `logout`. `/etc/shrc` (which every interactive pelt reads through ENV) defines one: in a shell that
leads its session (`/proc/$$/stat`'s sixth field is `$$`: the console's login shell, which init starts so) it is
`exit`, elsewhere it says `logout: not login shell: use `exit'` and returns 1, as bash's builtin does. Not `$0`:
pelt at its pin names itself `pelt` whatever its argv[0] (`-sh` from login), so a `$0` test was red at I9 in the
first green take. `tools/system-env` reads only `export` lines, so burrowd's SetEnv line is unchanged.

### 1.4 Where pid 1 is not init

The dev and release images keep `/bin/env ENV=/etc/shrc /bin/sh -i -m` (pelt) as pid 1 and the live stick
`/bin/pelt /etc/pax-live-login`: both still halt at `exit`, both carry `/bin/init` unused, and neither has /run's
tmpfs or a runtime directory. An install from the stick copies `/bin/init` with the rest and writes `/bin/login` as
its run list, so the installed system boots init.

### 1.5 The rows

`tests/mpx5-init` (new, its CI job, its tiers map lines) boots an installed-shaped tree from an ISO (`/etc/pax-run`
`/bin/login`, `/bin/init` beside it, login and sudo from tools/mkauth, pelt, ten boreutils, reboot and poweroff,
`user/elf/detach.c`, `user/elf/ttymode.c` (boreutils' stty reports no modes at its pin), `/etc/shrc` from user/shrc
without lope's line, one boot hook that leaves a `sleep` running in
pid 1's session) and types at its console through COM1 (I1-I12), then boots twice a disk whose ext2 volume is `/`
(I13). Each row is in the suite's header and in §0's table. `tests/mpx5-burrowd`'s installed shape carries
`/bin/init` and `/bin/poweroff`: B30 (an ssh command running across root's console logout), B31 (the runtime
directory over ssh) and B32 (`sudo -k -S poweroff` over ssh); B15 changes (below). The metal leg's live tree
(`tests/mpx6-install.d/metal.py`) carries `/bin/init`, so its installed disk boots it. `tests/distribution` holds
the images' `/bin/init` to tools/mkinit's bytes.

### 1.6 What changed for ssh (B15, B16)

A command over ssh is, at this burrow pin, in the session of the boot hook that started burrowd: pid 1's. Until
this lane the console was that session's terminal, so a bare `sudo` over ssh asked on the console and was stopped
there while its client waited (B15), and `sudo -S`'s record was keyed by the console, shared by every ssh session
(B16, measured). init gives the console up before the first login, so a command over ssh has no terminal: a bare
`sudo` is refused at once by name (`a terminal is required to read the password`, B15's new form), and a plain
`sudo -S`'s record is keyed by its parent, the session's own shell (px115's key), so another ssh session is asked.
The README's ssh section says so. A burrow that gives each program a session and a terminal of its own changes both
rows again (the pin bump queued ahead of this branch).

## 2. Decisions

Recommended and implemented; none ruled yet.

- **R-px124-1 what is pid 1.** A. a new `/bin/init` in wolf, small, with nothing of the accounts in it; B. login
  stays pid 1 and forks each session (one binary, but pid 1 would run the password hash's 128 MiB and every
  account's code, and a fault there ends the boot); C. pelt as pid 1 running a loop (a shell has no setsid or
  TIOCSCTTY, and the shell as pid 1 is the issue). **Recommended: A.**
- **R-px124-2 the installed `/etc/pax-run`.** A. keep `/bin/login`, every installer's text since px106; login as
  pid 1 execs `/bin/init`; B. the installer writes `/bin/init`, the upgrade regenerates the old text (a line in
  `baselines/generated.sha256`), the metal leg's tree and the upgrade suites' texts change, and a run list its owner
  kept still needs A's exec. **Recommended: A**: nothing on an installed disk is rewritten, an upgrade gives init by
  replacing two programs, and a kept run list gives it too. The kernel's `run 1:` line still names `/bin/login`;
  `/proc/1/cmdline` is `/bin/init`.
- **R-px124-3 login as pid 1 with no `/bin/init`.** A. sessions one after another as before, the boot duties gone
  (init's); B. the duties kept in login too. **Recommended: A**: only a suite's own tree or an archive older than
  this lane lacks init, and none of those has a hook (mpx5-sudo's login images, mpx5-den's login image).
- **R-px124-4 the console's hand-over.** A. init gives it up once (TIOCNOTTY) after the hooks, each login's child
  takes it (setsid, TIOCSCTTY 1); B. init keeps it and each child steals it (the same SIGHUP to init's group at the
  first steal, and pid 1's session holding a terminal it never reads). **Recommended: A.** Its consequence for ssh
  is §1.6.
- **R-px124-5 the hangup.** A. every process of the leader's session (`/proc/PID/stat` field 6): SIGHUP and
  SIGCONT, SIGKILL to any still there 2000 ms later (the kernel's own end's grace); B. only the kernel's terminal
  rule (the foreground group's SIGHUP: a background job outlives the logout); C. every process of the account
  (logind's `KillUserProcesses=yes`: a server that called setsid would die too, which warren must not); D. logind's
  90 s bound. **Recommended: A**, the contract's. A process that ignores SIGHUP (`nohup`) is killed with the rest;
  one that left the session first is not.
- **R-px124-6 the runtime directory.** Where: `/run/user/UID` on a tmpfs init mounts over `/run` at boot (as
  systemd mounts its own /run; not an `/etc/fstab` line, so no installer text changes; an fstab `/run` is kept).
  When: made at boot for every account with a login shell, and by login when missing. How long: from boot to
  shutdown, as logind keeps a lingering user's (`loginctl enable-linger`), not removed at the last logout as XDG's
  lifetime rule has it, so a server started at the console survives its logout and the next login finds its socket.
  Over ssh: the directory is there, the variable is not (burrowd's SetEnv is one text for every account).
  **Recommended as built.** The follow-up is burrow's: set `XDG_RUNTIME_DIR` when `/run/user/UID` exists and is the
  account's 0700, as pam_systemd does at a session's start (an issue to file on burrow).
- **R-px124-7 `logout`.** A. a function in `/etc/shrc`; B. a pelt builtin (pelt's repository, its own lane).
  **Recommended: A** now, B later if pelt wants it.
- **R-px124-8 shutdown.** A. the kernel's end as it is (reboot(2): SIGTERM and SIGCONT to every process, init
  among them, SIGKILL after 2000 ms, the volumes); B. init asked to end the sessions first (a signal from reboot's
  program, which is not init's, and a kernel that waits for init). **Recommended: A**: the bound and the order are
  the kernel's, every process including pid 1 is ended, and I12, I13 and B32 show `reboot -h`, `reboot` and
  `poweroff` from a session and over ssh.
- **R-px124-9 between sessions.** The boot's termios and root's 0600 put back; no screen reset (RIS) and no input
  flush: keys typed ahead reach the next login, as on PAX's console before. **Recommended as built.**
- **R-px124-10 a session that ends at once** waits 1 s, doubling to 60 s, so a missing or broken `/bin/login`
  never fills the console. **Recommended as built.**
- **R-px124-11 where the rows live.** A new suite for init's behaviour, sudo's logout row with them (it needs a
  logout; mpx5-sudo's login images are login-as-pid-1 trees held to an Ubuntu container); the ssh rows in
  mpx5-burrowd. **Recommended as built.**
- **R-px124-12 sudo's keys (pax#350).** A console `sudo` has the console as its terminal and the shell as its
  parent: the terminal's key, remembered in its session (I3), void in the next (I10, the leader's start time).
  pax#350's refusal of a parent that is pid 1 applies only with no terminal; with init as pid 1 such callers are
  orphans and what the hooks started, which give no password. **No change to sudo.**

## 3. Not done, by name

- `XDG_RUNTIME_DIR` over ssh (R-px124-6): burrow's to set.
- The runtime directory is never removed while the machine runs (R-px124-6), and a directory for an account made
  after the boot waits for its first console login.
- No Linux-side row: a logout's effect on Ubuntu needs logind and a real login session, which the suites' containers
  do not have; the rows hold PAX to the documents (§2) and to its own expectations.
- The dev and release images' and the stick's pid 1 are unchanged (no logout there).
