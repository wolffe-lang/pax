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

(Written as the lane goes.)
