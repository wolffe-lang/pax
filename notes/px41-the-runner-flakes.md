# px41 — The runner flakes (pax#45, #47, #53)

Contract: px41's, `sprints/pax/41-the-runner-flakes/` in wolffe-lang/wolf
(planning `ec9cf82`, read 2026-10-13). Branch `px41` in pax, cut from
pax trunk `7d2e9ba` (px40 merged). §1–§3 are committed before the first
change to the kernel, the tools, the tests or `user/`.

One deliverable: for each of three assertions that failed once or twice
on a CI runner and passed on a re-run, the cause found by reproduction,
then the fix that cause asks for: a kernel bug fixed, a harness race
fixed, or an assertion that was stricter than the thing it checks
restated with the reason beside it.

## 1. Forbidden, absolutely

- No kernel's, libc's or filesystem's source is read (ruling #22). Facts
  come from the man pages (`clock_nanosleep(2)`, `nanosleep(2)`,
  `ip(7)`, `bind(2)`, `proc_sys_fs(5)`), POSIX.1-2024, Intel's 8254 and
  8259A data sheets, QEMU's own documentation and black-box runs.
- No assertion deleted. None weakened without the reproduction that
  justifies it written beside it. A raised timeout or a widened
  tolerance alone is not a fix; a bound that moves is derived from a
  measurement or a rule, and says which.
- Nothing fixed that was not seen: each flake has a recipe and a red
  rate, or an honest "not reproduced after N tries under these loads".
- px39 is in `kernel/user`, the process area and `/proc`: none of
  `kernel/user/`, `kernel/process/`, `kernel/procfs/` is edited here. A
  cause found there is reported with its evidence and that item stops.
- Load on kasumi is bounded and stated: busy loops pinned with `taskset`
  to CPUs named in the script, the suite under `taskset` to the same
  CPUs, their pids recorded and ended by pid, each stretch as short as
  the count needs.
- None of the words the contract bars from pax. No trailer of any kind
  on a commit or the PR; no merge, tag, issue filed or closed; nothing
  under `~/.claude`; nothing installed; no build on nomad-1; no `/tmp`
  (scratch under `~/lanes/px41/` on every host); a job ended by its
  recorded pid only; another lane's CI run never cancelled; host ports
  8080 and 8088 never used.

## 2. Inputs (re-derived 2026-10-13)

| what | where | what it says |
|---|---|---|
| trunk | `7d2e9ba` (px40) | the base, as the contract says |
| pax#53 | run 38475501062 attempt 1, job 115565184433; artifact 11855625946 | `FAIL L1 release bios diff: lobo-session: no serial socket`, 10.2 s after the load session's last line. The session's own `steps.log`: `forwards: 55403->8081, 42365->8082, 50483->8083, 50041->8084, 50483->8090`: **one host port, 50483, given to two forwards.** `qemu.log` is not among the artifacts |
| pax#47 | run 38326787732 job 115067197334 (trunk `c86ba5e`); run 38334093289 attempt 1 job 115090172817 | both `release bios load`. First: files − 2 × threads at censuses 0–4 = −15 −16 −16 −15 −16 (R10 compares 1 and 3: `-16 -> -15`). Second: −16 −15 −16 −16 −16 (`-15 -> -16`). One open file more at some censuses, gone at the next; `tcp-inuse` 27 and `unix` 5 the same throughout |
| pax#45 | run 38297543688 attempt 1 job 114972170137; artifact 11779793892 | `FAIL K8 release uefi chord: 2 steps held [0, 4] ticks`. The timeline: tones at ticks 288, 292, 292, 295, 297, …; every other leg and the re-run: T, T+3, T+5, T+7, … So the second tone is one tick late, the third is on its usual tick (which is now the same tick), and everything after is as usual |
| CI since px25 | every `mpx4-lobo` and `mpx3-speaker` job log of the 200 newest runs dated 2026-10-12 or later (latest attempt), `~/lanes/px41/ci/harvest/` on nomad-1 | **K8**: 225 chord sessions: 219 `191 of 192`, 4 `192 of 192`, 2 `189 of 192` and FAIL (runs 38188215276 and 38322266282, both `release bios`, both `[0, 4]`, both `slots sound 990 …`): with the issue's that is **three K8 reds, one shape, all at the first step**. **Census**: 64 load sessions, 320 censuses: 313 at −16, **7 at −15, all on the release tier, in 4 sessions** (3 of 5, 2 of 5, 1, 1) |
| the method | `notes/px35-the-green-trunk.md`, `notes/px35/kasumi/scripts/` | 12 busy loops on four CPUs with the suite under `taskset` to the same four; counts kept; red N of M before, green M of M after |
| the tick and the sleep | `kernel/timer` (the 8254 at 99.998 Hz, counted per interrupt), `kernel/user`'s `sleep_until` (read only): a sleep ends at tick `ceil(target) + 1`, relative or absolute; a target not after now returns at once | so from code that runs right after a tick, a sleep is 0 ticks or at least 2 |
| `play` | `user/play/play.lu` `until(t)`: `now = time_now_ms(); if t > now { time_sleep_ms(t - now) }` | the schedule is absolute; the sleep asked of the kernel is relative to a clock read a moment before |
| the census | `user/lobo/steps/load.steps`: `loadwait`, `sleep 2`, `cat /proc/meminfo /proc/sys/fs/file-nr …`; `tools/lobo-check` R10: open files less two a lobo thread, the same at censuses 1 and 3 | the count is taken 2 s by the host's clock after the last reply |
| `tools/lobo-session` | `free_port()` binds port 0, reads the number, closes; called once a forward and once for COM1; then 200 tries 50 ms apart to connect to COM1, QEMU's exit never looked at | nothing keeps two calls from answering one port |
| kasumi | 16 CPUs, `/home` 33G free, load average 7–14 from other lanes before this lane ran anything | **there is no unloaded baseline here today**; "no added load" means that |

Drift, reported: the contract's line for pax#53 reads it as "QEMU did
not open its serial socket in 10 s", and the issue as "a slow QEMU start
on a loaded runner is the obvious reading". The artifact says otherwise
before any experiment (above). pax#45 says "once"; the logs hold three.

## 3. Prediction (committed before the first change)

**P1, pax#53 — a harness race, and not about time.** `free_port` gave
50483 twice; QEMU refuses a second `hostfwd` on a port it has just bound
and exits at once; lobo-session waits its 10 s for a socket that will
never open and names the wrong thing. Loading the host does not
reproduce it. Reproduced two ways: (a) counted: `free_port` called five
and six times in a row, a million rounds, on kasumi and on a runner: I
predict a repeat in about 10 of 28,232 rounds of five (0.035%) and 15 of
28,232 of six if the kernel picks evenly in `ip_local_port_range`
(32768–60999), which with CI's ~130 diff boots so far makes one sighting
unsurprising; (b) forced: a witness that hands lobo-session's QEMU
command a repeated port, red on trunk's tool with trunk's words. Fix:
the ports are picked while every earlier pick is still held, so they
differ by construction; COM1 needs no port of QEMU's: lobo-session
listens and QEMU connects, so there is no connect loop and no 10 s; a
QEMU that ends before the console is up fails the session at once with
QEMU's own last lines. Falsified by: QEMU starting with a repeated
forward; a repeat rate under a tenth of the predicted one.

**P2, pax#45 — the host's late tick, at the one place `play` is exposed
to it; the kernel is right.** `play` reads the clock, then asks for a
relative sleep. A tick that falls between the read and the kernel's own
reading makes the sleep a tick longer. The kernel's sleep always ends
the tick after its target, so `play` runs exactly one tick behind its
schedule, and a tone one tick late lands on the next tone's target:
that one is then started with no sleep, in the same tick. One late tick
therefore reads `[3 or 4, 0, 3]`, not K8's `[3, 1]`. The first step is
the exposed one: `play` is started by typing, at any phase of a tick,
and its first path from the clock read to the sleep is cold (pages not
yet touched, code not yet translated); every later step starts just
after a tick with a whole tick in hand. Numbers: on kasumi, short plays
in a loop in one boot, counting first steps that collapse: **about 1% of
plays with no added load (CI: 3 of ~230), over 5% under 12 loops on four
CPUs, and at least nine in ten of the collapses at the first step**.
Fix in `play`: sleep to the absolute target (`clock_nanosleep`,
`TIMER_ABSTIME`), which no tick between the read and the call can
lengthen; then 0 first-step collapses in at least 1,000 plays under the
same load. Falsified by: collapses spread evenly over the steps; a rate
the absolute sleep does not move. Not predicted to be needed: any change
to K8's words. If collapses remain in the middle of a tune under load
(the host holding the guest a whole tick between a wake and the tone),
their rate is reported and K8 is restated only on that count.

**P3, pax#47 — a guess, and the least sure.** The extra open file is one
lobo itself holds for a moment on its own clock (a descriptor a worker
closes late after the last connection, or a file the master opens on a
timer), and the census, taken 2 s by the host's clock after the last
reply, sometimes meets it: a clock wait where an event was wanted. It
is not a leak (the next census is back at −16). Only the release tier
shows it on CI. The discriminating observation is which record it is:
a scratch kernel prints the open-file table when `file-nr` is read, and
a steps file takes 20 censuses a boot. Numbers: no added load, 1–3% of
censuses at −15 on the release tier and none on native; under load,
over 10%. Falsified by: a record no descriptor names (then the kernel
holds it, and if that is in `kernel/user`, the process area or `/proc`
the item stops with the diagnosis); or `cat`'s or pelt's own record.
The fix follows the record: the census waits for the state it means to
count, or R10 counts what it means.

**P4, the soak.** The 10,000-echo soak's 180 s is a clock on a rate:
predicted to scale with the host's share, about 40 s on CI, and to pass
180 s only when the suite's CPUs are several times oversubscribed.
Measured under a ladder of loads before anything is said about the
bound.

**P5, the pipe shape.** `tests/mpx3-sound`'s `grep … | grep -qv` under
`pipefail` fails on a match when the left side is still writing; a
witness as px35's (a long input, the match early) shows it; the right
side reads to the end.

Proof per flake: the recipe and the red rate under a stated load, the
same count after the fix, then the suite by dispatch on CI.
