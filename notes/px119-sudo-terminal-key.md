# px119 — sudo's record made on a terminal names the session leader's start time (pax#339)

Base: pax#344's head `40da7481` (on trunk `1c827734` and pax#343's `3fa24cf5`). The prediction:
`notes/px119/prediction.txt`, committed before the first change. The rig: `notes/px119/rig/`.

## 1. What this lane does

sudo's timestamp kept a record made on a terminal under `tty NR sid SID`: the controlling terminal's number
(proc_pid_stat(5)'s tty_nr) and the session id. Both get reused. A pseudo-terminal takes the lowest free number,
so `/dev/pts/0` comes back as soon as its pair is closed, and a session id is its leader's pid. A later session on
the same pty number whose leader had the earlier leader's pid would match the earlier session's record and run
sudo with no password inside the timeout. sudoers_timestamp(5) keeps the session leader's start time in a
terminal's record for exactly this; PAX's record made with no terminal already keeps its parent's (px115).

- **The key** (`user/sudo/sudo.lu`, `ts_key`): a terminal's record is now `tty NR sid SID start T time MS`, T the
  session leader's start time, `start_of(SID)` (proc_pid_stat(5)'s field 22, the helper the no-terminal key
  already uses). A record of the old form starts `tty NR sid SID time`, which no key now begins with, so it
  matches nothing. `sudo -k` reads no record and is unchanged; `-K` removes the file as before.
- **When the leader's start time cannot be read** (its `/proc/SID/stat` gone or unreadable), the key is empty:
  sudo matches no record and writes none, so it asks and remembers nothing (R-px119-2). A key `start -1` would
  match a later session whose leader is unreadable too.
- **The rows.** `tests/mpx5-sudo` has a new image, `sudotty`, whose first program is a new probe,
  `user/elf/sudotty.c` (root, static glibc). It drives sudo on a pty from the master, typing bob's password when
  the prompt shows:
  - session A on `/dev/pts/0` (setsid, TIOCSCTTY, then bob) runs `sudo /bin/id -u` twice; **P9**: the second,
    inside the timeout, is not asked;
  - A's leader exits, the pair is closed, a new pair is `/dev/pts/0` again, and session B starts on it the same
    way. kernel/sched never reuses a pid (`take_pid` counts from 1), so B's leader cannot have A's pid in any time;
    the probe stubs it (R-px119-1): before B's sudo runs, A's record is given B's leader's pid where it named A's,
    everything else kept, which is the file a reused pid would meet. **P8**: B's sudo asks again.
  - The probe also prints the record's form after A (T3) and that B's leader started later (T6). Each row is held,
    with the lines it stands on, to `tests/mpx5-sudo.d/sudotty.pax` (PAX's own).
- **A Linux-side row** (`notes/px106/auth-ct.sh`, `sudo-n-tty-reused`, beside px115's `sudo-n-pid-reused`): in
  the suite's Ubuntu container, inside script(1)'s pseudo-terminal, root plants two records for bob in PAX's
  format for that very terminal and session, one of the old form and one with a start time a tick before the
  leader's, and `sudo -n id -u` runs as bob in that session. PAX's sudo asks, as Ubuntu's does (which keeps its
  records elsewhere): P4 holds the two the same.

## 2. Rulings

Recommended and implemented; none ruled yet.

- **R-px119-1 the reused pid on PAX.** kernel/sched never reuses a pid, so the honest reuse the issue describes is
  unreachable on PAX.
  - A. A stub in the row: A's record given B's leader's pid, all else kept (the file a reuse would leave). The key
    sudo builds and the record it wrote are the real ones; only the pid in the file is substituted.
  - B. Linux's `/proc/sys/kernel/ns_last_pid` (proc_sys_kernel(5)) in the kernel, so a test picks the next pid: an
    honest reuse, but a change to kernel/sched's core for a test, and a privileged interface PAX has no other use
    for yet.
  - C. pids that wrap at a `pid_max`, as Linux's do: a kernel change, and millions of forks a row.
  - **Recommended: A.** The Linux-side row has real pids and a real pty, with a planted record.
- **R-px119-2 the leader's start time unreadable.** A. match nothing and write nothing (sudo asks, remembers
  nothing); B. keep `start -1` in the key (it would match a later unreadable leader); C. fall back to the
  no-terminal key. **Recommended: A.** No row reaches it: a session's leader's end takes the terminal from the
  session (px111's hangup), so a caller with a terminal has a live leader (or a zombie, whose stat reads).
- **R-px119-3 the no-terminal key's `start -1`** (px115's key writes `ppid P start -1` when the parent's stat cannot
  be read). A. leave it (a running sudo's parent is alive, or sudo was given to an init whose stat reads); B. the
  same refusal there. **Recommended: A**, as out of this lane's issue; B is one line if wanted.
- **R-px119-4 the records' shape.** The local records use the recorder's steps mode with `--keep-going` and
  `--preflight` (the form for a take that holds a block: every red named in one take, the host checked before the
  first step), not px111's and px116's older `--output … -- CMD` form. **Recommended: steps mode.**

## 3. Named differences, and the prediction scored

No difference is named: `sudo-n-tty-reused` is the same bytes on both sides of the container (P4), and the
`sudotty` session is PAX's own expectation (`tests/mpx5-sudo.d/sudotty.pax`), with nothing on Linux to hold it to.
Every row the suite had before reads as before.

The prediction (`notes/px119/prediction.txt`), scored:

- Right: §A as read (the old key; `take_pid` never reuses a pid; `/dev/pts/0` back as soon as its pair closed:
  T5 says the same number).
- Right: at the rows' commit, before the fix, P9 green and P8 red by name, `not asked, ran as uid 0`, with T3
  showing the record `tty 34816 sid <the leader's pid> time <ms> (no start time)`; the container row red under P4,
  PAX's sudo running id (`--- rc 0`, `0`) where Ubuntu's asked (`--- rc 1`, `sudo: a password is required`).
- Right: after the fix, P8 asked, P9 not asked, T3 `tty 34816 sid <the leader's pid> start <the leader's start
  time> time <ms>`, T6 B's leader later than A's; the container row the same on both sides (`--- rc 1`,
  `sudo: a password is required`).
- Right: every other row unchanged in both takes (S1, S5, P1 to P7; the pw and admin sessions' second sudo still
  not asked).
- Right: the image boots in a few seconds under KVM (3 s on native BIOS, far under the 60 predicted).
- Not predicted: the suite says every verdict through `tools/lib.sh`'s `say` (`mpx5-sudo: FAIL …`), so a FAIL
  line never starts at column 0 by itself; the rig's `step.sh` lifts `mpx5-sudo: FAIL ROW` to `FAIL ROW` so the
  plant's rows are named in its record. The red take before the fix was taken before that change (its FAIL lines
  are indented; it is a red record, not a plant).
- The page read for sudoers_timestamp(5) was sudo 1.9.17p2's, not 1.9.15p5's as the prediction says; its
  `start_time` text is what the key follows.

**Seen red.** At `5b3837f4` (the rows, the container row and the rig, before the fix), the red take
(`red-5b3837f4.log`, sha256 `3445cc4ba3572aa9bba5809f9df2030869c811bfa3365c59342d1113008c97d2`, steps mode,
`keep-going=1 preflight=ok`) ended `END build exit=0`, `END auth exit=1`, `END boot exit=1`: `FAIL P4: unnamed
difference at 55/55:|- --- rc 1|+ --- rc 0|unnamed difference at 57/57:|- sudo: a password is required|+ 0|` and
`FAIL P8 native bios sudotty: < T3 … start <the leader's start time> time <ms>|> T3 … time <ms> (no start time)|<
P8 … asked, the password typed, ran as uid 0|> P8 … not asked, ran as uid 0|`, with `PASS P9 native bios sudotty`
and every other row green.

## 4. What is not done

- **An honest pid reuse on PAX** (R-px119-1): the kernel has none to reuse.
- **The leader-unreadable branch** has no row (R-px119-2): unreachable without a stub of /proc.
- **The console's records** had the same gap in principle (a reused session id alone); the same key covers them.
- **mpx6-install, mpx5-burrowd and the metal install suite** read user/sudo too (the planner selects them).
  Their sudo rows run with `-n`, NOPASSWD rules or no terminal, each within one session, where the key is the same
  from run to run, so the change should not reach their answers. They are the hosted run's, not the local
  gauntlet's.

## 5. Evidence index

- **The prediction.** `notes/px119/prediction.txt` (`4074b116`), before the first change.
- **The rows before the fix.** The probe (`3acef2eb`, its buffer widened in `00c99262`), the suite's image and
  rows (`f9dbf76a`), the tiers map's line (`49ff1f70`), the container row (`20cb128c`), all red first; the fix is
  `16f45f52`.
- **The rig.** `notes/px119/rig/`: `take.sh` takes the block's two lock names (the block's first) and runs the
  org's recorder in steps mode with `--keep-going` and `--preflight`; `gauntlet.manifest` (ci-plan; the build,
  native and release; the container sides; the boots, native and release, BIOS and UEFI, KVM) and
  `short.manifest` (the native build, the container sides, native BIOS's boots) name the steps, `step.sh` runs
  each (`lib.sh` its container), every rig file declared with its committed digest. The container sides use px106's
  `notes/px106/rig/docker-like`, so they run in docker's shape, as CI's do.
- **The red take** (§3): `red-5b3837f4.log`, at `5b3837f4`.
- **A take at the fix** (the short manifest, at `8f16db62`): `dev-8f16db62.log`, sha256
  `8f5bb80d35e13a3dc836b9fcfa1aa6872a018ac83824f8d3489f9e0bdd1392c7`, `END build exit=0`, `END auth exit=0`,
  `END boot exit=0`, worst 0: `PASS P4`, `PASS P8 native bios sudotty`, `PASS P9 native bios sudotty`, every other
  row green; the sudotty session is `tests/mpx5-sudo.d/sudotty.pax` line for line.
- **The records at this branch's head**: the green take (`gauntlet.manifest`, worst 0) and the plant
  `px119-plant-key` (one hunk of `user/sudo/sudo.lu`'s `ts_key`: the terminal's key back to `tty NR sid SID`; the
  short manifest, red by name at P8 and P4). Their files, sizes and sha256 are in the pull request's body.
- **The hosted run.** The pull request's run, and the full-matrix run its label starts.
