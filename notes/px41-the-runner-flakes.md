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
| CI since px25 | every `mpx4-lobo` and `mpx3-speaker` job log of the 200 newest runs dated 2026-10-12 or later (latest attempt), `~/lanes/px41/ci/harvest/` on nomad-1 | **K8**: 225 chord sessions: 219 `191 of 192`, 4 `192 of 192`, 2 `189 of 192` and FAIL (runs 38188215276 and 38322266282, both `release bios`, both `[0, 4]`, both `slots sound 990 …`): with the issue's that is **three K8 reds, one shape, all at the first step**. **Census**: 65 load sessions, 325 censuses: 318 at −16, **7 at −15, all on the release tier, in 4 sessions** (3 of 5, 2 of 5, 1, 1) (first written as 64 and 320; `notes/px41/ci/harvest.txt` is the count) |
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

## 4. What was found, flake by flake

Hosts. kasumi: Linux 7.2.8, QEMU 11.1.1 under TCG, 16 CPUs, wolf 0.2.28
by digest, programs built in `px13-ubuntu` with the container held to
CPUs 0–7. hasu: QEMU under KVM, no build. Trees on kasumi: `trunk` =
`7d2e9ba`; `w1` = `c142558` (play's absolute sleep; lobo-session's
start); `w2` = `17fb15e`; `w3` = `4b8b974`; `w6` = `188124b` (K9 as it
stands); `w4`, `w5` = `d1a9ff3` with the census's two tries. "Under
load" is px35's recipe: 12 busy loops pinned to four CPUs, the boot or
the suite under `taskset` to the same four (`notes/px41/kasumi/scripts/`).
**kasumi was never idle**: its load average was 2 to 14 from other lanes
before this lane ran anything and 20 to 50 while it did (two of this
lane's load sets at once on CPUs 8–11 and 12–15, and builds on 0–7), so
"no load added" is not an unloaded baseline, and several counts below
were taken on a host busier than their label says. Each
`conditions.txt` has `uptime` before and after.

### pax#53 — one port for two forwards; QEMU ended; nobody looked

**Cause (a harness race, not a slow QEMU).** `tools/lobo-session` asked
the kernel for a free port once a forward and once for COM1, closing
each socket before asking again, so nothing kept two answers apart. The
red run's own `steps.log` has 50483 for guest ports 8083 and 8090. QEMU
refuses the second forward (`Could not set up host forwarding rule`)
and ends with status 1 in 13 ms (`kasumi/portdup/result.txt`). The tool
never looked at QEMU: it tried to connect to COM1 for ten seconds and
said `no serial socket`.

**Reproduced by counting, not by load** (load has nothing to do with
it). A million rounds on kasumi: one port twice in 87 rounds of two
calls, 720 of five, **1,070 of six** (0.107%: the kernel hands out odd
ports only, so twice the even-handed guess of §3). On a CI runner
(Linux 6.17, the planted break below): **218 of 200,000 rounds of six**,
0.109%. A `diff` session takes six ports (five forwards and COM1), the
others two: about one `diff` boot in 930 dies this way, and each full
run makes two of them and a third on the Linux side with five.

**Fix.** The ports of a session are read from sockets all held until
the last is read, so they differ by construction; two forwards given
one port by hand are refused by name. COM1 needs no port of QEMU's any
more: the tool listens before QEMU starts and QEMU connects
(`-serial tcp:127.0.0.1:<port>`), so there is no connect loop and no
ten seconds; the wait is for the connection or for QEMU's end, and the
only clock is the session's own deadline. A QEMU that ends first fails
the session at once with its own last lines, and each session's
`qemu.log` is now kept by CI. The other suites that take two host
ports already refuse a pair that is equal (`pick_ports`).

**Seen red, then green.** `tests/lobo-session-selftest` (no guest; CI
runs it first in the mpx4-lobo job): W1 six ports all different over
200,000 rounds, W2 the real QEMU refusing a forward to a held port
(exit 2 in 0.1 s, QEMU's words), W3 a stand-in QEMU's console through
the listener, W4 a QEMU that never connects given up on at the
session's deadline, W5 a port given twice by hand. Against trunk's tool
all five FAIL (CI run 38484362350, each after 10.1 s with `no serial
socket`); with only the port picking put back to trunk's way W1 alone
FAILs, `218 with a port twice` (CI run 38485126730). Green: kasumi
(`w2/lobo-session-selftest.out`), and the whole suite through the new
console path on kasumi, 52 PASS, 15 boots (`suite-lines.txt`, w2).

### pax#45 — a tick between a clock reading and a relative sleep

**Three reds on CI, one shape.** The issue's (38297543688) and two more
found in the logs (38188215276, 38322266282): tone 1 one tick late,
tone 2 on its usual tick, which is now the same one: steps of 4, 0, 3
where every other boot has 3, 2, 2 (`ci/harvest.txt`). Always the first
step of the tune.

**Cause.** `play`'s schedule is absolute, but `until(t)` read the clock
and asked for a *relative* sleep of the difference. A tick that falls
between the reading and the kernel's own makes that sleep one tick
longer than the schedule. PAX's sleep ends on the tick after its target
(`kernel/user`'s `sleep_until`: `ceil(target) + 1`; right for a clock
that counts whole ticks, since a sleep is never shorter than asked), so
`play` always runs one tick behind its times, and a tone one tick late
starts exactly on the next tone's time: `play` then has nothing to
sleep and starts that one in the same tick. One late tick therefore
reads 3, 0, 3 (4, 0, 3 at a first step), not the 3, 1 that K8's "no
step off by more than one" was written to allow. The first step is
exposed because `play` is started by typing, at any phase of a tick,
with its path from the clock to the sleep still cold; every later step
starts just after a tick with a tick in hand. **The late tick is the
host's (or the phase's); the kernel's sleep is right as documented.**

**Reproduced** (`kasumi/chord-*`; 60 plays of a one-chord tune a boot in
a shell loop, the kernel's own timeline read from the halted machine;
first steps of 4, 0):

| play | load | release | native |
|---|---|---|---|
| trunk's | none added | **9 of 600** | 4 of 300 |
| trunk's | 12 loops on 4 CPUs | **45 of 600** (two of them 5, 0) | 27 of 300 |
| absolute sleep (`w1`) | none added (host at 30–39) | 1 of 600 | 0 of 300 |
| absolute sleep (`w1`) | 12 loops on 4 CPUs | **1 of 600** | 0 of 300 |

Typed, one play a line, 200 a boot, which is how the suite starts its
chord: trunk's 3 of 1,000, the absolute sleep 0 of 1,000. Under KVM on
hasu neither shows it (0 of 600 and 0 of 600): the cold path is too
short there. Prediction P2's numbers held (about 1% and over 5%); of
the 54 plays under load that were not the usual shape, 45 were at the
first step (P2 said nine in ten).

**Fix in `play`** (`44d784e`): `until` sleeps to the absolute time
(`clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME)` from `kd.S`, with the
clock read there too), which no tick between a reading and a call can
lengthen. wolf's prelude has only a relative sleep.

**What is left is the host's, and K8 could not allow it.** With the
sleep absolute a late tone needs the host to hold the guest a whole
tick between a wake and the tone. It happens under load: 1 first step
of 600 above, and the suite itself at `w2` on kasumi at a load average
of 23 to 35: **K8 red on 2 of 4 legs with the fixed play** (`w2/k8-red/`,
`suite-lines.txt`): native UEFI steps 195–197 held 3, 0, 3 (one late
tick), release UEFI steps of 4 and 0 (two ticks late) with the capture
15% long. So K8 is **restated with that run beside it**
(`tools/arp-check`, `d2e7e04`): every tone of a chord within one tick
of its place, the places being the ticks the chord's spacing gives.
One late tick passes, as the old words meant it to; a tone two ticks
late still fails (the release UEFI leg of that run does), 90% of the
steps must still be exact, the tones must still be the file's count
for count, and each slot must still sound its time within a tick. Under
the new rule the three CI reds would have passed; under the old one,
with the fixed play, CI's 225 chord sessions held no late tick after
the first step (0 of some 43,000 steps), so the restatement is for the
loaded host, not for CI as measured.

**K9, and a prediction that was wrong.** To hold `play` to the fix I
first added a session of 60, then 200, plays in a shell loop with "at
most one begins a tick late". With trunk's `play` put back it **passed
on CI** (run 38491453315: 800 plays, none late): in a loop each play
starts at a fixed time after the last one's final tick, so the phase
is one value a boot, not 200 (kasumi's own boots had shown it: 4 of 60
in one, 0 of 60 in the next). That session is gone. K9 is now
deterministic and needs no boot: `play` plays the chord study on the
build host under `strace` with its KIOCSOUND answered 0, and every one
of its 202 sleeps must be `clock_nanosleep(CLOCK_MONOTONIC,
TIMER_ABSTIME)` to times that never go back, none relative, the tones
the file's 197. trunk's `play`: 0 absolute, 202 relative
(`kasumi` by hand; the planted break in CI is in the PR body).

### pax#47 — the census counted the shell's own socket

**Cause (the test's instrument, not the kernel).** The census was
`cat /proc/meminfo /proc/sys/fs/file-nr …` typed at pelt. To start a
program pelt makes `socketpair(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC)`,
forks, and closes its own end only after the child's `execve` has
closed the other (`kasumi/strace/pelt-spawn.txt`, on Linux). On PAX's
one CPU pelt runs again when `cat` is preempted or waits, and whether
that comes before `cat` opens its second file is settled by where the
tick falls and how fast the host is. When `cat` won, `file-nr` counted
pelt's end: one open file more. R10 compares censuses 1 and 3 and
failed when they fell on different sides.

**The discriminating observation** came from CI, not kasumi. A scratch
kernel that prints the open-file table at every open of a `/proc` file
(`kasumi/scripts/inst-files.diff`, never committed; branch
`px41-probe-47`, runs 38486682897 and 38486693292: the load session six
times each, release BIOS): in **4 of 60 censuses** the table at `cat`'s
first open held one record more than at its next eight, and each time
it was kind 7, an end of a socket pair, one reference
(`ci/probe47/`). The table printed at the first open delays the second,
which is why the probe's own `file-nr` never caught it.

**Reproduced.** On kasumi under TCG, not at all: 0 of 250 censuses with
trunk's census (the scratch kernel for 154 of them; no load added, a sweep of 0 to 6 s after the round, 30 s
rounds, and four loops on the session's four CPUs; under 12 loops the
boot did not reach its prompt in 120 s): the host was too slow today
for `cat` to win. Under KVM on hasu, where `cat` always wins: **29 of
30 censuses one over and one two over** with trunk's census
(`hasu/hasu-census-cat-kvm`). On CI: 7 of 325 censuses, all release
tier (`ci/harvest.txt`), R10 red when 1 and 3 differed.

**Fix** (`f729733`): the shell reads `file-nr` itself
(`read fn < /proc/sys/fs/file-nr; echo "$fn"`), first, and the rest
stays one `cat`. The shell's own read starts no program, so no such
socket is open when the count is made: the count waits on nothing and
races nothing. hasu under KVM: **30 of 30 at −16** (`hasu-census-read2-kvm`);
kasumi: the load session three times, R10 and R13 PASS on both sides
(`w5`). A first try that split the `cat` in two around the shell's read
(`w4`) made R10's *frames* move, three runs of three: the shell's heap
grew 124 kB between the two readings at census 1. Frames free and
every process's pages must be read with the shell asleep; they still
are.

Not in px39's files: nothing in `kernel/` changed for this.

### The soak's deadline (px35's note)

`tests/mpx4-net`'s boot has 180 s, and its 10,000-echo soak is a
ping-pong: one echo, one reply. On CI the soak takes **0.29 to 1.55 s**
(74 soaks in 13 runs, `ci/harvest.txt`), not the 40 s px35's note
gives. On kasumi (`w2/soak.txt`, native BIOS, the suite and the loops
on CPUs 12–15):

| busy loops on the 4 CPUs | soak (net, modern) | suite |
|---|---|---|
| 0 | 0.71 s, 0.71 s | 23 s, 32 PASS |
| 4 | 1.23 s, 1.68 s | 45 s, 32 PASS |
| 8 | 45 s, 42 s | 326 s, 32 PASS |
| 12 | neither done in 180 s | 551 s, 22 PASS, 15 FAIL (N6, N9 and what follows them) |

px35's note is verified (12 loops on the suite's four CPUs miss the
deadline) and its reading corrected: it is a cliff, not a slope. Once
every CPU has more than one hog, each of the 20,000 wake-ups waits for
a slice of the host's scheduler, and the rate falls from thousands of
echoes a second to hundreds. That is the host's wake-up latency (an
inference from the shape; not traced), the same on trunk's kernel and
px35's. The bound is a watchdog a hundred times CI's slowest soak; it
is not raised, and no change is made.

### The pipe shape left in `tests/mpx3-sound`

`grep -E '^cost ' file | grep -qv ' 0 clamped$' && why+=…` under
pipefail: when the second grep finds a clamped line it leaves, the
first dies of SIGPIPE on its next write, the pipe is false, and the
clamping is **passed over** (the opposite of a flake: a failure
hidden). `kasumi/pipeshape/result.txt`, the first line clamped: 20,000
lines, called clean 50 times of 50; 200 lines, once in 300; today's
three lines, never in 300. Fixed (`c31da2e`): one grep that reads to
the end. The same shape with `readelf … | grep -q` stands in the
suites' `static_ok`; its input is one short write and it is not
changed here (§6).

## 5. Evidence index

- CI logs and artifacts read: `notes/px41/ci/harvest.txt` (how:
  `harvest.sh`), the reds' artifacts 11855625946 (pax#53), 11779793892
  (pax#45), 11784224298 (pax#47).
- kasumi: `notes/px41/kasumi/` — `portdup/`, `chord-*` (`lines.txt` a
  boot, `counts.txt` the shapes, `conditions.txt` the load),
  `census-*`, `strace/`, `pipeshape/`, `w*/summary.txt`,
  `suite-lines.txt` (every K8, K9, R10 and FAIL line of each suite
  run), `w2/k8-red/` (the two timelines), `w2/soak.txt`, `scripts/`.
- hasu (KVM): `notes/px41/hasu/`.
- The probe: `notes/px41/ci/probe47/run-{1,2}.txt` (`dumps.py`).
- The planted breaks and the CI runs at the head: the PR body.

## 6. Not verified, and inferred

- **pax#47 on kasumi under TCG**: never red there. The cause rests on
  the probe's four tables on CI, the strace of pelt on Linux, and KVM's
  29 of 30; that CI's seven were this record is inferred (the probe
  saw the record at `cat`'s first open, not in an unpatched kernel's
  `file-nr`).
- **One census of 30 under KVM was two over** (the first of a boot).
  The second record was not identified; the shell's own read has not
  shown it in 60 censuses.
- **How wide the window is on a runner**: CI's 3 of about 230 is three
  events. Under KVM the old `play` did not fail in 600 plays.
- A shape under load that the arithmetic does not explain: a play whose
  tones stay one tick late with no step of 0 (`2 3 2 2 …`, once in 600,
  trunk's play). Possibly a tick pending while a system call ran; not
  chased.
- K8 on a host loaded as kasumi was still fails when a tone is two
  ticks late or the capture runs long; nothing here changes that.
- `static_ok`'s `readelf … | grep -q` in eleven suites: not measured
  under load, not changed.
- The 8 kB R10 allows the kernel's frames is, by the probe, the same
  socket pair's two buffers at `cat`'s first open as often as "the
  census's own read of /proc"; the allowance is not changed.

## 7. Done-when

In the PR body: the commits, the CI runs, the audit.

- To close when this merges: pax#53, pax#45, pax#47.

## 8. The rebase, and the shas named again

The branch was rebased once, onto `d3f4aa9` (px39 merged; one conflict,
`docs/SOURCES.md`, where both lanes had added a section: both kept).
px39 changed `kernel/user`, `kernel/process`, `kernel/procfs` and three
lines of `kernel/files`; `sleep_until`'s `ceil(target) + 1` is as it
was, and none of this lane's files moved under it. The trees kasumi and
hasu ran were cut before the rebase (branch `px41-prerebase`, head
`2de1866`); each is the same change as the commit beside it:

| what | as the hosts ran it | on the branch now |
|---|---|---|
| the prediction | `b5f9534` | `a36de33` |
| tests/lobo-session-selftest, red | `55c0265` | `43ab257` |
| tools/lobo-session, the fix | `d64f0e4` | `f2580f5` |
| CI keeps `qemu.log` | `a8593dd` | `db9df5d` |
| play's absolute sleep | `61016b4` | `44d784e` |
| tests/mpx3-sound's pipe (`w1` = `c142558`) | `c142558` | `c31da2e` |
| K9 as a session of 60 (`w2` = `17fb15e`) | `17fb15e` | `a3a8c4f` |
| K8's place rule | `0c024bd` | `d2e7e04` |
| K9 as 200 plays (`w3` = `4b8b974`) | `4b8b974` | `7b950fb` |
| the census by the shell (`w4`, `w5` = `d1a9ff3` and this file) | `ee38206` | `f729733` |
| K9 under strace (`w6` = `188124b`) | `188124b` | `44a9330` |

The suites at the rebased head on kasumi, and the CI runs: the PR body.
