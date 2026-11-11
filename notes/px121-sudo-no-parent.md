# px121 — sudo with no terminal keeps no record when the parent cannot be read

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
- **The change.** With no terminal, when the parent's start time cannot be read the key is empty: sudo matches no
  record and writes none, so it asks every time and remembers nothing, as px119's terminal key does when the
  leader cannot be read. Records of the old shared form already in a file match nothing (no key now says
  `start -1`) and drop out when they are old. `-k` and `-K` are unchanged.
- **The rows** (`tests/mpx5-sudo`'s new `sudoppid` image, its probe `user/elf/sudoppid.c`, root, static glibc;
  held to `tests/mpx5-sudo.d/sudoppid.pax`, PAX's own). The image's run list is two commands:
  - init forks session D's leader, which starts a session of its own (no terminal) and forks two callers; init
    ends, then the leader, and the callers have no parent. They run `sudo -S /bin/id -u` as bob in turn, the
    password on standard input, the second after the first has ended. **P10**: the second, inside the timeout, is
    asked again, and no record file is left (T3: no terminal, one session, getppid 0, `/proc/0/stat` unreadable;
    T4: the first asked; T5: the record after D, none).
  - kmain_console starts the second command only when every process of the first has ended. It reads what D's
    runs did, then starts session E, whose two callers' parent is its leader, alive. **P11**: the second, inside
    the timeout, is not asked (T6: no terminal, one session, the parent's stat read; T7: the first asked; T8: the
    record `ppid <the parent's pid> start <the parent's start time> sid <the session> time <ms>`; T9).
  - P8 and P9 (the terminal's rows, `sudotty`) and every other row of the suite are unchanged.

## 2. Decisions (recommended and implemented; none ruled yet)

- **Reaching an unreadable parent on PAX.** A: callers left with no parent after init's end, a state the kernel
  really has (chosen); B: a stub of `/proc`, a test-only change to what the kernel serves; C: sudo as pid 1, one
  run a boot, which cannot show a second caller asked again.
- **No Linux-side row.** Ubuntu's sudo in this state is not measured: the suite's container runs one script whose
  callers all have a parent; a parentless caller needs an engine's exec into a running container.
- **Init's status line.** kernel/user records the status of the last process with no parent to exit as the run
  list's init status, so `PAX: init /bin/sudoppid ended with status 0` reads the second caller's (PAX's sudo runs
  the command in its own process, so it is `id`'s). Named here, not changed.
- **Out of this change:** a caller whose parent ended before sudo read it is given to pid 1, and its key
  `ppid 1 start <init's start time> sid SID` is every such caller's in the session while init lives. The parent
  reads there, so the key is px115's as before.

## 3. Seen red

The plant branch `px121-plant-key` is one hunk of `ts_key`: the no-terminal key back to
`"ppid {pp} start {start_of(pp)} sid {sid}"`. It is red by name at P10, the second caller of session D not asked
(`not asked, ran as uid 0`) and T5 showing the record `ppid 0 start -1 sid <the session> time <ms>`; P11, P8 and P9
stay green. The plant is pushed and never merged.

## 4. What is not done

- A Linux-side row (§2).
- The install suites that read `user/sudo` too (the tiers map names them) run sudo with `-n`, NOPASSWD rules, or
  callers with a live parent, so the change should not reach their answers; they are the hosted run's, not the
  local gauntlet's.

## 5. Evidence index

- **The change**: `user/sudo/sudo.lu` (`ts_key`); the probe, the image and rows, the tiers map's line, CHANGELOG and
  `docs/SOURCES.md` follow it on the branch.
- **The takes**: px119's rig (`notes/px119/rig/take.sh`, the recorder's steps mode with `--keep-going` and
  `--preflight` under the block's two locks): `gauntlet.manifest` for the green (ci-plan; the build, native and
  release; the container sides; the boots, native and release, BIOS and UEFI, KVM) and `short.manifest` for the
  plant (the native build, the container sides, native BIOS's boots). Their files, sizes and sha256 are in the pull
  request's body.
- **The hosted run**: the pull request's run, and the full-matrix run its label starts.
