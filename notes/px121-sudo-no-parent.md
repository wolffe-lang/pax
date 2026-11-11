# px121 — sudo with no terminal keeps no record when the parent cannot be read or is init

Base: trunk `3b6e4b64` (pax#345, px119's terminal key). The rig is px119's, unchanged (`notes/px119/rig/`).

## 1. What this lane does

px115 keyed sudo's timestamp record made with no terminal by the parent: `ppid P start T sid SID time MS`, T the
parent's start time (proc_pid_stat(5)'s field 22), as sudoers_timestamp(5) keeps a `TS_PPID` record. px119 refused
a key when a terminal's session leader cannot be read, and left this one as it was.

- **What the code did** (`user/sudo/sudo.lu`, `ts_key` at `3b6e4b64`): with no terminal the key was
  `"ppid {pp} start {start_of(pp)} sid {sid}"`. `start_of` gives -1 when `/proc/P/stat` cannot be read, and
  `authenticate` honoured and wrote that key like any other, so the record was `ppid P start -1 sid SID time MS`.
  The key is not one for every caller in that state: it keeps the parent's pid and the session, so it is shared by
  the callers of one session with the same parent pid whose parent cannot be read.
- **Where that happens.** On PAX a live process's `/proc/PID/stat` always reads, so the parent that cannot be read
  is none at all: getppid(2) says 0 for a process the kernel started and for one whose parents have ended after
  pid 1 has (kernel/sched's `reparent` gives them to nobody), and `/proc/0/stat` names no process. The shared key
  is then `ppid 0 start -1 sid SID`, every parentless caller's in the session: a password one gave was honoured for
  the others inside the timeout. On Linux getppid is 0 for a process whose parent is outside its pid namespace (a
  command a container engine's exec starts), and with no `/proc` every start time is unreadable.
- **The neighbouring case.** A caller whose parent ends is handed to pid 1 while it lives, so its key is
  `ppid 1 start <init's start time> sid SID`: every caller of the session handed to init shares it, for as long as
  init lives.
- **The change.** With no terminal, when the parent's start time cannot be read, or the parent is pid 1, the key
  is empty: sudo matches no record and writes none, so it asks every time and remembers nothing, as px119's
  terminal key does when the leader cannot be read. Records of the old shared forms already in a file match nothing
  (no key now says `start -1` or `ppid 1`) and drop out when they are old. `-k` and `-K` are unchanged.
- **The rows** (`tests/mpx5-sudo`'s new `sudoppid` image, its probe `user/elf/sudoppid.c`, root, static glibc;
  held to `tests/mpx5-sudo.d/sudoppid.pax`, PAX's own). The image's run list is two commands. In each session two
  callers run `sudo -S /bin/id -u` as bob in turn, the password on standard input, the second after the first has
  ended.
  - Session F: init forks its leader, which starts a session of its own (no terminal), forks two callers and ends
    at once, so the callers are handed to init, alive; init reaps them. **P12**: the second, inside the timeout,
    is asked again, and no record of the session is left (T2: no terminal, one session, the parent init; T3: the
    first asked; T4: the record after F, none).
  - Session D: init forks its leader the same way and ends, then the leader ends, and the callers have no parent.
    **P10**: the second is asked again, and no record of the session is left (T7: no terminal, one session,
    getppid 0, `/proc/0/stat` unreadable; T8: the first asked; T9: the record after D, none).
  - kmain_console starts the second command only when every process of the first has ended. It reads what D's
    runs did, then starts session E, whose two callers' parent is its leader, alive. **P11**: the second, inside
    the timeout, is not asked (T10: no terminal, one session, the parent's stat read; T11: the first asked; T12:
    the record `ppid <the parent's pid> start <the parent's start time> sid <the session> time <ms>`; T13).
  - P8 and P9 (the terminal's rows, `sudotty`) and every other row of the suite are unchanged.

## 2. Decisions

- **Reaching these parents on PAX.** Callers handed to a live init, and callers left with no parent after init's
  end: states the kernel really has, no stub. A stub of `/proc` (a test-only change to what the kernel serves) and
  sudo as pid 1 (one run a boot, which cannot show a second caller asked again) were the other ways.
- **The pid-1 parent.** The key is refused for every caller whose parent is pid 1, not only one handed to it.
  Where sudo runs as init's own child on PAX, none relies on a record made with no terminal:
  - an installed system's console: `/bin/login` (pid 1) execs the user's shell, so a command typed there is init's
    child, but the console is its controlling terminal and the terminal's key holds (`tests/mpx6-install`'s U13:
    `sudo -n` inside the timeout, refused after `-k`); the images' typed sessions (pelt as pid 1) the same;
  - the boot's hooks (`/etc/pax-boot.d`) run as root in the console's session; the burrowd loop the burrowd hook
    leaves behind is handed to init, but a command over ssh is, at this burrow pin, still in the console's session
    with the console its controlling terminal (`tests/mpx5-burrowd`'s B15 and B16), so the terminal's key holds;
  - `user/elf/sid.c`'s sudo rows (`tests/mpx5-sudo`'s `sudo` image) run sudo as init's child in a session of its
    own with no terminal, but every row there is NOPASSWD, root's, or refused before a password: no password is
    given, so no record is made and none is there to honour;
  - the container rows: px103's (`notes/px103/sudo-ct.sh`) give no password, so make no record; px106's
    (`notes/px106/auth-ct.sh`) give each row a session of its own or a pseudo-terminal, so no row's record reaches
    another's whatever its parent, and P4 holds PAX's sudo there to Ubuntu's as before.
- **No Linux-side row.** Ubuntu's sudo in these states is not measured: the suite's container runs one script whose
  callers all have a parent other than its pid 1; a parentless caller needs an engine's exec into a running
  container.
- **Init's status line.** kernel/user records the status of the last process with no parent to exit as the run
  list's init status, so `PAX: init /bin/sudoppid ended with status 0` reads the second caller of session D's (PAX's
  sudo runs the command in its own process, so it is `id`'s). Named here, not changed.

## 3. Seen red

Two plant branches, each one hunk of `ts_key`, pushed and never merged:

- `px121-plant-key`: the no-terminal key back to `"ppid {pp} start {start_of(pp)} sid {sid}"` before the pid-1
  refusal existed. Red by name at P10: D's second caller `not asked, ran as uid 0`, and the record after D
  `ppid 0 start -1 sid <the session> time <ms>`; P11, P8 and P9 green.
- `px121-plant-init`: the pid-1 refusal removed, the rest kept. Red by name at P12: F's second caller not asked,
  and the record after F `ppid 1 start <init's start time> sid <the session> time <ms>`; P10, P11, P8 and P9 green.

## 4. What is not done

- A Linux-side row (§2).
- The install suites that read `user/sudo` too (the tiers map names them) run sudo with `-n`, NOPASSWD rules, a
  terminal, or callers with a live parent, so the change should not reach their answers; they are the hosted run's,
  not the local gauntlet's.

## 5. Evidence index

- **The change**: `user/sudo/sudo.lu` (`ts_key`); the probe, the image and rows, the tiers map's line, CHANGELOG and
  `docs/SOURCES.md` follow it on the branch.
- **The takes**: px119's rig (`notes/px119/rig/take.sh`, the recorder's steps mode with `--keep-going` and
  `--preflight` under the block's two locks): `gauntlet.manifest` for the green (ci-plan; the build, native and
  release; the container sides; the boots, native and release, BIOS and UEFI, KVM) and `short.manifest` for the
  plants (the native build, the container sides, native BIOS's boots). Their files, sizes and sha256 are in the
  pull request's body.
- **The hosted run**: the pull request's run, and the full-matrix run its label starts.
