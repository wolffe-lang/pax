# px131, the second part — the clocks from the clock, and device-driven wake-ups at once

The first part (`notes/px131-long-kernel-paths.md`) measured how long the kernel holds the processor and proposed a
general rule in an order. Its bound, its second proposal (the clocks counted from the clock) and its third (the
network's and the keyboard's wake-ups run at once) were taken, and this part builds the last two, each seen red first
under the guard.

- **The clocks.** A tick due while interrupts were off waited in the APIC and every further one in the same stretch was
  lost, so CLOCK_MONOTONIC, CLOCK_REALTIME and every sleep and timeout counted in ticks stood still through a long call:
  beside 64 KiB console writes both clocks kept 7 % of the time-stamp counter's time, beside 64 MiB file writes 31 to
  40 %. Now the tick count follows `kernel/clock` (the HPET, else the ACPI PM timer, the counter the tick is calibrated
  against): both clocks
  keep the counter's time within 0.7 %, and a long call makes a deadline late by at most the call, never wrong. This
  closes pax#384 (the wall clock stood still on the real machine during a console flood), and the console's lane's
  recommendation of the same.
- **The wake-ups.** A host's ping beside a process that only computes waited a quantum a hop: 27 to 30 ms in the median,
  37 to 40 ms at the 99th percentile, against under 1.5 ms at idle. Now the network thread, the readers it wakes and
  the console's readers go to the head of the queue and run at once: 0.72 to 0.75 ms in the median and 1.9 to 2.0 ms at the 99th percentile, 1.40 to 1.45 times idle's.
- **The risk named:** under a ping flood every frame takes the processor from the hog, and how much depends on the
  flood's rate, which the host's CPUs set. On the native tier the hog kept 0.92 to 0.96 of its share at 8,300 to 11,100
  answered pings a second, 0.61 to 0.85 at 17,000 to 32,600 (two host CPUs), and 0.29 to 0.45 at 50,000 to 55,000 (six),
  where a 1 ms sleeper waited up to 1.42 s. L6 now holds the hog to half its share at an offered 4,000 datagrams a second
  and prints the saturating flood's curve on every boot; the native kernel under the saturating flood is its own work
  (section 4), and the urgent mark is not its lever.

**Rebased with the first part onto trunk `bbe91e16`** (the console's lane's drawing). The commits this note names
are those of `px131-clocks-wake3` (`be83835c`), replayed unchanged; the records before the rebase are for that code.
At the rebased head the guard holds on BIOS at 1 GiB under KVM (record sha256
`e3b269fe68e9815337fee1d33de9d1a68f6b7db364ceb38217a33ba6cc4ff090`, at `fcad7eef`): both clocks 0.992 and 0.994 of
the counter's time beside console and file writes, the ping beside `spin` 1.42 times idle's, and the hog under the flood
0.61 of its share (0.81 to 0.90 before the rebase, with 80,561 pings in the window against 98,000 to 129,000: one boot;
the head's take says more). The console's write with COM1 is as before (1.17 s for 64 KiB), so L4's load is unchanged.

**Restacked on the first part's fix for clef** (its entry paths call the latency close through a word, so the assembly
needs no `.weak`, which clef does not take): the same commits replayed unchanged once more, `px131b-clocks-wake`
(`a56d9948`) the code before it. On top, the delivered-tick count moves from a module variable to a word with a stable
name, `boot/isr.S`'s `pax_tick_delivered` beside `pax_tick_count`, and the USB session reads it by that name (section 3).
The first part merged as it stood (trunk `4007eaa0`), so these commits sit on trunk unchanged.

**A host too stalled to measure.** The restacked head's one take ran the USB session in a light slot beside heavy jobs:
32 of the hold's 32 intervals spanned ticks the guest lost (17 losses in the hold), and the session refused, `repeat
unmeasured`. That is the session doing its job (it neither passed nor failed the kernel on stamps it could not
trust), but a record cannot tell it from a failing kernel when both are exit 1. So `repeat unmeasured` is now its own
verdict: the session is held again, each time a fresh boot, at most three holds in all, each printed (`NOTE USB …
(hold N of 3)`) and listed in `OUTPUT/holds.txt`; a measured result, a pass or a failure, is final at once and never
held again; three unmeasured holds are a red under their own name, `FAIL R-unmeasured FIRMWARE-TOPOLOGY: the host
stalled the guest past measuring the repeat in 3 of 3 holds`, exit 3 (a failing kernel's is 1). U15 to U18 hold it.
The take that measures the repeat runs on a whole block, never in a light slot.

Footprint: cross-cutting (`kernel/timer`, `kernel/sched`, `kernel/latency`, `kernel/xhci`, `kernel/kmain_console.lu`,
`boot/isr.S`'s `pax_tick_delivered`;
`tests/mpx6-latency` and its probe and host side gain the clock, wake-up and flood rows).

## 1. Forbidden, and what was read

No kernel's source. Read: the Intel SDM vol. 3A on the local APIC timer and interrupt priority (a pending interrupt
of one vector is held, further ones at the same vector are lost), the IA-PC HPET specification, POSIX's
`clock_gettime`, `nanosleep` and `poll` (a timeout is a minimum, and lateness is allowed), QEMU's documentation of
`-mem-prealloc` and `-netdev user`. Linux was not run for this part: the first part's column stands.

## 2. The prediction, scored

Committed first (`73357a24`, `notes/px131/prediction-2.txt`), before the rows and any change:

- **C1** (the clocks count delivered ticks and stand still through a stretch): held.
- **C2** (beside console writes the clocks keep about 8 %, beside file writes about a quarter; a 2 % bound red by more
  than tenfold): held for the console (7.1 and 7.3 %), partly for the file write (31 to 40 %, more than a quarter);
  red by 30 to 47 times the bound.
- **C3** (the count follows the clock; both clocks within one tick): held, 0.3 to 0.7 % over windows of 3.2 to 3.7 s
  (a tick or two of 10 ms).
- **W1** (a ping beside a hog waits a quantum a hop: p50 about 27 ms, p99 about 36; red by about tenfold): the figures
  held (p50 27 to 30 ms, p99 37 to 40); the ratio was 26 to 30 times, not ten.
- **W2** (the fix: within three times idle's p99): held: p50 0.70 to 0.75 ms, p99 1.40 to 1.45 times idle's.
- **W3** (under a flood the hog keeps well over half its share): held: the hog kept 82 to 85 % of its share under 33,000 pings a second (before the change: 100 %, under the 3,000 a second the old wake-ups let through).
- **W4** (the loopback echo between two processes stays a quantum a hop beside the hog): partly wrong: the loopback echo beside `spin` went from 55 to 25 ms in the median (idle: 15 ms), because loopback's frames are delivered by the network thread too and its readers are woken from it; the hop left is the sender's own wake-up, a quantum.

## 3. The clocks

**Before.** `kernel/timer`'s count rose by one for each tick interrupt delivered. `kernel/user` reads CLOCK_MONOTONIC as
ticks times 10 ms and CLOCK_REALTIME as the RTC's time at boot plus the same; `kernel/sched`'s sleeps, `kernel/ready`'s
poll and epoll, `kernel/socket`'s receive timeouts, `kernel/futex`, `kernel/tcp`, `kernel/arp`, `kernel/dhcp` and
`kernel/xhci` count their deadlines in ticks. A stretch with interrupts off longer than a tick delivers one tick, so
every one of them stood still for the stretch less 10 ms.

**Now.** With `timer.follow_clock()` (called by `kmain_console`, the kernel the images ship), each delivered tick sets
the count to the larger of itself plus one and the ticks `kernel/clock` says are due since the tick was armed. The
clock is read at every tick already (it samples its wrapping counters there), so this costs a division. Every
deadline above is then a deadline in real time at the tick's resolution: a long call makes a sleep, a poll's timeout or
a retransmission late by at most the call, and both clocks keep the clock's time. The interrupts themselves are counted
apart (`timer.delivered`): the timer's own drift report and the instrument's lost ticks read that. The test kernels
(`kmain_timer`, `kmain_sched`, `kmain_metal`, which fakes its clock's readings for its rows) count interrupts as before.

**A deadline after a stretch.** A wait that looked at its deadline before its event could now time out after a long
stretch although its event came during it. Every wait in the tree was read for it: the system calls (`poll`, `epoll`,
a receive, a futex) look at their event first each time they run again, `kernel/sched`'s sleepers are woken by the
deadline itself, and TCP's, ARP's and DHCP's timers are deadlines. Two loops looked first at the deadline: `kernel/xhci`'s
command and control-transfer waits, where a timeout quarantines the controller. They look at the completion first now.

**A harness that leaned on lost ticks: the USB keyboard's repeat.** `tools/usb-session` holds `a` for 100 of the
guest's ticks and judges the repeat from the probe's CLOCK_MONOTONIC stamps (`user/elf/usbkeys.c`): a 250 ms delay
(220 to 320), then a 33 ms period (median 20 to 45, mean 31 to 37). Its own note said why it read the guest's ticks:
a stalled vCPU loses ticks while the host's clock runs on, and the repeat, the poll timeout and CLOCK_MONOTONIC all
counted those ticks, so a stall cost the stamps nothing. With the count following the clock, a stall's lost ticks
come back as a jump, and the stamps show the stall. Measured on the build host, the same session at each part's head:

- **five boots each, the session as it stands:** the first part's stamps were the same in all five (250 ms, then 30
  and 40 ms, mean 33.2); this part's in three, one tick early in one (240 ms), and uneven in one (280 ms, then 10 to
  50 ms, mean 32.2, inside the bounds); the head's take met one worse (300 ms, median 50 ms, mean 42.4).
- **four boots each, the hold's polls logged** (the count and the interrupts taken, from an instrumented copy of the
  session): the first part's count never stood still for more than 12 to 23 ms; in one of this part's boots the
  host's own polls came 57 ms apart, the guest took 3 interrupts where 6 were due, the count caught them up at the next
  one, and the intervals around it were 50 and 20 ms; the other three were as the first part's.
- **CI's runners** (the same suite, one run each): the first part's root session took 1.257 s of wall clock for its
  100 ticks (about 26 ticks lost), with stamps as even as ever; this part's had two stalls at the hold's end, intervals
  of 140 and 130 ms, mean 44.2 ms, and failed.

So the kernel's repeat did not change; what changed is what the stamps can hide. At a real keyboard nothing moves
while interrupts stay on: 250 ms, then 30 and 40 ms in turn. After a stretch with interrupts off (a 64 KiB console
write at the screen is 120 ms), the reports due inside it are dropped, as before (never a burst), and the next comes
on the clock's schedule rather than as if no time had passed: a tick's difference at most. The session now holds for
the interrupts the guest took (`boot/isr.S`'s `pax_tick_delivered`, written by `kernel/timer` and read as the tick
count is), so a stall lengthens the hold as
it used to, and leaves out of the period's figures every interval that spans ticks the guest lost (the probe prints
its first read's time, `USBT0`, to place the stamps on the ticks); at least 8 intervals must be left
(`tests/usb-session-selftest` U10 to U13: CI's failing stamps are refused without the losses and pass with them; U14:
the hold reads the word by its name). `repeat.txt` says which word the hold counted (`hold_counts`) and the verdict
(`verdict measured` or `verdict unmeasured`, with the hold's number).

**What it does not do.** The resolution stays a tick (10 ms): reading CLOCK_MONOTONIC from `kernel/clock`'s nanoseconds
directly is a later choice (decision 14). A clock counter that wraps inside one stretch loses its wraps: `kernel/clock`
reads the HPET where there is one (32 or 64 bits), else the ACPI PM timer (24 bits wrap after 4.7 s, longer than any
stretch the first part measured once its three fixes landed), else the PIT, whose 54.9 ms wrap any long call outlasts:
on a machine with neither of the others the clocks still lose time through a stretch, as before. CLOCK_REALTIME still starts from the RTC with no NTP: it now keeps the clock's rate, not the world's.

## 4. The wake-ups

**Before.** The device's interrupt queued the network thread at the tail; a switch happened only from idle or when the
running thread's two-tick quantum ran out; the thread's deliveries queued their readers at the tail again. Beside one
process that only computes, a ping's round trip was a quantum a hop.

**Now** (`kernel/sched`). `wake_urgent` puts a thread a device's work woke at the head of the queue and marks it:
`wake_net` (the network thread, by its device's interrupt), `wake_input` (a reader of the console, by a key) and
`wake_pipes` when the network thread calls it (the readers its deliveries wake; `block_net` names that thread). `kick`,
after a device's interrupt, and `preempt`, at the tick, switch to an urgent head at once when the running thread is not
urgent itself; the running thread goes to the tail as a preempted one does. An interrupt reaches `kick` only where it
was taken, so with IF set: in ring 3, or in a kernel thread outside its locks, where the tick could have preempted
already. A thread keeps its mark while it runs and loses it when it leaves the processor, so an urgent thread is not
taken off the processor for another urgent one.

**The risk: a flood.** Each frame now preempts a hog. The first form of the flood row ran `flood`, the hog's loop,
while the host sent pings as fast as the guest answered (16 in flight), and held the hog to half of its share beside
`spin`. Every take of it ran in a light slot of two host CPUs, where the hog kept 0.61 to 0.96 of its share; the first
take on a whole block (six host CPUs) failed it on every native boot. A flood as fast as the guest answers runs as
fast as the host can send, so the row measured the host as much as the kernel:

| host CPUs | tier | answered pings a second (over the window's real length) | the hog's share | the 1 ms sleeper's worst |
|---|---|---|---|---|
| 2 | native, wake-ups not urgent (the plants) | 3,500 to 7,700 | 0.94 to 1.00 | 29 to 37 ms |
| 2 | native | 8,300 to 11,100 | 0.92 to 0.96 | 31 to 50 ms |
| 2 | native | 17,200 to 32,600 | 0.61 to 0.85 | 22 to 51 ms |
| 2 | release | 39,500 to 74,500 | 0.89 to 0.98 | 20 to 26 ms |
| 6 | native, wake-ups not urgent (the plant) | 53,100 | 0.29 | 338 ms |
| 6 | native | 50,400 to 55,000 | 0.35 to 0.45 | 503 to 1,419 ms |
| 6 | release | 128,000 to 137,000 | 0.94 to 0.95 | 21 to 22 ms |

(35 rows of the second part's records under KVM; the same kernel and probe gave the two- and six-CPU rows of the head
before the offered flood, `a33caad0` and `a7a69460`.)

The same kernel, probe and host side, then measured in one block held whole, alternating six CPUs (6 to 11) and two
(6 and 7) for the guest and its host side, five boots of each, both firmwares, 1 GiB, at `a7a69460` (the host's load
average 4.4 to 5.6 and the package at 64 to 70 C before each boot):

| host CPUs | boots | answered a second | the hog's share | the sleeper's worst | L6 at half |
|---|---|---|---|---|---|
| 6 | 10 | 21,800 to 62,600 (median 46,600) | 0.21 to 0.78 (median 0.47) | 211 to 658 ms | 4 of 10 |
| 2 | 10 | 7,800 to 25,000 (median 15,200) | 0.61 to 0.96 (median 0.81) | 34 to 110 ms | 10 of 10 |

Within each set the share falls as the rate rises: the one six-CPU boot that held both firmwares (the fourth) ran the
slowest floods of its set, 21,800 and 35,300 a second, and kept 0.78 and 0.61; the six-CPU low, 0.21, came with its
fastest, 62,600. The same boots' L2 host pings: 30 rows on six CPUs, median 0.91 of `spin`'s, at most 1.82; 30 on two,
median 1.27, at most 2.00 (`spin`'s worst 1.8 to 3.7 ms); none over three times `spin`'s, so none near the floor.
The offered flood, on a light slot of two CPUs beside heavy jobs (block C's, three boots at `28344b2f`, both firmwares):
offered 3,999 to 4,001 a second in all six, the hog at 0.99 of its share; the saturating flood beside it answered 26,000
to 29,000 a second, the hog at 0.63 to 0.75. The share the hog loses over the answered rate is the guest's
cost a frame: 5 to 16 us on the native tier (11 to 13 us at six CPUs), 0.3 to 0.7 us on the release tier (one older
take 2.7 us). So a stream of about 50,000 frames a second takes over half of the native kernel's processor; a real
network device can deliver more than QEMU's user network does.

**The urgent mark is not the lever.** A budget was sketched here before: a thread loses its urgent mark when urgent work
has had more than half of the current tick. The plant (device wake-ups not marked urgent, the quantum's wait back) kept
the hog at 0.29 under the six-CPU flood, no better than the head. Under a flood that keeps the network thread busy the
thread is always runnable and every frame's interrupt is taken whoever runs, so taking the mark away would not hold the
hog at half. What would: a budget on the network thread's own work a tick, or fewer interrupts a frame (polling the
device's ring while frames keep coming, its interrupt re-armed when the ring is empty); and the native tier's cost a
frame is the other half. That is its own work, pax#408 (decision 17).

**L6 now** holds the hog to half its share at a flood the host offers at a fixed rate, 4,000 datagrams a second, each on
its own schedule whatever the answers (`flood:4000`; decision 21). Every take so far answered at least 8,300 a second on
two CPUs beside heavy jobs, so any slot offers 4,000 with room; the native kernel's hog keeps about 0.95 there. The
saturating flood stays on every boot as `~L6`, bounded by nothing: its answered rate, the hog's share and the sleeper's
worst, so the curve above goes on in every record.

**What it does not do** (prediction W4). Two processes that talk over a pipe or loopback still wait behind a hog's
quantum a hop: their wake-ups are not a device's. The next step (the first part's section 10) is a woken thread ahead
of a preempted one, with the same kind of budget. And a long call still holds everything: the first part's proposals
from the fourth on are for that.

## 5. The rows

`tests/mpx6-latency` gains three rows and a curve; its guard run adds the offered flood (`flood:4000`) and the
saturating one (`flood`) to `idle` and `spin`.

- **L4 the clocks:** over each clocked load's window (the console's write of 64 KiB, a file write of MiB/16), the time
  CLOCK_MONOTONIC and CLOCK_REALTIME say passed, each within 2 % of the time-stamp counter's. Under TCG too.
- **L5 the network's wake-ups:** beside `spin`, the host's ping's p99 at most three times its p99 at `idle`. KVM only.
- **L6 a hog under an offered ping flood:** the host offers 4,000 datagrams a second; the hog's ops (1 ms of CPU each)
  at least half of `spin`'s, the offered and answered rates printed. A host that offered under 90 % of the rate is
  unmeasured, neither a pass nor a failure: that boot's L6 is held again, a fresh boot of `spin` and the offered flood,
  at most three holds, each printed; a measured result is final at once; three unmeasured holds are
  `FAIL L6-unmeasured`, a red under its own name, and the suite exits 3 when that is its only red. KVM only.
- **~L6 the saturating flood:** as fast as the guest answers; its rate, the hog's share and the sleeper's worst, bounded
  by nothing, on both tiers.
- **L2's host ping** (the first part's row): within the larger of three times `spin`'s worst and `spin`'s worst plus
  10 ms, the 10 ms being the bound's own figure for anything (decision 22), with the instrument's longest
  interrupts-off stretch printed beside it. Since device wake-ups run at once `spin`'s worst ping is 1.5 to 6.5 ms, and
  three times that is within a host's own stall: the first six-CPU take failed it once, 7,575 us beside munmap of a
  hole over 2,453 us beside `spin` (3.09 times), with interrupts off at most 1.9 ms in that window.
- **S0:** `tests/mpx6-latency.d/rows-selftest`, first: the floor's arithmetic, the offered rate, unmeasured and its holds.

And the guest's memory is backed before it boots (`-mem-prealloc`, found here and moved into the first part,
`1e5d8fd6`): a first touch of a guest frame otherwise costs the host a page fault, and a fork's, an mmap's or an exit's
frames showed those as stretches of 30 to 150 ms now and then, on trunk's kernel as on this one; with the network's
wake-ups at once, `spin`'s worst ping fell to a few milliseconds and such a stretch alone could fail L2.

Under KVM at 1 GiB, BIOS and UEFI (and BIOS at 2 GiB), red at the rows' commit and green with the fixes and the backed
memory. Both records were taken before this part was replayed onto the first part's later commits (a link fix, the
backed memory): at `736f0830` and `96986862`, kept as `px131-clocks-wake-before-rebase`; the green record's sha256
`f394c8f7385ff802038c6a22aead9831532bad065a30fff66f670f7c0c595af7`:

| row | before | after |
|---|---|---|
| L4 the clocks over a window of 64 KiB console writes, of the counter's time | 0.071 (BIOS), 0.073 (UEFI) | 0.994, 0.994; 0.993 at 2 GiB |
| L4 the same over 64 MiB file writes (128 MiB at 2 GiB) | 0.399, 0.309 | 0.993, 0.995; 0.994 |
| L5 the host's ping beside `spin`, p50 / p99, and p99 over idle's | 29.9 / 40.1 ms, 29.6 times; 27.1 / 37.1 ms, 26.3 times | 0.75 / 1.91 ms, 1.45 times; 0.72 / 1.90 ms, 1.40 times; 0.70 / 1.97 ms, 1.45 times |
| L6 `flood`'s ops over `spin`'s; the pings in its window | 1.00, 8,036; 1.00, 9,337 | 0.85, 103,219; 0.82, 99,058; 0.85, 102,725 |
| the loopback echo beside `spin`, p50 (idle: 15 ms) | 55 ms | 25 ms |
| L2, the first part's three guarded loads over `spin` | 0.94 to 1.06 | 0.68 to 1.73 (`spin`'s worst ping is now 3.7 to 4.0 ms, not 41 to 42) |

Under TCG (CI's leg) L4 holds (0.997, 0.995) and L5 and L6 are printed and SKIPPED by name (1.18 and 0.62).

**A correction to the first part's table.** With the guest's memory backed, the calls that fill fresh frames hold
interrupts off for less than that table says, because part of what it measured was the host's page faults: a 64 MiB
file write 60 ms (the first part's takes: 113 to 359 ms), fork of 128 MiB 43 to 77 ms (40 to 115). The console's write
is not of that kind (1.15 s for 64 KiB with COM1 in these takes; each byte's port accesses leave the guest, and their
cost follows the host's load). The ranking stands; the file write's place is lower.

## 6. Fit for an image, and what to try at the machine

The head is fit for an image. The clocks change only where a stretch was long (they then keep time, where they stood
still); a device's wake-up changes only the order in which ready threads run. At the machine:

- **The wall clock** (pax#384): note `date` and a phone's clock, flood the console for a minute (`yes` at the console,
  then Ctrl-C), and look again: before, the machine's clock fell behind by most of the minute; now it keeps the phone's
  to the second.
- **A ping beside a hog:** from another machine `ping <machine>` while, over ssh, `while :; do :; done` runs: before,
  about 27 ms a reply; now about 1 ms, as at idle. The ssh session's echo improves by the device's and the network
  thread's hops only: the shell behind the pty still waits a hog's quantum (section 4).

## 7. Evidence index

| what | where | result |
|---|---|---|
| the prediction | `73357a24` | before the rows |
| the rows: the probe's clocks and `flood`, the host's flood, L4 to L6 | `f5a02ace`, `08109412`, `e2709ab5`; the rig `d29d7121` | |
| **red at the rows' commit** | `notes/px131/rig/red-2.manifest` at `736f0830` (before the replay; `d29d7121` after it): the first part's kernel, a light take, record sha256 `106be51c03ef7b2675231122ccc2919065663c08be1a7db52927b97e9a155805` | `FAIL L4 native-bios-1024 console:65536` (both clocks 0.071 of the counter's time), `FAIL L4 … write:64` (0.399), `FAIL L5 native-bios-1024` (the ping beside `spin` p99 40,147 us, at idle 1,357: 29.59 times), and the same three on UEFI (0.073, 0.309, 26.30 times); L6 held (1.00); `END latency exit=1 secs=93` |
| the clocks | `6d30b0ff`, `68a8ca9b`, `ccffc6b2`, `490cc70d` | |
| the wake-ups | `b03a6d12`, `3b68baee` | |
| the guest's memory backed | `1e5d8fd6` (the first part's) | |
| green at `96986862` (before the replay), the guard and the scheduler | `notes/px131/rig/green-2a.manifest`, a light take, sha256 `f394c8f7385ff802038c6a22aead9831532bad065a30fff66f670f7c0c595af7` | section 5's table; `END ci-plan exit=0 secs=111`, `END latency exit=0 secs=88`, `END latency-2g exit=0 secs=45`, `END latency-tcg exit=0 secs=50`, `END sched exit=0 secs=17`, `END interrupts exit=0 secs=41` |
| the delivered count by name | `tests/usb-session-selftest` U14 at `ec9c38a8`, red there; `d65baee7`, `b3ee7a36`, `b77b7548` | `FAIL U14: boot/isr.S lacks '.globl pax_tick_delivered'`, then `PASS U14` |
| unmeasured, its own verdict | `tests/usb-session-selftest` U15 to U18 at `4bedc6b5`, red there; `7b0ebdef` | `FAIL U15: tools/usb-session has no Unmeasured verdict …`, then `PASS U15` to `PASS U18` |
| the flood's rate is the host's | the six-CPU take at `a7a69460`, record sha256 `9e2e7499a73c0890fc161467af113921d242a1f902e1f6bf5667afdb53795bb8`, and its plant `5b8047f2`, `23471f62d7a659b107402b6c23950ce2173b74470a98f73834f1c0ec13761d7d`; the paired measurement (section 4) | `FAIL L6` on every native boot at 50,400 to 55,000 answered a second (0.35, 0.45, 0.35; the plant 0.29), the release tier 0.94 and 0.95; L2's one `FAIL` 7,575/2,453 us with interrupts off at most 1.9 ms |
| L2's floor, L6's offered rate, unmeasured and its holds, seen red | `tests/mpx6-latency.d/rows-selftest` at `f577949c` | `rows-selftest: FAIL S1: rows.py has no l2_parts`; S1 to S5 pass from `8eb61778` |
| the offered flood | `2064251d`, `37467a66`, `bb57f45a`, `86fa9f30`, `ffe2c55a`; the light-slot check at `28344b2f` | offered 3,999 to 4,001 a second, the hog 0.99 |
| the takes at the head, native and release, and the plant | `notes/px131/rig/{green-2a,green-2b,release-2,plant-2,final-2}.manifest` | their records and `END` lines are in the PR |

## 8. Decisions

The first part's decisions 1, 3 and 4 were taken as recommended: the bound (a path a user can drive keeps interrupts off
at most 1 ms, anything at most 10 ms, a wake-up at most three times the same boot's `spin`), the clocks from the clock,
and device-driven wake-ups at once with the flood named and held by a row. Its order for the rest (deferred work and
interrupt-driven block I/O, then reschedule points in long calls, then interrupts on in calls with the second
processor) is the plan.

14. **The clocks' form.** (A) the tick count follows `kernel/clock`, so every deadline already counted in ticks is one
    in real time at the tick's resolution, with no caller changed (implemented, recommended: cheap, local, certain);
    (B) CLOCK_MONOTONIC and CLOCK_REALTIME read `kernel/clock`'s nanoseconds at each call, and sleeps and timeouts
    become deadlines in nanoseconds: finer, but every caller changes and every clock read becomes a counter read.
    (B) can follow (A) at any time.
15. **Who is urgent.** (A) the network thread, the readers its deliveries wake, and the console's readers; the switch
    at a device's interrupt and at the tick (implemented, recommended); (B) every thread a wake-up makes ready: that is
    the next step's, and needs its budget first.
16. **A wait's deadline after its event.** (A) the two `kernel/xhci` loops look at their completion before their
    deadline (implemented, recommended: with real-time deadlines a stretch could otherwise quarantine a controller that
    answered); (B) leave them: a stretch of 2 s in a USB command's wait is rare.
17. **The flood's budget.** (A) none until a flood is seen to starve a process (taken; the six-CPU flood has now
    starved the native kernel's hog: pax#408); (B) a budget now. The budget once sketched here (a thread
    loses its urgent mark after half a tick) would not do: the plant, with no urgent mark at all, kept the hog at 0.29
    under the same flood. The work is a budget on the network thread's own work a tick or fewer interrupts a frame, and
    the native tier's cost a frame (section 4).
18. **The guest's memory in the guard.** (A) backed before boot, PAX's and Linux's alike (implemented in the first
    part, recommended: the host's page faults are not the guest's stretches); (B) left to fault: the yardstick of L2 is now a few milliseconds,
    so a fault of the host's could fail it.
19. **The USB session's repeat row.** (A) hold for the interrupts the guest took and leave out the intervals that span
    ticks it lost, a slow or uneven repeat with no loss still refused (implemented, recommended); (B) widen the bounds:
    a repeat broken slow would pass; (C) keep the repeat's deadlines on the interrupts taken: the stamps are the
    clock's now, so the stall would still show.
20. **A hold the host stalled past measuring.** (A) `repeat unmeasured` its own verdict, held again at most three
    times with a fresh boot each, a measured result final at once, three unmeasured holds a red named `R-unmeasured`
    with exit 3 (implemented, recommended); (B) a named SKIP: wrong for a required row; (C) exit 1 as any failure: a
    stalled host reads as a failing kernel.
21. **The flood row's form.** (A) the host offers a fixed rate, 4,000 datagrams a second, the hog held to half its share
    there on both tiers, a host that did not offer it unmeasured and held again as the USB row is, and the saturating
    flood kept as an unbounded `~L6` curve (implemented, recommended); (B) the saturating flood bounded, the rig pinned
    to two CPUs: two-CPU takes already ranged from 8,300 to 32,600 answered a second; (C) the budget first: its own
    work (decision 17).
22. **L2's host ping.** (A) within the larger of three times `spin`'s and `spin`'s plus 10 ms, the bound's own figure
    for anything, the instrument's interrupts-off stretch printed beside it (implemented, recommended); (B) a breach
    counted only when the instrument puts a stretch over the bound in that window; (C) four times `spin`'s: a bound
    with no reason.
